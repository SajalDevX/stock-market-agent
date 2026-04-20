from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from pydantic import BaseModel, ConfigDict


class Trade(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entry_date: date
    entry_price: float
    exit_date: date
    exit_price: float
    qty: float
    reason: str  # "signal" | "stop_loss" | "take_profit" | "max_hold" | "end_of_data"

    @property
    def pnl(self) -> float:
        return (self.exit_price - self.entry_price) * self.qty

    @property
    def return_pct(self) -> float:
        if self.entry_price <= 0:
            return 0.0
        return (self.exit_price - self.entry_price) / self.entry_price * 100.0

    @property
    def hold_days(self) -> int:
        return (self.exit_date - self.entry_date).days


def compute_equity_curve(trades: list[Trade], *, initial_capital: float) -> list[dict]:
    """Equity measured at each trade's entry+exit boundary.

    Realized PnL model: each trade's pnl (based on its recorded qty) is added
    to running equity at the exit bar.
    """
    equity = float(initial_capital)
    curve: list[dict] = []
    for t in trades:
        if t.entry_price <= 0:
            continue
        curve.append({"date": t.entry_date, "equity": round(equity, 4)})
        equity = equity + t.pnl
        curve.append({"date": t.exit_date, "equity": round(equity, 4)})
    if not curve:
        curve.append({"date": trades[0].entry_date if trades else None, "equity": round(equity, 4)})
    return curve


def max_drawdown(curve: list[dict]) -> float:
    """Worst peak-to-trough equity drop, returned as a negative percentage."""
    if not curve:
        return 0.0
    peak = curve[0]["equity"]
    worst = 0.0
    for pt in curve:
        eq = pt["equity"]
        if eq > peak:
            peak = eq
        if peak > 0:
            dd = (eq - peak) / peak * 100.0
            if dd < worst:
                worst = dd
    return round(worst, 4)


def summarize(trades: list[Trade], *, initial_capital: float) -> dict:
    if not trades:
        return {
            "n_trades": 0, "n_wins": 0, "n_losses": 0,
            "win_rate_pct": 0.0, "total_return_pct": 0.0,
            "max_drawdown_pct": 0.0, "avg_hold_days": 0.0,
            "final_equity": float(initial_capital),
        }
    wins = [t for t in trades if t.exit_price > t.entry_price]
    losses = [t for t in trades if t.exit_price < t.entry_price]
    curve = compute_equity_curve(trades, initial_capital=initial_capital)
    final = curve[-1]["equity"] if curve else initial_capital
    total_ret = (final - initial_capital) / initial_capital * 100.0
    avg_hold = sum(t.hold_days for t in trades) / len(trades)
    return {
        "n_trades": len(trades),
        "n_wins": len(wins),
        "n_losses": len(losses),
        "win_rate_pct": round(len(wins) / len(trades) * 100.0, 4),
        "total_return_pct": round(total_ret, 4),
        "max_drawdown_pct": max_drawdown(curve),
        "avg_hold_days": round(avg_hold, 2),
        "final_equity": round(final, 4),
    }
