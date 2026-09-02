"""Lietuvos telefono numerių ir el. pašto adresų atpažinimas/normalizavimas."""

from __future__ import annotations

import re
from dataclasses import dataclass

import phonenumbers

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

# Galimi LT telefonų formatai tekste: +370 6XX XXXXX, 8 6XX XXXXX, 8-6XX-XXXXX,
# (8 5) 2XX XXXX (miesto), 8 700 XXXXX
_PHONE_CANDIDATE_RE = re.compile(
    r"(?:\+370|8)[\s\-]?\(?\d{1,3}\)?[\s\-]?\d{2,3}[\s\-]?\d{2,3}[\s\-]?\d{0,3}"
)


@dataclass
class ParsedPhone:
    raw: str
    normalized: str | None  # E.164, pvz. +37061234567; None jei nepavyko normalizuoti


def normalize_phone(raw: str) -> ParsedPhone:
    candidate = raw.strip()
    digits_only = re.sub(r"[^\d+]", "", candidate)
    try_variants = [digits_only]
    if digits_only.startswith("8") and not digits_only.startswith("+"):
        try_variants.append("+370" + digits_only[1:])
    if not digits_only.startswith("+"):
        try_variants.append("+" + digits_only)

    for variant in try_variants:
        try:
            parsed = phonenumbers.parse(variant, "LT")
            if phonenumbers.is_valid_number(parsed):
                return ParsedPhone(
                    raw=raw,
                    normalized=phonenumbers.format_number(
                        parsed, phonenumbers.PhoneNumberFormat.E164
                    ),
                )
        except phonenumbers.NumberParseException:
            continue
    return ParsedPhone(raw=raw, normalized=None)


def find_phones(text: str) -> list[ParsedPhone]:
    if not text:
        return []
    results = []
    for m in _PHONE_CANDIDATE_RE.finditer(text):
        results.append(normalize_phone(m.group(0)))
    return results


def find_emails(text: str) -> list[str]:
    if not text:
        return []
    return list(dict.fromkeys(_EMAIL_RE.findall(text)))
