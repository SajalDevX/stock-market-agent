from datetime import date

import pytest

from quant_copilot.backtest.metrics import (
    Trade, compute_equity_curve, max_drawdown, summarize,
)


def _t(entry_date, entry_price, exit_date, exit_price, qty=1):
    return Trade(
        entry_date=entry_date, entry_price=entry_price,
        exit_date=exit_date, exit_price=exit_price,
        qty=qty, reason="signal",
    )


def test_equity_curve_reflects_realized_pnl():
    trades = [
        _t(date(2024, 1, 2), 100.0, date(2024, 1, 10), 110.0),  # +10%
        _t(date(2024, 2, 1), 110.0, date(2024, 2, 15),  99.0),  # -10%
    ]
    curve = compute_equity_curve(trades, initial_capital=1000.0)
    # Start, after trade 1, after trade 2
    dates = [p["date"] for p in curve]
    equity = [p["equity"] for p in curve]
    assert dates[0] == date(2024, 1, 2)
    # After +10% on 1 share with capital 1000: 1000 + 10 = 1010
    # (simple model: qty carried forward proportional to capital)
    assert equity[1] == pytest.approx(1010.0, rel=1e-4)
    assert equity[-1] < equity[1]  # drawdown


def test_max_drawdown():
    curve = [{"date": date(2024, 1, 1), "equity": 100},
             {"date": date(2024, 1, 2), "equity": 120},
             {"date": date(2024, 1, 3), "equity":  90},
             {"date": date(2024, 1, 4), "equity": 110}]
    # Peak 120 → trough 90 → dd = (90-120)/120 = -25%
    assert max_drawdown(curve) == pytest.approx(-25.0, abs=1e-6)


def test_summarize_computes_hit_rate_and_return():
    trades = [
        _t(date(2024, 1, 1), 100.0, date(2024, 1, 5), 110.0),  # win
        _t(date(2024, 2, 1), 100.0, date(2024, 2, 5), 105.0),  # win
        _t(date(2024, 3, 1), 100.0, date(2024, 3, 5),  90.0),  # loss
    ]
    s = summarize(trades, initial_capital=1000.0)
    assert s["n_trades"] == 3
    assert s["n_wins"] == 2
    assert s["win_rate_pct"] == pytest.approx(66.67, abs=0.1)
    assert s["total_return_pct"] > 0
    assert "max_drawdown_pct" in s
    assert "avg_hold_days" in s


def test_summarize_empty_trades_safe():
    s = summarize([], initial_capital=1000.0)
    assert s["n_trades"] == 0
    assert s["win_rate_pct"] == 0.0
    assert s["total_return_pct"] == 0.0
    assert s["max_drawdown_pct"] == 0.0
