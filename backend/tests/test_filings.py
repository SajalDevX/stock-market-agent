import hashlib
from datetime import datetime, timezone

import pytest

from quant_copilot.data.filings import FilingsService
from quant_copilot.models import Ticker, Filing


SAMPLE_BSE_JSON = {
    "Table": [
        {
            "SCRIP_CD": "500325",
            "COMPANYNAME": "RELIANCE",
            "HEADLINE": "Q4 FY26 Results",
            "ATTACHMENTNAME": "results.pdf",
            "NEWSSUB": "Financial Result",
            "NEWS_DT": "2026-04-18T10:00:00",
            "NSURL": "https://example.com/filing/reliance-q4.pdf",
        }
    ]
}


async def _seed(sm):
    async with sm() as s:
        s.add(Ticker(symbol="RELIANCE", exchange="NSE", name="Reliance Industries Ltd"))
        await s.commit()


async def test_filings_ingest_and_dedup(sm):
    await _seed(sm)
    svc = FilingsService(sm=sm, bse_fetcher=lambda: SAMPLE_BSE_JSON, symbol_from_scrip=lambda s: "RELIANCE")
    n = await svc.ingest_bse()
    assert n == 1
    # Idempotent
    assert await svc.ingest_bse() == 0

    from sqlalchemy import select
    async with sm() as s:
        rows = (await s.execute(select(Filing))).scalars().all()
    assert len(rows) == 1
    assert rows[0].ticker == "RELIANCE"
    assert rows[0].kind == "Financial Result"
