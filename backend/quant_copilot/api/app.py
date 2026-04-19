from __future__ import annotations

from contextlib import asynccontextmanager

from anthropic import AsyncAnthropic
from fastapi import FastAPI

from quant_copilot.agents.budget import BudgetGuard
from quant_copilot.agents.citations import CitationVerifier
from quant_copilot.agents.claude_client import ClaudeClient
from quant_copilot.agents.fundamental import FundamentalAgent
from quant_copilot.agents.macro import MacroAgent
from quant_copilot.agents.news import NewsAgent
from quant_copilot.agents.orchestrator import Orchestrator
from quant_copilot.agents.technical import TechnicalAgent
from quant_copilot.config import Settings, get_settings
from quant_copilot.data.layer import build_data_layer
from quant_copilot.data.macro import MacroData
from quant_copilot.db import build_engine, build_sessionmaker, set_pragmas
from quant_copilot.logging_setup import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings if hasattr(app.state, "settings") else get_settings()
    app.state.settings = settings
    configure_logging()
    engine = build_engine(settings)
    await set_pragmas(engine)
    from quant_copilot.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = build_sessionmaker(engine)
    app.state.engine = engine
    app.state.sm = sm
    app.state.layer = build_data_layer(settings, sm)
    app.state.sdk = AsyncAnthropic(api_key=settings.anthropic_api_key)
    app.state.budget = BudgetGuard(sm=sm, daily_cap_inr=settings.daily_llm_budget_inr)
    app.state.claude = ClaudeClient(sdk=app.state.sdk, sm=sm, budget=app.state.budget)
    verifier = CitationVerifier(sm=sm)
    tech = TechnicalAgent(data=app.state.layer, claude=app.state.claude)
    fund = FundamentalAgent(data=app.state.layer, claude=app.state.claude)
    news = NewsAgent(data=app.state.layer, claude=app.state.claude, verifier=verifier)
    macro = MacroAgent(macro_data=MacroData(), claude=app.state.claude)
    app.state.orchestrator = Orchestrator(
        data=app.state.layer, claude=app.state.claude,
        technical=tech, fundamental=fund, news=news, macro=macro,
    )
    try:
        yield
    finally:
        await engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(
        title="Quant Copilot",
        version="0.4.0",
        lifespan=lifespan,
    )
    # Allow tests to inject settings before lifespan runs
    app.state.settings = settings or get_settings()

    # Routes are registered by Tasks 3-6.
    from quant_copilot.api.routes import decisions, health, research, watchlist
    app.include_router(health.router)
    app.include_router(watchlist.router)
    app.include_router(decisions.router)
    app.include_router(research.router)

    return app
