# Quant Copilot — Design Spec

**Date:** 2026-04-19
**Owner:** Rohit (personal use)
**Status:** Draft for review (rev 2 — gap fixes applied)

## 1. Purpose

A personal, agentic AI research assistant for Indian equity markets (NSE/BSE) that produces cited, explainable analysis to support real-money trading and investing decisions across intraday, swing, and long-term timeframes.

The system is **advisory only** in v1 — it never places trades. The user makes all final decisions.

## 2. Goals & non-goals

**Goals**
- Explainable recommendations with every claim tied to a concrete data source
- Support research, watchlist monitoring, portfolio analysis, rules-based backtesting, and (phase 2) a daily market brief
- Work across intraday, swing, and long-term styles through a single modular platform
- Use free data sources only for v1
- Stay under a configurable daily LLM budget, projected against a concrete cost model (§8.2)

**Non-goals (v1)**
- Auto-executing trades (no broker integration)
- US markets, crypto, derivatives (planned for later phases)
- Social-media sentiment (Twitter/X, Reddit)
- Multi-user / cloud deployment
- LLM-in-the-loop backtesting (rules-only in v1; agent-based backtests deferred)

## 3. Users & usage

Single user, self-hosted, runs locally. Used daily around Indian market hours (9:15 AM – 3:30 PM IST) plus a morning review before open and occasional evening research sessions.

## 4. Architecture

### 4.1 Stack

- **Backend:** Python 3.11+, FastAPI, APScheduler
- **Frontend:** Next.js, Tailwind CSS, charting via TradingView Lightweight Charts or Recharts
- **Storage:** SQLite (metadata, reports, portfolio, news), local Parquet (OHLC)
- **LLM:** Claude API with prompt caching (model tiering in §8.2)
- **Deploy:** localhost for v1

### 4.2 Component map

```
┌─────────────────────────────────────────────────┐
│          Next.js Dashboard (UI)                  │
└───────────────────┬─────────────────────────────┘
                    │ REST / WebSocket
┌───────────────────▼─────────────────────────────┐
│          FastAPI Backend                         │
│  ┌──────────────────────────────────────────┐   │
│  │     Orchestrator Agent (Claude)          │   │
│  └────┬──────┬──────┬──────┬──────┬────────┘   │
│  ┌────▼─┐ ┌──▼──┐ ┌─▼──┐ ┌─▼──┐ ┌─▼────┐       │
│  │Tech  │ │Fund │ │News│ │Macro│ │Portf.│       │
│  │Agent │ │Agent│ │Agnt│ │Agnt │ │Agent │       │
│  └───┬──┘ └──┬──┘ └─┬──┘ └─┬──┘ └──┬───┘       │
│  ┌───▼───────▼──────▼──────▼───────▼───────┐   │
│  │   Data Layer (cached, deduplicated)      │   │
│  └──────────────────────────────────────────┘   │
│  Scheduler │ Clock/Calendar │ Archiver │ Eval    │
└──────────────────────────────────────────────────┘
```

### 4.3 Design principles

1. **Cited and grounded output.** Every agent claim is tied to a concrete artifact ID from the data layer. Citations are validated post-hoc (§5.3.1) — any citation that does not resolve to a retrieved artifact fails the response.
2. **Structured reports.** Agents return typed JSON (score + reasoning + evidence). Orchestrator aggregates deterministically.
3. **Data layer isolation.** Agents never call external APIs directly. The data layer is the only module that touches the internet.
4. **Reproducibility via clock abstraction + forward archival.** Every data call accepts an `asof` parameter. Historical fundamentals and news are only available back to the date the archiver first recorded them (§7.6).
5. **Surface disagreement.** When agents conflict, the orchestrator shows the conflict rather than papering over it.
6. **Advisory only.** No broker SDK dependency in v1.

### 4.4 Operational concerns

