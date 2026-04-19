from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from quant_copilot.agents.schemas import OrchestratorReport
from quant_copilot.models import Decision


async def persist_decision(
    sm: async_sessionmaker[AsyncSession],
    report: OrchestratorReport,
) -> int:
    async with sm() as s:
        d = Decision(
            ticker=report.ticker, timeframe=report.timeframe,
            verdict=report.verdict, conviction=report.conviction,
            entry=report.entry, stop=report.stop, target=report.target,
            ref_price=report.ref_price,
            created_at=datetime.now(tz=timezone.utc),
        )
        s.add(d)
        await s.commit()
        return d.id
