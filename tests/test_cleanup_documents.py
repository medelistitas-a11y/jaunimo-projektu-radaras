import datetime as dt

from app.config import Settings
from app.db import Base
from app.models.document import Document


def test_cleanup_removes_old_files_and_keeps_recent(tmp_path, monkeypatch):
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
        cleanup_module,
        "get_settings",
        lambda: Settings(document_retention_days=30),
    )

    old_file = tmp_path / "old.pdf"
    old_file.write_bytes(b"senas")
    new_file = tmp_path / "new.pdf"
    new_file.write_bytes(b"naujas")

    now = dt.datetime.now(dt.UTC)
    session = TestSession()
    session.add(
        Document(
            source_url="https://x.lt/old.pdf",
            file_type="pdf",
            content_hash="old",
            downloaded_at=now - dt.timedelta(days=60),
            storage_path=str(old_file),
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
            storage_path=str(new_file),
            extraction_method="text",
            extracted_text="naujas tekstas",
            extraction_status="ok",
        )
    )
    session.commit()
    session.close()

    removed_count = cleanup_module.cleanup_old_documents()

    assert removed_count == 1
    assert not old_file.exists()
    assert new_file.exists()

    session = TestSession()
    docs = {d.content_hash: d for d in session.query(Document).all()}
    assert docs["old"].storage_path is None
    assert docs["old"].extracted_text == "senas tekstas"  # tekstas NELIEČIAMAS
    assert docs["new"].storage_path == str(new_file)
    session.close()
