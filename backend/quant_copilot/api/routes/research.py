from __future__ import annotations

from fastapi import APIRouter

from quant_copilot.agents.decisions import persist_decision
from quant_copilot.api.deps import OrchestratorDep, SmDep
from quant_copilot.api.schemas import ResearchRequest


router = APIRouter(tags=["research"])


@router.post("/research")
async def research(body: ResearchRequest, orch: OrchestratorDep, sm: SmDep) -> dict:
    report = await orch.research(
        ticker=body.ticker, exchange=body.exchange, timeframe=body.timeframe,
    )
    if body.persist:
        await persist_decision(sm=sm, report=report)
    return report.model_dump(mode="json")
