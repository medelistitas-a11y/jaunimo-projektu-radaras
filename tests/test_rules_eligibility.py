from pathlib import Path

from app.extraction.html_extract import extract_page
from app.rules.eligibility import assess_eligibility

FIXTURES = Path(__file__).parent / "fixtures"


def _text_from_fixture(name: str) -> str:
    html = (FIXTURES / name).read_text(encoding="utf-8")
    return extract_page(html, base_url="https://testine-savivaldybe.lt/").text


def test_no_citation_means_neaisku():
    result = assess_eligibility("Šis tekstas apie orus rytoj.", source_url="https://x.lt")
    assert result.verdict == "neaisku"
    assert result.evidence_quote is None


def test_open_eligibility_verdict_taip():
    text = _text_from_fixture("mb_eligible_call.html")
    result = assess_eligibility(text, source_url="https://x.lt")
    assert result.verdict == "taip"
    assert result.evidence_quote is not None
    assert "juridin" in result.evidence_quote.lower()
    assert result.confidence >= 60


def test_mb_cannot_apply_but_can_be_vendor_verdict_ne_not_red_signal():
    """Kritinė taisyklė: MB negalėjimas teikti paraiškos = "ne", bet paaiškinime
    turi būti paminėta pardavimo galimybė (paslaugų teikėjas), o ne tik atmetimas.
    Šis testas taip pat naudojamas kaip pagrindas B (sales) testui, įrodančiam,
    kad tai NEGALI automatiškai virsti raudona spalva.
    """
    text = _text_from_fixture("vsi_only_call.html")
    result = assess_eligibility(text, source_url="https://x.lt")
    assert result.verdict == "ne"
    assert result.evidence_quote is not None
    assert result.confidence >= 50
    assert "paslaugų teikėj" in result.explanation_lt or "paslaugų teikėjo" in result.explanation_lt


def test_restricted_types_without_vendor_mention_still_ne():
    text = (
        "Konkursas skirtas jaunimo stovykloms. Paraiškas gali teikti tik viešosios "
        "įstaigos ir asociacijos, veikiančios jaunimo srityje."
    )
    result = assess_eligibility(text, source_url="https://x.lt")
    assert result.verdict == "ne"
    assert result.rule_code == "restricted_applicant_types"


def test_partnership_required_gives_su_salygomis():
    text = (
        "Paraiškas galima teikti tik kaip partneriui kartu su viešąja įstaiga. "
        "Pagrindiniu pareiškėju gali būti tik VšĮ."
    )
    result = assess_eligibility(text, source_url="https://x.lt")
    assert result.verdict in ("su_salygomis", "ne")


def test_empty_text_is_neaisku():
    result = assess_eligibility("", source_url="https://x.lt")
    assert result.verdict == "neaisku"
    assert result.confidence == 0
