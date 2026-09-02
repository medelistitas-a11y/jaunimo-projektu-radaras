import datetime as dt

from app.config import Settings
from app.db import Base
from app.models.document import Document


def test_cleanup_removes_old_s3_objects_and_keeps_recent(monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    import app.scripts.cleanup_documents as cleanup_module

    monkeypatch.setattr(cleanup_module, "SessionLocal", TestSession)
    monkeypatch.setattr(
        cleanup_module, "get_settings", lambda: Settings(document_retention_days=30)
    )

    deleted_keys = []
    monkeypatch.setattr(
        cleanup_module,
        "delete_document",
        lambda uri, settings: deleted_keys.append(uri) or True,
    )

    now = dt.datetime.now(dt.UTC)
    session = TestSession()
    session.add(
        Document(
            source_url="https://x.lt/old.pdf",
            file_type="pdf",
            content_hash="old",
            downloaded_at=now - dt.timedelta(days=60),
            storage_path="s3://mostai-bucket/documents/old.pdf",
            extraction_method="text",
            extracted_text="senas tekstas",
            extraction_status="ok",
        )
    )
    session.add(
        Document(
            source_url="https://x.lt/new.pdf",
            file_type="pdf",
            content_hash="new",
            downloaded_at=now - dt.timedelta(days=1),
            storage_path="s3://mostai-bucket/documents/new.pdf",
            extraction_method="text",
            extracted_text="naujas tekstas",
            extraction_status="ok",
        )
    )
    session.commit()
    session.close()

    removed_count = cleanup_module.cleanup_old_documents()

    assert removed_count == 1
    assert deleted_keys == ["s3://mostai-bucket/documents/old.pdf"]

    session = TestSession()
    docs = {d.content_hash: d for d in session.query(Document).all()}
    assert docs["old"].storage_path is None
    assert docs["old"].extracted_text == "senas tekstas"  # tekstas NELIEČIAMAS
    assert docs["new"].storage_path == "s3://mostai-bucket/documents/new.pdf"
    session.close()


def test_cleanup_is_noop_when_no_originals_ever_stored(monkeypatch):
    """Numatytoji būsena (S3_ENABLED=false): jokie Document įrašai neturi
    storage_path, tad valymas neturi ką daryti — tai NORMALU, ne klaida."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    import app.scripts.cleanup_documents as cleanup_module

    monkeypatch.setattr(cleanup_module, "SessionLocal", TestSession)
    monkeypatch.setattr(
        cleanup_module, "get_settings", lambda: Settings(document_retention_days=30)
    )

    now = dt.datetime.now(dt.UTC)
    session = TestSession()
    session.add(
        Document(
            source_url="https://x.lt/a.pdf",
            file_type="pdf",
            content_hash="a",
            downloaded_at=now - dt.timedelta(days=90),
            storage_path=None,
            extraction_method="text",
            extracted_text="tekstas be originalo saugojimo",
            extraction_status="ok",
        )
    )
    session.commit()
    session.close()

    assert cleanup_module.cleanup_old_documents() == 0
