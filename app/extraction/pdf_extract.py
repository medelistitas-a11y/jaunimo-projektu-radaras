"""PDF teksto ištraukimas. Tekstiniams PDF naudoja pdfplumber (tikslesnis
išdėstymas) su pypdf kaip atsarginiu variantu. Nuskenuotiems (be teksto
sluoksnio) PDF tekstas negrąžinamas — kviečiančioji pusė turi nuspręsti, ar
kreiptis į app.extraction.ocr, ar pažymėti needs_human_review.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

MIN_CHARS_FOR_TEXT_LAYER = 20


@dataclass
class PdfExtractionResult:
    text: str
    method: str  # "pdfplumber" | "pypdf" | "none"
    has_text_layer: bool
    page_count: int


def extract_pdf_text(path: str | Path) -> PdfExtractionResult:
    path = Path(path)
    text = ""
    page_count = 0
    method = "none"

    try:
        import pdfplumber

        with pdfplumber.open(path) as pdf:
            page_count = len(pdf.pages)
            parts = [page.extract_text() or "" for page in pdf.pages]
            text = "\n\n".join(p for p in parts if p)
            if text.strip():
                method = "pdfplumber"
    except Exception:
        text = ""

    if len(text.strip()) < MIN_CHARS_FOR_TEXT_LAYER:
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            page_count = len(reader.pages)
            parts = [page.extract_text() or "" for page in reader.pages]
            fallback_text = "\n\n".join(p for p in parts if p)
            if len(fallback_text.strip()) > len(text.strip()):
                text = fallback_text
                method = "pypdf"
        except Exception:
            pass

    has_text_layer = len(text.strip()) >= MIN_CHARS_FOR_TEXT_LAYER
    if not has_text_layer:
        method = "none"

    return PdfExtractionResult(
        text=text.strip(), method=method, has_text_layer=has_text_layer, page_count=page_count
    )
