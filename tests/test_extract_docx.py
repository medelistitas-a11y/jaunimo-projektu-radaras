from pathlib import Path

from app.extraction.docx_extract import extract_docx_text

FIXTURES = Path(__file__).parent / "fixtures"


def test_docx_text_extracted():
    result = extract_docx_text(FIXTURES / "sample.docx")
    assert result.success is True
    assert result.method == "python-docx"
    assert "Tinkamumo salygos" in result.text or "SINTETINIS" in result.text


def test_docx_extraction_failure_is_explicit():
    result = extract_docx_text(FIXTURES / "sample.pdf")  # netinkamas failo tipas
    assert result.success is False
    assert result.method == "failed"
