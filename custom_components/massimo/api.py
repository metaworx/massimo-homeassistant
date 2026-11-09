"""A client for Massimo's HTTP API.

The API is described in Massimo's ``docs/api-v1.md``. This module depends
on aiohttp alone, so that it can be tested without Home Assistant.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import aiohttp


class MassimoError(Exception):
    """An error the server answered or a request that failed."""


class MassimoConnectionError(MassimoError):
    """The server could not be reached, or the connection broke."""


class MassimoAuthError(MassimoError):
    """The API key is missing, wrong, revoked, or not allowed this."""


@dataclass(frozen=True, slots=True)
class StreamEvent:
    """An event of a Cube's event stream.

    ``id`` is the event's id where the server sent one: the stream's events
    carry one, the state burst of a first connection only on its last
    event. A client resumes after the last id it read.
    """

    kind: str
    data: dict[str, Any]
    id: str | None


class MassimoClient:
    """Talks to one Massimo server, with an API key or, for a server
    without users, without one."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        url: str,
        api_key: str | None = None,
        *,
        timeout: float = 10,
    ) -> None:
        """Initialise the client for the server at url."""
        self._session = session
        self.url = url.rstrip("/")
        self._key = api_key or None
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    def _headers(self, accept: str = "application/json") -> dict[str, str]:
        headers = {"Accept": accept}
        if self._key:
            headers["Authorization"] = f"Bearer {self._key}"
        return headers

    @staticmethod
    async def _check(resp: aiohttp.ClientResponse) -> None:
        if resp.status in (401, 403):
            raise MassimoAuthError(f"{resp.status}: {(await resp.text()).strip()}")
        if resp.status >= 400:
            raise MassimoError(f"{resp.status}: {(await resp.text()).strip()}")

    async def _get(self, path: str) -> Any:
        try:
            async with self._session.get(self.url + path, headers=self._headers(), timeout=self._timeout) as resp:
                await self._check(resp)
                return await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise MassimoConnectionError(f"{path}: {err}") from err

    async def health(self) -> dict[str, Any]:
        """The server's health: its version, start and node_id."""
        return await self._get("/healthz")

    async def me(self) -> dict[str, Any]:
        """Who the key is: the server's mode, the user, the capabilities."""
        return await self._get("/api/v1/me")

    async def cubes(self) -> list[dict[str, Any]]:
        """The Cubes the server serves; those discovery merely found are
        left out."""
        return [c for c in await self._get("/api/v1/cubes") if c.get("configured")]

    async def rooms(self, serial: str) -> list[dict[str, Any]]:
        """A Cube's rooms, each with its devices."""
        return await self._get(f"/api/v1/cubes/{quote(serial)}/rooms")

    async def events(self, serial: str, last_event_id: str | None = None) -> AsyncIterator[StreamEvent]:
        """A Cube's event stream, from the last id read where one is given.

        The stream ends when the server ends it; the caller reconnects with
        the last id it read. A comment every 30 seconds keeps it alive, so a
        read that waits much longer means a dead connection.
        """
        headers = self._headers("text/event-stream")
        if last_event_id:
            headers["Last-Event-ID"] = last_event_id
        timeout = aiohttp.ClientTimeout(total=None, sock_connect=10, sock_read=90)
        url = f"{self.url}/api/v1/cubes/{quote(serial)}/events"
        try:
            async with self._session.get(url, headers=headers, timeout=timeout) as resp:
                await self._check(resp)
                kind = ""
                data: list[str] = []
                event_id: str | None = None
                async for raw in resp.content:
                    line = raw.decode("utf-8", "replace").rstrip("\r\n")
                    if not line:
                        if kind or data:
                            try:
                                payload = json.loads("\n".join(data)) if data else {}
                            except ValueError:
                                payload = {}
                            yield StreamEvent(kind or "message", payload, event_id)
                        kind, data, event_id = "", [], None
                        continue
                    if line.startswith(":"):
                        continue  # the keep-alive comment
                    field, _, value = line.partition(":")
                    value = value.removeprefix(" ")
                    if field == "event":
                        kind = value
                    elif field == "data":
                        data.append(value)
                    elif field == "id":
                        event_id = value
        except (aiohttp.ClientError, TimeoutError) as err:
            raise MassimoConnectionError(f"events of {serial}: {err}") from err
