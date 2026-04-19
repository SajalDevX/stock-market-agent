from datetime import date
from unittest.mock import AsyncMock

import pandas as pd
import pytest
from sqlalchemy import insert

from quant_copilot.data.layer import DataLayer
from quant_copilot.data.fundamentals import FundamentalsService
from quant_copilot.data.news import NewsService
from quant_copilot.data.ohlc import OhlcService, OhlcStore
from quant_copilot.data.surveillance import SurveillanceService
from quant_copilot.data.ticker_resolver import TickerResolver
from quant_copilot.clock import SystemClock
from quant_copilot.models import CorporateAction, Ticker


async def test_get_ohlc_adjusted_applies_split(sm, tmp_path):
    # Seed: ticker + split action
    async with sm() as s:
        s.add(Ticker(symbol="ZZZ", exchange="NSE", name="ZZZ"))
        s.add(CorporateAction(ticker="ZZZ", ex_date=date(2026, 4, 16),
                              kind="split", ratio_num=1, ratio_den=2))
        await s.commit()

    store = OhlcStore(tmp_path)
    src = AsyncMock(); src.name = "m"
    src.fetch.return_value = pd.DataFrame(
        {"open": [200, 201, 99, 101], "high": [201, 202, 100, 102],
         "low": [199, 200, 98, 100], "close": [200, 201, 100, 101],
         "volume": [1000, 1100, 2200, 2300]},
        index=pd.to_datetime(["2026-04-14", "2026-04-15", "2026-04-16", "2026-04-17"], utc=True),
    )
    ohlc_svc = OhlcService(store=store, sources=[src])

    layer = DataLayer(
        ohlc=ohlc_svc,
        fundamentals=FundamentalsService(sm=sm, html_fetcher=lambda t: "<html></html>"),
        news=NewsService(sm=sm, feed_fetcher=lambda url: b""),
        surveillance=SurveillanceService(sm=sm, asm_fetcher=lambda: []),
        resolver=TickerResolver(sm),
        sm=sm,
        clock=SystemClock(),
    )

    adj = await layer.get_ohlc_adjusted("ZZZ", "NSE", "1d", date(2026, 4, 14), date(2026, 4, 17))
    # Pre-split rows halved
    assert round(adj.loc["2026-04-14", "close"], 2) == 100.0
    # Post-split row unchanged
    assert adj.loc["2026-04-16", "close"] == 100.0
