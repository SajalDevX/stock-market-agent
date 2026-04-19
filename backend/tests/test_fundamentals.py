import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from quant_copilot.data.fundamentals import FundamentalsService, parse_screener_html


HTML = (Path(__file__).parent / "fixtures" / "screener_reliance.html").read_text()


def test_parse_screener_html_extracts_top_ratios():
    parsed = parse_screener_html(HTML)
    assert parsed["pe"] == 28.5
    assert parsed["roe_pct"] == 9.2
    assert parsed["debt_to_equity"] == 0.45


async def test_service_caches_and_snapshots(sm, tmp_path, monkeypatch):
    calls = {"n": 0}

    async def fake_fetch(ticker):
        calls["n"] += 1
        return HTML

    svc = FundamentalsService(sm=sm, html_fetcher=fake_fetch, cache_ttl_days=30)
    fund1 = await svc.get("RELIANCE")
    fund2 = await svc.get("RELIANCE")  # within TTL → cached
    assert calls["n"] == 1
    assert fund1["pe"] == fund2["pe"] == 28.5

    # Snapshot table contains exactly one row
    from sqlalchemy import select
    from quant_copilot.models import FundamentalsSnapshot
    async with sm() as s:
        rows = (await s.execute(select(FundamentalsSnapshot))).scalars().all()
    assert len(rows) == 1
