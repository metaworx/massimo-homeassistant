"""Week programmes: read, written with the tag they were read with, and
copied, against a real server and the fake Cube's fixture rooms."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError, Unauthorized
from pytest_homeassistant_custom_component.common import MockUser
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.massimo.const import DOMAIN
from custom_components.massimo.program import DAYS

from .conftest import Server
from .test_entities import _setup, _unload, _until
from .test_rooms import SCHLAFEN, WOHNEN, _attr, _climate

DAY = [{"temp": 17.0, "until": "07:00"}, {"temp": 21.0, "until": "22:00"}, {"temp": 17.0, "until": "24:00"}]


async def _get(hass: HomeAssistant, entity_id: str) -> dict[str, Any]:
    answer = await hass.services.async_call(
        DOMAIN, "get_program", {"entity_id": entity_id}, blocking=True, return_response=True
    )
    return answer[entity_id]


async def _set(hass: HomeAssistant, entity_id: str, **data: Any) -> dict[str, Any]:
    answer = await hass.services.async_call(
        DOMAIN, "set_program", {"entity_id": entity_id, **data}, blocking=True, return_response=True
    )
    return answer[entity_id]


@pytest.fixture
async def rooms_kept(hass: HomeAssistant, massimo_server: Server, socket_enabled: None) -> AsyncIterator[dict]:
    """The integration set up, the two rooms' climates, and their
    programmes written back as they were after the test."""
    entry = await _setup(hass, massimo_server)
    room = {"entry": entry, "wohnen": _climate(hass, massimo_server, WOHNEN)}
    room["schlafen"] = _climate(hass, massimo_server, SCHLAFEN)
    before = {name: (await _get(hass, room[name]))["program"] for name in ("wohnen", "schlafen")}
    yield room
    for name, program in before.items():
        now = (await _get(hass, room[name]))["program"]
        changed = {day: points for day, points in program.items() if now.get(day) != points}
        if changed:  # each day is a radiogram on the fake Cube's duty cycle
            await _set(hass, room[name], program=changed)
    await _unload(hass, entry)


async def test_get_program(hass: HomeAssistant, rooms_kept: dict) -> None:
    """A room's programme: every day, its tag, not pending, consistent."""
    program = await _get(hass, rooms_kept["schlafen"])
    assert set(program["program"]) == set(DAYS)
    assert program["program"]["monday"][-1]["until"] == "24:00"
    assert program["etag"] and program["pending"] is False and program["consistent"] is True
    assert _attr(hass, rooms_kept["schlafen"], "program_tag") == program["etag"]


async def test_set_program_with_its_tag(hass: HomeAssistant, rooms_kept: dict) -> None:
    """A write with the tag it read changes the programme and answers the
    new tag; one with the old tag is refused; the climate then shows the new
    tag and when the change was seen."""
    room = rooms_kept["schlafen"]
    read = await _get(hass, room)
    answer = await _set(hass, room, program={"monday": DAY}, etag=read["etag"])
    assert answer["etag"] and answer["etag"] != read["etag"]
    assert (await _get(hass, room))["program"]["monday"] == DAY
    with pytest.raises(HomeAssistantError) as refused:
        await _set(hass, room, program={"monday": DAY[-1:]}, etag=read["etag"])
    assert refused.value.translation_key == "program_changed_meanwhile"
    await _until(hass, lambda: _attr(hass, room, "program_tag") == answer["etag"], "the new tag is shown")
    assert _attr(hass, room, "program_changed")


@pytest.mark.parametrize(
    ("program", "key"),
    [
        ({"monday": DAY[:2]}, "program_end"),
        ({"monday": [DAY[1], DAY[0], DAY[2]]}, "program_time"),
        ({"monday": [{"temp": 17, "until": "07:03"}, DAY[2]]}, "program_time"),
        ({"monday": [{"temp": 31, "until": "24:00"}]}, "program_temp"),
        ({"monday": [{"temp": 17.3, "until": "24:00"}]}, "program_temp"),
        ({"monday": [{"temp": 17, "until": f"{h:02d}:00"} for h in range(1, 14)] + DAY[2:]}, "program_points"),
        ({"funday": DAY}, "program_day"),
        ({}, "program_empty"),
    ],
)
async def test_a_programme_is_checked(hass: HomeAssistant, rooms_kept: dict, program: dict, key: str) -> None:
    """A programme Massimo would refuse is refused before it is sent, saying
    what is wrong."""
    with pytest.raises(ServiceValidationError) as refused:
        await _set(hass, rooms_kept["schlafen"], program=program)
    assert refused.value.translation_key == key


