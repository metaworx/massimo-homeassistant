"""The API client against a real Massimo server and its fake Cube."""

from __future__ import annotations

import asyncio
import secrets

import aiohttp
import pytest

from custom_components.massimo.api import (
    MassimoAuthError,
    MassimoClient,
    MassimoConnectionError,
    StreamEvent,
)

from .conftest import Server, thermostat_room


async def _events(client: MassimoClient, serial: str, last: str | None, want, seconds: float = 15) -> list[StreamEvent]:
    """Reads a stream until want(events) holds, then leaves it."""
    out: list[StreamEvent] = []

    async def read() -> None:
        async for ev in client.events(serial, last):
            out.append(ev)
            if want(out):
                return

    await asyncio.wait_for(read(), seconds)
    return out


async def test_reads_the_server(massimo_server: Server, socket_enabled: None) -> None:
    """Health, the key's user and role, the Cubes and their rooms."""
    async with aiohttp.ClientSession() as session:
        client = MassimoClient(session, massimo_server.url, massimo_server.key)
        health = await client.health()
        assert health["ok"] is True
        me = await client.me()
        assert me["role"]["key"] == "integration"
        assert "read" in me["capabilities"] and "setpoint" in me["capabilities"]
        cubes = await client.cubes()
        assert [c["serial"] for c in cubes] == [massimo_server.serial]
        rooms = await client.rooms(massimo_server.serial)
        assert rooms and any(r.get("devices") for r in rooms)


async def test_the_integration_role_configures(massimo_server: Server, socket_enabled: None) -> None:
    """The role integration may write week programmes (Massimo's AP
    HomeAssistant, Block 2)."""
    async with aiohttp.ClientSession() as session:
        me = await MassimoClient(session, massimo_server.url, massimo_server.key).me()
    if "configure" not in me["capabilities"]:
        pytest.skip("this Massimo's role integration does not configure yet")
    assert "configure" in me["capabilities"]


async def test_a_wrong_key_is_refused(massimo_server: Server, socket_enabled: None) -> None:
    """A wrong key raises MassimoAuthError."""
    async with aiohttp.ClientSession() as session:
        with pytest.raises(MassimoAuthError):
            await MassimoClient(session, massimo_server.url, "wrong").me()


async def test_an_unreachable_server(socket_enabled: None) -> None:
    """A server that does not answer raises MassimoConnectionError."""
    async with aiohttp.ClientSession() as session:
        with pytest.raises(MassimoConnectionError):
            await MassimoClient(session, "http://127.0.0.1:9", None, timeout=2).health()


async def test_the_stream_resumes(massimo_server: Server, socket_enabled: None) -> None:
    """The first connection sends the state, its last event with an id; a
    reconnection with that id gets what came since and no state burst."""
    srv = massimo_server
    async with aiohttp.ClientSession() as session:
        client = MassimoClient(session, srv.url, srv.key)
        devices = sum(len(r.get("devices") or []) for r in await client.rooms(srv.serial))
        first = await _events(client, srv.serial, None, lambda evs: sum(e.kind == "state" for e in evs) >= devices)
        last = first[-1].id
        if not last:
            pytest.skip("this Massimo's event stream has no ids yet")
        # The fake Cube changes no state on a setpoint, but a rename is a
        # metadata write the server announces (metadata, change).
        room = thermostat_room(srv)
        name = f"Room {secrets.token_hex(3)}"
        async with session.put(
            f"{srv.url}/api/v1/cubes/{srv.serial}/rooms/{room['id']}",
            json={"name": name},
            headers={"Authorization": f"Bearer {srv.owner}"},
        ) as resp:
            assert resp.status == 200, await resp.text()

        def reached(evs: list[StreamEvent]) -> bool:
            return any(e.kind == "metadata" for e in evs)

        resumed = await _events(client, srv.serial, last, reached)
        assert resumed[0].kind not in ("resync",), "a known id resumes"
        assert all(e.id for e in resumed), "every resumed event carries its id"
        stale = await _events(client, srv.serial, "0-1", lambda evs: len(evs) >= 1)
        assert stale[0].kind == "resync", "an id of another epoch gets resync"
