import datetime as dt

from app.models.assessment import Notification, SalesAssessment
from app.models.opportunity import Opportunity
from app.models.source import CrawlRun
from app.notify.center import generate_notifications_for_run
from app.notify.email_digest import build_digest_text, send_daily_digest


def _make_run(db, started_at) -> CrawlRun:
    run = CrawlRun(
        started_at=started_at,
        finished_at=started_at + dt.timedelta(minutes=5),
        trigger="manual",
        scope="all",
        status="completed",
    )
    db.add(run)
    db.flush()
    return run


def _make_opportunity(db, first_seen_at, application_end=None) -> Opportunity:
    opp = Opportunity(
        title="Testinė galimybė",
        status="open",
        topics=[],
        target_groups=[],
        primary_url="https://x.lt/1",
        source_urls=["https://x.lt/1"],
        document_urls=[],
        canonical_key="k1",
        content_hash="h1",
        first_seen_at=first_seen_at,
        last_changed_at=first_seen_at,
        last_checked_at=first_seen_at,
        application_end=application_end,
    )
    db.add(opp)
    db.flush()
    return opp


def test_new_green_opportunity_creates_notification(db_session):
    now = dt.datetime.now(dt.UTC)
    run = _make_run(db_session, now - dt.timedelta(minutes=1))
    opp = _make_opportunity(db_session, first_seen_at=now)
    db_session.add(
        SalesAssessment(
            opportunity_id=opp.id,
            color="green",
            reason_code="x",
            explanation_lt="Paaiškinimas",
            confidence=80,
            signals=[],
            assessed_by="rules",
            assessed_at=now,
        )
    )
    db_session.commit()

    count = generate_notifications_for_run(db_session, run)
    assert count == 1
    notif = db_session.query(Notification).one()
    assert notif.kind == "new_green"
    assert notif.opportunity_id == opp.id


def test_generate_notifications_is_deduplicated(db_session):
    now = dt.datetime.now(dt.UTC)
    run = _make_run(db_session, now - dt.timedelta(minutes=1))
    opp = _make_opportunity(db_session, first_seen_at=now)
    db_session.add(
        SalesAssessment(
            opportunity_id=opp.id,
            color="green",
            reason_code="x",
            explanation_lt="Paaiškinimas",
            confidence=80,
            signals=[],
            assessed_by="rules",
            assessed_at=now,
        )
    )
    db_session.commit()

    generate_notifications_for_run(db_session, run)
    generate_notifications_for_run(db_session, run)  # tas pats run, dar kartą
    assert db_session.query(Notification).count() == 1


def test_deadline_within_7_days_creates_notification(db_session):
    now = dt.datetime.now(dt.UTC)
    run = _make_run(db_session, now - dt.timedelta(minutes=1))
    # first_seen_at senas, kad nebūtų "new_green" - testuojame tik terminą.
    old_seen = now - dt.timedelta(days=30)
    _make_opportunity(
        db_session,
        first_seen_at=old_seen,
        application_end=(now + dt.timedelta(days=3)).date(),
    )
    db_session.commit()

    generate_notifications_for_run(db_session, run)
    kinds = [n.kind for n in db_session.query(Notification).all()]
    assert "deadline_soon" in kinds


def test_no_changes_creates_no_notifications(db_session):
    now = dt.datetime.now(dt.UTC)
    run = _make_run(db_session, now - dt.timedelta(minutes=1))
    db_session.commit()
    count = generate_notifications_for_run(db_session, run)
    assert count == 0


def test_build_digest_text_empty_and_nonempty():
    assert build_digest_text([]) == "Naujų pranešimų nėra."
    n = Notification(kind="new_green", title="T", body="B", dedup_key="d1", opportunity_id=None)
    text = build_digest_text([n])
    assert "T" in text and "B" in text


def test_send_daily_digest_noop_when_smtp_not_configured(db_session, test_settings):
    assert test_settings.smtp_configured is False
    sent = send_daily_digest(db_session, test_settings)
    assert sent is False
