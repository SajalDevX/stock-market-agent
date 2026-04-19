from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ResearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticker: str
    exchange: str = "NSE"
    timeframe: Literal["intraday", "swing", "long-term"] = "swing"
    tier: str = "sonnet"
    news_tier: str = "haiku"
    persist: bool = True


class WatchlistAddRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rules_json: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"] = "ok"
    db: bool
    llm_budget_spent_today: float
    daily_cap_inr: float
    scheduler_running: bool = True
