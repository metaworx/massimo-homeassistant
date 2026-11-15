"""The server's own device: its version and address, the Cubes beneath
it, and the connection's diagnostics."""

from __future__ import annotations

import json

from homeassistant.const import CONF_API_KEY, CONF_URL, CONF_VERIFY_SSL, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.massimo.api import MassimoConnectionError
from custom_components.massimo.const import DOMAIN
from custom_components.massimo.diagnostics import async_get_config_entry_diagnostics
from custom_components.massimo.entity import massimo_version

from .conftest import Server
from .test_entities import _entity, _setup, _unload


def _server_id(server: Server) -> str:
    return server.node_id or server.url


async def test_the_server_is_a_device(hass: HomeAssistant, massimo_server: Server, socket_enabled: None) -> None:
    """The server's device carries Massimo's version and its address; each
    Cube is beneath it."""
    entry = await _setup(hass, massimo_server)
    registry = dr.async_get(hass)
    server = registry.async_get_device_by_identifier((DOMAIN, _server_id(massimo_server)), entry.entry_id)
    assert server is not None and server.model == "Server" and server.name == "Massimo"
    assert server.configuration_url == massimo_server.url and server.sw_version
    cube_devices = [d for d in dr.async_entries_for_config_entry(registry, entry.entry_id) if d.model == "MAX! Cube"]
    assert len(cube_devices) == len(entry.runtime_data.data.cubes) > 0
    assert all(d.via_device_id == server.id for d in cube_devices)
    await _unload(hass, entry)


async def test_the_connection_s_entities(hass: HomeAssistant, massimo_server: Server, socket_enabled: None) -> None:
    """Connected follows the reads and streams, and stays available when
    the connection is lost; Signed in as says registered; Last contact is
    off by default."""
    entry = await _setup(hass, massimo_server)
    node = _server_id(massimo_server)
    connected = _entity(hass, "binary_sensor", f"{node}_connected")
    signed_in = _entity(hass, "sensor", f"{node}_signed_in_as")
    last_contact = er.async_get(hass).async_get(_entity(hass, "sensor", f"{node}_last_contact"))
    assert last_contact is not None and last_contact.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert hass.states.get(connected).state == STATE_ON  # type: ignore[union-attr]
    assert hass.states.get(signed_in).state == "registered"  # type: ignore[union-attr]
    coordinator = entry.runtime_data
    coordinator.async_set_update_error(MassimoConnectionError("lost"))
    await hass.async_block_till_done()
    assert hass.states.get(connected).state == STATE_OFF  # type: ignore[union-attr]
    coordinator.async_set_updated_data(coordinator.data)
    await hass.async_block_till_done()
    assert hass.states.get(connected).state == STATE_ON  # type: ignore[union-attr]
    await _unload(hass, entry)


async def test_a_person_s_key_is_signed_in_as(
    hass: HomeAssistant, massimo_server: Server, socket_enabled: None
) -> None:
    """With a person's key, Signed in as names the person."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=_server_id(massimo_server),
        data={CONF_URL: massimo_server.url, CONF_API_KEY: massimo_server.typed_key, CONF_VERIFY_SSL: True},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    state = hass.states.get(_entity(hass, "sensor", f"{_server_id(massimo_server)}_signed_in_as"))
    assert state is not None and state.state == "user_key" and state.attributes["user"] == "hand"
    await _unload(hass, entry)


async def test_diagnostics_carry_no_key(hass: HomeAssistant, massimo_server: Server, socket_enabled: None) -> None:
    """The diagnostics hold the entry without its key, and the Cubes without
    their serials."""
    entry = await _setup(hass, massimo_server)
    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    text = json.dumps(diagnostics)
    assert massimo_server.key not in text
    assert diagnostics["entry"]["data"][CONF_API_KEY] == "**REDACTED**"
    assert diagnostics["connected"] is True and diagnostics["cubes"]
    for cube in diagnostics["cubes"]:
        assert set(cube) == {"connected", "firmware", "rooms", "devices"}
    await _unload(hass, entry)


def test_massimo_s_version() -> None:
    """The version from the health's text."""
    assert massimo_version({"version": "massimo v0.15.0-alpha.1-441-g6ece4f25 (go1.26.11, linux/amd64)"}) == (
        "0.15.0-alpha.1-441-g6ece4f25"
    )
    assert massimo_version({"version": "1.2.3"}) == "1.2.3"
    assert massimo_version({}) is None
