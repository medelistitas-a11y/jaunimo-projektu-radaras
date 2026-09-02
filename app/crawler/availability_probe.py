"""Lengvas pasiekiamumo patikrinimas šaltiniams, pažymėtiems
`blocked_in_current_runtime` (arba bet kuriam šaltiniui apskritai) — TIK
vienas GET į pirmą start_url, be adapterio/turinio analizės. Įrašo tikslų
HTTP statusą, atsakymo Content-Type ir bot-apsaugos signatūrą (Cloudflare
`cf-mitigated`/`server: cloudflare` antraštes + „Just a moment“ turinį).

Paleidžiama automatiškai kartą per savaitę (žr. app/scheduler/jobs.py) —
NE kas dieną, kad nebūtų be reikalo apkraunami blokuoti domenai. Jei
patikrinimas parodo, kad šaltinis dabar pasiekiamas, statusas automatiškai
keičiamas į "needs_verification" (adapterio konfigūracija vis tiek turi būti
patvirtinta žmogaus prieš įjungiant automatinį crawl) ir sukuriamas
Notification įrašas.
"""

from __future__ import annotations

import datetime as dt
import logging

from sqlalchemy.orm import Session

from app.config import Settings
from app.crawler.http_client import FetchError, PoliteHttpClient, RobotsDisallowedError
from app.crawler.ssrf_guard import SsrfBlockedError
from app.models.assessment import Notification
from app.models.source import Source

logger = logging.getLogger("app.crawler.availability_probe")

WEEKLY_RECHECK_INTERVAL = dt.timedelta(days=7)

_CF_HEADER_MARKERS = ("cf-mitigated", "cf-ray")


def _detect_bot_protection_signature(status_code: int, headers, text: str | None) -> str | None:
    server = (headers.get("server") or "").lower()
    cf_mitigated = headers.get("cf-mitigated")
    signals = []
    if "cloudflare" in server:
        signals.append("server: cloudflare")
    if cf_mitigated:
        signals.append(f"cf-mitigated: {cf_mitigated}")
    if text and "Just a moment" in text[:2000]:
        signals.append('turinys: "Just a moment..." (Cloudflare JS iššūkis)')
    if status_code == 403 and signals:
        return "; ".join(signals)
    if status_code == 403 and not signals:
        return "HTTP 403 be aiškios Cloudflare signatūros (galimai kita bot-apsauga)"
    return None


def probe_source_availability(source: Source, settings: Settings) -> dict:
    """Grąžina diagnostinį žodyną. Nekelia išimties į viršų — klaidos įrašomos
    kaip rezultato dalis, kad iškviečiantis kodas visada galėtų atnaujinti DB.
    """
    now = dt.datetime.now(dt.UTC)
    result = {
        "probed_at": now,
        "http_status_code": None,
        "content_type": None,
        "bot_protection_signature": None,
        "now_accessible": False,
        "error": None,
    }
    if not source.start_urls:
        result["error"] = "Šaltinis neturi start_urls"
        return result

    allowed_domains = list({source.official_domain, *(source.allowed_document_domains or [])})
    try:
        with PoliteHttpClient(
            user_agent=settings.crawler_user_agent,
            allowed_domains=allowed_domains,
            min_delay_seconds=settings.crawler_min_delay_seconds,
            timeout_seconds=settings.crawler_request_timeout_seconds,
            max_retries=1,
            max_download_bytes=settings.crawler_max_download_mb * 1024 * 1024,
        ) as client:
            fetch = client.get(source.start_urls[0])
    except (FetchError, RobotsDisallowedError, SsrfBlockedError) as exc:
        result["error"] = str(exc)
        return result

    result["http_status_code"] = fetch.status_code
    result["content_type"] = fetch.headers.get("content-type")
    result["bot_protection_signature"] = _detect_bot_protection_signature(
        fetch.status_code, fetch.headers, fetch.text
    )
    result["now_accessible"] = (
        fetch.status_code == 200 and result["bot_protection_signature"] is None
    )
    return result


