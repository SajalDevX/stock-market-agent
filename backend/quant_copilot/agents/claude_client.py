from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from quant_copilot.agents.pricing import estimate_cost_inr
from quant_copilot.models import AgentCall


MODEL_ID = {
    "opus": "claude-opus-4-7",
    "sonnet": "claude-sonnet-4-6",
    "haiku": "claude-haiku-4-5-20251001",
}


@dataclass
class LLMResponse:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    cost_inr: float
    latency_ms: int
    stop_reason: str


class ClaudeClient:
    """Thin wrapper around the Anthropic async client.

    Responsibilities:
    - Apply prompt caching markers on long system prompts.
    - Record every call (success or failure) into `agent_calls`.
    - Estimate INR cost and attach it to both the returned LLMResponse and the
      persisted row so the BudgetGuard can read a running daily total.
    """

    def __init__(
        self,
        sdk,
        sm: async_sessionmaker[AsyncSession],
        usd_to_inr: float = 83.0,
        default_max_tokens: int = 2048,
    ) -> None:
        self._sdk = sdk
        self._sm = sm
        self._usd_to_inr = usd_to_inr
        self._default_max_tokens = default_max_tokens

    async def complete(
        self,
        *,
        agent_name: str,
        tier: str,
        system: str,
        messages: list[dict],
        cache_system: bool = True,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        model = MODEL_ID[tier]
        sys_param: list[dict] | str
        if cache_system and system:
            sys_param = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        else:
            sys_param = system

        input_hash = sha256(
            (system + "".join(m.get("content", "") if isinstance(m.get("content"), str) else str(m["content"]) for m in messages)).encode()
        ).hexdigest()

        started = time.monotonic()
        error: str | None = None
        try:
            msg = await self._sdk.messages.create(
                model=model,
                max_tokens=max_tokens or self._default_max_tokens,
                system=sys_param,
                messages=messages,
            )
            text = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
            it = int(getattr(msg.usage, "input_tokens", 0) or 0)
            ot = int(getattr(msg.usage, "output_tokens", 0) or 0)
            cit = int(getattr(msg.usage, "cache_read_input_tokens", 0) or 0)
            stop = getattr(msg, "stop_reason", "end_turn")
            elapsed_ms = int((time.monotonic() - started) * 1000)
            cost = estimate_cost_inr(
                tier=tier, input_tokens=it, output_tokens=ot,
                cached_input_tokens=cit, usd_to_inr=self._usd_to_inr,
            )
            await self._log(
                agent=agent_name, input_hash=input_hash, model=model,
                input_tokens=it, output_tokens=ot, cost_inr=cost,
                latency_ms=elapsed_ms, error=None,
            )
            return LLMResponse(
                text=text, model=model, input_tokens=it, output_tokens=ot,
                cached_input_tokens=cit, cost_inr=cost,
                latency_ms=elapsed_ms, stop_reason=stop,
            )
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
            elapsed_ms = int((time.monotonic() - started) * 1000)
            await self._log(
                agent=agent_name, input_hash=input_hash, model=model,
                input_tokens=0, output_tokens=0, cost_inr=0.0,
                latency_ms=elapsed_ms, error=error,
            )
            raise

    async def _log(
        self, *,
        agent: str, input_hash: str, model: str,
        input_tokens: int, output_tokens: int, cost_inr: float,
        latency_ms: int, error: str | None,
    ) -> None:
        async with self._sm() as s:
            s.add(AgentCall(
                agent=agent, input_hash=input_hash, model=model,
                input_tokens=input_tokens, output_tokens=output_tokens,
                cost_inr=cost_inr, latency_ms=latency_ms, error=error,
                created_at=datetime.now(tz=timezone.utc),
            ))
            await s.commit()
