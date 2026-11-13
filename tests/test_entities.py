"""The devices and entities of the fake Cube, against a real server."""

from __future__ import annotations

import asyncio
import copy
from collections.abc import Callable

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_API_KEY, CONF_URL, CONF_VERIFY_SSL, STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.massimo.api import MassimoConnectionError, StreamEvent
from custom_components.massimo.const import DOMAIN

from .conftest import Server, http


async def _setup(hass: HomeAssistant, server: Server) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=server.node_id or server.url,
        data={CONF_URL: server.url, CONF_API_KEY: server.key, CONF_VERIFY_SSL: True},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    return entry


async def _unload(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


def _entity(hass: HomeAssistant, platform: str, unique_id: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(platform, DOMAIN, unique_id)
    assert entity_id, f"no {platform} {unique_id}"
    return entity_id


async def _until(hass: HomeAssistant, holds: Callable[[], bool], what: str, seconds: float = 10) -> None:
    """Waits until holds() does: a refresh is a background task, which
    async_block_till_done does not wait for, beside the endless streams."""
    for _ in range(int(seconds * 10)):
        await hass.async_block_till_done()
        if holds():
            return
        await asyncio.sleep(0.1)
    raise AssertionError(what)


def _devices(server: Server) -> list[tuple[dict, dict]]:
    rooms = http("GET", f"{server.url}/api/v1/cubes/{server.serial}/rooms", server.owner)
    return [(room, dev) for room in rooms for dev in room.get("devices") or []]  # type: ignore[union-attr]


def _first(server: Server, kind: str) -> tuple[dict, dict]:
    return next((room, dev) for room, dev in _devices(server) if dev["type"] == kind)


async def test_devices_and_their_areas(hass: HomeAssistant, massimo_server: Server, socket_enabled: None) -> None:
    """The Cube is a hub, each device a device of its own beneath it, in an
    area named as its room."""
    entry = await _setup(hass, massimo_server)
    devices = dr.async_get(hass)
    areas = ar.async_get(hass)
    cube = devices.async_get_device_by_identifier((DOMAIN, massimo_server.serial), entry.entry_id)
    assert cube is not None and cube.model == "MAX! Cube" and cube.name == "Fake Cube"
    for room, dev in _devices(massimo_server):
        device = devices.async_get_device_by_identifier((DOMAIN, dev["serial"]), entry.entry_id)
        assert device is not None, dev["serial"]
        assert device.via_device_id == cube.id
        assert device.serial_number == dev["serial"]
        assert device.manufacturer == "eQ-3" and device.model and device.model.startswith("MAX! ")
        area = areas.async_get_area(device.area_id) if device.area_id else None
        assert area is not None and area.name == room["name"], f"{dev['serial']} is in its room's area"
    await _unload(hass, entry)


async def test_the_entities_show_the_devices(hass: HomeAssistant, massimo_server: Server, socket_enabled: None) -> None:
    """A thermostat's temperature, valve and key lock, a contact's window,
    every device's battery, the Cube's connection and budget."""
    entry = await _setup(hass, massimo_server)
    _, thermostat = _first(massimo_server, "radiator_thermostat")
    serial, state = thermostat["serial"], thermostat["state"]
    temperature = hass.states.get(_entity(hass, "sensor", f"{serial}_temperature"))
    assert float(temperature.state) == state["actual_temp"]
    assert temperature.attributes["unit_of_measurement"] == "°C"
    assert float(hass.states.get(_entity(hass, "sensor", f"{serial}_valve")).state) == state["valve_pct"]
    lock = hass.states.get(_entity(hass, "switch", f"{serial}_key_lock"))
    assert lock.state == (STATE_ON if state.get("panel_locked") else STATE_OFF)
    assert hass.states.get(_entity(hass, "binary_sensor", f"{serial}_battery")).state == STATE_OFF

    _, contact = _first(massimo_server, "shutter_contact")
    window = hass.states.get(_entity(hass, "binary_sensor", f"{contact['serial']}_window"))
    assert window.state == (STATE_ON if contact["state"]["window_open"] else STATE_OFF)
    registry = er.async_get(hass)
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{contact['serial']}_temperature") is None
    assert registry.async_get_entity_id("switch", DOMAIN, f"{contact['serial']}_key_lock") is None

    cube = massimo_server.serial
    assert hass.states.get(_entity(hass, "binary_sensor", f"{cube}_connected")).state == STATE_ON
    assert hass.states.get(_entity(hass, "sensor", f"{cube}_free_memory_slots")).state.isdigit()
    await _unload(hass, entry)


async def test_the_key_lock_writes_through_massimo(
    hass: HomeAssistant, massimo_server: Server, socket_enabled: None
) -> None:
    """Turning the key lock on sends Massimo's lock command for the
    thermostat, as the audit shows; off unlocks it again."""
    entry = await _setup(hass, massimo_server)
    _, thermostat = _first(massimo_server, "radiator_thermostat")
    lock = _entity(hass, "switch", f"{thermostat['serial']}_key_lock")

    def locks() -> list[dict]:
        rows = http("GET", f"{massimo_server.url}/api/v1/audit?user=homeassistant&limit=50", massimo_server.owner)
        return [r for r in rows if r["action"] == "device.lock"]  # type: ignore[union-attr]

    before = len(await hass.async_add_executor_job(locks))
    for service, locked in (("turn_on", True), ("turn_off", False)):
        await hass.services.async_call("switch", service, {"entity_id": lock}, blocking=True)
        rows = await hass.async_add_executor_job(locks)
        assert rows[0]["target"] == f"device:{thermostat['serial']}"
        assert rows[0]["detail"]["body"] == {"locked": locked}
        assert rows[0]["result"] == "ok"
    assert len(await hass.async_add_executor_job(locks)) == before + 2
    await _unload(hass, entry)


async def test_availability(hass: HomeAssistant, massimo_server: Server, socket_enabled: None) -> None:
    """A device's entities are unavailable while its Cube is disconnected or
    the stream is down, and available again when the stream opens, whether
    or not an event follows."""
    entry = await _setup(hass, massimo_server)
    coordinator = entry.runtime_data
    cube = massimo_server.serial
    _, thermostat = _first(massimo_server, "radiator_thermostat")
    temperature = _entity(hass, "sensor", f"{thermostat['serial']}_temperature")
    connected = _entity(hass, "binary_sensor", f"{cube}_connected")

    coordinator._apply(cube, StreamEvent("disconnected", {"kind": "disconnected"}, None))
    await hass.async_block_till_done()
    assert hass.states.get(temperature).state == STATE_UNAVAILABLE
    assert hass.states.get(connected).state == STATE_OFF
    coordinator._apply(cube, StreamEvent("connected", {"kind": "connected"}, None))
    await _until(hass, lambda: hass.states.get(temperature).state != STATE_UNAVAILABLE, "available when connected")
    assert hass.states.get(connected).state == STATE_ON

    coordinator.async_set_update_error(MassimoConnectionError("the stream broke"))
    await hass.async_block_till_done()
    assert hass.states.get(temperature).state == STATE_UNAVAILABLE
    assert hass.states.get(connected).state == STATE_UNAVAILABLE
    coordinator._apply(cube, StreamEvent("open", {}, None))
    await hass.async_block_till_done()
    assert hass.states.get(temperature).state != STATE_UNAVAILABLE
    assert hass.states.get(connected).state == STATE_ON

    # A device that has not reported, or is stale, says nothing current.
    dev = coordinator.data.cubes[cube].device(thermostat["rf_address"])
    dev["stale"] = True
    coordinator.async_set_updated_data(coordinator.data)
    await hass.async_block_till_done()
    assert hass.states.get(temperature).state == STATE_UNAVAILABLE
    await _unload(hass, entry)


async def test_devices_come_and_go_with_the_data(
    hass: HomeAssistant, massimo_server: Server, socket_enabled: None
) -> None:
    """A device the data brings gets its entities without a reload; once the
    server's rooms no longer list it, it leaves the registry with them."""
    entry = await _setup(hass, massimo_server)
    coordinator = entry.runtime_data
    cube = coordinator.data.cubes[massimo_server.serial]
    room, contact = _first(massimo_server, "shutter_contact")
    extra = copy.deepcopy(contact) | {"rf_address": "0a0f0f", "serial": "MEQ0009999", "name": "Extra contact"}
    next(r for r in cube.rooms if r["id"] == room["id"])["devices"].append(extra)
    coordinator.async_set_updated_data(coordinator.data)
    await hass.async_block_till_done()
    window = _entity(hass, "binary_sensor", "MEQ0009999_window")
    assert hass.states.get(window) is not None
    devices = dr.async_get(hass)
    assert devices.async_get_device_by_identifier((DOMAIN, "MEQ0009999"), entry.entry_id) is not None

    coordinator._refresh(massimo_server.serial)
    await _until(
        hass,
        lambda: devices.async_get_device_by_identifier((DOMAIN, "MEQ0009999"), entry.entry_id) is None,
        "the device left",
    )
    assert devices.async_get_device_by_identifier((DOMAIN, "MEQ0009999"), entry.entry_id) is None
    assert er.async_get(hass).async_get_entity_id("binary_sensor", DOMAIN, "MEQ0009999_window") is None
    assert hass.states.get(window) is None
    await _unload(hass, entry)
