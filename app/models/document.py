import datetime as dt

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import TimestampMixin


class CrawledPage(TimestampMixin, Base):
    """Vienas atsiųstas HTML puslapis."""

    __tablename__ = "crawled_pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    url: Mapped[str] = mapped_column(String(2048))
    canonical_url: Mapped[str] = mapped_column(String(2048), index=True)
    fetched_at: Mapped[dt.datetime] = mapped_column(nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    etag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_modified: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_method: Mapped[str] = mapped_column(String(30), default="html")

    documents: Mapped[list["Document"]] = relationship(back_populates="crawled_page")


class Document(TimestampMixin, Base):
    """Priedas (PDF/DOCX/DOC/XLSX). Originalas atskirtas nuo ištraukto teksto."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crawled_page_id: Mapped[int | None] = mapped_column(
        ForeignKey("crawled_pages.id"), nullable=True
    )
    source_url: Mapped[str] = mapped_column(String(2048))
    file_type: Mapped[str] = mapped_column(String(10))  # pdf | docx | doc | xlsx | other
    mime_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    downloaded_at: Mapped[dt.datetime] = mapped_column(nullable=False)
    storage_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    extraction_method: Mapped[str] = mapped_column(String(30), default="text")
    # text | ocr | libreoffice_convert | failed
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_status: Mapped[str] = mapped_column(String(30), default="pending")
    # pending | ok | needs_human_review | failed
    needs_human_review: Mapped[bool] = mapped_column(default=False)
    extra_meta: Mapped[dict] = mapped_column(JSON, default=dict)

    opportunity_id: Mapped[int | None] = mapped_column(
        ForeignKey("opportunities.id"), nullable=True
    )

    crawled_page: Mapped["CrawledPage | None"] = relationship(back_populates="documents")
