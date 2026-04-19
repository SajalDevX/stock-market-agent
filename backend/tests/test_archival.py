from datetime import date
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from quant_copilot.jobs.archival import nightly_archive
from quant_copilot.models import FundamentalsSnapshot, Ticker, WatchlistEntry


async def test_nightly_archive_snapshots_watchlist_fundamentals(sm):
    from datetime import datetime, timezone
    async with sm() as s:
        s.add(Ticker(symbol="RELIANCE", exchange="NSE", name="Reliance"))
        s.add(Ticker(symbol="HDFCBANK", exchange="NSE", name="HDFC Bank"))
        s.add(WatchlistEntry(ticker="RELIANCE", added_at=datetime.now(tz=timezone.utc)))
        s.add(WatchlistEntry(ticker="HDFCBANK", added_at=datetime.now(tz=timezone.utc)))
        await s.commit()

    fund = AsyncMock()
    fund.snapshot_all = AsyncMock()

    await nightly_archive(sm=sm, fundamentals=fund)

    fund.snapshot_all.assert_awaited_once()
    called_with = fund.snapshot_all.await_args[0][0]
    assert sorted(called_with) == ["HDFCBANK", "RELIANCE"]
