"""Vieno serverio MVP kasdienio paleidimo procesas (APScheduler).

Paleidimo laikas nustatomas DAILY_CRAWL_TIME (HH:MM) aplinkos kintamuoju,
laiko juosta — TIMEZONE (numatyta Europe/Vilnius). Architektūra leidžia
vėliau pakeisti į Celery/Redis, bet MVP tam poreikio nėra (vienas procesas,
vienas kasdienis darbas).

Paleidimas: python -m app.scheduler.run_worker
"""

from __future__ import annotations

import logging
import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.scheduler.jobs import run_daily_job

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app.scheduler.run_worker")


def main() -> None:
    settings = get_settings()
    if not settings.scheduler_enabled:
        logger.info("SCHEDULER_ENABLED=false — kasdienis darbas neplanuojamas. Procesas laukia.")
        while True:
            time.sleep(3600)

    hour, _, minute = settings.daily_crawl_time.partition(":")
    scheduler = BackgroundScheduler(timezone=settings.timezone)
    scheduler.add_job(
        run_daily_job,
        trigger=CronTrigger(hour=int(hour), minute=int(minute or 0), timezone=settings.timezone),
        id="daily_crawl",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    logger.info(
        "Planuoklis paleistas: kasdien %s (%s laiku).",
        settings.daily_crawl_time,
        settings.timezone,
    )
    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


if __name__ == "__main__":
    main()
