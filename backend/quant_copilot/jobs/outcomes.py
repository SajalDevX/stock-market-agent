from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from quant_copilot.data.layer import DataLayer
from quant_copilot.logging_setup import get_logger
from quant_copilot.models import Decision, DecisionOutcome

log = get_logger(__name__)


HORIZONS_DAYS = {"1d": 1, "7d": 7, "30d": 30}


async def compute_outcomes(sm: async_sessionmaker[AsyncSession], layer: DataLayer) -> int:
    """For each Decision, fill in any DecisionOutcome rows that are due and not yet computed."""
    now = datetime.now(tz=timezone.utc)
    written = 0

    async with sm() as s:
        decisions = (await s.execute(select(Decision))).scalars().all()
        existing = (await s.execute(select(DecisionOutcome.decision_id, DecisionOutcome.horizon))).all()
    have: set[tuple[int, str]] = {(did, h) for did, h in existing}

    for d in decisions:
        for horizon, days in HORIZONS_DAYS.items():
            if (d.id, horizon) in have:
                continue
            created_at = d.created_at if d.created_at.tzinfo else d.created_at.replace(tzinfo=timezone.utc)
            target_date = created_at + timedelta(days=days)
            if target_date > now:
                continue  # horizon hasn't arrived yet
            # Fetch OHLC covering created_at .. target_date; take the first close on/after target_date
            start = created_at.date()
            end = (target_date + timedelta(days=2)).date()  # small buffer
            try:
                df = await layer.get_ohlc_adjusted(d.ticker, "NSE", "1d", start, end)
            except Exception as e:
                log.warning("outcomes_fetch_failed", ticker=d.ticker, error=str(e))
                continue
            if df is None or df.empty or "close" not in df.columns:
                continue
            # Find the first bar on/after target_date
            eligible = df.loc[df.index.date >= target_date.date()]
            if eligible.empty:
                continue
            close = float(eligible["close"].iloc[0])
            if d.ref_price <= 0:
                continue
            return_pct = (close - d.ref_price) / d.ref_price * 100.0
            async with sm() as s:
                s.add(DecisionOutcome(
                    decision_id=d.id, horizon=horizon,
                    computed_at=now, return_pct=round(return_pct, 4),
                ))
                await s.commit()
            written += 1
    return written
