from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.assessment import Notification
from app.models.opportunity import Opportunity
from app.models.source import CrawlRun, Source
from app.web.queries import apply_filters, base_query

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    query = apply_filters(
        base_query(db),
        color=request.query_params.get("color") or None,
        municipality=request.query_params.get("municipality") or None,
        status=request.query_params.get("status") or None,
        eligibility=request.query_params.get("eligibility") or None,
        only_with_contacts=request.query_params.get("only_with_contacts") == "1",
        only_new=request.query_params.get("only_new") == "1",
        only_unread=request.query_params.get("only_unread") == "1",
        search=request.query_params.get("q") or None,
    )
    opportunities = query.order_by(Opportunity.first_seen_at.desc()).limit(300).all()

    today = dt.date.today()
    week = today + dt.timedelta(days=7)
    stats = {
        "new_green": sum(
            1
            for o in opportunities
            if o.sales
            and o.sales.color == "green"
            and o.first_seen_at.date() >= today - dt.timedelta(days=2)
        ),
        "new_yellow": sum(
            1
            for o in opportunities
            if o.sales
            and o.sales.color == "yellow"
            and o.first_seen_at.date() >= today - dt.timedelta(days=2)
        ),
        "deadlines_soon": sum(
            1 for o in opportunities if o.application_end and today <= o.application_end <= week
        ),
        "source_errors": db.query(Source).filter(Source.last_status == "error").count(),
        "last_check": db.query(CrawlRun).order_by(CrawlRun.started_at.desc()).first(),
    }
    municipalities = [m[0] for m in db.query(Opportunity.municipality).distinct().all() if m[0]]

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "opportunities": opportunities,
            "stats": stats,
            "municipalities": sorted(municipalities),
            "filters": dict(request.query_params),
        },
    )


@router.get("/galimybe/{opportunity_id}", response_class=HTMLResponse)
def opportunity_detail(request: Request, opportunity_id: int, db: Session = Depends(get_db)):
    opp = base_query(db).filter(Opportunity.id == opportunity_id).one_or_none()
    return templates.TemplateResponse("detail.html", {"request": request, "opp": opp})


@router.get("/saltiniai", response_class=HTMLResponse)
def sources_page(request: Request, db: Session = Depends(get_db)):
    sources = db.query(Source).order_by(Source.municipality.is_(None), Source.name).all()
    total = len(sources)
    active = sum(1 for s in sources if s.status == "active")
    return templates.TemplateResponse(
        "sources.html",
        {"request": request, "sources": sources, "total": total, "active": active},
    )


@router.get("/pranesimai", response_class=HTMLResponse)
def notifications_page(request: Request, db: Session = Depends(get_db)):
    notifications = db.query(Notification).order_by(Notification.created_at.desc()).limit(100).all()
    return templates.TemplateResponse(
        "notifications.html", {"request": request, "notifications": notifications}
    )
