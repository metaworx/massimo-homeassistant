"""The entities' common ground: the devices they belong to, and when they
are available.

A Cube is a hub, registered when the entry is set up, and each of its
devices a device of its own beneath it, found by its serial, which stays the
same if it is paired to another Cube. A device names its Cube by the Cube's
device id (``via_device_id``): the identifier form, ``via_device``, is
deprecated, to be removed in Home Assistant 2027.8. A device's area is
suggested by its room's name; Home Assistant matches or creates the area
once, and the areas stay the owner's.

A room is a device too, backed by its virtual wall thermostat (Massimo's
VWT): identified by its Cube and its room_uid, it stays the room's for the
room's life, whatever thermostats come and go in it.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from typing import Any, override

from homeassistant.auth.permissions.const import POLICY_READ
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import HomeAssistantError, Unauthorized, UnknownUser
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity, EntityDescription
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import MassimoDiscardedError, MassimoError
from .const import DOMAIN, MANUFACTURER, MODELS
from .coordinator import CubeData, MassimoConfigEntry, MassimoCoordinator, room_key


def cube_device(coordinator: MassimoCoordinator, serial: str) -> dict[str, Any]:
    """A Cube's device, as the device registry takes it."""
    info = coordinator.data.cubes[serial].info
    return {
        "identifiers": {(DOMAIN, serial)},
        "name": info.get("name") or serial,
        "manufacturer": MANUFACTURER,
        "model": "MAX! Cube",
        "serial_number": serial,
        "sw_version": info.get("firmware"),
        "configuration_url": coordinator.client.url,
    }


async def read_access(hass: HomeAssistant, context: Context | None) -> Callable[[str], bool]:
    """Whether a call's user may read an entity: a call without a user is
    the system's, and an administrator may read everything."""
    if context is None or not context.user_id:
        return lambda _: True
    user = await hass.auth.async_get_user(context.user_id)
    if user is None:
        raise UnknownUser(context=context, user_id=context.user_id, permission=POLICY_READ)
    if user.is_admin:
        return lambda _: True
    return lambda entity_id: user.permissions.check_entity(entity_id, POLICY_READ)


async def check_read(hass: HomeAssistant, context: Context | None, entity_ids: Iterable[str]) -> None:
    """Refuse a call whose user may not read each entity named, as Home
    Assistant refuses an entity service to a user who may not control one."""
    may_read = await read_access(hass, context)
    for entity_id in entity_ids:
        if not may_read(entity_id):
            raise Unauthorized(context=context, entity_id=entity_id, permission=POLICY_READ)


def register_cubes(coordinator: MassimoCoordinator) -> None:
    """Register the Cubes' devices, so that their devices can name them."""
    registry = dr.async_get(coordinator.hass)
    for serial in coordinator.data.cubes:
        registry.async_get_or_create(
            config_entry_id=coordinator.config_entry.entry_id, **cube_device(coordinator, serial)
        )


class MassimoEntity(CoordinatorEntity[MassimoCoordinator]):
    """An entity of a Massimo server."""

    _attr_has_entity_name = True

    @staticmethod
    async def write(request: Awaitable[Any]) -> Any:
        """Send a write, a refusal raised as a translated error. The entity
        shows what the devices report, so the change shows once they have
        taken it."""
        try:
            return await request
        except MassimoDiscardedError as err:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="discarded") from err
        except MassimoError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="write_failed", translation_placeholders={"error": str(err)}
            ) from err


class CubeEntity(MassimoEntity):
    """An entity of a Cube, available while the Cube is connected."""

    def __init__(self, coordinator: MassimoCoordinator, serial: str, description: EntityDescription) -> None:
        """Initialise the entity of a Cube's serial and a description."""
        super().__init__(coordinator)
        self.cube_serial = serial
        self.entity_description = description
        self._attr_unique_id = f"{serial}_{description.key}"
        self._attr_device_info = DeviceInfo(**cube_device(coordinator, serial))

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
        cube = dr.async_get(coordinator.hass).async_get_device_by_identifier(
            (DOMAIN, cube_serial), coordinator.config_entry.entry_id
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            name=dev.get("name") or serial,
            manufacturer=MANUFACTURER,
            model=MODELS.get(dev.get("type", ""), dev.get("type")),
            serial_number=serial,
            via_device_id=cube.id if cube else None,
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


class RoomEntity(MassimoEntity):
    """An entity of a room, on its virtual wall thermostat; available while
    the room's thermostats report through a connected Cube."""

    def __init__(
        self, coordinator: MassimoCoordinator, cube_serial: str, room_uid: str, description: EntityDescription
    ) -> None:
        """Initialise the entity of a room, by its Cube and room_uid, and a
        description."""
        super().__init__(coordinator)
        self.cube_serial = cube_serial
        self.room_uid = room_uid
        self.entity_description = description
        self._attr_unique_id = f"{cube_serial}_{room_uid}_{description.key}"
        found = coordinator.data.find_room(cube_serial, room_uid)
        assert found is not None, "an entity is made for a room the data lists"
        room, vwt = found
        cube = dr.async_get(coordinator.hass).async_get_device_by_identifier(
            (DOMAIN, cube_serial), coordinator.config_entry.entry_id
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, room_key(cube_serial, room))},
            name=room.get("name") or vwt.get("serial"),
            manufacturer="Massimo",
            model="Room",
            serial_number=vwt.get("serial"),
            via_device_id=cube.id if cube else None,
            suggested_area=room.get("name") or None,
        )

    @property
    def found(self) -> tuple[dict[str, Any], dict[str, Any]] | None:
        """The room and its virtual wall thermostat, while the server lists
        them."""
        return self.coordinator.data.find_room(self.cube_serial, self.room_uid)

    @property
    def vwt(self) -> dict[str, Any]:
        """The room's virtual wall thermostat; empty once the room is gone."""
        found = self.found
        return found[1] if found else {}

    @property
    def state_data(self) -> dict[str, Any]:
        """The room's state, as Massimo computes it."""
        return self.vwt.get("state") or {}

    @property
    def details(self) -> dict[str, Any]:
        """The room's details: its configuration, settings and tag."""
        cube = self.coordinator.data.cubes.get(self.cube_serial)
        return cube.details.get(self.room_uid, {}) if cube else {}

    @property
    def config(self) -> dict[str, Any]:
        """The room's configuration: its temperatures and limits."""
        return self.details.get("wall_thermostat") or self.details.get("thermostat") or {}

    @property
    @override
    def available(self) -> bool:
        """Whether the stream is up, the Cube connected, and the room's
        thermostats have reported and are not all stale."""
        cube = self.coordinator.data.cubes.get(self.cube_serial)
        vwt = self.vwt
        return (
            super().available
            and cube is not None
            and bool(cube.info.get("connected"))
            and bool(vwt.get("reported"))
            and not vwt.get("stale")
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
    """Every real device the server lists, by its serial."""
    return [(dev["serial"], dev) for cube in coordinator.data.cubes.values() for _, dev in cube.devices()]


def rooms_of(coordinator: MassimoCoordinator) -> list[tuple[str, dict[str, Any]]]:
    """Every room with a virtual wall thermostat, with its Cube's serial."""
    return [(serial, room) for serial, cube in coordinator.data.cubes.items() for room, _ in cube.virtual_rooms()]
