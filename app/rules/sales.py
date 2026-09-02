"""B vertinimas: ar dabar racionalu skambinti ir siūlyti MB "Mostai" mokymus.

Šviesoforo spalva pirmiausia atspindi PARDAVIMO veiksmą, ne vien paraiškos
tinkamumą. Svarbi taisyklė: eligibility_verdict == "ne" NIEKADA savaime
nepadaro spalvos raudonos — MB negalėjimas teikti paraiškos yra atskiras
klausimas nuo to, ar verta skambinti ir siūlyti mokymus.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from app.normalize.keywords_lt import find_negative_signals, find_positive_signals
from app.rules.config import (
    ACCREDITATION_MARKERS,
    BUNDLED_LOGISTICS_MARKERS,
    DEADLINE_PASSED_HINTS,
    PARTNERSHIP_MARKERS,
    PROCUREMENT_MARKERS,
    SALES_REASON_DESCRIPTIONS,
    TRAINING_FIT_MARKERS,
)


@dataclass
class SalesResult:
    color: str  # green | yellow | red
    reason_code: str
    explanation_lt: str
    confidence: int
    signals: list[str]


def _contains_any(text: str, markers: list[str]) -> list[str]:
    low = text.lower()
    return [m for m in markers if m.lower() in low]


def assess_sales(
    text: str,
    eligibility_verdict: str,
    application_end: dt.date | None,
    activity_end: dt.date | None,
    has_contact: bool,
    has_training_budget: bool,
    today: dt.date | None = None,
) -> SalesResult:
    today = today or dt.date.today()
    signals: list[str] = []

    positive_kw = find_positive_signals(text)
    negative_kw = find_negative_signals(text)
    training_fit = _contains_any(text, TRAINING_FIT_MARKERS)
    deadline_hint = _contains_any(text, DEADLINE_PASSED_HINTS)
    procurement_hint = _contains_any(text, PROCUREMENT_MARKERS)
    accreditation_hint = _contains_any(text, ACCREDITATION_MARKERS)
    logistics_hint = _contains_any(text, BUNDLED_LOGISTICS_MARKERS)
    partnership_hint = _contains_any(text, PARTNERSHIP_MARKERS)

    signals.extend(f"pozityvus:{k}" for k in positive_kw)
    signals.extend(f"neigiamas:{k}" for k in negative_kw)

    deadline_passed = bool(application_end and application_end < today)
    activity_passed = bool(activity_end and activity_end < today)
    # "explicitly_finished" frazės (pvz. "rezultatai paskelbti") laikomos patikimu signalu
    # TIK jei jos neprieštarauja jau nustatytam ateities terminui — pavienis žodis "pasibaigė"
    # tekste dažnai reiškia bendrą būsimą sąlygą ("veiklos turi pasibaigti iki..."), o ne tai,
    # kad ŠIS konkursas jau praėjęs.
    future_deadline_known = bool(application_end and application_end >= today)
    explicitly_finished = bool(deadline_hint) and not future_deadline_known

    # --- 1. RAUDONA ---
    if explicitly_finished or (deadline_passed and activity_passed):
        return SalesResult(
            color="red",
            reason_code="deadline_passed",
            explanation_lt=(
                "Terminas ir realus paslaugų pirkimo laikotarpis jau pasibaigęs, todėl "
                "kontaktavimas šiuo metu neaktualus."
            ),
            confidence=80,
            signals=signals,
        )

    if not training_fit and not positive_kw:
        return SalesResult(
            color="red",
            reason_code="not_relevant",
            explanation_lt=(
                "Turinyje nerasta jokių signalų, susijusių su mokymais, jaunimu ar "
                "„Mostai“ paslaugomis — kontaktavimas neturėtų komercinės vertės."
            ),
            confidence=70,
            signals=signals,
        )

    if negative_kw and not training_fit:
        return SalesResult(
            color="red",
            reason_code="no_commercial_value",
            explanation_lt=(
                "Numatytos tik kitokio pobūdžio išlaidos (pvz. infrastruktūra, inventorius, "
                "stipendijos) ir nėra matomo realaus mokymų ar konsultavimo poreikio."
            ),
            confidence=65,
            signals=signals,
        )

    # --- 2. GELTONA sąlygos ---
    yellow_reason = None
    if partnership_hint or eligibility_verdict == "su_salygomis":
        yellow_reason = "needs_partner_or_condition"
    elif procurement_hint:
        yellow_reason = "needs_procurement"
    elif accreditation_hint:
        yellow_reason = "needs_accreditation_or_registration"
    elif logistics_hint:
        yellow_reason = "bundled_logistics"
    elif not has_training_budget and not training_fit:
        yellow_reason = "unclear_purchase_window"

    if yellow_reason:
        signals.append(f"gelton_signalas:{yellow_reason}")
        return SalesResult(
            color="yellow",
            reason_code=yellow_reason,
            explanation_lt=SALES_REASON_DESCRIPTIONS[yellow_reason],
            confidence=55,
            signals=signals,
        )

    # --- 3. ŽALIA sąlygos ---
    if training_fit and has_contact and not deadline_passed:
        return SalesResult(
            color="green",
            reason_code="concrete_opportunity_with_contact",
            explanation_lt=SALES_REASON_DESCRIPTIONS["concrete_opportunity_with_contact"],
            confidence=80,
            signals=signals,
        )

    if training_fit and not has_contact and not deadline_passed:
        return SalesResult(
            color="yellow",
            reason_code="concrete_opportunity_needs_contact_search",
            explanation_lt=SALES_REASON_DESCRIPTIONS["concrete_opportunity_needs_contact_search"],
            confidence=50,
            signals=signals,
        )

    # --- 4. Numatytoji (atsargi) — geltona ---
    return SalesResult(
        color="yellow",
        reason_code="unclear_purchase_window",
        explanation_lt=SALES_REASON_DESCRIPTIONS["unclear_purchase_window"],
        confidence=35,
        signals=signals,
    )
