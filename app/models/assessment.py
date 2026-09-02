import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.opportunity import Opportunity


class Evidence(TimestampMixin, Base):
    """Cituojama teksto ištrauka, naudojama A ir/ar B vertinimo pagrindimui."""

    __tablename__ = "evidences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id"))
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    crawled_page_id: Mapped[int | None] = mapped_column(
        ForeignKey("crawled_pages.id"), nullable=True
    )

    quote: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(String(2048))
    section_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    used_for: Mapped[str] = mapped_column(String(20))  # eligibility | sales | both

    opportunity: Mapped["Opportunity"] = relationship(back_populates="evidences")


class EligibilityAssessment(TimestampMixin, Base):
    """A vertinimas: ar MB "Mostai" gali pati teikti paraišką."""

    __tablename__ = "eligibility_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id"), unique=True)

    verdict: Mapped[str] = mapped_column(String(20))  # taip | ne | su_salygomis | neaisku
    explanation_lt: Mapped[str] = mapped_column(Text)
    confidence: Mapped[int] = mapped_column(Integer)  # 0-100
    evidence_quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    evidence_section: Mapped[str | None] = mapped_column(String(500), nullable=True)
    what_to_verify: Mapped[str | None] = mapped_column(Text, nullable=True)

    rule_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
    assessed_by: Mapped[str] = mapped_column(String(20), default="rules")  # rules | llm | human
    assessed_at: Mapped[dt.datetime] = mapped_column(nullable=False)

    opportunity: Mapped["Opportunity"] = relationship(back_populates="eligibility")


class SalesAssessment(TimestampMixin, Base):
    """B vertinimas: pardavimo galimybė (šviesoforas)."""

    __tablename__ = "sales_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id"), unique=True)

    color: Mapped[str] = mapped_column(String(10))  # green | yellow | red
    reason_code: Mapped[str] = mapped_column(String(60))
    explanation_lt: Mapped[str] = mapped_column(Text)
    confidence: Mapped[int] = mapped_column(Integer)
    signals: Mapped[list[str]] = mapped_column(JSON, default=list)

    assessed_by: Mapped[str] = mapped_column(String(20), default="rules")
    assessed_at: Mapped[dt.datetime] = mapped_column(nullable=False)

    opportunity: Mapped["Opportunity"] = relationship(back_populates="sales")


class ChangeEvent(TimestampMixin, Base):
    """Pakeitimų istorija — kad atnaujintas dokumentas nekurtų tylaus perrašymo."""

    __tablename__ = "change_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id"))
    event_type: Mapped[str] = mapped_column(String(40))
    # created | content_changed | status_changed | assessment_changed | merged | duplicate_flagged
    description: Mapped[str] = mapped_column(Text)
    diff: Mapped[dict] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[dt.datetime] = mapped_column(nullable=False)

    opportunity: Mapped["Opportunity"] = relationship(back_populates="change_events")


class Notification(TimestampMixin, Base):
    """Pranešimų centro įrašas (in-app), su dedup raktu kad nedubliuotų."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(40))
    # new_green | changed_green_yellow | deadline_soon | source_error
    title: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)
    opportunity_id: Mapped[int | None] = mapped_column(
        ForeignKey("opportunities.id"), nullable=True
    )
    dedup_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    is_read: Mapped[bool] = mapped_column(default=False)
    emailed: Mapped[bool] = mapped_column(default=False)
