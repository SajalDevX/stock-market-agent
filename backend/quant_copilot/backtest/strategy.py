from __future__ import annotations

import math
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


Op = Literal["<", "<=", ">", ">=", "==", "!="]


class Condition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    indicator: str           # e.g. "rsi", "close", "ema20"
    op: Op
    value: float | None = None
    indicator_ref: str | None = None  # compare against another indicator key

    @model_validator(mode="after")
    def _check_rhs(self) -> "Condition":
        if self.value is None and self.indicator_ref is None:
            raise ValueError("Condition requires either value or indicator_ref")
        if self.value is not None and self.indicator_ref is not None:
            raise ValueError("Condition cannot have both value and indicator_ref")
        return self


class Strategy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticker: str
    exchange: str = "NSE"
    start: date
    end: date
    initial_capital: float = Field(..., gt=0)
    entry: list[Condition] = Field(..., min_length=1)
    exit: list[Condition] = Field(..., min_length=1)
    stop_loss_pct: float | None = Field(default=None, gt=0)
    take_profit_pct: float | None = Field(default=None, gt=0)
    max_hold_days: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _check_dates(self) -> "Strategy":
        if self.end <= self.start:
            raise ValueError("end must be after start")
        return self


_OPS = {
    "<":  lambda a, b: a <  b,
    "<=": lambda a, b: a <= b,
    ">":  lambda a, b: a >  b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def evaluate_condition(c: Condition, indicators: dict[str, float]) -> bool:
    left = indicators.get(c.indicator)
    if left is None or (isinstance(left, float) and math.isnan(left)):
        return False
    if c.indicator_ref is not None:
        right = indicators.get(c.indicator_ref)
        if right is None or (isinstance(right, float) and math.isnan(right)):
            return False
    else:
        right = c.value  # type: ignore[assignment]
    return _OPS[c.op](float(left), float(right))
