from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from quant_copilot.agents.claude_client import ClaudeClient, LLMResponse
from quant_copilot.agents.news import NewsAgent
from quant_copilot.agents.schemas import NewsReport
from quant_copilot.data.layer import DataLayer
from quant_copilot.models import Filing, NewsArticle, Ticker, TickerAlias


async def _seed(sm):
    async with sm() as s:
        s.add(Ticker(symbol="RELIANCE", exchange="NSE", name="Reliance Industries Ltd"))
        s.add(TickerAlias(ticker="RELIANCE", alias="Reliance Industries", kind="name"))
        a = NewsArticle(
            hash="h1", source="x", url="https://x/1",
            title="Reliance Q4 profit beats estimates",
            body="Reliance reported strong Q4 results.",
            published_at=datetime.now(timezone.utc),
            fetched_at=datetime.now(timezone.utc),
        )
        s.add(a)
        s.add(Filing(
            hash="f1", ticker="RELIANCE", exchange="BSE",
            kind="Financial Result", url="https://x/f",
            body_text="Board meeting outcome", filed_at=datetime.now(timezone.utc),
        ))
        await s.commit()


def _client_json(resp: str):
    c = MagicMock(spec=ClaudeClient)
    c.complete = AsyncMock(return_value=LLMResponse(
        text=resp, model="claude-haiku-4-5-20251001",
        input_tokens=2000, output_tokens=300, cached_input_tokens=500,
        cost_inr=0.4, latency_ms=900, stop_reason="end_turn",
    ))
    return c


def _data_layer(sm):
    # NewsAgent uses DataLayer.news.get_for_ticker and sm directly
    from quant_copilot.data.news import NewsService
    layer = MagicMock(spec=DataLayer)
    layer.sm = sm
    layer.news = NewsService(sm=sm, feed_fetcher=lambda u: b"")
    return layer


async def test_news_agent_returns_report_with_citations(sm):
    await _seed(sm)
    resp = """```json
{
  "headline_summary": "Reliance posted a strong Q4.",
  "material_events": ["Q4 results beat"],
  "sentiment": 0.6,
  "reasoning": "Positive results-driven headline.",
  "citations": [
    {"artifact_kind": "news_article", "artifact_id": "1", "title": "Reliance Q4", "url": "https://x/1"}
  ]
}
```"""
    client = _client_json(resp)
    agent = NewsAgent(data=_data_layer(sm), claude=client)
    r = await agent.analyze(ticker="RELIANCE", lookback_days=30)

    assert isinstance(r, NewsReport)
    assert r.sentiment == 0.6
    assert r.score == 0.6
    assert len(r.citations) == 1
    assert r.citations[0].artifact_id == "1"


async def test_news_agent_no_articles_returns_neutral(sm):
    await _seed(sm)  # seeds one article but lookback=0 should exclude it
    client = _client_json("should not be called")
    agent = NewsAgent(data=_data_layer(sm), claude=client)
    r = await agent.analyze(ticker="RELIANCE", lookback_days=0)
    assert r.sentiment == 0.0
    assert r.score == 0.0
    assert r.citations == []
    client.complete.assert_not_awaited()


from quant_copilot.agents.citations import CitationVerifier


async def test_news_agent_retries_when_citations_missing(sm):
    await _seed(sm)
    # First response cites a fake article; second cites the real one.
    bad = """```json
{"headline_summary":"s","material_events":[],"sentiment":0.3,
 "reasoning":"r","citations":[{"artifact_kind":"news_article","artifact_id":"999","title":"fake","url":"u"}]}
```"""
    good = """```json
{"headline_summary":"s","material_events":[],"sentiment":0.3,
 "reasoning":"r","citations":[{"artifact_kind":"news_article","artifact_id":"1","title":"Reliance Q4","url":"https://x/1"}]}
```"""
    client = MagicMock(spec=ClaudeClient)
    client.complete = AsyncMock(side_effect=[
        LLMResponse(text=bad, model="m", input_tokens=1, output_tokens=1, cached_input_tokens=0,
                    cost_inr=0.1, latency_ms=1, stop_reason="end_turn"),
        LLMResponse(text=good, model="m", input_tokens=1, output_tokens=1, cached_input_tokens=0,
                    cost_inr=0.1, latency_ms=1, stop_reason="end_turn"),
    ])
    agent = NewsAgent(data=_data_layer(sm), claude=client, verifier=CitationVerifier(sm=sm))
    r = await agent.analyze(ticker="RELIANCE", lookback_days=30)
    assert r.citations[0].artifact_id == "1"
    assert client.complete.await_count == 2


async def test_news_agent_raises_if_retry_also_ungrounded(sm):
    await _seed(sm)
    bad = """```json
{"headline_summary":"s","material_events":[],"sentiment":0.1,
 "reasoning":"r","citations":[{"artifact_kind":"news_article","artifact_id":"999","title":"fake","url":"u"}]}
```"""
    client = MagicMock(spec=ClaudeClient)
    client.complete = AsyncMock(return_value=LLMResponse(
        text=bad, model="m", input_tokens=1, output_tokens=1, cached_input_tokens=0,
        cost_inr=0.1, latency_ms=1, stop_reason="end_turn",
    ))
    agent = NewsAgent(data=_data_layer(sm), claude=client, verifier=CitationVerifier(sm=sm))
    with pytest.raises(RuntimeError, match="citations"):
        await agent.analyze(ticker="RELIANCE", lookback_days=30)
    assert client.complete.await_count == 2  # one retry
