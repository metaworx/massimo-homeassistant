"""Fixtures: a real Massimo server against Massimo's fake Cube.

The tests run against ``massimo serve`` and ``massimo fakecube``, as
Massimo's own UI suite does, rather than against mocks. MASSIMO_BIN names
the massimo binary (default: massimo on the PATH), MASSIMO_GREETING the fake
Cube's recorded greeting (Massimo's tools/ui-test/greeting.txt); without
them the tests that need a server are skipped, or fail where
MASSIMO_REQUIRED is set, as CI sets it.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import subprocess
import time
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
import pytest_socket

pytest_plugins = "pytest_homeassistant_custom_component"

SERIAL = "KEQ0000100"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Every test may load the integration from custom_components."""


@dataclass(frozen=True)
class Server:
    """A running Massimo server: its address, the owner's token, and an API
    key of a user with the role integration."""

    url: str
    owner: str
    key: str
    serial: str
    node_id: str
    port: int


def _wait_line(log: Path, pattern: str, what: str, seconds: float = 15) -> re.Match[str]:
    """Waits for a line of a program's log and returns its match."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if log.exists() and (m := re.search(pattern, log.read_text(errors="replace"))):
            return m
        time.sleep(0.1)
    raise RuntimeError(f"{what} did not start; its log:\n{log.read_text(errors='replace') if log.exists() else ''}")


def http(method: str, url: str, token: str | None, body: object | None = None) -> object:
    """A blocking request to the server, for the fixtures and the tests."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=130) as resp:
        raw = resp.read()
    return json.loads(raw) if raw else None


@pytest.fixture(scope="session")
def massimo_server(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Server]:
    """The fake Cube and a server connected to it, for the whole session."""
    binary = os.environ.get("MASSIMO_BIN") or shutil.which("massimo")
    greeting = os.environ.get("MASSIMO_GREETING")
    if not binary or not greeting:
        if os.environ.get("MASSIMO_REQUIRED"):
            pytest.fail("MASSIMO_REQUIRED is set, and MASSIMO_BIN or MASSIMO_GREETING is missing")
        pytest.skip("MASSIMO_BIN and MASSIMO_GREETING are needed for a server")
    # Home Assistant's harness blocks sockets for each test; the fixture's
    # own requests go to the loopback only.
    pytest_socket.enable_socket()
    work = tmp_path_factory.mktemp("massimo")
    env = {"PATH": os.environ.get("PATH", ""), "HOME": str(work)}
    procs: list[subprocess.Popen[bytes]] = []
    try:
        fake_log = work / "fakecube.log"
        procs.append(
            subprocess.Popen(
                [binary, "fakecube", "-greeting", greeting, "-listen", "127.0.0.1:0", "-discovery", "127.0.0.1:0"],
                cwd=work,
                env=env,
                stdout=fake_log.open("wb"),
                stderr=subprocess.STDOUT,
            )
        )
        cube = _wait_line(fake_log, r"fake cube listening on (127\.0\.0\.1:\d+)", "the fake Cube").group(1)
        disc = _wait_line(fake_log, r"answering discovery on (127\.0\.0\.1:\d+)", "the fake Cube's discovery").group(1)
        owner = secrets.token_hex(16)
        serve_log = work / "serve.log"
        procs.append(
            subprocess.Popen(
                # A setpoint shows in the Cube's next device list, which the
                # server polls: every second here, a minute by default.
                [
                    binary,
                    "serve",
                    "-proxy",
                    "off",
                    "-listen",
                    "127.0.0.1:0",
                    "-poll",
                    "1s",
                    "-update-status",
                    str(work / "no-update-status.json"),
                    "-discover-target",
                    disc,
                    "-discover-listen",
                    "127.0.0.1:0",
                    "-discover-interval",
                    "0",
                ],
                cwd=work,
                env=env
                | {
                    "MASSIMO_API_TOKEN": owner,
                    f"MASSIMO_CUBE_{SERIAL}_ADDRESS": cube,
                    f"MASSIMO_CUBE_{SERIAL}_NAME": "Fake Cube",
                },
                stdout=serve_log.open("wb"),
                stderr=subprocess.STDOUT,
            )
        )
        port = int(_wait_line(serve_log, r'msg="api listening"[^\n]*? addr=127\.0\.0\.1:(\d+)', "the server").group(1))
        url = f"http://127.0.0.1:{port}"
        deadline = time.monotonic() + 20
        while True:
            cubes = http("GET", url + "/api/v1/cubes", owner)
            if any(c.get("serial") == SERIAL and c.get("connected") for c in cubes):  # type: ignore[union-attr]
                break
            if time.monotonic() > deadline:
                raise RuntimeError(f"the server did not connect to the fake Cube; its log:\n{serve_log.read_text()}")
            time.sleep(0.2)
        http("POST", url + "/api/v1/users", owner, {"name": "homeassistant", "role": "integration"})
        made = http("POST", url + "/api/v1/users/homeassistant/tokens", owner, {"label": "tests"})
        key = made.get("token") or made.get("secret")  # type: ignore[union-attr]
        node = http("GET", url + "/healthz", None).get("node_id", "")  # type: ignore[union-attr]
        yield Server(url=url, owner=owner, key=key, serial=SERIAL, node_id=node, port=port)
    finally:
        for p in procs:
            p.terminate()
        for p in procs:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()


def thermostat_room(server: Server) -> dict:
    """The first room with a thermostat, as the API describes it."""
    for room in http("GET", f"{server.url}/api/v1/cubes/{server.serial}/rooms", server.owner):  # type: ignore[union-attr]
        if any("thermostat" in (d.get("type") or "") for d in room.get("devices") or []):
            return room
    raise AssertionError("the fake Cube has no room with a thermostat")


def stream_has_ids(server: Server) -> bool:
    """Whether the server's event stream carries ids (Massimo's AP
    HomeAssistant, Block 1): its first connection's state burst ends with
    one."""
    req = urllib.request.Request(f"{server.url}/api/v1/cubes/{server.serial}/events")
    req.add_header("Authorization", f"Bearer {server.owner}")
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            blank = 0
            for raw in resp:
                line = raw.decode("utf-8", "replace").rstrip("\r\n")
                if line.startswith("id:"):
                    return True
                if line.startswith(":") or blank > 64:
                    return False  # the keep-alive: the burst is over
                blank += not line
    except TimeoutError:
        pass  # the burst ended without an id, and nothing came after it
    return False
