"""The config flow against a real Massimo server."""

from __future__ import annotations

from ipaddress import ip_address
from typing import Any

import pytest
from homeassistant.config_entries import SOURCE_USER, SOURCE_ZEROCONF
from homeassistant.const import CONF_API_KEY, CONF_URL, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.massimo import config_flow
from custom_components.massimo.const import DOMAIN

from .conftest import INSTANCE, Server, http


@pytest.fixture(autouse=True)
def quick_poll(monkeypatch: pytest.MonkeyPatch) -> None:
    """A registration is asked after every 50 ms, not every two seconds."""
    monkeypatch.setattr(config_flow, "REGISTER_POLL", 0.05)


async def _unload_all(hass: HomeAssistant) -> None:
    await hass.async_block_till_done()  # a reload after reauth or reconfigure
    for entry in hass.config_entries.async_entries(DOMAIN):
        await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


def _request(server: Server, code: str) -> dict[str, Any]:
    """The request waiting with the code, as the owner sees it in Massimo."""
    waiting = http("GET", f"{server.url}/api/v1/integrations", server.owner)
    return next(i for i in waiting if i.get("request_code") == code)  # type: ignore[union-attr]


async def _decide(hass: HomeAssistant, server: Server, result: dict[str, Any], decision: str) -> dict[str, Any]:
    """The owner approves or refuses the request the flow shows; the flow
    goes on by itself, then to its next step."""
    assert result["type"] is FlowResultType.SHOW_PROGRESS, result
    assert result["progress_action"] == "register"
    request = _request(server, result["description_placeholders"]["code"])
    assert request["instance_id"] == INSTANCE and request["kind"] == "homeassistant"
    http("POST", f"{server.url}/api/v1/integrations/{request['uuid']}/{decision}", server.owner, {})
    await hass.async_block_till_done()
    return await hass.config_entries.flow.async_configure(result["flow_id"])


async def _address(hass: HomeAssistant, url: str) -> dict[str, Any]:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "user"
    return await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: url, CONF_VERIFY_SSL: True})


async def test_registers_by_a_code(hass: HomeAssistant, massimo_server: Server, socket_enabled: None) -> None:
    """The address, then registration: the flow shows the code, and once
    the owner approves the request the entry has the integration's key and
    the server's node id; the same server again is refused."""
    result = await _address(hass, massimo_server.url + "/")
    assert result["type"] is FlowResultType.MENU and result["menu_options"] == ["register", "api_key"]
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "register"})
    result = await _decide(hass, massimo_server, result, "approve")
    assert result["type"] is FlowResultType.CREATE_ENTRY, result
    assert result["data"][CONF_URL] == massimo_server.url
    key = result["data"][CONF_API_KEY]
    me = http("GET", massimo_server.url + "/api/v1/me", key)
    assert me["integration"]["instance_id"] == INSTANCE  # type: ignore[index]
    assert result["result"].unique_id == (massimo_server.node_id or massimo_server.url)
    again = await _address(hass, massimo_server.url)
    assert again["type"] is FlowResultType.ABORT and again["reason"] == "already_configured"
    await _unload_all(hass)


async def test_a_refused_registration(hass: HomeAssistant, massimo_server: Server, socket_enabled: None) -> None:
    """A request the owner refuses ends the flow, saying so."""
    result = await _address(hass, massimo_server.url)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "register"})
    result = await _decide(hass, massimo_server, result, "refuse")
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "registration_gone"


async def test_a_key_typed_by_hand(hass: HomeAssistant, massimo_server: Server, socket_enabled: None) -> None:
    """A key typed by hand makes an entry named by the key's user; a wrong
    key and an unreachable address are said."""
    result = await _address(hass, massimo_server.url)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "api_key"})
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "api_key"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_API_KEY: "wrong"})
    assert result["type"] is FlowResultType.FORM and result["errors"] == {"base": "invalid_auth"}
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_API_KEY: massimo_server.typed_key})
    assert result["type"] is FlowResultType.CREATE_ENTRY, result
    assert result["title"] == "Massimo (hand)"
    assert result["data"] == {
        CONF_URL: massimo_server.url,
        CONF_API_KEY: massimo_server.typed_key,
        CONF_VERIFY_SSL: True,
    }
    await _unload_all(hass)
    unreachable = await _address(hass, "http://127.0.0.1:9")
    assert unreachable["type"] is FlowResultType.FORM and unreachable["errors"] == {"base": "cannot_connect"}


