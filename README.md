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

## Full stack runbook (v0.5)

Start both services:

```bash
# terminal 1 — backend
cd backend && uv run qc serve

# terminal 2 — frontend
cd frontend && cp .env.local.example .env.local && pnpm install && pnpm dev
```

Open http://localhost:3000.

Tabs:
- **Research** — type a ticker, pick timeframe, run. Shows the verdict card, price chart with support/resistance, and expandable cards per specialist agent.
- **Watchlist** — add / remove tickers. The backend's scheduled watchlist polling (every 15 min during market hours) runs a lightweight news + technical pass on each; full verdicts are created by explicit research runs.
- **Decisions** — every research verdict is persisted. Forward returns (1d / 7d / 30d) fill in automatically as the nightly outcomes job runs.

The header shows API status and today's LLM spend (₹ spent / daily cap).

Frontend tests: `cd frontend && pnpm test`.
Backend tests: `cd backend && uv run pytest -q`.

## Backtester (v0.6)

```bash
# CLI
cat > /tmp/strategy.json <<'EOF'
{
  "ticker": "RELIANCE", "exchange": "NSE",
  "start": "2024-01-01", "end": "2024-12-31",
  "initial_capital": 100000,
  "entry": [{"indicator": "close", "op": ">", "indicator_ref": "ema20"}],
  "exit":  [{"indicator": "close", "op": "<", "indicator_ref": "ema20"}],
  "stop_loss_pct": 5, "take_profit_pct": 15, "max_hold_days": 30
}
EOF
uv run qc backtest /tmp/strategy.json | jq .summary

# HTTP
curl -s -X POST http://localhost:8000/backtest -H 'content-type: application/json' \
  --data @/tmp/strategy.json | jq .summary

# UI: http://localhost:3000/backtest
```

Rules supported:
- Entry: ALL conditions must match. Exit: ANY condition triggers.
- Implicit guards: `stop_loss_pct`, `take_profit_pct`, `max_hold_days`.
- Indicators available on each bar: `open`, `high`, `low`, `close`, `volume`, `rsi`, `macd`, `macd_signal`, `macd_hist`, `ema20`, `ema50`, `ema200`, `atr`, `bb_upper`, `bb_mid`, `bb_lower`.
- Long-only, one position at a time, daily bars. Agent-based backtests and news-keyword conditions are deferred to a later phase (spec §6.4).

