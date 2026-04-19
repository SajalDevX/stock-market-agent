from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from quant_copilot.agents.claude_client import ClaudeClient
from quant_copilot.agents.schemas import Evidence, MacroReport
from quant_copilot.analysis.macro import evaluate_macro
from quant_copilot.data.macro import MacroData


SYSTEM_PROMPT = """You are the Macro agent of an Indian equity research assistant.

You receive a structured snapshot of Indian indices, global indices, crude, and USD-INR, along with a deterministic regime classification and tailwinds/headwinds. Write a concise (2-3 sentences) narrative interpretation. Do not invent data; only reference values in the input. Do not give stock recommendations.
""".strip()


@dataclass
class MacroAgent:
    macro_data: MacroData
    claude: ClaudeClient
    tier: str = "haiku"

    async def analyze(self) -> MacroReport:
        snap = await self.macro_data.snapshot()
        evalr = evaluate_macro(snap)

        asof = datetime.now(timezone.utc)
        evidence: list[Evidence] = []
        for k in ("nifty", "banknifty"):
            cp = snap.get(k, {}).get("change_pct")
            if cp is not None:
                evidence.append(Evidence(kind="macro", label=f"{k}_change_pct", value=float(cp), asof=asof))
        for k in ("dow", "nasdaq", "crude"):
            cp = snap.get("global", {}).get(k, {}).get("change_pct")
            if cp is not None:
                evidence.append(Evidence(kind="macro", label=f"global.{k}_change_pct", value=float(cp), asof=asof))

        user_payload = {"snapshot": snap, "derived": evalr}
        user_text = (
            f"Market snapshot:\n```json\n{json.dumps(user_payload, indent=2, default=str)}\n```\n\n"
            f"Write the interpretation as specified."
        )
        resp = await self.claude.complete(
            agent_name="macro", tier=self.tier,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_text}],
        )

        return MacroReport(
            score=float(evalr["score"]),
            reasoning=resp.text.strip(),
            evidence=evidence,
            regime=evalr["regime"],
            tailwinds=evalr["tailwinds"],
            headwinds=evalr["headwinds"],
        )
