"""The config flow: a Massimo server by its address or by mDNS, and a key.

The server is identified by its node id (``/healthz``, and ``node`` in its
mDNS record), which stays the same across restarts, updates and new
addresses. The key is an API key of a user with the role ``integration``
(Massimo's docs/store.md, section 6); a server without users needs none.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, override

import probatio
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_API_KEY, CONF_URL, CONF_VERIFY_SSL
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .api import MassimoAuthError, MassimoClient, MassimoConnectionError, MassimoError
from .const import DOMAIN, LOGGER

# What the integration needs at least: reading. Setpoints and week
# programmes need setpoint and configure, which the role integration has.
REQUIRED_CAPABILITY = "read"


class MassimoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up a Massimo server."""

    VERSION = 1

    url: str = ""
    name: str = ""
    verify_ssl: bool = True

    async def _validate(self, url: str, key: str | None, verify_ssl: bool) -> tuple[str, str]:
        """Check the server and the key; return its node id and a name.

        Raises MassimoConnectionError, MassimoAuthError or MassimoError.
        """
        client = MassimoClient(async_get_clientsession(self.hass, verify_ssl=verify_ssl), url, key)
        health = await client.health()
        me = await client.me()
        if me.get("mode") == "users" and REQUIRED_CAPABILITY not in me.get("capabilities", []):
            raise MassimoAuthError("the key may not read")
        node = health.get("node_id") or url
        user = (me.get("user") or {}).get("name")
        return node, f"Massimo ({user})" if user else "Massimo"

    def _form(self, step_id: str, errors: dict[str, str] | None = None, *, url: bool = True) -> ConfigFlowResult:
        fields: dict[Any, Any] = {}
        if url:
            fields[probatio.Required(CONF_URL, default=self.url or "http://")] = str
        fields[probatio.Optional(CONF_API_KEY)] = str
        if url:
            fields[probatio.Optional(CONF_VERIFY_SSL, default=self.verify_ssl)] = bool
        return self.async_show_form(
            step_id=step_id,
            data_schema=probatio.Schema(fields),
            errors=errors or {},
            description_placeholders={"url": self.url, "name": self.name},
        )

    async def _try(self, url: str, key: str | None, verify_ssl: bool) -> tuple[str, str] | dict[str, str]:
        """Validate, turning failures into the form's errors."""
        try:
            return await self._validate(url, key, verify_ssl)
        except MassimoAuthError:
            return {"base": "invalid_auth"}
        except MassimoConnectionError:
            return {"base": "cannot_connect"}
        except MassimoError:
            LOGGER.exception("the server answered unexpectedly")
            return {"base": "unknown"}

    @override
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """A server by its address, and a key."""
        if user_input is None:
            return self._form("user")
        self.url = user_input[CONF_URL].rstrip("/")
        self.verify_ssl = user_input.get(CONF_VERIFY_SSL, True)
        key = user_input.get(CONF_API_KEY)
        found = await self._try(self.url, key, self.verify_ssl)
        if isinstance(found, dict):
            return self._form("user", found)
        node, title = found
        await self.async_set_unique_id(node)
        self._abort_if_unique_id_configured(updates={CONF_URL: self.url})
        return self.async_create_entry(
            title=title,
            data={CONF_URL: self.url, CONF_API_KEY: key, CONF_VERIFY_SSL: self.verify_ssl},
        )

    @override
    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo) -> ConfigFlowResult:
        """A server that announced itself by mDNS; the key comes next."""
        props = discovery_info.properties
        node = props.get("node")
        if not node:
            return self.async_abort(reason="not_massimo")
        scheme = "https" if props.get("tls") == "1" else "http"
        host = discovery_info.host if ":" not in discovery_info.host else f"[{discovery_info.host}]"
        self.url = f"{scheme}://{host}:{discovery_info.port}"
        # A server with its own certificate announces its fingerprint; the
        # check of a certificate no CA signed is left to the user's choice.
        self.verify_ssl = scheme == "http" or not props.get("fp")
        self.name = props.get("name") or node
        await self.async_set_unique_id(node)
        self._abort_if_unique_id_configured(updates={CONF_URL: self.url})
        self.context["title_placeholders"] = {"name": self.name}
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The key for a discovered server."""
        if user_input is None:
            return self._form("zeroconf_confirm", url=False)
        key = user_input.get(CONF_API_KEY)
        found = await self._try(self.url, key, self.verify_ssl)
        if isinstance(found, dict):
            return self._form("zeroconf_confirm", found, url=False)
        _, title = found
        return self.async_create_entry(
            title=title,
            data={CONF_URL: self.url, CONF_API_KEY: key, CONF_VERIFY_SSL: self.verify_ssl},
        )

    @override
    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """The key no longer works: ask for another."""
        self.url = entry_data[CONF_URL]
        self.verify_ssl = entry_data.get(CONF_VERIFY_SSL, True)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """A new key for the server."""
        if user_input is None:
            return self._form("reauth_confirm", url=False)
        key = user_input.get(CONF_API_KEY)
        found = await self._try(self.url, key, self.verify_ssl)
        if isinstance(found, dict):
            return self._form("reauth_confirm", found, url=False)
        node, _ = found
        await self.async_set_unique_id(node)
        self._abort_if_unique_id_mismatch(reason="wrong_server")
        return self.async_update_reload_and_abort(self._get_reauth_entry(), data_updates={CONF_API_KEY: key})
