"""Calls made for Home Assistant's users, as Massimo sees them: each names
its user and level where the key is a registered integration's."""

from __future__ import annotations

import pytest
from homeassistant.const import CONF_API_KEY, CONF_URL, CONF_VERIFY_SSL
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry, MockUser

from custom_components.massimo.const import DOMAIN

from .conftest import INSTANCE, Server, http, integration_users, register, rooms
from .test_entities import _entity, _setup, _unload
from .test_rooms import SCHLAFEN, _climate


def _lock(hass: HomeAssistant, server: Server) -> str:
    """The key lock of the first thermostat."""
    serial = next(d["serial"] for r in rooms(server) for d in r.get("devices") or [] if "thermostat" in d["type"])
    return _entity(hass, "switch", f"{serial}_key_lock")


async def _unlock(hass: HomeAssistant, entity_id: str, context: Context) -> None:
    await hass.services.async_call("switch", "turn_off", {"entity_id": entity_id}, blocking=True, context=context)


def _issue(hass: HomeAssistant, name: str, entry: MockConfigEntry) -> ir.IssueEntry | None:
    return ir.async_get(hass).async_get_issue(DOMAIN, f"{name}_{entry.entry_id}")


async def test_each_call_names_its_user(
    hass: HomeAssistant,
    massimo_server: Server,
    socket_enabled: None,
    hass_admin_user: MockUser,
    hass_read_only_user: MockUser,
) -> None:
    """An administrator's write is admin, a user's who may control the
    entity control, an automation's system's; a viewer's programme read is
    view. Massimo lists each with its name and last level."""
    entry = await _setup(hass, massimo_server)
    assert entry.runtime_data.integration["uuid"] == massimo_server.integration
    assert _issue(hass, "register", entry) is None
    lock = _lock(hass, massimo_server)
    anna = await hass.auth.async_create_user("Anna Müller", group_ids=["system-users"])
    await _unlock(hass, lock, Context(user_id=hass_admin_user.id))
    await _unlock(hass, lock, Context(user_id=anna.id))
    await _unlock(hass, lock, Context(parent_id="automation-run"))
    await hass.services.async_call(
        DOMAIN,
        "get_program",
        {"entity_id": _climate(hass, massimo_server, SCHLAFEN)},
        blocking=True,
        return_response=True,
        context=Context(user_id=hass_read_only_user.id),
    )
    users = {u["id"]: u for u in integration_users(massimo_server)}
    assert users[hass_admin_user.id]["last_level"] == "admin"
    assert users[anna.id]["last_level"] == "control" and users[anna.id]["name"] == "Anna Müller"
    assert users[hass_read_only_user.id]["last_level"] == "view"
    assert users["system"]["last_level"] == "admin"
    await _unload(hass, entry)


async def test_a_typed_key_names_nobody(hass: HomeAssistant, massimo_server: Server, socket_enabled: None) -> None:
    """A key typed by hand writes without the header, as before, and the
    entry gets the repair that offers registration."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=massimo_server.node_id or massimo_server.url,
        data={CONF_URL: massimo_server.url, CONF_API_KEY: massimo_server.typed_key, CONF_VERIFY_SSL: True},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.runtime_data.integration is None
    issue = _issue(hass, "register", entry)
    assert issue is not None and issue.translation_key == "register"
    await _unlock(hass, _lock(hass, massimo_server), Context())
    await _unload(hass, entry)


async def test_another_installation_is_accepted_first(
    hass: HomeAssistant, massimo_server: Server, socket_enabled: None
) -> None:
    """A registration accepted from another installation id raises the
    repair, and Massimo notes this one's for the owner; calls for users are
    refused with their own text until the owner accepts it, and the repair
    then goes."""
    key, uuid = register(massimo_server.url, massimo_server.owner, "moved", instance="e" * 32)
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=massimo_server.node_id or massimo_server.url,
        data={CONF_URL: massimo_server.url, CONF_API_KEY: key, CONF_VERIFY_SSL: True},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert _issue(hass, "instance_pending", entry) is not None
    integration = http("GET", f"{massimo_server.url}/api/v1/integrations/{uuid}", massimo_server.owner)
    assert integration["pending_instance"] == INSTANCE  # type: ignore[index]
    lock = _lock(hass, massimo_server)
    with pytest.raises(HomeAssistantError) as refused:
        await _unlock(hass, lock, Context())
    assert refused.value.translation_key == "refused_instance_pending"
    http("POST", f"{massimo_server.url}/api/v1/integrations/{uuid}/accept-instance", massimo_server.owner, {})
    await _unlock(hass, lock, Context())
    assert _issue(hass, "instance_pending", entry) is None
    await _unload(hass, entry)
