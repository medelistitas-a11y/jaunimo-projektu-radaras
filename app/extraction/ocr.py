"""OCR nuskenuotiems PDF be teksto sluoksnio (OCRmyPDF + Tesseract, lit+eng).

Jei OCRmyPDF/Tesseract nepasiekiami aplinkoje (pvz. lokaliame dev be Docker),
grąžinamas aiškus success=False rezultatas — niekas neišgalvojama, dokumentas
turi būti pažymėtas needs_human_review kviečiančiojoje pusėje.
"""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.extraction.pdf_extract import extract_pdf_text


@dataclass
class OcrResult:
    text: str
    success: bool
    error: str | None = None


def ocr_available() -> bool:
    try:
        import ocrmypdf  # noqa: F401

        return True
    except ImportError:
        return False


def ocr_pdf(path: str | Path, languages: str = "lit+eng", timeout_seconds: int = 180) -> OcrResult:
    path = Path(path)
    if not ocr_available():
        return OcrResult(text="", success=False, error="ocrmypdf neįdiegtas šioje aplinkoje")

    with tempfile.TemporaryDirectory(prefix="ocr_") as tmp:
        out_path = Path(tmp) / "ocr_output.pdf"
        try:
            result = subprocess.run(
                [
                    "ocrmypdf",
                    "--language",
                    languages,
                    "--force-ocr",
                    "--quiet",
                    str(path),
                    str(out_path),
                ],
                capture_output=True,
                timeout=timeout_seconds,
            )
        except FileNotFoundError:
            return OcrResult(text="", success=False, error="ocrmypdf CLI nerastas")
        except subprocess.TimeoutExpired:
            return OcrResult(text="", success=False, error="OCR viršijo laiko limitą")

        if result.returncode != 0 or not out_path.exists():
            stderr = result.stderr.decode("utf-8", errors="replace")[-2000:]
            return OcrResult(text="", success=False, error=f"ocrmypdf klaida: {stderr}")

        extracted = extract_pdf_text(out_path)
        if not extracted.has_text_layer:
            return OcrResult(text="", success=False, error="OCR nerado atpažįstamo teksto")
        return OcrResult(text=extracted.text, success=True)
