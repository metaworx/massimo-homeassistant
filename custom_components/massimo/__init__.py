"""The Massimo integration: a Massimo server's MAX! Cubes in Home Assistant.

Massimo (https://github.com/metaworx/massimo) holds the Cubes; this
integration is one more client of its HTTP API, signed in with an API key
of the role ``integration``.
"""

from __future__ import annotations

from homeassistant.const import CONF_API_KEY, CONF_URL, CONF_VERIFY_SSL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MassimoClient
from .const import DOMAIN
from .coordinator import MassimoConfigEntry, MassimoCoordinator
from .entity import register_cubes

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: MassimoConfigEntry) -> bool:
    """Read the server, then follow its Cubes' event streams.

    Returns True: Home Assistant 2026.10 requires a boolean, and 2026.11,
    which asks for None, ignores one from a custom integration.
    """
    session = async_get_clientsession(hass, verify_ssl=entry.data.get(CONF_VERIFY_SSL, True))
    client = MassimoClient(session, entry.data[CONF_URL], entry.data.get(CONF_API_KEY))
    coordinator = MassimoCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    register_cubes(coordinator)
    coordinator.start_streams()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MassimoConfigEntry) -> bool:
    """Stop following the server; the entry's background tasks end with it."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: MassimoConfigEntry, device: dr.DeviceEntry
) -> bool:
    """A device may be removed by hand once the server no longer lists it."""
    serials = entry.runtime_data.data.serials()
    return not any(domain == DOMAIN and ident in serials for domain, ident in device.identifiers)
