"""The config flow: a Massimo server by its address or by mDNS, registered
by a code or with a key typed by hand.

The server is identified by its node id (``/healthz``, and ``node`` in its
mDNS record), which stays the same across restarts, updates and new
addresses.

A Massimo with the feature ``integration`` registers Home Assistant without
a key typed anywhere (Massimo's docs/api-v1.md, "Integrations"): the flow
asks to be registered, shows the request's code while it waits, and
collects its key once the owner has approved the request in Massimo. A key
typed by hand stays possible, of any user who may read; a server without
users needs none.

Whether registration is offered is read from the server when the flow
reaches the sign-in step, and again whenever that step is opened again, as
when the card of a server discovered long before is clicked.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Mapping
from typing import Any, override
from urllib.parse import urlsplit

import probatio
from homeassistant.config_entries import (
    SOURCE_REAUTH,
    SOURCE_RECONFIGURE,
    SOURCE_ZEROCONF,
    ConfigEntry,
    ConfigEntryState,
    ConfigFlow,
    ConfigFlowResult,
)
from homeassistant.const import CONF_API_KEY, CONF_NAME, CONF_URL, CONF_VERIFY_SSL
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.helpers import instance_id
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import NoURLAvailableError, get_url
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .api import (
    MassimoAuthError,
    MassimoClient,
    MassimoConnectionError,
    MassimoError,
    MassimoRegistrationGoneError,
    MassimoRegistrationOffError,
)
from .const import CONF_ANNOUNCED, CONF_AUTO_TITLE, CONF_REGISTERED, CONF_REGISTRATION_NAME, DOMAIN, LOGGER
from .coordinator import has_feature
from .title import entry_name, entry_title, key_user, title_is_automatic

# What the integration needs at least: reading. Setpoints and week
# programmes need setpoint and configure, which the role integration has.
REQUIRED_CAPABILITY = "read"

# How often a registration request is asked after, and how long at most:
# Massimo lets a request wait ten minutes.
REGISTER_POLL = 2.0
REGISTER_WAIT = 11 * 60

# What Massimo takes of a request's name, address and version.
NAME_LEN, URL_LEN, VERSION_LEN = 64, 256, 32


class MassimoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up a Massimo server."""

    url: str = ""
    name: str = ""
    verify_ssl: bool = True
    # Whether the server may be asked to register: it has the feature and
    # users, and its announcement did not say it takes no requests.
    registers: bool = False
    takes_requests: bool = True
    # The server's location, from its mDNS record; whether the address is
    # the one its announcement led to.
    location: str = ""
    announced: bool = False
    # The entry's name in Home Assistant, as chosen in the flow.
    entry_name: str | None = None
    _request: dict[str, Any] | None = None
    _collect: asyncio.Task[str] | None = None

    def _client(self, key: str | None = None, url: str | None = None) -> MassimoClient:
        session = async_get_clientsession(self.hass, verify_ssl=self.verify_ssl)
        return MassimoClient(session, url or self.url, key)

    async def _server(self) -> str:
        """Read the server's health: its node id. Notes whether it can
        register this installation. Raises MassimoError."""
        client = self._client()
        health = await client.health()
        self.registers = False
        feature = has_feature(health, "integration")
        mode = None
        if feature and self.takes_requests:
            try:
                me = await client.me()
            except MassimoAuthError:
                mode = "users"  # a server with users wants a key
            else:
                mode = me.get("mode")
            self.registers = mode == "users"
        LOGGER.debug(
            "%s: registration %s (feature integration: %s, mode: %s, takes requests: %s)",
            self.url,
            "offered" if self.registers else "not offered",
            feature,
            mode,
            self.takes_requests,
        )
        return health.get("node_id") or self.url

    async def _read_again(self) -> None:
        """The sign-in step opened again: the server read again. The record
        the server was discovered with may be old, so its reg no longer
        counts; the request itself says whether requests are taken."""
        before = self.registers
        self.takes_requests = True
        try:
            await self._server()
        except MassimoError as err:
            LOGGER.debug("%s: not read again: %s", self.url, err)
            self.registers = before

    async def _validate(self, key: str | None) -> tuple[str, str | None, bool]:
        """Check the key; return the server's node id, the key's user and
        whether the key is a registered integration's.

        Raises MassimoConnectionError, MassimoAuthError or MassimoError.
        """
        client = self._client(key)
        health = await client.health()
        me = await client.me()
        if me.get("mode") == "users" and REQUIRED_CAPABILITY not in me.get("capabilities", []):
            raise MassimoAuthError("the key may not read")
        node = health.get("node_id") or self.url
        return node, key_user(me), me.get("integration") is not None

    def _placeholders(self) -> dict[str, str]:
        return {"url": self.url, "name": self.name or self.url}

    def _default_name(self) -> str:
        """The entry's name until one is chosen: the entry's own where it
        has one, else Massimo's location, else the address's host."""
        if self.source in (SOURCE_REAUTH, SOURCE_RECONFIGURE):
            entry = self._get_reauth_entry() if self.source == SOURCE_REAUTH else self._get_reconfigure_entry()
            if name := entry.data.get(CONF_NAME):
                return name
        where = self.location or urlsplit(self.url).hostname or ""
        return f"Massimo {where}" if where else "Massimo"

    def _discovered(self) -> str | None:
        """The address of a server discovered and not set up, to start from."""
        for flow in self.hass.config_entries.flow.async_progress_by_handler(
            DOMAIN, match_context={"source": SOURCE_ZEROCONF}
        ):
            if url := flow["context"].get("configuration_url"):
                return url
        return None

    def _address_form(self, step_id: str, errors: dict[str, str] | None = None) -> ConfigFlowResult:
        url = self.url or (self._discovered() if step_id == "user" else None) or "http://"
        fields: dict[Any, Any] = {
            probatio.Required(CONF_URL, default=url): str,
            probatio.Optional(CONF_VERIFY_SSL, default=self.verify_ssl): bool,
        }
        return self.async_show_form(
            step_id=step_id,
            data_schema=probatio.Schema(fields),
            errors=errors or {},
            description_placeholders=self._placeholders(),
        )

    def _name_field(self, fields: dict[Any, Any]) -> None:
        """The entry's name, asked except in re-authentication, which keeps
        it."""
        if self.source != SOURCE_REAUTH:
            fields[probatio.Required(CONF_NAME, default=self.entry_name or self._default_name())] = str

    def _take_name(self, user_input: Mapping[str, Any]) -> None:
        if self.source != SOURCE_REAUTH:
            self.entry_name = (user_input.get(CONF_NAME) or "").strip() or self._default_name()

    async def _address(self, step_id: str, user_input: dict[str, Any]) -> ConfigFlowResult:
        """The address typed: the server read, then the way to sign in."""
        self.url = user_input[CONF_URL].rstrip("/")
        self.verify_ssl = user_input.get(CONF_VERIFY_SSL, True)
        self.announced = False
        try:
            node = await self._server()
        except MassimoConnectionError:
            return self._address_form(step_id, {"base": "cannot_connect"})
        except MassimoError:
            LOGGER.exception("the server answered unexpectedly")
            return self._address_form(step_id, {"base": "unknown"})
        await self.async_set_unique_id(node)
        if self.source == SOURCE_RECONFIGURE:
            self._abort_if_unique_id_mismatch(reason="wrong_server")
        else:
            self._abort_if_unique_id_configured(updates={CONF_URL: self.url, CONF_ANNOUNCED: False})
        return await self._sign_in()

    async def async_step_sign_in(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The sign-in menu opened again: the server read again first."""
        await self._read_again()
        return await self._sign_in()

    async def _sign_in(self) -> ConfigFlowResult:
        """Registration and a key typed by hand, or the key alone."""
        if self.registers:
            return self.async_show_menu(
                step_id="sign_in", menu_options=["register", "api_key"], description_placeholders=self._placeholders()
            )
        return await self.async_step_api_key()

    async def _done(self, key: str | None, user: str | None, registered: bool) -> ConfigFlowResult:
        """The entry made, or the entry re-authenticated or reconfigured
        updated and reloaded."""
        data: dict[str, Any] = {
            CONF_URL: self.url,
            CONF_API_KEY: key,
            CONF_VERIFY_SSL: self.verify_ssl,
            CONF_REGISTERED: registered,
        }
        if self.source in (SOURCE_REAUTH, SOURCE_RECONFIGURE):
            self._abort_if_unique_id_mismatch(reason="wrong_server")
            entry = self._get_reauth_entry() if self.source == SOURCE_REAUTH else self._get_reconfigure_entry()
            if self.source == SOURCE_REAUTH:
                data[CONF_NAME] = entry_name(entry)
            else:
                data |= {CONF_NAME: self.entry_name or self._default_name(), CONF_ANNOUNCED: self.announced}
            if not title_is_automatic(entry):
                return self.async_update_reload_and_abort(entry, data_updates=data)
            title = await entry_title(self.hass, data[CONF_NAME], user, registered)
            return self.async_update_reload_and_abort(entry, title=title, data_updates=data | {CONF_AUTO_TITLE: title})
        data |= {CONF_NAME: self.entry_name or self._default_name(), CONF_ANNOUNCED: self.announced}
        title = await entry_title(self.hass, data[CONF_NAME], user, registered)
        return self.async_create_entry(title=title, data=data | {CONF_AUTO_TITLE: title})

    @override
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """A server by its address."""
        if user_input is None:
            return self._address_form("user")
        return await self._address("user", user_input)

    async def async_step_api_key(
        self, user_input: dict[str, Any] | None = None, errors: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """A key typed by hand; empty for a server without users."""
        if user_input is None and errors is None and self.cur_step and self.cur_step.get("step_id") == "api_key":
            # The key form opened again, not chosen from the menu just now.
            await self._read_again()
            if self.registers:
                return await self._sign_in()
        if user_input is not None:
            key = user_input.get(CONF_API_KEY)
            self._take_name(user_input)
            try:
                node, user, registered = await self._validate(key)
            except MassimoAuthError:
                errors = {"base": "invalid_auth"}
            except MassimoConnectionError:
                errors = {"base": "cannot_connect"}
            except MassimoError:
                LOGGER.exception("the server answered unexpectedly")
                errors = {"base": "unknown"}
            else:
                await self.async_set_unique_id(node)
                return await self._done(key, user, registered)
        fields: dict[Any, Any] = {probatio.Optional(CONF_API_KEY): str}
        self._name_field(fields)
        return self.async_show_form(
            step_id="api_key",
            data_schema=probatio.Schema(fields),
            errors=errors or {},
            description_placeholders=self._placeholders(),
        )

    async def async_step_register(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The names first; then ask Massimo to register this installation,
        and wait, showing the request's code, until the owner has approved
        it."""
        if self._collect is None:
            if user_input is None:
                return self._names_form()
            self._take_name(user_input)
            name = (user_input.get(CONF_REGISTRATION_NAME) or "").strip() or self._own_name()
            try:
                self._request = await self._client().request_registration(
                    name[:NAME_LEN],
                    await instance_id.async_get(self.hass),
                    self._own_url(),
                    HA_VERSION[:VERSION_LEN],
                )
            except MassimoRegistrationOffError:
                return await self.async_step_api_key(errors={"base": "registration_off"})
            except MassimoConnectionError:
                return await self.async_step_api_key(errors={"base": "cannot_connect"})
            except MassimoError:
                LOGGER.exception("the server answered the registration unexpectedly")
                return await self.async_step_api_key(errors={"base": "unknown"})
            self._collect = self.hass.async_create_task(self._wait(self._request["id"], self._request["code"]))
        if not self._collect.done():
            return self.async_show_progress(
                step_id="register",
                progress_action="register",
                progress_task=self._collect,
                description_placeholders=self._placeholders() | {"code": self._request["code"]},  # type: ignore[index]
            )
        try:
            self._collect.result()
        except MassimoRegistrationGoneError:
            return self.async_show_progress_done(next_step_id="register_gone")
        except MassimoError:
            LOGGER.exception("the registration was not collected")
            return self.async_show_progress_done(next_step_id="register_failed")
        return self.async_show_progress_done(next_step_id="register_done")

    def _names_form(self) -> ConfigFlowResult:
        """The name Home Assistant gives itself in Massimo, and the entry's
        name here."""
        fields: dict[Any, Any] = {probatio.Required(CONF_REGISTRATION_NAME, default=self._own_name()): str}
        self._name_field(fields)
        return self.async_show_form(
            step_id="register", data_schema=probatio.Schema(fields), description_placeholders=self._placeholders()
        )

    def _own_name(self) -> str:
        """Home Assistant's name, for Massimo's list of integrations."""
        return (self.hass.config.location_name or "Home Assistant")[:NAME_LEN]

    def _own_url(self) -> str:
        """Home Assistant's address, for Massimo's list of integrations."""
        try:
            url = get_url(self.hass, allow_ip=True, prefer_external=False)
        except NoURLAvailableError:
            return ""
        return url if len(url) <= URL_LEN else ""

    async def _wait(self, request_id: str, code: str) -> str:
        """The key, once the request is approved. Raises
        MassimoRegistrationGoneError once it is refused or expired; a
        connection lost meanwhile is tried again."""
        client = self._client()
        deadline = time.monotonic() + REGISTER_WAIT
        while True:
            try:
                answer = await client.collect_registration(request_id, code)
            except MassimoConnectionError:
                if time.monotonic() > deadline:
                    raise
                answer = None
            if answer is not None:
                return answer["key"]
            if time.monotonic() > deadline:
                raise MassimoRegistrationGoneError("the request was neither approved nor refused")
            await asyncio.sleep(REGISTER_POLL)

    async def async_step_register_done(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The key collected: the entry made, or updated."""
        key = self._collect.result()  # type: ignore[union-attr]
        try:
            node, user, registered = await self._validate(key)
        except MassimoError:
            LOGGER.exception("the key collected does not work")
            return self.async_abort(reason="registration_failed")
        await self.async_set_unique_id(node)
        return await self._done(key, user, registered)

    async def async_step_register_gone(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The request refused, or expired before it was approved."""
        return self.async_abort(reason="registration_gone")

    async def async_step_register_failed(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The key could not be collected."""
        return self.async_abort(reason="registration_failed")

    @override
    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo) -> ConfigFlowResult:
        """A server that announced itself by mDNS: at the address its
        record names where it answers there, else at the one it was found
        at."""
        props = discovery_info.properties
        node = props.get("node")
        if not node:
            return self.async_abort(reason="not_massimo")
        scheme = "https" if props.get("tls") == "1" else "http"
        host = discovery_info.host if ":" not in discovery_info.host else f"[{discovery_info.host}]"
        # A server with its own certificate announces its fingerprint; the
        # check of a certificate no CA signed is left to the user's choice.
        self.verify_ssl = scheme == "http" or not props.get("fp")
        self.url = f"{scheme}://{host}:{discovery_info.port}"
        recorded = (props.get("url") or "").rstrip("/")
        if recorded and recorded != self.url:
            self.url = await self._answers(recorded, node) or self.url
        self.takes_requests = props.get("reg") != "0"
        self.name = props.get("name") or node
        self.location = props.get("loc") or ""
        self.announced = True
        await self.async_set_unique_id(node)
        if entry := self.hass.config_entries.async_entry_for_domain_unique_id(DOMAIN, node):
            self._abort_if_unique_id_configured(updates=self._follow(entry, self.url == recorded))
        self.context["title_placeholders"] = {"name": self.name}
        self.context["configuration_url"] = self.url
        return await self.async_step_zeroconf_confirm()

    @staticmethod
    def _registered(entry: ConfigEntry) -> bool:
        if entry.state is ConfigEntryState.LOADED:
            return entry.runtime_data.integration is not None
        return bool(entry.data.get(CONF_REGISTERED))

    def _follow(self, entry: ConfigEntry, recorded: bool) -> dict[str, Any] | None:
        """What a discovery changes of an entry set up: the address where
        the entry took its own from an announcement, or where the entry is
        registered and the address is the one the record names; an address
        typed by hand is kept otherwise."""
        if self.url == entry.data.get(CONF_URL):
            return None
        if entry.data.get(CONF_ANNOUNCED):
            return {CONF_URL: self.url}
        if recorded and self._registered(entry):
            return {CONF_URL: self.url}
        return None

    async def _answers(self, url: str, node: str) -> str | None:
        """The address, where the server of that node answers there."""
        try:
            health = await self._client(url=url).health()
        except MassimoError:
            return None
        return url if health.get("node_id") == node else None

    async def async_step_zeroconf_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """A discovered server: the way to sign in."""
        try:
            await self._server()
        except MassimoError:
            return self.async_abort(reason="cannot_connect")
        return await self._sign_in()

    @override
    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """The key no longer works: register again, or another key."""
        self.url = entry_data[CONF_URL]
        self.verify_ssl = entry_data.get(CONF_VERIFY_SSL, True)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The way to sign in again."""
        try:
            await self._server()
        except MassimoError:
            self.registers = False
        return await self._sign_in()

    @override
    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Another address, or another way to sign in: registration for an
        entry made with a key typed by hand."""
        if user_input is None:
            entry = self._get_reconfigure_entry()
            self.url = entry.data[CONF_URL]
            self.verify_ssl = entry.data.get(CONF_VERIFY_SSL, True)
            return self._address_form("reconfigure")
        return await self._address("reconfigure", user_input)
