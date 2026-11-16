"""An entry's title: its name, and whose key it signs in with where that
is a person's; a title renamed by hand is kept."""

from __future__ import annotations

from typing import Any

from homeassistant.const import CONF_API_KEY, CONF_NAME, CONF_URL, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.massimo.const import CONF_AUTO_TITLE, CONF_REGISTERED, DOMAIN

from .conftest import Server, http
from .test_entities import _entity


async def _set_up(hass: HomeAssistant, server: Server, key: str, title: str, **data: Any) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=title,
        unique_id=server.node_id or server.url,
        data={CONF_URL: server.url, CONF_API_KEY: key, CONF_VERIFY_SSL: True} | data,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _unload(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """The entry removed, so that the next one may take its server."""
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()


async def test_an_old_title_names_the_key(hass: HomeAssistant, massimo_server: Server, socket_enabled: None) -> None:
    """An entry made before names were kept, with a person's key: its title
    becomes "Massimo (key of <user>)", its name "Massimo"."""
    entry = await _set_up(hass, massimo_server, massimo_server.typed_key, "Massimo (hand)")
    assert entry.title == "Massimo (key of hand)"
    assert entry.data[CONF_NAME] == "Massimo" and entry.data[CONF_AUTO_TITLE] == entry.title
    assert entry.data[CONF_REGISTERED] is False
    await _unload(hass, entry)


async def test_a_registered_entry_names_nobody(
    hass: HomeAssistant, massimo_server: Server, socket_enabled: None
) -> None:
    """A registered entry's title is its name alone: the key's user is the
    integration's own, which says nothing."""
    entry = await _set_up(hass, massimo_server, massimo_server.key, "Massimo (martin)")
    assert entry.title == "Massimo" and entry.data[CONF_REGISTERED] is True
    await _unload(hass, entry)
    entry = await _set_up(
        hass,
        massimo_server,
        massimo_server.key,
        "Massimo Keller (key of hand)",
        **{CONF_NAME: "Massimo Keller", CONF_AUTO_TITLE: "Massimo Keller (key of hand)"},
    )
    assert entry.title == "Massimo Keller"
    await _unload(hass, entry)


async def test_a_title_renamed_by_hand_is_kept(
    hass: HomeAssistant, massimo_server: Server, socket_enabled: None
) -> None:
    """A title that is not the one last set automatically was renamed by
    hand, and stays."""
    entry = await _set_up(
        hass,
        massimo_server,
        massimo_server.typed_key,
        "Heizung",
        **{CONF_NAME: "Massimo Keller", CONF_AUTO_TITLE: "Massimo Keller (key of hand)"},
    )
    assert entry.title == "Heizung"
    await _unload(hass, entry)
    entry = await _set_up(hass, massimo_server, massimo_server.typed_key, "Heizung")
    assert entry.title == "Heizung" and CONF_AUTO_TITLE not in entry.data
    await _unload(hass, entry)


async def test_the_title_in_home_assistants_language(
    hass: HomeAssistant, massimo_server: Server, socket_enabled: None
) -> None:
    """Whose key it is, in Home Assistant's language."""
    hass.config.language = "de"
    entry = await _set_up(hass, massimo_server, massimo_server.typed_key, "Massimo")
    assert entry.title == "Massimo (Schlüssel von hand)"
    await _unload(hass, entry)


async def test_the_title_names_the_user_by_display_name(
    hass: HomeAssistant, massimo_server: Server, socket_enabled: None
) -> None:
    """Whose key it is, by the user's display name; by its login name where
    it has none, as an integration's users are named by a uuid."""
    user = f"{massimo_server.url}/api/v1/users/hand"
    http("PUT", user, massimo_server.owner, {"display_name": "Hand Werker"})
    try:
        entry = await _set_up(hass, massimo_server, massimo_server.typed_key, "Massimo")
        assert entry.title == "Massimo (key of Hand Werker)"
        state = hass.states.get(_entity(hass, "sensor", f"{massimo_server.node_id or massimo_server.url}_signed_in_as"))
        assert state is not None and state.attributes["user"] == "Hand Werker"
        await _unload(hass, entry)
    finally:
        http("PUT", user, massimo_server.owner, {"display_name": ""})
    entry = await _set_up(hass, massimo_server, massimo_server.typed_key, "Massimo")
    assert entry.title == "Massimo (key of hand)"
    await _unload(hass, entry)
