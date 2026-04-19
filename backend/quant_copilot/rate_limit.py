from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class TokenBucket:
    rate_per_sec: float
    capacity: int
    monotonic: Callable[[], float] = field(default=time.monotonic)
    _tokens: float = field(init=False)
    _last: float = field(init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

    def __post_init__(self) -> None:
        self._tokens = float(self.capacity)
        self._last = self.monotonic()

    async def acquire(self, n: int = 1) -> None:
        while True:
            async with self._lock:
                now = self.monotonic()
                elapsed = now - self._last
                self._last = now
                self._tokens = min(self.capacity, self._tokens + elapsed * self.rate_per_sec)
                if self._tokens >= n:
                    self._tokens -= n
                    return
                need = n - self._tokens
                wait = need / self.rate_per_sec
            await asyncio.sleep(wait)


class RateLimiterRegistry:
    def __init__(self) -> None:
        self._buckets: dict[str, TokenBucket] = {}

    def register(self, key: str, *, rate_per_sec: float, capacity: int) -> None:
        self._buckets[key] = TokenBucket(rate_per_sec=rate_per_sec, capacity=capacity)

    @asynccontextmanager
    async def limit(self, key: str):
        bucket = self._buckets.get(key)
        if bucket is None:
            raise KeyError(f"No rate limiter registered for {key!r}")
        await bucket.acquire()
        yield
