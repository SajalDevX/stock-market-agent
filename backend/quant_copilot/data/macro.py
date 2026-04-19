from __future__ import annotations

import asyncio
from functools import partial

import pandas as pd
import yfinance as yf

from quant_copilot.logging_setup import get_logger

log = get_logger(__name__)


SYMBOLS = {
    "nifty":    "^NSEI",
    "banknifty": "^NSEBANK",
    "dow":      "^DJI",
    "nasdaq":   "^IXIC",
    "nikkei":   "^N225",
    "crude":    "CL=F",
    "usdinr":   "INR=X",
}


def _download(symbol: str) -> pd.DataFrame:
    df = yf.download(symbol, period="5d", interval="1d", auto_adjust=False,
                     progress=False, threads=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns={"Open": "open", "High": "high", "Low": "low",
                            "Close": "close", "Volume": "volume"})
    return df


class MacroData:
    async def _fetch_one(self, symbol: str) -> pd.DataFrame:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(_download, symbol))

    async def snapshot(self) -> dict:
        tasks = {k: self._fetch_one(v) for k, v in SYMBOLS.items()}
        results_list = await asyncio.gather(*tasks.values(), return_exceptions=True)
        dfs: dict[str, pd.DataFrame] = {}
        for k, v in zip(tasks.keys(), results_list):
            if isinstance(v, Exception):
                log.warning("macro_fetch_failed", key=k, error=str(v))
                continue
            dfs[k] = v

        def _entry(df: pd.DataFrame | None) -> dict:
            if df is None or df.empty or "close" not in df.columns:
                return {"close": None, "change_pct": None}
            if len(df) >= 2:
                prev, last = float(df["close"].iloc[-2]), float(df["close"].iloc[-1])
                ch = (last - prev) / prev * 100.0 if prev else 0.0
            else:
                last = float(df["close"].iloc[-1])
                ch = 0.0
            return {"close": round(last, 4), "change_pct": round(ch, 4)}

        return {
            "nifty": _entry(dfs.get("nifty")),
            "banknifty": _entry(dfs.get("banknifty")),
            "global": {
                "dow": _entry(dfs.get("dow")),
                "nasdaq": _entry(dfs.get("nasdaq")),
                "nikkei": _entry(dfs.get("nikkei")),
                "crude": _entry(dfs.get("crude")),
            },
            "fx": {"usdinr": _entry(dfs.get("usdinr"))},
        }
