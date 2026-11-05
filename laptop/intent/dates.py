"""Europe/Paris date math for the demo script."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")

WEEKDAY_ZH = {
    0: "周一",
    1: "周二",
    2: "周三",
    3: "周四",
    4: "周五",
    5: "周六",
    6: "周日",
}


def parse_ts(ts: str) -> datetime:
    parsed = datetime.fromisoformat(ts)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=PARIS)
    return parsed.astimezone(PARIS)


def next_weekday(day: date, weekday: int) -> date:
    """Next `weekday` (Monday=0) strictly after `day`."""
    delta = (weekday - day.weekday()) % 7
    if delta == 0:
        delta = 7
    return day + timedelta(days=delta)


def epoch_ms(day: date, hour: int, minute: int = 0) -> int:
    moment = datetime(day.year, day.month, day.day, hour, minute, tzinfo=PARIS)
    return int(moment.timestamp() * 1000)


def add_minutes_ms(begin_ms: int, minutes: int) -> int:
    return begin_ms + minutes * 60 * 1000
