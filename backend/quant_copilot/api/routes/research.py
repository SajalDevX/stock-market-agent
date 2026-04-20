from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter

from quant_copilot.agents.decisions import persist_decision
from quant_copilot.api.deps import LayerDep, OrchestratorDep, SmDep
from quant_copilot.api.schemas import ResearchRequest


router = APIRouter(tags=["research"])


@router.post("/research")
async def research(body: ResearchRequest, orch: OrchestratorDep, sm: SmDep, layer: LayerDep) -> dict:
    report = await orch.research(
        ticker=body.ticker, exchange=body.exchange, timeframe=body.timeframe,
    )
    if body.persist:
        await persist_decision(sm=sm, report=report)

    out = report.model_dump(mode="json")
    if body.include_ohlc:
        end = date.today()
        start = end - timedelta(days=250)
        try:
            df = await layer.get_ohlc_adjusted(body.ticker, body.exchange, "1d", start, end)
        except Exception:
            df = None
        bars = []
        if df is not None and not df.empty:
            df = df.tail(150)
            for ts, row in df.iterrows():
                bars.append({
                    "time": int(ts.timestamp()),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": int(row["volume"]) if "volume" in row else 0,
                })
        out["ohlc"] = bars
    return out
