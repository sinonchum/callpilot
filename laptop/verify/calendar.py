"""Programmatic check, the same idea as reading the calendar provider."""

from __future__ import annotations

import re

from contracts.models import Action, CalendarRow, VerifyResult

ROW_RE = re.compile(
    r"title=(?P<title>.*?), dtstart=(?P<dtstart>\d+), dtend=(?P<dtend>\d+), eventLocation=(?P<eventLocation>.*)$"
)
TOLERANCE_MS = 60_000
CALENDAR_URI = "content://com.android.calendar/events"


def parse_content_query(stdout: str) -> list[CalendarRow]:
    rows: list[CalendarRow] = []
    for line in stdout.splitlines():
        match = ROW_RE.search(line.strip())
        if not match:
            continue
        rows.append(
            CalendarRow(
                title=match.group("title"),
                dtstart=int(match.group("dtstart")),
                dtend=int(match.group("dtend")),
                eventLocation=match.group("eventLocation"),
            )
        )
    return rows


def format_rows(rows: list[CalendarRow]) -> str:
    if not rows:
        return "No result found."
    lines = []
    for index, row in enumerate(rows):
        lines.append(
            "Row: {i} _id={n}, title={title}, dtstart={start}, dtend={end}, eventLocation={loc}".format(
                i=index,
                n=index + 1,
                title=row.title,
                start=row.dtstart,
                end=row.dtend or 0,
                loc=row.eventLocation,
            )
        )
    return "\n".join(lines)


def verify_action(action: Action, rows: list[CalendarRow], ts: str, call_id: str) -> VerifyResult:
    if action.kind == "note.create":
        return VerifyResult(
            ts=ts,
            call_id=call_id,
            action_id=action.action_id,
            method="panel",
            matched=bool(action.payload.get("text")),
        )
    if action.kind == "calendar.delete":
        title, begin = _match_keys(action)
        gone = _find(rows, title, begin, "") is None
        return VerifyResult(
            ts=ts,
            call_id=call_id,
            action_id=action.action_id,
            method="content_query",
            uri=CALENDAR_URI,
            matched=gone,
        )
    title = str(action.payload.get("title") or "")
    begin = int(action.payload["beginTime"])
    location = str(action.payload.get("eventLocation") or "")
    found = _find(rows, title, begin, location)
    return VerifyResult(
        ts=ts,
        call_id=call_id,
        action_id=action.action_id,
        method="content_query",
        uri=CALENDAR_URI,
        matched=found is not None,
        row=found,
    )


def _match_keys(action: Action) -> tuple[str, int]:
    match = action.payload.get("match") or {}
    return str(match.get("title") or ""), int(match["beginTime"])


def _find(rows: list[CalendarRow], title: str, begin: int, location: str) -> CalendarRow | None:
    for row in rows:
        if row.title != title:
            continue
        if abs(row.dtstart - begin) > TOLERANCE_MS:
            continue
        if location and location not in (row.eventLocation or ""):
            continue
        return row
    return None
