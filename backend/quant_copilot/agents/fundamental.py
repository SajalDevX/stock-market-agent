from __future__ import annotations

import json
from dataclasses import dataclass

from quant_copilot.agents.claude_client import ClaudeClient
from quant_copilot.agents.schemas import Evidence, FundamentalReport
from quant_copilot.analysis.fundamentals_eval import evaluate_fundamentals
from quant_copilot.data.layer import DataLayer


SYSTEM_PROMPT = """You are the Fundamental Analyst agent of an Indian equity research assistant.

You receive a structured valuation / quality / growth summary of a company's fundamentals, plus any surveillance flags (ASM / GSM membership). Write a concise, evidence-grounded interpretation (3–5 sentences) that explains what the numbers imply. Do not invent figures; only reference values given in the input. Do not give a buy or sell recommendation — describe the fundamental picture and flag the main risks, including any surveillance status.
""".strip()


@dataclass
class FundamentalAgent:
    data: DataLayer
    claude: ClaudeClient
    tier: str = "sonnet"

    async def analyze(self, *, ticker: str) -> FundamentalReport:
        payload = await self.data.fundamentals.get(ticker)
        flags = await self.data.surveillance.get_flags(ticker)
        evalr = evaluate_fundamentals(payload or {})

        from datetime import datetime, timezone
        asof = datetime.now(timezone.utc)
        evidence: list[Evidence] = []
        for k in ("pe", "roe_pct", "roce_pct", "debt_to_equity", "earnings_growth_pct"):
            v = (payload or {}).get(k)
            if v is not None:
                evidence.append(Evidence(kind="fundamental", label=k, value=float(v), asof=asof))

        red_flags = list(evalr["red_flags"])
        if flags:
            for f in flags:
                red_flags.append(f"Surveillance: on {f['list']} list" + (f" stage {f.get('stage')}" if f.get("stage") else ""))

        # Compose user message for Claude
        user_payload = {
            "ticker": ticker,
            "inputs": payload or {},
            "derived": {
                "valuation": evalr["valuation"],
                "quality": evalr["quality"],
                "growth": evalr["growth"],
                "score": evalr["score"],
            },
            "red_flags": red_flags,
            "surveillance": flags,
        }
        user_text = (
            f"Company: {ticker}\n\n"
            f"Fundamentals:\n```json\n{json.dumps(user_payload, indent=2, default=str)}\n```\n\n"
            f"Write the narrative interpretation as specified."
        )
        resp = await self.claude.complete(
            agent_name="fundamental", tier=self.tier,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_text}],
        )

        return FundamentalReport(
            score=float(evalr["score"]),
            reasoning=resp.text.strip(),
            evidence=evidence,
            valuation=evalr["valuation"],
            quality=evalr["quality"],
            growth=evalr["growth"],
            red_flags=red_flags,
            surveillance=flags,
        )
