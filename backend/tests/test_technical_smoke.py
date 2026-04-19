from datetime import date
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pandas as pd

from quant_copilot.agents.claude_client import ClaudeClient, LLMResponse
from quant_copilot.agents.technical import TechnicalAgent
from quant_copilot.data.layer import DataLayer


def _ohlc(n=150):
    rng = np.random.default_rng(7)
    close = np.linspace(2000, 2500, n) + rng.normal(0, 10, n)
    idx = pd.date_range("2025-10-01", periods=n, freq="B", tz="UTC")
    return pd.DataFrame({
        "open": close, "high": close + 15, "low": close - 15,
        "close": close, "volume": rng.integers(500_000, 2_000_000, n),
    }, index=idx)


async def test_end_to_end_technical_report_shape(sm):
    layer = MagicMock(spec=DataLayer)
    layer.get_ohlc_adjusted = AsyncMock(return_value=_ohlc())
    client = MagicMock(spec=ClaudeClient)
    client.complete = AsyncMock(return_value=LLMResponse(
        text="Strong uptrend with constructive momentum and healthy volume.",
        model="claude-sonnet-4-6",
        input_tokens=1000, output_tokens=120, cached_input_tokens=0,
        cost_inr=1.4, latency_ms=800, stop_reason="end_turn",
    ))

    agent = TechnicalAgent(data=layer, claude=client)
    r = await agent.analyze(ticker="RELIANCE", exchange="NSE", timeframe="swing")
    d = r.model_dump(mode="json")

    # Shape assertions
    assert d["agent"] == "technical"
    assert isinstance(d["score"], float)
    assert d["trend"] in ("up", "down", "sideways")
    assert isinstance(d["key_levels"]["support"], list)
    assert isinstance(d["evidence"], list)
    assert all("label" in e for e in d["evidence"])
    assert "reasoning" in d and len(d["reasoning"]) > 10
