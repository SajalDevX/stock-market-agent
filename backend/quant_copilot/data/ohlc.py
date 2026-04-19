from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Sequence

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from quant_copilot.data.sources.base import OhlcRequest, OhlcSource
from quant_copilot.logging_setup import get_logger

log = get_logger(__name__)


class OhlcStore:
    def __init__(self, root: Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, ticker: str, interval: str, year: int) -> Path:
        d = self._root / ticker / interval
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{year}.parquet"

    def write(self, ticker: str, interval: str, df: pd.DataFrame) -> None:
        if df.empty:
            return
        by_year: dict[int, list[pd.DataFrame]] = {}
        for ts, row in df.iterrows():
            yr = ts.year
            by_year.setdefault(yr, []).append(row.to_frame().T)
        for yr, frames in by_year.items():
            chunk = pd.concat(frames)
            path = self._path(ticker, interval, yr)
            if path.exists():
                existing = pd.read_parquet(path)
                combined = pd.concat([existing, chunk])
                combined = combined[~combined.index.duplicated(keep="last")].sort_index()
            else:
                combined = chunk.sort_index()
            tbl = pa.Table.from_pandas(combined)
            pq.write_table(tbl, path)

    def read(self, ticker: str, interval: str, start: date, end: date) -> pd.DataFrame:
        years = range(start.year, end.year + 1)
        frames: list[pd.DataFrame] = []
        for yr in years:
            path = self._path(ticker, interval, yr)
            if path.exists():
                frames.append(pd.read_parquet(path))
        if not frames:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        df = pd.concat(frames).sort_index()
        mask = (df.index.date >= start) & (df.index.date <= end)
        return df.loc[mask]

    def coverage(self, ticker: str, interval: str, start: date, end: date) -> set[date]:
        df = self.read(ticker, interval, start, end)
        return {ts.date() for ts in df.index}


class OhlcService:
    def __init__(self, store: OhlcStore, sources: Sequence[OhlcSource]) -> None:
        self._store = store
        self._sources = list(sources)

    async def get_ohlc(self, ticker: str, exchange: str, interval: str, start: date, end: date) -> pd.DataFrame:
        cached = self._store.read(ticker, interval, start, end)
        # Simple coverage check: if cache has at least one bar per business day we trust it.
        covered = self._store.coverage(ticker, interval, start, end)
        expected_days = pd.bdate_range(start, end).date.tolist()
        missing = [d for d in expected_days if d not in covered]
        if not missing:
            return cached

        fetch_req = OhlcRequest(ticker=ticker, exchange=exchange, interval=interval, start=start, end=end)
        for src in self._sources:
            try:
                fresh = await src.fetch(fetch_req)
                if not fresh.empty:
                    self._store.write(ticker, interval, fresh)
                    return self._store.read(ticker, interval, start, end)
            except Exception as e:
                log.warning("ohlc_source_failed", source=src.name, error=str(e))
                continue
        return cached  # best-effort; may be empty
