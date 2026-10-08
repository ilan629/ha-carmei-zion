"""Parse the public Carmei Zion feed and work out the times.

Pure Python with no Home Assistant imports, so it is easy to test.
All dates in the feed are local wall-clock times in the feed's time zone
(Asia/Jerusalem), whatever time zone the Home Assistant installation uses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
import re
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .const import DAY_NAMES, DEFAULT_TIMEZONE, SUPPORTED_SCHEMA_VERSION

_HHMM = re.compile(r"^(\d{1,2}):(\d{2})$")


class FeedError(ValueError):
    """The feed can't be used (bad format, unsupported version, ...)."""


class TestDataError(FeedError):
    """The feed currently holds TEST data, which must never drive automations."""


@dataclass(frozen=True)
class Schedule:
    """One week's schedule, as published."""

    parasha: str
    erev_date: date
    shabbat_date: date
    tz: ZoneInfo
    candle_lighting: str | None
    havdala: str | None
    shabbat: dict[str, tuple[str, str]] = field(default_factory=dict)  # key -> (day, "HH:MM")
    # (key, weekday name) -> "HH:MM", from the "coming week" table
    weekdays: dict[tuple[str, str], str] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    # ---- time helpers -------------------------------------------------
    def _at(self, day: date, hhmm: str | None) -> datetime | None:
        parsed = parse_hhmm(hhmm)
        if parsed is None:
            return None
        return datetime.combine(day, parsed, tzinfo=self.tz)

    def candle_lighting_at(self) -> datetime | None:
        """Friday candle lighting."""
        return self._at(self.erev_date, self.candle_lighting)

    def havdala_at(self) -> datetime | None:
        """Tzeit Shabbat / Havdala."""
        return self._at(self.shabbat_date, self.havdala)

    def shabbat_at(self, key: str) -> datetime | None:
        """A Friday/Shabbat row from the flyer."""
        item = self.shabbat.get(key)
        if not item:
            return None
        day, hhmm = item
        return self._at(self.erev_date if day == "friday" else self.shabbat_date, hhmm)

    def weekday_time(self, key: str, day_name: str) -> str | None:
        """'HH:MM' for a weekday prayer on that weekday, if the table has it."""
        return self.weekdays.get((key, day_name))

    def next_weekday_at(self, key: str, day_name: str, now: datetime) -> datetime | None:
        """Next time this weekday prayer happens (today if still ahead, otherwise next week)."""
        hhmm = self.weekday_time(key, day_name)
        if hhmm is None:
            return None
        target = _python_weekday(day_name)
        local_now = now.astimezone(self.tz)
        for offset in range(8):
            day = local_now.date() + timedelta(days=offset)
            if day.weekday() != target:
                continue
            when = self._at(day, hhmm)
            if when and when > local_now:
                return when
        return None

    def is_current(self, now: datetime) -> bool:
        """True while this schedule is for this week's Shabbat (or a later one).

        Weeks run Sunday-Saturday, so a new flyer is expected each week before Shabbat.
        """
        today = now.astimezone(self.tz).date()
        days_to_saturday = (5 - today.weekday()) % 7  # Mon=0 ... Sat=5, Sun=6
        this_weeks_shabbat = today + timedelta(days=days_to_saturday)
        return self.shabbat_date >= this_weeks_shabbat


def parse_hhmm(value: Any) -> time | None:
    """'7:05' / '19:05' -> time, anything else -> None."""
    if not isinstance(value, str):
        return None
    match = _HHMM.match(value.strip())
    if not match:
        return None
    hour, minute = int(match.group(1)), int(match.group(2))
    if hour > 23 or minute > 59:
        return None
    return time(hour, minute)


def _python_weekday(day_name: str) -> int:
    # Python: Monday=0 ... Sunday=6. Feed day names are Sunday..Friday.
    return {"Sunday": 6, "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4}[day_name]


def _parse_date(value: Any, name: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as err:
        raise FeedError(f"bad {name}: {value!r}") from err


def parse_feed(data: Any) -> Schedule:
    """Validate the feed JSON and turn it into a Schedule.

    Raises TestDataError for TEST data and FeedError for anything unusable,
    so bad data never replaces a good schedule.
    """
    if not isinstance(data, dict):
        raise FeedError("feed is not a JSON object")

    version = data.get("schema_version", 1)
    if not isinstance(version, int) or version > SUPPORTED_SCHEMA_VERSION:
        raise FeedError(
            f"feed format version {version} is newer than this integration understands "
            f"(up to {SUPPORTED_SCHEMA_VERSION}); please update Carmei Zion Times in HACS"
        )
    if data.get("test"):
        raise TestDataError("the feed currently holds TEST data, not real times")

    try:
        tz = ZoneInfo(str(data.get("timezone") or DEFAULT_TIMEZONE))
    except (ZoneInfoNotFoundError, ValueError) as err:
        raise FeedError(f"unknown timezone {data.get('timezone')!r}") from err

    erev = _parse_date(data.get("erev_date"), "erev_date")
    shabbat = _parse_date(data.get("shabbat_date"), "shabbat_date")
    if not timedelta(days=1) <= shabbat - erev <= timedelta(days=2):
        raise FeedError(f"erev_date {erev} doesn't fit shabbat_date {shabbat}")

    shabbat_items: dict[str, tuple[str, str]] = {}
    for item in data.get("shabbat") or []:
        if not isinstance(item, dict):
            continue
        key, day, hhmm = item.get("key"), item.get("day"), item.get("time")
        if isinstance(key, str) and day in ("friday", "saturday") and parse_hhmm(hhmm):
            shabbat_items.setdefault(key, (day, hhmm.strip()))

    weekdays: dict[tuple[str, str], str] = {}
    for row in data.get("weekdays") or []:
        if not isinstance(row, dict):
            continue
        key, hhmm, days = row.get("key"), row.get("time"), row.get("days")
        if not isinstance(key, str) or not parse_hhmm(hhmm) or not isinstance(days, list):
            continue
        for day in days:
            if day in DAY_NAMES:
                weekdays.setdefault((key, day), hhmm.strip())

    candle = data.get("candle_lighting")
    havdala = data.get("havdala")
    if not parse_hhmm(candle) or not parse_hhmm(havdala):
        raise FeedError("candle lighting / havdala missing")

    return Schedule(
        parasha=str(data.get("parasha") or ""),
        erev_date=erev,
        shabbat_date=shabbat,
        tz=tz,
        candle_lighting=candle.strip(),
        havdala=havdala.strip(),
        shabbat=shabbat_items,
        weekdays=weekdays,
        raw=data,
    )
