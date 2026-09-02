"""Lietuviškų datų atpažinimas iš laisvo teksto.

Palaiko:
- Skaitmenines datas: 2026-09-15, 2026.09.15, 2026 09 15
- Žodines datas su lietuvišku mėnesio vardu (kilmininko linksniu): "rugsėjo 15 d.",
  "2026 m. rugsėjo 15 d.", "iki rugsėjo 15 d."
- Datų intervalus tame pačiame mėnesyje: "2026 m. rugsėjo 2–15 d.", "rugsėjo 2-15 d."

Visada grąžina originalų teksto fragmentą kartu su normalizuota reikšme — niekada
neišgalvojame trūkstamų metų be pagrindo (naudojamas `reference_year`, jei metai
tekste nenurodyti; jei ir jo nėra, laikoma dabartiniais kalendoriniais metais).
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass

LT_MONTHS = {
    "sausio": 1,
    "vasario": 2,
    "kovo": 3,
    "balandžio": 4,
    "gegužės": 5,
    "birželio": 6,
    "liepos": 7,
    "rugpjūčio": 8,
    "rugsėjo": 9,
    "spalio": 10,
    "lapkričio": 11,
    "gruodžio": 12,
}

_MONTH_ALT = "|".join(LT_MONTHS.keys())

_RANGE_RE = re.compile(
    rf"(?:(?P<year>\d{{4}})\s*m\.?\s*)?"
    rf"(?P<month>{_MONTH_ALT})\s+"
    rf"(?P<day1>\d{{1,2}})\s*[–\-]\s*(?P<day2>\d{{1,2}})\s*"
    rf"d?\.?",
    re.IGNORECASE,
)

_SINGLE_WORD_RE = re.compile(
    rf"(?P<until>iki\s+)?"
    rf"(?:(?P<year>\d{{4}})\s*m\.?\s*)?"
    rf"(?P<month>{_MONTH_ALT})\s+"
    rf"(?P<day>\d{{1,2}})\s*"
    rf"d?\.?",
    re.IGNORECASE,
)

_NUMERIC_RE = re.compile(
    r"(?P<until>iki\s+)?(?P<year>\d{4})[-.](?P<month>\d{1,2})[-.](?P<day>\d{1,2})"
)


@dataclass
class ParsedDate:
    raw: str
    start: dt.date
    end: dt.date | None = None
    is_deadline: bool = False  # tekste buvo "iki ..."

    @property
    def normalized(self) -> dt.date:
        """Vienai reikšmei: intervalo atveju grąžina pabaigos datą (svarbiausia terminui)."""
        return self.end or self.start


def _safe_date(year: int, month: int, day: int) -> dt.date | None:
    try:
        return dt.date(year, month, day)
    except ValueError:
        return None


def parse_first_date(text: str, reference_year: int | None = None) -> ParsedDate | None:
    """Randa pirmą atpažįstamą datą/intervalą tekste. Grąžina None, jei nerasta."""
    if not text:
        return None
    ref_year = reference_year or dt.date.today().year

    m = _NUMERIC_RE.search(text)
    if m:
        year = int(m.group("year"))
        month = int(m.group("month"))
        day = int(m.group("day"))
        d = _safe_date(year, month, day)
        if d:
            return ParsedDate(raw=m.group(0), start=d, is_deadline=bool(m.group("until")))

    m = _RANGE_RE.search(text)
    if m:
        year = int(m.group("year")) if m.group("year") else ref_year
        month = LT_MONTHS[m.group("month").lower()]
        day1 = int(m.group("day1"))
        day2 = int(m.group("day2"))
        d1 = _safe_date(year, month, day1)
        d2 = _safe_date(year, month, day2)
        if d1 and d2:
            return ParsedDate(raw=m.group(0), start=d1, end=d2)

    m = _SINGLE_WORD_RE.search(text)
    if m:
        year = int(m.group("year")) if m.group("year") else ref_year
        month = LT_MONTHS[m.group("month").lower()]
        day = int(m.group("day"))
        d = _safe_date(year, month, day)
        if d:
            return ParsedDate(raw=m.group(0), start=d, is_deadline=bool(m.group("until")))

    return None


def find_all_dates(text: str, reference_year: int | None = None) -> list[ParsedDate]:
    """Randa visas datas tekste (naudinga, kai reikia atskirti kelis laukus vienoje pastraipoje)."""
    results: list[ParsedDate] = []
    if not text:
        return results
    ref_year = reference_year or dt.date.today().year

    consumed = [False] * len(text)

    def mark(span: tuple[int, int]) -> None:
        for i in range(*span):
            consumed[i] = True

    for m in _NUMERIC_RE.finditer(text):
        year, month, day = int(m.group("year")), int(m.group("month")), int(m.group("day"))
        d = _safe_date(year, month, day)
        if d:
            results.append(ParsedDate(raw=m.group(0), start=d, is_deadline=bool(m.group("until"))))
            mark(m.span())

    for m in _RANGE_RE.finditer(text):
        if any(consumed[m.start() : m.end()]):
            continue
        year = int(m.group("year")) if m.group("year") else ref_year
        month = LT_MONTHS[m.group("month").lower()]
        d1 = _safe_date(year, month, int(m.group("day1")))
        d2 = _safe_date(year, month, int(m.group("day2")))
        if d1 and d2:
            results.append(ParsedDate(raw=m.group(0), start=d1, end=d2))
            mark(m.span())

    for m in _SINGLE_WORD_RE.finditer(text):
        if any(consumed[m.start() : m.end()]):
            continue
        year = int(m.group("year")) if m.group("year") else ref_year
        month = LT_MONTHS[m.group("month").lower()]
        d = _safe_date(year, month, int(m.group("day")))
        if d:
            results.append(ParsedDate(raw=m.group(0), start=d, is_deadline=bool(m.group("until"))))
            mark(m.span())

    results.sort(key=lambda r: text.index(r.raw))
    return results
