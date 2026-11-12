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

from .conftest import Server, http, thermostat_room


async def _events(client: MassimoClient, serial: str, last: str | None, want, seconds: float = 15) -> list[StreamEvent]:
    """Reads a stream until want(events) holds, then leaves it; the
    client's own open event, which comes first, is left out."""
    out: list[StreamEvent] = []

    async def read() -> None:
        first = True
        async for ev in client.events(serial, last):
            if first:
                assert ev.kind == "open", "the stream's first event is the client's open"
                first = False
                continue
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


class _LoseFirstAnswer:
    """A session whose first write reaches the server and whose answer is
    then lost, as on a broken connection."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self.session = session
        self.keys: list[str] = []

    def request(self, method: str, url: str, **kwargs):
        self.keys.append(kwargs["headers"]["Idempotency-Key"])
        outer = self

        class Call:
            async def __aenter__(self):
                if len(outer.keys) == 1:
                    async with outer.session.request(method, url, **kwargs) as resp:
                        await resp.read()
                    raise aiohttp.ClientConnectionError("the answer was lost")
                self.cm = outer.session.request(method, url, **kwargs)
                return await self.cm.__aenter__()

            async def __aexit__(self, *exc):
                return await self.cm.__aexit__(*exc)

        return Call()


async def test_a_write_lost_on_its_way_back_is_retried_once(massimo_server: Server, socket_enabled: None) -> None:
    """A write whose answer is lost is sent again with the same
    Idempotency-Key: the server answers the first one's outcome and runs
    the command once."""
    srv = massimo_server
    rooms = http("GET", f"{srv.url}/api/v1/cubes/{srv.serial}/rooms", srv.owner)
    rf = next(d["rf_address"] for r in rooms for d in r.get("devices") or [] if "thermostat" in d["type"])  # type: ignore[union-attr]

    def locks() -> int:
        rows = http("GET", f"{srv.url}/api/v1/audit?user=homeassistant&limit=50", srv.owner)
        return sum(r["action"] == "device.lock" for r in rows)  # type: ignore[union-attr]

    before = locks()
    async with aiohttp.ClientSession() as session:
        lossy = _LoseFirstAnswer(session)
        client = MassimoClient(lossy, srv.url, srv.key)  # type: ignore[arg-type]
        answer = await client.set_lock(srv.serial, rf, False)
    assert answer["ok"] is True
    assert len(lossy.keys) == 2 and lossy.keys[0] == lossy.keys[1], "the retry carries the same key"
    assert locks() == before + 1, "the command ran once"
