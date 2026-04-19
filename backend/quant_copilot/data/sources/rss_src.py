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
