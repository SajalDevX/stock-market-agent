from __future__ import annotations


def _get(d: dict, path: list[str], default=None):
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def evaluate_macro(snap: dict) -> dict:
    nifty = _get(snap, ["nifty", "change_pct"], 0.0) or 0.0
    banknifty = _get(snap, ["banknifty", "change_pct"], 0.0) or 0.0
    dow = _get(snap, ["global", "dow", "change_pct"], 0.0) or 0.0
    nasdaq = _get(snap, ["global", "nasdaq", "change_pct"], 0.0) or 0.0
    crude = _get(snap, ["global", "crude", "change_pct"], 0.0) or 0.0
    inr = _get(snap, ["fx", "usdinr", "change_pct"], 0.0) or 0.0

    # Weights chosen so the worst-case per-axis contribution is bounded in [-1, +1]:
    # index moves of ±1%, crude moves of ±3%, INR moves of ±0.5% saturate.
    weighted = (
        0.30 * max(-1.0, min(1.0, nifty))       # Indian market itself
      + 0.20 * max(-1.0, min(1.0, banknifty))   # Banking/financials pull
      + 0.15 * max(-1.0, min(1.0, dow / 1.0))
      + 0.15 * max(-1.0, min(1.0, nasdaq / 1.0))
      - 0.10 * max(-1.0, min(1.0, crude / 3.0)) # Crude up is a headwind for India
      - 0.10 * max(-1.0, min(1.0, inr / 0.5))   # Rupee weakening is a headwind
    )
    score = max(-1.0, min(1.0, weighted))

    if score > 0.15:
        regime = "bullish"
    elif score < -0.15:
        regime = "bearish"
    else:
        regime = "neutral"

    tailwinds: list[str] = []
    headwinds: list[str] = []
    if nifty > 0.2:
        tailwinds.append(f"Nifty positive today: +{nifty:.2f}%")
    if nifty < -0.2:
        headwinds.append(f"Nifty down today: {nifty:.2f}%")
    if dow > 0.3 or nasdaq > 0.3:
        tailwinds.append("Positive global cues from US")
    if dow < -0.3 or nasdaq < -0.3:
        headwinds.append("Negative global cues from US")
    if crude > 1.5:
        headwinds.append(f"Crude spike: +{crude:.2f}%")
    elif crude < -1.0:
        tailwinds.append(f"Crude soft: {crude:.2f}%")
    if inr > 0.3:
        headwinds.append("Rupee weakening")
    if banknifty > 0.5:
        tailwinds.append("Financials strong")
    if banknifty < -0.5:
        headwinds.append("Financials weak")

    return {
        "regime": regime,
        "score": round(score, 4),
        "tailwinds": tailwinds,
        "headwinds": headwinds,
    }
