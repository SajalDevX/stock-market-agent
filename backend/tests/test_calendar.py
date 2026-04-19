import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from quant_copilot.calendar import TradingCalendar, MarketSession


FIX = Path(__file__).parent / "fixtures" / "nse_holidays_2026.json"


def _load_cal() -> TradingCalendar:
    data = json.loads(FIX.read_text())
    return TradingCalendar.from_records(data["holidays"], tz="Asia/Kolkata")


def test_republic_day_is_closed():
    cal = _load_cal()
    assert cal.is_closed(date(2026, 1, 26)) is True


def test_regular_weekday_is_open():
    cal = _load_cal()
    assert cal.is_closed(date(2026, 4, 20)) is False  # Monday


def test_saturday_sunday_closed():
    cal = _load_cal()
    assert cal.is_closed(date(2026, 4, 18)) is True  # Sat
    assert cal.is_closed(date(2026, 4, 19)) is True  # Sun


def test_muhurat_day_classified_special():
    cal = _load_cal()
    assert cal.session_kind(date(2026, 11, 9)) == "muhurat"


def test_market_session_open_during_regular_hours():
    cal = _load_cal()
    tz = ZoneInfo("Asia/Kolkata")
    t = datetime(2026, 4, 20, 10, 30, tzinfo=tz)
    s = cal.classify(t)
    assert s == MarketSession.REGULAR


def test_market_session_preopen():
    cal = _load_cal()
    tz = ZoneInfo("Asia/Kolkata")
    t = datetime(2026, 4, 20, 9, 5, tzinfo=tz)
    assert cal.classify(t) == MarketSession.PREOPEN


def test_market_session_closed_after_hours():
    cal = _load_cal()
    tz = ZoneInfo("Asia/Kolkata")
    t = datetime(2026, 4, 20, 18, 0, tzinfo=tz)
    assert cal.classify(t) == MarketSession.CLOSED


def test_market_session_closed_on_holiday():
    cal = _load_cal()
    tz = ZoneInfo("Asia/Kolkata")
    t = datetime(2026, 1, 26, 10, 30, tzinfo=tz)
    assert cal.classify(t) == MarketSession.CLOSED
