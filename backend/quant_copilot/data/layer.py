from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from quant_copilot.clock import Clock, SystemClock
from quant_copilot.config import Settings
from quant_copilot.data.corporate_actions import CorporateActionSet, apply_adjustments
from quant_copilot.data.fundamentals import FundamentalsService
from quant_copilot.data.news import NewsService
from quant_copilot.data.ohlc import OhlcService, OhlcStore
from quant_copilot.data.sources.nsepython_src import NsePythonSource
from quant_copilot.data.sources.nsetools_src import NsetoolsSource
from quant_copilot.data.sources.yfinance_src import YFinanceSource
from quant_copilot.data.surveillance import SurveillanceService
from quant_copilot.data.ticker_resolver import TickerResolver
from quant_copilot.models import CorporateAction


@dataclass
class DataLayer:
    ohlc: OhlcService
    fundamentals: FundamentalsService
    news: NewsService
    surveillance: SurveillanceService
    resolver: TickerResolver
    sm: async_sessionmaker[AsyncSession]
    clock: Clock

    async def get_ohlc_adjusted(
        self, ticker: str, exchange: str, interval: str, start: date, end: date
    ) -> pd.DataFrame:
        raw = await self.ohlc.get_ohlc(ticker, exchange, interval, start, end)
        async with self.sm() as s:
            actions = (await s.execute(
                select(CorporateAction).where(CorporateAction.ticker == ticker)
                .order_by(CorporateAction.ex_date)
            )).scalars().all()
        action_records = [
            {
                "ex_date": a.ex_date,
                "kind": a.kind,
                "ratio_num": a.ratio_num,
                "ratio_den": a.ratio_den,
                "dividend_per_share": a.dividend_per_share,
            }
            for a in actions
        ]
        return apply_adjustments(raw, CorporateActionSet(action_records))


def build_data_layer(settings: Settings, sm: async_sessionmaker[AsyncSession]) -> DataLayer:
    store = OhlcStore(settings.parquet_root)
    sources = [YFinanceSource(), NsePythonSource(), NsetoolsSource()]
    ohlc_svc = OhlcService(store=store, sources=sources)
    clock = SystemClock(settings.market_tz)
    return DataLayer(
        ohlc=ohlc_svc,
        fundamentals=FundamentalsService(sm=sm),
        news=NewsService(sm=sm),
        surveillance=SurveillanceService(sm=sm, asm_fetcher=lambda: []),
        resolver=TickerResolver(sm),
        sm=sm,
        clock=clock,
    )
