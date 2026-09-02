"""A vertinimas: ar MB "Mostai" pati gali teikti paraišką.

Griežta taisyklė: TAIP arba NE galima grąžinti TIK jei radome citatą (konkretų
teksto sakinį apie tinkamus pareiškėjus). Priešingu atveju — visada NEAISKU.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.rules.config import (
    NEGATION_WORDS,
    OPEN_ELIGIBILITY_MARKERS,
    PARTNERSHIP_MARKERS,
    RESTRICTED_APPLICANT_TYPES,
    RESTRICTIVE_LANGUAGE,
    VENDOR_ROLE_MARKERS,
)

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")


@dataclass
class EligibilityResult:
    verdict: str  # taip | ne | su_salygomis | neaisku
    explanation_lt: str
    confidence: int
    evidence_quote: str | None
    evidence_section: str | None
    what_to_verify: str
    rule_code: str


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]


def _contains_any(text: str, markers: list[str]) -> list[str]:
    lower = text.lower()
    return [m for m in markers if m.lower() in lower]


def _find_eligibility_sentences(text: str) -> list[str]:
    sentences = _split_sentences(text)
    hits = []
    for s in sentences:
        low = s.lower()
        if ("paraišk" in low or "pareiškėj" in low) and (
            "teikti" in low or "teikėj" in low or "gali" in low
        ):
            hits.append(s)
    return hits


def assess_eligibility(
    text: str,
    source_url: str,
    section_title: str | None = None,
) -> EligibilityResult:
    if not text or not text.strip():
        return EligibilityResult(
            verdict="neaisku",
            explanation_lt=(
                "Dokumento teksto nepavyko gauti arba jis tuščias, todėl negalima "
                "įvertinti, ar MB „Mostai“ gali teikti paraišką."
            ),
            confidence=0,
            evidence_quote=None,
            evidence_section=section_title,
            what_to_verify="Rasti ir perskaityti pilną kvietimo/konkurso dokumentą.",
            rule_code="no_text",
        )

    candidate_sentences = _find_eligibility_sentences(text)

    if not candidate_sentences:
        return EligibilityResult(
            verdict="neaisku",
            explanation_lt=(
                "Tekste nerasta aiškaus teiginio apie tai, kas gali teikti paraišką "
                "šiame konkurse. Be citatos negalima pateikti TAIP/NE išvados."
            ),
            confidence=15,
            evidence_quote=None,
            evidence_section=section_title,
            what_to_verify=(
                "Rasti konkurso nuostatus arba kvietimo sąlygas ir patikrinti pareiškėjų "
                "tinkamumo skyrių."
            ),
            rule_code="no_eligibility_sentence",
        )

    # Vertiname visus kandidatinius sakinius, atsižvelgdami į neigimo žodžius (pvz.
    # "mažosios bendrijos ... paraiškų teikti NEGALI" — atviro tinkamumo žodis
    # "mažoji bendrija" čia iš tikrųjų yra NEIGIAMAS signalas, ne teigiamas).
    found_open: str | None = None
    found_negated_open: str | None = None
    found_restricted: str | None = None
    found_partnership: str | None = None

    for s in candidate_sentences:
        open_hits = _contains_any(s, OPEN_ELIGIBILITY_MARKERS)
        negation_hits = _contains_any(s, NEGATION_WORDS)
        if open_hits and negation_hits:
            if found_negated_open is None:
                found_negated_open = s
        elif open_hits:
            if found_open is None:
                found_open = s

        restricted_hits = _contains_any(s, RESTRICTED_APPLICANT_TYPES)
        restrictive_lang = _contains_any(s, RESTRICTIVE_LANGUAGE)
        if restricted_hits and restrictive_lang and found_restricted is None:
            found_restricted = s

        partnership_hits = _contains_any(s, PARTNERSHIP_MARKERS)
        if partnership_hits and found_partnership is None:
            found_partnership = s

    vendor_markers = _contains_any(text, VENDOR_ROLE_MARKERS)

    if found_open:
        best_sentence = found_open
        return EligibilityResult(
            verdict="taip",
            explanation_lt=(
                "Dokumente aiškiai nurodyta, kad paraiškas gali teikti privatūs juridiniai "
                "asmenys arba visi juridiniai asmenys neatsižvelgiant į teisinę formą — "
                "tai apima ir MB „Mostai“."
            ),
            confidence=80,
            evidence_quote=best_sentence,
            evidence_section=section_title,
            what_to_verify=(
                "Patikrinti, ar nėra papildomų sąlygų (veiklos srities, patirties, teritorijos) "
                "kituose dokumento skyriuose."
            ),
            rule_code="open_eligibility",
        )

    if found_negated_open or found_restricted:
        best_sentence = found_negated_open or found_restricted
        restricted_markers_final = _contains_any(best_sentence, RESTRICTED_APPLICANT_TYPES)
        if restricted_markers_final:
            reason = f"tik {', '.join(restricted_markers_final)} tipo organizacijos"
        else:
            reason = "juridiniai asmenys, kuriems mažoji bendrija nepriklauso"
        explanation = (
            f"Dokumente nurodyta, kad paraiškas gali teikti {reason}. MB „Mostai“ (mažoji "
            "bendrija) šiai grupei nepriklauso, todėl pati paraiškos teikti negali."
        )
        if vendor_markers:
            explanation += (
                " Tačiau dokumente minima galimybė pasitelkti išorinius paslaugų teikėjus — "
                "tai gali reikšti pardavimo galimybę (žr. B vertinimą), net jei paraiškos "
                "teikti negalima."
            )
        return EligibilityResult(
            verdict="ne",
            explanation_lt=explanation,
            confidence=75,
            evidence_quote=best_sentence,
            evidence_section=section_title,
            what_to_verify=(
                "Patikrinti, ar galimas partnerystės arba paslaugų teikėjo variantas kituose "
                "dokumento skyriuose."
            ),
            rule_code="restricted_applicant_types",
        )

    if found_partnership:
        return EligibilityResult(
            verdict="su_salygomis",
            explanation_lt=(
                "Dokumente minima galimybė dalyvauti tik kaip partneriui arba su papildomomis "
                "sąlygomis. MB „Mostai“ pati (be partnerio) tikriausiai paraiškos teikti negali, "
                "bet gali dalyvauti kaip partnerė ar paslaugų teikėja."
            ),
            confidence=55,
            evidence_quote=found_partnership,
            evidence_section=section_title,
            what_to_verify="Patikrinti tikslias partnerystės sąlygas ir reikalavimus partneriui.",
            rule_code="partnership_required",
        )

    return EligibilityResult(
        verdict="neaisku",
        explanation_lt=(
            "Rastas su pareiškėjais susijęs sakinys, bet jis nepakankamai aiškus, kad būtų "
            "galima vienareikšmiškai nustatyti, ar MB „Mostai“ gali teikti paraišką."
        ),
        confidence=30,
        evidence_quote=candidate_sentences[0],
        evidence_section=section_title,
        what_to_verify="Perskaityti pilną pareiškėjų tinkamumo skyrių dokumente.",
        rule_code="ambiguous_sentence",
    )
