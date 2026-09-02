"""Įkelia sources.yaml turinį į DB (upsert pagal `code`).

Naudojimas: `python -m app.seed.sources_seed` arba kviečiama automatiškai
programos starte (app/main.py lifespan), kad DB visada turėtų bent minimalų
registrą net švarioje aplinkoje.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from app.models.source import Source

SOURCES_YAML_PATH = Path(__file__).resolve().parent.parent.parent / "sources.yaml"


def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return text


def load_yaml(path: Path = SOURCES_YAML_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def seed_sources(db: Session, path: Path = SOURCES_YAML_PATH) -> tuple[int, int]:
    """Grąžina (sukurta, atnaujinta) skaičius."""
    data = load_yaml(path)
    created = 0
    updated = 0

    for entry in data.get("sources", []):
        existing = db.query(Source).filter_by(code=entry["code"]).one_or_none()
        fields = dict(
            name=entry["name"],
            institution_name=entry["institution_name"],
            municipality=entry.get("municipality"),
            region=entry.get("region"),
            official_domain=entry.get("official_domain") or "",
            start_urls=entry.get("start_urls") or [],
            source_type=entry.get("source_type", "unknown"),
            allowed_document_domains=entry.get("allowed_document_domains") or [],
            relevant_path_hints=entry.get("relevant_path_hints") or [],
            ignored_path_hints=entry.get("ignored_path_hints") or [],
            adapter=entry.get("adapter", "generic_html"),
            adapter_config=entry.get("adapter_config") or {},
            check_frequency_hours=entry.get("check_frequency_hours", 24),
            status=entry.get("status", "needs_verification"),
            is_official=entry.get("is_official", True),
            enabled=entry.get("enabled", False),
            notes=entry.get("notes"),
        )
        if existing is None:
            db.add(Source(code=entry["code"], **fields))
            created += 1
        else:
            for k, v in fields.items():
                setattr(existing, k, v)
            updated += 1

    for muni in data.get("municipalities", []):
        code = f"muni_{_slugify(muni['domain'])}"
        existing = db.query(Source).filter_by(code=code).one_or_none()
        if existing is not None:
            # Nepertvarkome jau administratoriaus rankiniu būdu sukonfigūruoto šaltinio,
            # jei jis jau turi savo adapter_config (pvz. Kaunas, Skuodas turi atskirus
            # `sources` įrašus, ne šioje sekcijoje, todėl kolizijos nebus).
            existing.status = muni["status"]
            existing.notes = (
                f"Automatinis auditas: HTTP {muni['http_status']} "
                f"({'žr. SOURCE_AUDIT.md' if muni['http_status'] else 'ryšio klaida iš audito aplinkos'})."
            )
            updated += 1
            continue
        db.add(
            Source(
                code=code,
                name=f"{muni['name']} savivaldybė",
                institution_name=f"{muni['name']} savivaldybė",
                municipality=muni["name"],
                region=None,
                official_domain=muni["domain"],
                start_urls=[f"https://www.{muni['domain']}/"],
                source_type="html",
                allowed_document_domains=[muni["domain"]],
                relevant_path_hints=[],
                ignored_path_hints=[],
                adapter="generic_html",
                adapter_config={},
                check_frequency_hours=24,
                status=muni["status"],
                is_official=True,
                enabled=False,
                notes=(
                    f"Automatinis auditas 2026-09-02: HTTP {muni['http_status']}. "
                    "Neįjungta automatiniam crawl, kol administratorius nepatvirtina tikslios "
                    "jaunimo/konkursų skilties URL (žr. SOURCE_AUDIT.md)."
                ),
            )
        )
        created += 1

    db.commit()
    return created, updated


if __name__ == "__main__":
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        c, u = seed_sources(db)
        print(f"Šaltinių registras: sukurta {c}, atnaujinta {u}.")
    finally:
        db.close()
