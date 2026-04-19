from __future__ import annotations

from typing import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from quant_copilot.agents.news import NewsAgent
from quant_copilot.agents.technical import TechnicalAgent
from quant_copilot.logging_setup import get_logger
from quant_copilot.models import Ticker, WatchlistEntry

log = get_logger(__name__)


async def poll_watchlist(
    sm: async_sessionmaker[AsyncSession],
    technical: TechnicalAgent,
    news: NewsAgent,
    news_ingest: Callable[[], object] | None = None,
) -> int:
    """Lightweight pass over each watchlist ticker.

    - Optionally refreshes RSS feeds via `news_ingest` (no-op if None).
    - Runs the Technical and News agents on each ticker.
    - Per-ticker failures are logged and swallowed so one bad ticker can't
      kill the whole pass. Returns the number of tickers that completed
      successfully.
    """
    if news_ingest is not None:
        try:
            await news_ingest()
        except Exception as e:
            log.warning("watchlist_news_ingest_failed", error=str(e))

    async with sm() as s:
        entries = (await s.execute(
            select(WatchlistEntry, Ticker)
            .join(Ticker, WatchlistEntry.ticker == Ticker.symbol)
        )).all()

    ok = 0
    for entry, t in entries:
        try:
            await technical.analyze(ticker=t.symbol, exchange=t.exchange, timeframe="swing")
            await news.analyze(ticker=t.symbol, lookback_days=7)
            ok += 1
        except Exception as e:
            log.warning("watchlist_ticker_failed", ticker=t.symbol, error=str(e))
            continue
    return ok
