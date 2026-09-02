from app.crawler.dedupe import canonicalize_url, find_fuzzy_duplicate
from app.crawler.pipeline import process_candidate
from app.models.assessment import ChangeEvent
from app.models.opportunity import Opportunity
from app.models.source import Source

SAMPLE_TEXT = (
    "Skelbiamas jaunimo darbuotojų mokymų konkursas. Paraiškas gali teikti visi "
    "juridiniai asmenys, neatsižvelgiant į teisinę formą. Finansavimas iki 10 000 Eur. "
    "Paraiškos priimamos iki rugsėjo 30 d. Kontaktai: tel. 8 686 12345, "
    "el. paštas info@testine.lt"
)


def _source() -> Source:
    return Source(
        code="test_source",
        name="Testinis šaltinis",
        institution_name="Testinė institucija",
        municipality="Testinė sav.",
        official_domain="testine.lt",
        start_urls=["https://testine.lt/"],
        source_type="html",
        adapter="generic_html",
        status="active",
        enabled=True,
    )


def test_canonicalize_url_strips_tracking_and_trailing_slash():
    a = canonicalize_url("https://www.testine.lt/naujiena/x/?utm_source=fb")
    b = canonicalize_url("https://testine.lt/naujiena/x")
    assert a == b


def test_same_url_does_not_create_duplicate_opportunity(db_session):
    source = _source()
    db_session.add(source)
    db_session.commit()

    r1 = process_candidate(
        db_session, source, "Mokymų konkursas", "https://testine.lt/naujiena/1", SAMPLE_TEXT, []
    )
    db_session.commit()
    assert r1.is_new is True

    r2 = process_candidate(
        db_session, source, "Mokymų konkursas", "https://testine.lt/naujiena/1", SAMPLE_TEXT, []
    )
    db_session.commit()
    assert r2.is_new is False
    assert r2.is_updated is False  # turinys nepasikeitė
    assert db_session.query(Opportunity).count() == 1


def test_unchanged_content_does_not_add_change_event(db_session):
    source = _source()
    db_session.add(source)
    db_session.commit()

    process_candidate(
        db_session, source, "Mokymų konkursas", "https://testine.lt/naujiena/2", SAMPLE_TEXT, []
    )
    db_session.commit()
    events_after_first = db_session.query(ChangeEvent).count()

    process_candidate(
        db_session, source, "Mokymų konkursas", "https://testine.lt/naujiena/2", SAMPLE_TEXT, []
    )
    db_session.commit()
    events_after_second = db_session.query(ChangeEvent).count()

    assert events_after_first == events_after_second == 1  # tik "created" įvykis


def test_changed_content_creates_change_event_and_history(db_session):
    source = _source()
    db_session.add(source)
    db_session.commit()

    process_candidate(
        db_session, source, "Mokymų konkursas", "https://testine.lt/naujiena/3", SAMPLE_TEXT, []
    )
    db_session.commit()

    changed_text = SAMPLE_TEXT + " Papildyta: registracija privaloma iš anksto."
    r2 = process_candidate(
        db_session, source, "Mokymų konkursas", "https://testine.lt/naujiena/3", changed_text, []
    )
    db_session.commit()

    assert r2.is_updated is True
    change_types = [
        e.event_type for e in db_session.query(ChangeEvent).order_by(ChangeEvent.id).all()
    ]
    assert "created" in change_types
    assert "content_changed" in change_types


def test_fuzzy_duplicate_is_flagged_not_auto_merged(db_session):
    source = _source()
    db_session.add(source)
    db_session.commit()

    process_candidate(
        db_session,
        source,
        "Jaunimo darbuotojų kompetencijų stiprinimo mokymų konkursas 2026",
        "https://testine.lt/a/originalas",
        SAMPLE_TEXT,
        [],
    )
    db_session.commit()

    r2 = process_candidate(
        db_session,
        source,
        "Jaunimo darbuotojų kompetencijų stiprinimo mokymų konkursas, 2026 m.",
        "https://testine.lt/b/kita-nuoroda-tas-pats-konkursas",
        SAMPLE_TEXT,
        [],
    )
    db_session.commit()

    assert db_session.query(Opportunity).count() == 2
    assert r2.opportunity.possible_duplicate_of_id is not None


def test_find_fuzzy_duplicate_respects_threshold(db_session):
    source = _source()
    db_session.add(source)
    db_session.commit()
    process_candidate(
        db_session,
        source,
        "Visai kitas renginys apie sportą",
        "https://testine.lt/sportas",
        SAMPLE_TEXT,
        [],
    )
    db_session.commit()

    match = find_fuzzy_duplicate(db_session, "Jaunimo mokymų konkursas", "Testinė sav.")
    assert match is None
