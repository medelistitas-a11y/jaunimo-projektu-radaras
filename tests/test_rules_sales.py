import datetime as dt
from pathlib import Path

from app.extraction.html_extract import extract_page
from app.rules.eligibility import assess_eligibility
from app.rules.sales import assess_sales

FIXTURES = Path(__file__).parent / "fixtures"


def _text_from_fixture(name: str) -> str:
    html = (FIXTURES / name).read_text(encoding="utf-8")
    return extract_page(html, base_url="https://testine-savivaldybe.lt/").text


def test_mb_cannot_apply_but_vendor_opportunity_is_not_red():
    """Kritinis kraštinis atvejis iš instrukcijų: eligibility == "ne" savaime
    NIEKADA neturi paversti pardavimo vertinimo raudonu.
    """
    text = _text_from_fixture("vsi_only_call.html")
    elig = assess_eligibility(text, source_url="https://x.lt")
    assert elig.verdict == "ne"

    result = assess_sales(
        text=text,
        eligibility_verdict=elig.verdict,
        application_end=dt.date(2026, 10, 10),
        activity_end=None,
        has_contact=True,
        has_training_budget=True,
        today=dt.date(2026, 9, 2),
    )
    assert result.color != "red"
    assert result.color in ("green", "yellow")


def test_deadline_passed_and_irrelevant_is_red():
    text = _text_from_fixture("expired_irrelevant.html")
    result = assess_sales(
        text=text,
        eligibility_verdict="neaisku",
        application_end=dt.date(2020, 5, 1),
        activity_end=dt.date(2020, 6, 1),
        has_contact=False,
        has_training_budget=False,
        today=dt.date(2026, 9, 2),
    )
    assert result.color == "red"


def test_concrete_opportunity_with_contact_is_green():
    text = _text_from_fixture("detail_page.html")
    result = assess_sales(
        text=text,
        eligibility_verdict="taip",
        application_end=dt.date(2026, 9, 20),
        activity_end=None,
        has_contact=True,
        has_training_budget=True,
        today=dt.date(2026, 9, 2),
    )
    assert result.color == "green"
    assert result.reason_code == "concrete_opportunity_with_contact"


def test_needs_procurement_is_yellow():
    text = (
        "Skelbiamas jaunimo mokymų paslaugų pirkimas viešojo pirkimo būdu (CVP IS). "
        "Reikalingi emocijų reguliavimo mokymai jaunimo darbuotojams."
    )
    result = assess_sales(
        text=text,
        eligibility_verdict="taip",
        application_end=dt.date(2026, 12, 1),
        activity_end=None,
        has_contact=False,
        has_training_budget=True,
        today=dt.date(2026, 9, 2),
    )
    assert result.color == "yellow"
    assert result.reason_code == "needs_procurement"


def test_not_relevant_content_is_red():
    result = assess_sales(
        text="Informuojame apie artėjantį miesto šventės renginį ir eismo ribojimus.",
        eligibility_verdict="neaisku",
        application_end=None,
        activity_end=None,
        has_contact=False,
        has_training_budget=False,
        today=dt.date(2026, 9, 2),
    )
    assert result.color == "red"
    assert result.reason_code == "not_relevant"


def test_green_requires_no_future_deadline_passed():
    text = _text_from_fixture("detail_page.html")
    result = assess_sales(
        text=text,
        eligibility_verdict="taip",
        application_end=dt.date(2020, 1, 1),
        activity_end=dt.date(2020, 2, 1),
        has_contact=True,
        has_training_budget=True,
        today=dt.date(2026, 9, 2),
    )
    assert result.color == "red"
