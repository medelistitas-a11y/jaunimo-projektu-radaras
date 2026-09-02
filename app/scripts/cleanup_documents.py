"""Ištrina originalius dokumentų failus (S3 suderinamoje saugykloje),
senesnius nei DOCUMENT_RETENTION_DAYS.

Ištrauktas tekstas (Document.extracted_text) DB įraše NELIEČIAMAS — trinamas
tik originalas saugykloje ir Document.storage_path nustatomas į NULL. Jei
S3 neįjungta, dauguma Document įrašų iš viso neturės storage_path (originalai
niekada nebuvo saugomi), todėl šis skriptas paprastai neras ką valyti — tai
NORMALU, ne klaida.

Naudojimas: python -m app.scripts.cleanup_documents
"""

from __future__ import annotations

import datetime as dt
import logging

from app.config import get_settings
from app.db import SessionLocal
from app.models.document import Document
from app.storage.object_store import delete_document

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
            if doc.storage_path.startswith("s3://"):
                delete_document(doc.storage_path, settings)
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
