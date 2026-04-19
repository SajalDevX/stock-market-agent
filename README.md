# Quant Copilot

Personal agentic AI research assistant for Indian equity markets (NSE/BSE).

See `docs/superpowers/specs/2026-04-19-quant-copilot-design.md` for the full design spec.

## Dev quickstart

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run qc --help
```

## Layout

- `backend/` — Python (FastAPI-shape, CLI today)
- `frontend/` — Next.js (future plan)
- `docs/superpowers/` — specs and implementation plans

Advisory only. Not financial advice.

## Runbook (v0.1)

```bash
cd backend
cp .env.example .env  # then fill ANTHROPIC_API_KEY
uv sync --extra dev
uv run alembic upgrade head

# Manual ops
uv run qc fetch-ohlc RELIANCE --days 30
uv run qc ingest-news https://www.moneycontrol.com/rss/marketsnews.xml
uv run qc archive
uv run qc backup

# Tests
uv run pytest -q
```

## Data layer contract

All external data access goes through `quant_copilot.data.layer.DataLayer`.
Agents (plans 2+) must depend on this facade, not on source adapters directly.

## Technical Analyst (v0.2)

After Plan 2:

```bash
cd backend
/home/sajal/.local/bin/uv run qc analyze-technical RELIANCE --timeframe swing
```

Output is a JSON `TechnicalReport` with deterministic trend/momentum/score and a Claude-authored narrative in `reasoning`. All Claude calls are logged to `agent_calls`; the daily cap (default ₹500) is enforced by `BudgetGuard`.
