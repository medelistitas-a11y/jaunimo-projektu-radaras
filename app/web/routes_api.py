from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.crawler.runner import run_crawl
from app.db import get_db
from app.models.assessment import Notification
from app.models.opportunity import Opportunity, UserReview
from app.models.source import CrawlRun, Source
from app.notify.center import generate_notifications_for_run
from app.schemas.opportunity import OpportunityDetail, OpportunitySummary, ReviewUpdate
from app.web.auth import require_admin
from app.web.csv_export import opportunities_to_csv
from app.web.queries import apply_filters, base_query

router = APIRouter(prefix="/api")


def _to_summary(opp: Opportunity) -> OpportunitySummary:
    return OpportunitySummary(
        id=opp.id,
        title=opp.title,
        organizer_name=opp.organizer_name,
        municipality=opp.municipality,
        status=opp.status,
        application_end=opp.application_end,
        total_budget_cents=opp.total_budget_cents,
        sales_color=opp.sales.color if opp.sales else None,
        eligibility_verdict=opp.eligibility.verdict if opp.eligibility else None,
        next_action=opp.next_action,
        is_read=bool(opp.review and opp.review.is_read),
        first_seen_at=opp.first_seen_at,
    )


@router.get("/opportunities")
def list_opportunities(
    color: str | None = None,
    municipality: str | None = None,
    topic: str | None = None,
    status: str | None = None,
    eligibility: str | None = None,
    deadline_before: dt.date | None = None,
    budget_min: int | None = None,
    budget_max: int | None = None,
    only_with_contacts: bool = False,
    only_new: bool = False,
    only_unread: bool = False,
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> list[OpportunitySummary]:
    query = apply_filters(
        base_query(db),
        color=color,
        municipality=municipality,
        topic=topic,
        status=status,
        eligibility=eligibility,
        deadline_before=deadline_before,
        budget_min_cents=budget_min * 100 if budget_min else None,
        budget_max_cents=budget_max * 100 if budget_max else None,
        only_with_contacts=only_with_contacts,
        only_new=only_new,
        only_unread=only_unread,
        search=q,
    )
    results = query.order_by(Opportunity.first_seen_at.desc()).all()
    if topic:
        results = [o for o in results if topic in (o.topics or [])]
    return [_to_summary(o) for o in results[offset : offset + limit]]


@router.get("/opportunities/{opportunity_id}", response_model=OpportunityDetail)
def get_opportunity(opportunity_id: int, db: Session = Depends(get_db)) -> Opportunity:
    opp = base_query(db).filter(Opportunity.id == opportunity_id).one_or_none()
    if opp is None:
        raise HTTPException(status_code=404, detail="Galimybė nerasta")
    return opp


@router.patch("/opportunities/{opportunity_id}/review")
def update_review(
    opportunity_id: int,
    payload: ReviewUpdate,
    db: Session = Depends(get_db),
    _admin: str = Depends(require_admin),
) -> dict:
    opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id).one_or_none()
    if opp is None:
        raise HTTPException(status_code=404, detail="Galimybė nerasta")

    review = opp.review
    if review is None:
        review = UserReview(opportunity_id=opp.id)
        db.add(review)

    for field in ("is_read", "interest", "remind_at", "notes"):
        value = getattr(payload, field)
        if value is not None:
            setattr(review, field, value)

    if payload.eligibility_override is not None and opp.eligibility:
        opp.eligibility.verdict = payload.eligibility_override
        opp.eligibility.assessed_by = "human"
    if payload.sales_color_override is not None and opp.sales:
        opp.sales.color = payload.sales_color_override
        opp.sales.assessed_by = "human"

    db.commit()
    return {"ok": True}


@router.get("/export.csv")
def export_csv(
    color: str | None = None,
    municipality: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
) -> Response:
    query = apply_filters(base_query(db), color=color, municipality=municipality, status=status)
    opportunities = query.order_by(Opportunity.first_seen_at.desc()).all()
    csv_bytes = opportunities_to_csv(opportunities)
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=galimybes.csv"},
    )


