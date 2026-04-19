from datetime import date
from unittest.mock import AsyncMock

import pandas as pd

from quant_copilot.data.layer import DataLayer
from quant_copilot.data.fundamentals import FundamentalsService
from quant_copilot.data.news import NewsService
from quant_copilot.data.ohlc import OhlcService, OhlcStore
from quant_copilot.data.surveillance import SurveillanceService
from quant_copilot.data.ticker_resolver import TickerResolver
from quant_copilot.clock import SystemClock
from quant_copilot.models import Ticker, TickerAlias


async def test_end_to_end_smoke(sm, tmp_path):
    async with sm() as s:
        s.add(Ticker(symbol="RELIANCE", exchange="NSE", name="Reliance Industries Ltd"))
        s.add(TickerAlias(ticker="RELIANCE", alias="Reliance Industries", kind="name"))
        await s.commit()

    src = AsyncMock(); src.name = "m"
    src.fetch.return_value = pd.DataFrame(
        {"open":[2800,2810],"high":[2820,2830],"low":[2790,2800],"close":[2810,2825],"volume":[1,2]},
        index=pd.to_datetime(["2026-04-14","2026-04-15"], utc=True),
    )
    ohlc = OhlcService(OhlcStore(tmp_path), [src])

    async def _html(t):
        return "<html><div id='top-ratios'><ul><li><span class='name'>Stock P/E</span><span class='value'>28</span></li></ul></div></html>"

    fund = FundamentalsService(sm=sm, html_fetcher=_html)
    news = NewsService(sm=sm, feed_fetcher=lambda url: b"""<?xml version='1.0'?><rss><channel><item><title>Reliance Industries rallies</title><link>http://x</link><description>d</description><pubDate>Fri, 17 Apr 2026 15:00:00 GMT</pubDate></item></channel></rss>""")
    layer = DataLayer(
        ohlc=ohlc, fundamentals=fund, news=news,
        surveillance=SurveillanceService(sm=sm, asm_fetcher=lambda: []),
        resolver=TickerResolver(sm), sm=sm, clock=SystemClock(),
    )

    df = await layer.get_ohlc_adjusted("RELIANCE", "NSE", "1d", date(2026, 4, 14), date(2026, 4, 15))
    assert len(df) == 2

    f = await layer.fundamentals.get("RELIANCE")
    assert f["pe"] == 28.0

    n = await layer.news.ingest(["http://example.com/rss"])
    assert n == 1
    items = await layer.news.get_for_ticker("RELIANCE", lookback_days=30)
    assert len(items) == 1
