"""Sensors: a thermostat's measured temperature and valve, a Cube's radio
budget and queue."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, override

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import RADIATOR_THERMOSTATS, THERMOSTATS
from .coordinator import MassimoConfigEntry
from .entity import CubeEntity, DeviceEntity, ServerEntity, add_entities_as_they_come, devices_of


@dataclass(frozen=True, kw_only=True)
class DeviceSensorDescription(SensorEntityDescription):
    """A sensor of the devices of some types, its value from the state."""

    types: frozenset[str]
    value_fn: Callable[[dict[str, Any]], Any]


@dataclass(frozen=True, kw_only=True)
class CubeSensorDescription(SensorEntityDescription):
    """A sensor of a Cube, its value from the Cube's data."""

    value_fn: Callable[[dict[str, Any]], Any]


DEVICE_SENSORS = (
    # Radiator thermostats report the measured temperature only now and
    # then; the sensor shows what Massimo has.
    DeviceSensorDescription(
        key="temperature",
        types=THERMOSTATS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda state: state.get("actual_temp"),
    ),
    DeviceSensorDescription(
        key="valve",
        translation_key="valve",
        types=RADIATOR_THERMOSTATS,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda state: state.get("valve_pct"),
    ),
)

CUBE_SENSORS = (
    CubeSensorDescription(
        key="duty_cycle",
        translation_key="duty_cycle",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda info: (info.get("budget") or {}).get("duty_cycle_pct"),
    ),
    CubeSensorDescription(
        key="free_memory_slots",
        translation_key="free_memory_slots",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda info: (info.get("budget") or {}).get("free_memory_slots"),
    ),
    CubeSensorDescription(
        key="pending_radiograms",
        translation_key="pending_radiograms",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda info: info.get("pending_radiograms"),
    ),
    CubeSensorDescription(
        key="queued",
        translation_key="queued",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda info: info.get("queued"),
    ),
)


# The server's: when it last answered or sent an event, off by default
# since it changes with each; and how the entry signs in to it.
LAST_CONTACT = SensorEntityDescription(
    key="last_contact",
    translation_key="last_contact",
    device_class=SensorDeviceClass.TIMESTAMP,
    entity_category=EntityCategory.DIAGNOSTIC,
    entity_registry_enabled_default=False,
)
SIGNED_IN_AS = SensorEntityDescription(
    key="signed_in_as",
    translation_key="signed_in_as",
    device_class=SensorDeviceClass.ENUM,
    options=["registered", "user_key", "no_users"],
    entity_category=EntityCategory.DIAGNOSTIC,
)


async def async_setup_entry(
    hass: HomeAssistant, entry: MassimoConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add the sensors of the server, its Cubes and devices."""
    coordinator = entry.runtime_data
    async_add_entities([LastContact(coordinator, LAST_CONTACT), SignedInAs(coordinator, SIGNED_IN_AS)])

    def make():
        for serial in coordinator.data.cubes:
            for c in CUBE_SENSORS:
                yield f"{serial}_{c.key}", lambda serial=serial, c=c: CubeSensor(coordinator, serial, c)
        for serial, dev in devices_of(coordinator):
            for d in DEVICE_SENSORS:
                if dev.get("type") in d.types:
                    yield f"{serial}_{d.key}", lambda serial=serial, d=d: DeviceSensor(coordinator, serial, d)

    add_entities_as_they_come(coordinator, entry, async_add_entities, make)


class DeviceSensor(DeviceEntity, SensorEntity):
    """A sensor of a device."""

    entity_description: DeviceSensorDescription

    @property
    @override
    def native_value(self) -> Any:
        """The value the device last reported."""
        return self.entity_description.value_fn(self.state_data)


class CubeSensor(CubeEntity, SensorEntity):
    """A sensor of a Cube."""

    entity_description: CubeSensorDescription

    @property
    @override
    def native_value(self) -> Any:
        """The value the Cube last reported."""
        cube = self.cube
        return self.entity_description.value_fn(cube.info) if cube else None


class LastContact(ServerEntity, SensorEntity):
    """When the server last answered a read or sent an event."""

    @property
    @override
    def available(self) -> bool:
        """Always: the time stays known while the connection is lost."""
        return self.coordinator.last_contact is not None

    @property
    @override
    def native_value(self) -> datetime | None:
        """The last contact."""
        return self.coordinator.last_contact


class SignedInAs(ServerEntity, SensorEntity):
    """How the entry signs in: registered, with a person's key, or to a
    server without users."""

    @property
    @override
    def native_value(self) -> str:
        """The way the entry signs in."""
        if self.coordinator.integration is not None:
            return "registered"
        return "user_key" if self.coordinator.me.get("mode") == "users" else "no_users"

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        """The key's person, where it is one's."""
        if self.native_value != "user_key":
            return {}
        return {"user": (self.coordinator.me.get("user") or {}).get("name")}
