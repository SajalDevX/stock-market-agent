from __future__ import annotations

from fastapi import APIRouter

from quant_copilot.api.deps import LayerDep
from quant_copilot.backtest.engine import BacktestEngine
from quant_copilot.backtest.strategy import Strategy


router = APIRouter(tags=["backtest"])


@router.post("/backtest")
async def run_backtest(strategy: Strategy, layer: LayerDep) -> dict:
    engine = BacktestEngine(layer)
    result = await engine.run(strategy)
    return {
        "summary": result.summary,
        "bars_seen": result.bars_seen,
        "trades": [t.model_dump(mode="json") for t in result.trades],
        "equity_curve": result.equity_curve,
    }
