from pathlib import Path

from app.extraction.pdf_extract import extract_pdf_text

FIXTURES = Path(__file__).parent / "fixtures"


def test_text_pdf_extracted():
    result = extract_pdf_text(FIXTURES / "sample.pdf")
    assert result.has_text_layer is True
    assert "Konkurso pavadinimas" in result.text
    assert result.method in ("pdfplumber", "pypdf")


def test_scanned_pdf_has_no_text_layer():
    result = extract_pdf_text(FIXTURES / "scanned_no_text.pdf")
    assert result.has_text_layer is False
    assert result.text == ""
    assert result.method == "none"
