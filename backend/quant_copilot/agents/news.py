from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select

from quant_copilot.agents.citations import CitationVerifier
from quant_copilot.agents.claude_client import ClaudeClient
from quant_copilot.agents.schemas import Evidence, NewsCitation, NewsReport
from quant_copilot.data.layer import DataLayer
from quant_copilot.models import Filing


SYSTEM_PROMPT = """You are the News Analyst agent of an Indian equity research assistant.

You receive a JSON array of recent news articles and corporate filings for a company. Summarise what's material, identify notable events, and score the overall sentiment from -1.0 (very negative) to +1.0 (very positive).

STRICT RULES:
- You MUST respond with a single JSON object (no prose outside). Start your response with ```json and end with ```.
- Every `citations[].artifact_id` you include must be a STRING that exactly matches an `id` from the input list. Do not invent IDs, URLs, or titles.
- If the input list is empty, return sentiment 0 and no citations.

Response schema:
{
  "headline_summary": "<one-paragraph summary>",
  "material_events": ["<short phrases>"],
  "sentiment": <float -1 to 1>,
  "reasoning": "<2-3 sentences explaining the score>",
  "citations": [{"artifact_kind": "news_article"|"filing", "artifact_id": "<id>", "title": "<title>", "url": "<url>"}]
}
""".strip()


def _extract_json_block(text: str) -> dict:
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        return json.loads(m.group(1))
    # Fallback: if the model forgot the fence, try raw JSON
    return json.loads(text.strip())


@dataclass
class NewsAgent:
    data: DataLayer
    claude: ClaudeClient
    tier: str = "haiku"
    verifier: CitationVerifier | None = None

    async def analyze(self, *, ticker: str, lookback_days: int = 7) -> NewsReport:
        articles = await self.data.news.get_for_ticker(ticker, lookback_days=lookback_days)
        from datetime import timedelta
        since = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        async with self.data.sm() as s:
            filings = (await s.execute(
                select(Filing).where(Filing.ticker == ticker, Filing.filed_at >= since)
                .order_by(Filing.filed_at.desc())
            )).scalars().all()

        if not articles and not filings:
            return NewsReport(
                score=0.0, reasoning="No recent news or filings in the lookback window.",
                evidence=[], headline_summary="", material_events=[],
                sentiment=0.0, citations=[],
            )

        items: list[dict] = []
        for a in articles:
            items.append({
                "id": str(a.id), "kind": "news_article",
                "title": a.title, "url": a.url,
                "published_at": a.published_at.isoformat() if a.published_at else None,
                "body": (a.body or "")[:800],
            })
        for f in filings:
            items.append({
                "id": str(f.id), "kind": "filing",
                "title": f.body_text or f.kind, "url": f.url,
                "published_at": f.filed_at.isoformat() if f.filed_at else None,
                "body": (f.body_text or "")[:800],
            })
        allowed_ids = {f"{i['kind']}:{i['id']}" for i in items}

        user_text = (
            f"Company: {ticker}\n\n"
            f"Articles/filings (JSON):\n```json\n{json.dumps(items, indent=2, default=str)}\n```\n\n"
            f"Allowed citation IDs: {sorted(allowed_ids)}\n\n"
            f"Produce the JSON response per the schema."
        )
        messages = [{"role": "user", "content": user_text}]

        resp = await self.claude.complete(
            agent_name="news", tier=self.tier,
            system=SYSTEM_PROMPT, messages=messages,
        )
        parsed = _extract_json_block(resp.text)
        citations = [NewsCitation(**c) for c in parsed.get("citations", [])]

        # Citation grounding post-check + one retry
        if self.verifier is not None and citations:
            result = await self.verifier.verify(citations)
            if not result.all_valid:
                retry_msg = (
                    f"Your previous response included citations that do not resolve to "
                    f"the provided items: {result.missing_ids}. Re-emit the JSON using "
                    f"ONLY ids from this list: {sorted(allowed_ids)}."
                )
                messages = messages + [
                    {"role": "assistant", "content": resp.text},
                    {"role": "user", "content": retry_msg},
                ]
                resp = await self.claude.complete(
                    agent_name="news", tier=self.tier,
                    system=SYSTEM_PROMPT, messages=messages,
                )
                parsed = _extract_json_block(resp.text)
                citations = [NewsCitation(**c) for c in parsed.get("citations", [])]
                result = await self.verifier.verify(citations)
                if not result.all_valid:
                    raise RuntimeError(
                        f"NewsAgent could not ground its citations after one retry: {result.missing_ids}"
                    )

        sentiment = float(parsed.get("sentiment", 0.0))
        sentiment = max(-1.0, min(1.0, sentiment))
        asof = datetime.now(timezone.utc)
        evidence: list[Evidence] = [
            Evidence(kind="news", label=str(c.title or c.artifact_id),
                     value=None, asof=asof, ref=f"{c.artifact_kind}:{c.artifact_id}")
            for c in citations
        ]

        return NewsReport(
            score=sentiment,
            reasoning=str(parsed.get("reasoning", "")).strip(),
            evidence=evidence,
            headline_summary=str(parsed.get("headline_summary", "")),
            material_events=list(parsed.get("material_events", [])),
            sentiment=sentiment,
            citations=citations,
        )
