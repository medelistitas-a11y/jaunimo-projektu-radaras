"""Regresijos testai duomenų kokybės auditui (2026-09-02, žr. SOURCE_AUDIT.md).

Rankinis 30 iš 83 tuo metu esančių įrašų auditas (proporcinga imtis iš visų 3
veikiančių šaltinių, palyginus su realiu šaltinio puslapiu) atskleidė du atskirus,
konkrečiais realiais atvejais patvirtintus klaidų šaltinius:

1. Prie DAUGELIO skirtingų, tarpusavyje nesusijusių skelbimų buvo prijungti TIE
   PATYS bendriniai dokumentai (pvz. LTKT bendri vertinimo kriterijų aprašai,
   skuodas.lt bendros paraiškų formos), kurių standartinė kalba klaidingai
   pažymėdavo VISIŠKAI nesusijusius skelbimus (architektūros, žemės ūkio
   finansavimo ir kt.) aktualiais "Mostai" jaunimo mokymų verslui.
2. Ta pati bendrinio dokumento tarša klaidingai perrašydavo TEISINGĄ, straipsnio
   tekste esantį paraiškos terminą bendriniame dokumente rastu, visiškai
   nesusijusiu terminu (pvz. "iki kovo 26 d." → teisingai 2026-03-26, bet
   pasirinkta neteisinga "iki 2025-05-18" iš bendrinio priedo).

Šie testai patikrina PATAISYTĄ elgesį: `process_candidate` dabar priima
`page_text` parametrą (TIK paties puslapio tekstas, be dokumentų) ir naudoja
JĮ tiek aktualumo sprendimui, tiek datos pasirinkimo pirmenybei.
"""

import datetime as dt

from app.crawler.pipeline import process_candidate
from app.models.source import Source
from app.rules.processing_status import (
    CONFIRMED,
    NEEDS_REVIEW,
    UNPROCESSED_CANDIDATE,
    compute_processing_status,
)


def _source() -> Source:
    return Source(
        code="test_dq_source",
        name="Testinis šaltinis",
        institution_name="Testinė institucija",
        municipality="Testinė sav.",
        official_domain="testine.lt",
        start_urls=["https://testine.lt/"],
        source_type="html",
        adapter="generic_html",
        status="active",
        enabled=True,
    )


def test_irrelevant_page_not_made_relevant_by_attached_generic_document(db_session):
    """Realus atvejis: LTKT architektūros konkurso puslapis (jokio jaunimo/mokymų
    signalo savo tekste) NETURI tapti Opportunity vien todėl, kad prie jo
    prijungtas bendrinis vertinimo kriterijų dokumentas mini "socialinė nauda"
    ir "specialistų kompetencija"."""
    page_text = (
        "Architektūra: pastatų architektūra, urbanistika, kraštovaizdžio architektūra. "
        "Finansuojamos profesionaliosios kūrybos veiklos. Kūryba, sklaida Lietuvoje ir "
        "užsienyje. Kvietimo vykstančio nuo liepos 7 d. iki rugsėjo 9 d. metu vienas "
        "juridinis asmuo gali pateikti ne daugiau nei 5-ias projekto paraiškas."
    )
    generic_attached_document_text = (
        "Vertinimo kriterijai: projekto socialinė nauda ir aktualumas (0-20 balų). "
        "Turite klausimų? Kreipkitės! Dovilė Miliukštė, vyriausioji specialistė."
    )
    full_text = page_text + "\n\n" + generic_attached_document_text

    source = _source()
    db_session.add(source)
    db_session.commit()

    result = process_candidate(
        db_session,
        source,
        "Architektūra (Vykstantis kvietimas)",
        "https://testine.lt/architektura",
        full_text,
        [],
        page_text=page_text,
    )
    assert result is None


def test_relevant_page_with_generic_attached_document_still_accepted(db_session):
    """Kontrolinis atvejis: kai PATS puslapis turi realų jaunimo/mokymų signalą,
    kandidatas priimamas nepriklausomai nuo to, kad taip pat prijungtas bendrinis
    dokumentas."""
    page_text = (
        "Kviečiame teikti paraiškas jaunimo darbuotojų mokymų konkursui. "
        "Finansavimas skiriamas neformaliojo ugdymo veikloms su paaugliais."
    )
    generic_attached_document_text = (
        "Turite klausimų? Kreipkitės! Dovilė Miliukštė, vyriausioji specialistė."
    )
    full_text = page_text + "\n\n" + generic_attached_document_text

    source = _source()
    db_session.add(source)
    db_session.commit()

    result = process_candidate(
        db_session,
        source,
        "Jaunimo mokymų konkursas",
        "https://testine.lt/jaunimo-mokymai",
        full_text,
        [],
        page_text=page_text,
    )
    assert result is not None
    assert result.is_new is True


def test_deadline_from_page_text_wins_over_bogus_date_in_attached_document(db_session):
    """Realus atvejis: puslapio tekste teisingas terminas "iki kovo 26 d.", bet
    prie jo prijungtame bendriniame dokumente (naudojamame DAUGELYJE kitų,
    nesusijusių skelbimų) yra visiškai nesusijusi "iki 2025-05-18" data — anksčiau
    min() logika klaidingai pasirinkdavo pastarąją."""
    page_text = (
        "Kviečiame teikti paraiškas jaunimo sporto projektų finansavimo konkursui. "
        "Paraiškas galima teikti iki kovo 26 d. Kontaktai: tel. 8 686 12345."
    )
    generic_attached_document_text = "Ši forma galioja iki 2025-05-18."
    full_text = page_text + "\n\n" + generic_attached_document_text

    source = _source()
    db_session.add(source)
    db_session.commit()

    now = dt.datetime(2026, 1, 15, tzinfo=dt.UTC)
    result = process_candidate(
        db_session,
        source,
        "Sporto projektų konkursas",
        "https://testine.lt/sportas",
        full_text,
        [],
        page_text=page_text,
        now=now,
    )
    assert result is not None
    assert result.opportunity.application_end == dt.date(2026, 3, 26)


