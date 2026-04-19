from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

import pandas as pd

from quant_copilot.agents.claude_client import ClaudeClient
from quant_copilot.agents.schemas import Evidence, TechnicalReport
from quant_copilot.analysis.circuit import detect_circuit_state
from quant_copilot.analysis.indicators import compute_indicators
from quant_copilot.analysis.liquidity import avg_traded_value, below_liquidity_floor
from quant_copilot.analysis.patterns import detect_breakout, key_levels
from quant_copilot.data.layer import DataLayer


Timeframe = Literal["intraday", "swing", "long-term"]


def _trend_from_emas(close: float, ema20: float, ema50: float, ema200: float | None) -> str:
    # Classic: price above EMA20 > EMA50 (> EMA200) = up
    if ema200 is not None and not math.isnan(ema200):
        if close > ema20 > ema50 > ema200:
            return "up"
        if close < ema20 < ema50 < ema200:
            return "down"
    if close > ema20 > ema50:
        return "up"
    if close < ema20 < ema50:
        return "down"
    return "sideways"


def _momentum(rsi: float, macd_hist: float) -> str:
    if math.isnan(rsi) or math.isnan(macd_hist):
        return "neutral"
    if rsi > 60 and macd_hist > 0:
        return "strong"
    if rsi < 40 and macd_hist < 0:
        return "strong"
    if 45 <= rsi <= 55 and abs(macd_hist) < 0.5:
        return "weak"
    return "neutral"


def compute_technical_signals(df: pd.DataFrame, *, timeframe: Timeframe = "swing") -> dict:
    if df.empty:
        return {
            "trend": "sideways", "momentum": "neutral", "score": 0.0,
            "signals": [], "key_levels": {"support": [], "resistance": []},
            "liquidity_warning": True, "circuit_state": "none",
            "indicators_tail": {},
        }

    ind = compute_indicators(df)
    last = df.iloc[-1]
    last_ind = ind.iloc[-1]
    close = float(last["close"])

    def _f(val):
        if val is None:
            return float("nan")
        try:
            return float(val)
        except (TypeError, ValueError):
            return float("nan")

    ema200_raw = last_ind.get("ema200") if "ema200" in last_ind else None
    trend = _trend_from_emas(
        close,
        _f(last_ind.get("ema20")),
        _f(last_ind.get("ema50")),
        _f(ema200_raw) if ema200_raw is not None else None,
    )
    momentum = _momentum(
        _f(last_ind.get("rsi")),
        _f(last_ind.get("macd_hist")),
    )

    levels = key_levels(df)
    breakout = detect_breakout(df)

    signals: list[dict] = []
    # EMA-based trend signal
    if trend == "up":
        signals.append({"name": "ema_stack", "direction": "bullish", "strength": 0.6})
    elif trend == "down":
        signals.append({"name": "ema_stack", "direction": "bearish", "strength": 0.6})

    # Momentum signal
    rsi = _f(last_ind.get("rsi"))
    if not math.isnan(rsi):
        if rsi > 70:
            signals.append({"name": "rsi_overbought", "direction": "bearish", "strength": 0.3})
        elif rsi < 30:
            signals.append({"name": "rsi_oversold", "direction": "bullish", "strength": 0.3})
        elif rsi > 55 and momentum == "strong":
            signals.append({"name": "rsi_momentum", "direction": "bullish", "strength": 0.4})
        elif rsi < 45 and momentum == "strong":
            signals.append({"name": "rsi_momentum", "direction": "bearish", "strength": 0.4})

    # Breakout signal
    if breakout["breakout_direction"] == "up":
        signals.append({"name": "breakout", "direction": "bullish", "strength": 0.7})
    elif breakout["breakout_direction"] == "down":
        signals.append({"name": "breakout", "direction": "bearish", "strength": 0.7})

    # Aggregate score: sum of signed strengths, normalized to [-1, 1]
    raw = sum(s["strength"] * (1 if s["direction"] == "bullish" else -1) for s in signals)
    total_strength = sum(s["strength"] for s in signals) or 1.0
    score = max(-1.0, min(1.0, raw / total_strength))

    # Liquidity + circuit
    liq_warn = below_liquidity_floor(df, floor_inr=10_000_000)
    circuit = detect_circuit_state(df)

    # Compact indicator tail for the LLM
    tail = {k: (None if v is None or pd.isna(v) else float(v)) for k, v in last_ind.to_dict().items()}

    return {
        "trend": trend,
        "momentum": momentum,
        "score": round(score, 4),
        "signals": signals,
        "key_levels": levels,
        "liquidity_warning": liq_warn,
        "circuit_state": circuit,
        "indicators_tail": tail,
        "last_close": close,
        "last_asof": df.index[-1].to_pydatetime(),
    }


