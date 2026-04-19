from __future__ import annotations

import asyncio
from datetime import timedelta
from functools import partial

import pandas as pd
import yfinance as yf

from quant_copilot.data.sources.base import OhlcRequest, OhlcSource


def _yf_download(symbol: str, start: str, end: str, interval: str) -> pd.DataFrame:
    df = yf.download(
        symbol,
        start=start,
        end=end,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=False,
    )
    return df


class YFinanceSource:
    name = "yfinance"

    @staticmethod
    def _yf_symbol(ticker: str, exchange: str) -> str:
        suffix = {"NSE": ".NS", "BSE": ".BO"}[exchange]
        return f"{ticker}{suffix}"

    async def fetch(self, req: OhlcRequest) -> pd.DataFrame:
        sym = self._yf_symbol(req.ticker, req.exchange)
        # yfinance `end` is exclusive; push forward a day for inclusivity
        end = req.end + timedelta(days=1)
        loop = asyncio.get_running_loop()
        fn = partial(_yf_download, sym, str(req.start), str(end), req.interval)
        df = await loop.run_in_executor(None, fn)
        if df is None or df.empty:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        # yfinance may return multi-index columns when threads=True; flatten defensively
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        df = df[["open", "high", "low", "close", "volume"]]
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        return df
