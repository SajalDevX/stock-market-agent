import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pandas as pd

from quant_copilot.agents.claude_client import ClaudeClient, LLMResponse
from quant_copilot.agents.citations import CitationVerifier
from quant_copilot.agents.decisions import persist_decision
from quant_copilot.agents.fundamental import FundamentalAgent
from quant_copilot.agents.news import NewsAgent
from quant_copilot.agents.orchestrator import Orchestrator
from quant_copilot.agents.schemas import OrchestratorReport
from quant_copilot.agents.technical import TechnicalAgent
from quant_copilot.data.layer import DataLayer
from quant_copilot.models import ArticleTicker, Decision, NewsArticle, Ticker, TickerAlias


async def _seed(sm):
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    async with sm() as s:
        s.add(Ticker(symbol="RELIANCE", exchange="NSE", name="Reliance Industries Ltd"))
        s.add(TickerAlias(ticker="RELIANCE", alias="Reliance Industries", kind="name"))
        article = NewsArticle(
            hash="h1", source="x", url="https://x/1",
            title="Reliance Q4 profit beats estimates",
            body="Strong quarter.", published_at=now - timedelta(days=1),
            fetched_at=now,
        )
        s.add(article)
        await s.flush()
        s.add(ArticleTicker(article_id=article.id, ticker="RELIANCE", match_confidence=1.0))
        await s.commit()


def _ohlc_up(n=120):
    rng = np.random.default_rng(11)
    close = np.linspace(2000, 2500, n) + rng.normal(0, 5, n)
    idx = pd.date_range("2025-10-01", periods=n, freq="B", tz="UTC")
    return pd.DataFrame({
        "open": close, "high": close + 10, "low": close - 10,
        "close": close, "volume": rng.integers(500_000, 1_000_000, n),
    }, index=idx)


def _resp(text, cost=1.0):
    return LLMResponse(text=text, model="m", input_tokens=500, output_tokens=80,
                       cached_input_tokens=0, cost_inr=cost, latency_ms=800,
                       stop_reason="end_turn")


async def test_full_research_flow_persists_decision(sm):
    await _seed(sm)

    from quant_copilot.data.news import NewsService
    layer = MagicMock(spec=DataLayer)
    layer.sm = sm
    layer.get_ohlc_adjusted = AsyncMock(return_value=_ohlc_up())
    layer.fundamentals = MagicMock()
    layer.fundamentals.get = AsyncMock(return_value={
        "pe": 18, "roe_pct": 20, "roce_pct": 22, "debt_to_equity": 0.5, "earnings_growth_pct": 15,
    })
    layer.surveillance = MagicMock()
    layer.surveillance.get_flags = AsyncMock(return_value=[])
    layer.news = NewsService(sm=sm, feed_fetcher=lambda u: b"")

    client = MagicMock(spec=ClaudeClient)
    client.complete = AsyncMock(side_effect=[
        _resp("Technical uptrend intact."),
        _resp("Fairly valued with solid returns and growth."),
        _resp("""```json
{"headline_summary":"Q4 beat","material_events":["Q4 results"],"sentiment":0.5,
 "reasoning":"Positive","citations":[{"artifact_kind":"news_article","artifact_id":"1","title":"Q4","url":"https://x/1"}]}
```"""),
        _resp("""```json
{"thesis":"Up-trending with supportive fundamentals and positive news.","risks":["macro shock"],
 "entry":2480.0,"stop":2380.0,"target":2650.0}
```"""),
    ])

    tech = TechnicalAgent(data=layer, claude=client)
    fund = FundamentalAgent(data=layer, claude=client)
    news = NewsAgent(data=layer, claude=client, verifier=CitationVerifier(sm=sm))
    orch = Orchestrator(data=layer, claude=client, technical=tech, fundamental=fund, news=news)

    report = await orch.research(ticker="RELIANCE", exchange="NSE", timeframe="swing")
    assert isinstance(report, OrchestratorReport)
    assert report.verdict in ("buy", "hold", "avoid")

    await persist_decision(sm=sm, report=report)

    from sqlalchemy import select
    async with sm() as s:
        rows = (await s.execute(select(Decision))).scalars().all()
    assert len(rows) == 1
    assert rows[0].ticker == "RELIANCE"
