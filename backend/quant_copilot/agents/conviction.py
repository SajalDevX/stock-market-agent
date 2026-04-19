from __future__ import annotations

from typing import Literal


Timeframe = Literal["intraday", "swing", "long-term"]

WEIGHTS: dict[str, dict[str, float]] = {
    "intraday":  {"technical": 0.70, "news": 0.25, "macro": 0.05},
    "swing":     {"technical": 0.45, "news": 0.25, "fundamental": 0.20, "macro": 0.10},
    "long-term": {"fundamental": 0.55, "technical": 0.15, "news": 0.15, "macro": 0.15},
}

HOLD_BAND = 0.15


def verdict_from_weighted(weighted: float) -> str:
    if abs(weighted) < HOLD_BAND:
        return "hold"
    return "buy" if weighted > 0 else "avoid"


def _has_disagreement(scores: dict[str, float]) -> bool:
    signs = {1 if s > 0 else (-1 if s < 0 else 0) for s in scores.values() if s != 0}
    return 1 in signs and -1 in signs


def compute_conviction(scores: dict[str, float], *, timeframe: str) -> dict:
    """Deterministic synthesis of agent scores into a verdict + conviction %.

    Rules (spec §5.6.1):
    - Use timeframe-specific weights.
    - If some agents are missing, renormalise remaining weights.
    - Weighted sum (signed) → verdict via HOLD_BAND threshold.
    - If any pair of agents disagrees in sign, halve conviction and emit
      `disagreement_penalty = 1`.
    """
    if timeframe not in WEIGHTS:
        raise KeyError(f"Unknown timeframe: {timeframe}")
    base_w = WEIGHTS[timeframe]
    # Keep only agents that both have a score AND a weight
    active = {k: base_w[k] for k in scores.keys() if k in base_w}
    if not active:
        return {"weighted": 0.0, "conviction": 0, "verdict": "hold",
                "disagreement_penalty": 0, "effective_weights": {}}

    total = sum(active.values())
    eff_w = {k: w / total for k, w in active.items()}
    weighted = sum(scores[k] * eff_w[k] for k in eff_w)
    disagreement = _has_disagreement({k: scores[k] for k in eff_w})
    raw_conviction = abs(weighted) * 100
    if disagreement:
        raw_conviction = raw_conviction / 2.0

    return {
        "weighted": round(weighted, 4),
        "conviction": int(round(raw_conviction)),
        "verdict": verdict_from_weighted(weighted),
        "disagreement_penalty": 1 if disagreement else 0,
        "effective_weights": {k: round(v, 4) for k, v in eff_w.items()},
    }
