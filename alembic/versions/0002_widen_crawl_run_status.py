"""widen crawl_runs.status column

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-02

Rastas realiu bandymu prieš tikrą PostgreSQL: crawl_runs.status buvo
VARCHAR(20), bet reikšmė "completed_with_errors" turi 22 simbolius, todėl
PostgreSQL metė StringDataRightTruncation klaidą (SQLite šio apribojimo
netikrina, todėl klaida nebuvo pastebėta testuose su SQLite).
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "crawl_runs",
        "status",
        existing_type=sa.String(length=20),
        type_=sa.String(length=40),
    )


def downgrade() -> None:
    op.alter_column(
        "crawl_runs",
        "status",
        existing_type=sa.String(length=40),
        type_=sa.String(length=20),
    )
