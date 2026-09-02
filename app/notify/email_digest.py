"""Kasdienė el. pašto santrauka per SMTP. Išjungta, kol .env nepateikti SMTP
duomenys (žr. Settings.smtp_configured). Nesiunčia, jei nėra nieko naujo,
nebent WEEKLY_EMPTY_SUMMARY=true. Nedubliuoja: naudoja tą patį Notification
registrą ir žymi emailed=True, kad tas pats pranešimas nebūtų persiųstas.
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from app.config import Settings
from app.models.assessment import Notification

logger = logging.getLogger("app.notify.email_digest")

_KIND_LABELS = {
    "new_green": "Naujos žalios galimybės",
    "changed_green_yellow": "Pasikeitę vertinimai",
    "deadline_soon": "Artėjantys terminai",
    "source_error": "Šaltinių klaidos",
}


def build_digest_text(notifications: list[Notification]) -> str:
    if not notifications:
        return "Naujų pranešimų nėra."
    by_kind: dict[str, list[Notification]] = {}
    for n in notifications:
        by_kind.setdefault(n.kind, []).append(n)

    lines = ["„Mostai galimybių radaras“ — kasdienė santrauka", ""]
    for kind, label in _KIND_LABELS.items():
        items = by_kind.get(kind, [])
        if not items:
            continue
        lines.append(f"== {label} ({len(items)}) ==")
        for n in items:
            lines.append(f"- {n.title}")
            lines.append(f"  {n.body}")
        lines.append("")
    return "\n".join(lines)


def send_daily_digest(db: Session, settings: Settings) -> bool:
    if not settings.smtp_configured:
        logger.info("SMTP nesukonfigūruotas — el. pašto santrauka neišsiunčiama.")
        return False

    pending = db.query(Notification).filter(Notification.emailed.is_(False)).all()
    if not pending and not settings.weekly_empty_summary:
        logger.info("Nėra naujų pranešimų — el. laiškas nesiunčiamas (WEEKLY_EMPTY_SUMMARY=false).")
        return False

    body = build_digest_text(pending)
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = "Mostai galimybių radaras — kasdienė santrauka"
    msg["From"] = settings.smtp_from
    msg["To"] = settings.smtp_to

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(settings.smtp_from, [settings.smtp_to], msg.as_string())
    except (smtplib.SMTPException, OSError) as exc:
        logger.error("Nepavyko išsiųsti el. pašto santraukos: %s", exc)
        return False

    for n in pending:
        n.emailed = True
    db.commit()
    return True
