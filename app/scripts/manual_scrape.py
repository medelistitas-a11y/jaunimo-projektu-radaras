"""Rankinis tikrinimo paleidimas iš komandinės eilutės.

Naudojimas:
  python -m app.scripts.manual_scrape                 # visi įjungti šaltiniai
  python -m app.scripts.manual_scrape --source kaunas_naujienos   # tik vienas šaltinis
"""

from __future__ import annotations

import argparse
import logging
import sys

from app.config import get_settings
from app.crawler.runner import run_crawl
from app.db import SessionLocal
from app.notify.center import generate_notifications_for_run
from app.seed.sources_seed import seed_sources

logging.basicConfig(level=logging.INFO)


def main() -> int:
    parser = argparse.ArgumentParser(description="Rankinis šaltinių tikrinimas")
    parser.add_argument("--source", help="Vieno šaltinio kodas (žr. sources.yaml)", default=None)
    args = parser.parse_args()

    settings = get_settings()
    db = SessionLocal()
    try:
        seed_sources(db)
        run = run_crawl(db, settings, trigger="manual", only_source_code=args.source)
        notifications = generate_notifications_for_run(db, run)
        print(
            f"CrawlRun #{run.id}: statusas={run.status}, šaltiniai ok={run.sources_ok}, "
            f"klaidos={run.sources_error}, blokuota={run.sources_blocked}, "
            f"naujos={run.new_opportunities}, atnaujintos={run.updated_opportunities}, "
            f"nauji pranešimai={notifications}"
        )
        if run.log:
            print("--- log ---")
            print(run.log)
        return 0 if run.status != "failed" else 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
