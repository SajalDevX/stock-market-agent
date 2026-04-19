"""Per-model pricing constants for Claude API cost tracking.

Prices are rough approximations of list prices as of early 2026. Update these
when Anthropic changes pricing. USD→INR is passed in so callers can use a
daily-updated rate (or the default ~83).

Cached input pricing is 10% of regular input pricing (Anthropic's stated
cache-read rate).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ModelTier = Literal["opus", "sonnet", "haiku"]


@dataclass(frozen=True)
class Pricing:
    input_usd_per_mtok: float
    output_usd_per_mtok: float
    cached_input_usd_per_mtok: float


MODEL_PRICING: dict[str, Pricing] = {
    "opus":   Pricing(input_usd_per_mtok=15.0, output_usd_per_mtok=75.0, cached_input_usd_per_mtok=1.5),
    "sonnet": Pricing(input_usd_per_mtok=3.0,  output_usd_per_mtok=15.0, cached_input_usd_per_mtok=0.3),
    "haiku":  Pricing(input_usd_per_mtok=1.0,  output_usd_per_mtok=5.0,  cached_input_usd_per_mtok=0.1),
}


def estimate_cost_inr(
    *,
    tier: str,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int,
    usd_to_inr: float,
) -> float:
    p = MODEL_PRICING[tier]
    usd = (
        input_tokens * p.input_usd_per_mtok / 1_000_000
        + cached_input_tokens * p.cached_input_usd_per_mtok / 1_000_000
        + output_tokens * p.output_usd_per_mtok / 1_000_000
    )
    return usd * usd_to_inr
