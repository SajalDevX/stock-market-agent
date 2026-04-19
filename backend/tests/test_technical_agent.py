import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pandas as pd
import pytest

from quant_copilot.agents.claude_client import ClaudeClient, LLMResponse
from quant_copilot.agents.schemas import TechnicalReport
from quant_copilot.agents.technical import TechnicalAgent
from quant_copilot.data.layer import DataLayer


def _uptrend(n=120):
    rng = np.random.default_rng(3)
    close = np.linspace(100, 200, n) + rng.normal(0, 0.3, n)
    idx = pd.date_range("2025-10-01", periods=n, freq="B", tz="UTC")
    return pd.DataFrame({
        "open": close, "high": close + 1.0, "low": close - 1.0,
        "close": close, "volume": rng.integers(500_000, 800_000, n),
    }, index=idx)


def _make_layer_with_ohlc(df: pd.DataFrame) -> DataLayer:
    layer = MagicMock(spec=DataLayer)
    layer.get_ohlc_adjusted = AsyncMock(return_value=df)
    return layer


async def test_technical_agent_produces_valid_report(sm):
    layer = _make_layer_with_ohlc(_uptrend())
    thesis_text = (
        "The stock is in a clean daily uptrend with healthy momentum; "
        "the recent breakout over ₹190 suggests continuation toward ₹210. "
        "Risk: pullback to ₹180 support invalidates the near-term setup."
    )
    client = MagicMock(spec=ClaudeClient)
    client.complete = AsyncMock(return_value=LLMResponse(
        text=thesis_text, model="claude-sonnet-4-6",
        input_tokens=1500, output_tokens=200, cached_input_tokens=0,
        cost_inr=3.0, latency_ms=1200, stop_reason="end_turn",
    ))

    agent = TechnicalAgent(data=layer, claude=client)
    report = await agent.analyze(ticker="RELIANCE", exchange="NSE", timeframe="swing")

    assert isinstance(report, TechnicalReport)
    assert report.agent == "technical"
    assert report.trend == "up"
    assert report.score > 0
    assert thesis_text.split(".")[0] in report.reasoning
    assert report.liquidity_warning is False
    assert report.circuit_state == "none"

    # Client was called with both a system prompt and a user message containing the compact signals
    client.complete.assert_awaited_once()
    kwargs = client.complete.await_args.kwargs
    assert kwargs["agent_name"] == "technical"
    assert kwargs["tier"] in ("sonnet", "haiku", "opus")
    user_text = kwargs["messages"][-1]["content"]
    assert "RELIANCE" in user_text
    assert "trend" in user_text


async def test_technical_agent_short_circuits_on_low_liquidity(sm):
    idx = pd.date_range("2025-10-01", periods=40, freq="B", tz="UTC")
    illiquid = pd.DataFrame({
        "open": [3] * 40, "high": [3.1] * 40, "low": [2.9] * 40,
        "close": [3] * 40, "volume": [1_000] * 40,  # ₹3k/day — tiny
    }, index=idx)
    layer = _make_layer_with_ohlc(illiquid)
    client = MagicMock(spec=ClaudeClient)
    client.complete = AsyncMock()  # must not be called

    agent = TechnicalAgent(data=layer, claude=client)
    report = await agent.analyze(ticker="TINYCO", exchange="NSE", timeframe="swing")

    assert report.liquidity_warning is True
    assert report.score == 0.0
    client.complete.assert_not_awaited()
