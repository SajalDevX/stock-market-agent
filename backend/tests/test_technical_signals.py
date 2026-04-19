import numpy as np
import pandas as pd

from quant_copilot.agents.technical import compute_technical_signals


def _uptrend(n=120) -> pd.DataFrame:
    rng = np.random.default_rng(1)
    close = np.linspace(100, 200, n) + rng.normal(0, 0.3, n)
    idx = pd.date_range("2025-01-01", periods=n, freq="B", tz="UTC")
    return pd.DataFrame({
        "open": close, "high": close + 1.0, "low": close - 1.0,
        "close": close, "volume": rng.integers(100_000, 200_000, n),
    }, index=idx)


def _downtrend(n=120) -> pd.DataFrame:
    rng = np.random.default_rng(2)
    close = np.linspace(200, 100, n) + rng.normal(0, 0.3, n)
    idx = pd.date_range("2025-01-01", periods=n, freq="B", tz="UTC")
    return pd.DataFrame({
        "open": close, "high": close + 1.0, "low": close - 1.0,
        "close": close, "volume": rng.integers(100_000, 200_000, n),
    }, index=idx)


def test_uptrend_yields_bullish_signals_and_positive_score():
    sig = compute_technical_signals(_uptrend(), timeframe="swing")
    assert sig["trend"] == "up"
    assert sig["score"] > 0
    assert sig["liquidity_warning"] is False
    assert any(s["direction"] == "bullish" for s in sig["signals"])


def test_downtrend_yields_bearish_signals_and_negative_score():
    sig = compute_technical_signals(_downtrend(), timeframe="swing")
    assert sig["trend"] == "down"
    assert sig["score"] < 0


def test_score_is_bounded_in_minus_one_to_one():
    sig = compute_technical_signals(_uptrend(), timeframe="swing")
    assert -1.0 <= sig["score"] <= 1.0
