from __future__ import annotations

import hashlib
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from quant_copilot.data.sources.rss_src import RssItem, parse_rss_bytes
from quant_copilot.data.ticker_resolver import TickerResolver
from quant_copilot.models import ArticleTicker, NewsArticle


def _hash(url: str, title: str) -> str:
    return hashlib.sha256(f"{url}|{title}".encode()).hexdigest()


FetchFn = Callable[[str], Awaitable[bytes] | bytes]


async def default_feed_fetcher(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=20, headers={"User-Agent": "quant-copilot/0.1"}) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.content


# Re-export for tests
__all__ = ["NewsService", "parse_rss_bytes"]


class NewsService:
    def __init__(
        self,
        sm: async_sessionmaker[AsyncSession],
        feed_fetcher: FetchFn = default_feed_fetcher,
        resolver: TickerResolver | None = None,
    ) -> None:
        self._sm = sm
        self._fetch = feed_fetcher
        self._resolver = resolver or TickerResolver(sm)

    async def _fetch_bytes(self, url: str) -> bytes:
        res = self._fetch(url)
        if hasattr(res, "__await__"):
            res = await res  # type: ignore[misc]
        return res  # type: ignore[return-value]

    async def ingest(self, feed_urls: list[str]) -> int:
        added = 0
        for url in feed_urls:
            try:
                raw = await self._fetch_bytes(url)
            except Exception:
                continue
            items = parse_rss_bytes(raw, source_hint=url)
            for item in items:
                h = _hash(item.url, item.title)
                async with self._sm() as s:
                    existing = (await s.execute(
                        select(NewsArticle).where(NewsArticle.hash == h)
                    )).scalar_one_or_none()
                    if existing is not None:
                        continue
                    art = NewsArticle(
                        hash=h, source=item.source, url=item.url,
                        title=item.title, body=item.body,
                        published_at=item.published_at,
                        fetched_at=datetime.now(tz=timezone.utc),
                    )
                    s.add(art)
                    await s.flush()
                    # Match tickers
                    full_text = f"{item.title}. {item.body}"
                    matches = await self._resolver.find_in_text(full_text, fuzzy_threshold=95)
                    for m in matches:
                        s.add(ArticleTicker(article_id=art.id, ticker=m.ticker, match_confidence=m.confidence))
                    await s.commit()
                    added += 1
        return added

    async def get_for_ticker(self, ticker: str, *, lookback_days: int = 7) -> list[NewsArticle]:
        since = datetime.now(tz=timezone.utc) - timedelta(days=lookback_days)
        async with self._sm() as s:
            rows = (await s.execute(
                select(NewsArticle)
                .join(ArticleTicker, ArticleTicker.article_id == NewsArticle.id)
                .where(ArticleTicker.ticker == ticker, NewsArticle.published_at >= since)
                .order_by(NewsArticle.published_at.desc())
            )).scalars().all()
        return list(rows)
