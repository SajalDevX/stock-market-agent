from __future__ import annotations

from datetime import date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo


class Clock(Protocol):
    def now(self) -> datetime: ...
    def today(self) -> date: ...
    def resolve_asof(self, asof: datetime | None) -> datetime: ...


class SystemClock:
    def __init__(self, tz: str = "Asia/Kolkata") -> None:
        self._tz = ZoneInfo(tz)

    def now(self) -> datetime:
        return datetime.now(self._tz)

    def today(self) -> date:
        return self.now().date()

    def resolve_asof(self, asof: datetime | None) -> datetime:
        if asof is None:
            return self.now()
        if asof.tzinfo is None:
            return asof.replace(tzinfo=self._tz)
        return asof.astimezone(self._tz)


class FrozenClock:
    """Used in tests and backtests."""

    def __init__(self, at: datetime) -> None:
        if at.tzinfo is None:
            raise ValueError("FrozenClock requires timezone-aware datetime")
        self._at = at

    def now(self) -> datetime:
        return self._at

    def today(self) -> date:
        return self._at.date()

    def resolve_asof(self, asof: datetime | None) -> datetime:
        return asof if asof is not None else self._at
