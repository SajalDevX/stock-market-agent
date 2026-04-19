from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from quant_copilot.models import SurveillanceFlag


Fetcher = Callable[[], list[dict] | Awaitable[list[dict]]]


class SurveillanceService:
    def __init__(self, sm: async_sessionmaker[AsyncSession], asm_fetcher: Fetcher) -> None:
        self._sm = sm
        self._asm = asm_fetcher

    async def _fetch_asm(self) -> list[dict]:
        res = self._asm()
        if hasattr(res, "__await__"):
            res = await res  # type: ignore[misc]
        return list(res)  # type: ignore[arg-type]

    async def refresh_asm(self, today: date) -> int:
        incoming = await self._fetch_asm()
        incoming_map = {r["symbol"]: r.get("stage") for r in incoming}

        added = 0
        async with self._sm() as s:
            open_rows = (await s.execute(
                select(SurveillanceFlag).where(
                    SurveillanceFlag.list_name == "ASM",
                    SurveillanceFlag.removed_on.is_(None),
                )
            )).scalars().all()
            open_by_ticker = {r.ticker: r for r in open_rows}

            # End-date anything not in incoming
            for t, row in open_by_ticker.items():
                if t not in incoming_map:
                    row.removed_on = today

            # Open new entries for tickers not currently open
            for t, stage in incoming_map.items():
                if t not in open_by_ticker:
                    s.add(SurveillanceFlag(
                        ticker=t, list_name="ASM", stage=stage,
                        added_on=today, removed_on=None,
                    ))
                    added += 1
            await s.commit()
        return added

    async def get_flags(self, ticker: str) -> list[dict]:
        async with self._sm() as s:
            rows = (await s.execute(
                select(SurveillanceFlag).where(
                    SurveillanceFlag.ticker == ticker,
                    SurveillanceFlag.removed_on.is_(None),
                )
            )).scalars().all()
        return [{"list": r.list_name, "stage": r.stage} for r in rows]
