from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from quant_copilot.agents.claude_client import ClaudeClient, LLMResponse
from quant_copilot.models import AgentCall


def _fake_message(text: str, input_tokens: int, output_tokens: int, cached: int = 0):
    m = MagicMock()
    m.content = [MagicMock(type="text", text=text)]
    m.usage = MagicMock(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_input_tokens=cached,
        cache_creation_input_tokens=0,
    )
    m.stop_reason = "end_turn"
    m.model = "claude-sonnet-4-6"
    return m


async def test_complete_returns_text_and_logs_call(sm):
    sdk = MagicMock()
    sdk.messages.create = AsyncMock(return_value=_fake_message("hello", 100, 20))
    client = ClaudeClient(sdk=sdk, sm=sm, usd_to_inr=83.0)

    resp = await client.complete(
        agent_name="technical",
        tier="sonnet",
        system="You are a technical analyst.",
        messages=[{"role": "user", "content": "analyze"}],
    )
    assert isinstance(resp, LLMResponse)
    assert resp.text == "hello"
    assert resp.input_tokens == 100
    assert resp.output_tokens == 20
    assert resp.cost_inr > 0

    async with sm() as s:
        rows = (await s.execute(select(AgentCall))).scalars().all()
    assert len(rows) == 1
    assert rows[0].agent == "technical"
    assert rows[0].model == "claude-sonnet-4-6"
    assert rows[0].input_tokens == 100
    assert rows[0].output_tokens == 20
    assert rows[0].error is None


async def test_complete_logs_errors_and_reraises(sm):
    sdk = MagicMock()
    sdk.messages.create = AsyncMock(side_effect=RuntimeError("boom"))
    client = ClaudeClient(sdk=sdk, sm=sm, usd_to_inr=83.0)

    with pytest.raises(RuntimeError):
        await client.complete(
            agent_name="technical", tier="haiku", system="s",
            messages=[{"role": "user", "content": "x"}],
        )

    async with sm() as s:
        rows = (await s.execute(select(AgentCall))).scalars().all()
    assert len(rows) == 1
    assert rows[0].error is not None
    assert "boom" in rows[0].error


async def test_prompt_caching_wraps_system(sm):
    """System prompt should be sent with cache_control on cacheable blocks."""
    sdk = MagicMock()
    sdk.messages.create = AsyncMock(return_value=_fake_message("ok", 10, 5, cached=50))
    client = ClaudeClient(sdk=sdk, sm=sm, usd_to_inr=83.0)

    await client.complete(
        agent_name="technical", tier="sonnet",
        system="BIG CACHED SYSTEM PROMPT",
        messages=[{"role": "user", "content": "q"}],
        cache_system=True,
    )

    kwargs = sdk.messages.create.await_args.kwargs
    sys_param = kwargs["system"]
    assert isinstance(sys_param, list)
    assert sys_param[0]["type"] == "text"
    assert sys_param[0]["cache_control"] == {"type": "ephemeral"}


from quant_copilot.agents.budget import BudgetGuard, BudgetExceeded


async def test_claude_client_refuses_when_budget_exceeded(sm):
    # Seed a call that puts us right at the cap
    from quant_copilot.models import AgentCall
    from datetime import datetime, timezone
    async with sm() as s:
        s.add(AgentCall(agent="x", input_hash="h", model="m",
                        input_tokens=1, output_tokens=1, cost_inr=499.5,
                        latency_ms=1, error=None,
                        created_at=datetime.now(tz=timezone.utc)))
        await s.commit()

    sdk = MagicMock()
    sdk.messages.create = AsyncMock(return_value=_fake_message("nope", 10, 5))
    guard = BudgetGuard(sm=sm, daily_cap_inr=500)
    client = ClaudeClient(sdk=sdk, sm=sm, usd_to_inr=83.0, budget=guard,
                          min_projected_cost_inr=5.0)

    with pytest.raises(BudgetExceeded):
        await client.complete(
            agent_name="technical", tier="sonnet",
            system="s", messages=[{"role": "user", "content": "x"}],
        )
    sdk.messages.create.assert_not_called()
