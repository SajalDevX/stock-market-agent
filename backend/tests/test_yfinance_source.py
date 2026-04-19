import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from quant_copilot.data.sources.base import OhlcRequest
from quant_copilot.data.sources.yfinance_src import YFinanceSource


FIX = json.loads((Path(__file__).parent / "fixtures" / "yfinance_reliance_daily.json").read_text())


def _fake_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Open": b["open"], "High": b["high"], "Low": b["low"], "Close": b["close"], "Volume": b["volume"]}
            for b in FIX["bars"]
        ],
        index=pd.to_datetime([b["ts"] for b in FIX["bars"]], utc=True),
    )


async def test_yfinance_suffix_nse():
    src = YFinanceSource()
    assert src._yf_symbol("RELIANCE", "NSE") == "RELIANCE.NS"
    assert src._yf_symbol("RELIANCE", "BSE") == "RELIANCE.BO"


async def test_yfinance_fetch_returns_normalised_df():
    src = YFinanceSource()
    with patch("quant_copilot.data.sources.yfinance_src._yf_download", return_value=_fake_df()):
        df = await src.fetch(OhlcRequest("RELIANCE", "NSE", "1d", date(2026, 4, 13), date(2026, 4, 17)))
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert len(df) == 5
    assert df.index.tz is not None
    assert df["close"].iloc[-1] == 2845.0
