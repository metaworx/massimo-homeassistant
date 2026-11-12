"""Binary sensors: a device's battery, window and errors, a Cube's
connection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, override

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import MODELS
from .coordinator import MassimoConfigEntry
from .entity import CubeEntity, DeviceEntity, add_entities_as_they_come, devices_of


@dataclass(frozen=True, kw_only=True)
class DeviceBinarySensorDescription(BinarySensorEntityDescription):
    """A binary sensor of the devices of some types, from a state field."""

    types: frozenset[str]
    field: str


ALL = frozenset(MODELS)

DEVICE_BINARY_SENSORS = (
    DeviceBinarySensorDescription(
        key="battery",
        types=ALL,
        field="battery_low",
        device_class=BinarySensorDeviceClass.BATTERY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DeviceBinarySensorDescription(
        key="window",
        types=frozenset({"shutter_contact"}),
        field="window_open",
        device_class=BinarySensorDeviceClass.WINDOW,
    ),
    # A failed link with a partner device, such as the room's wall
    # thermostat.
    DeviceBinarySensorDescription(
        key="link_error",
        translation_key="link_error",
        types=ALL,
        field="link_error",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # The Cube's flag that a command to the device was not delivered.
    DeviceBinarySensorDescription(
        key="transmit_error",
        translation_key="transmit_error",
        types=ALL,
        field="error",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

CONNECTED = BinarySensorEntityDescription(
    key="connected",
    translation_key="connected",
    device_class=BinarySensorDeviceClass.CONNECTIVITY,
    entity_category=EntityCategory.DIAGNOSTIC,
)


async def async_setup_entry(
    hass: HomeAssistant, entry: MassimoConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add the binary sensors of the server's Cubes and devices."""
    coordinator = entry.runtime_data

    def make():
        for serial in coordinator.data.cubes:
            yield f"{serial}_{CONNECTED.key}", lambda serial=serial: CubeConnected(coordinator, serial, CONNECTED)
        for serial, dev in devices_of(coordinator):
            for d in DEVICE_BINARY_SENSORS:
                if dev.get("type") in d.types:
                    yield f"{serial}_{d.key}", lambda serial=serial, d=d: DeviceBinarySensor(coordinator, serial, d)

    add_entities_as_they_come(coordinator, entry, async_add_entities, make)


class DeviceBinarySensor(DeviceEntity, BinarySensorEntity):
    """A binary sensor of a device."""

    entity_description: DeviceBinarySensorDescription

    @property
    @override
    def is_on(self) -> bool | None:
        """The flag the device last reported."""
        value: Any = self.state_data.get(self.entity_description.field)
        return None if value is None else bool(value)


class CubeConnected(CubeEntity, BinarySensorEntity):
    """Whether Massimo is connected to the Cube."""

    @property
    @override
    def available(self) -> bool:
        """Whether the stream is up: the connection is known then."""
        return self.coordinator.last_update_success and self.cube is not None

    @property
    @override
    def is_on(self) -> bool:
        """Whether the Cube is connected."""
        cube = self.cube
        return bool(cube and cube.info.get("connected"))
