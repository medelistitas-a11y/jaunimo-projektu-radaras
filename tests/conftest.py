import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.db import Base
from app.models import *  # noqa: F401,F403 register all models


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def test_settings():
    return Settings(
        database_url="sqlite+pysqlite:///:memory:",
        crawler_user_agent="MostaiGalimybiuRadaras/0.1-test (+mailto:test@example.lt)",
        crawler_min_delay_seconds=0.0,
        crawler_request_timeout_seconds=5,
        crawler_max_retries=1,
        ocr_enabled=False,
    )