SYSTEM_PROMPT = """You are the Technical Analyst agent of an Indian equity research assistant.

You receive a structured summary of a stock's technical state (trend, momentum, indicator values, key levels, recent signals). Your job is to produce a concise, evidence-grounded narrative interpretation. Do NOT invent numbers — only reference values given in the input. Do NOT give buy/sell instructions; describe the technical picture and flag the main risks.

Output format (strict): plain prose, 3–5 sentences. No preamble, no disclaimers.
""".strip()


@dataclass
class TechnicalAgent:
    data: DataLayer
    claude: ClaudeClient
    lookback_days: int = 250
    tier: str = "sonnet"

    async def analyze(self, *, ticker: str, exchange: str, timeframe: str) -> TechnicalReport:
        end = date.today()
        start = end - timedelta(days=self.lookback_days)
        df = await self.data.get_ohlc_adjusted(ticker, exchange, "1d", start, end)

        sig = compute_technical_signals(df, timeframe=timeframe)  # type: ignore[arg-type]

        evidence: list[Evidence] = []
        if df.empty or sig.get("last_asof") is None:
            asof = None
        else:
            asof = sig["last_asof"]
            for key in ("rsi", "macd", "macd_hist", "ema20", "ema50", "ema200", "atr"):
                v = sig["indicators_tail"].get(key)
                if v is not None:
                    evidence.append(Evidence(kind="indicator", label=key.upper(), value=round(v, 4), asof=asof))

        if sig["liquidity_warning"]:
            return TechnicalReport(
                score=0.0,
                reasoning=(
                    f"{ticker} is below the liquidity floor "
                    f"(20-day avg traded value insufficient). No technical signal generated."
                ),
                evidence=evidence,
                trend=sig["trend"], momentum=sig["momentum"],
                key_levels=sig["key_levels"], signals=sig["signals"],
                liquidity_warning=True, circuit_state=sig["circuit_state"],
            )

        # Compose compact user message for Claude
        user_payload = {
            "ticker": ticker, "exchange": exchange, "timeframe": timeframe,
            "last_close": sig.get("last_close"),
            "trend": sig["trend"], "momentum": sig["momentum"],
            "score": sig["score"], "signals": sig["signals"],
            "key_levels": sig["key_levels"], "circuit_state": sig["circuit_state"],
            "indicators_tail": {k: (None if v is None else round(v, 4)) for k, v in sig["indicators_tail"].items()},
        }
        user_text = (
            f"Stock: {ticker} ({exchange}) — timeframe: {timeframe}\n\n"
            f"Technical state:\n```json\n{json.dumps(user_payload, default=str, indent=2)}\n```\n\n"
            f"Write the narrative interpretation as specified."
        )
        resp = await self.claude.complete(
            agent_name="technical", tier=self.tier,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_text}],
        )

        return TechnicalReport(
            score=float(sig["score"]),
            reasoning=resp.text.strip(),
            evidence=evidence,
            trend=sig["trend"], momentum=sig["momentum"],
            key_levels=sig["key_levels"], signals=sig["signals"],
            liquidity_warning=False, circuit_state=sig["circuit_state"],
        )
