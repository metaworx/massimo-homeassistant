"""The rooms: a device per room on its virtual wall thermostat, its climate
and its temperature method, against a real server and the fake Cube's
fixture rooms (tests/conftest.py)."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from homeassistant.components.climate import HVACAction, HVACMode
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.massimo.api import MassimoClient
from custom_components.massimo.climate import RoomClimate, vacation_until
from custom_components.massimo.const import DOMAIN

from .conftest import Server, http, rooms
from .test_entities import _entity, _setup, _unload, _until

ECO, COMFORT = 15, 22  # the fixture's rooms
# The fixture's rooms by id: their names change, as test_init renames one.
WOHNEN, SCHLAFEN = 1, 2


def _room(server: Server, room_id: int) -> dict:
    return next(r for r in rooms(server) if r["id"] == room_id)


def _climate(hass: HomeAssistant, server: Server, room_id: int) -> str:
    return _entity(hass, "climate", f"{server.serial}_{_room(server, room_id)['room_uid']}_climate")


async def _call(hass: HomeAssistant, service: str, entity_id: str, **data: object) -> None:
    domain = DOMAIN if service == "set_vacation" else "climate"
    await hass.services.async_call(domain, service, {"entity_id": entity_id, **data}, blocking=True)


def _attr(hass: HomeAssistant, entity_id: str, name: str) -> object:
    return hass.states.get(entity_id).attributes.get(name)


async def test_rooms_are_devices(hass: HomeAssistant, massimo_server: Server, socket_enabled: None) -> None:
    """A room with a thermostat is a device beneath its Cube, in its area,
    with a climate and a temperature method; the room with only a window
    contact has none, its contact being a device of its own in its area; no
    virtual wall thermostat is a device of its own."""
    entry = await _setup(hass, massimo_server)
    devices = dr.async_get(hass)
    areas = ar.async_get(hass)
    registry = er.async_get(hass)
    cube = devices.async_get_device_by_identifier((DOMAIN, massimo_server.serial), entry.entry_id)
    for room in rooms(massimo_server):
        uid = room["room_uid"]
        device = devices.async_get_device_by_identifier((DOMAIN, f"{massimo_server.serial}:{uid}"), entry.entry_id)
        climate = registry.async_get_entity_id("climate", DOMAIN, f"{massimo_server.serial}_{uid}_climate")
        method = registry.async_get_entity_id("select", DOMAIN, f"{massimo_server.serial}_{uid}_temp_method")
        assert devices.async_get_device_by_identifier((DOMAIN, f"VWT{room['id']:07d}"), entry.entry_id) is None
        if not any("thermostat" in d["type"] for d in room["devices"]):
            assert device is None and climate is None and method is None, room["name"]
            continue
        assert device is not None and device.model == "Room" and device.name == room["name"]
        assert device.via_device_id == cube.id
        assert device.serial_number == f"VWT{room['id']:07d}"
        assert areas.async_get_area(device.area_id).name == room["name"]
        assert climate is not None and method is not None, room["name"]
        entity = registry.async_get(climate)
        assert entity.device_id == device.id
    await _unload(hass, entry)


async def test_the_room_temperature(hass: HomeAssistant, massimo_server: Server, socket_enabled: None) -> None:
    """A room with a wall thermostat has its temperature; one without has
    the median of its radiator thermostats; each says which devices
    measured it."""
    entry = await _setup(hass, massimo_server)
    wohnen = _climate(hass, massimo_server, WOHNEN)
    schlafen = _climate(hass, massimo_server, SCHLAFEN)
    assert _attr(hass, wohnen, "current_temperature") == 21.4
    assert _attr(hass, wohnen, "temperature_sources") == ["Wandthermostat Wohnen"]
    assert _attr(hass, schlafen, "current_temperature") == 19.5  # 19.0, 19.5, 23.5
    assert len(_attr(hass, schlafen, "temperature_sources")) == 3
    assert _attr(hass, schlafen, "min_temp") == 4.5 and _attr(hass, schlafen, "max_temp") == 30.5
    await _unload(hass, entry)


async def test_modes_and_presets(hass: HomeAssistant, massimo_server: Server, socket_enabled: None) -> None:
    """A setpoint holds as heat; eco and comfort hold the room's
    temperatures; off holds 4.5 °C, heat after it the comfort temperature;
    none goes back to the week programme; away is refused, naming the
    vacation action."""
    entry = await _setup(hass, massimo_server)
    room = _climate(hass, massimo_server, SCHLAFEN)

    def shows(target: float, mode: str, preset: str | None = None):
        def holds() -> bool:
            state = hass.states.get(room)
            return (
                state.attributes.get("temperature") == target
                and state.state == mode
                and (preset is None or state.attributes.get("preset_mode") == preset)
            )

        return holds

    try:
        await _call(hass, "set_temperature", room, temperature=21.5)
        await _until(hass, shows(21.5, HVACMode.HEAT, "none"), "a setpoint holds as heat")
        await _call(hass, "set_preset_mode", room, preset_mode="eco")
        await _until(hass, shows(ECO, HVACMode.HEAT, "eco"), "eco")
        await _call(hass, "set_preset_mode", room, preset_mode="comfort")
        await _until(hass, shows(COMFORT, HVACMode.HEAT, "comfort"), "comfort")
        await _call(hass, "set_hvac_mode", room, hvac_mode="off")
        await _until(hass, shows(4.5, HVACMode.OFF), "off")
        assert _attr(hass, room, "hvac_action") == HVACAction.OFF
        await _call(hass, "set_hvac_mode", room, hvac_mode="heat")
        await _until(hass, shows(COMFORT, HVACMode.HEAT), "heat after off is comfort")
        with pytest.raises(ServiceValidationError) as refused:
            await _call(hass, "set_preset_mode", room, preset_mode="away")
        assert refused.value.translation_key == "away_needs_vacation"
        await _call(hass, "set_preset_mode", room, preset_mode="none")
        await _until(hass, lambda: hass.states.get(room).state == HVACMode.AUTO, "none is the week programme")
    finally:
        await _call(hass, "set_hvac_mode", room, hvac_mode="auto")
    await _unload(hass, entry)


async def test_vacation(hass: HomeAssistant, massimo_server: Server, socket_enabled: None) -> None:
    """massimo.set_vacation holds a temperature until an end rounded up to
    the half hour, shown as away; an end in the past is refused."""
    entry = await _setup(hass, massimo_server)
    room = _climate(hass, massimo_server, SCHLAFEN)
    end = dt_util.now().replace(second=0, microsecond=0) + timedelta(days=2)
    end = end.replace(minute=10)
    until = end.replace(minute=30).strftime("%Y-%m-%d %H:%M")
    try:
        await _call(hass, "set_vacation", room, temperature=16, end=end.isoformat())
        await _until(hass, lambda: _attr(hass, room, "preset_mode") == "away", "vacation shows as away")
        assert _attr(hass, room, "temperature") == 16
        assert _attr(hass, room, "vacation_until") == until
        with pytest.raises(ServiceValidationError) as refused:
            await _call(
                hass, "set_vacation", room, temperature=16, end=(dt_util.now() - timedelta(hours=1)).isoformat()
            )
        assert refused.value.translation_key == "vacation_in_past"
    finally:
        await _call(hass, "set_hvac_mode", room, hvac_mode="auto")
    await _until(hass, lambda: hass.states.get(room).state == HVACMode.AUTO, "back to the week programme")
    await _unload(hass, entry)


def test_a_vacation_ends_on_the_half_hour() -> None:
    """The end is rounded up to the next half hour, kept where it is on
    one."""
    now = dt_util.as_local(dt_util.utcnow()).replace(
        year=2026, month=11, day=13, hour=12, minute=0, second=0, microsecond=0
    )
    at = now.replace(hour=14)
    assert vacation_until(at.replace(minute=0), now) == at.strftime("%Y-%m-%d 14:00")
    assert vacation_until(at.replace(minute=1), now) == at.strftime("%Y-%m-%d 14:30")
    assert vacation_until(at.replace(minute=30), now) == at.strftime("%Y-%m-%d 14:30")
    assert vacation_until(at.replace(minute=31), now) == at.strftime("%Y-%m-%d 15:00")


def test_the_temperatures_by_both_names() -> None:
    """Home Assistant 2026.11 names climate's temperatures native_* and
    warns of an entity that gives an old name alone (it stops working in
    2027.11); 2026.10 reads the old names. A room gives each by both names,
    the same value, so that 2026.11 takes the native one without a warning.
    """
    names = {
        "_attr_temperature_unit": "_attr_native_temperature_unit",
        "current_temperature": "native_current_temperature",
        "target_temperature": "native_target_temperature",
    }
    own = vars(RoomClimate)
    for old, native in names.items():
        assert old in own and native in own, (old, native)
    assert own["current_temperature"] is own["native_current_temperature"]
    assert own["target_temperature"] is own["native_target_temperature"]
    # Home Assistant makes an _attr_ class attribute a property; an instance
    # reads its value.
    room = RoomClimate.__new__(RoomClimate)
    assert room._attr_temperature_unit == room._attr_native_temperature_unit == UnitOfTemperature.CELSIUS
    assert not {"temperature_unit", "target_temperature_high", "target_temperature_low"} & own.keys()


async def test_the_temperature_method(hass: HomeAssistant, massimo_server: Server, socket_enabled: None) -> None:
    """The method mean makes a room without a wall thermostat take the mean
    of its radiator thermostats; median again their median."""
    entry = await _setup(hass, massimo_server)
    room = _climate(hass, massimo_server, SCHLAFEN)
    uid = _room(massimo_server, SCHLAFEN)["room_uid"]
    method = _entity(hass, "select", f"{massimo_server.serial}_{uid}_temp_method")
    assert hass.states.get(method).state == "median"
    try:
        await hass.services.async_call(
            "select", "select_option", {"entity_id": method, "option": "mean"}, blocking=True
        )
        await _until(hass, lambda: _attr(hass, room, "current_temperature") == 20.7, "the mean of 19.0, 19.5, 23.5")
        await _until(hass, lambda: hass.states.get(method).state == "mean", "the select shows mean")
    finally:
        await hass.services.async_call(
            "select", "select_option", {"entity_id": method, "option": "median"}, blocking=True
        )
    await _until(hass, lambda: _attr(hass, room, "current_temperature") == 19.5, "the median again")
    await _unload(hass, entry)


async def test_a_wall_thermostat_comes_and_goes(
    hass: HomeAssistant, massimo_server: Server, socket_enabled: None
) -> None:
    """A room's device and climate stay while its wall thermostat leaves
    and comes back: the temperature is then its radiator thermostats', then
    the wall thermostat's again."""
    entry = await _setup(hass, massimo_server)
    room = _climate(hass, massimo_server, WOHNEN)
    uid = _room(massimo_server, WOHNEN)["room_uid"]
    devices = dr.async_get(hass)
    device = devices.async_get_device_by_identifier((DOMAIN, f"{massimo_server.serial}:{uid}"), entry.entry_id)
    wall = next(d for d in _room(massimo_server, WOHNEN)["devices"] if d["type"] == "wall_thermostat")

    def control(action: str) -> None:
        http("POST", f"{massimo_server.control}/devices/{wall['rf_address']}/{action}", None)
        http("POST", f"{massimo_server.control}/drop", None)

    try:
        await hass.async_add_executor_job(control, "remove")
        await _until(
            hass,
            lambda: _attr(hass, room, "temperature_sources") == ["Heizung Wohnen Fenster", "Heizung Wohnen Tür"],
            "the radiator thermostats measure the room",
            seconds=30,
        )
        assert _attr(hass, room, "current_temperature") in (21.2, 21.3)  # the median of 20.5 and 22.0
    finally:
        await hass.async_add_executor_job(control, "restore")
    await _until(hass, lambda: _attr(hass, room, "current_temperature") == 21.4, "the wall thermostat again", 30)
    same = devices.async_get_device_by_identifier((DOMAIN, f"{massimo_server.serial}:{uid}"), entry.entry_id)
    assert same is not None and same.id == device.id
    assert _climate(hass, massimo_server, WOHNEN) == room
    await _unload(hass, entry)


