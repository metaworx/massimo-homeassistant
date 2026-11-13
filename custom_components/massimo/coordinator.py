"""The coordinator: the server's Cubes and rooms, kept by its event stream.

It reads the server once, then follows each Cube's event stream: a state
event updates its device in place; an event that changes rooms, names or
devices, or says that events were lost (resync), reads the Cube's rooms
again. A broken stream is opened again with the last id read, so that the
server sends what came meanwhile instead of the whole state; while it is
down the data counts as not up to date, and once it is open again as up to
date, whether or not anything came meanwhile.

After every read of the rooms, a device the server no longer lists leaves
the device registry, and its entities with it.

What the server supports is its health's ``features``, each name with a
version "MAJOR.MINOR" (Massimo's docs/api-v1.md, GET /healthz). With
``vwt``, every room has a virtual wall thermostat, read with the rooms
(``?devices=all``), and its details beside it: the room's configuration,
its settings and its programme's tag (``GET …/devices/{vwt}``), read again
with the rooms after a configuration change. Where a room's tag differs from
the one read before, its programme changed, and the time it was seen is
kept for the room's climate.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, override

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import DEVICES_ALL, DEVICES_REAL, MassimoAuthError, MassimoClient, MassimoError, StreamEvent
from .const import DOMAIN, LOGGER, RECONNECT_FIRST, RECONNECT_LAST, REFRESH_KINDS, THERMOSTATS

type MassimoConfigEntry = ConfigEntry[MassimoCoordinator]


def has_feature(server: dict[str, Any], name: str, minor: int = 0) -> bool:
    """Whether the server's health lists a feature at major 1 and at least
    the minor given."""
    version = (server.get("features") or {}).get(name)
    if not isinstance(version, str):
        return False
    major, _, rest = version.partition(".")
    return major == "1" and rest.isdigit() and int(rest) >= minor


def room_key(cube_serial: str, room: dict[str, Any]) -> str:
    """The identifier of a room's device: its Cube and its room_uid, which
    Massimo never gives to another room."""
    return f"{cube_serial}:{room['room_uid']}"


def virtual_of(room: dict[str, Any]) -> dict[str, Any] | None:
    """A room's virtual wall thermostat, where the server has them."""
    return next((dev for dev in room.get("devices") or [] if dev.get("virtual")), None)


def has_thermostat(room: dict[str, Any]) -> bool:
    """Whether a room has a real thermostat, so something to control."""
    return any(not dev.get("virtual") and dev.get("type") in THERMOSTATS for dev in room.get("devices") or [])


@dataclass
class CubeData:
    """A Cube as the API describes it, its rooms with their devices, and
    each room's details by its room_uid."""

    info: dict[str, Any]
    rooms: list[dict[str, Any]] = field(default_factory=list)
    details: dict[str, dict[str, Any]] = field(default_factory=dict)

    def device(self, rf_address: str) -> dict[str, Any] | None:
        """The device of a radio address, in whichever room it is."""
        for room in self.rooms:
            for dev in room.get("devices") or []:
                if dev.get("rf_address") == rf_address:
                    return dev
        return None

    def devices(self) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        """Every real device with a serial, with its room; the virtual wall
        thermostats are the rooms'."""
        return [
            (room, dev)
            for room in self.rooms
            for dev in room.get("devices") or []
            if dev.get("serial") and not dev.get("virtual")
        ]

    def virtual_rooms(self) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        """Every room with its virtual wall thermostat."""
        return [(room, vwt) for room in self.rooms if room.get("room_uid") and (vwt := virtual_of(room))]


