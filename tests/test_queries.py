"""Regresijos testas: `color` + `eligibility` filtrų derinys anksčiau sukeldavo
Dekarto sandaugą tarp Opportunity ir EligibilityAssessment (nes JOIN buvo
praleidžiamas, kai `color` jau nustatytas), todėl grąžindavo klaidingus
rezultatus, kai DB turėjo kelis įrašus su skirtingomis spalvomis/verdiktais.
"""

import datetime as dt

from app.models.assessment import EligibilityAssessment, SalesAssessment
from app.models.opportunity import Opportunity
from app.web.queries import apply_filters, base_query


def _make_opportunity(db, idx: int, color: str, verdict: str) -> Opportunity:
    now = dt.datetime.now(dt.UTC)
    opp = Opportunity(
        title=f"Testinė galimybė {idx}",
        status="open",
        topics=[],
        target_groups=[],
        primary_url=f"https://x.lt/{idx}",
        source_urls=[f"https://x.lt/{idx}"],
        document_urls=[],
        canonical_key=f"k{idx}",
        content_hash=f"h{idx}",
        first_seen_at=now,
        last_changed_at=now,
        last_checked_at=now,
    )
    db.add(opp)
    db.flush()
    db.add(
        SalesAssessment(
            opportunity_id=opp.id,
            color=color,
            reason_code="x",
            explanation_lt="x",
            confidence=50,
            signals=[],
            assessed_by="rules",
            assessed_at=now,
        )
    )
    db.add(
        EligibilityAssessment(
            opportunity_id=opp.id,
            verdict=verdict,
            explanation_lt="x",
            confidence=50,
            assessed_by="rules",
            assessed_at=now,
        )
    )
    return opp


def test_color_and_eligibility_filters_combine_correctly(db_session):
    # green+ne turi būti IŠFILTRUOTAS, kai ieškoma green+taip, nes tai skirtingi įrašai.
    _make_opportunity(db_session, 1, "green", "ne")
    _make_opportunity(db_session, 2, "green", "taip")
    _make_opportunity(db_session, 3, "yellow", "taip")
    db_session.commit()

    results = apply_filters(base_query(db_session), color="green", eligibility="taip").all()

    assert [r.title for r in results] == ["Testinė galimybė 2"]


def test_eligibility_filter_alone_still_works(db_session):
    _make_opportunity(db_session, 1, "green", "ne")
    _make_opportunity(db_session, 2, "yellow", "taip")
    db_session.commit()

    results = apply_filters(base_query(db_session), eligibility="taip").all()
    assert [r.title for r in results] == ["Testinė galimybė 2"]
