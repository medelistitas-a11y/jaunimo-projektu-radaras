"""Dublikatų atpažinimas: URL kanonizavimas ir panašumo paieška.

Automatinis sujungimas vyksta TIK esant aukštam pasitikėjimui (identiškas
kanoninis URL arba identiškas dokumento turinio hash). Kitais atvejais —
tik pažymima kaip galimas dublikatas žmogaus peržiūrai
(``Opportunity.possible_duplicate_of_id``), niekada tyliai nesujungiama.
"""

from __future__ import annotations

import difflib
import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy.orm import Session

from app.models.opportunity import Opportunity

_TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid"}

FUZZY_TITLE_THRESHOLD = 0.84


def canonicalize_url(url: str) -> str:
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = parsed.path.rstrip("/") or "/"
    query = [(k, v) for k, v in parse_qsl(parsed.query) if k.lower() not in _TRACKING_PARAMS]
    query.sort()
    return urlunparse((parsed.scheme, netloc, path, "", urlencode(query), ""))


def slugify_title(title: str) -> str:
    title = title.lower().strip()
    title = re.sub(r"[^\w\s]", "", title, flags=re.UNICODE)
    title = re.sub(r"\s+", "-", title)
    return title[:120]


def make_canonical_key(title: str, municipality: str | None) -> str:
    return f"{municipality or 'lt'}::{slugify_title(title)}"


def find_by_canonical_url(db: Session, canonical_url: str) -> Opportunity | None:
    candidates = db.query(Opportunity).filter(Opportunity.merged_into_id.is_(None)).all()
    for opp in candidates:
        for url in [opp.primary_url, *opp.source_urls]:
            if canonicalize_url(url) == canonical_url:
                return opp
    return None


def find_fuzzy_duplicate(
    db: Session,
    title: str,
    municipality: str | None,
    exclude_id: int | None = None,
    threshold: float = FUZZY_TITLE_THRESHOLD,
) -> Opportunity | None:
    query = db.query(Opportunity).filter(Opportunity.merged_into_id.is_(None))
    if municipality:
        query = query.filter(Opportunity.municipality == municipality)
    if exclude_id:
        query = query.filter(Opportunity.id != exclude_id)

    best_match: Opportunity | None = None
    best_ratio = 0.0
    norm_title = title.lower().strip()
    for candidate in query.all():
        ratio = difflib.SequenceMatcher(None, norm_title, candidate.title.lower().strip()).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = candidate

    if best_match and best_ratio >= threshold:
        return best_match
    return None
