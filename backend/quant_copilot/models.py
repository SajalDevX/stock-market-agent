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
