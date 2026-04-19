from datetime import date
from unittest.mock import AsyncMock

import pandas as pd
import pytest

from quant_copilot.data.ohlc import OhlcStore, OhlcService
from quant_copilot.data.sources.base import OhlcRequest


def _bars(dates, closes):
    return pd.DataFrame(
        {
            "open": closes, "high": closes, "low": closes,
            "close": closes, "volume": [100] * len(closes),
        },
        index=pd.to_datetime(dates, utc=True),
    )


async def test_store_writes_and_reads_parquet(tmp_path):
    store = OhlcStore(tmp_path)
    df = _bars(["2026-04-14", "2026-04-15"], [100.0, 101.0])
    store.write("RELIANCE", "1d", df)
    got = store.read("RELIANCE", "1d", date(2026, 4, 14), date(2026, 4, 15))
    assert list(got["close"]) == [100.0, 101.0]


async def test_service_fills_cache_from_primary_source(tmp_path):
    store = OhlcStore(tmp_path)
    primary = AsyncMock()
    primary.name = "primary"
    primary.fetch.return_value = _bars(["2026-04-14", "2026-04-15"], [100.0, 101.0])

    svc = OhlcService(store=store, sources=[primary])
    df = await svc.get_ohlc("RELIANCE", "NSE", "1d", date(2026, 4, 14), date(2026, 4, 15))
    assert len(df) == 2
    primary.fetch.assert_awaited_once()
    # Second call served from cache
    primary.fetch.reset_mock()
    df2 = await svc.get_ohlc("RELIANCE", "NSE", "1d", date(2026, 4, 14), date(2026, 4, 15))
    assert len(df2) == 2
    primary.fetch.assert_not_awaited()


async def test_service_fallback_on_primary_failure(tmp_path):
    store = OhlcStore(tmp_path)
    primary = AsyncMock(); primary.name = "primary"
    primary.fetch.side_effect = RuntimeError("boom")
    secondary = AsyncMock(); secondary.name = "secondary"
    secondary.fetch.return_value = _bars(["2026-04-14"], [100.0])

    svc = OhlcService(store=store, sources=[primary, secondary])
    df = await svc.get_ohlc("RELIANCE", "NSE", "1d", date(2026, 4, 14), date(2026, 4, 14))
    assert len(df) == 1
    secondary.fetch.assert_awaited_once()