def probe_with_playwright(url: str, user_agent: str, timeout_ms: int = 25000) -> dict:
    """Diagnostinis TIK-navigacijos patikrinimas realia (Chromium) naršykle —
    NIEKADA nebando spręsti CAPTCHA ar kitaip apeiti iššūkio, tik stebi, ar
    puslapis apskritai pasiekiamas ir koks turinys grąžinamas. Naudojama
    IŠSKIRTINAI diagnostikai (žr. app/scripts/smoke_test_jra_vilnius.py), ne
    reguliariam crawl'ui.

    Grąžina {"status": "success"|"challenge_shown"|"connection_reset"|"error"|
    "not_tested_sandbox_limitation", "detail": str, "title": str|None}.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {
            "status": "not_tested_sandbox_limitation",
            "detail": "Playwright paketas neįdiegtas šioje aplinkoje.",
            "title": None,
        }

    try:
        with sync_playwright() as p:
            # channel="chromium" priverčia naudoti pilną Chromium naršyklę, ne naujesnį
            # "chrome-headless-shell" variantą — pastarasis kai kuriose Docker/CI aplinkose
            # neįdiegtas atskirai net kai pilnas chromium yra, ir turi labiau atpažįstamą
            # bot-fingerprint sudėtingoms svetainėms su anti-bot apsauga.
            browser = p.chromium.launch(headless=True, channel="chromium")
            try:
                page = browser.new_page(user_agent=user_agent)
                response = page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)  # leidžiama JS iššūkiui automatiškai pasireikšti
                title = page.title()
                content = page.content()
                status_code = response.status if response else None

                if title and "just a moment" in title.lower():
                    return {
                        "status": "challenge_shown",
                        "detail": f"HTTP {status_code}, antraštė: {title!r}",
                        "title": title,
                    }
                if status_code and status_code < 400:
                    return {
                        "status": "success",
                        "detail": f"HTTP {status_code}, antraštė: {title!r}, turinio ilgis: {len(content)}",
                        "title": title,
                    }
                return {
                    "status": "error",
                    "detail": f"HTTP {status_code}, antraštė: {title!r}",
                    "title": title,
                }
            finally:
                browser.close()
    except Exception as exc:  # noqa: BLE001 - diagnostinė funkcija, niekada neturi mesti išimties
        message = str(exc)
        if "ERR_CONNECTION_RESET" in message or "net::ERR" in message:
            return {"status": "connection_reset", "detail": message[:500], "title": None}
        return {"status": "error", "detail": message[:500], "title": None}


def run_weekly_availability_probes(db: Session, settings: Settings) -> int:
    """Patikrina visus šaltinius, kurių statusas rodo blokavimą arba
    nepatvirtintą pasiekiamumą, IR kurių paskutinis probe buvo prieš 7+ dienų
    (arba niekada). Grąžina patikrintų šaltinių skaičių.
    """
    now = dt.datetime.now(dt.UTC)
    cutoff = now - WEEKLY_RECHECK_INTERVAL

    candidates = (
        db.query(Source)
        .filter(Source.status.in_(["blocked_in_current_runtime", "needs_verification"]))
        .filter((Source.last_probe_at.is_(None)) | (Source.last_probe_at < cutoff))
        .all()
    )

    checked = 0
    for source in candidates:
        diag = probe_source_availability(source, settings)
        source.last_probe_at = diag["probed_at"]
        source.last_http_status_code = diag["http_status_code"]
        source.last_response_content_type = diag["content_type"]
        source.last_bot_protection_signature = diag["bot_protection_signature"]
        checked += 1

        if diag["now_accessible"] and source.status == "blocked_in_current_runtime":
            old_status = source.status
            source.status = "needs_verification"
            logger.info(
                "Šaltinis %s dabar pasiekiamas (buvo %s) — pažymėtas needs_verification.",
                source.code,
                old_status,
            )
            db.add(
                Notification(
                    kind="source_now_accessible",
                    title=f"Šaltinis vėl pasiekiamas: {source.name}",
                    body=(
                        f"Savaitinė patikra parodė, kad {source.code} dabar grąžina HTTP "
                        f"{diag['http_status_code']} be bot-apsaugos signatūros. Statusas "
                        "pakeistas į needs_verification — reikia patvirtinti adapterio "
                        "konfigūraciją prieš įjungiant automatinį crawl."
                    ),
                    opportunity_id=None,
                    dedup_key=f"source_now_accessible:{source.code}:{now.date().isoformat()}",
                )
            )
        elif diag["error"]:
            source.last_error = diag["error"]

    db.commit()
    return checked