@router.get("/sources")
def list_sources(db: Session = Depends(get_db)) -> dict:
    sources = db.query(Source).order_by(Source.municipality.is_(None), Source.name).all()
    total = len(sources)
    accessible = sum(1 for s in sources if s.status == "active")
    blocked = sum(1 for s in sources if s.status == "blocked_bot_protection")
    needs_verification = sum(1 for s in sources if s.status == "needs_verification")
    return {
        "summary": {
            "total": total,
            "active": accessible,
            "blocked_bot_protection": blocked,
            "needs_verification": needs_verification,
            "label": f"sėkmingai patikrinta {accessible}/{total}",
        },
        "sources": [
            {
                "id": s.id,
                "code": s.code,
                "name": s.name,
                "municipality": s.municipality,
                "official_domain": s.official_domain,
                "status": s.status,
                "adapter": s.adapter,
                "enabled": s.enabled,
                "last_checked_at": s.last_checked_at,
                "last_status": s.last_status,
                "last_error": s.last_error,
                "notes": s.notes,
                "start_urls": s.start_urls,
            }
            for s in sources
        ],
    }


@router.post("/sources/{code}/check")
def check_single_source(
    code: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _admin: str = Depends(require_admin),
) -> dict:
    running = db.query(CrawlRun).filter(CrawlRun.status == "running").first()
    if running is not None:
        raise HTTPException(status_code=409, detail="Kitas tikrinimas jau vyksta")
    source = db.query(Source).filter(Source.code == code).one_or_none()
    if source is None:
        raise HTTPException(status_code=404, detail="Šaltinis nerastas")
    run = run_crawl(db, settings, trigger="manual", only_source_code=code)
    generate_notifications_for_run(db, run)
    return {"run_id": run.id, "status": run.status}


@router.post("/crawl/run")
def trigger_crawl(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _admin: str = Depends(require_admin),
) -> dict:
    running = db.query(CrawlRun).filter(CrawlRun.status == "running").first()
    if running is not None:
        raise HTTPException(
            status_code=409, detail="Tikrinimas jau vyksta — palaukite, kol baigsis."
        )
    run = run_crawl(db, settings, trigger="manual")
    generate_notifications_for_run(db, run)
    return {"run_id": run.id, "status": run.status, "new": run.new_opportunities}


@router.get("/crawl/status")
def crawl_status(db: Session = Depends(get_db)) -> dict:
    latest = db.query(CrawlRun).order_by(CrawlRun.started_at.desc()).first()
    if latest is None:
        return {"status": "never_run"}
    return {
        "id": latest.id,
        "status": latest.status,
        "started_at": latest.started_at,
        "finished_at": latest.finished_at,
        "sources_total": latest.sources_total,
        "sources_ok": latest.sources_ok,
        "sources_error": latest.sources_error,
        "sources_blocked": latest.sources_blocked,
        "new_opportunities": latest.new_opportunities,
        "updated_opportunities": latest.updated_opportunities,
    }


@router.get("/notifications")
def list_notifications(unread_only: bool = False, db: Session = Depends(get_db)) -> list[dict]:
    query = db.query(Notification).order_by(Notification.created_at.desc())
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    return [
        {
            "id": n.id,
            "kind": n.kind,
            "title": n.title,
            "body": n.body,
            "opportunity_id": n.opportunity_id,
            "is_read": n.is_read,
            "created_at": n.created_at,
        }
        for n in query.limit(200).all()
    ]


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, db: Session = Depends(get_db)) -> dict:
    n = db.query(Notification).filter(Notification.id == notification_id).one_or_none()
    if n is None:
        raise HTTPException(status_code=404, detail="Pranešimas nerastas")
    n.is_read = True
    db.commit()
    return {"ok": True}
