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

## Full research flow (v0.3)

After Plan 3:

```bash
cd backend
uv run qc analyze RELIANCE --timeframe swing
# per-agent:
uv run qc analyze-technical RELIANCE
uv run qc analyze-fundamental RELIANCE
uv run qc analyze-news RELIANCE --lookback-days 7
```

`qc analyze` runs the Orchestrator: it dispatches Technical + Fundamental + News in parallel, computes conviction deterministically from their signed scores (weights per timeframe in `agents/conviction.py`), surfaces any sign disagreements, asks Claude for the thesis prose, and persists the verdict to the `decisions` table so future evaluation jobs can compute forward-return calibration.

News citations are grounded: every `artifact_id` in the News agent's output must resolve to a real row in `news_articles` or `filings`. Unresolved citations trigger one re-prompt; a second failure raises an error rather than returning hallucinated evidence.

## HTTP API + scheduler (v0.4)

```bash
cd backend
uv run qc serve --host 127.0.0.1 --port 8000
```

Endpoints:
- `GET  /health` — DB + budget + scheduler status
- `POST /research` — run the Orchestrator; body `{"ticker": "RELIANCE", "timeframe": "swing"}`
- `GET  /decisions` — recent verdicts
- `GET  /decisions/{id}` — a verdict with its computed forward-return outcomes
- `GET  /watchlist`, `POST /watchlist/{ticker}`, `DELETE /watchlist/{ticker}`

Scheduled jobs (IST, skipping weekends/holidays where appropriate):
- **23:00** — nightly fundamentals archival
- **23:30** — SQLite backup + 30-day retention
- **01:00** — compute 1d/7d/30d forward returns for any eligible decisions
- **09:00–15:45 Mon-Fri, every 15 min** — lightweight watchlist poll (news + technical)

The Macro agent is now wired into the Orchestrator for swing and long-term timeframes; intraday uses macro but skips fundamentals.