async def test_reconfigured_to_register(hass: HomeAssistant, massimo_server: Server, socket_enabled: None) -> None:
    """An entry with a key typed by hand registers by reconfiguring it."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=massimo_server.node_id or massimo_server.url,
        data={CONF_URL: massimo_server.url, CONF_API_KEY: massimo_server.typed_key, CONF_VERIFY_SSL: True},
    )
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "reconfigure"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: massimo_server.url, CONF_VERIFY_SSL: True}
    )
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "register"})
    result = await _decide(hass, massimo_server, result, "approve")
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "reconfigure_successful", result
    assert entry.data[CONF_API_KEY] != massimo_server.typed_key
    me = http("GET", massimo_server.url + "/api/v1/me", entry.data[CONF_API_KEY])
    assert me["integration"] is not None  # type: ignore[index]
    await _unload_all(hass)


async def test_reauth_offers_registration(hass: HomeAssistant, massimo_server: Server, socket_enabled: None) -> None:
    """A key that no longer works is replaced by registering again, or by
    another key."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=massimo_server.node_id or massimo_server.url,
        data={CONF_URL: massimo_server.url, CONF_API_KEY: "revoked", CONF_VERIFY_SSL: True},
    )
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.MENU and result["step_id"] == "sign_in"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "api_key"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_API_KEY: massimo_server.key})
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "reauth_successful", result
    assert entry.data[CONF_API_KEY] == massimo_server.key
    await _unload_all(hass)


def _found(server: Server, port: int, **props: str) -> ZeroconfServiceInfo:
    return ZeroconfServiceInfo(
        ip_address=ip_address("127.0.0.1"),
        ip_addresses=[ip_address("127.0.0.1")],
        port=port,
        hostname="massimo-test.local.",
        type="_massimo._tcp.local.",
        name="Massimo test._massimo._tcp.local.",
        properties={"node": server.node_id or "test-node", "v": "test", "tls": "0", "name": "test"} | props,
    )


async def test_zeroconf_flow(hass: HomeAssistant, massimo_server: Server, socket_enabled: None) -> None:
    """A server found by mDNS that takes no requests asks for the key, then
    makes an entry at its announced address."""
    info = _found(massimo_server, massimo_server.port, reg="0", api="1")
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_ZEROCONF}, data=info)
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "api_key"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_API_KEY: massimo_server.key})
    assert result["type"] is FlowResultType.CREATE_ENTRY, result
    assert result["data"][CONF_URL] == f"http://127.0.0.1:{massimo_server.port}"
    await _unload_all(hass)


async def test_zeroconf_takes_the_announced_url(
    hass: HomeAssistant, massimo_server: Server, socket_enabled: None
) -> None:
    """The record's url is taken where the server answers there; one where
    it does not leaves the address it was found at. Registration is
    offered where the record says requests are taken."""
    info = _found(massimo_server, 9, url=massimo_server.url, reg="1", api="1")
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_ZEROCONF}, data=info)
    assert result["type"] is FlowResultType.MENU and result["menu_options"] == ["register", "api_key"]
    assert result["description_placeholders"]["url"] == massimo_server.url
    hass.config_entries.flow.async_abort(result["flow_id"])
    info = _found(massimo_server, massimo_server.port, url="http://127.0.0.1:9", reg="1", api="1")
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_ZEROCONF}, data=info)
    assert result["description_placeholders"]["url"] == f"http://127.0.0.1:{massimo_server.port}"
    hass.config_entries.flow.async_abort(result["flow_id"])


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
