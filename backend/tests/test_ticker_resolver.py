from datetime import datetime, timezone

import pytest

from quant_copilot.models import Ticker, TickerAlias
from quant_copilot.data.ticker_resolver import TickerResolver


async def _seed(sm):
    async with sm() as s:
        s.add(Ticker(symbol="HDFCBANK", exchange="NSE", name="HDFC Bank Ltd", isin="INE040A01034"))
        s.add(Ticker(symbol="HDFC", exchange="NSE", name="Housing Development Finance Corp (merged)",
                     delisted_on=datetime(2023, 7, 1, tzinfo=timezone.utc)))
        s.add_all([
            TickerAlias(ticker="HDFCBANK", alias="HDFC Bank", kind="name"),
            TickerAlias(ticker="HDFCBANK", alias="HDFC Bank Ltd", kind="name"),
            TickerAlias(ticker="HDFCBANK", alias="HDFCB", kind="code"),
            TickerAlias(ticker="HDFC", alias="HDFC Ltd", kind="name"),
        ])
        await s.commit()


async def test_exact_alias_resolves(sm):
    await _seed(sm)
    r = TickerResolver(sm)
    matches = await r.resolve("HDFC Bank")
    assert [m.ticker for m in matches] == ["HDFCBANK"]
    assert matches[0].confidence == 1.0


async def test_ambiguous_input_returns_multiple(sm):
    await _seed(sm)
    r = TickerResolver(sm)
    matches = await r.resolve("HDFC")
    tickers = sorted(m.ticker for m in matches)
    assert tickers == ["HDFC", "HDFCBANK"]


async def test_fuzzy_match_above_threshold(sm):
    await _seed(sm)
    r = TickerResolver(sm)
    matches = await r.resolve("HDFC Bnk", fuzzy_threshold=85)
    assert any(m.ticker == "HDFCBANK" for m in matches)


async def test_find_tickers_in_headline(sm):
    await _seed(sm)
    r = TickerResolver(sm)
    hits = await r.find_in_text("HDFC Bank Q4 results beat estimates", fuzzy_threshold=95)
    assert [h.ticker for h in hits] == ["HDFCBANK"]
