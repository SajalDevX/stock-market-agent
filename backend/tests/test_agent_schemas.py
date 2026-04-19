from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from quant_copilot.agents.schemas import Evidence, AgentReport, TechnicalReport
from quant_copilot.agents.schemas import (
    FundamentalReport, NewsReport, NewsCitation, OrchestratorReport, Disagreement,
)


def test_evidence_round_trips():
    e = Evidence(kind="indicator", label="RSI(14)", value=72.3,
                 asof=datetime(2026, 4, 17, tzinfo=timezone.utc))
    assert e.model_dump()["value"] == 72.3


def test_agent_report_rejects_out_of_range_score():
    with pytest.raises(ValidationError):
        AgentReport(agent="technical", score=2.5, reasoning="x", evidence=[])


def test_technical_report_validates_and_serializes():
    r = TechnicalReport(
        agent="technical",
        score=0.5,
        reasoning="Uptrend on daily with RSI room.",
        evidence=[Evidence(kind="indicator", label="RSI(14)", value=55.0,
                           asof=datetime.now(timezone.utc))],
        trend="up",
        momentum="strong",
        key_levels={"support": [2800.0], "resistance": [2900.0]},
        signals=[{"name": "ema_cross", "direction": "bullish", "strength": 0.7}],
        liquidity_warning=False,
        circuit_state="none",
    )
    j = r.model_dump_json()
    assert '"trend":"up"' in j
    assert '"score":0.5' in j


def test_technical_report_allows_string_score_coercion():
    r = TechnicalReport(
        agent="technical", score="0.1", reasoning="r", evidence=[],
        trend="sideways", momentum="neutral",
        key_levels={"support": [], "resistance": []}, signals=[],
        liquidity_warning=False, circuit_state="none",
    )
    assert r.score == 0.1


def test_fundamental_report_validates():
    r = FundamentalReport(
        score=0.3, reasoning="Reasonable valuation, steady growth.",
        evidence=[],
        valuation="fair", quality="good", growth="moderate",
        red_flags=[], surveillance=[],
    )
    assert r.agent == "fundamental"
    assert r.valuation == "fair"


def test_news_citation_requires_artifact_ref():
    c = NewsCitation(artifact_kind="news_article", artifact_id="42",
                     title="Q4 results", url="https://x/y")
    assert c.artifact_id == "42"


def test_news_report_with_citations():
    r = NewsReport(
        score=0.5, reasoning="Positive Q4 headline.",
        evidence=[],
        headline_summary="Strong earnings announced.",
        material_events=["Q4 results"],
        sentiment=0.5,
        citations=[NewsCitation(artifact_kind="news_article", artifact_id="42",
                                title="Q4 beats", url="https://x")],
    )
    assert r.agent == "news"
    assert len(r.citations) == 1


def test_orchestrator_report_structure():
    r = OrchestratorReport(
        ticker="RELIANCE", timeframe="swing",
        verdict="buy", conviction=65,
        conviction_breakdown={"technical": 0.4, "fundamental": 0.2, "news": 0.3},
        thesis="Up-trending with healthy fundamentals and positive news.",
        risks=["Crude price spike"],
        entry=2820.0, stop=2700.0, target=3000.0,
        ref_price=2825.0,
        agent_reports={},
        disagreements=[],
    )
    assert r.verdict == "buy"
    assert 0 <= r.conviction <= 100


def test_disagreement_names_conflicting_agents():
    d = Disagreement(between=["technical", "news"],
                     summary="Technicals bullish, news flags probe.")
    assert sorted(d.between) == ["news", "technical"]


from quant_copilot.agents.schemas import MacroReport


def test_macro_report_basic():
    r = MacroReport(
        score=0.3, reasoning="Positive cues.", evidence=[],
        regime="bullish", tailwinds=["positive US cues"], headwinds=[],
    )
    assert r.agent == "macro"
    assert r.regime == "bullish"
