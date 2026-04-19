from datetime import datetime, timezone
from pathlib import Path

import pytest

from quant_copilot.data.news import NewsService, parse_rss_bytes
from quant_copilot.models import NewsArticle, ArticleTicker, Ticker, TickerAlias


FIX = (Path(__file__).parent / "fixtures" / "moneycontrol_rss.xml").read_bytes()


def test_parse_rss_returns_items():
    items = parse_rss_bytes(FIX)
    assert len(items) == 2
    titles = [i.title for i in items]
    assert "HDFC Bank Q4 profit beats estimates" in titles


async def _seed_tickers(sm):
    async with sm() as s:
        s.add_all([
            Ticker(symbol="HDFCBANK", exchange="NSE", name="HDFC Bank Ltd"),
            Ticker(symbol="RELIANCE", exchange="NSE", name="Reliance Industries Ltd"),
            TickerAlias(ticker="HDFCBANK", alias="HDFC Bank", kind="name"),
            TickerAlias(ticker="RELIANCE", alias="Reliance Industries", kind="name"),
        ])
        await s.commit()


async def test_news_ingest_creates_articles_and_matches(sm):
    await _seed_tickers(sm)
    svc = NewsService(sm=sm, feed_fetcher=lambda url: FIX)
    n = await svc.ingest(["https://example.com/rss"])
    assert n == 2

    from sqlalchemy import select
    async with sm() as s:
        articles = (await s.execute(select(NewsArticle))).scalars().all()
        assert len(articles) == 2
        links = (await s.execute(select(ArticleTicker))).all()
        tickers = sorted(l[0].ticker for l in links)
        assert tickers == ["HDFCBANK", "RELIANCE"]


async def test_news_ingest_is_idempotent(sm):
    await _seed_tickers(sm)
    svc = NewsService(sm=sm, feed_fetcher=lambda url: FIX)
    await svc.ingest(["https://example.com/rss"])
    n2 = await svc.ingest(["https://example.com/rss"])
    assert n2 == 0  # all deduped on hash


async def test_news_service_query_by_ticker(sm):
    await _seed_tickers(sm)
    svc = NewsService(sm=sm, feed_fetcher=lambda url: FIX)
    await svc.ingest(["https://example.com/rss"])
    items = await svc.get_for_ticker("HDFCBANK", lookback_days=30)
    assert len(items) == 1
    assert items[0].title.startswith("HDFC Bank")
