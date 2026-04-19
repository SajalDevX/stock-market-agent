from quant_copilot.analysis.macro import evaluate_macro


def test_bullish_regime_when_indices_up_and_crude_soft():
    snap = {
        "nifty": {"close": 22500, "change_pct": 0.4},
        "banknifty": {"close": 49000, "change_pct": 0.6},
        "global": {"dow": {"close": 38000, "change_pct": 0.3},
                   "nasdaq": {"close": 16000, "change_pct": 0.2},
                   "nikkei": {"close": 38000, "change_pct": 0.5},
                   "crude": {"close": 82, "change_pct": -0.5}},
        "fx": {"usdinr": {"close": 83.5, "change_pct": 0.0}},
    }
    r = evaluate_macro(snap)
    assert r["regime"] == "bullish"
    assert r["score"] > 0
    assert any("positive" in t.lower() or "up" in t.lower() for t in r["tailwinds"])


def test_bearish_regime_when_indices_down_and_crude_spikes():
    snap = {
        "nifty": {"close": 22500, "change_pct": -0.8},
        "banknifty": {"close": 49000, "change_pct": -1.1},
        "global": {"dow": {"close": 38000, "change_pct": -0.5},
                   "nasdaq": {"close": 16000, "change_pct": -0.9},
                   "nikkei": {"close": 38000, "change_pct": -0.4},
                   "crude": {"close": 88, "change_pct": 2.5}},
        "fx": {"usdinr": {"close": 84.0, "change_pct": 0.5}},
    }
    r = evaluate_macro(snap)
    assert r["regime"] == "bearish"
    assert r["score"] < 0
    assert any("crude" in h.lower() for h in r["headwinds"])


def test_neutral_regime_when_mixed_small_moves():
    snap = {
        "nifty": {"close": 22500, "change_pct": 0.05},
        "banknifty": {"close": 49000, "change_pct": -0.05},
        "global": {"dow": {"close": 38000, "change_pct": 0.02},
                   "nasdaq": {"close": 16000, "change_pct": -0.02},
                   "nikkei": {"close": 38000, "change_pct": 0.0},
                   "crude": {"close": 82, "change_pct": 0.1}},
        "fx": {"usdinr": {"close": 83.5, "change_pct": 0.0}},
    }
    r = evaluate_macro(snap)
    assert r["regime"] == "neutral"
    assert abs(r["score"]) < 0.15
