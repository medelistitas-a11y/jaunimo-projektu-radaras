"""Lietuviškų pinigų sumų atpažinimas iš laisvo teksto.

Palaiko:
- "10 000 Eur", "10000 EUR", "10.000,50 Eur" (grupavimo tarpai/taškai)
- "iki 5 tūkst. eurų", "5 tūkst. Eur", "2 mln. Eur"
- Grąžina centus (int), kad išvengtume float apvalinimo klaidų, + originalų tekstą.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_MULTIPLIERS = {
    "tūkst": 1_000,
    "tukst": 1_000,
    "t.": 1_000,
    "mln": 1_000_000,
    "milijon": 1_000_000,
}

_CURRENCY_RE = r"(?:eur\w*|€)"

# "10 000 Eur", "10.000,50 Eur", "1500 Eur"
_PLAIN_RE = re.compile(
    rf"(?P<until>iki\s+)?"
    rf"(?P<num>\d{{1,3}}(?:[.\s]\d{{3}})*(?:,\d{{1,2}})?|\d+(?:,\d{{1,2}})?)"
    rf"\s*(?P<mult>tūkst\.?|tukst\.?|mln\.?|milijon\w*)?"
    rf"\s*{_CURRENCY_RE}\b",
    re.IGNORECASE,
)


@dataclass
class ParsedMoney:
    raw: str
    amount_cents: int
    is_upper_bound: bool = False  # tekste buvo "iki ..."

    @property
    def amount(self) -> float:
        return self.amount_cents / 100


def _multiplier(token: str | None) -> int:
    if not token:
        return 1
    token = token.lower().rstrip(".")
    for key, val in _MULTIPLIERS.items():
        if token.startswith(key.rstrip(".")):
            return val
    return 1


def _parse_number(raw: str) -> float:
    """Palaiko '10 000', '10.000', '10,50', '10.000,50' formatus."""
    raw = raw.strip()
    if "," in raw:
        integer_part, _, frac_part = raw.rpartition(",")
        integer_part = integer_part.replace(".", "").replace(" ", "")
        return float(f"{integer_part}.{frac_part}")
    raw = raw.replace(".", "").replace(" ", "")
    return float(raw)


def parse_first_money(text: str) -> ParsedMoney | None:
    if not text:
        return None
    m = _PLAIN_RE.search(text)
    if not m:
        return None
    number = _parse_number(m.group("num"))
    mult = _multiplier(m.group("mult"))
    amount = number * mult
    cents = round(amount * 100)
    return ParsedMoney(
        raw=m.group(0).strip(), amount_cents=cents, is_upper_bound=bool(m.group("until"))
    )


def find_all_money(text: str) -> list[ParsedMoney]:
    results = []
    if not text:
        return results
    for m in _PLAIN_RE.finditer(text):
        number = _parse_number(m.group("num"))
        mult = _multiplier(m.group("mult"))
        amount = number * mult
        cents = round(amount * 100)
        results.append(
            ParsedMoney(
                raw=m.group(0).strip(),
                amount_cents=cents,
                is_upper_bound=bool(m.group("until")),
            )
        )
    return results
