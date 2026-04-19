import pandas as pd

from quant_copilot.analysis.circuit import detect_circuit_state


def _bar(o, h, l, c, v):
    return {"open": o, "high": h, "low": l, "close": c, "volume": v}


def test_no_circuit_when_range_normal():
    idx = pd.date_range("2025-01-01", periods=5, freq="B", tz="UTC")
    df = pd.DataFrame([_bar(100, 102, 99, 101, 10_000)] * 5, index=idx)
    assert detect_circuit_state(df) == "none"


def test_upper_circuit_when_high_equals_low_above_prev_close():
    idx = pd.date_range("2025-01-01", periods=2, freq="B", tz="UTC")
    df = pd.DataFrame([
        _bar(100, 102, 99, 100, 10_000),   # prev close 100
        _bar(110, 110, 110, 110, 5_000),   # flat bar above -> upper
    ], index=idx)
    assert detect_circuit_state(df) == "upper"


def test_lower_circuit_when_high_equals_low_below_prev_close():
    idx = pd.date_range("2025-01-01", periods=2, freq="B", tz="UTC")
    df = pd.DataFrame([
        _bar(100, 102, 99, 100, 10_000),
        _bar(90, 90, 90, 90, 5_000),
    ], index=idx)
    assert detect_circuit_state(df) == "lower"


def test_frozen_days_tracks_consecutive_flat_bars():
    idx = pd.date_range("2025-01-01", periods=4, freq="B", tz="UTC")
    df = pd.DataFrame([
        _bar(100, 102, 99, 100, 10_000),   # normal
        _bar(110, 110, 110, 110, 5_000),   # upper
        _bar(110, 110, 110, 110, 2_000),   # upper again
        _bar(110, 110, 110, 110, 1_000),   # upper again
    ], index=idx)
    assert detect_circuit_state(df) == "frozen_days:3"
