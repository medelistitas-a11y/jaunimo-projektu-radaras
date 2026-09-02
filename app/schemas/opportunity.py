from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class ContactOut(BaseModel):
    id: int
    full_name: str | None
    role_title: str | None
    organization_name: str | None
    phone_raw: str | None
    phone_normalized: str | None
    email: str | None
    is_general_contact: bool

    model_config = {"from_attributes": True}


class EvidenceOut(BaseModel):
    id: int
    quote: str
    source_url: str
    section_title: str | None
    used_for: str

    model_config = {"from_attributes": True}


class ChangeEventOut(BaseModel):
    id: int
    event_type: str
    description: str
    occurred_at: dt.datetime

    model_config = {"from_attributes": True}


class EligibilityOut(BaseModel):
    verdict: str
    explanation_lt: str
    confidence: int
    evidence_quote: str | None
    evidence_url: str | None
    what_to_verify: str | None

    model_config = {"from_attributes": True}


class SalesOut(BaseModel):
    color: str
    reason_code: str
    explanation_lt: str
    confidence: int

    model_config = {"from_attributes": True}


class ReviewOut(BaseModel):
    is_read: bool
    interest: str | None
    remind_at: dt.date | None
    notes: str | None

    model_config = {"from_attributes": True}


class ReviewUpdate(BaseModel):
    is_read: bool | None = None
    interest: str | None = None
    remind_at: dt.date | None = None
    notes: str | None = None
    eligibility_override: str | None = None
    sales_color_override: str | None = None


class OpportunitySummary(BaseModel):
    id: int
    title: str
    organizer_name: str | None
    municipality: str | None
    status: str
    application_end: dt.date | None
    total_budget_cents: int | None
    sales_color: str | None
    eligibility_verdict: str | None
    next_action: str | None
    is_read: bool
    first_seen_at: dt.datetime


class OpportunityDetail(BaseModel):
    id: int
    title: str
    organizer_name: str | None
    grantee_or_implementer_name: str | None
    municipality: str | None
    region: str | None
    topics: list[str]
    target_groups: list[str]
    summary: str | None
    published_at: dt.date | None
    application_start: dt.date | None
    application_end: dt.date | None
    application_end_raw: str | None
    activity_start: dt.date | None
    activity_end: dt.date | None
    total_budget_cents: int | None
    total_budget_raw: str | None
    max_grant_cents: int | None
    status: str
    nuance_notes: str | None
    next_action: str | None
    call_script: str | None
    primary_url: str
    source_urls: list[str]
    document_urls: list[str]
    first_seen_at: dt.datetime
    last_changed_at: dt.datetime
    last_checked_at: dt.datetime
    possible_duplicate_of_id: int | None

    eligibility: EligibilityOut | None
    sales: SalesOut | None
    contacts: list[ContactOut]
    evidences: list[EvidenceOut]
    change_events: list[ChangeEventOut]
    review: ReviewOut | None
