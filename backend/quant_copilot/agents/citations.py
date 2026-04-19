from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from quant_copilot.agents.schemas import NewsCitation
from quant_copilot.models import ArticleTicker, Filing, NewsArticle


@dataclass
class CitationResult:
    all_valid: bool
    missing_ids: list[str]   # e.g. ["news_article:42", "filing:7"]


class CitationVerifier:
    """Resolves artifact IDs cited by an agent against real data-layer rows."""

    def __init__(self, sm: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sm

    async def verify(self, citations: list[NewsCitation]) -> CitationResult:
        by_kind: dict[str, set[int]] = {"news_article": set(), "filing": set()}
        for c in citations:
            try:
                by_kind[c.artifact_kind].add(int(c.artifact_id))
            except (ValueError, KeyError):
                # Unknown kind or non-int id → treat as missing
                by_kind.setdefault(c.artifact_kind, set())
        missing: list[str] = []
        async with self._sm() as s:
            for kind, ids in by_kind.items():
                if not ids:
                    continue
                model = NewsArticle if kind == "news_article" else Filing
                rows = (await s.execute(
                    select(model.id).where(model.id.in_(ids))
                )).scalars().all()
                found = set(rows)
                for i in ids:
                    if i not in found:
                        missing.append(f"{kind}:{i}")
        return CitationResult(all_valid=not missing, missing_ids=sorted(missing))

    async def available_ids(self, *, ticker: str, news_lookback_days: int = 7) -> list[str]:
        since = datetime.now(tz=timezone.utc) - timedelta(days=news_lookback_days)
        async with self._sm() as s:
            news_ids = (await s.execute(
                select(NewsArticle.id)
                .join(ArticleTicker, ArticleTicker.article_id == NewsArticle.id)
                .where(ArticleTicker.ticker == ticker, NewsArticle.published_at >= since)
            )).scalars().all()
            filing_ids = (await s.execute(
                select(Filing.id).where(Filing.ticker == ticker, Filing.filed_at >= since)
            )).scalars().all()
        return [f"news_article:{i}" for i in news_ids] + [f"filing:{i}" for i in filing_ids]
