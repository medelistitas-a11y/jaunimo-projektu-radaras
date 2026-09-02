"""Sujungia ištraukimą, normalizavimą, taisyklių vertinimą ir DB įrašymą
vienam aptiktam kandidatui (puslapis + jo dokumentai) į Opportunity.

Datų/pinigų laukų priskyrimas konkrečiam Opportunity laukui (paraiškos
terminas vs. veiklos laikotarpis; bendras biudžetas vs. vieno projekto suma)
yra heuristinis — tikslus atskyrimas iš laisvo teksto be LLM yra sudėtinga
NLP užduotis. Kai heuristika nepasitiki (kelios datos/sumos be aiškaus
konteksto), laukas paliekamas NULL su originaliu tekstu `summary`/`nuance_notes`
lauke, o ne spėjama.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re

from sqlalchemy.orm import Session

from app.config import Settings
from app.crawler.dedupe import (
    canonicalize_url,
    find_by_canonical_url,
    find_fuzzy_duplicate,
    make_canonical_key,
)
from app.llm.classifier import classify_eligibility
from app.models.assessment import ChangeEvent, EligibilityAssessment, Evidence, SalesAssessment
from app.models.opportunity import Opportunity
from app.models.organization import Contact
from app.models.source import Source
from app.normalize.contacts_lt import find_emails, find_phones
from app.normalize.dates_lt import find_all_dates
from app.normalize.keywords_lt import find_positive_signals, is_relevant_candidate
from app.normalize.money_lt import find_all_money
from app.rules.call_script import build_call_script
from app.rules.eligibility import assess_eligibility
from app.rules.sales import assess_sales

_NAME_NEAR_PHONE_RE = re.compile(
    r"([A-ZĄČĘĖĮŠŲŪŽ][a-ząčęėįšųūž]+\s+[A-ZĄČĘĖĮŠŲŪŽ][a-ząčęėįšųūž]+)[^.]{0,40}?"
    r"(?:tel\.?|telefon\w*)[^\d]{0,10}"
)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


class ProcessResult:
    def __init__(self, opportunity: Opportunity | None, is_new: bool, is_updated: bool):
        self.opportunity = opportunity
        self.is_new = is_new
        self.is_updated = is_updated


def _choose_deadline(deadlines: list, today: dt.date):
    """Iš kelių tekste rastų "iki <data>" terminų pirmenybę teikia ANKSČIAUSIAM
    dar NEPRAĖJUSIAM (>= šiandien) terminui, o ne tiesiog absoliučiai
    ankstyviausiai datai. SVARBU (2026-09-02 duomenų kokybės auditas, žr.
    SOURCE_AUDIT.md): realiu auditu rastas atvejis, kai puslapio tekste yra ir
    SENA, jau praėjusi data (pvz. kito susijusio dokumento/nuostatų PATVIRTINIMO
    data, ne paraiškų terminas) IR reali, būsima paraiškų priėmimo data — aklas
    min() rinkdavosi seną, jau praėjusią datą, nes ji skaitmeniškai mažesnė.
    """
    future = [d for d in deadlines if d.start >= today]
    if future:
        return min(future, key=lambda d: d.start)
    return min(deadlines, key=lambda d: d.start)


def _pick_dates(text: str, now: dt.date, primary_text: str | None = None) -> dict:
    """`primary_text` (jei duotas) yra PATIES puslapio tekstas, be prijungtų
    dokumentų. SVARBU (2026-09-02 duomenų kokybės auditas, žr. SOURCE_AUDIT.md):
    realiu auditu nustatyta, kad prie kelių skirtingų skelbimų prijungtas TAS
    PATS bendrinis šablono dokumentas (pvz. bendra paraiškos forma) kartais
    turi savo, VISIŠKAI NESUSIJUSIĄ "iki <data>" frazę (pvz. formos galiojimo
    ar pavyzdinę datą), kuri, imant tiesiog min() iš VISŲ rastų terminų
    (puslapis+dokumentai), klaidingai NUSTELBDAVO teisingą, straipsnio TEKSTE
    esantį terminą (pvz. "iki kovo 26 d." → 2026-03-26, teisinga; bet
    bendriniame dokumente rasta "iki 2025-05-18" laimėdavo kaip min()).
    Todėl PIRMENYBĖ visada teikiama terminui, rastam PAČIAME puslapyje —
    prie dokumentų tekste rastas terminas naudojamas TIK jei puslapyje jo
    apskritai nėra.
    """
    if primary_text:
        primary_deadlines = [
            p for p in find_all_dates(primary_text, reference_year=now.year) if p.is_deadline
        ]
        if primary_deadlines:
            chosen = _choose_deadline(primary_deadlines, now)
            parsed = find_all_dates(text, reference_year=now.year)
            ranges = [p for p in parsed if p.end is not None]
            activity_start = ranges[0].start if ranges else None
            activity_end = ranges[0].end if ranges else None
            return {
                "application_end": chosen.start,
                "application_end_raw": chosen.raw,
                "activity_start": activity_start,
                "activity_end": activity_end,
                "published_at": None,
                "raw": [p.raw for p in primary_deadlines] + [p.raw for p in parsed],
            }

    parsed = find_all_dates(text, reference_year=now.year)
    application_end = None
    application_end_raw = None
    activity_start = None
    activity_end = None
    published_at = None

    deadlines = [p for p in parsed if p.is_deadline]
    ranges = [p for p in parsed if p.end is not None]
    singles = [p for p in parsed if not p.is_deadline and p.end is None]

    if deadlines:
        # SVARBU: `application_end_raw` VISADA turi atitikti TĄ PAČIĄ datą, kuri
        # buvo pasirinkta kaip `application_end` — anksčiau čia (žr. process_candidate)
        # buvo naudojamas tiesiog dates["raw"][0], t. y. PIRMA rasta data VISAME
        # tekste, kuri dažnai NESUTAPDAVO su realiai pasirinktu min() terminu
        # (rodydavo, pvz., nesusijusią 2023 m. datą kaip "raw" tekstą prie 2026 m.
        # pasirinkto termino). Žr. SOURCE_AUDIT.md duomenų kokybės auditą.
        chosen = _choose_deadline(deadlines, now)
        application_end = chosen.start
        application_end_raw = chosen.raw
    if ranges:
        activity_start = ranges[0].start
        activity_end = ranges[0].end
    if not application_end and singles:
        # Jei tik viena data be aiškaus "iki" žymens ir be intervalo — laikome
        # tikėtina paskelbimo/termino data, bet nepriskiriame automatiškai kaip
        # application_end, nebent tai vienintelė rasta data (žemas pasitikėjimas).
        published_at = singles[0].start

    return {
        "application_end": application_end,
        "application_end_raw": application_end_raw,
        "activity_start": activity_start,
        "activity_end": activity_end,
        "published_at": published_at,
        "raw": [p.raw for p in parsed],
    }


def _pick_money(text: str) -> dict:
    parsed = find_all_money(text)
    if not parsed:
        return {"total_budget_cents": None, "max_grant_cents": None, "raw": None}
    if len(parsed) == 1:
        return {
            "total_budget_cents": parsed[0].amount_cents,
            "max_grant_cents": None,
            "raw": parsed[0].raw,
        }
    # Kelios sumos: didžiausia laikoma bendru biudžetu, mažesnė - vieno projekto suma.
    amounts = sorted(parsed, key=lambda p: p.amount_cents, reverse=True)
    return {
        "total_budget_cents": amounts[0].amount_cents,
        "max_grant_cents": amounts[-1].amount_cents if len(amounts) > 1 else None,
        "raw": ", ".join(p.raw for p in parsed),
    }


def _extract_contacts(text: str, source_url: str) -> list[dict]:
    contacts: list[dict] = []
    phones = [p for p in find_phones(text) if p.normalized]
    emails = find_emails(text)

    used_emails = set()
    for phone in phones:
        idx = text.find(phone.raw)
        window = text[max(0, idx - 60) : idx]
        name_match = _NAME_NEAR_PHONE_RE.search(window + text[idx : idx + 5])
        name = name_match.group(1) if name_match else None
        nearby_email = None
        for email in emails:
            if email not in used_emails and (
                abs(text.find(email) - idx) < 150 or text.find(email) == -1
            ):
                nearby_email = email
                used_emails.add(email)
                break
        contacts.append(
            {
                "full_name": name,
                "phone_raw": phone.raw,
                "phone_normalized": phone.normalized,
                "email": nearby_email,
                "is_general_contact": name is None,
                "source_url": source_url,
            }
        )

    for email in emails:
        if email in used_emails:
            continue
        contacts.append(
            {
                "full_name": None,
                "phone_raw": None,
                "phone_normalized": None,
                "email": email,
                "is_general_contact": True,
                "source_url": source_url,
            }
        )

    return contacts


def process_candidate(
    db: Session,
    source: Source,
    title: str,
    url: str,
    text: str,
    document_urls: list[str],
    now: dt.datetime | None = None,
    settings: Settings | None = None,
    page_text: str | None = None,
) -> ProcessResult | None:
    """`page_text`, jei duotas, yra TIK paties puslapio (be prijungtų dokumentų)
    ištrauktas tekstas — `text` yra puslapis + visų prijungtų dokumentų tekstas
    kartu. SVARBU (2026-09-02 duomenų kokybės auditas, žr. SOURCE_AUDIT.md):
    aktualumo sprendimas (is_relevant_candidate) DABAR visada priimamas TIK
    pagal `page_text` (jei jis duotas), NE pagal pilną `text`. Realiu auditu
    prieš www.ltkt.lt ir skuodas.lt nustatyta, kad prie DAUGELIO skirtingų,
    tarpusavyje nesusijusių skelbimų prijungti TIE PATYS bendriniai dokumentai
    (pvz. bendri vertinimo kriterijų aprašai, bendros paraiškų formos), kurių
    standartinė kalba (pvz. "socialinė nauda", "specialistų kompetencija")
    klaidingai pažymėdavo VISIŠKAI nesusijusius skelbimus (architektūros,
    žemės ūkio finansavimo ir kt.) aktualiais. Dokumentų tekstas TOLIAU
    naudojamas datų/pinigų/tinkamumo citatų IŠTRAUKIMUI jau priimtiems
    kandidatams — tik NE pačiam aktualumo sprendimui.
    """
    now = now or dt.datetime.now(dt.UTC)
    today = now.date()

    relevance_text = page_text if page_text else text
    if not is_relevant_candidate(relevance_text):
        return None

    dates = _pick_dates(text, today, primary_text=page_text)
    money = _pick_money(text)
    contacts_data = _extract_contacts(text, url)
    has_contact = any(c["phone_normalized"] or c["email"] for c in contacts_data)

    hash_value = content_hash(text)
    canon_url = canonicalize_url(url)
    canon_key = make_canonical_key(title, source.municipality)

    existing = find_by_canonical_url(db, canon_url)
    is_new = False
    is_updated = False
    possible_duplicate_id = None

    if existing is None:
        duplicate = find_fuzzy_duplicate(db, title, source.municipality)
        if duplicate is not None:
            possible_duplicate_id = duplicate.id

        opp = Opportunity(
            title=title[:500],
            organizer_name=source.institution_name,
            municipality=source.municipality,
            topics=[],
            target_groups=[],
            summary=text[:1000],
            application_end=dates["application_end"],
            application_end_raw=dates["application_end_raw"],
            activity_start=dates["activity_start"],
            activity_end=dates["activity_end"],
            published_at=dates["published_at"],
            total_budget_cents=money["total_budget_cents"],
            max_grant_cents=money["max_grant_cents"],
            total_budget_raw=money["raw"],
            status="unclear",
            primary_url=url,
            source_urls=[url],
            document_urls=document_urls,
            canonical_key=canon_key,
            content_hash=hash_value,
            first_seen_at=now,
            last_changed_at=now,
            last_checked_at=now,
            possible_duplicate_of_id=possible_duplicate_id,
        )
        db.add(opp)
        db.flush()
        is_new = True
        db.add(
            ChangeEvent(
                opportunity_id=opp.id,
                event_type="created",
                description=f"Nauja galimybė aptikta šaltinyje {source.name}.",
                diff={},
                occurred_at=now,
            )
        )
    else:
        opp = existing
        opp.last_checked_at = now
        if url not in opp.source_urls:
            opp.source_urls = [*opp.source_urls, url]
        merged_docs = list(dict.fromkeys([*opp.document_urls, *document_urls]))
        opp.document_urls = merged_docs

        if opp.content_hash != hash_value:
            is_updated = True
            old_hash = opp.content_hash
            opp.content_hash = hash_value
            opp.summary = text[:1000]
            opp.last_changed_at = now
            if dates["application_end"]:
                opp.application_end = dates["application_end"]
                opp.application_end_raw = dates["application_end_raw"]
            if money["total_budget_cents"]:
                opp.total_budget_cents = money["total_budget_cents"]
            db.add(
                ChangeEvent(
                    opportunity_id=opp.id,
                    event_type="content_changed",
                    description="Turinys pasikeitė nuo paskutinio patikrinimo.",
                    diff={"old_hash": old_hash, "new_hash": hash_value},
                    occurred_at=now,
                )
            )

    # --- Vertinimai (visada perskaičiuojami, kad atspindėtų naujausią tekstą) ---
    elig = assess_eligibility(text, source_url=url)
    if elig.verdict == "neaisku" and settings is not None and settings.llm_configured:
        # Taisyklių variklis nerado aiškaus atsakymo — pasirenkamas LLM klasifikatorius
        # (jei sukonfigūruotas) gali padėti, bet TIK jei jo atsakymas praeina citatos
        # patikrą (žr. app/llm/classifier.py). Sistema visada veikia be šio žingsnio.
        llm_result = classify_eligibility(text, source_url=url, settings=settings)
        if llm_result is not None and llm_result.verdict != "neaisku":
            elig = llm_result
    sales = assess_sales(
        text=text,
        eligibility_verdict=elig.verdict,
        application_end=opp.application_end,
        activity_end=opp.activity_end,
        has_contact=has_contact,
        has_training_budget=bool(money["total_budget_cents"]),
        today=today,
    )

    opp.next_action = sales.explanation_lt
    opp.status = _infer_status(opp, today)
    opp.topics = find_positive_signals(text)[:8]
    opp.call_script = build_call_script(
        institution_name=source.institution_name,
        project_title=title,
        full_text=text,
        is_already_funded=opp.status == "funded_ongoing",
    )

    elig_assessed_by = "llm" if elig.rule_code == "llm_classifier" else "rules"

    if opp.eligibility is None:
        db.add(
            EligibilityAssessment(
                opportunity_id=opp.id,
                verdict=elig.verdict,
                explanation_lt=elig.explanation_lt,
                confidence=elig.confidence,
                evidence_quote=elig.evidence_quote,
                evidence_url=url,
                evidence_section=elig.evidence_section,
                what_to_verify=elig.what_to_verify,
                rule_code=elig.rule_code,
                assessed_by=elig_assessed_by,
                assessed_at=now,
            )
        )
    else:
        opp.eligibility.verdict = elig.verdict
        opp.eligibility.explanation_lt = elig.explanation_lt
        opp.eligibility.confidence = elig.confidence
        opp.eligibility.evidence_quote = elig.evidence_quote
        opp.eligibility.evidence_url = url
        opp.eligibility.rule_code = elig.rule_code
        opp.eligibility.assessed_by = elig_assessed_by
        opp.eligibility.assessed_at = now

    if opp.sales is None:
        db.add(
            SalesAssessment(
                opportunity_id=opp.id,
                color=sales.color,
                reason_code=sales.reason_code,
                explanation_lt=sales.explanation_lt,
                confidence=sales.confidence,
                signals=sales.signals,
                assessed_by="rules",
                assessed_at=now,
            )
        )
    else:
        prev_color = opp.sales.color
        opp.sales.color = sales.color
        opp.sales.reason_code = sales.reason_code
        opp.sales.explanation_lt = sales.explanation_lt
        opp.sales.confidence = sales.confidence
        opp.sales.signals = sales.signals
        opp.sales.assessed_at = now
        if prev_color != sales.color:
            db.add(
                ChangeEvent(
                    opportunity_id=opp.id,
                    event_type="assessment_changed",
                    description=f"Pardavimo spalva pasikeitė: {prev_color} -> {sales.color}.",
                    diff={"old_color": prev_color, "new_color": sales.color},
                    occurred_at=now,
                )
            )

    if elig.evidence_quote:
        db.add(
            Evidence(
                opportunity_id=opp.id,
                quote=elig.evidence_quote,
                source_url=url,
                section_title=elig.evidence_section,
                used_for="eligibility",
            )
        )

    for c in contacts_data:
        db.add(
            Contact(
                opportunity_id=opp.id,
                full_name=c["full_name"],
                organization_name=source.institution_name,
                phone_raw=c["phone_raw"],
                phone_normalized=c["phone_normalized"],
                email=c["email"],
                is_general_contact=c["is_general_contact"],
                source_url=c["source_url"],
            )
        )

    db.flush()
    return ProcessResult(opportunity=opp, is_new=is_new, is_updated=is_updated)


def _infer_status(opp: Opportunity, today: dt.date) -> str:
    if opp.application_end and opp.application_end < today:
        if opp.activity_end and opp.activity_end < today:
            return "finished"
        return "funded_ongoing"
    if opp.application_end and opp.application_end >= today:
        return "open"
    if opp.activity_start and opp.activity_start > today:
        return "planned"
    return "unclear"
