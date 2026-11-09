"""Setting up an entry: the coordinator reads the server and follows the
event stream."""

from __future__ import annotations

import asyncio
import secrets

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_API_KEY, CONF_URL, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.massimo.api import StreamEvent
from custom_components.massimo.const import DOMAIN

from .conftest import Server, http, stream_has_ids, thermostat_room


def _entry(hass: HomeAssistant, server: Server, key: str) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=server.node_id or server.url,
        data={CONF_URL: server.url, CONF_API_KEY: key, CONF_VERIFY_SSL: True},
    )
    entry.add_to_hass(hass)
    return entry


async def test_setup_follows_the_stream(hass: HomeAssistant, massimo_server: Server, socket_enabled: None) -> None:
    """The entry loads with the Cube and its rooms; a setpoint changed on
    the server arrives through the stream; unloading ends the stream."""
    entry = _entry(hass, massimo_server, massimo_server.key)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    coordinator = entry.runtime_data
    cube = coordinator.data.cubes[massimo_server.serial]
    assert cube.info["name"] == "Fake Cube" and cube.rooms

    # The fake Cube changes no state on a setpoint; a rename is a metadata
    # write, after which the coordinator reads the rooms again.
    room = thermostat_room(massimo_server)
    name = f"Room {secrets.token_hex(3)}"
    await hass.async_add_executor_job(
        http,
        "PUT",
        f"{massimo_server.url}/api/v1/cubes/{massimo_server.serial}/rooms/{room['id']}",
        massimo_server.owner,
        {"name": name},
    )

    def room_name() -> str:
        for r in coordinator.data.cubes[massimo_server.serial].rooms:
            if r["id"] == room["id"]:
                return r.get("name", "")
        return ""

    for _ in range(100):
        if room_name() == name:
            break
        await asyncio.sleep(0.1)
    assert room_name() == name, "the stream's metadata event read the rooms again"
    if await hass.async_add_executor_job(stream_has_ids, massimo_server):
        assert coordinator.last_event_id.get(massimo_server.serial), "the coordinator noted the last id"
    assert coordinator.last_update_success

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_a_wrong_key_asks_for_another(hass: HomeAssistant, massimo_server: Server, socket_enabled: None) -> None:
    """A key the server refuses fails the setup and starts re-authentication."""
    entry = _entry(hass, massimo_server, "wrong")
    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert any(f["context"]["source"] == "reauth" for f in flows)


async def test_a_state_event_updates_its_device(
    hass: HomeAssistant, massimo_server: Server, socket_enabled: None
) -> None:
    """A state event replaces its device's data in its room."""
    entry = _entry(hass, massimo_server, massimo_server.key)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coordinator = entry.runtime_data
    cube = coordinator.data.cubes[massimo_server.serial]
    dev = next(d for r in cube.rooms for d in r.get("devices") or [] if "thermostat" in (d.get("type") or ""))
    changed = dict(dev, state=dict(dev.get("state") or {}, setpoint=29.5))
    updates = []
    remove = coordinator.async_add_listener(lambda: updates.append(1))
    coordinator._apply(
        massimo_server.serial, StreamEvent("state", {"device": dev["rf_address"], "state": changed}, "x-1")
    )
    assert cube.device(dev["rf_address"])["state"]["setpoint"] == 29.5
    assert updates, "the listeners heard of it"
    remove()
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
