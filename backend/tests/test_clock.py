from datetime import datetime
from zoneinfo import ZoneInfo

from freezegun import freeze_time

from quant_copilot.clock import Clock, SystemClock, FrozenClock


def test_system_clock_returns_ist_now():
    with freeze_time("2026-04-19T10:30:00+05:30"):
        c: Clock = SystemClock("Asia/Kolkata")
        now = c.now()
        assert now.tzinfo is not None
        assert now.utcoffset().total_seconds() == 19800  # +05:30


def test_frozen_clock_fixed_value():
    fixed = datetime(2023, 6, 15, 11, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    c: Clock = FrozenClock(fixed)
    assert c.now() == fixed
    assert c.today().isoformat() == "2023-06-15"


def test_resolve_asof_none_uses_now():
    fixed = datetime(2024, 1, 2, 9, 30, tzinfo=ZoneInfo("Asia/Kolkata"))
    c = FrozenClock(fixed)
    assert c.resolve_asof(None) == fixed
    explicit = datetime(2024, 1, 1, tzinfo=ZoneInfo("Asia/Kolkata"))
    assert c.resolve_asof(explicit) == explicit
