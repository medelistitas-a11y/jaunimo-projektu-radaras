"""Patikrina, kad tas pats dokumentas (pagal turinio hash), pasiekiamas iš
DVIEJŲ skirtingų puslapių, nėra analizuojamas (OCR/tekstas ištraukiamas) du
kartus — antrą kartą naudojamas jau turimas rezultatas.
"""

from __future__ import annotations

from pathlib import Path

import httpx

import app.crawler.runner as runner_module
from app.crawler.adapters.base import DiscoveredItem
from app.crawler.runner import _process_item
from app.models.document import Document
from app.models.source import Source, SourceCheckResult

FIXTURES = Path(__file__).parent / "fixtures"
# Realus, parsuojamas PDF (tas pats fixture'as, naudojamas test_extract_pdf.py) —
# reikalingas, kad dedup logika (kuri tikrina extraction_status == "ok") suveiktų.
PDF_BYTES = (FIXTURES / "sample.pdf").read_bytes()


class _FakeFetchResult:
    def __init__(self, text=None, content=None, headers=None, not_modified=False):
        self.text = text
        self.content = content
        self.headers = headers or httpx.Headers({})
        self.not_modified = not_modified


class _FakeClient:
    """Grąžina skirtingą HTML kiekvienam puslapiui, bet tą patį PDF turinį abiem."""

    def __init__(self):
        self.doc_fetch_count = 0

    def get(self, url, **kwargs):
        if url.endswith(".pdf"):
            self.doc_fetch_count += 1
            return _FakeFetchResult(content=PDF_BYTES, headers=httpx.Headers({}))
        if "page1" in url:
            html = (
                "<html><body><main><h1>Puslapis 1</h1>"
                "<p>Jaunimo mokymų konkursas puslapyje 1.</p>"
                '<a href="https://testine.lt/doc.pdf">doc.pdf</a></main></body></html>'
            )
        else:
            html = (
                "<html><body><main><h1>Puslapis 2</h1>"
                "<p>Jaunimo mokymų konkursas puslapyje 2 (kitas tekstas).</p>"
                '<a href="https://testine.lt/doc.pdf">doc.pdf</a></main></body></html>'
            )
        return _FakeFetchResult(text=html, headers=httpx.Headers({}))


def _source() -> Source:
    return Source(
        code="test_doc_dedup",
        name="Testinis šaltinis",
        institution_name="Testinė institucija",
        municipality="Testinė sav.",
        official_domain="testine.lt",
        start_urls=["https://testine.lt/"],
        source_type="html",
        allowed_document_domains=["testine.lt"],
        adapter="generic_html",
        status="active",
        enabled=True,
    )


def test_same_document_extracted_only_once_across_pages(db_session, test_settings, monkeypatch):
    extraction_calls = {"n": 0}
    real_extract = runner_module._extract_document_text

    def counting_extract(url, content, settings):
        extraction_calls["n"] += 1
        return real_extract(url, content, settings)

    monkeypatch.setattr(runner_module, "_extract_document_text", counting_extract)

    source = _source()
    db_session.add(source)
    db_session.commit()

    client = _FakeClient()
    check = SourceCheckResult(
        crawl_run_id=1,
        source_id=source.id,
        status="ok",
        pages_fetched=0,
        pages_unchanged=0,
        documents_found=0,
        opportunities_found=0,
    )
    check._created_count = 0
    check._updated_count = 0

    item1 = DiscoveredItem(title="Puslapis 1", url="https://testine.lt/page1")
    item2 = DiscoveredItem(title="Puslapis 2", url="https://testine.lt/page2")

    _process_item(db_session, source, item1, client, test_settings, check)
    _process_item(db_session, source, item2, client, test_settings, check)
    db_session.commit()

    # PDF turinys buvo atsiųstas du kartus (skirtingi puslapiai), bet ekstrakcija
    # (potencialiai brangus OCR/tekstinis parsavimas) turėjo įvykti TIK KARTĄ.
    assert client.doc_fetch_count == 2
    assert extraction_calls["n"] == 1

    docs = db_session.query(Document).all()
    assert len(docs) == 2  # abi Document eilutės išsaugotos (kilmės istorija)
    assert all(d.extracted_text for d in docs)
    assert docs[0].extracted_text == docs[1].extracted_text
