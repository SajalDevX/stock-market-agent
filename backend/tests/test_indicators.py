import numpy as np
import pandas as pd

from quant_copilot.analysis.indicators import compute_indicators


def _synthetic_uptrend(n: int = 120) -> pd.DataFrame:
    # Steady uptrend with mild noise — RSI should sit in 50–80, EMA20 < EMA50 early then flip.
    rng = np.random.default_rng(42)
    base = np.linspace(100, 200, n)
    noise = rng.normal(0, 0.5, n)
    close = base + noise
    idx = pd.date_range("2025-01-01", periods=n, freq="B", tz="UTC")
    return pd.DataFrame(
        {"open": close, "high": close + 1.0, "low": close - 1.0,
         "close": close, "volume": rng.integers(10_000, 20_000, n)},
        index=idx,
    )


def test_compute_indicators_contains_expected_keys():
    df = _synthetic_uptrend()
    out = compute_indicators(df)
    for k in ("rsi", "macd", "macd_signal", "ema20", "ema50", "ema200", "atr", "bb_upper", "bb_lower"):
        assert k in out.columns


def test_rsi_range_and_uptrend_bias():
    df = _synthetic_uptrend()
    out = compute_indicators(df)
    rsi = out["rsi"].dropna()
    assert rsi.min() >= 0
    assert rsi.max() <= 100
    # Steady uptrend: last 20 bars' RSI should be well above 50
    assert rsi.iloc[-20:].mean() > 55


def test_short_series_returns_na_for_long_period_indicators():
    df = _synthetic_uptrend(n=30)
    out = compute_indicators(df)
    # EMA200 needs at least 200 bars; should be all NaN on a 30-bar series
    assert out["ema200"].isna().all()
