"""The week programme card's side of the integration: Massimo's element
and texts passed on to a signed-in browser, and the card served and
loaded."""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.massimo.frontend import CARD_FILE, STATIC_URL

from .conftest import Server
from .test_entities import _setup, _unload
from .test_rooms import SCHLAFEN, _climate


async def test_massimo_files_for_a_signed_in_browser(
    hass: HomeAssistant, massimo_server: Server, socket_enabled: None, hass_client: ClientSessionGenerator
) -> None:
    """The view passes on Massimo's element and its texts, from the Massimo
    of the room named; it serves nothing else."""
    entry = await _setup(hass, massimo_server)
    client = await hass_client()
    room = _climate(hass, massimo_server, SCHLAFEN)
    resp = await client.get(f"/api/massimo/ui/week-program.js?entity_id={room}")
    assert resp.status == 200 and "javascript" in resp.content_type
    assert 'customElements.define("massimo-week-program"' in await resp.text()
    resp = await client.get("/api/massimo/ui/i18n/de.json")
    assert resp.status == 200
    assert "prog.copy" in await resp.json()
    for name in ("app.js", "i18n/../app.js", "i18n/xx.json"):
        resp = await client.get(f"/api/massimo/ui/{name}")
        assert resp.status == 404, name
    await _unload(hass, entry)


async def test_massimo_files_need_a_sign_in(
    hass: HomeAssistant,
    massimo_server: Server,
    socket_enabled: None,
    hass_client_no_auth: ClientSessionGenerator,
) -> None:
    """Without Home Assistant's sign-in, the view passes nothing on."""
    entry = await _setup(hass, massimo_server)
    client = await hass_client_no_auth()
    resp = await client.get("/api/massimo/ui/week-program.js")
    assert resp.status == 401
    await _unload(hass, entry)


async def test_the_card_is_served(
    hass: HomeAssistant, massimo_server: Server, socket_enabled: None, hass_client_no_auth: ClientSessionGenerator
) -> None:
    """The card's script is served as the frontend loads it, and defines the
    card."""
    entry = await _setup(hass, massimo_server)
    client = await hass_client_no_auth()
    resp = await client.get(f"{STATIC_URL}/{CARD_FILE}")
    assert resp.status == 200
    script = await resp.text()
    assert "customElements.define(CARD" in script and '"massimo-week-program-card"' in script
    assert "week-program.js" in script and "AGPL" in script, "the element is fetched, not carried"
    await _unload(hass, entry)


async def test_the_card_is_loaded_on_every_page(
    hass: HomeAssistant, massimo_server: Server, socket_enabled: None
) -> None:
    """Where the frontend runs, the card's script is added to every page,
    once, with the integration's version."""
    from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL  # noqa: PLC0415

    urls = MagicMock()
    hass.data[DATA_EXTRA_MODULE_URL] = urls
    hass.config.components.add("frontend")
    entry = await _setup(hass, massimo_server)
    urls.add.assert_called_once()
    assert urls.add.call_args.args[0].startswith(f"{STATIC_URL}/{CARD_FILE}?v=")
    await _unload(hass, entry)
