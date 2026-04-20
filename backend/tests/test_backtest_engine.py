from datetime import date
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pandas as pd

from quant_copilot.backtest.engine import BacktestEngine, BacktestResult
from quant_copilot.backtest.strategy import Condition, Strategy
from quant_copilot.data.layer import DataLayer


def _trend(n=80, start=100, end=200):
    rng = np.random.default_rng(0)
    close = np.linspace(start, end, n) + rng.normal(0, 0.3, n)
    idx = pd.date_range("2024-01-01", periods=n, freq="B", tz="UTC")
    return pd.DataFrame({
        "open": close, "high": close + 1, "low": close - 1,
        "close": close, "volume": rng.integers(500_000, 1_000_000, n),
    }, index=idx)


def _layer_with(df: pd.DataFrame) -> DataLayer:
    layer = MagicMock(spec=DataLayer)
    layer.get_ohlc_adjusted = AsyncMock(return_value=df)
    return layer


async def test_engine_produces_at_least_one_trade_on_uptrend():
    layer = _layer_with(_trend())
    strat = Strategy(
        ticker="X", exchange="NSE",
        start=date(2024, 1, 1), end=date(2024, 12, 31),
        initial_capital=100000,
        entry=[Condition(indicator="close", op=">", indicator_ref="ema20")],
        exit=[Condition(indicator="close", op="<", indicator_ref="ema20")],
        max_hold_days=30,
    )
    engine = BacktestEngine(layer)
    result = await engine.run(strat)
    assert isinstance(result, BacktestResult)
    assert result.summary["n_trades"] >= 1
    assert len(result.equity_curve) > 0


async def test_engine_respects_stop_loss():
    # Falling series → if we enter, stop-loss should trip.
    rng = np.random.default_rng(1)
    close = np.linspace(200, 100, 80) + rng.normal(0, 0.2, 80)
    idx = pd.date_range("2024-01-01", periods=80, freq="B", tz="UTC")
    df = pd.DataFrame({
        "open": close, "high": close + 0.5, "low": close - 0.5,
        "close": close, "volume": [1_000_000] * 80,
    }, index=idx)
    layer = _layer_with(df)

    strat = Strategy(
        ticker="X", exchange="NSE",
        start=date(2024, 1, 1), end=date(2024, 12, 31),
        initial_capital=100000,
        # Force entry at first opportunity: close > 0 (always true once warm)
        entry=[Condition(indicator="close", op=">", value=0.0)],
        exit=[Condition(indicator="close", op="<", value=-1.0)],  # never
        stop_loss_pct=3.0,
    )
    engine = BacktestEngine(layer)
    result = await engine.run(strat)
    assert result.trades[0].reason == "stop_loss"


async def test_engine_respects_max_hold():
    # Flat close; no exit conditions → max_hold should force exit.
    idx = pd.date_range("2024-01-01", periods=60, freq="B", tz="UTC")
    df = pd.DataFrame({
        "open": [100] * 60, "high": [101] * 60, "low": [99] * 60,
        "close": [100] * 60, "volume": [1_000_000] * 60,
    }, index=idx)
    layer = _layer_with(df)

    strat = Strategy(
        ticker="X", exchange="NSE",
        start=date(2024, 1, 1), end=date(2024, 3, 31),
        initial_capital=100000,
        entry=[Condition(indicator="close", op=">", value=0.0)],
        exit=[Condition(indicator="close", op="<", value=-1.0)],  # never
        max_hold_days=10,
    )
    result = await BacktestEngine(layer).run(strat)
    assert result.trades
    assert result.trades[0].reason == "max_hold"
    assert result.trades[0].hold_days >= 10


async def test_engine_only_one_open_position_at_a_time():
    layer = _layer_with(_trend())
    strat = Strategy(
        ticker="X", exchange="NSE",
        start=date(2024, 1, 1), end=date(2024, 12, 31),
        initial_capital=100000,
        # Always-true entry, always-true exit → alternating entry/exit per bar
        entry=[Condition(indicator="close", op=">", value=0.0)],
        exit=[Condition(indicator="close", op=">", value=0.0)],
    )
    result = await BacktestEngine(layer).run(strat)
    # Check: no overlapping holds
    for a, b in zip(result.trades, result.trades[1:]):
        assert a.exit_date <= b.entry_date
