from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import TimestampMixin


class Organization(TimestampMixin, Base):
    """Institucija / organizatorius / finansuotojas / pareiškėjas / vykdytojas."""

    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(500), index=True)
    org_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    # ministerija | agentura | savivaldybe | vsi | asociacija | mb | biudzetine | nezinoma
    municipality: Mapped[str | None] = mapped_column(String(120), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)

    contacts: Mapped[list["Contact"]] = relationship(back_populates="organization")


class Contact(TimestampMixin, Base):
    """Kontaktinis asmuo, susietas su Opportunity ir/ar Organization."""

    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    opportunity_id: Mapped[int | None] = mapped_column(
        ForeignKey("opportunities.id"), nullable=True
    )
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )

    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    organization_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    phone_raw: Mapped[str | None] = mapped_column(String(60), nullable=True)
    phone_normalized: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_general_contact: Mapped[bool] = mapped_column(default=False)
    # True, jei tai bendras savivaldybės/institucijos telefonas/paštas, o ne konkretaus
    # projekto vadovo/koordinatoriaus kontaktas. Niekada nerodoma kaip "projekto vadovas".

    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    organization: Mapped["Organization | None"] = relationship(back_populates="contacts")
