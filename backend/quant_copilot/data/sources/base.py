from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

import pandas as pd


@dataclass(frozen=True)
class OhlcRequest:
    ticker: str        # internal symbol, e.g. "RELIANCE"
    exchange: str      # NSE | BSE
    interval: str      # 1d | 1h | 15m | 5m | 1m
    start: date
    end: date          # inclusive


class OhlcSource(Protocol):
    name: str

    async def fetch(self, req: OhlcRequest) -> pd.DataFrame:
        """Returns DataFrame indexed by UTC timestamp with columns open/high/low/close/volume."""
        ...
