"""Atskiras JRA ir Vilniaus konkursų sistemos pasiekiamumo smoke testas.

Šie du šaltiniai yra privalomi pagal užduotį, bet buvo blokuojami iš šios
kūrimo sesijos aplinkos (Cloudflare bot-apsauga). Kadangi jie yra vieši ir
pasiekiami iš dalies tinklo aplinkų, šis testas TURI būti paleistas iš
realios hostingo aplinkos (pvz. Render), kur rezultatas gali skirtis.

Testuoja DU kelius:
1. Paprastą HTTP klientą (tą patį, kurį naudoja generic_html adapteris).
2. Playwright/Chromium (TIK navigacijos patikrai — niekada nebandoma spręsti
   CAPTCHA ar kitaip apeiti iššūkio).

Atnaujina Source diagnostinius laukus DB (jei šaltiniai jau seedinti) ir
atspausdina žmogui skaitomą santrauką.

Naudojimas: python -m app.scripts.smoke_test_jra_vilnius
"""

from __future__ import annotations

import datetime as dt
import logging
import sys

from app.config import get_settings
from app.crawler.availability_probe import probe_source_availability, probe_with_playwright
from app.db import SessionLocal
from app.models.source import Source

logging.basicConfig(level=logging.WARNING)

TARGET_CODES = ["jra_finansavimo_konkursai", "vilnius_konkursai"]


def _print_result(code: str, name: str, url: str, http_diag: dict, pw_diag: dict) -> None:
    print(f"\n=== {name} ({code}) ===")
    print(f"URL: {url}")
    print("--- Paprastas HTTP klientas ---")
    print(f"  HTTP statusas: {http_diag['http_status_code']}")
    print(f"  Content-Type: {http_diag['content_type']}")
    print(f"  Bot-apsaugos signatūra: {http_diag['bot_protection_signature']}")
    print(f"  Dabar pasiekiamas: {http_diag['now_accessible']}")
    if http_diag["error"]:
        print(f"  Klaida: {http_diag['error']}")
    print("--- Playwright/Chromium (tik navigacija, CAPTCHA NESPRENDŽIAMA) ---")
    print(f"  Statusas: {pw_diag['status']}")
    print(f"  Detalės: {pw_diag['detail']}")


def main() -> int:
    settings = get_settings()
    db = SessionLocal()
    now = dt.datetime.now(dt.UTC)
    any_error = False
    try:
        sources = db.query(Source).filter(Source.code.in_(TARGET_CODES)).all()
        if not sources:
            print(
                "ĮSPĖJIMAS: šaltiniai nerasti DB. Paleiskite "
                "`python -m app.seed.sources_seed` prieš šį testą, kad rezultatai "
                "būtų įrašyti į registrą. Testas vis tiek tęsiamas prieš žinomus URL."
            )
            from app.seed.sources_seed import load_yaml

            data = load_yaml()
            sources = [
                s
                for s in [
                    _entry_to_source(e)
                    for e in data.get("sources", [])
                    if e["code"] in TARGET_CODES
                ]
            ]

        for source in sources:
            http_diag = probe_source_availability(source, settings)
            pw_diag = probe_with_playwright(source.start_urls[0], settings.crawler_user_agent)

            _print_result(source.code, source.name, source.start_urls[0], http_diag, pw_diag)

            if isinstance(source, Source) and source.id is not None:
                source.last_probe_at = http_diag["probed_at"]
                source.last_http_status_code = http_diag["http_status_code"]
                source.last_response_content_type = http_diag["content_type"]
                source.last_bot_protection_signature = http_diag["bot_protection_signature"]
                source.last_playwright_check_status = pw_diag["status"]
                source.last_playwright_checked_at = now
                if http_diag["now_accessible"] and source.status == "blocked_in_current_runtime":
                    source.status = "needs_verification"
                    print("  -> Statusas atnaujintas į needs_verification (buvo blokuotas).")

            if http_diag["error"] and pw_diag["status"] == "error":
                any_error = True

        db.commit()
    finally:
        db.close()

    print("\nBaigta. Šis testas NIEKADA nebando apeiti CAPTCHA ar kitos prieigos kontrolės.")
    return 1 if any_error else 0


def _entry_to_source(entry: dict) -> Source:
    """Sukuria laikiną (neišsaugotą) Source objektą iš sources.yaml įrašo,
    kai šaltinis dar neseedintas į DB — kad testas veiktų ir prieš pirmą seedą.
    """
    return Source(
        code=entry["code"],
        name=entry["name"],
        institution_name=entry["institution_name"],
        official_domain=entry.get("official_domain") or "",
        start_urls=entry.get("start_urls") or [],
        source_type=entry.get("source_type", "unknown"),
        allowed_document_domains=entry.get("allowed_document_domains") or [],
        adapter=entry.get("adapter", "generic_html"),
        status=entry.get("status", "needs_verification"),
    )


if __name__ == "__main__":
    sys.exit(main())
