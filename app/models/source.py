import datetime as dt

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import TimestampMixin


class Source(TimestampMixin, Base):
    """Vieno šaltinio (institucijos/savivaldybės/portalo) registro įrašas.

    Konfigūruojama per sources.yaml (seedinama į DB), bet redaguojama ir DB
    tiesiogiai, kad naują šaltinį būtų galima pridėti be branduolio perrašymo.
    """

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    institution_name: Mapped[str] = mapped_column(String(255))
    municipality: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    region: Mapped[str | None] = mapped_column(String(120), nullable=True)
    official_domain: Mapped[str] = mapped_column(String(255))

    start_urls: Mapped[list[str]] = mapped_column(JSON, default=list)
    source_type: Mapped[str] = mapped_column(String(30))
    # html | rss | sitemap | api | search | js | unknown

    allowed_document_domains: Mapped[list[str]] = mapped_column(JSON, default=list)
    relevant_path_hints: Mapped[list[str]] = mapped_column(JSON, default=list)
    ignored_path_hints: Mapped[list[str]] = mapped_column(JSON, default=list)

    adapter: Mapped[str] = mapped_column(String(50), default="generic_html")
    adapter_config: Mapped[dict] = mapped_column(JSON, default=dict)

    check_frequency_hours: Mapped[int] = mapped_column(Integer, default=24)

    robots_status: Mapped[str] = mapped_column(String(30), default="unknown")
    # allowed | disallowed_partial | disallowed_all | unreachable | unknown

    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    # active | blocked_bot_protection | needs_verification | disabled | error

    is_official: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    last_checked_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)
    last_success_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)
    last_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    check_results: Mapped[list["SourceCheckResult"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )


class CrawlRun(TimestampMixin, Base):
    """Vienas tikrinimo (crawl) paleidimas — arba visų šaltinių, arba vieno."""

    __tablename__ = "crawl_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[dt.datetime] = mapped_column(nullable=False)
    finished_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)
    trigger: Mapped[str] = mapped_column(String(20), default="manual")  # manual | scheduled
    scope: Mapped[str] = mapped_column(String(20), default="all")  # all | single_source
    source_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    # running | completed | completed_with_errors | failed

    sources_total: Mapped[int] = mapped_column(Integer, default=0)
    sources_ok: Mapped[int] = mapped_column(Integer, default=0)
    sources_error: Mapped[int] = mapped_column(Integer, default=0)
    sources_blocked: Mapped[int] = mapped_column(Integer, default=0)
    new_opportunities: Mapped[int] = mapped_column(Integer, default=0)
    updated_opportunities: Mapped[int] = mapped_column(Integer, default=0)

    log: Mapped[str | None] = mapped_column(Text, nullable=True)

    check_results: Mapped[list["SourceCheckResult"]] = relationship(
        back_populates="crawl_run", cascade="all, delete-orphan"
    )


class SourceCheckResult(TimestampMixin, Base):
    """Vieno šaltinio patikrinimo rezultatas per konkretų CrawlRun."""

    __tablename__ = "source_check_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crawl_run_id: Mapped[int] = mapped_column(ForeignKey("crawl_runs.id"))
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))

    status: Mapped[str] = mapped_column(String(30))
    # ok | error | blocked_bot_protection | skipped_not_modified
    pages_fetched: Mapped[int] = mapped_column(Integer, default=0)
    pages_unchanged: Mapped[int] = mapped_column(Integer, default=0)
    documents_found: Mapped[int] = mapped_column(Integer, default=0)
    opportunities_found: Mapped[int] = mapped_column(Integer, default=0)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    crawl_run: Mapped["CrawlRun"] = relationship(back_populates="check_results")
    source: Mapped["Source"] = relationship(back_populates="check_results")
