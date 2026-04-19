from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from anthropic import AsyncAnthropic
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from quant_copilot.agents.budget import BudgetGuard
from quant_copilot.agents.citations import CitationVerifier
from quant_copilot.agents.claude_client import ClaudeClient
from quant_copilot.agents.fundamental import FundamentalAgent
from quant_copilot.agents.news import NewsAgent
from quant_copilot.agents.orchestrator import Orchestrator
from quant_copilot.agents.technical import TechnicalAgent
from quant_copilot.config import Settings, get_settings
from quant_copilot.data.layer import DataLayer


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_sm(request: Request) -> async_sessionmaker[AsyncSession]:
    return request.app.state.sm


def get_layer(request: Request) -> DataLayer:
    return request.app.state.layer


def get_sdk(request: Request) -> AsyncAnthropic:
    return request.app.state.sdk


def get_budget(request: Request) -> BudgetGuard:
    return request.app.state.budget


def get_claude(request: Request) -> ClaudeClient:
    return request.app.state.claude


def get_orchestrator(request: Request) -> Orchestrator:
    return request.app.state.orchestrator


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
SmDep = Annotated[async_sessionmaker[AsyncSession], Depends(get_sm)]
LayerDep = Annotated[DataLayer, Depends(get_layer)]
BudgetDep = Annotated[BudgetGuard, Depends(get_budget)]
ClaudeDep = Annotated[ClaudeClient, Depends(get_claude)]
OrchestratorDep = Annotated[Orchestrator, Depends(get_orchestrator)]
