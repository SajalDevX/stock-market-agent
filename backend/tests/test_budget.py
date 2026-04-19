from datetime import datetime, timedelta, timezone

import pytest

from quant_copilot.agents.budget import BudgetGuard, BudgetExceeded
from quant_copilot.models import AgentCall


async def _seed_calls(sm, costs_today: list[float], costs_yesterday: list[float] = ()):
    now = datetime.now(tz=timezone.utc)
    yesterday = now - timedelta(days=1, hours=6)
    async with sm() as s:
        for c in costs_today:
            s.add(AgentCall(agent="x", input_hash="h", model="m",
                            input_tokens=1, output_tokens=1, cost_inr=c,
                            latency_ms=1, error=None, created_at=now))
        for c in costs_yesterday:
            s.add(AgentCall(agent="x", input_hash="h", model="m",
                            input_tokens=1, output_tokens=1, cost_inr=c,
                            latency_ms=1, error=None, created_at=yesterday))
        await s.commit()


async def test_spent_today_sums_only_todays_rows(sm):
    await _seed_calls(sm, costs_today=[10.0, 20.0, 5.5], costs_yesterday=[100.0])
    g = BudgetGuard(sm=sm, daily_cap_inr=500)
    assert await g.spent_today() == pytest.approx(35.5, rel=1e-6)


async def test_check_passes_below_cap(sm):
    await _seed_calls(sm, costs_today=[100.0])
    g = BudgetGuard(sm=sm, daily_cap_inr=500)
    await g.check(projected_cost_inr=50.0)  # does not raise


async def test_check_raises_when_projection_exceeds_cap(sm):
    await _seed_calls(sm, costs_today=[490.0])
    g = BudgetGuard(sm=sm, daily_cap_inr=500)
    with pytest.raises(BudgetExceeded):
        await g.check(projected_cost_inr=50.0)  # 490 + 50 > 500
