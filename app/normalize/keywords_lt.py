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
    "priklausomyb",
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
    "specialist",
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
# "kontekstas svarbiau už raktažodžių skaičių").
#
# SVARBU (2026-09-02 duomenų kokybės auditas, žr. SOURCE_AUDIT.md): ankstesnė versija
# leisdavo tekstą laikyti aktualiu vien dėl ≥3 bendrų/administracinių žodžių KARTU, be
# jokio specifinio signalo. Realiu auditu prieš www.ltkt.lt nustatyta, kad ŠI riba
# beveik NIEKO nefiltruoja — bet kuris finansavimo kvietimas BET KURIA tema (pvz.
# architektūros, dizaino, muziejų konkursai, visiškai nesusiję su jaunimu ar mokymais)
# savaime paminės "konkursas", "kvietimas", "finansavimas", "projektas", "programa" ir
# "partneris" kelis kartus vien todėl, kad tai yra finansavimo kvietimo TEKSTO ŽANRAS,
# o ne jaunimo/mokymų temos signalas. Todėl `is_relevant_candidate` DABAR visada
# reikalauja bent vieno SPECIFINIO (ne administracinio) signalo — vien bendrų žodžių,
# nesvarbu kiek jų, NEPAKANKA.
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
    # "kvalifikacij" (kvalifikacijos kėlimas) pati viena YRA per daug bendra —
    # tai standartinė leidžiamų veiklų/išlaidų kategorija beveik kiekviename
    # finansavimo konkurse BET KURIOJE srityje (pvz. LTKT architektūros ar
    # muzikos konkursuose ji reiškia PAČIŲ pareiškėjų, ne "Mostai" tikslinės
    # auditorijos, profesinį tobulėjimą). Realus rastas atvejis: LTKT
    # architektūros konkurso puslapis (nesusijęs su jaunimu) buvo klaidingai
    # pažymimas aktualiu vien dėl šio žodžio standartiniame veiklų sąraše.
    "kvalifikacij",
    # "specialist" viena pati taip pat per daug bendra — tai standartinis
    # institucijos KONTAKTINIO ASMENS pareigybės pavadinimas ("Vyriausioji
    # specialistė"), esantis beveik KIEKVIENO valstybinės institucijos puslapio
    # kontaktų bloke, nepriklausomai nuo puslapio temos. Realus rastas atvejis:
    # visi LTKT konkursų puslapiai (architektūros, dizaino ir kt., nesusiję su
    # jaunimu) turėjo bendrą kontaktų bloką "Vyriausioji specialistė ... tel. ...",
    # kuris vienas pats klaidingai pažymėdavo puslapį aktualiu.
    "specialist",
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


def is_relevant_candidate(text: str) -> bool:
    """Greitas pirminis filtras: ar tekstą apskritai verta toliau apdoroti.

    Reikalaujamas bent vienas SPECIFINIS (ne vien administracinis) signalas —
    žr. `_GENERIC_ADMINISTRATIVE_STEMS` docstring aukščiau dėl to, kodėl vien
    bendrų administracinių žodžių, nesvarbu kiek jų, NEPAKANKA: kiekvienas
    finansavimo kvietimas bet kuria tema juos paminės vien dėl žanro.
    """
    positives = find_positive_signals(text)
    specific = [p for p in positives if p not in _GENERIC_ADMINISTRATIVE_STEMS]
    return bool(specific)
