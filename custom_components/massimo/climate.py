"""A `climate` per room, on the room's virtual wall thermostat.

Massimo computes the room's values (its docs/api-v1.md, the virtual wall
thermostat): the temperature is the room's wall thermostat's, else the
median or mean of its radiator thermostats; mode and setpoint are those its
thermostats hold. Writes go to the room through the virtual wall
thermostat's routes, and the entity shows them once the thermostats report
them.

The modes are MAX!'s: ``auto`` follows the week programme, ``heat`` holds a
setpoint (manual), ``off`` holds 4.5 °C, which a thermostat shows as off.
The presets ``eco`` and ``comfort`` hold the room's eco and comfort
temperatures, ``away`` is vacation mode, set with ``massimo.set_vacation``
for its temperature and end, and ``none`` goes back to the week programme.
``boost``, where the server lists the feature boost, opens the valves for
the thermostats' boost time, after which they go back to the mode they had
by themselves; it shows while any thermostat of the room boosts.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any, override

import probatio
from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    PRESET_AWAY,
    PRESET_BOOST,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_NONE,
    ClimateEntity,
    ClimateEntityDescription,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import MassimoConfigEntry, has_thermostat
from .entity import RoomEntity, add_entities_as_they_come, rooms_of

# What MAX! calls off: a manual setpoint of 4.5 °C, shown as "OFF".
OFF_TEMP = 4.5
MIN_TEMP = 4.5
MAX_TEMP = 30.5
STEP = 0.5

SERVICE_SET_VACATION = "set_vacation"
ATTR_END = "end"

ROOM = ClimateEntityDescription(key="climate")


async def async_setup_entry(
    hass: HomeAssistant, entry: MassimoConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add a `climate` per room with a thermostat, and the vacation
    service."""
    coordinator = entry.runtime_data

    def make():
        for serial, room in rooms_of(coordinator):
            if has_thermostat(room):
                uid = room["room_uid"]
                yield f"{serial}_{uid}", lambda serial=serial, uid=uid: RoomClimate(coordinator, serial, uid, ROOM)

    add_entities_as_they_come(coordinator, entry, async_add_entities, make)

    entity_platform.async_get_current_platform().async_register_entity_service(
        SERVICE_SET_VACATION,
        {
            probatio.Required(ATTR_TEMPERATURE): probatio.All(
                probatio.Coerce(float), probatio.Range(min=MIN_TEMP, max=MAX_TEMP)
            ),
            probatio.Required(ATTR_END): cv.datetime,
        },
        "async_set_vacation",
    )


def _half(value: float) -> float:
    """A temperature on MAX!'s steps of 0.5 °C."""
    return round(value * 2) / 2


def vacation_until(end: datetime, now: datetime) -> str:
    """A vacation's end as Massimo takes it: in local time, rounded up to
    the half hour, "YYYY-MM-DD HH:MM"; an end not after now is refused."""
    if end.tzinfo is None:
        end = end.replace(tzinfo=dt_util.get_default_time_zone())
    local = dt_util.as_local(end)
    hour = local.replace(minute=0, second=0, microsecond=0)
    rounded = hour + timedelta(minutes=30 * math.ceil((local - hour).total_seconds() / 1800))
    if rounded <= now:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="vacation_in_past")
    return rounded.strftime("%Y-%m-%d %H:%M")


