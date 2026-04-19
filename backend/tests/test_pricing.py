from quant_copilot.agents.pricing import estimate_cost_inr, MODEL_PRICING, ModelTier


def test_known_models_have_pricing():
    for tier in ("opus", "sonnet", "haiku"):
        assert tier in MODEL_PRICING
        p = MODEL_PRICING[tier]
        assert p.input_usd_per_mtok > 0
        assert p.output_usd_per_mtok > 0
        assert 0 < p.cached_input_usd_per_mtok < p.input_usd_per_mtok


def test_estimate_cost_sonnet_typical_query():
    # Sonnet 4.6: $3/M in, $15/M out. At ~83 INR/USD.
    cost = estimate_cost_inr(
        tier="sonnet",
        input_tokens=20_000,
        output_tokens=2_000,
        cached_input_tokens=0,
        usd_to_inr=83.0,
    )
    # 20k * $3/M = $0.06; 2k * $15/M = $0.03; total $0.09 ≈ 7.47 INR
    assert 6.0 < cost < 9.0


def test_estimate_cost_haiku_with_cache_hit():
    # Haiku 4.5: $1/M in, $5/M out. Cached read is 10% of input rate.
    cost = estimate_cost_inr(
        tier="haiku",
        input_tokens=1_000,
        output_tokens=500,
        cached_input_tokens=10_000,
        usd_to_inr=83.0,
    )
    # Regular input: 1k * $1/M = $0.001
    # Cached input : 10k * $0.10/M = $0.001
    # Output       : 500 * $5/M  = $0.0025
    # Total ~$0.0045 ≈ 0.37 INR
    assert 0.2 < cost < 0.6


def test_unknown_tier_raises():
    import pytest
    with pytest.raises(KeyError):
        estimate_cost_inr(tier="not-a-model", input_tokens=1, output_tokens=1,
                         cached_input_tokens=0, usd_to_inr=83.0)
