from __future__ import annotations


def _tier_pe(pe: float | None) -> str:
    if pe is None:
        return "unknown"
    if pe < 20:
        return "cheap"
    if pe < 40:
        return "fair"
    return "expensive"


def _tier_quality(roe: float | None, roce: float | None, dte: float | None) -> str:
    if roe is None and roce is None and dte is None:
        return "unknown"
    good = (roe or 0) >= 15 and (roce or 0) >= 15 and (dte or 0) <= 1.0
    poor = ((roe or 100) < 8) or ((dte or 0) > 1.5)
    if good and not poor:
        return "good"
    if poor:
        return "poor"
    return "average"


def _tier_growth(g: float | None) -> str:
    if g is None:
        return "unknown"
    if g >= 15:
        return "high"
    if g >= 5:
        return "moderate"
    if g >= 0:
        return "low"
    return "negative"


def evaluate_fundamentals(payload: dict) -> dict:
    pe = payload.get("pe")
    roe = payload.get("roe_pct")
    roce = payload.get("roce_pct")
    dte = payload.get("debt_to_equity")
    growth = payload.get("earnings_growth_pct")

    valuation = _tier_pe(pe)
    quality = _tier_quality(roe, roce, dte)
    grow = _tier_growth(growth)

    red_flags: list[str] = []
    if dte is not None and dte > 1.5:
        red_flags.append(f"High debt-to-equity: {dte}")
    if roe is not None and roe < 5:
        red_flags.append(f"Very low ROE: {roe}%")
    if growth is not None and growth < -10:
        red_flags.append(f"Earnings declining: {growth}%")

    # Scoring: each axis contributes a signed component in [-1, +1]; weighted sum → final.
    v_map = {"cheap": 0.6, "fair": 0.1, "expensive": -0.5, "unknown": 0.0}
    q_map = {"good": 0.6, "average": 0.1, "poor": -0.6, "unknown": 0.0}
    g_map = {"high": 0.6, "moderate": 0.2, "low": 0.0, "negative": -0.6, "unknown": 0.0}

    raw = 0.4 * v_map[valuation] + 0.35 * q_map[quality] + 0.25 * g_map[grow]
    score = max(-1.0, min(1.0, raw))

    return {
        "valuation": valuation,
        "quality": quality,
        "growth": grow,
        "red_flags": red_flags,
        "score": round(score, 4),
    }
