from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["indicator", "news", "filing", "fundamental", "macro", "price"]
    label: str
    value: float | str | None = None
    asof: datetime
    ref: str | None = None  # e.g. artifact_id for news/filings


class Citation(BaseModel):
    """Pointer into the data layer's persisted artifacts.

    Used by the News agent in Plan 3 to prove every claim maps to a real
    retrieved article. Included here so the Technical agent's report can also
    reference OHLC/indicator sources when useful.
    """
    model_config = ConfigDict(extra="forbid")
    artifact_kind: Literal["news_article", "filing", "fundamentals_snapshot", "ohlc"]
    artifact_id: str
    title: str | None = None
    url: str | None = None


class AgentReport(BaseModel):
    """Base report shape all specialist agents extend."""
    model_config = ConfigDict(extra="allow")  # subclasses can add fields
    agent: str
    score: float = Field(..., ge=-1.0, le=1.0)
    reasoning: str
    evidence: list[Evidence]


class TechnicalReport(AgentReport):
    agent: Literal["technical"] = "technical"
    trend: Literal["up", "down", "sideways"]
    momentum: Literal["strong", "weak", "neutral"]
    key_levels: dict[str, list[float]]  # {"support": [...], "resistance": [...]}
    signals: list[dict[str, Any]]
    liquidity_warning: bool
    circuit_state: Literal["none", "upper", "lower", "frozen_days:N"] | str


# --- Fundamental ---------------------------------------------------------

class FundamentalReport(AgentReport):
    agent: Literal["fundamental"] = "fundamental"
    valuation: Literal["cheap", "fair", "expensive", "unknown"]
    quality: Literal["good", "average", "poor", "unknown"]
    growth: Literal["high", "moderate", "low", "negative", "unknown"]
    red_flags: list[str]
    surveillance: list[dict]  # e.g. [{"list": "ASM", "stage": "II"}]


# --- News ----------------------------------------------------------------

class NewsCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    artifact_kind: Literal["news_article", "filing"]
    artifact_id: str
    title: str | None = None
    url: str | None = None


class NewsReport(AgentReport):
    agent: Literal["news"] = "news"
    headline_summary: str
    material_events: list[str]
    sentiment: float = Field(..., ge=-1.0, le=1.0)
    citations: list[NewsCitation]


# --- Orchestrator --------------------------------------------------------

class Disagreement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    between: list[str]
    summary: str


class MacroReport(AgentReport):
    agent: Literal["macro"] = "macro"
    regime: Literal["bullish", "neutral", "bearish"]
    tailwinds: list[str]
    headwinds: list[str]


class OrchestratorReport(BaseModel):
    model_config = ConfigDict(extra="allow")
    ticker: str
    timeframe: Literal["intraday", "swing", "long-term"]
    verdict: Literal["buy", "hold", "avoid"]
    conviction: int = Field(..., ge=0, le=100)
    conviction_breakdown: dict[str, float]
    thesis: str
    risks: list[str]
    entry: float | None
    stop: float | None
    target: float | None
    ref_price: float
    agent_reports: dict[str, Any]
    disagreements: list[Disagreement]
