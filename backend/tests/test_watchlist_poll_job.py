from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from quant_copilot.agents.news import NewsAgent
from quant_copilot.agents.technical import TechnicalAgent
from quant_copilot.jobs.watchlist_poll import poll_watchlist
from quant_copilot.models import AgentReport, Ticker, WatchlistEntry


async def _seed(sm):
    async with sm() as s:
        s.add_all([
            Ticker(symbol="RELIANCE", exchange="NSE", name="R"),
            Ticker(symbol="HDFCBANK", exchange="NSE", name="H"),
        ])
        s.add_all([
            WatchlistEntry(ticker="RELIANCE", added_at=datetime.now(timezone.utc)),
            WatchlistEntry(ticker="HDFCBANK", added_at=datetime.now(timezone.utc)),
        ])
        await s.commit()


async def test_poll_runs_news_and_technical_per_watchlist_ticker(sm):
    await _seed(sm)
    tech = MagicMock(spec=TechnicalAgent)
    tech.analyze = AsyncMock(return_value=MagicMock(model_dump_json=lambda: "{}"))
    news = MagicMock(spec=NewsAgent)
    news.analyze = AsyncMock(return_value=MagicMock(model_dump_json=lambda: "{}"))

    n = await poll_watchlist(sm=sm, technical=tech, news=news, news_ingest=None)
    assert n == 2
    assert tech.analyze.await_count == 2
    assert news.analyze.await_count == 2
    # Each call targets one of the watchlist tickers
    called_tickers = sorted([c.kwargs["ticker"] for c in tech.analyze.await_args_list])
    assert called_tickers == ["HDFCBANK", "RELIANCE"]


async def test_poll_swallows_per_ticker_errors(sm):
    await _seed(sm)
    tech = MagicMock(spec=TechnicalAgent)
    tech.analyze = AsyncMock(side_effect=[RuntimeError("boom"), MagicMock()])
    news = MagicMock(spec=NewsAgent)
    news.analyze = AsyncMock(return_value=MagicMock())
    n = await poll_watchlist(sm=sm, technical=tech, news=news, news_ingest=None)
    # Both tickers attempted; one succeeded
    assert n == 1
