from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from quant_copilot.models import AgentCall


class BudgetExceeded(RuntimeError):
    pass


class BudgetGuard:
    def __init__(self, sm: async_sessionmaker[AsyncSession], daily_cap_inr: float) -> None:
        self._sm = sm
        self._cap = float(daily_cap_inr)

    async def spent_today(self) -> float:
        now = datetime.now(tz=timezone.utc)
        start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        async with self._sm() as s:
            total = (
                await s.execute(
                    select(func.coalesce(func.sum(AgentCall.cost_inr), 0.0))
                    .where(AgentCall.created_at >= start)
                )
            ).scalar_one()
        return float(total or 0.0)

    async def check(self, projected_cost_inr: float) -> None:
        spent = await self.spent_today()
        if spent + projected_cost_inr > self._cap:
            raise BudgetExceeded(
                f"Daily LLM budget exceeded: spent ₹{spent:.2f}, projecting ₹{projected_cost_inr:.2f}, cap ₹{self._cap:.2f}"
            )
