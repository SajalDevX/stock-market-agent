import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pandas as pd
import pytest

from quant_copilot.agents.claude_client import ClaudeClient, LLMResponse
from quant_copilot.agents.fundamental import FundamentalAgent
from quant_copilot.agents.news import NewsAgent
from quant_copilot.agents.orchestrator import Orchestrator
from quant_copilot.agents.schemas import (
    FundamentalReport, NewsReport, OrchestratorReport, TechnicalReport,
)
from quant_copilot.agents.technical import TechnicalAgent
from quant_copilot.data.layer import DataLayer


def _ohlc_up(n=120):
    rng = np.random.default_rng(9)
    close = np.linspace(100, 200, n) + rng.normal(0, 0.3, n)
    idx = pd.date_range("2025-10-01", periods=n, freq="B", tz="UTC")
    return pd.DataFrame({
        "open": close, "high": close + 1, "low": close - 1,
        "close": close, "volume": rng.integers(500_000, 800_000, n),
    }, index=idx)


def _make_layer(sm, ohlc):
    layer = MagicMock(spec=DataLayer)
    layer.sm = sm
    layer.get_ohlc_adjusted = AsyncMock(return_value=ohlc)
    layer.fundamentals = MagicMock()
    layer.fundamentals.get = AsyncMock(return_value={"pe": 15, "roe_pct": 22, "roce_pct": 24,
                                                      "debt_to_equity": 0.4, "earnings_growth_pct": 18})
    layer.surveillance = MagicMock()
    layer.surveillance.get_flags = AsyncMock(return_value=[])
    # News service returns empty by default → news agent short-circuits to neutral
    layer.news = MagicMock()
    layer.news.get_for_ticker = AsyncMock(return_value=[])
    return layer


def _resp(text: str, cost=1.0):
    return LLMResponse(text=text, model="m", input_tokens=100, output_tokens=50,
                       cached_input_tokens=0, cost_inr=cost, latency_ms=500,
                       stop_reason="end_turn")


async def test_orchestrator_synthesizes_verdict(sm):
    layer = _make_layer(sm, _ohlc_up())
    client = MagicMock(spec=ClaudeClient)
    # Returns: technical prose, fundamental prose, orchestrator thesis JSON
    client.complete = AsyncMock(side_effect=[
        _resp("Clean uptrend with volume."),                             # technical
        _resp("Trades cheap with strong returns and growth."),           # fundamental
        _resp("""```json
{"thesis":"Strong technical trend with supportive fundamentals.","risks":["macro shock"],
 "entry":195.0,"stop":180.0,"target":220.0}
```"""),                                                                   # orchestrator
    ])

    orch = Orchestrator(
        data=layer, claude=client,
        technical=TechnicalAgent(data=layer, claude=client),
        fundamental=FundamentalAgent(data=layer, claude=client),
        news=NewsAgent(data=layer, claude=client),
    )
    report = await orch.research(ticker="RELIANCE", exchange="NSE", timeframe="swing")

    assert isinstance(report, OrchestratorReport)
    assert report.verdict == "buy"
    assert 0 <= report.conviction <= 100
    assert "technical" in report.agent_reports
    assert "fundamental" in report.agent_reports
    assert "news" in report.agent_reports
    assert report.entry == 195.0
    assert report.disagreements == []


async def test_orchestrator_intraday_skips_fundamental(sm):
    layer = _make_layer(sm, _ohlc_up())
    client = MagicMock(spec=ClaudeClient)
    client.complete = AsyncMock(side_effect=[
        _resp("Intraday uptrend."),      # technical
        _resp("""```json
{"thesis":"OK","risks":[],"entry":null,"stop":null,"target":null}
```"""),                                   # orchestrator
    ])
    orch = Orchestrator(
        data=layer, claude=client,
        technical=TechnicalAgent(data=layer, claude=client),
        fundamental=FundamentalAgent(data=layer, claude=client),
        news=NewsAgent(data=layer, claude=client),
    )
    report = await orch.research(ticker="RELIANCE", exchange="NSE", timeframe="intraday")
    assert "fundamental" not in report.agent_reports
    assert "technical" in report.agent_reports


async def test_orchestrator_surfaces_disagreement(sm):
    # Technical bullish, fundamental bearish (via poor fundamentals)
    layer = _make_layer(sm, _ohlc_up())
    layer.fundamentals.get = AsyncMock(return_value={
        "pe": 95, "roe_pct": 4, "roce_pct": 5, "debt_to_equity": 2.5,
        "earnings_growth_pct": -15,
    })
    client = MagicMock(spec=ClaudeClient)
    client.complete = AsyncMock(side_effect=[
        _resp("Technicals bullish."),
        _resp("Expensive, poor quality, shrinking."),
        _resp("""```json
{"thesis":"Tech/fund disagreement.","risks":["fundamental deterioration"],"entry":null,"stop":null,"target":null}
```"""),
    ])
    orch = Orchestrator(
        data=layer, claude=client,
        technical=TechnicalAgent(data=layer, claude=client),
        fundamental=FundamentalAgent(data=layer, claude=client),
        news=NewsAgent(data=layer, claude=client),
    )
    r = await orch.research(ticker="XYZ", exchange="NSE", timeframe="swing")
    assert len(r.disagreements) >= 1
    assert set(r.disagreements[0].between) & {"technical", "fundamental"}
