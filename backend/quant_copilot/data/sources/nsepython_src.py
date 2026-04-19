from __future__ import annotations

import asyncio
from functools import partial

import pandas as pd

from quant_copilot.data.sources.base import OhlcRequest


class NsePythonSource:
    name = "nsepython"

    async def fetch(self, req: OhlcRequest) -> pd.DataFrame:
        from nsepython import equity_history  # local import so tests can patch

        if req.interval != "1d":
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        start = req.start.strftime("%d-%m-%Y")
        end = req.end.strftime("%d-%m-%Y")

        loop = asyncio.get_running_loop()
        fn = partial(equity_history, req.ticker, "EQ", start, end)
        raw = await loop.run_in_executor(None, fn)
        if raw is None or len(raw) == 0:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        df = pd.DataFrame(raw)
        # nsepython returns columns like CH_OPENING_PRICE, CH_TRADE_HIGH_PRICE, etc.
        df = df.rename(columns={
            "CH_TIMESTAMP": "ts",
            "CH_OPENING_PRICE": "open",
            "CH_TRADE_HIGH_PRICE": "high",
            "CH_TRADE_LOW_PRICE": "low",
            "CH_CLOSING_PRICE": "close",
            "CH_TOT_TRADED_QTY": "volume",
        })
        df["ts"] = pd.to_datetime(df["ts"], utc=True)
        df = df.set_index("ts").sort_index()
        return df[["open", "high", "low", "close", "volume"]]
