"""Vienkartinis kasdienio darbo paleidimas iš komandinės eilutės (naudojama
Render cron servise, žr. render.yaml). Atlieka tą patį darbą kaip
app.scheduler.run_worker suplanuotas darbas: seedina šaltinius, paleidžia
CrawlRun, generuoja pranešimus, siunčia SMTP santrauką (jei sukonfigūruota),
išvalo pasenusius dokumentus — tada baigia darbą (nesilieka veikti).

Naudojimas: python -m app.scripts.run_daily
"""

from __future__ import annotations

import logging

from app.scheduler.jobs import run_daily_job

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_daily_job()
