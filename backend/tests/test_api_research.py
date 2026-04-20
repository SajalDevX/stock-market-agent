import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from quant_copilot.agents.schemas import OrchestratorReport
from quant_copilot.api.app import create_app
from quant_copilot.config import Settings


def _settings(tmp_path):
    os.environ["ANTHROPIC_API_KEY"] = "sk-test"
    os.environ["DATA_DIR"] = str(tmp_path / "data")
    os.environ["BACKUP_DIR"] = str(tmp_path / "backups")
    return Settings()  # type: ignore[call-arg]


async def test_research_endpoint_returns_orchestrator_report(tmp_path):
    app = create_app(settings=_settings(tmp_path))
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            fake_report = OrchestratorReport(
                ticker="RELIANCE", timeframe="swing",
                verdict="buy", conviction=60,
                conviction_breakdown={"technical": 0.5},
                thesis="Good setup.", risks=["macro shock"],
                entry=2820.0, stop=2700.0, target=3000.0,
                ref_price=2825.0,
                agent_reports={}, disagreements=[],
            )
            app.state.orchestrator = MagicMock()
            app.state.orchestrator.research = AsyncMock(return_value=fake_report)

            r = await c.post("/research", json={"ticker": "RELIANCE", "timeframe": "swing", "persist": False})
            assert r.status_code == 200
            body = r.json()
            assert body["verdict"] == "buy"
            assert body["conviction"] == 60
            assert body["ticker"] == "RELIANCE"


async def test_research_persists_when_flag_set(tmp_path):
    app = create_app(settings=_settings(tmp_path))
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            from quant_copilot.models import Ticker
            sm = app.state.sm
            async with sm() as s:
                s.add(Ticker(symbol="RELIANCE", exchange="NSE", name="Reliance"))
                await s.commit()

            fake_report = OrchestratorReport(
                ticker="RELIANCE", timeframe="swing", verdict="hold", conviction=30,
                conviction_breakdown={}, thesis="t", risks=[],
                entry=None, stop=None, target=None, ref_price=2825.0,
                agent_reports={}, disagreements=[],
            )
            app.state.orchestrator = MagicMock()
            app.state.orchestrator.research = AsyncMock(return_value=fake_report)

            r = await c.post("/research", json={"ticker": "RELIANCE", "timeframe": "swing", "persist": True})
            assert r.status_code == 200

            from sqlalchemy import select
            from quant_copilot.models import Decision
            async with sm() as s:
                rows = (await s.execute(select(Decision))).scalars().all()
            assert len(rows) == 1


async def test_research_returns_ohlc_when_flag_set(tmp_path):
    import pandas as pd
    from unittest.mock import AsyncMock, MagicMock

    from quant_copilot.agents.schemas import OrchestratorReport

    app = create_app(settings=_settings(tmp_path))
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            fake = OrchestratorReport(
                ticker="RELIANCE", timeframe="swing", verdict="hold", conviction=10,
                conviction_breakdown={}, thesis="t", risks=[],
                entry=None, stop=None, target=None, ref_price=2800.0,
                agent_reports={}, disagreements=[],
            )
            app.state.orchestrator = MagicMock()
            app.state.orchestrator.research = AsyncMock(return_value=fake)

            import numpy as np
            idx = pd.date_range("2026-01-01", periods=5, freq="B", tz="UTC")
            df = pd.DataFrame({
                "open":[1.0]*5,"high":[2.0]*5,"low":[0.5]*5,"close":[1.5]*5,"volume":[10]*5,
            }, index=idx)
            app.state.layer.get_ohlc_adjusted = AsyncMock(return_value=df)

            r = await c.post("/research", json={"ticker": "RELIANCE", "timeframe": "swing",
                                                 "persist": False, "include_ohlc": True})
            assert r.status_code == 200
            body = r.json()
            assert "ohlc" in body
            assert len(body["ohlc"]) == 5
            assert body["ohlc"][0]["close"] == 1.5
