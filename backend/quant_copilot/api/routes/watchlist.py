from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import delete, select

from quant_copilot.api.deps import SmDep
from quant_copilot.api.schemas import WatchlistAddRequest
from quant_copilot.models import Ticker, WatchlistEntry


router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("")
async def list_watchlist(sm: SmDep) -> list[dict]:
    async with sm() as s:
        rows = (await s.execute(
            select(WatchlistEntry).order_by(WatchlistEntry.ticker)
        )).scalars().all()
    return [
        {"ticker": r.ticker, "added_at": r.added_at.isoformat(), "rules_json": r.rules_json}
        for r in rows
    ]


@router.post("/{ticker}")
async def add_watchlist(ticker: str, body: WatchlistAddRequest, sm: SmDep) -> dict:
    async with sm() as s:
        exists = (await s.execute(select(Ticker).where(Ticker.symbol == ticker))).scalar_one_or_none()
        if exists is None:
            raise HTTPException(status_code=404, detail=f"Unknown ticker: {ticker}")
        existing = (await s.execute(
            select(WatchlistEntry).where(WatchlistEntry.ticker == ticker)
        )).scalar_one_or_none()
        if existing is not None:
            existing.rules_json = body.rules_json
            await s.commit()
            return {"ticker": ticker, "added_at": existing.added_at.isoformat(),
                    "rules_json": existing.rules_json}
        entry = WatchlistEntry(
            ticker=ticker,
            added_at=datetime.now(timezone.utc),
            rules_json=body.rules_json,
        )
        s.add(entry)
        await s.commit()
        return {"ticker": ticker, "added_at": entry.added_at.isoformat(),
                "rules_json": entry.rules_json}


@router.delete("/{ticker}", status_code=204)
async def remove_watchlist(ticker: str, sm: SmDep) -> Response:
    async with sm() as s:
        await s.execute(delete(WatchlistEntry).where(WatchlistEntry.ticker == ticker))
        await s.commit()
    return Response(status_code=204)
