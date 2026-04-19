from datetime import datetime, timezone

import pytest

from quant_copilot.agents.citations import CitationVerifier, CitationResult
from quant_copilot.agents.schemas import NewsCitation
from quant_copilot.models import ArticleTicker, Filing, NewsArticle


async def _seed(sm):
    async with sm() as s:
        article = NewsArticle(
            hash="h1", source="x", url="https://x/1",
            title="Real article", body="body",
            published_at=datetime.now(timezone.utc),
            fetched_at=datetime.now(timezone.utc),
        )
        s.add(article)
        await s.flush()
        s.add(ArticleTicker(
            article_id=article.id, ticker="RELIANCE", match_confidence=1.0,
        ))
        s.add(Filing(
            hash="f1", ticker="RELIANCE", exchange="BSE",
            kind="Financial Result", url="https://x/f1",
            body_text="h", filed_at=datetime.now(timezone.utc),
        ))
        await s.commit()


async def test_verify_resolves_existing_citation(sm):
    await _seed(sm)
    v = CitationVerifier(sm=sm)
    cit = NewsCitation(artifact_kind="news_article", artifact_id="1",
                       title="Real", url="https://x/1")
    result = await v.verify([cit])
    assert isinstance(result, CitationResult)
    assert result.all_valid is True
    assert result.missing_ids == []


async def test_verify_flags_missing_citation(sm):
    await _seed(sm)
    v = CitationVerifier(sm=sm)
    cits = [
        NewsCitation(artifact_kind="news_article", artifact_id="1", title="ok", url="u"),
        NewsCitation(artifact_kind="news_article", artifact_id="999", title="fake", url="u"),
        NewsCitation(artifact_kind="filing", artifact_id="1", title="real filing", url="u"),
        NewsCitation(artifact_kind="filing", artifact_id="42", title="fake filing", url="u"),
    ]
    r = await v.verify(cits)
    assert r.all_valid is False
    assert sorted(r.missing_ids) == ["filing:42", "news_article:999"]


async def test_available_ids_returns_ids_as_strings(sm):
    await _seed(sm)
    v = CitationVerifier(sm=sm)
    ids = await v.available_ids(ticker="RELIANCE", news_lookback_days=30)
    assert "news_article:1" in ids
    assert "filing:1" in ids
