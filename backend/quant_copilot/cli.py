from __future__ import annotations

import asyncio
from datetime import date, timedelta
from pathlib import Path

import typer

from quant_copilot.config import get_settings
from quant_copilot.db import build_engine, build_sessionmaker, set_pragmas
from quant_copilot.data.layer import build_data_layer
from quant_copilot.jobs.archival import nightly_archive
from quant_copilot.jobs.backup import backup_sqlite, prune_backups
from quant_copilot.logging_setup import configure_logging


app = typer.Typer(help="Quant Copilot command line")


def _bootstrap():
    configure_logging()
    settings = get_settings()
    engine = build_engine(settings)
    sm = build_sessionmaker(engine)
    return settings, engine, sm


@app.command("fetch-ohlc")
def fetch_ohlc(ticker: str, exchange: str = "NSE", interval: str = "1d", days: int = 365):
    """Fetch and cache OHLC for a ticker, printing a summary."""
    async def _run():
        settings, engine, sm = _bootstrap()
        await set_pragmas(engine)
        layer = build_data_layer(settings, sm)
        end = date.today()
        start = end - timedelta(days=days)
        df = await layer.get_ohlc_adjusted(ticker, exchange, interval, start, end)
        typer.echo(f"{ticker}: {len(df)} bars [{start}..{end}]")
        if not df.empty:
            typer.echo(df.tail(5).to_string())
    asyncio.run(_run())


@app.command("ingest-news")
def ingest_news(feeds: list[str]):
    """Ingest RSS feeds into the news table."""
    async def _run():
        _, _, sm = _bootstrap()
        settings, engine, _ = _bootstrap()
        await set_pragmas(engine)
        layer = build_data_layer(settings, sm)
        added = await layer.news.ingest(list(feeds))
        typer.echo(f"Ingested {added} new articles")
    asyncio.run(_run())


@app.command("refresh-asm")
def refresh_asm():
    """Refresh ASM flag list (placeholder: no real fetcher wired yet)."""
    async def _run():
        settings, engine, sm = _bootstrap()
        await set_pragmas(engine)
        layer = build_data_layer(settings, sm)
        n = await layer.surveillance.refresh_asm(date.today())
        typer.echo(f"ASM rows added: {n}")
    asyncio.run(_run())


@app.command("archive")
def archive():
    """Run the nightly archival job."""
    async def _run():
        settings, engine, sm = _bootstrap()
        await set_pragmas(engine)
        layer = build_data_layer(settings, sm)
        await nightly_archive(sm=sm, fundamentals=layer.fundamentals)
        typer.echo("Archival complete")
    asyncio.run(_run())


@app.command("backup")
def backup(keep_days: int = 30):
    """Back up the SQLite database."""
    settings, _, _ = _bootstrap()
    out = backup_sqlite(settings.sqlite_path, settings.backup_dir)
    prune_backups(settings.backup_dir, keep_days=keep_days)
    typer.echo(f"Backup written to {out}")


if __name__ == "__main__":
    app()