- **Timezone:** all scheduling, timestamps, and display use `Asia/Kolkata` via `zoneinfo`. Storage uses UTC; conversion happens at boundaries. Scheduler is explicitly pinned to IST regardless of host timezone.
- **Trading calendar:** NSE holiday calendar fetched at app startup and cached (refreshable weekly). Scheduler jobs and watchlist polling are no-ops on closed days, including Muhurat-only sessions (which are handled as a special schedule).
- **Concurrency:** SQLite runs in WAL mode. Data-layer writes are idempotent (upsert on natural keys). Agent calls triggered by scheduler take an advisory lock per `(ticker, agent)` key to prevent duplicate work if the user simultaneously hits refresh.
- **Cancellation:** agent calls accept an `asyncio.CancelledError` path; orchestrator checks cancellation between agent calls and returns partial results with a "cancelled" flag.
- **Observability:** every agent invocation writes a row to `agent_calls` table (inputs, outputs, model, input/output token counts, latency, cost, error). This is the primary debugging surface.
- **Backup:** daily job dumps SQLite to `backups/YYYY-MM-DD.sqlite.gz` and rsyncs `data/` (Parquet) to a configured second location. Retention 30 days.

## 5. Agents

Each agent has a narrow domain, tool access on the data layer, and returns a typed JSON report with a confidence score and cited evidence.

### 5.1 Technical Analyst

- **Input:** ticker, timeframe (intraday / swing / long-term)
- **Tools:** `get_ohlc`, `compute_indicators` (RSI, MACD, EMAs, Bollinger, ATR, volume profile), `detect_patterns`
- **Output:**
  ```json
  {
    "trend": "up|down|sideways",
    "momentum": "strong|weak|neutral",
    "key_levels": {"support": [...], "resistance": [...]},
    "signals": [{"name": "...", "direction": "bullish|bearish", "strength": 0..1}],
    "score": -1.0..+1.0,
    "reasoning": "...",
    "evidence": [{"indicator": "RSI(14)", "value": 72.3, "asof": "..."}],
    "liquidity_warning": true|false,
    "circuit_state": "none|upper|lower|frozen_days:N"
  }
  ```
- **Guardrails:**
  - Refuses analysis if 20-day average traded value < ₹1 crore (configurable liquidity floor). Returns a "low-liquidity" warning instead of signals.
  - Detects stuck-at-circuit conditions and flags rather than pretending indicators are meaningful.
  - All indicator computation uses split/bonus-adjusted series (see §7.5).

### 5.2 Fundamental Analyst

- **Input:** ticker
- **Tools:** `get_financials`, `get_ratios`, `peer_compare`, `get_surveillance_flags` (ASM/GSM list membership)
- **Output:** `{valuation, quality, growth, red_flags[], surveillance[], score, reasoning, evidence[]}`
- ASM/GSM membership and auditor-qualification flags appear in `red_flags`/`surveillance` automatically.
- Relevant for long-term and swing; skipped for pure intraday queries.

### 5.3 News & Sentiment

- **Input:** ticker + lookback window (default 7 days)
- **Tools:** `fetch_news`, `fetch_filings`, `summarize_news`
- **Output:** `{headline_summary, material_events[], sentiment: -1..+1, reasoning, citations[]}` where each citation is `{artifact_id, url, title, published_at}` — the `artifact_id` must reference a row in `news_articles` or `filings`.

#### 5.3.1 Ticker ↔ news matching

RSS feeds are firehose; filtering per ticker is non-trivial.

- **Alias table:** `ticker_aliases(ticker, alias, kind)` seeded from NSE-listed company master plus hand-curated aliases (e.g., `HDFCBANK`: "HDFC Bank", "HDFC Bank Ltd", "HDFCB"). Expected maintenance: append entries when the matcher misses.
- **Matching pipeline:**
  1. Exact alias match in article title (fast path)
  2. Exact alias match in article body (medium)
  3. Fuzzy match (rapidfuzz, ≥90% on normalized alias) against title only, to avoid false positives from body noise
- **Disambiguation:** if an article matches 2+ tickers, it's stored against each with a `match_confidence` and the News agent receives both sets; the orchestrator surfaces the ambiguity if it affects the verdict.
- **Ticker input disambiguation:** user inputs like "HDFC" resolve via the alias table; if multiple matches, the UI prompts the user to pick.

#### 5.3.2 Citation grounding (post-check)

Before the News agent's output is returned, a deterministic verifier resolves every `artifact_id` in `citations`. Any unresolved ID → the agent is re-prompted once with "these citations don't exist, use only IDs from this list: [...]". A second failure returns an error report rather than a hallucinated answer. This applies to every agent that outputs citations.

### 5.4 Macro (phase 2)

