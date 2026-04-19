from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from quant_copilot.models import Ticker, TickerAlias


@dataclass(frozen=True)
class TickerMatch:
    ticker: str
    confidence: float
    matched_alias: str


def _normalise(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


class TickerResolver:
    def __init__(self, sm: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sm

    async def _all_aliases(self) -> list[tuple[str, str]]:
        async with self._sm() as s:
            rows = (await s.execute(select(TickerAlias.ticker, TickerAlias.alias))).all()
        return [(t, a) for t, a in rows]

    async def resolve(self, text: str, *, fuzzy_threshold: int = 90) -> list[TickerMatch]:
        norm = _normalise(text)
        aliases = await self._all_aliases()

        exact = [TickerMatch(t, 1.0, a) for t, a in aliases if _normalise(a) == norm]
        if exact:
            # Return all exact matches (ambiguity preserved for caller)
            seen: set[str] = set()
            out: list[TickerMatch] = []
            for m in exact:
                if m.ticker not in seen:
                    seen.add(m.ticker)
                    out.append(m)
            return out

        # Also treat the input as a raw symbol match against the ticker column.
        # We use a prefix match so an ambiguous short code like "HDFC" surfaces
        # both the legacy "HDFC" ticker and the still-listed "HDFCBANK".
        upper = text.upper()
        async with self._sm() as s:
            syms = (await s.execute(select(Ticker.symbol).where(Ticker.symbol.like(f"{upper}%")))).scalars().all()
        if syms:
            return [TickerMatch(sym, 1.0, sym) for sym in syms]

        # Fuzzy fallback
        scored: dict[str, TickerMatch] = {}
        for t, a in aliases:
            score = fuzz.ratio(norm, _normalise(a))
            if score >= fuzzy_threshold:
                m = TickerMatch(t, score / 100.0, a)
                if t not in scored or m.confidence > scored[t].confidence:
                    scored[t] = m
        return sorted(scored.values(), key=lambda m: -m.confidence)

    async def find_in_text(self, text: str, *, fuzzy_threshold: int = 95) -> list[TickerMatch]:
        """Used by news ingestion. Scans text for any known alias."""
        norm = _normalise(text)
        aliases = await self._all_aliases()
        hits: dict[str, TickerMatch] = {}
        for t, a in aliases:
            na = _normalise(a)
            if len(na) < 3:
                continue
            # exact substring match
            if na in norm:
                hits[t] = TickerMatch(t, 1.0, a)
                continue
            # partial_ratio on long aliases only (cheap guard)
            if len(na) >= 6:
                score = fuzz.partial_ratio(na, norm)
                if score >= fuzzy_threshold:
                    cand = TickerMatch(t, score / 100.0, a)
                    if t not in hits or cand.confidence > hits[t].confidence:
                        hits[t] = cand
        return sorted(hits.values(), key=lambda m: -m.confidence)
