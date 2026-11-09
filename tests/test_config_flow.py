"""The config flow against a real Massimo server."""

from __future__ import annotations

from ipaddress import ip_address

from homeassistant.config_entries import SOURCE_USER, SOURCE_ZEROCONF
from homeassistant.const import CONF_API_KEY, CONF_URL, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from custom_components.massimo.const import DOMAIN

from .conftest import Server


async def _unload_all(hass: HomeAssistant) -> None:
    for entry in hass.config_entries.async_entries(DOMAIN):
        await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_user_flow(hass: HomeAssistant, massimo_server: Server, socket_enabled: None) -> None:
    """An address and a key make an entry named by the key's user, the
    server's node id its unique id; the same server again is refused."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "user"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_URL: massimo_server.url + "/", CONF_API_KEY: massimo_server.key, CONF_VERIFY_SSL: True},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY, result
    assert result["title"] == "Massimo (homeassistant)"
    assert result["data"] == {CONF_URL: massimo_server.url, CONF_API_KEY: massimo_server.key, CONF_VERIFY_SSL: True}
    assert result["result"].unique_id == (massimo_server.node_id or massimo_server.url)

    again = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    again = await hass.config_entries.flow.async_configure(
        again["flow_id"], {CONF_URL: massimo_server.url, CONF_API_KEY: massimo_server.key}
    )
    assert again["type"] is FlowResultType.ABORT and again["reason"] == "already_configured"
    await _unload_all(hass)


async def test_user_flow_errors(hass: HomeAssistant, massimo_server: Server, socket_enabled: None) -> None:
    """A wrong key and an unreachable server keep the form, with the
    reason."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: massimo_server.url, CONF_API_KEY: "wrong"}
    )
    assert result["type"] is FlowResultType.FORM and result["errors"] == {"base": "invalid_auth"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: "http://127.0.0.1:9", CONF_API_KEY: massimo_server.key}
    )
    assert result["type"] is FlowResultType.FORM and result["errors"] == {"base": "cannot_connect"}


async def test_zeroconf_flow(hass: HomeAssistant, massimo_server: Server, socket_enabled: None) -> None:
    """A server found by mDNS asks for the key, then makes an entry at its
    announced address."""
    info = ZeroconfServiceInfo(
        ip_address=ip_address("127.0.0.1"),
        ip_addresses=[ip_address("127.0.0.1")],
        port=massimo_server.port,
        hostname="massimo-test.local.",
        type="_massimo._tcp.local.",
        name="Massimo test._massimo._tcp.local.",
        properties={"node": massimo_server.node_id or "test-node", "v": "test", "tls": "0", "name": "test"},
    )
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_ZEROCONF}, data=info)
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "zeroconf_confirm"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_API_KEY: massimo_server.key})
    assert result["type"] is FlowResultType.CREATE_ENTRY, result
    assert result["data"][CONF_URL] == f"http://127.0.0.1:{massimo_server.port}"
    await _unload_all(hass)


async def test_zeroconf_without_a_node_is_not_massimo(hass: HomeAssistant) -> None:
    """An announcement without the node id is not a Massimo server's."""
    info = ZeroconfServiceInfo(
        ip_address=ip_address("127.0.0.1"),
        ip_addresses=[ip_address("127.0.0.1")],
        port=8099,
        hostname="other.local.",
        type="_massimo._tcp.local.",
        name="other._massimo._tcp.local.",
        properties={},
    )
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_ZEROCONF}, data=info)
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "not_massimo"