- **Tools:** `get_indices`, `get_global_cues` (Dow, Nasdaq, SGX Nifty, crude, USD-INR, key ADRs of large Indian names), `get_fii_dii_flows`
- **Output:** `{market_regime, tailwinds[], headwinds[], score, reasoning}`

### 5.5 Portfolio (phase 2)

- **Input:** user holdings (manual / CSV in v1, Kite API later)
- **P&L math:** lot-based (FIFO) with explicit handling of splits, bonuses, and dividends; realized vs unrealized broken out. CSV schema documented in the CSV import handler; import format mirrors Zerodha's holdings export for forward compatibility.
- **Output:** `{concentration_risks[], underperformers[], rebalance_suggestions[], reasoning}`

### 5.6 Orchestrator

- Picks relevant agents based on timeframe, runs them in parallel, synthesizes:
  ```json
  {
    "verdict": "buy|hold|avoid",
    "conviction": 0..100,
    "conviction_breakdown": {"technical": ..., "fundamental": ..., "news": ..., "macro": ...},
    "thesis": "...",
    "risks": [...],
    "entry": ..., "stop": ..., "target": ...,
    "agent_reports": { ... }
  }
  ```

#### 5.6.1 Conviction scoring (deterministic)

Conviction is **computed, not asserted by the LLM**, so the number doesn't drift.

- Each agent returns `score ∈ [-1, +1]`.
- Orchestrator applies timeframe-dependent weights (configurable, defaults):
  - **Intraday:** technical 0.70, news 0.25, macro 0.05
  - **Swing:** technical 0.45, news 0.25, fundamental 0.20, macro 0.10
  - **Long-term:** fundamental 0.55, technical 0.15, news 0.15, macro 0.15
- `weighted = Σ(score_i × weight_i)`
- `conviction = round(abs(weighted) × 100)`; verdict = sign (with `hold` band for `|weighted| < 0.15`)
- If agents disagree in sign, `conviction` is halved and the thesis explicitly names the conflict.
- The LLM's role is to write the `thesis` and `risks` prose around these numbers, not to set the numbers.

## 6. User flows

### 6.1 Research a stock

1. User enters ticker / company name; if ambiguous, UI disambiguation modal appears.
2. Orchestrator selects relevant agents; dispatches in parallel.
3. Dashboard shows verdict card, annotated chart (split-adjusted), expandable per-agent sections with clickable evidence.
4. **Event-aware caching:** research report cached by `(ticker, timeframe)` with TTL 1 hour **or** invalidated on any new news/filing for that ticker, whichever comes first.

### 6.2 Watchlist & alerts

- User adds tickers with optional triggers.
- Scheduler polls every 5–15 min during market hours (holiday-aware).
- Polling uses **batch fetch** on the data layer to stay inside rate-limit budgets (§7.3).
- Triggering runs a lightweight pass (news + technicals, no full research report) and shows an in-dashboard badge.

### 6.3 Portfolio analysis

- Manual entry or CSV import (Zerodha-compatible schema).
- v1: basic exposure + underperformer flags. Full portfolio agent in phase 2.
- Handles splits/bonuses/dividends when computing cost basis.

### 6.4 Backtesting (rules-only in v1)

- Strategy form: entry/exit conditions using technical indicators and simple news-keyword filters (no fundamental rules in v1 — see §7.6 on why historical fundamentals are limited).
- Replays historical data using the data layer's `asof` clock.
- Output: equity curve, win rate, max drawdown, trade log.
- Agent-based backtests deferred to phase 3; prerequisite (forward archival, §7.6) begins in v1.

### 6.5 Daily brief (phase 2)

Scheduler runs ~8:45 AM IST on trading days only. Produces Markdown home page.

## 7. Data layer

### 7.1 Interface

Typed functions: `get_ohlc`, `get_news`, `get_financials`, `get_ratios`, `get_indices`, `get_fii_dii_flows`, `fetch_filings`, `get_surveillance_flags`, `resolve_ticker`.

### 7.2 Storage

