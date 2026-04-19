from unittest.mock import AsyncMock, MagicMock

import pytest

from quant_copilot.agents.claude_client import ClaudeClient, LLMResponse
from quant_copilot.agents.macro import MacroAgent
from quant_copilot.agents.schemas import MacroReport
from quant_copilot.data.macro import MacroData


async def test_macro_agent_returns_structured_report():
    md = MagicMock(spec=MacroData)
    md.snapshot = AsyncMock(return_value={
        "nifty": {"close": 22500, "change_pct": 0.4},
        "banknifty": {"close": 49000, "change_pct": 0.6},
        "global": {"dow": {"close": 38000, "change_pct": 0.3},
                   "nasdaq": {"close": 16000, "change_pct": 0.2},
                   "nikkei": {"close": 38000, "change_pct": 0.5},
                   "crude": {"close": 82, "change_pct": -0.5}},
        "fx": {"usdinr": {"close": 83.5, "change_pct": 0.0}},
    })
    client = MagicMock(spec=ClaudeClient)
    client.complete = AsyncMock(return_value=LLMResponse(
        text="Constructive tape supported by soft crude and positive US cues.",
        model="claude-haiku-4-5-20251001", input_tokens=300, output_tokens=50,
        cached_input_tokens=0, cost_inr=0.3, latency_ms=500, stop_reason="end_turn",
    ))

    agent = MacroAgent(macro_data=md, claude=client)
    r = await agent.analyze()
    assert isinstance(r, MacroReport)
    assert r.regime == "bullish"
    assert r.score > 0
    assert "crude" in (r.reasoning + " " + " ".join(r.tailwinds + r.headwinds)).lower() or r.reasoning
    client.complete.assert_awaited_once()
