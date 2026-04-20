from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

import pandas as pd

from quant_copilot.analysis.indicators import compute_indicators
from quant_copilot.backtest.metrics import Trade, compute_equity_curve, summarize
from quant_copilot.backtest.strategy import Condition, Strategy, evaluate_condition
from quant_copilot.data.layer import DataLayer


@dataclass
class BacktestResult:
    trades: list[Trade]
    equity_curve: list[dict]
    summary: dict
    bars_seen: int


def _bar_indicators(df_ind: pd.DataFrame, df_ohlc: pd.DataFrame, i: int) -> dict[str, float]:
    row = df_ind.iloc[i]
    ohlc = df_ohlc.iloc[i]
    out: dict[str, float] = {
        "open": float(ohlc["open"]), "high": float(ohlc["high"]),
        "low": float(ohlc["low"]), "close": float(ohlc["close"]),
        "volume": float(ohlc["volume"]) if "volume" in ohlc else 0.0,
    }
    for k, v in row.to_dict().items():
        try:
            out[k] = float(v) if v is not None else float("nan")
        except (TypeError, ValueError):
            out[k] = float("nan")
    return out


def _all_true(conds: list[Condition], bar: dict[str, float]) -> bool:
    return all(evaluate_condition(c, bar) for c in conds) if conds else False


def _any_true(conds: list[Condition], bar: dict[str, float]) -> bool:
    return any(evaluate_condition(c, bar) for c in conds) if conds else False


class BacktestEngine:
    def __init__(self, data: DataLayer) -> None:
        self._data = data

    async def run(self, strategy: Strategy) -> BacktestResult:
        df = await self._data.get_ohlc_adjusted(
            strategy.ticker, strategy.exchange, "1d",
            strategy.start, strategy.end,
        )
        if df is None or df.empty:
            return BacktestResult(trades=[], equity_curve=[],
                                   summary=summarize([], initial_capital=strategy.initial_capital),
                                   bars_seen=0)

        ind = compute_indicators(df)

        trades: list[Trade] = []
        in_position = False
        entry_i: int | None = None
        entry_date: date | None = None
        entry_price: float | None = None
        qty = 0.0
        capital = float(strategy.initial_capital)

        n = len(df)
        for i in range(n):
            bar = _bar_indicators(ind, df, i)
            bar_date = df.index[i].date()

            if in_position:
                assert entry_price is not None and entry_i is not None
                # Check implicit guards first, then declared exit conditions.
                reason: Optional[str] = None
                price_now = bar["close"]
                if strategy.stop_loss_pct is not None and price_now <= entry_price * (1 - strategy.stop_loss_pct / 100.0):
                    reason = "stop_loss"
                elif strategy.take_profit_pct is not None and price_now >= entry_price * (1 + strategy.take_profit_pct / 100.0):
                    reason = "take_profit"
                elif strategy.max_hold_days is not None and (bar_date - entry_date).days >= strategy.max_hold_days:  # type: ignore[operator]
                    reason = "max_hold"
                elif _any_true(strategy.exit, bar):
                    reason = "signal"

                if reason is not None:
                    exit_price = float(price_now)
                    trades.append(Trade(
                        entry_date=entry_date,  # type: ignore[arg-type]
                        entry_price=float(entry_price),
                        exit_date=bar_date,
                        exit_price=exit_price,
                        qty=qty, reason=reason,
                    ))
                    capital = qty * exit_price  # realized
                    in_position = False
                    entry_i = None
                    entry_date = None
                    entry_price = None
                    qty = 0.0
                    continue
            else:
                if _all_true(strategy.entry, bar):
                    entry_price = bar["close"]
                    if entry_price <= 0:
                        continue
                    qty = capital / entry_price
                    entry_i = i
                    entry_date = bar_date
                    in_position = True

        # End of data: close any open position at last bar's close
        if in_position and entry_price is not None:
            last_i = n - 1
            last_close = float(df.iloc[last_i]["close"])
            last_date = df.index[last_i].date()
            trades.append(Trade(
                entry_date=entry_date,  # type: ignore[arg-type]
                entry_price=float(entry_price),
                exit_date=last_date,
                exit_price=last_close,
                qty=qty, reason="end_of_data",
            ))

        summary = summarize(trades, initial_capital=strategy.initial_capital)
        curve = compute_equity_curve(trades, initial_capital=strategy.initial_capital)
        return BacktestResult(trades=trades, equity_curve=curve, summary=summary, bars_seen=n)
