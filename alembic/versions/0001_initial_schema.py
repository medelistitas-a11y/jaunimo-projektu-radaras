"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-02

Šis pradinis migracijos failas naudoja SQLAlchemy modelių metaduomenis
(``Base.metadata``), kad sukurtų visas lenteles vienu žingsniu — tai leidžia
laikyti vieną tiesos šaltinį (app/models/*.py) tiek SQLite (testams), tiek
PostgreSQL (Docker/produkcija) aplinkose be dviejų atskirų schemų priežiūros.

SVARBI PASTABA (2026-09-02): iš pradžių čia buvo pridėtos dvi atskiros
explicit migracijos (0002, 0003) tolesniems schemos pakeitimams. Jos buvo
SUJUNGTOS atgal į šį failą, nes paaiškėjo reali problema — kadangi šis
failas skaito GYVĄ ``Base.metadata`` migracijos VEIKIMO metu (ne užšaldytą
istorinę schemą), bet koks naujas modelio laukas automatiškai atsiranda ir
ČIA, todėl atskira vėlesnė migracija, bandanti pridėti TĄ PATĮ lauką, gauna
"duplicate column" klaidą. Kadangi ši programa dar nepaskelbta produkcijoje
(nėra realios DB, priklausančios nuo istorinės migracijų sekos), saugu ir
teisinga sujungti schemą atgal į vieną pradinį failą. PO PIRMO REALAUS
PRODUKCINIO PALEIDIMO šis sprendimas nebebus tinkamas — nuo to momento
kiekvienas schemos pakeitimas TURI būti atskira migracija su explicit
``op.*`` komandomis (idealiausia — sugeneruota ``alembic revision
--autogenerate`` ir rankiniu būdu patikrinta), o šis failas daugiau
NEBEKEIČIAMAS.
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
