"""Week programmes as Massimo takes them (its docs/api-v1.md, the room's
programme): keyed by weekday, each day 1 to 13 switch points
``{"temp": 21, "until": "07:00"}``, times rising in steps of five minutes,
the last at 24:00, temperatures 4.5 to 30.5 °C in steps of 0.5.

They are checked here before they are sent, so that a mistake is told at
once and in the user's language, rather than as the server's refusal.
"""

from __future__ import annotations

from typing import Any

from homeassistant.exceptions import ServiceValidationError

from .const import DOMAIN

DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
MAX_POINTS = 13
MIN_TEMP = 4.5
MAX_TEMP = 30.5


def _refuse(key: str, **placeholders: object) -> ServiceValidationError:
    return ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key=key,
        translation_placeholders={k: str(v) for k, v in placeholders.items()},
    )


def _minutes(until: object, day: str) -> int:
    text = str(until)
    hours, sep, minutes = text.partition(":")
    if not sep or not hours.isdigit() or not minutes.isdigit() or len(minutes) != 2:
        raise _refuse("program_time", day=day, until=text)
    return int(hours) * 60 + int(minutes)


def check_days(days: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """The days given, checked and in Massimo's form; refused with a
    ServiceValidationError naming the day and what is wrong."""
    if not days:
        raise _refuse("program_empty")
    out: dict[str, list[dict[str, Any]]] = {}
    for day, points in days.items():
        if day not in DAYS:
            raise _refuse("program_day", day=day)
        if not isinstance(points, list) or not 1 <= len(points) <= MAX_POINTS:
            raise _refuse("program_points", day=day, max=MAX_POINTS)
        previous = 0
        checked = []
        for point in points:
            if not isinstance(point, dict) or "temp" not in point or "until" not in point:
                raise _refuse("program_point", day=day)
            try:
                temp = float(point["temp"])
            except TypeError, ValueError:
                raise _refuse("program_temp", day=day, temp=point["temp"]) from None
            if not MIN_TEMP <= temp <= MAX_TEMP or temp * 2 != int(temp * 2):
                raise _refuse("program_temp", day=day, temp=point["temp"])
            minutes = _minutes(point["until"], day)
            if minutes <= previous or minutes > 24 * 60 or minutes % 5:
                raise _refuse("program_time", day=day, until=point["until"])
            previous = minutes
            checked.append({"temp": temp, "until": f"{minutes // 60:02d}:{minutes % 60:02d}"})
        if previous != 24 * 60:
            raise _refuse("program_end", day=day)
        out[day] = checked
    return out


def days_of(program: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """The days of a programme as Massimo answers it, without its tag and
    flags."""
    return {day: program[day] for day in DAYS if isinstance(program.get(day), list)}


def copied(source: dict[str, Any], days: list[str] | None, to_days: list[str] | None) -> dict[str, Any]:
    """The days a copy writes: one day of the source onto the days to_days
    names, or the days named (all where none are) onto the same days."""
    for day in [*(days or []), *(to_days or [])]:
        if day not in DAYS:
            raise _refuse("program_day", day=day)
    program = days_of(source)
    if to_days:
        if not days or len(days) != 1:
            raise _refuse("program_copy_one_day")
        return {day: program[days[0]] for day in to_days}
    return {day: program[day] for day in days or DAYS if day in program}
