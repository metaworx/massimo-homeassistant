"""The week programme card's side of the integration.

The card hosts Massimo's own editor, the element <massimo-week-program>
(Massimo's internal/server/ui/week-program.js), with Massimo's texts. Both
are Massimo's, under its AGPL, and stay there: the view below passes them
on from the Massimo server an entry is connected to, to a browser signed in
to Home Assistant, kept per Massimo version, so that the editor always
matches the server's API.

The card itself, frontend/massimo-week-program-card.js, is the
integration's: it is served on a static path and loaded on every page of
the frontend, so that nothing is installed by hand.
"""

from __future__ import annotations

import re
from pathlib import Path

from aiohttp import web
from homeassistant.components.http import KEY_HASS, HomeAssistantView, StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.loader import async_get_integration

from .api import MassimoError, MassimoNotFoundError
from .const import DOMAIN, LOGGER
from .coordinator import MassimoCoordinator

CARD_FILE = "massimo-week-program-card.js"
STATIC_URL = "/massimo_static"
# The files the view passes on: the element and its texts.
UI_FILES = re.compile(r"^(week-program\.js|i18n/[a-z]{2}\.json)$")

DATA_FRONTEND = f"{DOMAIN}_frontend"


def _coordinator(hass: HomeAssistant, entity_id: str | None) -> MassimoCoordinator | None:
    """The coordinator of the entry an entity belongs to, else of the first
    loaded entry."""
    if entity_id and (entry_id := getattr(er.async_get(hass).async_get(entity_id), "config_entry_id", None)):
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry and entry.domain == DOMAIN and getattr(entry, "runtime_data", None):
            return entry.runtime_data
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        return entry.runtime_data
    return None


class MassimoUiView(HomeAssistantView):
    """Massimo's week programme element and texts, for a signed-in
    browser."""

    url = "/api/massimo/ui/{name:.+}"
    name = "api:massimo:ui"
    requires_auth = True

    def __init__(self) -> None:
        """Keep each file per server and Massimo version."""
        self._cache: dict[tuple[str, str, str], tuple[bytes, str]] = {}

    async def get(self, request: web.Request, name: str) -> web.Response:
        """One of the files, from the Massimo of the entity named, if any."""
        if not UI_FILES.match(name):
            return web.Response(status=404, text="not a file of the week programme editor")
        coordinator = _coordinator(request.app[KEY_HASS], request.query.get("entity_id"))
        if coordinator is None:
            return web.Response(status=404, text="no Massimo server is set up")
        key = (coordinator.client.url, str(coordinator.data.server.get("version", "")), name)
        if key not in self._cache:
            try:
                self._cache[key] = await coordinator.client.ui_file(name)
            except MassimoNotFoundError:
                return web.Response(status=404, text=f"this Massimo has no {name}")
            except MassimoError as err:
                LOGGER.debug("%s could not be read: %s", name, err)
                return web.Response(status=502, text=str(err))
        body, content_type = self._cache[key]
        return web.Response(body=body, content_type=content_type, headers={"Cache-Control": "no-cache"})


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Register the view, serve the card, and load it on every page where
    the frontend runs; once, whatever the number of entries."""
    if hass.data.get(DATA_FRONTEND):
        return
    hass.data[DATA_FRONTEND] = True
    hass.http.register_view(MassimoUiView())
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, str(Path(__file__).parent / "frontend"), cache_headers=False)]
    )
    if "frontend" in hass.config.components:
        from homeassistant.components.frontend import add_extra_js_url  # noqa: PLC0415

        version = (await async_get_integration(hass, DOMAIN)).version
        add_extra_js_url(hass, f"{STATIC_URL}/{CARD_FILE}?v={version}")
