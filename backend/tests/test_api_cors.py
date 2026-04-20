import os

import pytest
from httpx import ASGITransport, AsyncClient

from quant_copilot.api.app import create_app
from quant_copilot.config import Settings


def _settings(tmp_path):
    os.environ["ANTHROPIC_API_KEY"] = "sk-test"
    os.environ["DATA_DIR"] = str(tmp_path / "data")
    os.environ["BACKUP_DIR"] = str(tmp_path / "backups")
    return Settings()  # type: ignore[call-arg]


async def test_cors_headers_present_on_health(tmp_path):
    app = create_app(settings=_settings(tmp_path))
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/health", headers={"Origin": "http://localhost:3000"})
            assert r.status_code == 200
            assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