async def test_copy_a_room_and_a_day(hass: HomeAssistant, rooms_kept: dict) -> None:
    """A room's programme copied to another room; one day of a room copied
    onto its other days."""
    wohnen, schlafen = rooms_kept["wohnen"], rooms_kept["schlafen"]
    await _set(hass, schlafen, program={"monday": DAY})
    await hass.services.async_call(DOMAIN, "copy_program", {"entity_id": wohnen, "source": schlafen}, blocking=True)
    assert (await _get(hass, wohnen))["program"] == (await _get(hass, schlafen))["program"]
    await hass.services.async_call(
        DOMAIN,
        "copy_program",
        {"entity_id": schlafen, "days": ["monday"], "to_days": ["saturday", "sunday"]},
        blocking=True,
    )
    program = (await _get(hass, schlafen))["program"]
    assert program["saturday"] == program["sunday"] == DAY
    with pytest.raises(ServiceValidationError) as refused:
        await hass.services.async_call(DOMAIN, "copy_program", {"entity_id": schlafen}, blocking=True)
    assert refused.value.translation_key == "program_copy_nothing"


async def test_a_viewer_reads_a_programme(
    hass: HomeAssistant, rooms_kept: dict, hass_ws_client: WebSocketGenerator, hass_read_only_access_token: str
) -> None:
    """A user who may only view reads a room's programme as the card calls
    it, and may not write it."""
    room = rooms_kept["schlafen"]
    ws = await hass_ws_client(hass, hass_read_only_access_token)

    async def call(service: str, data: dict[str, Any]) -> dict[str, Any]:
        await ws.send_json_auto_id(
            {
                "type": "call_service",
                "domain": DOMAIN,
                "service": service,
                "service_data": data,
                "target": {"entity_id": room},
                "return_response": True,
            }
        )
        return await ws.receive_json()

    read = await call("get_program", {})
    assert read["success"], read
    assert set(read["result"]["response"][room]["program"]) == set(DAYS)
    written = await call("set_program", {"program": {"monday": DAY}})
    assert not written["success"]
    assert written["error"]["message"] == "Unauthorized", written


async def test_reading_needs_view(hass: HomeAssistant, rooms_kept: dict, hass_read_only_user: MockUser) -> None:
    """A user who may not view a room is refused its programme, and a copy
    from it; all rooms means those the user may view."""
    wohnen, schlafen = rooms_kept["wohnen"], rooms_kept["schlafen"]
    hass_read_only_user.mock_policy({"entities": {"entity_ids": {wohnen: True}}})
    context = Context(user_id=hass_read_only_user.id)
    with pytest.raises(Unauthorized):
        await hass.services.async_call(
            DOMAIN, "get_program", {"entity_id": schlafen}, blocking=True, return_response=True, context=context
        )
    answer = await hass.services.async_call(
        DOMAIN, "get_program", {"entity_id": "all"}, blocking=True, return_response=True, context=context
    )
    assert list(answer) == [wohnen]
    with pytest.raises(Unauthorized):
        await hass.services.async_call(
            DOMAIN, "copy_program", {"entity_id": wohnen, "source": schlafen}, blocking=True, context=context
        )


async def test_get_program_is_for_rooms(hass: HomeAssistant, rooms_kept: dict) -> None:
    """An entity that is not a Massimo room is refused, saying which."""
    with pytest.raises(ServiceValidationError) as refused:
        await hass.services.async_call(
            DOMAIN, "get_program", {"entity_id": "climate.elsewhere"}, blocking=True, return_response=True
        )
    assert refused.value.translation_key == "not_a_room"


async def test_program_changed_outlasts_a_reload(
    hass: HomeAssistant, massimo_server: Server, socket_enabled: None
) -> None:
    """When the programme was seen to change is kept across a reload where
    its tag stayed the same."""
    entry = await _setup(hass, massimo_server)
    room = _climate(hass, massimo_server, SCHLAFEN)
    before = (await _get(hass, room))["program"]
    try:
        answer = await _set(hass, room, program={"tuesday": DAY})
        await _until(hass, lambda: _attr(hass, room, "program_tag") == answer["etag"], "the new tag is shown")
        changed = _attr(hass, room, "program_changed")
        assert changed
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        assert _attr(hass, room, "program_tag") == answer["etag"]
        assert _attr(hass, room, "program_changed") == changed
    finally:
        await _set(hass, room, program={"tuesday": before["tuesday"]})
    await _unload(hass, entry)
