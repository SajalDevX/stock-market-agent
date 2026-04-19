import pytest

from quant_copilot.agents.conviction import (
    compute_conviction, WEIGHTS, verdict_from_weighted,
)


def test_weights_for_each_timeframe_exist():
    assert set(WEIGHTS.keys()) == {"intraday", "swing", "long-term"}
    for tf, w in WEIGHTS.items():
        assert sum(w.values()) == pytest.approx(1.0, abs=1e-6)


def test_all_bullish_yields_buy_and_high_conviction():
    scores = {"technical": 0.8, "fundamental": 0.6, "news": 0.4, "macro": 0.3}
    r = compute_conviction(scores, timeframe="swing")
    assert r["verdict"] == "buy"
    assert r["conviction"] >= 40
    assert r["disagreement_penalty"] == 0


def test_mixed_signs_penalize_conviction():
    scores = {"technical": 0.7, "fundamental": -0.4, "news": -0.3}
    r = compute_conviction(scores, timeframe="swing")
    assert r["disagreement_penalty"] > 0  # halving kicks in
    # Absolute value of weighted should be halved
    assert r["conviction"] < compute_conviction(
        {"technical": 0.7, "fundamental": 0.4, "news": 0.3}, timeframe="swing"
    )["conviction"]


def test_hold_band_for_small_weighted():
    scores = {"technical": 0.05, "news": -0.05, "fundamental": 0.0}
    r = compute_conviction(scores, timeframe="swing")
    assert r["verdict"] == "hold"


def test_missing_agent_scores_ignored_and_weights_renormalised():
    # Intraday: weights are technical 0.70, news 0.25, macro 0.05.
    # If macro is missing, remaining renormalise to technical 0.70/0.95, news 0.25/0.95.
    scores = {"technical": 0.8, "news": -0.2}
    r = compute_conviction(scores, timeframe="intraday")
    assert r["verdict"] in ("buy", "hold")
    # Effective weight on technical ≈ 0.737
    assert r["weighted"] > 0.3  # driven by technical


def test_verdict_threshold_monotonic():
    assert verdict_from_weighted(0.0) == "hold"
    assert verdict_from_weighted(0.14) == "hold"
    assert verdict_from_weighted(0.20) == "buy"
    assert verdict_from_weighted(-0.20) == "avoid"
