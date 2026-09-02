"""Aktualumo raktažodžiai: lietuviškų žodžių kamienai, ne tikslūs sutapimai.

Naudojama pirminiam kandidatų filtravimui (ar puslapį/dokumentą apskritai verta
toliau analizuoti) ir kaip vienas iš pardavimo/tinkamumo vertinimo signalų.
Kontekstas visada svarbesnis už vien raktažodžių skaičių — šis modulis tik
suranda signalus, GALUTINĮ sprendimą priima app/rules/*.
"""

from __future__ import annotations

import re

POSITIVE_STEMS: list[str] = [
    "jaunim",
    "paaugl",
    "vaik",
    "šeim",
    "jaunimo darbuotoj",
    "su jaunimu dirban",
    "specialist",
    "pedagog",
    "socialin",
    "mokym",
    "seminar",
    "dirbtuv",
    "kompetenc",
    "kvalifikacij",
    "superviz",
    "konsultacij",
    "psichikos sveikat",
    "emoc",
    "savižudyb",
    "smurt",
    "patyč",
    "kriz",
    "atsparum",
    "psichoaktyv",
    "narkot",
    "alkohol",
    "tabak",
    "priklausom",
    "prevenc",
    "neformal",
    "įtraukt",
    "bendruomen",
    "savanor",
    "mobilusis darbas",
    "darbas gatvėje",
    "atvirasis jaunimo centras",
    "atviroji jaunimo erdvė",
    "veiklų vykdytoj",
    "paslaugų teikėj",
    "lektor",
    "ekspert",
    "partner",
    "konkurs",
    "kvietim",
    "finansavim",
    "projekt",
    "program",
    "pirkim",
]

# Bendri/administraciniai žodžiai (konkurs*, kvietim*, finansavim*, projekt*, program*,
# pirkim*, partner*, bendruomen*, ekspert*, lektor*, savanor*, veiklų vykdytoj*,
# paslaugų teikėj*) yra privalomi pagal užduoties raktažodžių sąrašą, BET pasitaiko
# beveik KIEKVIENAME savivaldybės naujienų sraute (pvz. straipsniuose apie
# infrastruktūros projektus, viešuosius pirkimus, kultūros renginius), taigi vieno
# tokio žodžio PAKAKTI negali, kad tekstas būtų laikomas aktualiu (žr. instrukcijos
# "kontekstas svarbiau už raktažodžių skaičių"). `is_relevant_candidate` todėl reikalauja
# arba bent vieno signalo iš siauresnio, jaunimo/mokymų temai specifinio poaibio, arba
# kelių bendrų signalų kartu — o ne vien atsitiktinio bendro žodžio.
_GENERIC_ADMINISTRATIVE_STEMS: set[str] = {
    "konkurs",
    "kvietim",
    "finansavim",
    "projekt",
    "program",
    "pirkim",
    "partner",
    "bendruomen",
    "ekspert",
    "lektor",
    "savanor",
    "veiklų vykdytoj",
    "paslaugų teikėj",
    "įtraukt",
}

NEGATIVE_HINTS: list[str] = [
    "infrastruktūros statyb",
    "kelio remont",
    "statybos darb",
    "sporto inventoriaus įsigijim",
    "sporto inventorius",
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


def is_relevant_candidate(text: str, min_generic_only_signals: int = 3) -> bool:
    """Greitas pirminis filtras: ar tekstą apskritai verta toliau apdoroti.

    Vieno specifinio (ne vien administracinio) signalo pakanka. Vien bendrų/
    administracinių žodžių (žr. `_GENERIC_ADMINISTRATIVE_STEMS`) reikia bent
    `min_generic_only_signals`, kad sumažintume klaidingų teigiamų atvejų
    (pvz. bendrų savivaldybės naujienų apie infrastruktūros pirkimus).
    """
    positives = find_positive_signals(text)
    specific = [p for p in positives if p not in _GENERIC_ADMINISTRATIVE_STEMS]
    if specific:
        return True
    return len(positives) >= min_generic_only_signals
