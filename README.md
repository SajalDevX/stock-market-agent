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
