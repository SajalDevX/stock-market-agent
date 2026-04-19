from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any

from quant_copilot.agents.claude_client import ClaudeClient
from quant_copilot.agents.conviction import compute_conviction
from quant_copilot.agents.fundamental import FundamentalAgent
from quant_copilot.agents.news import NewsAgent
from quant_copilot.agents.schemas import (
    Disagreement, FundamentalReport, NewsReport, OrchestratorReport, TechnicalReport,
)
from quant_copilot.agents.technical import TechnicalAgent
from quant_copilot.data.layer import DataLayer


ORCHESTRATOR_SYSTEM = """You are the Orchestrator of an Indian equity research assistant.

You receive the structured reports of specialist agents (technical, fundamental, news) for a single stock, plus a deterministic verdict and conviction percentage already computed from their scores.

Your job is to write ONLY the `thesis`, `risks`, `entry`, `stop`, and `target` fields. Do NOT change the verdict or conviction — those are fixed.

STRICT RULES:
- Respond with a single JSON object inside ```json ... ``` fences.
- `thesis` is 2–4 sentences summarising the *why*. If agents disagree, name the disagreement.
- `risks` is 2–4 short bullet phrases.
- `entry`, `stop`, `target` are floats (or null if you cannot justify them from the agents' key_levels).
- Do not reference data that is not in the agent reports.

Response schema:
{"thesis":"...","risks":["..."],"entry":null|<float>,"stop":null|<float>,"target":null|<float>}
""".strip()


def _extract_json_block(text: str) -> dict:
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        return json.loads(m.group(1))
    return json.loads(text.strip())


def _detect_disagreements(scores: dict[str, float]) -> list[Disagreement]:
    pos = [k for k, v in scores.items() if v > 0.1]
    neg = [k for k, v in scores.items() if v < -0.1]
    if pos and neg:
        return [Disagreement(
            between=sorted(pos + neg),
            summary=f"{', '.join(sorted(pos))} lean bullish; {', '.join(sorted(neg))} lean bearish.",
        )]
    return []


AGENTS_FOR_TIMEFRAME = {
    "intraday":  ["technical", "news"],
    "swing":     ["technical", "fundamental", "news"],
    "long-term": ["technical", "fundamental", "news"],
}


@dataclass
class Orchestrator:
    data: DataLayer
    claude: ClaudeClient
    technical: TechnicalAgent
    fundamental: FundamentalAgent
    news: NewsAgent
    tier: str = "sonnet"

    async def research(self, *, ticker: str, exchange: str, timeframe: str) -> OrchestratorReport:
        agent_names = AGENTS_FOR_TIMEFRAME.get(timeframe, AGENTS_FOR_TIMEFRAME["swing"])

        tasks: dict[str, Any] = {}
        if "technical" in agent_names:
            tasks["technical"] = self.technical.analyze(ticker=ticker, exchange=exchange, timeframe=timeframe)
        if "fundamental" in agent_names:
            tasks["fundamental"] = self.fundamental.analyze(ticker=ticker)
        if "news" in agent_names:
            tasks["news"] = self.news.analyze(ticker=ticker)

        results_list = await asyncio.gather(*tasks.values(), return_exceptions=True)
        results: dict[str, Any] = dict(zip(tasks.keys(), results_list))

        scores: dict[str, float] = {}
        agent_reports: dict[str, Any] = {}
        for name, r in results.items():
            if isinstance(r, Exception):
                agent_reports[name] = {"error": f"{type(r).__name__}: {r}"}
                continue
            scores[name] = float(r.score)
            agent_reports[name] = r.model_dump(mode="json")

        conviction_info = compute_conviction(scores, timeframe=timeframe)
        disagreements = _detect_disagreements(scores)

        # Reference price from the technical report (last close), if available
        tech = results.get("technical")
        ref_price = 0.0
        if isinstance(tech, TechnicalReport):
            for ev in tech.evidence:
                pass  # evidence doesn't carry price; use key_levels midpoint as crude fallback
            supports = tech.key_levels.get("support", [])
            resistances = tech.key_levels.get("resistance", [])
            if supports or resistances:
                all_lvls = (supports or []) + (resistances or [])
                ref_price = float(sum(all_lvls) / len(all_lvls))

        thesis_prompt = {
            "ticker": ticker, "timeframe": timeframe,
            "fixed": {
                "verdict": conviction_info["verdict"],
                "conviction": conviction_info["conviction"],
                "weighted_score": conviction_info["weighted"],
                "effective_weights": conviction_info["effective_weights"],
            },
            "agent_reports": agent_reports,
            "disagreements": [d.model_dump() for d in disagreements],
        }
        user_text = (
            f"Stock: {ticker} ({exchange}) — timeframe: {timeframe}\n\n"
            f"Agent reports + fixed verdict:\n```json\n{json.dumps(thesis_prompt, indent=2, default=str)}\n```\n\n"
            f"Return the JSON object per the schema."
        )
        resp = await self.claude.complete(
            agent_name="orchestrator", tier=self.tier,
            system=ORCHESTRATOR_SYSTEM,
            messages=[{"role": "user", "content": user_text}],
        )
        parsed = _extract_json_block(resp.text)

        return OrchestratorReport(
            ticker=ticker, timeframe=timeframe,  # type: ignore[arg-type]
            verdict=conviction_info["verdict"],  # type: ignore[arg-type]
            conviction=conviction_info["conviction"],
            conviction_breakdown=scores,
            thesis=str(parsed.get("thesis", "")),
            risks=list(parsed.get("risks", [])),
            entry=(float(parsed["entry"]) if parsed.get("entry") is not None else None),
            stop=(float(parsed["stop"]) if parsed.get("stop") is not None else None),
            target=(float(parsed["target"]) if parsed.get("target") is not None else None),
            ref_price=ref_price,
            agent_reports=agent_reports,
            disagreements=disagreements,
        )
