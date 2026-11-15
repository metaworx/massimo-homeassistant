"""Diagnostics of an entry, for a report of a problem: the entry without its
key, what the server says of itself and of the key, and the Cubes counted,
without their serials."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant

from .coordinator import MassimoConfigEntry

TO_REDACT = {CONF_API_KEY}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: MassimoConfigEntry) -> dict[str, Any]:
    """The entry's diagnostics."""
    coordinator = entry.runtime_data
    cubes = coordinator.data.cubes.values()
    return {
        "entry": {"title": entry.title, "data": async_redact_data(dict(entry.data), TO_REDACT)},
        "server": coordinator.data.server,
        "me": coordinator.me,
        "connected": coordinator.last_update_success,
        "last_contact": coordinator.last_contact.isoformat() if coordinator.last_contact else None,
        "cubes": [
            {
                "connected": bool(cube.info.get("connected")),
                "firmware": cube.info.get("firmware"),
                "rooms": len(cube.rooms),
                "devices": len(cube.devices()),
            }
            for cube in cubes
        ],
    }
