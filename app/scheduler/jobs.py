"""Kasdienio darbo logika: paleidžia CrawlRun, generuoja pranešimus, siunčia
el. pašto santrauką (jei sukonfigūruota). Naudoja PostgreSQL advisory lock
(žr. app.crawler.runner) apsaugai nuo dvigubo paleidimo.
"""

from __future__ import annotations

import logging

from app.config import get_settings
from app.crawler.runner import run_crawl
from app.db import SessionLocal
from app.notify.center import generate_notifications_for_run
from app.notify.email_digest import send_daily_digest
from app.scripts.cleanup_documents import cleanup_old_documents
from app.seed.sources_seed import seed_sources

logger = logging.getLogger("app.scheduler.jobs")


def run_daily_job() -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        seed_sources(db)
        logger.info("Pradedamas kasdienis tikrinimas (trigger=scheduled).")
        run = run_crawl(db, settings, trigger="scheduled")
        logger.info(
            "Kasdienis tikrinimas baigtas: statusas=%s, šaltinių ok=%d, klaidų=%d, "
            "naujų=%d, atnaujintų=%d.",
            run.status,
            run.sources_ok,
            run.sources_error,
            run.new_opportunities,
            run.updated_opportunities,
        )
        generate_notifications_for_run(db, run)
        send_daily_digest(db, settings)
        removed = cleanup_old_documents()
        if removed:
            logger.info("Išvalyta pasenusių originalių dokumentų: %d.", removed)
    except RuntimeError as exc:
        # Advisory lock užimtas — kitas paleidimas jau vyksta, praleidžiame ramiai.
        logger.warning("Kasdienis tikrinimas praleistas: %s", exc)
    except Exception:
        logger.exception("Kasdienis tikrinimas nepavyko dėl nenumatytos klaidos.")
    finally:
        db.close()