async def test_a_massimo_without_virtual_wall_thermostats(
    hass: HomeAssistant, massimo_server: Server, socket_enabled: None, caplog: pytest.LogCaptureFixture
) -> None:
    """A server that does not list vwt gets its devices but no rooms, and a
    warning that the rooms need a newer Massimo; without idempotency, a
    lost write is not sent again."""
    health = MassimoClient.health

    async def older(self: MassimoClient) -> dict:
        return {k: v for k, v in (await health(self)).items() if k != "features"}

    with patch.object(MassimoClient, "health", older):
        entry = await _setup(hass, massimo_server)
    coordinator = entry.runtime_data
    assert coordinator.client.devices == "real" and coordinator.client.retry_writes is False
    assert not hass.states.async_entity_ids("climate")
    assert not hass.states.async_entity_ids("select")
    assert hass.states.async_entity_ids("sensor"), "the devices are there"
    assert "its rooms need a newer Massimo" in caplog.text
    await _unload(hass, entry)


async def test_boost(hass: HomeAssistant, massimo_server: Server, socket_enabled: None) -> None:
    """The preset boost opens the room's valves; after the boost time the
    thermostats go back to the mode they had by themselves."""
    entry = await _setup(hass, massimo_server)
    room = _climate(hass, massimo_server, SCHLAFEN)
    assert "boost" in _attr(hass, room, "preset_modes")
    await _until(hass, lambda: hass.states.get(room).state == HVACMode.AUTO, "the room follows its programme")
    await _call(hass, "set_preset_mode", room, preset_mode="boost")
    await _until(hass, lambda: _attr(hass, room, "preset_mode") == "boost", "the room boosts")
    assert hass.states.get(room).state == HVACMode.HEAT
    assert _attr(hass, room, "hvac_action") == HVACAction.HEATING
    await _until(hass, lambda: hass.states.get(room).state == HVACMode.AUTO, "back to the programme", seconds=20)
    assert _attr(hass, room, "preset_mode") == "none"
    await _unload(hass, entry)


async def test_no_boost_without_the_feature(hass: HomeAssistant, massimo_server: Server, socket_enabled: None) -> None:
    """A server that does not list boost gets no preset boost, and choosing
    it is refused."""
    health = MassimoClient.health

    async def without_boost(self: MassimoClient) -> dict:
        answer = await health(self)
        answer["features"] = {k: v for k, v in answer["features"].items() if k != "boost"}
        return answer

    with patch.object(MassimoClient, "health", without_boost):
        entry = await _setup(hass, massimo_server)
    room = _climate(hass, massimo_server, SCHLAFEN)
    assert "boost" not in _attr(hass, room, "preset_modes")
    with pytest.raises(ServiceValidationError):
        await _call(hass, "set_preset_mode", room, preset_mode="boost")
    await _unload(hass, entry)