- **OHLC:** Parquet partitioned by ticker + year. **Stored unadjusted** alongside a corporate-actions table; adjusted series is computed on read (§7.5).
- **News:** SQLite `news_articles(id, ticker, published_at, source, url, title, body, hash)` with dedup on `hash`; many-to-many `article_tickers` for multi-ticker matches with `match_confidence`.
- **Filings:** `filings(id, ticker, filed_at, kind, url, body_text, hash)`.
- **Fundamentals:** SQLite, refreshed quarterly or on-demand, with `snapshot_at` for point-in-time queries (§7.6).
- **Agent reports:** `agent_reports(ticker, agent, query_hash, asof_date, report_json, created_at)`.
- **Agent call log:** `agent_calls(id, agent, input_hash, model, input_tokens, output_tokens, cost_inr, latency_ms, error, created_at)`.

### 7.3 Cache, rate limits & budgets

- Cache-first on all fetches.
- Per-source token-bucket rate limiter. Default budgets (configurable):
  - yfinance: 2 req/s burst 10, soft daily cap 10k
  - Screener scrape: 1 req/3s, daily cap 500
  - RSS feeds: 1 poll / 15 min per feed (feeds aggregate all tickers, so per-ticker cost is ~0)
  - NSE/BSE filings: 1 poll / 15 min per exchange
- **Watchlist polling is batch-shaped.** One RSS sweep per cycle covers the whole watchlist; per-ticker calls only happen on price/indicator updates, batched into a single yfinance request.
- Fallback chain for prices: yfinance → nsepython → nsetools.

### 7.4 Clock abstraction

Every data function accepts `asof: datetime | None`. `None` = now; backtest passes historical dates. Callers must never read "latest" state for historical work — the function enforces it.

### 7.5 Corporate actions

- **Table** `corporate_actions(ticker, ex_date, kind, ratio, details)` where `kind ∈ {split, bonus, dividend, rights, merger, delisting}`. Seeded from NSE corporate-actions feed, refreshed daily.
- **Adjusted OHLC** computed on read by walking the action table backwards from `asof` and applying ratio adjustments to price and volume. Never stored; always derived, so corrections to the action table propagate cleanly.
- Technical agent always consumes adjusted series. Portfolio agent consumes unadjusted prices but applies corporate actions to cost basis (e.g., 1:5 split → avg-price ÷ 5, qty × 5).
- Delisted tickers are retained with a `delisted_on` flag; agents refuse analysis with a clear message.

### 7.6 Forward archival (for future backtesting)

Historical backtests on fundamental or news data require **point-in-time** snapshots. Free sources do not provide them. Therefore v1 begins archiving from day 1, even though we can't use the archive until it accumulates:

- **Fundamentals snapshot:** nightly job snapshots every watchlist + portfolio ticker's Screener data into `fundamentals_snapshots(ticker, snapshot_at, payload_json)`. Stored compressed.
- **News archival:** all fetched articles/filings are permanent in the data layer — never purged. This gives us a growing, usable corpus.
- **Macro snapshot:** nightly snapshot of indices, FII/DII, global cues.
- **Backtest constraint:** agent-based backtests (phase 3) are valid only from the earliest available snapshot date forward; pre-archive dates can use OHLC only.

This is the gate item that makes phase 3 feasible. Starting late = phase 3 permanently blocked.

### 7.7 Fundamentals fallback

- **Primary:** Screener.in scrape.
- **Secondary:** Tickertape unofficial JSON endpoints (evaluated during implementation, wired in if stable).
- **Tertiary:** NSE/BSE direct financial disclosures (XBRL parsing — heavier lift, last resort).
- **Resilience:** aggressive caching (30-day TTL on fundamentals since they change quarterly) means a broken primary source only hurts ticker coverage *added* during the outage. Existing coverage stays queryable.

## 8. Security, cost & guardrails

### 8.1 Secrets & safety

- Secrets in `.env`, git-ignored.
- No broker SDK dependency — cannot place trades.
- "Research tool, not financial advice" disclaimer in UI.

### 8.2 LLM cost model

Back-of-envelope per flow, using Claude pricing (Opus ~$15/M out, Sonnet ~$3/M out, Haiku ~$1/M out, plus input; prompt caching ~10% read cost):

| Flow | Calls | Model tiering | Est. tokens | Est. cost/call |
|---|---|---|---|---|
| Research (full) | 1 orch + 3 specialists | Orch: Sonnet. News summarization: Haiku. Technical/Fundamental: Sonnet. | ~40k in / 5k out total | ₹8–15 |
| Watchlist lightweight pass | News + Technical only | Haiku for both | ~10k in / 1k out | ₹1–2 |
| Daily brief (phase 2) | Macro + per-holding news | Haiku throughout | ~30k in / 3k out | ₹4–6 |
| Backtest (rules-only) | 0 LLM calls | — | — | ₹0 |

