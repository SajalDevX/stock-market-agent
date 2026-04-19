from datetime import date
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

from quant_copilot.data.macro import MacroData


def _fake_hist(last_close: float, change_pct: float):
    idx = pd.date_range("2026-04-18", periods=2, freq="B", tz="UTC")
    base = last_close / (1 + change_pct / 100)
    return pd.DataFrame({
        "open": [base, last_close], "high": [base * 1.01, last_close * 1.01],
        "low": [base * 0.99, last_close * 0.99],
        "close": [base, last_close], "volume": [10, 20],
    }, index=idx)


async def test_macro_snapshot_returns_indices_and_fx():
    md = MacroData()
    fake = {
        "^NSEI":   _fake_hist(22500, 0.4),   # Nifty +0.4%
        "^NSEBANK": _fake_hist(49000, 0.6),  # BankNifty +0.6%
        "^DJI":    _fake_hist(38000, 0.2),   # Dow +0.2%
        "^IXIC":   _fake_hist(16000, -0.1),  # Nasdaq -0.1%
        "CL=F":    _fake_hist(82, -0.3),     # Crude -0.3%
        "INR=X":   _fake_hist(83.5, 0.05),   # USD-INR
    }
    with patch.object(md, "_fetch_one", AsyncMock(side_effect=lambda sym: fake[sym])):
        snap = await md.snapshot()

    assert snap["nifty"]["close"] == 22500
    assert snap["banknifty"]["change_pct"] == pytest.approx(0.6, abs=0.01)
    assert snap["global"]["dow"]["change_pct"] == pytest.approx(0.2, abs=0.01)
    assert snap["global"]["crude"]["change_pct"] < 0
    assert snap["fx"]["usdinr"]["close"] == 83.5
