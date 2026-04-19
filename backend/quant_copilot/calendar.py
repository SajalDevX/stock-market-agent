from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from enum import StrEnum
from typing import Literal
from zoneinfo import ZoneInfo


class MarketSession(StrEnum):
    CLOSED = "closed"
    PREOPEN = "preopen"
    REGULAR = "regular"
    POSTCLOSE = "postclose"
    MUHURAT = "muhurat"


@dataclass(frozen=True)
class Holiday:
    on: date
    name: str
    muhurat_only: bool = False


# Standard NSE equity session times (IST)
PREOPEN_START = time(9, 0)
REGULAR_START = time(9, 15)
REGULAR_END = time(15, 30)
POSTCLOSE_END = time(16, 0)


class TradingCalendar:
    def __init__(self, holidays: list[Holiday], tz: str = "Asia/Kolkata") -> None:
        self._holidays = {h.on: h for h in holidays}
        self._tz = ZoneInfo(tz)

    @classmethod
    def from_records(cls, records: list[dict], tz: str = "Asia/Kolkata") -> "TradingCalendar":
        holidays = [
            Holiday(
                on=date.fromisoformat(r["date"]),
                name=r["name"],
                muhurat_only=bool(r.get("muhurat_only", False)),
            )
            for r in records
        ]
        return cls(holidays, tz=tz)

    def session_kind(self, on: date) -> Literal["weekend", "holiday", "muhurat", "regular"]:
        if on.weekday() >= 5:
            return "weekend"
        h = self._holidays.get(on)
        if h is None:
            return "regular"
        return "muhurat" if h.muhurat_only else "holiday"

    def is_closed(self, on: date) -> bool:
        kind = self.session_kind(on)
        return kind in ("weekend", "holiday")

    def classify(self, at: datetime) -> MarketSession:
        at = at.astimezone(self._tz)
        kind = self.session_kind(at.date())
        if kind in ("weekend", "holiday"):
            return MarketSession.CLOSED
        if kind == "muhurat":
            # v1 treats muhurat as a special separate session; polling skips it
            return MarketSession.MUHURAT
        t = at.time()
        if PREOPEN_START <= t < REGULAR_START:
            return MarketSession.PREOPEN
        if REGULAR_START <= t < REGULAR_END:
            return MarketSession.REGULAR
        if REGULAR_END <= t < POSTCLOSE_END:
            return MarketSession.POSTCLOSE
        return MarketSession.CLOSED
