from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from quant_copilot.agents.schemas import Evidence, AgentReport, TechnicalReport


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
