import os
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from quant_copilot.api.app import create_app
from quant_copilot.config import Settings


def _test_settings(tmp_path) -> Settings:
    os.environ["ANTHROPIC_API_KEY"] = "sk-test"
    os.environ["DATA_DIR"] = str(tmp_path / "data")
    os.environ["BACKUP_DIR"] = str(tmp_path / "backups")
    return Settings()  # type: ignore[call-arg]


async def test_health_returns_ok(tmp_path):
    app = create_app(settings=_test_settings(tmp_path))
    # Bootstrap tables on the ephemeral DB created by lifespan.
    # httpx 0.28 ASGITransport does not dispatch lifespan events, so we run
    # the lifespan context manually to populate app.state.
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            # trigger lifespan startup
            await c.__aenter__ if False else None  # no-op, AsyncClient enters via context

            r = await c.get("/health")
            assert r.status_code == 200
            body = r.json()
            assert body["status"] == "ok"
            assert "llm_budget_spent_today" in body
            assert body["daily_cap_inr"] > 0
            assert body["scheduler_running"] is True
