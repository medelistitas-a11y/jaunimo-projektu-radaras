from __future__ import annotations

import datetime as dt

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session, joinedload

from app.models.assessment import EligibilityAssessment, SalesAssessment
from app.models.opportunity import Opportunity, UserReview
from app.models.organization import Contact


def base_query(db: Session) -> Query:
    return db.query(Opportunity).options(
        joinedload(Opportunity.eligibility),
        joinedload(Opportunity.sales),
        joinedload(Opportunity.review),
        joinedload(Opportunity.contacts),
    )


def apply_filters(
    query: Query,
    color: str | None = None,
    municipality: str | None = None,
    topic: str | None = None,
    status: str | None = None,
    eligibility: str | None = None,
    deadline_before: dt.date | None = None,
    budget_min_cents: int | None = None,
    budget_max_cents: int | None = None,
    only_with_contacts: bool = False,
    only_new: bool = False,
    only_unread: bool = False,
    search: str | None = None,
) -> Query:
    if color:
        query = query.join(SalesAssessment).filter(SalesAssessment.color == color)
    if municipality:
        query = query.filter(Opportunity.municipality == municipality)
    if status:
        query = query.filter(Opportunity.status == status)
    if eligibility:
        # Visada JOIN'inti EligibilityAssessment čia, nepriklausomai nuo to, ar `color`
        # jau prijungė SalesAssessment — tai skirtinga lentelė. Anksčiau čia buvo klaidinga
        # sąlyga, praleisdavusi JOIN, kai `color` nustatytas, o tai sukeldavo Dekarto
        # sandaugą (SQLAlchemy SAWarning) tarp Opportunity ir EligibilityAssessment bei
        # galimai neteisingus rezultatus, kai DB turi kelis įrašus.
        query = query.join(EligibilityAssessment).filter(
            EligibilityAssessment.verdict == eligibility
        )
    if deadline_before:
        query = query.filter(
            Opportunity.application_end.is_not(None),
            Opportunity.application_end <= deadline_before,
        )
    if budget_min_cents is not None:
        query = query.filter(Opportunity.total_budget_cents >= budget_min_cents)
    if budget_max_cents is not None:
        query = query.filter(Opportunity.total_budget_cents <= budget_max_cents)
    if only_with_contacts:
        query = query.join(Contact, Contact.opportunity_id == Opportunity.id)
    if only_new:
        recent = dt.datetime.now(dt.UTC) - dt.timedelta(days=2)
        query = query.filter(Opportunity.first_seen_at >= recent)
    if only_unread:
        query = query.outerjoin(UserReview).filter(
            or_(UserReview.is_read.is_(False), UserReview.id.is_(None))
        )
    # Pastaba: `topic` filtras taikomas Python lygyje po užklausos (app/web/routes_api.py),
    # nes JSON masyvo "contains" elgesys nevienodas tarp SQLite (testams) ir PostgreSQL.
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Opportunity.title.ilike(like),
                Opportunity.summary.ilike(like),
                Opportunity.organizer_name.ilike(like),
            )
        )
    return query
