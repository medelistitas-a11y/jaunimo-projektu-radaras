"""Ištrina originalius dokumentų failus, senesnius nei DOCUMENT_RETENTION_DAYS.

Ištrauktas tekstas (Document.extracted_text) DB įraše NELIEČIAMAS — trinamas
tik originalus failas diske ir Document.storage_path nustatomas į NULL.

Naudojimas: python -m app.scripts.cleanup_documents
"""

from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path

from app.config import get_settings
from app.db import SessionLocal
from app.models.document import Document

logger = logging.getLogger("app.scripts.cleanup_documents")


def cleanup_old_documents() -> int:
    settings = get_settings()
    cutoff = dt.datetime.now(dt.UTC) - dt.timedelta(days=settings.document_retention_days)
    db = SessionLocal()
    deleted = 0
    try:
        old_docs = (
            db.query(Document)
            .filter(Document.storage_path.is_not(None), Document.downloaded_at < cutoff)
            .all()
        )
        for doc in old_docs:
            path = Path(doc.storage_path)
            if path.exists():
                path.unlink(missing_ok=True)
            doc.storage_path = None
            deleted += 1
        db.commit()
    finally:
        db.close()
    return deleted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    count = cleanup_old_documents()
    print(f"Ištrinta pasenusių originalių dokumentų: {count}")
