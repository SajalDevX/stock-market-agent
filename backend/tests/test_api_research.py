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
