from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd


@dataclass(frozen=True)
class Pivot:
    idx: int
    date: pd.Timestamp
    price: float
    kind: Literal["high", "low"]


def find_pivots(df: pd.DataFrame, window: int = 5) -> list[Pivot]:
    """Local maxima/minima with symmetric window.

    A bar is a high pivot if its `high` is the max within [i-window, i+window]
    (inclusive of itself). Low pivot analogous on `low`.
    """
    if df.empty or window < 1:
        return []
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    dates = df.index.to_list()
    n = len(df)
    pivots: list[Pivot] = []
    for i in range(window, n - window):
        w_high = highs[i - window : i + window + 1]
        if highs[i] == w_high.max() and (w_high == highs[i]).sum() == 1:
            pivots.append(Pivot(idx=i, date=dates[i], price=float(highs[i]), kind="high"))
        w_low = lows[i - window : i + window + 1]
        if lows[i] == w_low.min() and (w_low == lows[i]).sum() == 1:
            pivots.append(Pivot(idx=i, date=dates[i], price=float(lows[i]), kind="low"))
    return pivots


def _cluster(levels: list[float], tol_pct: float) -> list[float]:
    if not levels:
        return []
    levels = sorted(levels)
    clusters: list[list[float]] = [[levels[0]]]
    for v in levels[1:]:
        ref = clusters[-1][-1]
        if abs(v - ref) / ref * 100 <= tol_pct:
            clusters[-1].append(v)
        else:
            clusters.append([v])
    return [round(sum(c) / len(c), 2) for c in clusters]


def key_levels(df: pd.DataFrame, *, window: int = 5, cluster_tol_pct: float = 0.8) -> dict[str, list[float]]:
    pivots = find_pivots(df, window=window)
    supports = [p.price for p in pivots if p.kind == "low"]
    resistances = [p.price for p in pivots if p.kind == "high"]
    return {
        "support": _cluster(supports, cluster_tol_pct),
        "resistance": _cluster(resistances, cluster_tol_pct),
    }


def detect_breakout(df: pd.DataFrame, *, window: int = 5, cluster_tol_pct: float = 0.8) -> dict:
    lv = key_levels(df, window=window, cluster_tol_pct=cluster_tol_pct)
    if df.empty:
        return {"breakout_direction": "none", "breakout_level": None, "key_levels": lv}
    last = df.iloc[-1]
    # Breakout up: close above the highest resistance
    if lv["resistance"]:
        r = max(lv["resistance"])
        if float(last["close"]) > r:
            return {"breakout_direction": "up", "breakout_level": r, "key_levels": lv}
    # Breakdown: close below lowest support
    if lv["support"]:
        s = min(lv["support"])
        if float(last["close"]) < s:
            return {"breakout_direction": "down", "breakout_level": s, "key_levels": lv}
    return {"breakout_direction": "none", "breakout_level": None, "key_levels": lv}
