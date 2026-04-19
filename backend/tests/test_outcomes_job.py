from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import select

from quant_copilot.data.layer import DataLayer
from quant_copilot.jobs.outcomes import compute_outcomes
from quant_copilot.models import Decision, DecisionOutcome, Ticker


async def _seed_decision(sm, created_at: datetime, ref_price: float = 100.0) -> int:
    async with sm() as s:
        s.add(Ticker(symbol="TEST", exchange="NSE", name="Test Co"))
        d = Decision(
            ticker="TEST", timeframe="swing", verdict="buy", conviction=60,
            entry=ref_price, stop=ref_price * 0.95, target=ref_price * 1.1,
            ref_price=ref_price, created_at=created_at,
        )
        s.add(d)
        await s.flush()
        did = d.id
        await s.commit()
    return did


def _ohlc_last(last_close: float, start: datetime, days: int):
    from unittest.mock import MagicMock
    idx = pd.date_range(start, periods=days, freq="B", tz="UTC")
    base = np.linspace(100, last_close, days)
    return pd.DataFrame({
        "open": base, "high": base * 1.01, "low": base * 0.99,
        "close": base, "volume": [1000] * days,
    }, index=idx)


async def test_compute_outcomes_writes_1d_7d_30d(sm):
    now = datetime.now(timezone.utc)
    created = now - timedelta(days=35)
    did = await _seed_decision(sm, created_at=created, ref_price=100.0)

    layer = AsyncMock(spec=DataLayer)
    # First call: 1d slice (just after 2 days). Simpler: always return a wide slice.
    # Return an OHLC that gives clear forward returns at 1d, 7d, 30d horizons.
    layer.get_ohlc_adjusted = AsyncMock(return_value=_ohlc_last(130.0, created, days=35))

    await compute_outcomes(sm=sm, layer=layer)

    async with sm() as s:
        rows = (await s.execute(select(DecisionOutcome).where(DecisionOutcome.decision_id == did))).scalars().all()
    horizons = sorted(r.horizon for r in rows)
    assert horizons == ["1d", "30d", "7d"]


async def test_compute_outcomes_skips_already_computed(sm):
    now = datetime.now(timezone.utc)
    created = now - timedelta(days=35)
    did = await _seed_decision(sm, created_at=created, ref_price=100.0)
    # Pre-seed a 7d outcome
    async with sm() as s:
        s.add(DecisionOutcome(decision_id=did, horizon="7d",
                              computed_at=now, return_pct=3.0))
        await s.commit()

    layer = AsyncMock(spec=DataLayer)
    layer.get_ohlc_adjusted = AsyncMock(return_value=_ohlc_last(130.0, created, days=35))
    await compute_outcomes(sm=sm, layer=layer)

    async with sm() as s:
        rows = (await s.execute(select(DecisionOutcome).where(DecisionOutcome.decision_id == did))).scalars().all()
    assert sorted(r.horizon for r in rows) == ["1d", "30d", "7d"]
    # Existing 7d row is untouched
    seven = next(r for r in rows if r.horizon == "7d")
    assert seven.return_pct == 3.0
