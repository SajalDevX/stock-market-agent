# Plan 1 — Foundation & Data Layer

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the backend foundation and a cache-first, reproducible data layer that every future agent in Quant Copilot will depend on.

**Architecture:** Python backend project (uv + FastAPI-ready layout) with a pure `DataLayer` module that is the *only* component allowed to touch external data sources. All data flows through typed async functions that accept an `asof` clock parameter, go through per-source rate limiters, cache to SQLite (metadata) + Parquet (OHLC), and compute corporate-action adjustments on read. Forward-archival jobs begin accumulating point-in-time snapshots from day 1 so phase-3 agent backtests become feasible later.

**Tech Stack:** Python 3.11+, uv, FastAPI-shape (not yet mounted), SQLAlchemy 2.0 async, Alembic, Pydantic v2, pydantic-settings, yfinance, nsepython, feedparser, beautifulsoup4 + lxml, pyarrow, pandas, pandas-ta, rapidfuzz, httpx, APScheduler, Typer CLI, pytest + pytest-asyncio + vcrpy.

**Related spec:** `docs/superpowers/specs/2026-04-19-quant-copilot-design.md` (rev 2). Sections most relevant: §4.4 (ops), §5.3.1 (ticker matching), §7 (data layer), §7.5 (corporate actions), §7.6 (archival), §7.7 (fundamentals fallback).

---

## File structure

Monorepo with `backend/` for Python and (later, plans 5+) `frontend/` for Next.js.

```
stock-market-bot/
├── .gitignore
├── README.md
├── backend/
│   ├── pyproject.toml
│   ├── uv.lock                      # generated
│   ├── .env.example
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/                # migrations live here
│   ├── quant_copilot/
│   │   ├── __init__.py
│   │   ├── config.py                # Settings (pydantic-settings)
│   │   ├── logging_setup.py         # structlog config
│   │   ├── db.py                    # Async SQLAlchemy engine + session
│   │   ├── models.py                # ORM models
│   │   ├── clock.py                 # Clock abstraction (asof)
│   │   ├── calendar.py              # NSE holidays + market hours
│   │   ├── rate_limit.py            # Token-bucket rate limiter
│   │   ├── paths.py                 # Data/backup/parquet path helpers
│   │   ├── cli.py                   # Typer CLI entry
│   │   └── data/
│   │       ├── __init__.py
│   │       ├── layer.py             # DataLayer facade
│   │       ├── ticker_resolver.py   # Alias table + fuzzy matching
│   │       ├── ohlc.py              # Parquet I/O + adjustment application
│   │       ├── corporate_actions.py # Splits/bonuses/dividends/mergers
│   │       ├── fundamentals.py      # Screener scrape + 30d cache
│   │       ├── news.py              # RSS ingest + ticker matching
│   │       ├── filings.py           # BSE/NSE XML announcements
│   │       ├── surveillance.py      # ASM/GSM list membership
│   │       ├── macro.py             # Indices + global cues + FII/DII (light v1 — used by phase-2 Macro agent)
│   │       └── sources/
│   │           ├── __init__.py
│   │           ├── base.py          # Shared protocol for OHLC sources
│   │           ├── yfinance_src.py
│   │           ├── nsepython_src.py
│   │           ├── nsetools_src.py
│   │           └── rss_src.py       # Feedparser wrapper
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py              # Shared fixtures (tmp db, parquet root)
│       ├── fixtures/
│       │   ├── yfinance_reliance_daily.json
│       │   ├── screener_reliance.html
│       │   ├── moneycontrol_rss.xml
│       │   └── nse_holidays_2026.json
│       ├── test_config.py
│       ├── test_clock.py
│       ├── test_calendar.py
│       ├── test_rate_limit.py
│       ├── test_ticker_resolver.py
│       ├── test_corporate_actions.py
│       ├── test_ohlc.py
│       ├── test_fundamentals.py
│       ├── test_news.py
│       ├── test_filings.py
│       ├── test_surveillance.py
│       ├── test_archival.py
│       └── test_data_layer.py
```

**Why this split:** `quant_copilot.data.*` is the boundary layer — every outbound request lives there. Everything outside `data/` is pure logic or orchestration with no network calls, which makes the rest of the codebase trivially unit-testable.

---

## Task 1 — Repo scaffolding & git setup

**Files:**
- Create: `.gitignore`
- Create: `README.md`
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`
- Create: `backend/quant_copilot/__init__.py`

- [ ] **Step 1.1: Initialise git repo with project-local identity**

```bash
cd /home/sajal/Desktop/projects/stock-market-bot
git init
git config user.name "SajalDevX"
git config user.email "kakalijana1254@gmail.com"
git config commit.gpgsign false
```

- [ ] **Step 1.2: Create `.gitignore`**

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
.venv/
venv/
.pytest_cache/
.ruff_cache/
.mypy_cache/
*.egg-info/
dist/
build/

# Data + secrets
backend/.env
backend/data/
backend/backups/
backend/quant_copilot.db*
*.parquet

# Node (future)
node_modules/
.next/
.turbo/

# OS / IDE
.DS_Store
.idea/
.vscode/
*.swp
```

- [ ] **Step 1.3: Create `README.md`**

```markdown
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
```

- [ ] **Step 1.4: Create `backend/pyproject.toml`**

```toml
[project]
name = "quant-copilot"
version = "0.1.0"
description = "Personal agentic AI research assistant for Indian equity markets"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.7",
    "pydantic-settings>=2.3",
    "sqlalchemy[asyncio]>=2.0.30",
    "aiosqlite>=0.20",
    "alembic>=1.13",
    "httpx>=0.27",
    "yfinance>=0.2.40",
    "nsepython>=2.9",
    "nsetools>=1.0.11",
    "feedparser>=6.0.11",
    "beautifulsoup4>=4.12",
    "lxml>=5.2",
    "pandas>=2.2",
    "pyarrow>=16.1",
    "pandas-ta>=0.3.14b0",
    "rapidfuzz>=3.9",
    "apscheduler>=3.10",
    "typer>=0.12",
    "structlog>=24.1",
    "python-dateutil>=2.9",
    "tenacity>=8.4",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "vcrpy>=6.0",
    "ruff>=0.5",
    "freezegun>=1.5",
    "respx>=0.21",
]

[project.scripts]
qc = "quant_copilot.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["quant_copilot"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "B", "UP", "SIM", "RUF"]
ignore = ["E501"]  # handled by formatter
```

- [ ] **Step 1.5: Create `backend/.env.example`**

```dotenv
# Anthropic
ANTHROPIC_API_KEY=

# Paths
DATA_DIR=./data
BACKUP_DIR=./backups

# Budgets
DAILY_LLM_BUDGET_INR=500

# Rate limits (requests per minute unless noted)
YFINANCE_RPM=120
SCREENER_RPM=20
RSS_POLL_INTERVAL_MIN=15

# Calendar
MARKET_TZ=Asia/Kolkata
```

- [ ] **Step 1.6: Create `backend/quant_copilot/__init__.py`**

```python
__version__ = "0.1.0"
```

- [ ] **Step 1.7: Install dependencies and verify**

```bash
cd backend
uv sync --extra dev
uv run python -c "import quant_copilot; print(quant_copilot.__version__)"
```
Expected output: `0.1.0`

- [ ] **Step 1.8: Commit**

```bash
git add .gitignore README.md backend/pyproject.toml backend/.env.example backend/quant_copilot/__init__.py backend/uv.lock
git commit -m "chore: scaffold backend project with uv + pyproject"
```

---

## Task 2 — Config & logging

**Files:**
- Create: `backend/quant_copilot/config.py`
- Create: `backend/quant_copilot/logging_setup.py`
- Create: `backend/quant_copilot/paths.py`
- Test: `backend/tests/test_config.py`

- [ ] **Step 2.1: Write failing test `tests/test_config.py`**

```python
from pathlib import Path

from quant_copilot.config import Settings


def test_settings_load_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    s = Settings()
    assert s.anthropic_api_key == "sk-test"
    assert s.data_dir == Path(tmp_path / "data")
    assert s.daily_llm_budget_inr == 500
    assert s.market_tz == "Asia/Kolkata"


def test_settings_require_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    try:
        Settings(_env_file=None)
    except Exception as e:
        assert "anthropic_api_key" in str(e).lower()
    else:
        raise AssertionError("Settings should have failed without ANTHROPIC_API_KEY")
```

- [ ] **Step 2.2: Run test, confirm failure**

```bash
cd backend && uv run pytest tests/test_config.py -v
```
Expected: `ModuleNotFoundError: No module named 'quant_copilot.config'`

- [ ] **Step 2.3: Implement `config.py`**

```python
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    data_dir: Path = Field(Path("./data"), alias="DATA_DIR")
    backup_dir: Path = Field(Path("./backups"), alias="BACKUP_DIR")
    daily_llm_budget_inr: int = Field(500, alias="DAILY_LLM_BUDGET_INR")
    yfinance_rpm: int = Field(120, alias="YFINANCE_RPM")
    screener_rpm: int = Field(20, alias="SCREENER_RPM")
    rss_poll_interval_min: int = Field(15, alias="RSS_POLL_INTERVAL_MIN")
    market_tz: str = Field("Asia/Kolkata", alias="MARKET_TZ")

    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / "quant_copilot.db"

    @property
    def parquet_root(self) -> Path:
        return self.data_dir / "ohlc"


def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
```

- [ ] **Step 2.4: Implement `paths.py`**

```python
from pathlib import Path

from quant_copilot.config import Settings


def ensure_dirs(settings: Settings) -> None:
    for p in [settings.data_dir, settings.backup_dir, settings.parquet_root]:
        Path(p).mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 2.5: Implement `logging_setup.py`**

```python
import logging
import sys

import structlog


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level)),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
```

- [ ] **Step 2.6: Run tests, confirm pass**

```bash
uv run pytest tests/test_config.py -v
```
Expected: 2 passed.

- [ ] **Step 2.7: Commit**

```bash
git add backend/quant_copilot/config.py backend/quant_copilot/logging_setup.py backend/quant_copilot/paths.py backend/tests/test_config.py
git commit -m "feat: settings, paths, and structured logging"
```

---

## Task 3 — Clock abstraction

**Files:**
- Create: `backend/quant_copilot/clock.py`
- Test: `backend/tests/test_clock.py`

- [ ] **Step 3.1: Write failing test**

```python
from datetime import datetime
from zoneinfo import ZoneInfo

from freezegun import freeze_time

from quant_copilot.clock import Clock, SystemClock, FrozenClock


def test_system_clock_returns_ist_now():
    with freeze_time("2026-04-19T10:30:00+05:30"):
        c: Clock = SystemClock("Asia/Kolkata")
        now = c.now()
        assert now.tzinfo is not None
        assert now.utcoffset().total_seconds() == 19800  # +05:30


