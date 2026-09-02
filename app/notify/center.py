"""Pranešimų centras: generuoja in-app Notification įrašus po CrawlRun.

Rodomos tik: naujos žalios galimybės, reikšmingai pasikeitusios žalios/geltonos
galimybės, terminai per artimiausias 7 dienas, kritinės šaltinių klaidos.
Dedup raktas užtikrina, kad tas pats pranešimas nebūtų sukurtas du kartus.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from app.models.assessment import ChangeEvent, Notification
from app.models.opportunity import Opportunity
from app.models.source import CrawlRun, SourceCheckResult


def _add_if_new(db: Session, **kwargs) -> None:
    existing = db.query(Notification).filter_by(dedup_key=kwargs["dedup_key"]).one_or_none()
    if existing is None:
        db.add(Notification(**kwargs))


def generate_notifications_for_run(db: Session, run: CrawlRun) -> int:
    count_before = db.query(Notification).count()
    now = dt.datetime.now(dt.UTC)

    changed_since = run.started_at

    new_green = db.query(Opportunity).filter(Opportunity.first_seen_at >= changed_since).all()
    for opp in new_green:
        if opp.sales and opp.sales.color == "green":
            _add_if_new(
                db,
                kind="new_green",
                title=f"Nauja žalia galimybė: {opp.title}",
                body=opp.sales.explanation_lt,
                opportunity_id=opp.id,
                dedup_key=f"new_green:{opp.id}",
            )

    changed_events = (
        db.query(ChangeEvent)
        .filter(
            ChangeEvent.event_type == "assessment_changed",
            ChangeEvent.occurred_at >= changed_since,
        )
        .all()
    )
    for event in changed_events:
        new_color = (event.diff or {}).get("new_color")
        if new_color in ("green", "yellow"):
            _add_if_new(
                db,
                kind="changed_green_yellow",
                title=f"Pasikeitė vertinimas: {event.opportunity.title}",
                body=event.description,
                opportunity_id=event.opportunity_id,
                dedup_key=f"changed:{event.id}",
            )

    week_from_now = now.date() + dt.timedelta(days=7)
    upcoming = (
        db.query(Opportunity)
        .filter(
            Opportunity.application_end.is_not(None),
            Opportunity.application_end >= now.date(),
            Opportunity.application_end <= week_from_now,
        )
        .all()
    )
    for opp in upcoming:
        _add_if_new(
            db,
            kind="deadline_soon",
            title=f"Terminas artėja: {opp.title}",
            body=f"Paraiškų terminas: {opp.application_end.isoformat()}.",
            opportunity_id=opp.id,
            dedup_key=f"deadline:{opp.id}:{opp.application_end.isoformat()}",
        )

    error_checks = (
        db.query(SourceCheckResult)
        .filter(SourceCheckResult.crawl_run_id == run.id, SourceCheckResult.status == "error")
        .all()
    )
    for check in error_checks:
        _add_if_new(
            db,
            kind="source_error",
            title=f"Šaltinio klaida: {check.source.name}",
            body=check.error_message or "Nenurodyta klaidos priežastis.",
            opportunity_id=None,
            dedup_key=f"source_error:{check.source_id}:{run.id}",
        )

    db.commit()
    return db.query(Notification).count() - count_before
