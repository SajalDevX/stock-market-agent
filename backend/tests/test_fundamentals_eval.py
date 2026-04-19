from quant_copilot.analysis.fundamentals_eval import evaluate_fundamentals


def test_cheap_good_growing_stock_scores_positive():
    payload = {
        "pe": 15.0, "roe_pct": 22.0, "roce_pct": 24.0,
        "debt_to_equity": 0.4, "market_cap_cr": 100000, "dividend_yield_pct": 1.2,
        "earnings_growth_pct": 20.0,  # optional
    }
    r = evaluate_fundamentals(payload)
    assert r["valuation"] == "cheap"
    assert r["quality"] == "good"
    assert r["growth"] in ("high", "moderate")
    assert r["score"] > 0
    assert r["red_flags"] == []


def test_expensive_poor_shrinking_stock_scores_negative():
    payload = {
        "pe": 95.0, "roe_pct": 4.0, "roce_pct": 5.0,
        "debt_to_equity": 2.5, "earnings_growth_pct": -15.0,
    }
    r = evaluate_fundamentals(payload)
    assert r["valuation"] == "expensive"
    assert r["quality"] == "poor"
    assert r["growth"] == "negative"
    assert r["score"] < 0
    assert any("debt" in f.lower() for f in r["red_flags"])


def test_unknown_when_payload_empty():
    r = evaluate_fundamentals({})
    assert r["valuation"] == "unknown"
    assert r["quality"] == "unknown"
    assert r["growth"] == "unknown"
    assert r["score"] == 0.0


def test_score_bounded():
    r = evaluate_fundamentals({"pe": 10, "roe_pct": 40, "roce_pct": 40,
                               "debt_to_equity": 0.1, "earnings_growth_pct": 60})
    assert -1.0 <= r["score"] <= 1.0
