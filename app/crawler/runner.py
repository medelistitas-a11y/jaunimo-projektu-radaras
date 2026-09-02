"""CrawlRun orkestravimas: paleidžia vieną ar visus šaltinius, apskaito
rezultatus, niekada nenutraukia viso paleidimo dėl vieno šaltinio klaidos.
"""

from __future__ import annotations

import datetime as dt
import logging
import time

from sqlalchemy.orm import Session

from app.config import Settings
from app.crawler.adapters import generic_html, wp_json
from app.crawler.adapters.js_playwright import PlaywrightUnavailableError
from app.crawler.adapters.js_playwright import discover_items as js_discover_items
from app.crawler.dedupe import canonicalize_url
from app.crawler.http_client import FetchError, PoliteHttpClient, RobotsDisallowedError
from app.crawler.pipeline import content_hash, process_candidate
from app.crawler.ssrf_guard import SsrfBlockedError
from app.extraction.docx_extract import extract_docx_text
from app.extraction.html_extract import extract_page
from app.extraction.pdf_extract import extract_pdf_text
from app.models.document import CrawledPage, Document
from app.models.source import CrawlRun, Source, SourceCheckResult

logger = logging.getLogger("app.crawler.runner")

_ADAPTERS = {
    "generic_html": generic_html.discover_items,
    "wp_json": wp_json.discover_items,
}

_DOC_EXT_TO_TYPE = {".pdf": "pdf", ".docx": "docx", ".doc": "doc", ".xlsx": "xlsx"}


def _document_type(url: str) -> str:
    lower = url.lower()
    for ext, kind in _DOC_EXT_TO_TYPE.items():
        if lower.endswith(ext):
            return kind
    return "other"


def _persist_original(
    content: bytes, content_hash: str, file_type: str, settings: Settings
) -> str | None:
    """Įrašo originalų dokumentą į DOCUMENT_STORAGE_DIR, jeigu katalogas
    egzistuoja ir yra rašomas (pvz. Docker Compose bendras tomas). Jei ne
    (pvz. atskiras vienkartinis Render cron konteineris be bendro disko su
    web servisu) — tyliai negrąžina kelio; ištrauktas tekstas vis tiek
    išsaugomas DB, kuri YRA bendra abiem servisams.
    """
    from pathlib import Path

    try:
        base_dir = Path(settings.document_storage_dir)
        base_dir.mkdir(parents=True, exist_ok=True)
        target = base_dir / f"{content_hash}.{file_type}"
        if not target.exists():
            target.write_bytes(content)
        return str(target)
    except OSError as exc:
        logger.debug("Nepavyko išsaugoti originalaus dokumento (%s): %s", content_hash, exc)
        return None


def _try_advisory_lock(db: Session, key: int = 823_401) -> bool:
    """PostgreSQL advisory lock, kad du procesai nepaleistų crawl vienu metu.
    SQLite (testams) tokio mechanizmo neturi — tokiu atveju visada leidžiama
    (testai patys kontroliuoja lygiagretumą).
    """
    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        return True
    result = db.execute(
        __import__("sqlalchemy").text("SELECT pg_try_advisory_lock(:key)"), {"key": key}
    )
    return bool(result.scalar())


def _release_advisory_lock(db: Session, key: int = 823_401) -> None:
    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        return
    db.execute(__import__("sqlalchemy").text("SELECT pg_advisory_unlock(:key)"), {"key": key})


