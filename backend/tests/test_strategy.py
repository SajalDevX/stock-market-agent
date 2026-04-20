from datetime import date

import pytest
from pydantic import ValidationError

from quant_copilot.backtest.strategy import (
    Condition, Strategy, evaluate_condition,
)


def test_strategy_requires_ticker_and_dates():
    s = Strategy(
        ticker="RELIANCE", exchange="NSE",
        start=date(2024, 1, 1), end=date(2024, 12, 31),
        initial_capital=100000,
        entry=[Condition(indicator="rsi", op="<", value=30)],
        exit=[Condition(indicator="rsi", op=">", value=70)],
    )
    assert s.ticker == "RELIANCE"
    assert s.initial_capital == 100000


def test_strategy_rejects_end_before_start():
    with pytest.raises(ValidationError):
        Strategy(
            ticker="R", exchange="NSE",
            start=date(2024, 6, 1), end=date(2024, 1, 1),
            initial_capital=100000,
            entry=[], exit=[Condition(indicator="rsi", op=">", value=70)],
        )


def test_strategy_rejects_empty_entry():
    with pytest.raises(ValidationError):
        Strategy(
            ticker="R", exchange="NSE",
            start=date(2024, 1, 1), end=date(2024, 12, 31),
            initial_capital=100000,
            entry=[], exit=[Condition(indicator="rsi", op=">", value=70)],
        )


def test_condition_against_scalar_value():
    # rsi=25 < 30 → True
    assert evaluate_condition(
        Condition(indicator="rsi", op="<", value=30),
        indicators={"rsi": 25.0, "close": 100.0},
    ) is True
    # rsi=31 < 30 → False
    assert evaluate_condition(
        Condition(indicator="rsi", op="<", value=30),
        indicators={"rsi": 31.0, "close": 100.0},
    ) is False


def test_condition_against_other_indicator():
    # close > ema50
    c = Condition(indicator="close", op=">", indicator_ref="ema50")
    assert evaluate_condition(c, {"close": 110.0, "ema50": 100.0}) is True
    assert evaluate_condition(c, {"close":  90.0, "ema50": 100.0}) is False


def test_condition_nan_indicator_evaluates_false():
    import math
    c = Condition(indicator="rsi", op="<", value=30)
    assert evaluate_condition(c, {"rsi": float("nan"), "close": 100.0}) is False


def test_condition_requires_value_or_indicator_ref():
    with pytest.raises(ValidationError):
        Condition(indicator="rsi", op="<")  # neither value nor indicator_ref