@dataclass
class MassimoData:
    """The server's health and its Cubes, by serial."""

    server: dict[str, Any]
    cubes: dict[str, CubeData]

    def find(self, serial: str) -> tuple[str, dict[str, Any], dict[str, Any]] | None:
        """A device by its serial, which stays the same on another Cube:
        its Cube's serial, its room and its data."""
        for cube_serial, cube in self.cubes.items():
            for room, dev in cube.devices():
                if dev["serial"] == serial:
                    return cube_serial, room, dev
        return None

    def find_room(self, cube_serial: str, room_uid: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
        """A room and its virtual wall thermostat, while the server lists
        them."""
        cube = self.cubes.get(cube_serial)
        if cube is None:
            return None
        return next(((room, vwt) for room, vwt in cube.virtual_rooms() if room["room_uid"] == room_uid), None)

    def serials(self) -> set[str]:
        """The identifiers of the Cubes, their real devices and their rooms."""
        out = set(self.cubes)
        for serial, cube in self.cubes.items():
            out |= {dev["serial"] for _, dev in cube.devices()}
            out |= {room_key(serial, room) for room, _ in cube.virtual_rooms()}
        return out

    def feature(self, name: str, minor: int = 0) -> bool:
        """Whether the server lists a feature (has_feature)."""
        return has_feature(self.server, name, minor)


class MassimoCoordinator(DataUpdateCoordinator[MassimoData]):
    """Reads a Massimo server and follows its Cubes' event streams."""

    config_entry: MassimoConfigEntry

    def __init__(self, hass: HomeAssistant, entry: MassimoConfigEntry, client: MassimoClient) -> None:
        """Initialise the coordinator; it polls nothing, the streams push."""
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{client.url}",
            update_interval=None,
        )
        self.client = client
        # The last event id read per Cube, where its stream resumes.
        self.last_event_id: dict[str, str] = {}
        self._refreshing: dict[str, asyncio.Task[None]] = {}
        self._warned_vwt = False
        # When a room's programme was last seen to change, by room_key.
        self.program_changed: dict[str, datetime] = {}

    @override
    async def _async_update_data(self) -> MassimoData:
        """Read the server, its Cubes and their rooms."""
        try:
            server = await self.client.health()
            self._configure(server)
            cubes = {}
            for info in await self.client.cubes():
                serial = info["serial"]
                cubes[serial] = CubeData(info, *await self._read_rooms(serial))
        except MassimoAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except MassimoError as err:
            raise UpdateFailed(str(err)) from err
        data = MassimoData(server, cubes)
        self._prune(data)
        return data

    def _configure(self, server: dict[str, Any]) -> None:
        """Set the client to what the server supports."""
        self.client.retry_writes = has_feature(server, "idempotency")
        if has_feature(server, "vwt"):
            self.client.devices = DEVICES_ALL
            return
        self.client.devices = DEVICES_REAL
        if not self._warned_vwt:
            self._warned_vwt = True
            LOGGER.warning(
                "%s has no virtual wall thermostats (the feature vwt): its rooms need a newer Massimo",
                self.client.url,
            )

    async def _read_rooms(self, serial: str) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
        """A Cube's rooms, and each room's details from its virtual wall
        thermostat; from the server's copy, without radio."""
        rooms = await self.client.rooms(serial)
        details = {}
        for room in rooms:
            if room.get("room_uid") and (vwt := virtual_of(room)):
                details[room["room_uid"]] = await self.client.device(serial, vwt["rf_address"])
        return rooms, details

    @callback
    def _prune(self, data: MassimoData) -> None:
        """Take the devices the server no longer lists out of the registry."""
        registry = dr.async_get(self.hass)
        serials = data.serials()
        for device in dr.async_entries_for_config_entry(registry, self.config_entry.entry_id):
            ids = {ident for domain, ident in device.identifiers if domain == DOMAIN}
            if ids and not ids & serials:
                LOGGER.debug("%s is gone from the server", device.name)
                registry.async_remove_device(device.id)

    @callback
    def start_streams(self) -> None:
        """Follow every Cube's event stream, for as long as the entry is
        loaded."""
        for serial in self.data.cubes:
            self.config_entry.async_create_background_task(
                self.hass, self._follow(serial), f"{DOMAIN} events of {serial}"
            )

    async def _follow(self, serial: str) -> None:
        """Read a Cube's events, reconnecting with the last id read."""
        wait = RECONNECT_FIRST.total_seconds()
        while True:
            try:
                async for event in self.client.events(serial, self.last_event_id.get(serial)):
                    # A stream that opens and breaks at once keeps its wait.
                    if event.kind != "open":
                        wait = RECONNECT_FIRST.total_seconds()
                    if event.id:
                        self.last_event_id[serial] = event.id
                    self._apply(serial, event)
                LOGGER.debug("the event stream of %s ended", serial)
            except MassimoAuthError as err:
                self.async_set_update_error(err)
                self.config_entry.async_start_reauth(self.hass)
                return
            except MassimoError as err:
                LOGGER.debug("the event stream of %s broke: %s", serial, err)
                self.async_set_update_error(err)
            await asyncio.sleep(wait)
            wait = min(wait * 2, RECONNECT_LAST.total_seconds())

    @callback
    def _apply(self, serial: str, event: StreamEvent) -> None:
        """Take an event into the data."""
        if event.kind == "open":
            if not self.last_update_success:
                self.async_set_updated_data(self.data)
            return
        cube = self.data.cubes.get(serial)
        if cube is None:
            return
        if event.kind == "state":
            state = event.data.get("state") or {}
            dev = cube.device(state.get("rf_address") or event.data.get("device", ""))
            if dev is None:
                self._refresh(serial)
                return
            dev.clear()
            dev.update(state)
            self.async_set_updated_data(self.data)
        elif event.kind in ("connected", "disconnected"):
            cube.info["connected"] = event.kind == "connected"
            if event.kind == "connected":
                self._refresh(serial)
            else:
                self.async_set_updated_data(self.data)
        elif event.kind in REFRESH_KINDS:
            self._refresh(serial)

    @callback
    def _note_programs(self, serial: str, before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]]) -> None:
        """Note the rooms whose programme's tag changed between two reads."""
        now = dt_util.utcnow()
        for uid, details in after.items():
            old, new = (before.get(uid) or {}).get("etag"), details.get("etag")
            if old and new and old != new:
                self.program_changed[f"{serial}:{uid}"] = now

    @callback
    def refresh_rooms(self, serial: str) -> None:
        """Read a Cube's rooms again soon, as after a write of the
        integration's own that changes them."""
        self._refresh(serial)

    @callback
    def _refresh(self, serial: str) -> None:
        """Read a Cube's rooms again, once for a burst of events."""
        if serial in self._refreshing:
            return

        async def read() -> None:
            try:
                rooms, details = await self._read_rooms(serial)
            except MassimoError as err:
                LOGGER.debug("the rooms of %s could not be read: %s", serial, err)
                return
            finally:
                self._refreshing.pop(serial, None)
            if serial in self.data.cubes:
                self._note_programs(serial, self.data.cubes[serial].details, details)
                self.data.cubes[serial].rooms = rooms
                self.data.cubes[serial].details = details
                self._prune(self.data)
                self.async_set_updated_data(self.data)

        self._refreshing[serial] = self.config_entry.async_create_background_task(
            self.hass, read(), f"{DOMAIN} rooms of {serial}"
        )