def run_crawl(
    db: Session,
    settings: Settings,
    trigger: str = "manual",
    only_source_code: str | None = None,
) -> CrawlRun:
    if not _try_advisory_lock(db):
        raise RuntimeError(
            "Kitas tikrinimas jau vyksta (advisory lock užimtas) — paleidimas praleistas."
        )

    started_at = dt.datetime.now(dt.UTC)
    run = CrawlRun(
        started_at=started_at,
        trigger=trigger,
        scope="single_source" if only_source_code else "all",
        source_code=only_source_code,
        status="running",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    log_lines: list[str] = []

    try:
        query = db.query(Source).filter(Source.enabled.is_(True))
        if only_source_code:
            query = query.filter(Source.code == only_source_code)
        sources = query.all()
        run.sources_total = len(sources)

        for source in sources:
            check = _run_single_source(db, run, source, settings, log_lines)
            db.add(check)
            db.commit()

            if check.status == "ok":
                run.sources_ok += 1
            elif check.status == "blocked_bot_protection":
                run.sources_blocked += 1
            else:
                run.sources_error += 1
            run.new_opportunities += _count_created(check)
            run.updated_opportunities += _count_updated(check)

        run.status = "completed" if run.sources_error == 0 else "completed_with_errors"
    except Exception as exc:  # noqa: BLE001 - pati crawl orkestracija, ne vieno šaltinio kodas
        run.status = "failed"
        log_lines.append(f"KRITINĖ KLAIDA: {exc}")
        logger.exception("Crawl run nepavyko")
    finally:
        run.finished_at = dt.datetime.now(dt.UTC)
        run.log = "\n".join(log_lines)[:20000]
        try:
            db.commit()
        except Exception:
            # Jei net baigiamasis commit nepavyksta (pvz. netikėta DB klaida), NIEKADA
            # nepalikime CrawlRun įrašo su status="running" amžinai — kitaip
            # `run_crawl` sekantis kvietimas visada gautų RuntimeError dėl "jau vyksta"
            # ir programa liktų užstrigusi. Atšaukiame ir priverstinai užrašome "failed"
            # tiesiogine SQL komanda, apeinant ORM būseną.
            logger.exception(
                "Nepavyko įrašyti CrawlRun #%s baigiamosios būsenos — žymima 'failed'.", run.id
            )
            db.rollback()
            try:
                from sqlalchemy import text

                db.execute(
                    text(
                        "UPDATE crawl_runs SET status='failed', finished_at=:finished_at "
                        "WHERE id=:id"
                    ),
                    {"finished_at": dt.datetime.now(dt.UTC), "id": run.id},
                )
                db.commit()
            except Exception:
                logger.exception("Nepavyko net priverstinai pažymėti CrawlRun #%s.", run.id)
                db.rollback()
        _release_advisory_lock(db)

    return run


# Laikinas skaitiklių saugojimas per SourceCheckResult (paprastumo dėlei
# naudojame patį objektą kaip nešėją tarp _run_single_source ir run_crawl).
def _count_created(check: SourceCheckResult) -> int:
    return getattr(check, "_created_count", 0)


def _count_updated(check: SourceCheckResult) -> int:
    return getattr(check, "_updated_count", 0)


def _run_single_source(
    db: Session,
    run: CrawlRun,
    source: Source,
    settings: Settings,
    log_lines: list[str],
) -> SourceCheckResult:
    start_time = time.monotonic()
    check = SourceCheckResult(
        crawl_run_id=run.id,
        source_id=source.id,
        status="ok",
        pages_fetched=0,
        pages_unchanged=0,
        documents_found=0,
        opportunities_found=0,
    )
    check._created_count = 0  # type: ignore[attr-defined]
    check._updated_count = 0  # type: ignore[attr-defined]

    if source.status == "blocked_bot_protection":
        check.status = "blocked_bot_protection"
        check.error_message = source.notes
        check.duration_seconds = time.monotonic() - start_time
        source.last_checked_at = dt.datetime.now(dt.UTC)
        source.last_status = "blocked_bot_protection"
        log_lines.append(f"[{source.code}] praleista — bot apsauga (žr. registro pastabas).")
        return check

    allowed_domains = list({source.official_domain, *source.allowed_document_domains})

    try:
        if source.adapter == "js_playwright" or source.source_type == "js":
            items = js_discover_items(source)
        else:
            adapter_fn = _ADAPTERS.get(source.adapter)
            if adapter_fn is None:
                raise ValueError(f"Nežinomas adapteris: {source.adapter}")
            with PoliteHttpClient(
                user_agent=settings.crawler_user_agent,
                allowed_domains=allowed_domains,
                min_delay_seconds=settings.crawler_min_delay_seconds,
                timeout_seconds=settings.crawler_request_timeout_seconds,
                max_retries=settings.crawler_max_retries,
                max_download_bytes=settings.crawler_max_download_mb * 1024 * 1024,
            ) as client:
                items = adapter_fn(client, source, max_items=settings.crawler_max_urls_per_source)

                for item in items[: settings.crawler_max_urls_per_source]:
                    try:
                        _process_item(db, source, item, client, settings, check)
                    except (FetchError, RobotsDisallowedError, SsrfBlockedError) as exc:
                        log_lines.append(f"[{source.code}] praleistas elementas {item.url}: {exc}")
                        continue

        check.opportunities_found = check._created_count + check._updated_count  # type: ignore[attr-defined]
        source.last_success_at = dt.datetime.now(dt.UTC)
        source.last_status = "ok"

    except PlaywrightUnavailableError as exc:
        check.status = "error"
        check.error_message = str(exc)
        source.last_status = "error"
        log_lines.append(f"[{source.code}] Playwright nepasiekiamas: {exc}")
    except (FetchError, RobotsDisallowedError, SsrfBlockedError) as exc:
        check.status = "error"
        check.error_message = str(exc)
        source.last_status = "error"
        log_lines.append(f"[{source.code}] klaida: {exc}")
    except Exception as exc:  # noqa: BLE001 - vieno šaltinio klaida negali sustabdyti viso runo
        check.status = "error"
        check.error_message = f"{type(exc).__name__}: {exc}"
        source.last_status = "error"
        log_lines.append(f"[{source.code}] nenumatyta klaida: {exc}")
        logger.exception("Šaltinio %s tikrinimas nepavyko", source.code)

    source.last_checked_at = dt.datetime.now(dt.UTC)
    check.duration_seconds = time.monotonic() - start_time
    return check


def _process_item(db, source, item, client, settings, check) -> None:
    check.pages_fetched += 1
    canon_url = canonicalize_url(item.url)
    previous_page = (
        db.query(CrawledPage)
        .filter(CrawledPage.source_id == source.id, CrawledPage.canonical_url == canon_url)
        .one_or_none()
    )

    if item.detail_html is not None:
        html = item.detail_html
        base_url = item.url
    else:
        result = client.get(
            item.url,
            etag=previous_page.etag if previous_page else None,
            last_modified=previous_page.last_modified if previous_page else None,
        )
        if result.not_modified:
            check.pages_unchanged += 1
            return
        if not result.text:
            return
        html = result.text
        base_url = item.url

    content_hash_value = content_hash(html)
    if previous_page is not None and previous_page.content_hash == content_hash_value:
        # Turinys nepasikeitė (serveris negrąžino 304, bet hash sutampa) — neanalizuojame
        # iš naujo, tik atnaujiname patikrinimo laiką.
        check.pages_unchanged += 1
        previous_page.fetched_at = dt.datetime.now(dt.UTC)
        return

    etag = None
    last_modified = None
    if item.detail_html is None:
        etag = result.headers.get("etag")
        last_modified = result.headers.get("last-modified")

    if previous_page is None:
        previous_page = CrawledPage(
            source_id=source.id,
            url=item.url,
            canonical_url=canon_url,
            content_hash=content_hash_value,
        )
        db.add(previous_page)
    previous_page.fetched_at = dt.datetime.now(dt.UTC)
    previous_page.content_hash = content_hash_value
    previous_page.etag = etag
    previous_page.last_modified = last_modified
    previous_page.title = item.title[:500]

    content_selector = (source.adapter_config or {}).get("detail_content_selector")
    page = extract_page(html, base_url=base_url, content_selector=content_selector)
    full_text = page.text
    document_urls: list[str] = []

    for doc_url in page.document_links[:5]:
        doc_domain_allowed = any(
            d in doc_url for d in [source.official_domain, *source.allowed_document_domains]
        )
        if not doc_domain_allowed:
            continue
        try:
            doc_result = client.get(doc_url)
        except Exception:  # noqa: BLE001
            continue
        if not doc_result.content:
            continue
        document_urls.append(doc_url)
        check.documents_found += 1

        import hashlib

        doc_hash = hashlib.sha256(doc_result.content).hexdigest()

        existing_doc = (
            db.query(Document)
            .filter(Document.content_hash == doc_hash, Document.extraction_status == "ok")
            .first()
        )
        if existing_doc is not None:
            # Tas pats dokumentas (pagal turinio hash) jau sėkmingai ištrauktas anksčiau —
            # NEKVIEČIAME _extract_document_text (potencialiai brangus OCR/tekstinis
            # parsavimas) iš naujo, naudojame jau turimą rezultatą.
            doc_text = existing_doc.extracted_text
            extraction_method = existing_doc.extraction_method
            needs_review = existing_doc.needs_human_review
            storage_path = existing_doc.storage_path
        else:
            doc_text, extraction_method, needs_review = _extract_document_text(
                doc_url, doc_result.content, settings
            )
            storage_path = _persist_original(
                doc_result.content, doc_hash, _document_type(doc_url), settings
            )

        if doc_text:
            full_text += "\n\n" + doc_text

        db.add(
            Document(
                source_url=doc_url,
                file_type=_document_type(doc_url),
                file_size_bytes=len(doc_result.content),
                content_hash=doc_hash,
                downloaded_at=dt.datetime.now(dt.UTC),
                storage_path=storage_path,
                extraction_method=extraction_method,
                extracted_text=doc_text,
                extraction_status="ok"
                if doc_text
                else ("needs_human_review" if needs_review else "failed"),
                needs_human_review=needs_review,
            )
        )
        # Flush (ne commit) iš karto — kad TOS PAČIOS CrawlRun eigoje kitas puslapis,
        # nurodantis į tą patį dokumentą (pagal content_hash), jį rastų aukščiau esančioje
        # užklausoje net jei sesija sukonfigūruota su autoflush=False (žr. app/db.py).
        db.flush()

    result = process_candidate(
        db=db,
        source=source,
        title=item.title,
        url=item.url,
        text=full_text,
        document_urls=document_urls,
        settings=settings,
    )
    if result is not None:
        if result.is_new:
            check._created_count += 1  # type: ignore[attr-defined]
        elif result.is_updated:
            check._updated_count += 1  # type: ignore[attr-defined]


def _extract_document_text(
    url: str, content: bytes, settings: Settings
) -> tuple[str | None, str, bool]:
    import tempfile
    from pathlib import Path

    suffix = (
        ".pdf" if url.lower().endswith(".pdf") else ".docx" if url.lower().endswith(".docx") else ""
    )
    if not suffix:
        return None, "failed", True

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        if suffix == ".pdf":
            result = extract_pdf_text(tmp_path)
            if result.has_text_layer:
                return result.text, "text", False
            if settings.ocr_enabled:
                from app.extraction.ocr import ocr_pdf

                ocr_result = ocr_pdf(tmp_path, languages=settings.ocr_languages)
                if ocr_result.success:
                    return ocr_result.text, "ocr", False
            return None, "failed", True
        if suffix == ".docx":
            result = extract_docx_text(tmp_path)
            if result.success:
                return result.text, "text", False
            return None, "failed", True
    finally:
        tmp_path.unlink(missing_ok=True)

    return None, "failed", True
