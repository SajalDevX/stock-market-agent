import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import numpy as np
import pandas as pd
import pytest
from httpx import ASGITransport, AsyncClient

from quant_copilot.api.app import create_app
from quant_copilot.config import Settings


def _settings(tmp_path):
    os.environ["ANTHROPIC_API_KEY"] = "sk-test"
    os.environ["DATA_DIR"] = str(tmp_path / "data")
    os.environ["BACKUP_DIR"] = str(tmp_path / "backups")
    return Settings()  # type: ignore[call-arg]


def _uptrend(n=80):
    rng = np.random.default_rng(2)
    close = np.linspace(100, 200, n) + rng.normal(0, 0.3, n)
    idx = pd.date_range("2024-01-01", periods=n, freq="B", tz="UTC")
    return pd.DataFrame({
        "open": close, "high": close + 1, "low": close - 1,
        "close": close, "volume": [1_000_000] * n,
    }, index=idx)


async def test_post_backtest_returns_summary_and_trades(tmp_path):
    app = create_app(settings=_settings(tmp_path))
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            app.state.layer.get_ohlc_adjusted = AsyncMock(return_value=_uptrend())
            body = {
                "ticker": "X", "exchange": "NSE",
                "start": "2024-01-01", "end": "2024-12-31",
                "initial_capital": 100000,
                "entry": [{"indicator": "close", "op": ">", "indicator_ref": "ema20"}],
                "exit":  [{"indicator": "close", "op": "<", "indicator_ref": "ema20"}],
                "max_hold_days": 30,
            }
            r = await c.post("/backtest", json=body)
            assert r.status_code == 200
            data = r.json()
            assert "summary" in data
            assert "trades" in data
            assert "equity_curve" in data
            assert data["summary"]["n_trades"] >= 1


async def test_post_backtest_rejects_invalid_strategy(tmp_path):
    app = create_app(settings=_settings(tmp_path))
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/backtest", json={
                "ticker": "X", "exchange": "NSE",
                "start": "2024-12-31", "end": "2024-01-01",  # invalid
                "initial_capital": 100000,
                "entry": [{"indicator": "rsi", "op": "<", "value": 30}],
                "exit":  [{"indicator": "rsi", "op": ">", "value": 70}],
            })
            assert r.status_code == 422