def test_application_end_raw_matches_the_chosen_application_end(db_session):
    """Realus atvejis: puslapyje yra DVI "iki"-tipo datos — sena (jau praėjusi,
    2023 m., susijusi su kito dokumento patvirtinimo data) ir reali būsima
    (2026 m.). Anksčiau `application_end_raw` būdavo tiesiog PIRMA rasta data
    VISAME tekste (dates["raw"][0]), kuri galėjo NESUTAPTI su realiai pasirinktu
    min() terminu — UI rodydavo, pvz., "2023 m. liepos 17 d." kaip termino
    tekstą prie teisingai apskaičiuotos 2026 m. datos. Dabar `application_end_raw`
    visada atitinka TĄ PAČIĄ datą, kuri tapo `application_end`."""
    page_text = (
        "DĖL jaunimo ir vyresnio amžiaus žmonių nevyriausybinių organizacijų "
        "projektų atrankos konkurso nuostatų patvirtinimo, priimta iki 2023 m. "
        "liepos 17 d. Paraiškas konkursui teikti galima iki 2026 m. lapkričio 3 d."
    )
    source = _source()
    db_session.add(source)
    db_session.commit()

    now = dt.datetime(2026, 1, 15, tzinfo=dt.UTC)
    result = process_candidate(
        db_session,
        source,
        "Jaunimo NVO projektų konkursas",
        "https://testine.lt/jaunimo-nvo-konkursas",
        page_text,
        [],
        page_text=page_text,
        now=now,
    )
    assert result is not None
    opp = result.opportunity
    assert opp.application_end == dt.date(2026, 11, 3)
    assert "2026" in opp.application_end_raw
    assert "2023" not in opp.application_end_raw


def test_process_candidate_without_page_text_keeps_old_combined_behavior(db_session):
    """Atgalinio suderinamumo patikra: kai `page_text` NEDUOTAS (pvz. senesnis
    iškvietimas), elgesys nepasikeičia — sprendimas priimamas pagal `text`."""
    text = (
        "Kviečiame teikti paraiškas jaunimo darbuotojų mokymų konkursui. "
        "Paraiškas galima teikti iki kovo 26 d."
    )
    source = _source()
    db_session.add(source)
    db_session.commit()

    now = dt.datetime(2026, 1, 15, tzinfo=dt.UTC)
    result = process_candidate(
        db_session,
        source,
        "Jaunimo mokymų konkursas",
        "https://testine.lt/be-page-text",
        text,
        [],
        now=now,
    )
    assert result is not None
    assert result.opportunity.application_end == dt.date(2026, 3, 26)


class _FakeEligibility:
    def __init__(self, verdict="neaisku", confidence=15, evidence_quote=None):
        self.verdict = verdict
        self.confidence = confidence
        self.evidence_quote = evidence_quote


class _FakeSales:
    def __init__(self, confidence=55):
        self.confidence = confidence


class _FakeOpportunity:
    def __init__(self, eligibility=None, sales=None, evidences=None, possible_duplicate_of_id=None):
        self.eligibility = eligibility
        self.sales = sales
        self.evidences = evidences or []
        self.possible_duplicate_of_id = possible_duplicate_of_id


def test_processing_status_unprocessed_when_no_citation_basis_at_all():
    """Realus atvejis: kaunas.lt bendro naujienų srauto straipsniai (pvz. apie
    darželio atidarymą), kuriuos aptiko silpnas vieno žodžio raktažodžio
    sutapimas ("vaik") — taisyklių variklis NERADO jokios citatos, tad tai TIK
    neapdorotas kandidatas, ne patvirtinta galimybė."""
    opp = _FakeOpportunity(
        eligibility=_FakeEligibility(verdict="neaisku", confidence=15, evidence_quote=None),
        sales=_FakeSales(confidence=55),
        evidences=[],
    )
    assert compute_processing_status(opp) == UNPROCESSED_CANDIDATE


def test_processing_status_needs_review_when_duplicate_flagged():
    opp = _FakeOpportunity(
        eligibility=_FakeEligibility(verdict="taip", confidence=80, evidence_quote="x"),
        sales=_FakeSales(confidence=80),
        evidences=["ev"],
        possible_duplicate_of_id=42,
    )
    assert compute_processing_status(opp) == NEEDS_REVIEW


def test_processing_status_needs_review_when_sales_is_default_cautious():
    """Realus atvejis: "jau paskelbti rezultatai" straipsnis, kuriam pardavimo
    variklis grąžino žemiausio pasitikėjimo (35) atsargią numatytąją geltoną —
    tai signalas žmogui peržiūrėti, ne rodyti kaip patvirtintą."""
    opp = _FakeOpportunity(
        eligibility=_FakeEligibility(verdict="neaisku", confidence=30, evidence_quote="x"),
        sales=_FakeSales(confidence=35),
        evidences=["ev"],
    )
    assert compute_processing_status(opp) == NEEDS_REVIEW


def test_processing_status_confirmed_with_real_evidence_and_confidence():
    opp = _FakeOpportunity(
        eligibility=_FakeEligibility(verdict="ne", confidence=75, evidence_quote="x"),
        sales=_FakeSales(confidence=55),
        evidences=["ev"],
    )
    assert compute_processing_status(opp) == CONFIRMED
