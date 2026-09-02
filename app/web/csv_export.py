"""CSV eksportas su UTF-8 BOM, kad korektiškai atsidarytų Excel su lietuviškais
simboliais.
"""

from __future__ import annotations

import csv
import io

from app.models.opportunity import Opportunity

_HEADERS = [
    "ID",
    "Pavadinimas",
    "Organizatorius",
    "Savivaldybė",
    "Būsena",
    "Pardavimo spalva",
    "Paraiškos tinkamumas",
    "Paraiškų terminas",
    "Bendras biudžetas (Eur)",
    "Kitas veiksmas",
    "Pirminis URL",
    "Pirmą kartą aptikta",
]


def opportunities_to_csv(opportunities: list[Opportunity]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(_HEADERS)
    for opp in opportunities:
        writer.writerow(
            [
                opp.id,
                opp.title,
                opp.organizer_name or "",
                opp.municipality or "",
                opp.status,
                opp.sales.color if opp.sales else "",
                opp.eligibility.verdict if opp.eligibility else "",
                opp.application_end.isoformat() if opp.application_end else "nenurodyta",
                f"{opp.total_budget_cents / 100:.2f}" if opp.total_budget_cents else "nenurodyta",
                opp.next_action or "",
                opp.primary_url,
                opp.first_seen_at.date().isoformat(),
            ]
        )
    text = buffer.getvalue()
    return b"\xef\xbb\xbf" + text.encode("utf-8")
