from __future__ import annotations

import pandas as pd


def avg_traded_value(df: pd.DataFrame, window: int = 20) -> float:
    """Average value traded per bar (close × volume) over the last `window` bars.

    Returns 0.0 if the DataFrame has fewer than `window` rows or is empty.
    """
    if df.empty or len(df) < window:
        if df.empty:
            return 0.0
        tail = df
    else:
        tail = df.tail(window)
    values = tail["close"] * tail["volume"]
    return float(values.mean())


def below_liquidity_floor(df: pd.DataFrame, *, floor_inr: float, window: int = 20) -> bool:
    return avg_traded_value(df, window=window) < float(floor_inr)