class RoomClimate(RoomEntity, ClimateEntity):
    """A room's heating."""

    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = STEP
    _attr_hvac_modes = [HVACMode.AUTO, HVACMode.HEAT, HVACMode.OFF]
    _presets = [PRESET_NONE, PRESET_ECO, PRESET_COMFORT, PRESET_AWAY]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_translation_key = "room"

    @property
    def _mode(self) -> str | None:
        return self.state_data.get("mode")

    @property
    def _setpoint(self) -> float | None:
        return self.state_data.get("setpoint")

    @property
    @override
    def current_temperature(self) -> float | None:
        """The room's temperature, as Massimo computes it."""
        return self.state_data.get("actual_temp")

    @property
    @override
    def target_temperature(self) -> float | None:
        """The setpoint the room's thermostats hold."""
        return self._setpoint

    @property
    @override
    def min_temp(self) -> float:
        """The room's lowest setpoint."""
        return float(self.config.get("min_setpoint") or MIN_TEMP)

    @property
    @override
    def max_temp(self) -> float:
        """The room's highest setpoint."""
        return float(self.config.get("max_setpoint") or MAX_TEMP)

    @property
    @override
    def hvac_mode(self) -> HVACMode | None:
        """auto, off (manual at 4.5 °C), or heat."""
        mode = self._mode
        if mode is None:
            return None
        if mode == "auto":
            return HVACMode.AUTO
        if mode == "manual" and (self._setpoint or 0) <= OFF_TEMP:
            return HVACMode.OFF
        return HVACMode.HEAT

    @property
    @override
    def hvac_action(self) -> HVACAction | None:
        """Heating while a valve of the room is open."""
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        valve = self.state_data.get("valve_pct")
        if valve is None:
            return None
        return HVACAction.HEATING if valve > 0 else HVACAction.IDLE

    @property
    def _boost(self) -> bool:
        return self.coordinator.data.feature("boost")

    @property
    @override
    def preset_modes(self) -> list[str]:
        """none, eco, comfort, away, and boost where the server has it."""
        return [*self._presets, PRESET_BOOST] if self._boost else list(self._presets)

    @property
    @override
    def preset_mode(self) -> str | None:
        """away in vacation mode; boost while a thermostat boosts; eco or
        comfort where a manual setpoint is the room's eco or comfort
        temperature; else none."""
        mode, setpoint = self._mode, self._setpoint
        if mode == "vacation":
            return PRESET_AWAY
        if mode == "boost" and self._boost:
            return PRESET_BOOST
        if mode == "manual" and setpoint is not None:
            if setpoint == self.config.get("eco_temp"):
                return PRESET_ECO
            if setpoint == self.config.get("comfort_temp"):
                return PRESET_COMFORT
        return PRESET_NONE

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        """Whether the thermostats agree, which devices measure the room, a
        vacation's end, and whether radiograms are still on their way."""
        state = self.state_data
        names = {}
        found = self.found
        if found:
            names = {dev.get("rf_address"): dev.get("name") for dev in found[0].get("devices") or []}
        sources = (self.vwt.get("sources") or {}).get("actual_temp") or []
        cube = self.coordinator.data.cubes.get(self.cube_serial)
        return {
            "consistent": state.get("consistent"),
            "temperature_sources": [names.get(rf, rf) for rf in sources],
            "vacation_until": state.get("until") if self._mode == "vacation" else None,
            "pending": bool(cube and (cube.info.get("pending_radiograms") or 0) > 0),
        }

    async def _set(self, body: dict[str, Any]) -> None:
        rf = self.vwt.get("rf_address")
        if not rf:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="device_gone")
        await self.write(self.coordinator.client.set_setpoint(self.cube_serial, rf, body))

    @override
    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Hold a setpoint; with the mode auto, until the next switch
        point."""
        hvac_mode = kwargs.get(ATTR_HVAC_MODE)
        if hvac_mode == HVACMode.OFF:
            await self.async_set_hvac_mode(HVACMode.OFF)
            return
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            if hvac_mode is not None:
                await self.async_set_hvac_mode(hvac_mode)
            return
        mode = "auto" if hvac_mode == HVACMode.AUTO else "manual"
        await self._set({"mode": mode, "temp": _half(float(temp))})

    @override
    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """auto: the week programme; heat: the setpoint held, or the comfort
        temperature after off; off: 4.5 °C."""
        if hvac_mode == HVACMode.AUTO:
            await self._set({"mode": "auto"})
        elif hvac_mode == HVACMode.OFF:
            await self._set({"mode": "manual", "temp": OFF_TEMP})
        else:
            setpoint = self._setpoint
            if setpoint is None or setpoint <= OFF_TEMP:
                setpoint = float(self.config.get("comfort_temp") or 21)
            await self._set({"mode": "manual", "temp": _half(setpoint)})

    @override
    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """eco and comfort hold the room's temperatures; boost opens the
        valves for the boost time; none goes back to the week programme;
        away is set with massimo.set_vacation."""
        if preset_mode == PRESET_AWAY:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="away_needs_vacation")
        if preset_mode == PRESET_NONE:
            await self._set({"mode": "auto"})
            return
        if preset_mode == PRESET_BOOST:
            await self._set({"mode": "boost"})
            return
        key = "eco_temp" if preset_mode == PRESET_ECO else "comfort_temp"
        temp = self.config.get(key)
        if temp is None:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="room_not_read")
        await self._set({"mode": "manual", "temp": float(temp)})

    async def async_set_vacation(self, temperature: float, end: datetime) -> None:
        """Hold a temperature until an end, then go back to the week
        programme."""
        until = vacation_until(end, dt_util.now())
        await self._set({"mode": "vacation", "temp": _half(temperature), "until": until})
