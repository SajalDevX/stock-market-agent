import os
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from quant_copilot.api.app import create_app
from quant_copilot.config import Settings
from quant_copilot.models import Ticker, WatchlistEntry


def _settings(tmp_path):
    os.environ["ANTHROPIC_API_KEY"] = "sk-test"
    os.environ["DATA_DIR"] = str(tmp_path / "data")
    os.environ["BACKUP_DIR"] = str(tmp_path / "backups")
    return Settings()  # type: ignore[call-arg]


async def test_watchlist_add_list_remove(tmp_path):
    app = create_app(settings=_settings(tmp_path))
    # httpx 0.28 ASGITransport does not dispatch lifespan events, so we run
    # the lifespan context manually to populate app.state.
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            # Seed a ticker so FK is satisfied
            sm = app.state.sm
            async with sm() as s:
                s.add(Ticker(symbol="RELIANCE", exchange="NSE", name="Reliance"))
                await s.commit()

            # Empty initially
            r = await c.get("/watchlist")
            assert r.status_code == 200
            assert r.json() == []

            # Add
            r = await c.post("/watchlist/RELIANCE", json={})
            assert r.status_code == 200
            assert r.json()["ticker"] == "RELIANCE"

            # List
            r = await c.get("/watchlist")
            assert r.status_code == 200
            assert [e["ticker"] for e in r.json()] == ["RELIANCE"]

            # Idempotent add
            r = await c.post("/watchlist/RELIANCE", json={})
            assert r.status_code == 200

            # Delete
            r = await c.delete("/watchlist/RELIANCE")
            assert r.status_code == 204

            # Gone
            r = await c.get("/watchlist")
            assert r.json() == []


async def test_watchlist_rejects_unknown_ticker(tmp_path):
    app = create_app(settings=_settings(tmp_path))
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/watchlist/UNKNOWN", json={})
            assert r.status_code == 404
