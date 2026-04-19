from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import desc, select

from quant_copilot.api.deps import SmDep
from quant_copilot.models import Decision, DecisionOutcome


router = APIRouter(prefix="/decisions", tags=["decisions"])


def _decision_row(d: Decision) -> dict:
    return {
        "id": d.id, "ticker": d.ticker, "timeframe": d.timeframe,
        "verdict": d.verdict, "conviction": d.conviction,
        "entry": d.entry, "stop": d.stop, "target": d.target,
        "ref_price": d.ref_price, "created_at": d.created_at.isoformat(),
    }


@router.get("")
async def list_decisions(sm: SmDep, limit: int = 100) -> list[dict]:
    async with sm() as s:
        rows = (await s.execute(
            select(Decision).order_by(desc(Decision.created_at)).limit(limit)
        )).scalars().all()
    return [_decision_row(d) for d in rows]


@router.get("/{decision_id}")
async def get_decision(decision_id: int, sm: SmDep) -> dict:
    async with sm() as s:
        d = (await s.execute(
            select(Decision).where(Decision.id == decision_id)
        )).scalar_one_or_none()
        if d is None:
            raise HTTPException(status_code=404, detail="Decision not found")
        outcomes = (await s.execute(
            select(DecisionOutcome).where(DecisionOutcome.decision_id == decision_id)
        )).scalars().all()
    body = _decision_row(d)
    body["outcomes"] = [
        {"horizon": o.horizon, "return_pct": round(o.return_pct, 4)} for o in outcomes
    ]
    return body
