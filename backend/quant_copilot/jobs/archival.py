from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from quant_copilot.data.fundamentals import FundamentalsService
from quant_copilot.logging_setup import get_logger
from quant_copilot.models import WatchlistEntry

log = get_logger(__name__)


async def nightly_archive(sm: async_sessionmaker[AsyncSession], fundamentals: FundamentalsService) -> None:
    async with sm() as s:
        tickers = (await s.execute(select(WatchlistEntry.ticker))).scalars().all()
    await fundamentals.snapshot_all(sorted(tickers))
    log.info("nightly_archive_done", n_tickers=len(tickers))
