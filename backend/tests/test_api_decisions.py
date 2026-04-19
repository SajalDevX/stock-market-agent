import os
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from quant_copilot.api.app import create_app
from quant_copilot.config import Settings
from quant_copilot.models import Decision, DecisionOutcome, Ticker


def _settings(tmp_path):
    os.environ["ANTHROPIC_API_KEY"] = "sk-test"
    os.environ["DATA_DIR"] = str(tmp_path / "data")
    os.environ["BACKUP_DIR"] = str(tmp_path / "backups")
    return Settings()  # type: ignore[call-arg]


async def test_list_decisions_and_get_one(tmp_path):
    app = create_app(settings=_settings(tmp_path))
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            sm = app.state.sm
            async with sm() as s:
                s.add(Ticker(symbol="RELIANCE", exchange="NSE", name="Reliance"))
                await s.flush()
                d = Decision(
                    ticker="RELIANCE", timeframe="swing", verdict="buy", conviction=65,
                    entry=2800.0, stop=2700.0, target=3000.0, ref_price=2825.0,
                    created_at=datetime.now(timezone.utc),
                )
                s.add(d)
                await s.flush()
                s.add(DecisionOutcome(decision_id=d.id, horizon="7d",
                                       computed_at=datetime.now(timezone.utc), return_pct=2.3))
                await s.commit()

            r = await c.get("/decisions")
            assert r.status_code == 200
            data = r.json()
            assert len(data) == 1
            assert data[0]["ticker"] == "RELIANCE"
            assert data[0]["verdict"] == "buy"

            did = data[0]["id"]
            r = await c.get(f"/decisions/{did}")
            assert r.status_code == 200
            body = r.json()
            assert body["ticker"] == "RELIANCE"
            assert body["outcomes"] == [{"horizon": "7d", "return_pct": 2.3}]


async def test_get_decision_404(tmp_path):
    app = create_app(settings=_settings(tmp_path))
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/decisions/9999")
            assert r.status_code == 404
