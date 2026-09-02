import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.assessment import ChangeEvent, EligibilityAssessment, Evidence, SalesAssessment
    from app.models.organization import Contact


class Opportunity(TimestampMixin, Base):
    """Pagrindinė esybė: aptikta galimybė (konkursas / kvietimas / finansuotas projektas)."""

    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    title: Mapped[str] = mapped_column(String(500))
    organizer_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    grantee_or_implementer_name: Mapped[str | None] = mapped_column(String(500), nullable=True)

    municipality: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    region: Mapped[str | None] = mapped_column(String(120), nullable=True)

    topics: Mapped[list[str]] = mapped_column(JSON, default=list)
    target_groups: Mapped[list[str]] = mapped_column(JSON, default=list)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    published_at_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_at: Mapped[dt.date | None] = mapped_column(nullable=True)

    application_start_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    application_start: Mapped[dt.date | None] = mapped_column(nullable=True)
    application_end_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    application_end: Mapped[dt.date | None] = mapped_column(nullable=True)

    activity_start_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    activity_start: Mapped[dt.date | None] = mapped_column(nullable=True)
    activity_end_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    activity_end: Mapped[dt.date | None] = mapped_column(nullable=True)

    total_budget_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_budget_cents: Mapped[int | None] = mapped_column(nullable=True)
    min_grant_cents: Mapped[int | None] = mapped_column(nullable=True)
    max_grant_cents: Mapped[int | None] = mapped_column(nullable=True)
    training_budget_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    training_budget_cents: Mapped[int | None] = mapped_column(nullable=True)

    status: Mapped[str] = mapped_column(String(30), default="unclear", index=True)
    # planned | open | funded_ongoing | finished | unclear

    nuance_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_action_date: Mapped[dt.date | None] = mapped_column(nullable=True)
    call_script: Mapped[str | None] = mapped_column(Text, nullable=True)

    primary_url: Mapped[str] = mapped_column(String(2048))
    source_urls: Mapped[list[str]] = mapped_column(JSON, default=list)
    document_urls: Mapped[list[str]] = mapped_column(JSON, default=list)

    canonical_key: Mapped[str] = mapped_column(String(500), index=True)
    content_hash: Mapped[str] = mapped_column(String(64))

    first_seen_at: Mapped[dt.datetime] = mapped_column(nullable=False)
    last_changed_at: Mapped[dt.datetime] = mapped_column(nullable=False)
    last_checked_at: Mapped[dt.datetime] = mapped_column(nullable=False)

    merged_into_id: Mapped[int | None] = mapped_column(
        ForeignKey("opportunities.id"), nullable=True
    )
    possible_duplicate_of_id: Mapped[int | None] = mapped_column(
        ForeignKey("opportunities.id"), nullable=True
    )

    eligibility: Mapped["EligibilityAssessment | None"] = relationship(
        back_populates="opportunity", uselist=False, cascade="all, delete-orphan"
    )
    sales: Mapped["SalesAssessment | None"] = relationship(
        back_populates="opportunity", uselist=False, cascade="all, delete-orphan"
    )
    evidences: Mapped[list["Evidence"]] = relationship(
        back_populates="opportunity", cascade="all, delete-orphan"
    )
    contacts: Mapped[list["Contact"]] = relationship()
    change_events: Mapped[list["ChangeEvent"]] = relationship(
        back_populates="opportunity", cascade="all, delete-orphan"
    )
    review: Mapped["UserReview | None"] = relationship(
        back_populates="opportunity", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def processing_status(self) -> str:
        """Ar šis įrašas yra tik neapdorotas raktažodžių sutapimas, ar reikia
        žmogaus peržiūros, ar patikimai patvirtinta galimybė — žr.
        app/rules/processing_status.py dėl pilno pagrindimo."""
        from app.rules.processing_status import compute_processing_status

        return compute_processing_status(self)


class UserReview(TimestampMixin, Base):
    """Žmogaus žymos ir pastabos apie Opportunity."""

    __tablename__ = "user_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id"), unique=True)

    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    interest: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # interested | not_interested | contacted | remind_later
    remind_at: Mapped[dt.date | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    eligibility_override: Mapped[str | None] = mapped_column(String(30), nullable=True)
    sales_color_override: Mapped[str | None] = mapped_column(String(10), nullable=True)

    opportunity: Mapped["Opportunity"] = relationship(back_populates="review")
