"""Aktualumo raktažodžiai: lietuviškų žodžių kamienai, ne tikslūs sutapimai.

Naudojama pirminiam kandidatų filtravimui (ar puslapį/dokumentą apskritai verta
toliau analizuoti) ir kaip vienas iš pardavimo/tinkamumo vertinimo signalų.
Kontekstas visada svarbesnis už vien raktažodžių skaičių — šis modulis tik
suranda signalus, GALUTINĮ sprendimą priima app/rules/*.
"""

from __future__ import annotations

import re

POSITIVE_STEMS: list[str] = [
    "jaunim", "paaugl", "vaik", "šeim",
    "jaunimo darbuotoj", "su jaunimu dirban", "specialist", "pedagog", "socialin",
    "mokym", "seminar", "dirbtuv", "kompetenc", "kvalifikacij", "superviz", "konsultacij",
    "psichikos sveikat", "emoc", "savižudyb", "smurt", "patyč", "kriz", "atsparum",
    "psichoaktyv", "narkot", "alkohol", "tabak", "priklausom", "prevenc",
    "neformal", "įtraukt", "bendruomen", "savanor", "mobilusis darbas", "darbas gatvėje",
    "atvirasis jaunimo centras", "atviroji jaunimo erdvė",
    "veiklų vykdytoj", "paslaugų teikėj", "lektor", "ekspert", "partner",
    "konkurs", "kvietim", "finansavim", "projekt", "program", "pirkim",
]

NEGATIVE_HINTS: list[str] = [
    "infrastruktūros statyb", "kelio remont", "statybos darb",
    "sporto inventoriaus įsigijim", "sporto inventorius",
    "stipendij",  # individualioms stipendijoms, ne paslaugoms
]


def _stem_pattern(stem: str) -> re.Pattern:
    escaped = re.escape(stem)
    return re.compile(escaped, re.IGNORECASE)


_POSITIVE_PATTERNS = [(s, _stem_pattern(s)) for s in POSITIVE_STEMS]
_NEGATIVE_PATTERNS = [(s, _stem_pattern(s)) for s in NEGATIVE_HINTS]


def find_positive_signals(text: str) -> list[str]:
    if not text:
        return []
    return [stem for stem, pattern in _POSITIVE_PATTERNS if pattern.search(text)]


def find_negative_signals(text: str) -> list[str]:
    if not text:
        return []
    return [stem for stem, pattern in _NEGATIVE_PATTERNS if pattern.search(text)]


def is_relevant_candidate(text: str, min_positive_signals: int = 1) -> bool:
    """Greitas pirminis filtras: ar tekstą apskritai verta toliau apdoroti."""
    positives = find_positive_signals(text)
    return len(positives) >= min_positive_signals
