import numpy as np
import pandas as pd

from quant_copilot.analysis.patterns import find_pivots, key_levels, detect_breakout


def _with_peak_and_trough() -> pd.DataFrame:
    idx = pd.date_range("2025-01-01", periods=21, freq="B", tz="UTC")
    highs = [100, 101, 102, 103, 104, 105, 110, 108, 107, 106,
             105, 104, 103, 102, 101, 100,  99, 100, 101, 102, 103]
    lows  = [ 95,  96,  97,  98,  99, 100, 105, 103, 102, 101,
             100,  99,  98,  97,  96,  95,  94,  95,  96,  97,  98]
    closes = [(h + l) / 2 for h, l in zip(highs, lows)]
    return pd.DataFrame({"open": closes, "high": highs, "low": lows,
                         "close": closes, "volume": [1000] * 21}, index=idx)


def test_find_pivots_detects_high_and_low():
    df = _with_peak_and_trough()
    pivots = find_pivots(df, window=3)
    # The peak at index 6 (high=110) should be flagged as a high pivot
    highs = [p for p in pivots if p.kind == "high"]
    lows = [p for p in pivots if p.kind == "low"]
    assert any(p.idx == 6 for p in highs)
    # The trough at index 16 (low=94) should be a low pivot
    assert any(p.idx == 16 for p in lows)


def test_key_levels_clusters_nearby_pivots():
    df = _with_peak_and_trough()
    lv = key_levels(df, window=3, cluster_tol_pct=1.0)
    assert "support" in lv and "resistance" in lv
    assert any(abs(s - 94.0) < 1.5 for s in lv["support"])
    assert any(abs(r - 110.0) < 1.5 for r in lv["resistance"])


def test_detect_breakout_above_resistance():
    df = _with_peak_and_trough()
    # Force last bar to close above the known resistance at 110
    df = df.copy()
    df.iloc[-1] = df.iloc[-1]
    df.loc[df.index[-1], ["high", "close"]] = [115.0, 114.0]
    res = detect_breakout(df, window=3, cluster_tol_pct=1.0)
    assert res["breakout_direction"] == "up"
    assert res["breakout_level"] is not None
