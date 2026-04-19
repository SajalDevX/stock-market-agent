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

import json as _json
import os

from anthropic import AsyncAnthropic

from quant_copilot.agents.budget import BudgetGuard
from quant_copilot.agents.claude_client import ClaudeClient
from quant_copilot.agents.technical import TechnicalAgent


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


@app.command("analyze-technical")
def analyze_technical(
    ticker: str,
    exchange: str = "NSE",
    timeframe: str = "swing",
    tier: str = "sonnet",
):
    """Run the Technical Analyst agent on a ticker and print the report JSON."""
    async def _run():
        settings, engine, sm = _bootstrap()
        await set_pragmas(engine)
        layer = build_data_layer(settings, sm)
        sdk = AsyncAnthropic(api_key=settings.anthropic_api_key)
        guard = BudgetGuard(sm=sm, daily_cap_inr=settings.daily_llm_budget_inr)
        client = ClaudeClient(sdk=sdk, sm=sm, usd_to_inr=83.0, budget=guard,
                              min_projected_cost_inr=2.0)
        agent = TechnicalAgent(data=layer, claude=client, tier=tier)
        report = await agent.analyze(ticker=ticker, exchange=exchange, timeframe=timeframe)
        typer.echo(_json.dumps(report.model_dump(mode="json"), indent=2, default=str))
    asyncio.run(_run())


from quant_copilot.agents.fundamental import FundamentalAgent


@app.command("analyze-fundamental")
def analyze_fundamental(ticker: str, tier: str = "sonnet"):
    """Run the Fundamental Analyst agent on a ticker."""
    async def _run():
        settings, engine, sm = _bootstrap()
        await set_pragmas(engine)
        layer = build_data_layer(settings, sm)
        sdk = AsyncAnthropic(api_key=settings.anthropic_api_key)
        guard = BudgetGuard(sm=sm, daily_cap_inr=settings.daily_llm_budget_inr)
        client = ClaudeClient(sdk=sdk, sm=sm, usd_to_inr=83.0, budget=guard)
        agent = FundamentalAgent(data=layer, claude=client, tier=tier)
        report = await agent.analyze(ticker=ticker)
        typer.echo(_json.dumps(report.model_dump(mode="json"), indent=2, default=str))
    asyncio.run(_run())


from quant_copilot.agents.citations import CitationVerifier
from quant_copilot.agents.news import NewsAgent


@app.command("analyze-news")
def analyze_news(ticker: str, lookback_days: int = 7, tier: str = "haiku"):
    """Run the News agent on a ticker (with citation grounding)."""
    async def _run():
        settings, engine, sm = _bootstrap()
        await set_pragmas(engine)
        layer = build_data_layer(settings, sm)
        sdk = AsyncAnthropic(api_key=settings.anthropic_api_key)
        guard = BudgetGuard(sm=sm, daily_cap_inr=settings.daily_llm_budget_inr)
        client = ClaudeClient(sdk=sdk, sm=sm, usd_to_inr=83.0, budget=guard)
        verifier = CitationVerifier(sm=sm)
        agent = NewsAgent(data=layer, claude=client, tier=tier, verifier=verifier)
        report = await agent.analyze(ticker=ticker, lookback_days=lookback_days)
        typer.echo(_json.dumps(report.model_dump(mode="json"), indent=2, default=str))
    asyncio.run(_run())


from quant_copilot.agents.decisions import persist_decision
from quant_copilot.agents.orchestrator import Orchestrator


@app.command("analyze")
def analyze(
    ticker: str,
    exchange: str = "NSE",
    timeframe: str = "swing",
    tier: str = "sonnet",
    news_tier: str = "haiku",
    persist: bool = True,
):
    """Run full research via the Orchestrator and print the verdict JSON."""
    async def _run():
        settings, engine, sm = _bootstrap()
        await set_pragmas(engine)
        layer = build_data_layer(settings, sm)
        sdk = AsyncAnthropic(api_key=settings.anthropic_api_key)
        guard = BudgetGuard(sm=sm, daily_cap_inr=settings.daily_llm_budget_inr)
        client = ClaudeClient(sdk=sdk, sm=sm, usd_to_inr=83.0, budget=guard)
        verifier = CitationVerifier(sm=sm)

        tech = TechnicalAgent(data=layer, claude=client, tier=tier)
        fund = FundamentalAgent(data=layer, claude=client, tier=tier)
        news = NewsAgent(data=layer, claude=client, tier=news_tier, verifier=verifier)
        orch = Orchestrator(data=layer, claude=client, technical=tech, fundamental=fund,
                            news=news, tier=tier)
        report = await orch.research(ticker=ticker, exchange=exchange, timeframe=timeframe)
        if persist:
            await persist_decision(sm=sm, report=report)
        typer.echo(_json.dumps(report.model_dump(mode="json"), indent=2, default=str))
    asyncio.run(_run())


import uvicorn


@app.command("serve")
def serve(host: str = "127.0.0.1", port: int = 8000, reload: bool = False):
    """Run the HTTP API (FastAPI + scheduler) with uvicorn."""
    uvicorn.run("quant_copilot.api.app:create_app", host=host, port=port,
                reload=reload, factory=True)


if __name__ == "__main__":
    app()
