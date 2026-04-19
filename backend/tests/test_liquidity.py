import numpy as np
import pandas as pd

from quant_copilot.analysis.liquidity import avg_traded_value, below_liquidity_floor


def test_avg_traded_value_last_20():
    idx = pd.date_range("2025-01-01", periods=30, freq="B", tz="UTC")
    df = pd.DataFrame({
        "open": [100] * 30, "high": [101] * 30, "low": [99] * 30,
        "close": [100] * 30, "volume": [10_000] * 30,
    }, index=idx)
    # avg traded value = close * volume = 100 * 10_000 = 10_00_000 per bar
    assert avg_traded_value(df, window=20) == 1_000_000.0


def test_below_liquidity_floor_liquid_stock():
    idx = pd.date_range("2025-01-01", periods=30, freq="B", tz="UTC")
    df = pd.DataFrame({
        "open": [2800] * 30, "high": [2810] * 30, "low": [2790] * 30,
        "close": [2800] * 30, "volume": [1_000_000] * 30,  # ~₹280 Cr/day
    }, index=idx)
    assert not below_liquidity_floor(df, floor_inr=10_000_000)  # ₹1 Cr floor


def test_below_liquidity_floor_illiquid_stock():
    idx = pd.date_range("2025-01-01", periods=30, freq="B", tz="UTC")
    df = pd.DataFrame({
        "open": [3] * 30, "high": [3.1] * 30, "low": [2.9] * 30,
        "close": [3] * 30, "volume": [10_000] * 30,  # ₹30k/day
    }, index=idx)
    assert below_liquidity_floor(df, floor_inr=10_000_000)
