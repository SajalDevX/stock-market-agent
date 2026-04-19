from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from quant_copilot.models import FundamentalsSnapshot


def _num(s: str) -> float | None:
    s = s.replace("₹", "").replace(",", "").replace("%", "").strip()
    try:
        return float(s.split()[0])
    except (ValueError, IndexError):
        return None


_KEY_MAP = {
    "Stock P/E": "pe",
    "Book Value": "book_value",
    "ROE": "roe_pct",
    "ROCE": "roce_pct",
    "Debt to equity": "debt_to_equity",
    "Market Cap": "market_cap_cr",
    "Dividend Yield": "dividend_yield_pct",
    "Face Value": "face_value",
}


def parse_screener_html(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    out: dict = {}
    for li in soup.select("#top-ratios li"):
        name = li.select_one(".name")
        val = li.select_one(".value")
        if not name or not val:
            continue
        key = _KEY_MAP.get(name.get_text(strip=True))
        if key:
            out[key] = _num(val.get_text(strip=True))
    return out


async def default_fetcher(ticker: str) -> str:
    url = f"https://www.screener.in/company/{ticker}/consolidated/"
    async with httpx.AsyncClient(timeout=20, headers={"User-Agent": "quant-copilot/0.1"}) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.text


class FundamentalsService:
    def __init__(
        self,
        sm: async_sessionmaker[AsyncSession],
        html_fetcher: Callable[[str], Awaitable[str]] = default_fetcher,
        cache_ttl_days: int = 30,
    ) -> None:
        self._sm = sm
        self._fetch = html_fetcher
        self._ttl = timedelta(days=cache_ttl_days)

    async def get(self, ticker: str) -> dict:
        async with self._sm() as s:
            row = (
                await s.execute(
                    select(FundamentalsSnapshot)
                    .where(FundamentalsSnapshot.ticker == ticker)
                    .order_by(FundamentalsSnapshot.snapshot_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            if row is not None:
                snap_at = row.snapshot_at
                if snap_at.tzinfo is None:
                    snap_at = snap_at.replace(tzinfo=timezone.utc)
                if (datetime.now(tz=timezone.utc) - snap_at) < self._ttl:
                    return json.loads(row.payload_json)

        html = await self._fetch(ticker)
        parsed = parse_screener_html(html)
        async with self._sm() as s:
            snap = FundamentalsSnapshot(
                ticker=ticker,
                snapshot_at=datetime.now(tz=timezone.utc),
                payload_json=json.dumps(parsed),
            )
            s.add(snap)
            await s.commit()
        return parsed

    async def snapshot_all(self, tickers: list[str]) -> None:
        """Forward-archival: called nightly to force-record a snapshot even if cache is warm."""
        for t in tickers:
            try:
                html = await self._fetch(t)
                parsed = parse_screener_html(html)
                async with self._sm() as s:
                    s.add(FundamentalsSnapshot(
                        ticker=t,
                        snapshot_at=datetime.now(tz=timezone.utc),
                        payload_json=json.dumps(parsed),
                    ))
                    await s.commit()
            except Exception:
                # Archival is best-effort; log & move on (logging wired in Task 19)
                continue
