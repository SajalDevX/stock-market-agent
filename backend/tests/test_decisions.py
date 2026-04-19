from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from quant_copilot.agents.decisions import persist_decision
from quant_copilot.agents.schemas import OrchestratorReport
from quant_copilot.models import Decision, Ticker


async def test_persist_decision_writes_row(sm):
    async with sm() as s:
        s.add(Ticker(symbol="RELIANCE", exchange="NSE", name="Reliance"))
        await s.commit()

    r = OrchestratorReport(
        ticker="RELIANCE", timeframe="swing",
        verdict="buy", conviction=65,
        conviction_breakdown={"technical": 0.4, "news": 0.3},
        thesis="t", risks=["r"],
        entry=2800.0, stop=2700.0, target=3000.0,
        ref_price=2825.0,
        agent_reports={}, disagreements=[],
    )
    await persist_decision(sm=sm, report=r)

    async with sm() as s:
        rows = (await s.execute(select(Decision))).scalars().all()
    assert len(rows) == 1
    assert rows[0].ticker == "RELIANCE"
    assert rows[0].verdict == "buy"
    assert rows[0].conviction == 65
    assert rows[0].ref_price == 2825.0
