from __future__ import annotations

import hashlib
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from quant_copilot.models import Filing

Fetcher = Callable[[], dict | Awaitable[dict]]
SymbolMap = Callable[[str], str | None]


def _hash_filing(url: str, headline: str, filed_at: datetime) -> str:
    return hashlib.sha256(f"{url}|{headline}|{filed_at.isoformat()}".encode()).hexdigest()


class FilingsService:
    def __init__(
        self,
        sm: async_sessionmaker[AsyncSession],
        bse_fetcher: Fetcher,
        symbol_from_scrip: SymbolMap,
    ) -> None:
        self._sm = sm
        self._bse_fetcher = bse_fetcher
        self._symbol = symbol_from_scrip

    async def _fetch_bse(self) -> dict:
        res = self._bse_fetcher()
        if hasattr(res, "__await__"):
            res = await res  # type: ignore[misc]
        return res  # type: ignore[return-value]

    async def ingest_bse(self) -> int:
        data = await self._fetch_bse()
        rows = data.get("Table", []) if isinstance(data, dict) else []
        added = 0
        for r in rows:
            symbol = self._symbol(r.get("SCRIP_CD", ""))
            if not symbol:
                continue
            url = r.get("NSURL") or r.get("ATTACHMENTNAME") or ""
            headline = r.get("HEADLINE", "")
            try:
                filed_at = datetime.fromisoformat(r["NEWS_DT"]).replace(tzinfo=timezone.utc)
            except Exception:
                filed_at = datetime.now(tz=timezone.utc)
            h = _hash_filing(url, headline, filed_at)
            async with self._sm() as s:
                existing = (await s.execute(select(Filing).where(Filing.hash == h))).scalar_one_or_none()
                if existing is not None:
                    continue
                s.add(Filing(
                    hash=h, ticker=symbol, exchange="BSE",
                    kind=r.get("NEWSSUB") or "announcement",
                    url=url, body_text=headline, filed_at=filed_at,
                ))
                await s.commit()
                added += 1
        return added


async def default_bse_fetcher() -> dict:
    url = "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w?pageno=1&strCat=-1&strPrevDate=&strScrip=&strSearch=P&strToDate=&strType=C"
    async with httpx.AsyncClient(timeout=20, headers={"User-Agent": "quant-copilot/0.1"}) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.json()
