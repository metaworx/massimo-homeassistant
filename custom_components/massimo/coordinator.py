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
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, override

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MassimoAuthError, MassimoClient, MassimoError, StreamEvent
from .const import DOMAIN, LOGGER, RECONNECT_FIRST, RECONNECT_LAST, REFRESH_KINDS

type MassimoConfigEntry = ConfigEntry[MassimoCoordinator]


@dataclass
class CubeData:
    """A Cube as the API describes it, and its rooms with their devices."""

    info: dict[str, Any]
    rooms: list[dict[str, Any]] = field(default_factory=list)

    def device(self, rf_address: str) -> dict[str, Any] | None:
        """The device of a radio address, in whichever room it is."""
        for room in self.rooms:
            for dev in room.get("devices") or []:
                if dev.get("rf_address") == rf_address:
                    return dev
        return None

    def devices(self) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        """Every device with a serial, with its room."""
        return [(room, dev) for room in self.rooms for dev in room.get("devices") or [] if dev.get("serial")]


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

    def serials(self) -> set[str]:
        """The serials of the Cubes and of their devices."""
        return set(self.cubes) | {dev["serial"] for cube in self.cubes.values() for _, dev in cube.devices()}


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

    @override
    async def _async_update_data(self) -> MassimoData:
        """Read the server, its Cubes and their rooms."""
        try:
            server = await self.client.health()
            cubes = {}
            for info in await self.client.cubes():
                serial = info["serial"]
                cubes[serial] = CubeData(info, await self.client.rooms(serial))
        except MassimoAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except MassimoError as err:
            raise UpdateFailed(str(err)) from err
        data = MassimoData(server, cubes)
        self._prune(data)
        return data

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
    def _refresh(self, serial: str) -> None:
        """Read a Cube's rooms again, once for a burst of events."""
        if serial in self._refreshing:
            return

        async def read() -> None:
            try:
                rooms = await self.client.rooms(serial)
            except MassimoError as err:
                LOGGER.debug("the rooms of %s could not be read: %s", serial, err)
                return
            finally:
                self._refreshing.pop(serial, None)
            if serial in self.data.cubes:
                self.data.cubes[serial].rooms = rooms
                self._prune(self.data)
                self.async_set_updated_data(self.data)

        self._refreshing[serial] = self.config_entry.async_create_background_task(
            self.hass, read(), f"{DOMAIN} rooms of {serial}"
        )
