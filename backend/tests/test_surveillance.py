from datetime import date

import pytest
from sqlalchemy import select

from quant_copilot.data.surveillance import SurveillanceService
from quant_copilot.models import SurveillanceFlag, Ticker


async def test_asm_list_upsert(sm):
    async with sm() as s:
        s.add(Ticker(symbol="XYZ", exchange="NSE", name="XYZ Ltd"))
        s.add(Ticker(symbol="ABC", exchange="NSE", name="ABC Ltd"))
        await s.commit()

    svc = SurveillanceService(sm=sm,
        asm_fetcher=lambda: [{"symbol": "XYZ", "stage": "II"}])
    today = date(2026, 4, 20)
    n = await svc.refresh_asm(today)
    assert n == 1
    # Running again with ABC added and XYZ removed should end-date XYZ and open ABC
    svc2 = SurveillanceService(sm=sm,
        asm_fetcher=lambda: [{"symbol": "ABC", "stage": "I"}])
    await svc2.refresh_asm(today)

    async with sm() as s:
        rows = (await s.execute(select(SurveillanceFlag).order_by(SurveillanceFlag.ticker))).scalars().all()
    assert {(r.ticker, r.list_name, r.removed_on is None) for r in rows} == {
        ("ABC", "ASM", True),
        ("XYZ", "ASM", False),
    }


async def test_is_flagged(sm):
    async with sm() as s:
        s.add(Ticker(symbol="XYZ", exchange="NSE", name="XYZ Ltd"))
        s.add(SurveillanceFlag(ticker="XYZ", list_name="ASM", stage="II",
                               added_on=date(2026, 4, 1), removed_on=None))
        await s.commit()
    svc = SurveillanceService(sm=sm, asm_fetcher=lambda: [])
    flags = await svc.get_flags("XYZ")
    assert flags == [{"list": "ASM", "stage": "II"}]