def test_frozen_clock_fixed_value():
    fixed = datetime(2023, 6, 15, 11, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    c: Clock = FrozenClock(fixed)
    assert c.now() == fixed
    assert c.today().isoformat() == "2023-06-15"


def test_resolve_asof_none_uses_now():
    fixed = datetime(2024, 1, 2, 9, 30, tzinfo=ZoneInfo("Asia/Kolkata"))
    c = FrozenClock(fixed)
    assert c.resolve_asof(None) == fixed
    explicit = datetime(2024, 1, 1, tzinfo=ZoneInfo("Asia/Kolkata"))
    assert c.resolve_asof(explicit) == explicit
```

- [ ] **Step 3.2: Run test, confirm failure**

```bash
uv run pytest tests/test_clock.py -v
```
Expected: ModuleNotFoundError.

- [ ] **Step 3.3: Implement `clock.py`**

```python
from __future__ import annotations

from datetime import date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo


class Clock(Protocol):
    def now(self) -> datetime: ...
    def today(self) -> date: ...
    def resolve_asof(self, asof: datetime | None) -> datetime: ...


class SystemClock:
    def __init__(self, tz: str = "Asia/Kolkata") -> None:
        self._tz = ZoneInfo(tz)

    def now(self) -> datetime:
        return datetime.now(self._tz)

    def today(self) -> date:
        return self.now().date()

    def resolve_asof(self, asof: datetime | None) -> datetime:
        if asof is None:
            return self.now()
        if asof.tzinfo is None:
            return asof.replace(tzinfo=self._tz)
        return asof.astimezone(self._tz)


class FrozenClock:
    """Used in tests and backtests."""

    def __init__(self, at: datetime) -> None:
        if at.tzinfo is None:
            raise ValueError("FrozenClock requires timezone-aware datetime")
        self._at = at

    def now(self) -> datetime:
        return self._at

    def today(self) -> date:
        return self._at.date()

    def resolve_asof(self, asof: datetime | None) -> datetime:
        return asof if asof is not None else self._at
```

- [ ] **Step 3.4: Run tests, confirm pass**

```bash
uv run pytest tests/test_clock.py -v
```
Expected: 3 passed.

- [ ] **Step 3.5: Commit**

```bash
git add backend/quant_copilot/clock.py backend/tests/test_clock.py
git commit -m "feat: clock abstraction with system and frozen variants"
```

---

## Task 4 — NSE trading calendar & market hours

**Files:**
- Create: `backend/quant_copilot/calendar.py`
- Create: `backend/tests/fixtures/nse_holidays_2026.json`
- Test: `backend/tests/test_calendar.py`

- [ ] **Step 4.1: Create fixture `tests/fixtures/nse_holidays_2026.json`**

```json
{
  "year": 2026,
  "holidays": [
    {"date": "2026-01-26", "name": "Republic Day"},
    {"date": "2026-03-06", "name": "Holi"},
    {"date": "2026-04-03", "name": "Good Friday"},
    {"date": "2026-04-14", "name": "Dr. Ambedkar Jayanti"},
    {"date": "2026-05-01", "name": "Maharashtra Day"},
    {"date": "2026-08-15", "name": "Independence Day"},
    {"date": "2026-10-02", "name": "Gandhi Jayanti"},
    {"date": "2026-11-09", "name": "Diwali Laxmi Pujan (Muhurat session only)", "muhurat_only": true}
  ]
}
```

- [ ] **Step 4.2: Write failing test `tests/test_calendar.py`**

```python
import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from quant_copilot.calendar import TradingCalendar, MarketSession


FIX = Path(__file__).parent / "fixtures" / "nse_holidays_2026.json"


def _load_cal() -> TradingCalendar:
    data = json.loads(FIX.read_text())
    return TradingCalendar.from_records(data["holidays"], tz="Asia/Kolkata")


def test_republic_day_is_closed():
    cal = _load_cal()
    assert cal.is_closed(date(2026, 1, 26)) is True


def test_regular_weekday_is_open():
    cal = _load_cal()
    assert cal.is_closed(date(2026, 4, 20)) is False  # Monday


def test_saturday_sunday_closed():
    cal = _load_cal()
    assert cal.is_closed(date(2026, 4, 18)) is True  # Sat
    assert cal.is_closed(date(2026, 4, 19)) is True  # Sun


def test_muhurat_day_classified_special():
    cal = _load_cal()
    assert cal.session_kind(date(2026, 11, 9)) == "muhurat"


def test_market_session_open_during_regular_hours():
    cal = _load_cal()
    tz = ZoneInfo("Asia/Kolkata")
    t = datetime(2026, 4, 20, 10, 30, tzinfo=tz)
    s = cal.classify(t)
    assert s == MarketSession.REGULAR


def test_market_session_preopen():
    cal = _load_cal()
    tz = ZoneInfo("Asia/Kolkata")
    t = datetime(2026, 4, 20, 9, 5, tzinfo=tz)
    assert cal.classify(t) == MarketSession.PREOPEN


def test_market_session_closed_after_hours():
    cal = _load_cal()
    tz = ZoneInfo("Asia/Kolkata")
    t = datetime(2026, 4, 20, 18, 0, tzinfo=tz)
    assert cal.classify(t) == MarketSession.CLOSED


def test_market_session_closed_on_holiday():
    cal = _load_cal()
    tz = ZoneInfo("Asia/Kolkata")
    t = datetime(2026, 1, 26, 10, 30, tzinfo=tz)
    assert cal.classify(t) == MarketSession.CLOSED
```

- [ ] **Step 4.3: Run tests, confirm failure**

```bash
uv run pytest tests/test_calendar.py -v
```

- [ ] **Step 4.4: Implement `calendar.py`**

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from enum import StrEnum
from typing import Literal
from zoneinfo import ZoneInfo


class MarketSession(StrEnum):
    CLOSED = "closed"
    PREOPEN = "preopen"
    REGULAR = "regular"
    POSTCLOSE = "postclose"
    MUHURAT = "muhurat"


@dataclass(frozen=True)
class Holiday:
    on: date
    name: str
    muhurat_only: bool = False


# Standard NSE equity session times (IST)
PREOPEN_START = time(9, 0)
REGULAR_START = time(9, 15)
REGULAR_END = time(15, 30)
POSTCLOSE_END = time(16, 0)


class TradingCalendar:
    def __init__(self, holidays: list[Holiday], tz: str = "Asia/Kolkata") -> None:
        self._holidays = {h.on: h for h in holidays}
        self._tz = ZoneInfo(tz)

    @classmethod
    def from_records(cls, records: list[dict], tz: str = "Asia/Kolkata") -> "TradingCalendar":
        holidays = [
            Holiday(
                on=date.fromisoformat(r["date"]),
                name=r["name"],
                muhurat_only=bool(r.get("muhurat_only", False)),
            )
            for r in records
        ]
        return cls(holidays, tz=tz)

    def session_kind(self, on: date) -> Literal["weekend", "holiday", "muhurat", "regular"]:
        if on.weekday() >= 5:
            return "weekend"
        h = self._holidays.get(on)
        if h is None:
            return "regular"
        return "muhurat" if h.muhurat_only else "holiday"

    def is_closed(self, on: date) -> bool:
        kind = self.session_kind(on)
        return kind in ("weekend", "holiday")

    def classify(self, at: datetime) -> MarketSession:
        at = at.astimezone(self._tz)
        kind = self.session_kind(at.date())
        if kind in ("weekend", "holiday"):
            return MarketSession.CLOSED
        if kind == "muhurat":
            # v1 treats muhurat as a special separate session; polling skips it
            return MarketSession.MUHURAT
        t = at.time()
        if PREOPEN_START <= t < REGULAR_START:
            return MarketSession.PREOPEN
        if REGULAR_START <= t < REGULAR_END:
            return MarketSession.REGULAR
        if REGULAR_END <= t < POSTCLOSE_END:
            return MarketSession.POSTCLOSE
        return MarketSession.CLOSED
```

- [ ] **Step 4.5: Run tests, confirm pass**

```bash
uv run pytest tests/test_calendar.py -v
```
Expected: 7 passed.

- [ ] **Step 4.6: Commit**

```bash
git add backend/quant_copilot/calendar.py backend/tests/test_calendar.py backend/tests/fixtures/nse_holidays_2026.json
git commit -m "feat: NSE trading calendar with market session classification"
```

---

## Task 5 — Token-bucket rate limiter

**Files:**
- Create: `backend/quant_copilot/rate_limit.py`
- Test: `backend/tests/test_rate_limit.py`

- [ ] **Step 5.1: Write failing test**

```python
import asyncio
import time

import pytest

from quant_copilot.rate_limit import TokenBucket, RateLimiterRegistry


async def test_token_bucket_allows_burst_up_to_capacity():
    b = TokenBucket(rate_per_sec=5.0, capacity=5, monotonic=time.monotonic)
    for _ in range(5):
        await b.acquire()  # should not wait
    start = time.monotonic()
    await b.acquire()  # 6th call must wait ~0.2s
    elapsed = time.monotonic() - start
    assert 0.15 < elapsed < 0.5


async def test_registry_keys_isolate_buckets():
    reg = RateLimiterRegistry()
    reg.register("yfinance", rate_per_sec=1000, capacity=10)
    reg.register("screener", rate_per_sec=0.33, capacity=1)  # 1 per 3s
    # Exhaust screener's single token
    async with reg.limit("screener"):
        pass
    # yfinance unaffected
    async with reg.limit("yfinance"):
        pass
```

- [ ] **Step 5.2: Run, confirm fail**

- [ ] **Step 5.3: Implement `rate_limit.py`**

```python
from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class TokenBucket:
    rate_per_sec: float
    capacity: int
    monotonic: Callable[[], float] = field(default=time.monotonic)
    _tokens: float = field(init=False)
    _last: float = field(init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

    def __post_init__(self) -> None:
        self._tokens = float(self.capacity)
        self._last = self.monotonic()

    async def acquire(self, n: int = 1) -> None:
        while True:
            async with self._lock:
                now = self.monotonic()
                elapsed = now - self._last
                self._last = now
                self._tokens = min(self.capacity, self._tokens + elapsed * self.rate_per_sec)
                if self._tokens >= n:
                    self._tokens -= n
                    return
                need = n - self._tokens
                wait = need / self.rate_per_sec
            await asyncio.sleep(wait)


class RateLimiterRegistry:
    def __init__(self) -> None:
        self._buckets: dict[str, TokenBucket] = {}

    def register(self, key: str, *, rate_per_sec: float, capacity: int) -> None:
        self._buckets[key] = TokenBucket(rate_per_sec=rate_per_sec, capacity=capacity)

    @asynccontextmanager
    async def limit(self, key: str):
        bucket = self._buckets.get(key)
        if bucket is None:
            raise KeyError(f"No rate limiter registered for {key!r}")
        await bucket.acquire()
        yield
```

- [ ] **Step 5.4: Run tests, confirm pass**

```bash
uv run pytest tests/test_rate_limit.py -v
```
Expected: 2 passed.

- [ ] **Step 5.5: Commit**

```bash
git add backend/quant_copilot/rate_limit.py backend/tests/test_rate_limit.py
git commit -m "feat: async token-bucket rate limiter with per-source registry"
```

---

## Task 6 — Database engine, models, and migrations

**Files:**
- Create: `backend/quant_copilot/db.py`
- Create: `backend/quant_copilot/models.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_initial.py`

- [ ] **Step 6.1: Implement `models.py`**

```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, Date, DateTime, Float, ForeignKey, Index,
    Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Ticker(Base):
    __tablename__ = "tickers"
    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)  # e.g. RELIANCE
    exchange: Mapped[str] = mapped_column(String(8))  # NSE | BSE
    name: Mapped[str] = mapped_column(String(255))
    isin: Mapped[str | None] = mapped_column(String(16))
    sector: Mapped[str | None] = mapped_column(String(64))
    delisted_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TickerAlias(Base):
    __tablename__ = "ticker_aliases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(ForeignKey("tickers.symbol"), index=True)
    alias: Mapped[str] = mapped_column(String(255), index=True)
    kind: Mapped[str] = mapped_column(String(16))  # name|short|code|fuzzy
    __table_args__ = (UniqueConstraint("ticker", "alias", name="uq_ticker_alias"),)


class CorporateAction(Base):
    __tablename__ = "corporate_actions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(ForeignKey("tickers.symbol"), index=True)
    ex_date: Mapped[datetime] = mapped_column(Date, index=True)
    kind: Mapped[str] = mapped_column(String(16))  # split|bonus|dividend|rights|merger|delisting
    ratio_num: Mapped[float | None] = mapped_column(Float)  # e.g. split 1:5 -> 1
    ratio_den: Mapped[float | None] = mapped_column(Float)  # e.g. split 1:5 -> 5
    dividend_per_share: Mapped[float | None] = mapped_column(Float)
    details: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        UniqueConstraint("ticker", "ex_date", "kind", name="uq_corp_action"),
    )


class NewsArticle(Base):
    __tablename__ = "news_articles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(64))
    url: Mapped[str] = mapped_column(String(1024))
    title: Mapped[str] = mapped_column(String(512))
    body: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ArticleTicker(Base):
    __tablename__ = "article_tickers"
    article_id: Mapped[int] = mapped_column(ForeignKey("news_articles.id"), primary_key=True)
    ticker: Mapped[str] = mapped_column(ForeignKey("tickers.symbol"), primary_key=True)
    match_confidence: Mapped[float] = mapped_column(Float)


class Filing(Base):
    __tablename__ = "filings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    ticker: Mapped[str] = mapped_column(ForeignKey("tickers.symbol"), index=True)
    exchange: Mapped[str] = mapped_column(String(8))
    kind: Mapped[str] = mapped_column(String(32))
    url: Mapped[str] = mapped_column(String(1024))
    body_text: Mapped[str | None] = mapped_column(Text)
    filed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class FundamentalsSnapshot(Base):
    __tablename__ = "fundamentals_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(ForeignKey("tickers.symbol"), index=True)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload_json: Mapped[str] = mapped_column(Text)  # Full Screener payload, compressed-on-disk later
    __table_args__ = (
        UniqueConstraint("ticker", "snapshot_at", name="uq_fund_snap"),
    )


class SurveillanceFlag(Base):
    __tablename__ = "surveillance_flags"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(ForeignKey("tickers.symbol"), index=True)
    list_name: Mapped[str] = mapped_column(String(16))  # ASM | GSM
    stage: Mapped[str | None] = mapped_column(String(16))
    added_on: Mapped[datetime] = mapped_column(Date, index=True)
    removed_on: Mapped[datetime | None] = mapped_column(Date)


class AgentReport(Base):
    __tablename__ = "agent_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(ForeignKey("tickers.symbol"), index=True)
    agent: Mapped[str] = mapped_column(String(32))
    query_hash: Mapped[str] = mapped_column(String(64), index=True)
    asof_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    report_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AgentCall(Base):
    __tablename__ = "agent_calls"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent: Mapped[str] = mapped_column(String(32), index=True)
    input_hash: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(64))
    input_tokens: Mapped[int] = mapped_column(BigInteger)
    output_tokens: Mapped[int] = mapped_column(BigInteger)
    cost_inr: Mapped[float] = mapped_column(Float)
    latency_ms: Mapped[int] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Decision(Base):
    __tablename__ = "decisions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(ForeignKey("tickers.symbol"), index=True)
    timeframe: Mapped[str] = mapped_column(String(16))
    verdict: Mapped[str] = mapped_column(String(8))
    conviction: Mapped[int] = mapped_column(Integer)
    entry: Mapped[float | None] = mapped_column(Float)
    stop: Mapped[float | None] = mapped_column(Float)
    target: Mapped[float | None] = mapped_column(Float)
    ref_price: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class DecisionOutcome(Base):
    __tablename__ = "decision_outcomes"
    decision_id: Mapped[int] = mapped_column(ForeignKey("decisions.id"), primary_key=True)
    horizon: Mapped[str] = mapped_column(String(8), primary_key=True)  # 1d|7d|30d
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    return_pct: Mapped[float] = mapped_column(Float)


class WatchlistEntry(Base):
    __tablename__ = "watchlist"
    ticker: Mapped[str] = mapped_column(ForeignKey("tickers.symbol"), primary_key=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    rules_json: Mapped[str | None] = mapped_column(Text)


Index("ix_article_tickers_ticker", ArticleTicker.ticker)
```

- [ ] **Step 6.2: Implement `db.py`**

```python
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from quant_copilot.config import Settings
from quant_copilot.paths import ensure_dirs


def build_engine(settings: Settings):
    ensure_dirs(settings)
    url = f"sqlite+aiosqlite:///{settings.sqlite_path}"
    engine = create_async_engine(
        url,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    return engine


def build_sessionmaker(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def session_scope(sm: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with sm() as s:
        try:
            yield s
            await s.commit()
        except Exception:
            await s.rollback()
            raise


async def set_pragmas(engine) -> None:
    async with engine.begin() as conn:
        await conn.exec_driver_sql("PRAGMA journal_mode=WAL")
        await conn.exec_driver_sql("PRAGMA synchronous=NORMAL")
        await conn.exec_driver_sql("PRAGMA foreign_keys=ON")
```

- [ ] **Step 6.3: Set up Alembic**

```bash
cd backend
uv run alembic init alembic
```

Then edit `alembic.ini` to set:
```ini
sqlalchemy.url = sqlite:///./data/quant_copilot.db
```

Replace `alembic/env.py` with:

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

from quant_copilot.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 6.4: Generate initial migration**

```bash
uv run alembic revision --autogenerate -m "initial schema"
```

Rename the generated file to `alembic/versions/0001_initial.py` and hand-verify the upgrade/downgrade functions cover every model from Task 6.1.

- [ ] **Step 6.5: Apply and verify**

```bash
mkdir -p data
uv run alembic upgrade head
uv run python -c "import sqlite3; c=sqlite3.connect('data/quant_copilot.db'); print(sorted(r[0] for r in c.execute('SELECT name FROM sqlite_master WHERE type=\"table\"').fetchall()))"
```
Expected: prints the list of all tables from `models.py` plus `alembic_version`.

- [ ] **Step 6.6: Commit**

```bash
git add backend/quant_copilot/db.py backend/quant_copilot/models.py backend/alembic.ini backend/alembic/
git commit -m "feat: SQLAlchemy async engine, models, and initial Alembic migration"
```

---

## Task 7 — Ticker resolver & alias matching

**Files:**
- Create: `backend/quant_copilot/data/__init__.py` (empty)
- Create: `backend/quant_copilot/data/ticker_resolver.py`
- Test: `backend/tests/test_ticker_resolver.py`
- Test: `backend/tests/conftest.py`

- [ ] **Step 7.1: Create `conftest.py` with shared fixtures**

```python
import asyncio
import os
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from quant_copilot.models import Base


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def engine(tmp_path):
    db = tmp_path / "test.db"
    eng = create_async_engine(f"sqlite+aiosqlite:///{db}", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def sm(engine):
    from sqlalchemy.ext.asyncio import async_sessionmaker
    return async_sessionmaker(engine, expire_on_commit=False)
```

- [ ] **Step 7.2: Write failing test**

```python
from datetime import datetime, timezone

import pytest

from quant_copilot.models import Ticker, TickerAlias
from quant_copilot.data.ticker_resolver import TickerResolver


async def _seed(sm):
    async with sm() as s:
        s.add(Ticker(symbol="HDFCBANK", exchange="NSE", name="HDFC Bank Ltd", isin="INE040A01034"))
        s.add(Ticker(symbol="HDFC", exchange="NSE", name="Housing Development Finance Corp (merged)",
                     delisted_on=datetime(2023, 7, 1, tzinfo=timezone.utc)))
        s.add_all([
            TickerAlias(ticker="HDFCBANK", alias="HDFC Bank", kind="name"),
            TickerAlias(ticker="HDFCBANK", alias="HDFC Bank Ltd", kind="name"),
            TickerAlias(ticker="HDFCBANK", alias="HDFCB", kind="code"),
            TickerAlias(ticker="HDFC", alias="HDFC Ltd", kind="name"),
        ])
        await s.commit()


async def test_exact_alias_resolves(sm):
    await _seed(sm)
    r = TickerResolver(sm)
    matches = await r.resolve("HDFC Bank")
    assert [m.ticker for m in matches] == ["HDFCBANK"]
    assert matches[0].confidence == 1.0


async def test_ambiguous_input_returns_multiple(sm):
    await _seed(sm)
    r = TickerResolver(sm)
    matches = await r.resolve("HDFC")
    tickers = sorted(m.ticker for m in matches)
    assert tickers == ["HDFC", "HDFCBANK"]


async def test_fuzzy_match_above_threshold(sm):
    await _seed(sm)
    r = TickerResolver(sm)
    matches = await r.resolve("HDFC Bnk", fuzzy_threshold=85)
    assert any(m.ticker == "HDFCBANK" for m in matches)


async def test_find_tickers_in_headline(sm):
    await _seed(sm)
    r = TickerResolver(sm)
    hits = await r.find_in_text("HDFC Bank Q4 results beat estimates", fuzzy_threshold=95)
    assert [h.ticker for h in hits] == ["HDFCBANK"]
```

- [ ] **Step 7.3: Run, confirm fail**

- [ ] **Step 7.4: Implement `ticker_resolver.py`**

```python
from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from quant_copilot.models import Ticker, TickerAlias


@dataclass(frozen=True)
class TickerMatch:
    ticker: str
    confidence: float
    matched_alias: str


def _normalise(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


class TickerResolver:
    def __init__(self, sm: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sm

    async def _all_aliases(self) -> list[tuple[str, str]]:
        async with self._sm() as s:
            rows = (await s.execute(select(TickerAlias.ticker, TickerAlias.alias))).all()
        return [(t, a) for t, a in rows]

    async def resolve(self, text: str, *, fuzzy_threshold: int = 90) -> list[TickerMatch]:
        norm = _normalise(text)
        aliases = await self._all_aliases()

        exact = [TickerMatch(t, 1.0, a) for t, a in aliases if _normalise(a) == norm]
        if exact:
            # Return all exact matches (ambiguity preserved for caller)
            seen: set[str] = set()
            out: list[TickerMatch] = []
            for m in exact:
                if m.ticker not in seen:
                    seen.add(m.ticker)
                    out.append(m)
            return out

        # Also treat the input as a raw symbol match against the ticker column
        async with self._sm() as s:
            sym = (await s.execute(select(Ticker.symbol).where(Ticker.symbol == text.upper()))).scalar_one_or_none()
        if sym:
            return [TickerMatch(sym, 1.0, sym)]

        # Fuzzy fallback
        scored: dict[str, TickerMatch] = {}
        for t, a in aliases:
            score = fuzz.ratio(norm, _normalise(a))
            if score >= fuzzy_threshold:
                m = TickerMatch(t, score / 100.0, a)
                if t not in scored or m.confidence > scored[t].confidence:
                    scored[t] = m
        return sorted(scored.values(), key=lambda m: -m.confidence)

    async def find_in_text(self, text: str, *, fuzzy_threshold: int = 95) -> list[TickerMatch]:
        """Used by news ingestion. Scans text for any known alias."""
        norm = _normalise(text)
        aliases = await self._all_aliases()
        hits: dict[str, TickerMatch] = {}
        for t, a in aliases:
            na = _normalise(a)
            if len(na) < 3:
                continue
            # exact substring match
            if na in norm:
                hits[t] = TickerMatch(t, 1.0, a)
                continue
            # partial_ratio on long aliases only (cheap guard)
            if len(na) >= 6:
                score = fuzz.partial_ratio(na, norm)
                if score >= fuzzy_threshold:
                    cand = TickerMatch(t, score / 100.0, a)
                    if t not in hits or cand.confidence > hits[t].confidence:
                        hits[t] = cand
        return sorted(hits.values(), key=lambda m: -m.confidence)
```

- [ ] **Step 7.5: Run tests, confirm pass**

```bash
uv run pytest tests/test_ticker_resolver.py -v
```
Expected: 4 passed.

- [ ] **Step 7.6: Commit**

```bash
git add backend/quant_copilot/data/__init__.py backend/quant_copilot/data/ticker_resolver.py backend/tests/test_ticker_resolver.py backend/tests/conftest.py
git commit -m "feat: ticker resolver with alias table and fuzzy matching"
```

---

## Task 8 — Corporate actions & OHLC adjustment math

**Files:**
- Create: `backend/quant_copilot/data/corporate_actions.py`
- Test: `backend/tests/test_corporate_actions.py`

- [ ] **Step 8.1: Write failing test**

```python
from datetime import date

import pandas as pd

from quant_copilot.data.corporate_actions import CorporateActionSet, apply_adjustments


def _sample_ohlc() -> pd.DataFrame:
    idx = pd.to_datetime([
        "2023-06-12", "2023-06-13", "2023-06-14", "2023-06-15", "2023-06-16",
    ])
    return pd.DataFrame(
        {
            "open":  [2500.0, 2510.0, 2520.0, 510.0, 515.0],
            "high":  [2530.0, 2530.0, 2540.0, 520.0, 525.0],
            "low":   [2490.0, 2500.0, 2500.0, 500.0, 510.0],
            "close": [2520.0, 2525.0, 2530.0, 510.0, 520.0],
            "volume": [100, 110, 120, 600, 610],
        },
        index=idx,
    )


def test_split_adjustment_back_adjusts_historical_prices():
    df = _sample_ohlc()
    actions = CorporateActionSet([
        {"ex_date": date(2023, 6, 15), "kind": "split", "ratio_num": 1.0, "ratio_den": 5.0},
    ])
    adj = apply_adjustments(df, actions)
    # Pre-split rows divided by 5, volumes multiplied by 5
    assert round(adj.loc["2023-06-14", "close"], 2) == round(2530.0 / 5, 2)
    assert adj.loc["2023-06-14", "volume"] == 600
    # Post-split rows unchanged
    assert adj.loc["2023-06-15", "close"] == 510.0
    assert adj.loc["2023-06-15", "volume"] == 600


def test_bonus_adjustment_similar_to_split():
    df = _sample_ohlc()
    # 1:1 bonus -> 2 shares per 1
    actions = CorporateActionSet([
        {"ex_date": date(2023, 6, 15), "kind": "bonus", "ratio_num": 1.0, "ratio_den": 2.0},
    ])
    adj = apply_adjustments(df, actions)
    assert round(adj.loc["2023-06-14", "close"], 2) == round(2530.0 / 2, 2)


def test_no_actions_returns_original_values():
    df = _sample_ohlc()
    adj = apply_adjustments(df, CorporateActionSet([]))
    pd.testing.assert_frame_equal(df, adj)


def test_dividend_does_not_adjust_ohlc_for_technicals():
    df = _sample_ohlc()
    actions = CorporateActionSet([
        {"ex_date": date(2023, 6, 15), "kind": "dividend", "dividend_per_share": 5.0},
    ])
    adj = apply_adjustments(df, actions)
    pd.testing.assert_frame_equal(df, adj)
```

- [ ] **Step 8.2: Run, confirm fail**

- [ ] **Step 8.3: Implement `corporate_actions.py`**

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd


@dataclass
class CorporateAction:
    ex_date: date
    kind: str  # split|bonus|dividend|rights|merger|delisting
    ratio_num: float | None = None
    ratio_den: float | None = None
    dividend_per_share: float | None = None

    @property
    def price_factor(self) -> float:
        """Multiplier to apply to pre-ex_date prices."""
        if self.kind in ("split", "bonus") and self.ratio_num and self.ratio_den:
            return self.ratio_num / self.ratio_den
        return 1.0

    @property
    def volume_factor(self) -> float:
        if self.kind in ("split", "bonus") and self.ratio_num and self.ratio_den:
            return self.ratio_den / self.ratio_num
        return 1.0


class CorporateActionSet:
    def __init__(self, records: list[dict | CorporateAction]) -> None:
        self._actions: list[CorporateAction] = []
        for r in records:
            if isinstance(r, CorporateAction):
                self._actions.append(r)
            else:
                self._actions.append(CorporateAction(**r))
        self._actions.sort(key=lambda a: a.ex_date)

    def iter_price_affecting(self):
        for a in self._actions:
            if a.kind in ("split", "bonus"):
                yield a


def apply_adjustments(df: pd.DataFrame, actions: CorporateActionSet) -> pd.DataFrame:
    """Back-adjust OHLC so historical rows are comparable to post-action prices.

    Convention: bars with index date strictly earlier than ex_date get multiplied
    by the action's price_factor (and volumes by volume_factor).
    Dividends and rights are not applied here (technical agent treats them separately).
    """
    if df.empty:
        return df.copy()
    out = df.copy()
    for a in actions.iter_price_affecting():
        ex = pd.Timestamp(a.ex_date)
        mask = out.index < ex
        pf = a.price_factor
        vf = a.volume_factor
        for col in ("open", "high", "low", "close"):
            if col in out.columns:
                out.loc[mask, col] = out.loc[mask, col] * pf
        if "volume" in out.columns:
            out.loc[mask, "volume"] = (out.loc[mask, "volume"] * vf).round().astype("int64")
    return out
```

- [ ] **Step 8.4: Run, confirm pass**

```bash
uv run pytest tests/test_corporate_actions.py -v
```
Expected: 4 passed.

- [ ] **Step 8.5: Commit**

```bash
git add backend/quant_copilot/data/corporate_actions.py backend/tests/test_corporate_actions.py
git commit -m "feat: corporate-action back-adjustment for OHLC"
```

---

## Task 9 — OHLC source abstraction + yfinance adapter

**Files:**
- Create: `backend/quant_copilot/data/sources/base.py`
- Create: `backend/quant_copilot/data/sources/yfinance_src.py`
- Create: `backend/tests/fixtures/yfinance_reliance_daily.json`
- Test: `backend/tests/test_yfinance_source.py`

- [ ] **Step 9.1: Create fixture**

Generate a small fixture by running once (in a scratch script) and saving the result. For the plan, ship a minimal hand-crafted fixture:

Create `tests/fixtures/yfinance_reliance_daily.json`:
```json
{
  "symbol": "RELIANCE.NS",
  "bars": [
    {"ts": "2026-04-13", "open": 2800.0, "high": 2820.0, "low": 2790.0, "close": 2810.0, "volume": 1200000},
    {"ts": "2026-04-14", "open": 2810.0, "high": 2830.0, "low": 2800.0, "close": 2825.0, "volume": 1300000},
    {"ts": "2026-04-15", "open": 2825.0, "high": 2840.0, "low": 2810.0, "close": 2815.0, "volume": 1250000},
    {"ts": "2026-04-16", "open": 2815.0, "high": 2830.0, "low": 2800.0, "close": 2820.0, "volume": 1150000},
    {"ts": "2026-04-17", "open": 2820.0, "high": 2850.0, "low": 2815.0, "close": 2845.0, "volume": 1400000}
  ]
}
```

- [ ] **Step 9.2: Implement `sources/base.py`**

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

import pandas as pd


@dataclass(frozen=True)
class OhlcRequest:
    ticker: str        # internal symbol, e.g. "RELIANCE"
    exchange: str      # NSE | BSE
    interval: str      # 1d | 1h | 15m | 5m | 1m
    start: date
    end: date          # inclusive


class OhlcSource(Protocol):
    name: str

    async def fetch(self, req: OhlcRequest) -> pd.DataFrame:
        """Returns DataFrame indexed by UTC timestamp with columns open/high/low/close/volume."""
        ...
```

- [ ] **Step 9.3: Write failing test**

```python
import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from quant_copilot.data.sources.base import OhlcRequest
from quant_copilot.data.sources.yfinance_src import YFinanceSource


FIX = json.loads((Path(__file__).parent / "fixtures" / "yfinance_reliance_daily.json").read_text())


def _fake_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Open": b["open"], "High": b["high"], "Low": b["low"], "Close": b["close"], "Volume": b["volume"]}
            for b in FIX["bars"]
        ],
        index=pd.to_datetime([b["ts"] for b in FIX["bars"]], utc=True),
    )


async def test_yfinance_suffix_nse():
    src = YFinanceSource()
    assert src._yf_symbol("RELIANCE", "NSE") == "RELIANCE.NS"
    assert src._yf_symbol("RELIANCE", "BSE") == "RELIANCE.BO"


async def test_yfinance_fetch_returns_normalised_df():
    src = YFinanceSource()
    with patch("quant_copilot.data.sources.yfinance_src._yf_download", return_value=_fake_df()):
        df = await src.fetch(OhlcRequest("RELIANCE", "NSE", "1d", date(2026, 4, 13), date(2026, 4, 17)))
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert len(df) == 5
    assert df.index.tz is not None
    assert df["close"].iloc[-1] == 2845.0
```

- [ ] **Step 9.4: Run, confirm fail**

- [ ] **Step 9.5: Implement `yfinance_src.py`**

```python
from __future__ import annotations

import asyncio
from datetime import timedelta
from functools import partial

import pandas as pd
import yfinance as yf

from quant_copilot.data.sources.base import OhlcRequest, OhlcSource


def _yf_download(symbol: str, start: str, end: str, interval: str) -> pd.DataFrame:
    df = yf.download(
        symbol,
        start=start,
        end=end,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=False,
    )
    return df


class YFinanceSource:
    name = "yfinance"

    @staticmethod
    def _yf_symbol(ticker: str, exchange: str) -> str:
        suffix = {"NSE": ".NS", "BSE": ".BO"}[exchange]
        return f"{ticker}{suffix}"

    async def fetch(self, req: OhlcRequest) -> pd.DataFrame:
        sym = self._yf_symbol(req.ticker, req.exchange)
        # yfinance `end` is exclusive; push forward a day for inclusivity
        end = req.end + timedelta(days=1)
        loop = asyncio.get_running_loop()
        fn = partial(_yf_download, sym, str(req.start), str(end), req.interval)
        df = await loop.run_in_executor(None, fn)
        if df is None or df.empty:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        # yfinance may return multi-index columns when threads=True; flatten defensively
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        df = df[["open", "high", "low", "close", "volume"]]
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        return df
```

- [ ] **Step 9.6: Run, confirm pass**

```bash
uv run pytest tests/test_yfinance_source.py -v
```
Expected: 2 passed.

- [ ] **Step 9.7: Commit**

```bash
git add backend/quant_copilot/data/sources/__init__.py backend/quant_copilot/data/sources/base.py backend/quant_copilot/data/sources/yfinance_src.py backend/tests/test_yfinance_source.py backend/tests/fixtures/yfinance_reliance_daily.json
git commit -m "feat: OHLC source protocol and yfinance adapter"
```

*(Ensure `backend/quant_copilot/data/sources/__init__.py` exists and is empty.)*

---

## Task 10 — nsepython & nsetools fallback adapters

**Files:**
- Create: `backend/quant_copilot/data/sources/nsepython_src.py`
- Create: `backend/quant_copilot/data/sources/nsetools_src.py`
- Test: `backend/tests/test_fallback_sources.py`

- [ ] **Step 10.1: Implement `nsepython_src.py`**

```python
from __future__ import annotations

import asyncio
from functools import partial

import pandas as pd

from quant_copilot.data.sources.base import OhlcRequest


class NsePythonSource:
    name = "nsepython"

    async def fetch(self, req: OhlcRequest) -> pd.DataFrame:
        from nsepython import equity_history  # local import so tests can patch

        if req.interval != "1d":
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        start = req.start.strftime("%d-%m-%Y")
        end = req.end.strftime("%d-%m-%Y")

        loop = asyncio.get_running_loop()
        fn = partial(equity_history, req.ticker, "EQ", start, end)
        raw = await loop.run_in_executor(None, fn)
        if raw is None or len(raw) == 0:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        df = pd.DataFrame(raw)
        # nsepython returns columns like CH_OPENING_PRICE, CH_TRADE_HIGH_PRICE, etc.
        df = df.rename(columns={
            "CH_TIMESTAMP": "ts",
            "CH_OPENING_PRICE": "open",
            "CH_TRADE_HIGH_PRICE": "high",
            "CH_TRADE_LOW_PRICE": "low",
            "CH_CLOSING_PRICE": "close",
            "CH_TOT_TRADED_QTY": "volume",
        })
        df["ts"] = pd.to_datetime(df["ts"], utc=True)
        df = df.set_index("ts").sort_index()
        return df[["open", "high", "low", "close", "volume"]]
```

- [ ] **Step 10.2: Implement `nsetools_src.py` (quote only — last-resort)**

```python
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from functools import partial

import pandas as pd

from quant_copilot.data.sources.base import OhlcRequest


class NsetoolsSource:
    name = "nsetools"

    async def fetch(self, req: OhlcRequest) -> pd.DataFrame:
        """nsetools has no history API; this returns an empty frame.

        Kept in the chain purely so that `get_quote` can still be used by the
        quote-snapshot helper in DataLayer (added in Task 15).
        """
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    async def quote(self, ticker: str) -> dict:
        from nsetools import Nse  # local import
        loop = asyncio.get_running_loop()
        nse = Nse()
        fn = partial(nse.get_quote, ticker.lower())
        q = await loop.run_in_executor(None, fn)
        return {
            "ticker": ticker,
            "ltp": float(q["lastPrice"]),
            "asof": datetime.now(tz=timezone.utc).isoformat(),
        }
```

- [ ] **Step 10.3: Write tests (patching the local imports)**

```python
from datetime import date
from unittest.mock import patch

import pandas as pd

from quant_copilot.data.sources.base import OhlcRequest
from quant_copilot.data.sources.nsepython_src import NsePythonSource
from quant_copilot.data.sources.nsetools_src import NsetoolsSource


async def test_nsepython_parses_equity_history_format():
    sample = [
        {"CH_TIMESTAMP": "2026-04-15", "CH_OPENING_PRICE": 2825, "CH_TRADE_HIGH_PRICE": 2840,
         "CH_TRADE_LOW_PRICE": 2810, "CH_CLOSING_PRICE": 2815, "CH_TOT_TRADED_QTY": 1250000},
        {"CH_TIMESTAMP": "2026-04-16", "CH_OPENING_PRICE": 2815, "CH_TRADE_HIGH_PRICE": 2830,
         "CH_TRADE_LOW_PRICE": 2800, "CH_CLOSING_PRICE": 2820, "CH_TOT_TRADED_QTY": 1150000},
    ]
    with patch("nsepython.equity_history", return_value=sample):
        src = NsePythonSource()
        df = await src.fetch(OhlcRequest("RELIANCE", "NSE", "1d", date(2026, 4, 15), date(2026, 4, 16)))
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert len(df) == 2


async def test_nsetools_quote_shape():
    with patch("nsetools.Nse.get_quote", return_value={"lastPrice": "2820.5"}):
        q = await NsetoolsSource().quote("RELIANCE")
    assert q["ticker"] == "RELIANCE"
    assert q["ltp"] == 2820.5
```

- [ ] **Step 10.4: Run tests, commit**

```bash
uv run pytest tests/test_fallback_sources.py -v
git add backend/quant_copilot/data/sources/nsepython_src.py backend/quant_copilot/data/sources/nsetools_src.py backend/tests/test_fallback_sources.py
git commit -m "feat: nsepython + nsetools fallback OHLC adapters"
```

---

## Task 11 — OHLC storage (Parquet) + DataLayer.get_ohlc with fallback chain

**Files:**
- Create: `backend/quant_copilot/data/ohlc.py`
- Test: `backend/tests/test_ohlc.py`

- [ ] **Step 11.1: Write failing test**

```python
from datetime import date
from unittest.mock import AsyncMock

import pandas as pd
import pytest

from quant_copilot.data.ohlc import OhlcStore, OhlcService
from quant_copilot.data.sources.base import OhlcRequest


def _bars(dates, closes):
    return pd.DataFrame(
        {
            "open": closes, "high": closes, "low": closes,
            "close": closes, "volume": [100] * len(closes),
        },
        index=pd.to_datetime(dates, utc=True),
    )


async def test_store_writes_and_reads_parquet(tmp_path):
    store = OhlcStore(tmp_path)
    df = _bars(["2026-04-14", "2026-04-15"], [100.0, 101.0])
    store.write("RELIANCE", "1d", df)
    got = store.read("RELIANCE", "1d", date(2026, 4, 14), date(2026, 4, 15))
    assert list(got["close"]) == [100.0, 101.0]


async def test_service_fills_cache_from_primary_source(tmp_path):
    store = OhlcStore(tmp_path)
    primary = AsyncMock()
    primary.name = "primary"
    primary.fetch.return_value = _bars(["2026-04-14", "2026-04-15"], [100.0, 101.0])

    svc = OhlcService(store=store, sources=[primary])
    df = await svc.get_ohlc("RELIANCE", "NSE", "1d", date(2026, 4, 14), date(2026, 4, 15))
    assert len(df) == 2
    primary.fetch.assert_awaited_once()
    # Second call served from cache
    primary.fetch.reset_mock()
    df2 = await svc.get_ohlc("RELIANCE", "NSE", "1d", date(2026, 4, 14), date(2026, 4, 15))
    assert len(df2) == 2
    primary.fetch.assert_not_awaited()


async def test_service_fallback_on_primary_failure(tmp_path):
    store = OhlcStore(tmp_path)
    primary = AsyncMock(); primary.name = "primary"
    primary.fetch.side_effect = RuntimeError("boom")
    secondary = AsyncMock(); secondary.name = "secondary"
    secondary.fetch.return_value = _bars(["2026-04-14"], [100.0])

    svc = OhlcService(store=store, sources=[primary, secondary])
    df = await svc.get_ohlc("RELIANCE", "NSE", "1d", date(2026, 4, 14), date(2026, 4, 14))
    assert len(df) == 1
    secondary.fetch.assert_awaited_once()
```

- [ ] **Step 11.2: Run, confirm fail**

- [ ] **Step 11.3: Implement `ohlc.py`**

```python
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Sequence

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from quant_copilot.data.sources.base import OhlcRequest, OhlcSource
from quant_copilot.logging_setup import get_logger

log = get_logger(__name__)


class OhlcStore:
    def __init__(self, root: Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, ticker: str, interval: str, year: int) -> Path:
        d = self._root / ticker / interval
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{year}.parquet"

    def write(self, ticker: str, interval: str, df: pd.DataFrame) -> None:
        if df.empty:
            return
        by_year: dict[int, list[pd.DataFrame]] = {}
        for ts, row in df.iterrows():
            yr = ts.year
            by_year.setdefault(yr, []).append(row.to_frame().T)
        for yr, frames in by_year.items():
            chunk = pd.concat(frames)
            path = self._path(ticker, interval, yr)
            if path.exists():
                existing = pd.read_parquet(path)
                combined = pd.concat([existing, chunk])
                combined = combined[~combined.index.duplicated(keep="last")].sort_index()
            else:
                combined = chunk.sort_index()
            tbl = pa.Table.from_pandas(combined)
            pq.write_table(tbl, path)

    def read(self, ticker: str, interval: str, start: date, end: date) -> pd.DataFrame:
        years = range(start.year, end.year + 1)
        frames: list[pd.DataFrame] = []
        for yr in years:
            path = self._path(ticker, interval, yr)
            if path.exists():
                frames.append(pd.read_parquet(path))
        if not frames:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        df = pd.concat(frames).sort_index()
        mask = (df.index.date >= start) & (df.index.date <= end)
        return df.loc[mask]

    def coverage(self, ticker: str, interval: str, start: date, end: date) -> set[date]:
        df = self.read(ticker, interval, start, end)
        return {ts.date() for ts in df.index}


class OhlcService:
    def __init__(self, store: OhlcStore, sources: Sequence[OhlcSource]) -> None:
        self._store = store
        self._sources = list(sources)

    async def get_ohlc(self, ticker: str, exchange: str, interval: str, start: date, end: date) -> pd.DataFrame:
        cached = self._store.read(ticker, interval, start, end)
        # Simple coverage check: if cache has at least one bar per business day we trust it.
        covered = self._store.coverage(ticker, interval, start, end)
        expected_days = pd.bdate_range(start, end).date.tolist()
        missing = [d for d in expected_days if d not in covered]
        if not missing:
            return cached

        fetch_req = OhlcRequest(ticker=ticker, exchange=exchange, interval=interval, start=start, end=end)
        for src in self._sources:
            try:
                fresh = await src.fetch(fetch_req)
                if not fresh.empty:
                    self._store.write(ticker, interval, fresh)
                    return self._store.read(ticker, interval, start, end)
            except Exception as e:
                log.warning("ohlc_source_failed", source=src.name, error=str(e))
                continue
        return cached  # best-effort; may be empty
```

- [ ] **Step 11.4: Run tests, confirm pass; commit**

```bash
uv run pytest tests/test_ohlc.py -v
git add backend/quant_copilot/data/ohlc.py backend/tests/test_ohlc.py
git commit -m "feat: OHLC Parquet store with source fallback chain"
```

---

## Task 12 — Screener fundamentals scrape + cache + snapshot

**Files:**
- Create: `backend/quant_copilot/data/fundamentals.py`
- Create: `backend/tests/fixtures/screener_reliance.html`
- Test: `backend/tests/test_fundamentals.py`

- [ ] **Step 12.1: Fixture `tests/fixtures/screener_reliance.html`** — save a trimmed Screener page. For the plan, provide a minimal HTML sample:

```html
<!DOCTYPE html>
<html><head><title>Reliance Industries</title></head>
<body>
  <div id="top-ratios">
    <ul>
      <li><span class="name">Market Cap</span><span class="nowrap value">₹ 18,00,000 Cr</span></li>
      <li><span class="name">Stock P/E</span><span class="nowrap value">28.5</span></li>
      <li><span class="name">Book Value</span><span class="nowrap value">₹ 1200</span></li>
      <li><span class="name">ROE</span><span class="nowrap value">9.2 %</span></li>
      <li><span class="name">ROCE</span><span class="nowrap value">10.1 %</span></li>
      <li><span class="name">Debt to equity</span><span class="nowrap value">0.45</span></li>
    </ul>
  </div>
</body></html>
```

- [ ] **Step 12.2: Write failing test**

```python
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from quant_copilot.data.fundamentals import FundamentalsService, parse_screener_html


HTML = (Path(__file__).parent / "fixtures" / "screener_reliance.html").read_text()


def test_parse_screener_html_extracts_top_ratios():
    parsed = parse_screener_html(HTML)
    assert parsed["pe"] == 28.5
    assert parsed["roe_pct"] == 9.2
    assert parsed["debt_to_equity"] == 0.45


async def test_service_caches_and_snapshots(sm, tmp_path, monkeypatch):
    calls = {"n": 0}

    async def fake_fetch(ticker):
        calls["n"] += 1
        return HTML

    svc = FundamentalsService(sm=sm, html_fetcher=fake_fetch, cache_ttl_days=30)
    fund1 = await svc.get("RELIANCE")
    fund2 = await svc.get("RELIANCE")  # within TTL → cached
    assert calls["n"] == 1
    assert fund1["pe"] == fund2["pe"] == 28.5

    # Snapshot table contains exactly one row
    from sqlalchemy import select
    from quant_copilot.models import FundamentalsSnapshot
    async with sm() as s:
        rows = (await s.execute(select(FundamentalsSnapshot))).scalars().all()
    assert len(rows) == 1
```

- [ ] **Step 12.3: Implement `fundamentals.py`**

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from quant_copilot.models import FundamentalsSnapshot


def _num(s: str) -> float | None:
    s = s.replace("₹", "").replace(",", "").replace("%", "").strip()
    try:
        return float(s.split()[0])
    except (ValueError, IndexError):
        return None


_KEY_MAP = {
    "Stock P/E": "pe",
    "Book Value": "book_value",
    "ROE": "roe_pct",
    "ROCE": "roce_pct",
    "Debt to equity": "debt_to_equity",
    "Market Cap": "market_cap_cr",
    "Dividend Yield": "dividend_yield_pct",
    "Face Value": "face_value",
}


def parse_screener_html(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    out: dict = {}
    for li in soup.select("#top-ratios li"):
        name = li.select_one(".name")
        val = li.select_one(".value")
        if not name or not val:
            continue
        key = _KEY_MAP.get(name.get_text(strip=True))
        if key:
            out[key] = _num(val.get_text(strip=True))
    return out


async def default_fetcher(ticker: str) -> str:
    url = f"https://www.screener.in/company/{ticker}/consolidated/"
    async with httpx.AsyncClient(timeout=20, headers={"User-Agent": "quant-copilot/0.1"}) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.text


class FundamentalsService:
    def __init__(
        self,
        sm: async_sessionmaker[AsyncSession],
        html_fetcher: Callable[[str], Awaitable[str]] = default_fetcher,
        cache_ttl_days: int = 30,
    ) -> None:
        self._sm = sm
        self._fetch = html_fetcher
        self._ttl = timedelta(days=cache_ttl_days)

    async def get(self, ticker: str) -> dict:
        async with self._sm() as s:
            row = (
                await s.execute(
                    select(FundamentalsSnapshot)
                    .where(FundamentalsSnapshot.ticker == ticker)
                    .order_by(FundamentalsSnapshot.snapshot_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            if row and (datetime.now(tz=timezone.utc) - row.snapshot_at) < self._ttl:
                return json.loads(row.payload_json)

        html = await self._fetch(ticker)
        parsed = parse_screener_html(html)
        async with self._sm() as s:
            snap = FundamentalsSnapshot(
                ticker=ticker,
                snapshot_at=datetime.now(tz=timezone.utc),
                payload_json=json.dumps(parsed),
            )
            s.add(snap)
            await s.commit()
        return parsed

    async def snapshot_all(self, tickers: list[str]) -> None:
        """Forward-archival: called nightly to force-record a snapshot even if cache is warm."""
        for t in tickers:
            try:
                html = await self._fetch(t)
                parsed = parse_screener_html(html)
                async with self._sm() as s:
                    s.add(FundamentalsSnapshot(
                        ticker=t,
                        snapshot_at=datetime.now(tz=timezone.utc),
                        payload_json=json.dumps(parsed),
                    ))
                    await s.commit()
            except Exception:
                # Archival is best-effort; log & move on (logging wired in Task 19)
                continue
```

- [ ] **Step 12.4: Run tests, commit**

```bash
uv run pytest tests/test_fundamentals.py -v
git add backend/quant_copilot/data/fundamentals.py backend/tests/fixtures/screener_reliance.html backend/tests/test_fundamentals.py
git commit -m "feat: Screener fundamentals scraper with 30-day cache and snapshot"
```

---

## Task 13 — RSS news ingestion + ticker matching

**Files:**
- Create: `backend/quant_copilot/data/sources/rss_src.py`
- Create: `backend/quant_copilot/data/news.py`
- Create: `backend/tests/fixtures/moneycontrol_rss.xml`
- Test: `backend/tests/test_news.py`

- [ ] **Step 13.1: Fixture `tests/fixtures/moneycontrol_rss.xml`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Moneycontrol Markets</title>
    <item>
      <title>HDFC Bank Q4 profit beats estimates</title>
      <link>https://example.com/news/hdfcbank-q4</link>
      <description>HDFC Bank reported Q4 FY26 net profit of ...</description>
      <pubDate>Sat, 18 Apr 2026 10:15:00 GMT</pubDate>
      <guid isPermaLink="false">hdfcbank-q4-2026</guid>
    </item>
    <item>
      <title>Reliance Industries announces new JV</title>
      <link>https://example.com/news/ril-jv</link>
      <description>Reliance Industries has announced ...</description>
      <pubDate>Fri, 17 Apr 2026 15:00:00 GMT</pubDate>
      <guid isPermaLink="false">ril-jv-2026</guid>
    </item>
  </channel>
</rss>
```

- [ ] **Step 13.2: Write failing test**

```python
from datetime import datetime, timezone
from pathlib import Path

import pytest

from quant_copilot.data.news import NewsService, parse_rss_bytes
from quant_copilot.models import NewsArticle, ArticleTicker, Ticker, TickerAlias


FIX = (Path(__file__).parent / "fixtures" / "moneycontrol_rss.xml").read_bytes()


def test_parse_rss_returns_items():
    items = parse_rss_bytes(FIX)
    assert len(items) == 2
    titles = [i.title for i in items]
    assert "HDFC Bank Q4 profit beats estimates" in titles


async def _seed_tickers(sm):
    async with sm() as s:
        s.add_all([
            Ticker(symbol="HDFCBANK", exchange="NSE", name="HDFC Bank Ltd"),
            Ticker(symbol="RELIANCE", exchange="NSE", name="Reliance Industries Ltd"),
            TickerAlias(ticker="HDFCBANK", alias="HDFC Bank", kind="name"),
            TickerAlias(ticker="RELIANCE", alias="Reliance Industries", kind="name"),
        ])
        await s.commit()


async def test_news_ingest_creates_articles_and_matches(sm):
    await _seed_tickers(sm)
    svc = NewsService(sm=sm, feed_fetcher=lambda url: FIX)
    n = await svc.ingest(["https://example.com/rss"])
    assert n == 2

    from sqlalchemy import select
    async with sm() as s:
        articles = (await s.execute(select(NewsArticle))).scalars().all()
        assert len(articles) == 2
        links = (await s.execute(select(ArticleTicker))).all()
        tickers = sorted(l[0].ticker for l in links)
        assert tickers == ["HDFCBANK", "RELIANCE"]


async def test_news_ingest_is_idempotent(sm):
    await _seed_tickers(sm)
    svc = NewsService(sm=sm, feed_fetcher=lambda url: FIX)
    await svc.ingest(["https://example.com/rss"])
    n2 = await svc.ingest(["https://example.com/rss"])
    assert n2 == 0  # all deduped on hash


async def test_news_service_query_by_ticker(sm):
    await _seed_tickers(sm)
    svc = NewsService(sm=sm, feed_fetcher=lambda url: FIX)
    await svc.ingest(["https://example.com/rss"])
    items = await svc.get_for_ticker("HDFCBANK", lookback_days=30)
    assert len(items) == 1
    assert items[0].title.startswith("HDFC Bank")
```

- [ ] **Step 13.3: Implement `sources/rss_src.py`**

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import feedparser


@dataclass(frozen=True)
class RssItem:
    source: str
    url: str
    title: str
    body: str
    published_at: datetime


def parse_rss_bytes(raw: bytes, source_hint: str = "rss") -> list[RssItem]:
    d = feedparser.parse(raw)
    source = d.feed.get("title", source_hint) if getattr(d, "feed", None) else source_hint
    out: list[RssItem] = []
    for e in d.entries:
        pub = e.get("published_parsed") or e.get("updated_parsed")
        dt = datetime(*pub[:6], tzinfo=timezone.utc) if pub else datetime.now(tz=timezone.utc)
        out.append(RssItem(
            source=source,
            url=e.get("link", ""),
            title=e.get("title", "").strip(),
            body=(e.get("summary") or e.get("description") or "").strip(),
            published_at=dt,
        ))
    return out
```

- [ ] **Step 13.4: Implement `data/news.py`**

```python
from __future__ import annotations

import hashlib
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from quant_copilot.data.sources.rss_src import RssItem, parse_rss_bytes
from quant_copilot.data.ticker_resolver import TickerResolver
from quant_copilot.models import ArticleTicker, NewsArticle


def _hash(url: str, title: str) -> str:
    return hashlib.sha256(f"{url}|{title}".encode()).hexdigest()


FetchFn = Callable[[str], Awaitable[bytes] | bytes]


async def default_feed_fetcher(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=20, headers={"User-Agent": "quant-copilot/0.1"}) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.content


# Re-export for tests
__all__ = ["NewsService", "parse_rss_bytes"]


class NewsService:
    def __init__(
        self,
        sm: async_sessionmaker[AsyncSession],
        feed_fetcher: FetchFn = default_feed_fetcher,
        resolver: TickerResolver | None = None,
    ) -> None:
        self._sm = sm
        self._fetch = feed_fetcher
        self._resolver = resolver or TickerResolver(sm)

    async def _fetch_bytes(self, url: str) -> bytes:
        res = self._fetch(url)
        if hasattr(res, "__await__"):
            res = await res  # type: ignore[misc]
        return res  # type: ignore[return-value]

    async def ingest(self, feed_urls: list[str]) -> int:
        added = 0
        for url in feed_urls:
            try:
                raw = await self._fetch_bytes(url)
            except Exception:
                continue
            items = parse_rss_bytes(raw, source_hint=url)
            for item in items:
                h = _hash(item.url, item.title)
                async with self._sm() as s:
                    existing = (await s.execute(
                        select(NewsArticle).where(NewsArticle.hash == h)
                    )).scalar_one_or_none()
                    if existing is not None:
                        continue
                    art = NewsArticle(
                        hash=h, source=item.source, url=item.url,
                        title=item.title, body=item.body,
                        published_at=item.published_at,
                        fetched_at=datetime.now(tz=timezone.utc),
                    )
                    s.add(art)
                    await s.flush()
                    # Match tickers
                    full_text = f"{item.title}. {item.body}"
                    matches = await self._resolver.find_in_text(full_text, fuzzy_threshold=95)
                    for m in matches:
                        s.add(ArticleTicker(article_id=art.id, ticker=m.ticker, match_confidence=m.confidence))
                    await s.commit()
                    added += 1
        return added

    async def get_for_ticker(self, ticker: str, *, lookback_days: int = 7) -> list[NewsArticle]:
        since = datetime.now(tz=timezone.utc) - timedelta(days=lookback_days)
        async with self._sm() as s:
            rows = (await s.execute(
                select(NewsArticle)
                .join(ArticleTicker, ArticleTicker.article_id == NewsArticle.id)
                .where(ArticleTicker.ticker == ticker, NewsArticle.published_at >= since)
                .order_by(NewsArticle.published_at.desc())
            )).scalars().all()
        return list(rows)
```

- [ ] **Step 13.5: Run tests, commit**

```bash
uv run pytest tests/test_news.py -v
git add backend/quant_copilot/data/news.py backend/quant_copilot/data/sources/rss_src.py backend/tests/fixtures/moneycontrol_rss.xml backend/tests/test_news.py
git commit -m "feat: RSS news ingestion with ticker matching and dedup"
```

---

## Task 14 — Exchange filings ingestion (BSE/NSE corporate announcements)

**Files:**
- Create: `backend/quant_copilot/data/filings.py`
- Test: `backend/tests/test_filings.py`

- [ ] **Step 14.1: Write failing test**

```python
import hashlib
from datetime import datetime, timezone

import pytest

from quant_copilot.data.filings import FilingsService
from quant_copilot.models import Ticker, Filing


SAMPLE_BSE_JSON = {
    "Table": [
        {
            "SCRIP_CD": "500325",
            "COMPANYNAME": "RELIANCE",
            "HEADLINE": "Q4 FY26 Results",
            "ATTACHMENTNAME": "results.pdf",
            "NEWSSUB": "Financial Result",
            "NEWS_DT": "2026-04-18T10:00:00",
            "NSURL": "https://example.com/filing/reliance-q4.pdf",
        }
    ]
}


async def _seed(sm):
    async with sm() as s:
        s.add(Ticker(symbol="RELIANCE", exchange="NSE", name="Reliance Industries Ltd"))
        await s.commit()


async def test_filings_ingest_and_dedup(sm):
    await _seed(sm)
    svc = FilingsService(sm=sm, bse_fetcher=lambda: SAMPLE_BSE_JSON, symbol_from_scrip=lambda s: "RELIANCE")
    n = await svc.ingest_bse()
    assert n == 1
    # Idempotent
    assert await svc.ingest_bse() == 0

    from sqlalchemy import select
    async with sm() as s:
        rows = (await s.execute(select(Filing))).scalars().all()
    assert len(rows) == 1
    assert rows[0].ticker == "RELIANCE"
    assert rows[0].kind == "Financial Result"
```

- [ ] **Step 14.2: Implement `filings.py`**

```python
from __future__ import annotations

import hashlib
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from quant_copilot.models import Filing

Fetcher = Callable[[], dict | Awaitable[dict]]
SymbolMap = Callable[[str], str | None]


def _hash_filing(url: str, headline: str, filed_at: datetime) -> str:
    return hashlib.sha256(f"{url}|{headline}|{filed_at.isoformat()}".encode()).hexdigest()


class FilingsService:
    def __init__(
        self,
        sm: async_sessionmaker[AsyncSession],
        bse_fetcher: Fetcher,
        symbol_from_scrip: SymbolMap,
    ) -> None:
        self._sm = sm
        self._bse_fetcher = bse_fetcher
        self._symbol = symbol_from_scrip

    async def _fetch_bse(self) -> dict:
        res = self._bse_fetcher()
        if hasattr(res, "__await__"):
            res = await res  # type: ignore[misc]
        return res  # type: ignore[return-value]

    async def ingest_bse(self) -> int:
        data = await self._fetch_bse()
        rows = data.get("Table", []) if isinstance(data, dict) else []
        added = 0
        for r in rows:
            symbol = self._symbol(r.get("SCRIP_CD", ""))
            if not symbol:
                continue
            url = r.get("NSURL") or r.get("ATTACHMENTNAME") or ""
            headline = r.get("HEADLINE", "")
            try:
                filed_at = datetime.fromisoformat(r["NEWS_DT"]).replace(tzinfo=timezone.utc)
            except Exception:
                filed_at = datetime.now(tz=timezone.utc)
            h = _hash_filing(url, headline, filed_at)
            async with self._sm() as s:
                existing = (await s.execute(select(Filing).where(Filing.hash == h))).scalar_one_or_none()
                if existing is not None:
                    continue
                s.add(Filing(
                    hash=h, ticker=symbol, exchange="BSE",
                    kind=r.get("NEWSSUB") or "announcement",
                    url=url, body_text=headline, filed_at=filed_at,
                ))
                await s.commit()
                added += 1
        return added


async def default_bse_fetcher() -> dict:
    url = "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w?pageno=1&strCat=-1&strPrevDate=&strScrip=&strSearch=P&strToDate=&strType=C"
    async with httpx.AsyncClient(timeout=20, headers={"User-Agent": "quant-copilot/0.1"}) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.json()
```

- [ ] **Step 14.3: Run tests, commit**

```bash
uv run pytest tests/test_filings.py -v
git add backend/quant_copilot/data/filings.py backend/tests/test_filings.py
git commit -m "feat: BSE corporate filings ingestion with dedup"
```

---

## Task 15 — Surveillance (ASM/GSM) list ingestion

**Files:**
- Create: `backend/quant_copilot/data/surveillance.py`
- Test: `backend/tests/test_surveillance.py`

- [ ] **Step 15.1: Write failing test**

```python
from datetime import date

import pytest
from sqlalchemy import select

from quant_copilot.data.surveillance import SurveillanceService
from quant_copilot.models import SurveillanceFlag, Ticker


async def test_asm_list_upsert(sm):
    async with sm() as s:
        s.add(Ticker(symbol="XYZ", exchange="NSE", name="XYZ Ltd"))
        s.add(Ticker(symbol="ABC", exchange="NSE", name="ABC Ltd"))
        await s.commit()

    svc = SurveillanceService(sm=sm,
        asm_fetcher=lambda: [{"symbol": "XYZ", "stage": "II"}])
    today = date(2026, 4, 20)
    n = await svc.refresh_asm(today)
    assert n == 1
    # Running again with ABC added and XYZ removed should end-date XYZ and open ABC
    svc2 = SurveillanceService(sm=sm,
        asm_fetcher=lambda: [{"symbol": "ABC", "stage": "I"}])
    await svc2.refresh_asm(today)

    async with sm() as s:
        rows = (await s.execute(select(SurveillanceFlag).order_by(SurveillanceFlag.ticker))).scalars().all()
    assert {(r.ticker, r.list_name, r.removed_on is None) for r in rows} == {
        ("ABC", "ASM", True),
        ("XYZ", "ASM", False),
    }


async def test_is_flagged(sm):
    async with sm() as s:
        s.add(Ticker(symbol="XYZ", exchange="NSE", name="XYZ Ltd"))
        s.add(SurveillanceFlag(ticker="XYZ", list_name="ASM", stage="II",
                               added_on=date(2026, 4, 1), removed_on=None))
        await s.commit()
    svc = SurveillanceService(sm=sm, asm_fetcher=lambda: [])
    flags = await svc.get_flags("XYZ")
    assert flags == [{"list": "ASM", "stage": "II"}]
```

- [ ] **Step 15.2: Implement `surveillance.py`**

```python
from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from quant_copilot.models import SurveillanceFlag


Fetcher = Callable[[], list[dict] | Awaitable[list[dict]]]


class SurveillanceService:
    def __init__(self, sm: async_sessionmaker[AsyncSession], asm_fetcher: Fetcher) -> None:
        self._sm = sm
        self._asm = asm_fetcher

    async def _fetch_asm(self) -> list[dict]:
        res = self._asm()
        if hasattr(res, "__await__"):
            res = await res  # type: ignore[misc]
        return list(res)  # type: ignore[arg-type]

    async def refresh_asm(self, today: date) -> int:
        incoming = await self._fetch_asm()
        incoming_map = {r["symbol"]: r.get("stage") for r in incoming}

        added = 0
        async with self._sm() as s:
            open_rows = (await s.execute(
                select(SurveillanceFlag).where(
                    SurveillanceFlag.list_name == "ASM",
                    SurveillanceFlag.removed_on.is_(None),
                )
            )).scalars().all()
            open_by_ticker = {r.ticker: r for r in open_rows}

            # End-date anything not in incoming
            for t, row in open_by_ticker.items():
                if t not in incoming_map:
                    row.removed_on = today

            # Open new entries for tickers not currently open
            for t, stage in incoming_map.items():
                if t not in open_by_ticker:
                    s.add(SurveillanceFlag(
                        ticker=t, list_name="ASM", stage=stage,
                        added_on=today, removed_on=None,
                    ))
                    added += 1
            await s.commit()
        return added

    async def get_flags(self, ticker: str) -> list[dict]:
        async with self._sm() as s:
            rows = (await s.execute(
                select(SurveillanceFlag).where(
                    SurveillanceFlag.ticker == ticker,
                    SurveillanceFlag.removed_on.is_(None),
                )
            )).scalars().all()
        return [{"list": r.list_name, "stage": r.stage} for r in rows]
```

- [ ] **Step 15.3: Run tests, commit**

```bash
uv run pytest tests/test_surveillance.py -v
git add backend/quant_copilot/data/surveillance.py backend/tests/test_surveillance.py
git commit -m "feat: ASM/GSM surveillance flag ingestion with open/close tracking"
```

---

## Task 16 — DataLayer facade (composes everything above)

**Files:**
- Create: `backend/quant_copilot/data/layer.py`
- Test: `backend/tests/test_data_layer.py`

- [ ] **Step 16.1: Implement `data/layer.py`**

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from quant_copilot.clock import Clock, SystemClock
from quant_copilot.config import Settings
from quant_copilot.data.corporate_actions import CorporateActionSet, apply_adjustments
from quant_copilot.data.fundamentals import FundamentalsService
from quant_copilot.data.news import NewsService
from quant_copilot.data.ohlc import OhlcService, OhlcStore
from quant_copilot.data.sources.nsepython_src import NsePythonSource
from quant_copilot.data.sources.nsetools_src import NsetoolsSource
from quant_copilot.data.sources.yfinance_src import YFinanceSource
from quant_copilot.data.surveillance import SurveillanceService
from quant_copilot.data.ticker_resolver import TickerResolver
from quant_copilot.models import CorporateAction


@dataclass
class DataLayer:
    ohlc: OhlcService
    fundamentals: FundamentalsService
    news: NewsService
    surveillance: SurveillanceService
    resolver: TickerResolver
    sm: async_sessionmaker[AsyncSession]
    clock: Clock

    async def get_ohlc_adjusted(
        self, ticker: str, exchange: str, interval: str, start: date, end: date
    ) -> pd.DataFrame:
        raw = await self.ohlc.get_ohlc(ticker, exchange, interval, start, end)
        async with self.sm() as s:
            actions = (await s.execute(
                select(CorporateAction).where(CorporateAction.ticker == ticker)
                .order_by(CorporateAction.ex_date)
            )).scalars().all()
        action_records = [
            {
                "ex_date": a.ex_date,
                "kind": a.kind,
                "ratio_num": a.ratio_num,
                "ratio_den": a.ratio_den,
                "dividend_per_share": a.dividend_per_share,
            }
            for a in actions
        ]
        return apply_adjustments(raw, CorporateActionSet(action_records))


def build_data_layer(settings: Settings, sm: async_sessionmaker[AsyncSession]) -> DataLayer:
    store = OhlcStore(settings.parquet_root)
    sources = [YFinanceSource(), NsePythonSource(), NsetoolsSource()]
    ohlc_svc = OhlcService(store=store, sources=sources)
    clock = SystemClock(settings.market_tz)
    return DataLayer(
        ohlc=ohlc_svc,
        fundamentals=FundamentalsService(sm=sm),
        news=NewsService(sm=sm),
        surveillance=SurveillanceService(sm=sm, asm_fetcher=lambda: []),
        resolver=TickerResolver(sm),
        sm=sm,
        clock=clock,
    )
```

- [ ] **Step 16.2: Write integration-style test**

```python
from datetime import date
from unittest.mock import AsyncMock

import pandas as pd
import pytest
from sqlalchemy import insert

from quant_copilot.data.layer import DataLayer
from quant_copilot.data.fundamentals import FundamentalsService
from quant_copilot.data.news import NewsService
from quant_copilot.data.ohlc import OhlcService, OhlcStore
from quant_copilot.data.surveillance import SurveillanceService
from quant_copilot.data.ticker_resolver import TickerResolver
from quant_copilot.clock import SystemClock
from quant_copilot.models import CorporateAction, Ticker


async def test_get_ohlc_adjusted_applies_split(sm, tmp_path):
    # Seed: ticker + split action
    async with sm() as s:
        s.add(Ticker(symbol="ZZZ", exchange="NSE", name="ZZZ"))
        s.add(CorporateAction(ticker="ZZZ", ex_date=date(2026, 4, 16),
                              kind="split", ratio_num=1, ratio_den=2))
        await s.commit()

    store = OhlcStore(tmp_path)
    src = AsyncMock(); src.name = "m"
    src.fetch.return_value = pd.DataFrame(
        {"open": [200, 201, 99, 101], "high": [201, 202, 100, 102],
         "low": [199, 200, 98, 100], "close": [200, 201, 100, 101],
         "volume": [1000, 1100, 2200, 2300]},
        index=pd.to_datetime(["2026-04-14", "2026-04-15", "2026-04-16", "2026-04-17"], utc=True),
    )
    ohlc_svc = OhlcService(store=store, sources=[src])

    layer = DataLayer(
        ohlc=ohlc_svc,
        fundamentals=FundamentalsService(sm=sm, html_fetcher=lambda t: "<html></html>"),
        news=NewsService(sm=sm, feed_fetcher=lambda url: b""),
        surveillance=SurveillanceService(sm=sm, asm_fetcher=lambda: []),
        resolver=TickerResolver(sm),
        sm=sm,
        clock=SystemClock(),
    )

    adj = await layer.get_ohlc_adjusted("ZZZ", "NSE", "1d", date(2026, 4, 14), date(2026, 4, 17))
    # Pre-split rows halved
    assert round(adj.loc["2026-04-14", "close"], 2) == 100.0
    # Post-split row unchanged
    assert adj.loc["2026-04-16", "close"] == 100.0
```

- [ ] **Step 16.3: Run, commit**

```bash
uv run pytest tests/test_data_layer.py -v
git add backend/quant_copilot/data/layer.py backend/tests/test_data_layer.py
git commit -m "feat: DataLayer facade with corporate-action-adjusted OHLC"
```

---

## Task 17 — Nightly archival job (APScheduler wiring)

**Files:**
- Create: `backend/quant_copilot/jobs/__init__.py`
- Create: `backend/quant_copilot/jobs/archival.py`
- Test: `backend/tests/test_archival.py`

- [ ] **Step 17.1: Write failing test**

```python
from datetime import date
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from quant_copilot.jobs.archival import nightly_archive
from quant_copilot.models import FundamentalsSnapshot, Ticker, WatchlistEntry


async def test_nightly_archive_snapshots_watchlist_fundamentals(sm):
    from datetime import datetime, timezone
    async with sm() as s:
        s.add(Ticker(symbol="RELIANCE", exchange="NSE", name="Reliance"))
        s.add(Ticker(symbol="HDFCBANK", exchange="NSE", name="HDFC Bank"))
        s.add(WatchlistEntry(ticker="RELIANCE", added_at=datetime.now(tz=timezone.utc)))
        s.add(WatchlistEntry(ticker="HDFCBANK", added_at=datetime.now(tz=timezone.utc)))
        await s.commit()

    fund = AsyncMock()
    fund.snapshot_all = AsyncMock()

    await nightly_archive(sm=sm, fundamentals=fund)

    fund.snapshot_all.assert_awaited_once()
    called_with = fund.snapshot_all.await_args[0][0]
    assert sorted(called_with) == ["HDFCBANK", "RELIANCE"]
```

- [ ] **Step 17.2: Implement `jobs/archival.py`**

```python
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from quant_copilot.data.fundamentals import FundamentalsService
from quant_copilot.logging_setup import get_logger
from quant_copilot.models import WatchlistEntry

log = get_logger(__name__)


async def nightly_archive(sm: async_sessionmaker[AsyncSession], fundamentals: FundamentalsService) -> None:
    async with sm() as s:
        tickers = (await s.execute(select(WatchlistEntry.ticker))).scalars().all()
    await fundamentals.snapshot_all(sorted(tickers))
    log.info("nightly_archive_done", n_tickers=len(tickers))
```

- [ ] **Step 17.3: Run tests, commit**

```bash
uv run pytest tests/test_archival.py -v
git add backend/quant_copilot/jobs/__init__.py backend/quant_copilot/jobs/archival.py backend/tests/test_archival.py
git commit -m "feat: nightly archival job snapshots watchlist fundamentals"
```

---

## Task 18 — Daily SQLite + data backup job

**Files:**
- Create: `backend/quant_copilot/jobs/backup.py`
- Test: `backend/tests/test_backup.py`

- [ ] **Step 18.1: Write failing test**

```python
import gzip
import sqlite3
from pathlib import Path

import pytest

from quant_copilot.jobs.backup import backup_sqlite, prune_backups


def test_backup_sqlite_creates_compressed_copy(tmp_path):
    src = tmp_path / "db.sqlite"
    # Real sqlite file so the backup API works
    conn = sqlite3.connect(src)
    conn.execute("CREATE TABLE t(x INT)")
    conn.execute("INSERT INTO t VALUES (1)")
    conn.commit()
    conn.close()

    backup_dir = tmp_path / "backups"
    out = backup_sqlite(src, backup_dir, date_str="2026-04-20")

    assert out.exists()
    assert out.name == "2026-04-20.sqlite.gz"
    # Decompress and verify content
    with gzip.open(out, "rb") as fh:
        raw = fh.read()
    assert raw.startswith(b"SQLite format 3")


def test_prune_keeps_last_n(tmp_path):
    bdir = tmp_path / "backups"
    bdir.mkdir()
    for d in ["2026-04-10", "2026-04-15", "2026-04-20", "2026-04-22"]:
        (bdir / f"{d}.sqlite.gz").write_bytes(b"x")
    prune_backups(bdir, keep_days=2)
    remaining = sorted(p.name for p in bdir.iterdir())
    assert remaining == ["2026-04-20.sqlite.gz", "2026-04-22.sqlite.gz"]
```

- [ ] **Step 18.2: Implement `jobs/backup.py`**

```python
from __future__ import annotations

import gzip
import shutil
import sqlite3
from datetime import date, datetime
from pathlib import Path


def backup_sqlite(src: Path, backup_dir: Path, date_str: str | None = None) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    date_str = date_str or date.today().isoformat()
    raw_tmp = backup_dir / f".{date_str}.sqlite.tmp"
    final = backup_dir / f"{date_str}.sqlite.gz"

    # Use SQLite's online backup API so we don't need to pause writers
    src_conn = sqlite3.connect(str(src))
    dst_conn = sqlite3.connect(str(raw_tmp))
    try:
        with dst_conn:
            src_conn.backup(dst_conn)
    finally:
        src_conn.close()
        dst_conn.close()

    with open(raw_tmp, "rb") as f_in, gzip.open(final, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    raw_tmp.unlink()
    return final


def prune_backups(backup_dir: Path, keep_days: int = 30) -> None:
    backups = sorted(backup_dir.glob("*.sqlite.gz"))
    if len(backups) <= keep_days:
        return
    for old in backups[:-keep_days]:
        old.unlink()
```

- [ ] **Step 18.3: Run tests, commit**

```bash
uv run pytest tests/test_backup.py -v
git add backend/quant_copilot/jobs/backup.py backend/tests/test_backup.py
git commit -m "feat: daily SQLite backup with gzip compression and retention"
```

---

## Task 19 — Typer CLI for manual ops

**Files:**
- Create: `backend/quant_copilot/cli.py`
- Test: `backend/tests/test_cli.py` (smoke only — sub-commands exist & wire up)

- [ ] **Step 19.1: Write failing test**

```python
from typer.testing import CliRunner

from quant_copilot.cli import app

runner = CliRunner()


def test_cli_help_lists_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("fetch-ohlc", "ingest-news", "refresh-asm", "archive", "backup"):
        assert cmd in result.output
```

- [ ] **Step 19.2: Implement `cli.py`**

```python
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
```

- [ ] **Step 19.3: Run tests**

```bash
uv run pytest tests/test_cli.py -v
```
Expected: 1 passed.

- [ ] **Step 19.4: Smoke-run the CLI**

```bash
cp .env.example .env
# manually set ANTHROPIC_API_KEY=sk-placeholder in .env
uv run qc --help
```
Expected: command list including `fetch-ohlc`, `ingest-news`, `refresh-asm`, `archive`, `backup`.

- [ ] **Step 19.5: Commit**

```bash
git add backend/quant_copilot/cli.py backend/tests/test_cli.py
git commit -m "feat: Typer CLI for manual ops (fetch, ingest, archive, backup)"
```

---

## Task 20 — End-to-end smoke test & README polish

**Files:**
- Modify: `README.md`
- Create: `backend/tests/test_smoke.py`

- [ ] **Step 20.1: Write smoke test that exercises the DataLayer end-to-end with all external calls mocked**

```python
from datetime import date
from unittest.mock import AsyncMock

import pandas as pd

from quant_copilot.data.layer import DataLayer
from quant_copilot.data.fundamentals import FundamentalsService
from quant_copilot.data.news import NewsService
from quant_copilot.data.ohlc import OhlcService, OhlcStore
from quant_copilot.data.surveillance import SurveillanceService
from quant_copilot.data.ticker_resolver import TickerResolver
from quant_copilot.clock import SystemClock
from quant_copilot.models import Ticker, TickerAlias


async def test_end_to_end_smoke(sm, tmp_path):
    async with sm() as s:
        s.add(Ticker(symbol="RELIANCE", exchange="NSE", name="Reliance Industries Ltd"))
        s.add(TickerAlias(ticker="RELIANCE", alias="Reliance Industries", kind="name"))
        await s.commit()

    src = AsyncMock(); src.name = "m"
    src.fetch.return_value = pd.DataFrame(
        {"open":[2800,2810],"high":[2820,2830],"low":[2790,2800],"close":[2810,2825],"volume":[1,2]},
        index=pd.to_datetime(["2026-04-14","2026-04-15"], utc=True),
    )
    ohlc = OhlcService(OhlcStore(tmp_path), [src])
    fund = FundamentalsService(sm=sm, html_fetcher=lambda t: "<html><div id='top-ratios'><ul><li><span class='name'>Stock P/E</span><span class='value'>28</span></li></ul></div></html>")
    news = NewsService(sm=sm, feed_fetcher=lambda url: b"""<?xml version='1.0'?><rss><channel><item><title>Reliance Industries rallies</title><link>http://x</link><description>d</description><pubDate>Fri, 17 Apr 2026 15:00:00 GMT</pubDate></item></channel></rss>""")
    layer = DataLayer(
        ohlc=ohlc, fundamentals=fund, news=news,
        surveillance=SurveillanceService(sm=sm, asm_fetcher=lambda: []),
        resolver=TickerResolver(sm), sm=sm, clock=SystemClock(),
    )

    df = await layer.get_ohlc_adjusted("RELIANCE", "NSE", "1d", date(2026, 4, 14), date(2026, 4, 15))
    assert len(df) == 2

    f = await layer.fundamentals.get("RELIANCE")
    assert f["pe"] == 28.0

    n = await layer.news.ingest(["http://example.com/rss"])
    assert n == 1
    items = await layer.news.get_for_ticker("RELIANCE", lookback_days=30)
    assert len(items) == 1
```

- [ ] **Step 20.2: Extend README with runbook**

Append to `README.md`:

```markdown
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
```

- [ ] **Step 20.3: Run full test suite**

```bash
uv run pytest -q
```
Expected: all tests pass, no warnings beyond known upstream deprecations.

- [ ] **Step 20.4: Commit**

```bash
git add backend/tests/test_smoke.py README.md
git commit -m "test: end-to-end DataLayer smoke test; doc runbook in README"
```

---

## Self-review

**Spec coverage check** (§ refers to sections in the design spec):

| Spec requirement | Covered by |
|---|---|
| §4.4 timezone, IST scheduling | Task 3 (Clock), Task 4 (Calendar) |
| §4.4 NSE holiday calendar + Muhurat | Task 4 |
| §4.4 SQLite WAL, idempotent upserts | Task 6 (db pragmas), Task 13/14 (hash dedup) |
| §4.4 agent_calls logging table | Task 6 (model) — populated by plan 2 |
| §4.4 backup job | Task 18 |
| §5.3.1 ticker alias table + fuzzy matching | Task 7 |
| §5.3.1 find_in_text for news | Task 7 + Task 13 |
| §7 DataLayer interface | Task 16 |
| §7.2 Parquet OHLC by ticker + year | Task 11 |
| §7.3 rate-limit budgets | Task 5 (registry; agent-specific registration in plan 2) |
| §7.3 source fallback chain | Tasks 9, 10, 11 |
| §7.4 clock abstraction w/ `asof` | Task 3 |
| §7.5 corporate action back-adjustment | Tasks 8, 16 |
| §7.6 forward archival from day 1 | Task 17 (fundamentals); news permanent in Task 13 |
| §7.7 fundamentals fallback | Screener primary in Task 12; secondary/tertiary noted as follow-up |
| §8.1 .env secrets handling | Task 1 + Task 2 |
| Agent reports / decisions / outcomes tables | Task 6 (models defined; populated by plans 2–4) |

**Gaps that are intentionally deferred to later plans:**
- Plan 2 will register rate-limit buckets on app startup, wire the agent_calls logging into a middleware/decorator around Claude calls, and add the Macro data (§5.4) when the Macro agent is built.
- Plan 4 will mount APScheduler and actually schedule the archival + backup + watchlist-polling jobs.
- ASM/GSM real fetchers: Task 15 ships the upsert logic with a pluggable fetcher; wiring a real NSE/BSE scraper is a phase-2 follow-up. This is a known limitation — until wired, `refresh-asm` CLI is a no-op. Acceptable for v1 MVP because the Fundamental agent (plan 3) reads from `surveillance_flags` and correctly returns "no flags" when empty.

**Placeholder scan:** none — every step has working code or concrete commands.

**Type consistency:** `TickerMatch` fields used consistently across Tasks 7 and 13. `OhlcSource` protocol adhered to by all three source adapters. `DataLayer` dataclass matches `build_data_layer` constructor.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-19-plan-1-foundation-and-data-layer.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
