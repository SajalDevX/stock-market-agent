#!/usr/bin/env bash
# Quant Copilot — one-shot dev starter.
# Runs the FastAPI backend + APScheduler and the Next.js frontend, streams their
# logs, and cleans both up on Ctrl-C.
#
# Usage:   ./start.sh
# Options: BACKEND_PORT (default 8000), FRONTEND_PORT (default 3000),
#          SKIP_INSTALL=1 to skip dependency sync.

set -euo pipefail

cd "$(dirname "$0")"
ROOT="$(pwd)"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
SKIP_INSTALL="${SKIP_INSTALL:-0}"

LOG_DIR="$ROOT/.logs"
mkdir -p "$LOG_DIR"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

# --- tool discovery ---------------------------------------------------------

UV=""
for candidate in "$HOME/.local/bin/uv" "$(command -v uv 2>/dev/null || true)"; do
    if [ -n "$candidate" ] && [ -x "$candidate" ]; then
        UV="$candidate"
        break
    fi
done
if [ -z "$UV" ]; then
    echo "error: uv not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    exit 1
fi

if ! command -v pnpm >/dev/null 2>&1; then
    echo "error: pnpm not found. Install with: npm install -g pnpm" >&2
    exit 1
fi

# --- env checks -------------------------------------------------------------

if [ ! -f "$ROOT/backend/.env" ]; then
    if [ -f "$ROOT/backend/.env.example" ]; then
        cp "$ROOT/backend/.env.example" "$ROOT/backend/.env"
        echo "Created backend/.env from example — set ANTHROPIC_API_KEY in it, then re-run."
        exit 1
    else
        echo "error: backend/.env missing and no backend/.env.example to copy from." >&2
        exit 1
    fi
fi

if ! grep -q '^ANTHROPIC_API_KEY=.\+' "$ROOT/backend/.env"; then
    echo "error: ANTHROPIC_API_KEY is empty in backend/.env — set it before running." >&2
    exit 1
fi

if [ ! -f "$ROOT/frontend/.env.local" ]; then
    if [ -f "$ROOT/frontend/.env.local.example" ]; then
        cp "$ROOT/frontend/.env.local.example" "$ROOT/frontend/.env.local"
        echo "Created frontend/.env.local from example."
    fi
fi

# Point the frontend at the chosen backend port.
if [ -f "$ROOT/frontend/.env.local" ]; then
    if grep -q '^NEXT_PUBLIC_API_BASE=' "$ROOT/frontend/.env.local"; then
        sed -i "s|^NEXT_PUBLIC_API_BASE=.*|NEXT_PUBLIC_API_BASE=http://localhost:${BACKEND_PORT}|" "$ROOT/frontend/.env.local"
    else
        echo "NEXT_PUBLIC_API_BASE=http://localhost:${BACKEND_PORT}" >> "$ROOT/frontend/.env.local"
    fi
fi

# --- dependency sync --------------------------------------------------------

if [ "$SKIP_INSTALL" != "1" ]; then
    echo "[1/4] syncing backend deps..."
    (cd "$ROOT/backend" && "$UV" sync --extra dev) >"$LOG_DIR/uv-sync.log" 2>&1

    echo "[2/4] running DB migrations..."
    (cd "$ROOT/backend" && "$UV" run alembic upgrade head) >"$LOG_DIR/alembic.log" 2>&1

    echo "[3/4] installing frontend deps..."
    (cd "$ROOT/frontend" && pnpm install --silent) >"$LOG_DIR/pnpm-install.log" 2>&1
else
    echo "[skipping dependency sync]"
fi

# --- startup ----------------------------------------------------------------

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    echo ""
    echo "shutting down..."
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    wait 2>/dev/null || true
    echo "stopped."
}
trap cleanup INT TERM EXIT

echo "[4/4] starting services..."

# Backend: FastAPI + scheduler
(cd "$ROOT/backend" && "$UV" run qc serve --host 127.0.0.1 --port "$BACKEND_PORT") \
    >"$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

# Frontend: Next.js dev
(cd "$ROOT/frontend" && pnpm dev --port "$FRONTEND_PORT") \
    >"$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!

# --- readiness probe --------------------------------------------------------

wait_for() {
    local url="$1" label="$2" pid="$3"
    local deadline=$(( $(date +%s) + 45 ))
    while [ "$(date +%s)" -lt "$deadline" ]; do
        if ! kill -0 "$pid" 2>/dev/null; then
            echo "error: $label died during startup. Check logs." >&2
            return 1
        fi
        if curl -sf "$url" >/dev/null 2>&1; then
            return 0
        fi
        sleep 0.5
    done
    echo "error: $label did not become ready within 45s. Check logs." >&2
    return 1
}

wait_for "http://127.0.0.1:${BACKEND_PORT}/health" backend "$BACKEND_PID" || { tail -30 "$BACKEND_LOG"; exit 1; }
wait_for "http://127.0.0.1:${FRONTEND_PORT}" frontend "$FRONTEND_PID" || { tail -30 "$FRONTEND_LOG"; exit 1; }

# --- running ----------------------------------------------------------------

cat <<BANNER

  Quant Copilot is running.
    Frontend: http://localhost:${FRONTEND_PORT}
    Backend:  http://localhost:${BACKEND_PORT}   (GET /health, POST /research, ...)
    Logs:     ${BACKEND_LOG}
              ${FRONTEND_LOG}

  Press Ctrl-C to stop.

BANNER

# Stream both logs side-by-side until Ctrl-C.
tail -n 0 -f "$BACKEND_LOG" "$FRONTEND_LOG" &
TAIL_PID=$!

# Wait on whichever service dies first; cleanup handles the rest.
wait -n "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true

kill "$TAIL_PID" 2>/dev/null || true
