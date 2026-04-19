import asyncio
import time

import pytest

from quant_copilot.rate_limit import TokenBucket, RateLimiterRegistry


async def test_token_bucket_allows_burst_up_to_capacity():
    b = TokenBucket(rate_per_sec=5.0, capacity=5, monotonic=time.monotonic)
    for _ in range(5):
        await b.acquire()  # should not wait
    start = time.monotonic()
    await b.acquire()  # 6th call must wait ~0.2s
    elapsed = time.monotonic() - start
    assert 0.15 < elapsed < 0.5


async def test_registry_keys_isolate_buckets():
    reg = RateLimiterRegistry()
    reg.register("yfinance", rate_per_sec=1000, capacity=10)
    reg.register("screener", rate_per_sec=0.33, capacity=1)  # 1 per 3s
    # Exhaust screener's single token
    async with reg.limit("screener"):
        pass
    # yfinance unaffected
    async with reg.limit("yfinance"):
        pass
