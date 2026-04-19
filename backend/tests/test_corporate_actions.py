from datetime import date

import pandas as pd

from quant_copilot.data.corporate_actions import CorporateActionSet, apply_adjustments


def _sample_ohlc() -> pd.DataFrame:
    idx = pd.to_datetime([
        "2023-06-12", "2023-06-13", "2023-06-14", "2023-06-15", "2023-06-16",
    ])
    return pd.DataFrame(
        {
            "open":  [2500.0, 2510.0, 2520.0, 510.0, 515.0],
            "high":  [2530.0, 2530.0, 2540.0, 520.0, 525.0],
            "low":   [2490.0, 2500.0, 2500.0, 500.0, 510.0],
            "close": [2520.0, 2525.0, 2530.0, 510.0, 520.0],
            "volume": [100, 110, 120, 600, 610],
        },
        index=idx,
    )


def test_split_adjustment_back_adjusts_historical_prices():
    df = _sample_ohlc()
    actions = CorporateActionSet([
        {"ex_date": date(2023, 6, 15), "kind": "split", "ratio_num": 1.0, "ratio_den": 5.0},
    ])
    adj = apply_adjustments(df, actions)
    # Pre-split rows divided by 5, volumes multiplied by 5
    assert round(adj.loc["2023-06-14", "close"], 2) == round(2530.0 / 5, 2)
    assert adj.loc["2023-06-14", "volume"] == 600
    # Post-split rows unchanged
    assert adj.loc["2023-06-15", "close"] == 510.0
    assert adj.loc["2023-06-15", "volume"] == 600


def test_bonus_adjustment_similar_to_split():
    df = _sample_ohlc()
    # 1:1 bonus -> 2 shares per 1
    actions = CorporateActionSet([
        {"ex_date": date(2023, 6, 15), "kind": "bonus", "ratio_num": 1.0, "ratio_den": 2.0},
    ])
    adj = apply_adjustments(df, actions)
    assert round(adj.loc["2023-06-14", "close"], 2) == round(2530.0 / 2, 2)


def test_no_actions_returns_original_values():
    df = _sample_ohlc()
    adj = apply_adjustments(df, CorporateActionSet([]))
    pd.testing.assert_frame_equal(df, adj)


def test_dividend_does_not_adjust_ohlc_for_technicals():
    df = _sample_ohlc()
    actions = CorporateActionSet([
        {"ex_date": date(2023, 6, 15), "kind": "dividend", "dividend_per_share": 5.0},
    ])
    adj = apply_adjustments(df, actions)
    pd.testing.assert_frame_equal(df, adj)
