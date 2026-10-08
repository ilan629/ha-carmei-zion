"""Date/time logic (no Home Assistant needed)."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys
import types

import pytest

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "carmei_zion"
FEED = json.loads((Path(__file__).parent / "feed_bereshit.json").read_text(encoding="utf-8"))


def _load():
    """Import schedule.py without running the integration's __init__ (which needs Home Assistant)."""
    pkg = types.ModuleType("cz_pure")
    pkg.__path__ = [str(ROOT)]
    sys.modules["cz_pure"] = pkg
    for name in ("const", "schedule"):
        spec = importlib.util.spec_from_file_location(f"cz_pure.{name}", ROOT / f"{name}.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
    return sys.modules["cz_pure.schedule"]


sched = _load()
UTC = timezone.utc


def iso(dt):
    return dt.isoformat() if dt else None


def test_shabbat_times_are_israel_local():
    s = sched.parse_feed(FEED)
    assert s.parasha == "שבת פרשת בראשית"
    assert iso(s.candle_lighting_at()) == "2026-10-09T17:56:00+03:00"
    assert iso(s.havdala_at()) == "2026-10-10T18:52:00+03:00"
    assert iso(s.shabbat_at("mincha_kabbalat_shabbat")) == "2026-10-09T18:01:00+03:00"
    assert iso(s.shabbat_at("shacharit_1")) == "2026-10-10T07:00:00+03:00"
    assert s.shabbat_at("plag_hamincha") is None  # not on this week's flyer
    assert s.shabbat_at("daf_yomi") is None


def test_winter_time_offset():
    """After the clocks change (Oct 25 2026) times must be +02:00, not +03:00."""
    feed = dict(FEED, erev_date="2026-10-30", shabbat_date="2026-10-31")
    assert iso(sched.parse_feed(feed).candle_lighting_at()) == "2026-10-30T17:56:00+02:00"


def test_next_weekday_prayer():
    s = sched.parse_feed(FEED)
    sat_night = datetime(2026, 10, 10, 21, 0, tzinfo=UTC)  # Sunday 00:00 Israel
    assert iso(s.next_weekday_at("shacharit_1", "Sunday", sat_night)) == "2026-10-11T06:10:00+03:00"
    assert iso(s.next_weekday_at("shacharit_1", "Thursday", sat_night)) == "2026-10-15T06:15:00+03:00"
    assert iso(s.next_weekday_at("mincha", "Monday", sat_night)) == "2026-10-12T13:30:00+03:00"
    assert s.next_weekday_at("mincha", "Friday", sat_night) is None  # no Friday Mincha in the table
    # Sunday 14:00 Israel: today's Mincha (13:30) has passed -> next Sunday.
    sun_afternoon = datetime(2026, 10, 11, 11, 0, tzinfo=UTC)
    assert iso(s.next_weekday_at("mincha", "Sunday", sun_afternoon)) == "2026-10-18T13:30:00+03:00"
    assert iso(s.next_weekday_at("maariv", "Sunday", sun_afternoon)) == "2026-10-11T20:15:00+03:00"


def test_is_current_follows_israel_week():
    s = sched.parse_feed(FEED)
    assert s.is_current(datetime(2026, 10, 8, 20, 0, tzinfo=UTC))  # Thu night
    assert s.is_current(datetime(2026, 10, 10, 20, 59, tzinfo=UTC))  # Sat 23:59 Israel
    assert not s.is_current(datetime(2026, 10, 10, 21, 0, tzinfo=UTC))  # Sun 00:00 Israel: new week


def test_test_data_is_refused():
    with pytest.raises(sched.TestDataError):
        sched.parse_feed(dict(FEED, test=True))


def test_newer_format_is_refused_with_a_clear_message():
    with pytest.raises(sched.FeedError, match="update Carmei Zion Times"):
        sched.parse_feed(dict(FEED, schema_version=2))


def test_original_format_without_version_still_works():
    feed = {k: v for k, v in FEED.items() if k not in ("schema_version", "timezone")}
    assert iso(sched.parse_feed(feed).candle_lighting_at()) == "2026-10-09T17:56:00+03:00"


@pytest.mark.parametrize(
    "change",
    [
        {"erev_date": "2026-10-01"},
        {"shabbat_date": "not a date"},
        {"candle_lighting": "25:00"},
        {"havdala": None},
        {"timezone": "Mars/Base"},
    ],
)
def test_bad_feeds_are_refused(change):
    with pytest.raises(sched.FeedError):
        sched.parse_feed(dict(FEED, **change))


def test_junk_rows_are_skipped():
    feed = copy.deepcopy(FEED)
    feed["shabbat"] += ["junk", {"key": "shkia", "day": "friday", "time": "99:99"}, {"key": "x", "day": "sunday", "time": "10:00"}]
    feed["weekdays"].append({"key": "mincha", "days": ["Saturday"], "time": "13:30"})
    s = sched.parse_feed(feed)
    assert iso(s.shabbat_at("shkia")) == "2026-10-09T18:16:00+03:00"  # first good row wins
    assert "x" not in s.shabbat
