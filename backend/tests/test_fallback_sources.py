from datetime import date
from unittest.mock import patch

import pandas as pd

from quant_copilot.data.sources.base import OhlcRequest
from quant_copilot.data.sources.nsepython_src import NsePythonSource
from quant_copilot.data.sources.nsetools_src import NsetoolsSource


async def test_nsepython_parses_equity_history_format():
    sample = [
        {"CH_TIMESTAMP": "2026-04-15", "CH_OPENING_PRICE": 2825, "CH_TRADE_HIGH_PRICE": 2840,
         "CH_TRADE_LOW_PRICE": 2810, "CH_CLOSING_PRICE": 2815, "CH_TOT_TRADED_QTY": 1250000},
        {"CH_TIMESTAMP": "2026-04-16", "CH_OPENING_PRICE": 2815, "CH_TRADE_HIGH_PRICE": 2830,
         "CH_TRADE_LOW_PRICE": 2800, "CH_CLOSING_PRICE": 2820, "CH_TOT_TRADED_QTY": 1150000},
    ]
    with patch("nsepython.equity_history", return_value=sample):
        src = NsePythonSource()
        df = await src.fetch(OhlcRequest("RELIANCE", "NSE", "1d", date(2026, 4, 15), date(2026, 4, 16)))
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert len(df) == 2


async def test_nsetools_quote_shape():
    with patch("nsetools.Nse.get_quote", return_value={"lastPrice": "2820.5"}):
        q = await NsetoolsSource().quote("RELIANCE")
    assert q["ticker"] == "RELIANCE"
    assert q["ltp"] == 2820.5
