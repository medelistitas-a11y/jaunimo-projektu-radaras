"""Apdorojimo etapo (processing_status) nustatymas rodymui UI.

SVARBU (2026-09-02 duomenų kokybės auditas, žr. SOURCE_AUDIT.md): rankinis 30
įrašų auditas atskleidė, kad net po raktažodžių filtro pataisymų kai kurie
kandidatai (dažniausiai su vienu silpnu/dviprasmišku raktažodžio kamienu, pvz.
homonimu) vis tiek taps Opportunity įrašais. Užduotis aiškiai reikalauja: "žalias
raktažodžių sutapimas niekada neturi būti rodomas kaip patvirtinta galimybė".
Šis modulis atskiria, ar konkretus Opportunity įrašas turi TIKRĄ, citata
pagrįstą vertinimą, ar tėra silpnas, dar nepatvirtintas kandidatas — NEKURIANT
naujo DB stulpelio (skaičiuojama iš jau egzistuojančių EligibilityAssessment/
SalesAssessment laukų, kad nereikėtų dar vienos schemos migracijos šiame etape).

Trys galimos būsenos (rodomos UI atskirai, žr. app/web/templates/index.html):
- "unprocessed_candidate" ("Neapdoroti kandidatai"): taisyklių variklis NERADO
  JOKIOS citatos pagrindo tinkamumui (EligibilityAssessment.confidence yra
  žemiausiame "nėra jokio signalo" lygyje IR nėra nė vieno Evidence įrašo) —
  tai tik raktažodžių sutapimas, dar realiai neįvertintas.
- "needs_review" ("Reikia žmogaus peržiūros"): yra tam tikras pagrindas, bet
  pasitikėjimas žemas (galimas dublikatas, arba ir tinkamumo, ir pardavimo
  vertinimai yra silpni/numatytieji-atsargūs).
- "confirmed" ("Aktuali galimybė"): pakankamai patikimas vertinimas, rodomas
  pagal įprastą žalia/geltona/raudona spalvą.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.opportunity import Opportunity

UNPROCESSED_CANDIDATE = "unprocessed_candidate"
NEEDS_REVIEW = "needs_review"
CONFIRMED = "confirmed"

# EligibilityAssessment.confidence == _NO_EVIDENCE_CONFIDENCE reiškia
# "assess_eligibility nerado JOKIO citatos pagrindo tekste" (žr.
# app/rules/eligibility.py numatytąją šaką be teksto/be signalo).
_NO_EVIDENCE_CONFIDENCE = 15
# SalesAssessment.confidence == _SALES_DEFAULT_CAUTIOUS_CONFIDENCE reiškia
# "assess_sales numatytoji atsargi geltona šaka" (žr. app/rules/sales.py) —
# joks aiškus signalas nerastas nei žalia, nei raudona kryptimi.
_SALES_DEFAULT_CAUTIOUS_CONFIDENCE = 35
_WEAK_ELIGIBILITY_CONFIDENCE = 20


def compute_processing_status(opp: Opportunity) -> str:
    elig = opp.eligibility
    sales = opp.sales

    if elig is None or sales is None:
        return UNPROCESSED_CANDIDATE

    if not elig.evidence_quote and elig.confidence <= _NO_EVIDENCE_CONFIDENCE and not opp.evidences:
        return UNPROCESSED_CANDIDATE

    if opp.possible_duplicate_of_id is not None:
        return NEEDS_REVIEW

    if sales.confidence <= _SALES_DEFAULT_CAUTIOUS_CONFIDENCE:
        return NEEDS_REVIEW

    if elig.verdict == "neaisku" and elig.confidence < _WEAK_ELIGIBILITY_CONFIDENCE:
        return NEEDS_REVIEW

    return CONFIRMED


PROCESSING_STATUS_LABELS_LT: dict[str, str] = {
    UNPROCESSED_CANDIDATE: "Neapdorotas kandidatas",
    NEEDS_REVIEW: "Reikia žmogaus peržiūros",
    CONFIRMED: "Aktuali galimybė",
}