**Model tiering decision:** Opus only used for the orchestrator on ambiguous queries where specialists disagree (detected deterministically). Default orchestrator is Sonnet. This keeps typical research cost an order of magnitude below naive "Opus everywhere".

**Daily budget enforcement:** orchestrator reads `SUM(cost_inr)` from `agent_calls` for today before each call. On exceed:
- Research flow: serves last cached report + "budget exhausted" banner
- Watchlist polling: pauses with an in-dashboard badge
- Daily brief: skipped with a note in the next available brief

Default daily cap ₹500. Based on the table above and typical usage (5–10 research queries + watchlist polling on 10–20 tickers), expected daily cost is ₹50–150; the ₹500 cap is a 3–4× safety margin.

## 9. Evaluation & ground truth

Without an eval loop, the bot's quality drifts invisibly — unacceptable for real money.

- **`decisions` table:** every orchestrator verdict is persisted with `(ticker, verdict, conviction, timeframe, entry_hint, target_hint, stop_hint, created_at)`.
- **Outcome job (nightly):** for each open decision, computes 1d / 7d / 30d forward return from the decision's creation price, and records to `decision_outcomes`.
- **Dashboard eval tab:** rolling hit rate, Brier score on the conviction number (proper calibration metric — conviction 70% should correspond to ~70% accuracy), per-agent contribution analysis (which agent's scores correlate with good outcomes).
- **Calibration alerts:** if rolling Brier score on last 50 decisions exceeds a threshold, surface a banner. The bot is allowed to be wrong; it is not allowed to be confidently wrong without flagging it.

This starts v1; data accumulates over weeks before it's statistically meaningful, but the infrastructure must exist from day 1.

## 10. Phased roadmap

**Phase 1 — MVP (v1)**
- FastAPI backend, Next.js dashboard, SQLite + Parquet data layer
- Sources: yfinance + nsepython fallback, Screener scraping, Moneycontrol/ET/LiveMint RSS, BSE/NSE filings XML, NSE corporate actions + holiday calendar + ASM/GSM lists
- Agents: Technical, Fundamental, News, Orchestrator
- Features: research, watchlist with in-dashboard alerts, manual/CSV portfolio entry + basic analysis, rules-based backtester
- Operational: timezone/calendar, corporate-action adjustment, forward archival jobs, agent-call logging, decisions + outcomes tables, daily backup

**Phase 2**
- Macro agent with FII/DII flows
- Portfolio agent with concentration and risk
- Daily brief
- Telegram bot for alerts
- Eval dashboard surfacing calibration metrics

**Phase 3**
- Agent-based backtests (uses forward archive)
- Zerodha Kite read-only integration
- US markets and crypto

**Phase 4 (stretch)**
- Social sentiment (Reddit)
- Multi-user / cloud deploy
- Paper-trading mode

## 11. Known edge cases & deferred items

Documented but not fixed in v1 (ordered by expected impact):

- **Penny / low-liquidity stocks:** technical agent refuses below liquidity floor (implemented). Other agents run normally with a UI warning.
- **Trading halts & circuit limits:** technical agent detects and flags; no special handling in fundamental/news paths.
- **Pre-open session (9:00–9:15):** treated as market-open; no special logic.
- **ADR/GDR cross-read for overnight signal:** macro agent (phase 2) picks up major ADRs (INFY, HDB, WIT); individual-stock cross-read deferred.
- **Tax lots / advanced P&L:** FIFO only in v1; LIFO/specific-identification deferred.
- **Multi-currency portfolios:** single-currency (INR) in v1. Phase 3 when US/crypto land.
- **UI-side websocket push for live updates:** polling in v1; push in phase 2.

## 12. Open questions

- Screener scraping stability over time — revisit if `match_rate` on fundamentals drops below 90% of watchlist tickers in any 30-day window.
- Whether to expose the conviction-weight knobs in the UI or keep them config-only in v1.
- Whether the eval Brier-score threshold for banners should auto-tune or be manually set.
