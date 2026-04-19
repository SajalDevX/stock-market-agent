from __future__ import annotations

import pandas as pd
import pandas_ta as ta


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Return a new DataFrame (same index) with technical indicators.

    Expects columns: open, high, low, close, volume.
    Input is left unchanged.
    """
    if df.empty:
        return df.copy()

    out = pd.DataFrame(index=df.index)

    out["rsi"] = ta.rsi(df["close"], length=14)

    macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
    if macd is not None and not macd.empty:
        out["macd"] = macd.iloc[:, 0]
        out["macd_signal"] = macd.iloc[:, 2]
        out["macd_hist"] = macd.iloc[:, 1]
    else:
        out["macd"] = pd.Series(index=df.index, dtype=float)
        out["macd_signal"] = pd.Series(index=df.index, dtype=float)
        out["macd_hist"] = pd.Series(index=df.index, dtype=float)

    out["ema20"] = ta.ema(df["close"], length=20)
    out["ema50"] = ta.ema(df["close"], length=50)
    out["ema200"] = ta.ema(df["close"], length=200)

    out["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)

    bb = ta.bbands(df["close"], length=20, std=2)
    if bb is not None and not bb.empty:
        out["bb_lower"] = bb.iloc[:, 0]
        out["bb_mid"] = bb.iloc[:, 1]
        out["bb_upper"] = bb.iloc[:, 2]
    else:
        for k in ("bb_lower", "bb_mid", "bb_upper"):
            out[k] = pd.Series(index=df.index, dtype=float)

    return out
