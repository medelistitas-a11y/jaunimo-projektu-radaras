"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-02

Šis pradinis migracijos failas naudoja SQLAlchemy modelių metaduomenis
(``Base.metadata``), kad sukurtų visas lenteles vienu žingsniu — tai leidžia
laikyti vieną tiesos šaltinį (app/models/*.py) tiek SQLite (testams), tiek
PostgreSQL (Docker/produkcija) aplinkose be dviejų atskirų schemų priežiūros.
Būsimi schemos pakeitimai turėtų būti pridedami kaip atskiros, įprastos
Alembic migracijos su explicit op.* komandomis.
"""

from alembic import op

from app.db import Base
from app.models import *  # noqa: F401,F403

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
