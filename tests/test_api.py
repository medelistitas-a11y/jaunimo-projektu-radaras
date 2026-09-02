import datetime as dt

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import *  # noqa: F401,F403
from app.models.assessment import EligibilityAssessment, SalesAssessment
from app.models.opportunity import Opportunity


@pytest.fixture()
def client(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    from app import db as db_module

    monkeypatch.setattr(db_module, "SessionLocal", TestSession)

    session = TestSession()
    now = dt.datetime.now(dt.UTC)
    opp = Opportunity(
        title="Testinė galimybė API testui",
        organizer_name="Testinė institucija",
        municipality="Testinė sav.",
        topics=["jaunim", "mokym"],
        target_groups=[],
        status="open",
        application_end=dt.date(2026, 12, 1),
        total_budget_cents=500000,
        primary_url="https://testine.lt/a",
        source_urls=["https://testine.lt/a"],
        document_urls=[],
        canonical_key="testine::api-testui",
        content_hash="abc123",
        first_seen_at=now,
        last_changed_at=now,
        last_checked_at=now,
    )
    session.add(opp)
    session.flush()
    session.add(
        EligibilityAssessment(
            opportunity_id=opp.id,
            verdict="taip",
            explanation_lt="Testinis paaiškinimas.",
            confidence=80,
            assessed_by="rules",
            assessed_at=now,
        )
    )
    session.add(
        SalesAssessment(
            opportunity_id=opp.id,
            color="green",
            reason_code="concrete_opportunity_with_contact",
            explanation_lt="Testinis pardavimo paaiškinimas.",
            confidence=80,
            signals=[],
            assessed_by="rules",
            assessed_at=now,
        )
    )
    session.commit()
    session.close()

    from app.main import app

    def override_get_db():
        s = TestSession()
        try:
            yield s
        finally:
            s.close()

    from app.db import get_db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def test_dashboard_renders(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Testinė galimybė API testui" in resp.text


def test_list_opportunities_api(client):
    resp = client.get("/api/opportunities")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["sales_color"] == "green"
    assert data[0]["eligibility_verdict"] == "taip"


def test_filter_by_color(client):
    resp = client.get("/api/opportunities?color=green")
    assert len(resp.json()) == 1
    resp = client.get("/api/opportunities?color=red")
    assert len(resp.json()) == 0


def test_opportunity_detail_api(client):
    resp = client.get("/api/opportunities")
    opp_id = resp.json()[0]["id"]
    detail = client.get(f"/api/opportunities/{opp_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["title"] == "Testinė galimybė API testui"
    assert body["eligibility"]["verdict"] == "taip"


def test_opportunity_detail_page_renders(client):
    resp = client.get("/api/opportunities")
    opp_id = resp.json()[0]["id"]
    page = client.get(f"/galimybe/{opp_id}")
    assert page.status_code == 200
    assert "Ar MB gali teikti para" in page.text  # "Ar MB gali teikti paraišką"


def test_sources_page_renders(client):
    resp = client.get("/saltiniai")
    assert resp.status_code == 200


def test_csv_export_has_bom_and_row(client):
    resp = client.get("/api/export.csv")
    assert resp.status_code == 200
    assert resp.content.startswith(b"\xef\xbb\xbf")
    text = resp.content.decode("utf-8-sig")
    assert "Testinė galimybė API testui" in text


def test_review_update_requires_no_auth_when_unconfigured(client):
    resp = client.get("/api/opportunities")
    opp_id = resp.json()[0]["id"]
    patch = client.patch(
        f"/api/opportunities/{opp_id}/review", json={"interest": "interested", "is_read": True}
    )
    assert patch.status_code == 200

    detail = client.get(f"/api/opportunities/{opp_id}").json()
    assert detail["review"]["interest"] == "interested"
    assert detail["review"]["is_read"] is True
