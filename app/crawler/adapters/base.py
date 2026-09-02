from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DiscoveredItem:
    """Vienas kandidatas į Opportunity, rastas šaltinio sąrašo/API puslapyje."""

    title: str
    url: str
    detail_html: str | None = None  # jei jau turime pilną turinį (pvz. API atsakymas)
    published_hint: str | None = None
