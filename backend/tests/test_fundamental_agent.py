from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from quant_copilot.agents.claude_client import ClaudeClient, LLMResponse
from quant_copilot.agents.fundamental import FundamentalAgent
from quant_copilot.agents.schemas import FundamentalReport
from quant_copilot.data.layer import DataLayer


def _layer_with(payload, flags):
    layer = MagicMock(spec=DataLayer)
    layer.fundamentals = MagicMock()
    layer.fundamentals.get = AsyncMock(return_value=payload)
    layer.surveillance = MagicMock()
    layer.surveillance.get_flags = AsyncMock(return_value=flags)
    return layer


def _client_text(t: str):
    c = MagicMock(spec=ClaudeClient)
    c.complete = AsyncMock(return_value=LLMResponse(
        text=t, model="claude-sonnet-4-6",
        input_tokens=500, output_tokens=100, cached_input_tokens=0,
        cost_inr=1.0, latency_ms=700, stop_reason="end_turn",
    ))
    return c


async def test_fundamental_report_on_healthy_stock(sm):
    layer = _layer_with(
        {"pe": 15, "roe_pct": 22, "roce_pct": 24, "debt_to_equity": 0.4,
         "earnings_growth_pct": 18},
        [],
    )
    client = _client_text("Trades at reasonable multiples with strong returns.")
    agent = FundamentalAgent(data=layer, claude=client)
    r = await agent.analyze(ticker="RELIANCE")

    assert isinstance(r, FundamentalReport)
    assert r.valuation == "cheap"
    assert r.quality == "good"
    assert r.score > 0
    assert r.surveillance == []
    client.complete.assert_awaited_once()


async def test_fundamental_surveillance_flagged(sm):
    layer = _layer_with(
        {"pe": 12, "roe_pct": 18, "roce_pct": 22, "debt_to_equity": 0.3},
        [{"list": "ASM", "stage": "II"}],
    )
    client = _client_text("ASM II — heightened surveillance.")
    agent = FundamentalAgent(data=layer, claude=client)
    r = await agent.analyze(ticker="XYZ")
    assert r.surveillance == [{"list": "ASM", "stage": "II"}]
    assert any("surveillance" in x.lower() or "ASM" in x for x in r.red_flags + [r.reasoning])


async def test_fundamental_unknown_payload_returns_neutral(sm):
    layer = _layer_with({}, [])
    client = _client_text("Insufficient data to form a view.")
    agent = FundamentalAgent(data=layer, claude=client)
    r = await agent.analyze(ticker="NEWCO")
    assert r.valuation == "unknown"
    assert r.score == 0.0
