from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from quant_copilot.config import Settings
from quant_copilot.paths import ensure_dirs


def build_engine(settings: Settings):
    ensure_dirs(settings)
    url = f"sqlite+aiosqlite:///{settings.sqlite_path}"
    engine = create_async_engine(
        url,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    return engine


def build_sessionmaker(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def session_scope(sm: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with sm() as s:
        try:
            yield s
            await s.commit()
        except Exception:
            await s.rollback()
            raise


async def set_pragmas(engine) -> None:
    async with engine.begin() as conn:
        await conn.exec_driver_sql("PRAGMA journal_mode=WAL")
        await conn.exec_driver_sql("PRAGMA synchronous=NORMAL")
        await conn.exec_driver_sql("PRAGMA foreign_keys=ON")
