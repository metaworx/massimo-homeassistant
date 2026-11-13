"""The entities' common ground: the devices they belong to, and when they
are available.

A Cube is a hub, each of its devices a device of its own, found by its
serial, which stays the same if it is paired to another Cube. A device's
area is suggested by its room's name; Home Assistant matches or creates
the area once, and the areas stay the owner's.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, override

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity, EntityDescription
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODELS
from .coordinator import CubeData, MassimoConfigEntry, MassimoCoordinator


class MassimoEntity(CoordinatorEntity[MassimoCoordinator]):
    """An entity of a Massimo server."""

    _attr_has_entity_name = True


class CubeEntity(MassimoEntity):
    """An entity of a Cube, available while the Cube is connected."""

    def __init__(self, coordinator: MassimoCoordinator, serial: str, description: EntityDescription) -> None:
        """Initialise the entity of a Cube's serial and a description."""
        super().__init__(coordinator)
        self.cube_serial = serial
        self.entity_description = description
        self._attr_unique_id = f"{serial}_{description.key}"
        info = coordinator.data.cubes[serial].info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            name=info.get("name") or serial,
            manufacturer=MANUFACTURER,
            model="MAX! Cube",
            serial_number=serial,
            sw_version=info.get("firmware"),
            configuration_url=coordinator.client.url,
        )

    @property
    def cube(self) -> CubeData | None:
        """The Cube's data, while the server lists it."""
        return self.coordinator.data.cubes.get(self.cube_serial)

    @property
    @override
    def available(self) -> bool:
        """Whether the stream is up and the Cube connected."""
        cube = self.cube
        return super().available and cube is not None and bool(cube.info.get("connected"))


class DeviceEntity(MassimoEntity):
    """An entity of a device, available while it reports through a
    connected Cube."""

    def __init__(self, coordinator: MassimoCoordinator, serial: str, description: EntityDescription) -> None:
        """Initialise the entity of a device's serial and a description."""
        super().__init__(coordinator)
        self.serial = serial
        self.entity_description = description
        self._attr_unique_id = f"{serial}_{description.key}"
        found = coordinator.data.find(serial)
        assert found is not None, "an entity is made for a device the data lists"
        cube_serial, room, dev = found
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            name=dev.get("name") or serial,
            manufacturer=MANUFACTURER,
            model=MODELS.get(dev.get("type", ""), dev.get("type")),
            serial_number=serial,
            via_device=(DOMAIN, cube_serial),
            suggested_area=room.get("name") or None,
        )

    @property
    def found(self) -> tuple[str, dict[str, Any], dict[str, Any]] | None:
        """The device's Cube serial, room and data, while the server
        lists it."""
        return self.coordinator.data.find(self.serial)

    @property
    def device(self) -> dict[str, Any]:
        """The device's data; empty once the server no longer lists it."""
        found = self.found
        return found[2] if found else {}

    @property
    def state_data(self) -> dict[str, Any]:
        """What the device last reported; empty before it has."""
        return self.device.get("state") or {}

    @property
    @override
    def available(self) -> bool:
        """Whether the stream is up, the Cube connected, and the device has
        reported and is not stale."""
        found = self.found
        if not super().available or found is None:
            return False
        cube = self.coordinator.data.cubes[found[0]]
        dev = found[2]
        return (
            bool(cube.info.get("connected"))
            and bool(dev.get("reported"))
            and dev.get("state") is not None
            and not dev.get("stale")
        )


def add_entities_as_they_come(
    coordinator: MassimoCoordinator,
    entry: MassimoConfigEntry,
    add: AddConfigEntryEntitiesCallback,
    make: Callable[[], Iterable[tuple[str, Callable[[], Entity]]]],
) -> None:
    """Add the entities make lists, by a key each, now and whenever the data
    brings one that is not there yet; a key that left the data may come
    back."""
    known: set[str] = set()

    def update() -> None:
        current = dict(make())
        known.intersection_update(current)
        new = [factory() for key, factory in current.items() if key not in known]
        known.update(current)
        if new:
            add(new)

    update()
    entry.async_on_unload(coordinator.async_add_listener(update))


def devices_of(coordinator: MassimoCoordinator) -> list[tuple[str, dict[str, Any]]]:
    """Every device the server lists, by its serial."""
    return [(dev["serial"], dev) for cube in coordinator.data.cubes.values() for _, dev in cube.devices()]
