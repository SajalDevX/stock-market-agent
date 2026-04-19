from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from quant_copilot.api.deps import BudgetDep, SettingsDep, SmDep
from quant_copilot.api.schemas import HealthResponse


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(settings: SettingsDep, sm: SmDep, budget: BudgetDep) -> HealthResponse:
    db_ok = True
    try:
        async with sm() as s:
            await s.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    spent = await budget.spent_today()
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        db=db_ok,
        llm_budget_spent_today=round(spent, 2),
        daily_cap_inr=float(settings.daily_llm_budget_inr),
    )
