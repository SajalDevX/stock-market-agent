from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from functools import partial

import pandas as pd

from quant_copilot.data.sources.base import OhlcRequest


class NsetoolsSource:
    name = "nsetools"

    async def fetch(self, req: OhlcRequest) -> pd.DataFrame:
        """nsetools has no history API; this returns an empty frame.

        Kept in the chain purely so that `get_quote` can still be used by the
        quote-snapshot helper in DataLayer (added in Task 15).
        """
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    async def quote(self, ticker: str) -> dict:
        from nsetools import Nse  # local import
        loop = asyncio.get_running_loop()
        nse = Nse()
        fn = partial(nse.get_quote, ticker.lower())
        q = await loop.run_in_executor(None, fn)
        return {
            "ticker": ticker,
            "ltp": float(q["lastPrice"]),
            "asof": datetime.now(tz=timezone.utc).isoformat(),
        }
