import asyncio
import os
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from quant_copilot.models import Base


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def engine(tmp_path):
    db = tmp_path / "test.db"
    eng = create_async_engine(f"sqlite+aiosqlite:///{db}", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def sm(engine):
    from sqlalchemy.ext.asyncio import async_sessionmaker
    return async_sessionmaker(engine, expire_on_commit=False)
