from __future__ import annotations

import pandas as pd


def detect_circuit_state(df: pd.DataFrame) -> str:
    """Crude circuit detector.

    A bar is considered "stuck" when high == low (single-price bar) — a strong
    signal the stock hit an exchange-imposed circuit. We compare the first
    stuck bar's close to the previous (non-stuck) bar's close to label upper
    vs lower.

    If the last N bars are all stuck in the same direction, we report
    `frozen_days:N`.
    """
    if df.empty or len(df) < 2:
        return "none"

    def _is_stuck(row) -> bool:
        return float(row["high"]) == float(row["low"])

    # Walk backward to find the length of the trailing stuck streak.
    streak = 0
    first_stuck_idx = len(df)
    for i in range(len(df) - 1, 0, -1):
        cur = df.iloc[i]
        if not _is_stuck(cur):
            break
        streak += 1
        first_stuck_idx = i

    if streak == 0:
        return "none"

    # Determine direction by comparing the first stuck bar's close against
    # the bar immediately preceding it (must be non-stuck, since we stopped
    # the streak there — or we're at index 0 which we don't count as streak).
    first_stuck = df.iloc[first_stuck_idx]
    prev = df.iloc[first_stuck_idx - 1]
    if float(first_stuck["close"]) > float(prev["close"]):
        direction = "upper"
    elif float(first_stuck["close"]) < float(prev["close"]):
        direction = "lower"
    else:
        return "none"

    if streak == 1:
        return direction
    return f"frozen_days:{streak}"
