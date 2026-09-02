"""Patikrina, kad crawl pipeline naudoja LLM klasifikatorių TIK kai taisyklių
variklis grąžina "neaisku" IR jis sukonfigūruotas, ir kad rezultatas
pažymimas assessed_by="llm".
"""

import app.crawler.pipeline as pipeline_module
from app.config import Settings
from app.crawler.pipeline import process_candidate
from app.models.source import Source
from app.rules.eligibility import EligibilityResult

AMBIGUOUS_TEXT = (
    "Skelbiamas jaunimo mokymų konkursas. Kviečiame teikti paraiškas. "
    "Finansavimas iki 10 000 Eur. Kontaktai: tel. 8 686 12345."
)


def _source() -> Source:
    return Source(
        code="test_llm_source",
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


def test_llm_not_called_when_not_configured(db_session, monkeypatch):
    called = {"n": 0}

    def fake_classify(*args, **kwargs):
        called["n"] += 1
        return None

    monkeypatch.setattr(pipeline_module, "classify_eligibility", fake_classify)

    source = _source()
    db_session.add(source)
    db_session.commit()

    settings = Settings(anthropic_api_key="")  # nesukonfigūruotas
    result = process_candidate(
        db_session,
        source,
        "Mokymų konkursas",
        "https://testine.lt/1",
        AMBIGUOUS_TEXT,
        [],
        settings=settings,
    )
    db_session.commit()

    assert called["n"] == 0
    assert result.opportunity.eligibility.assessed_by == "rules"


def test_llm_upgrades_ambiguous_verdict_when_configured(db_session, monkeypatch):
    def fake_classify(text, source_url, settings, client=None):
        return EligibilityResult(
            verdict="taip",
            explanation_lt="LLM: aiškiai leidžiama.",
            confidence=90,
            evidence_quote="Kviečiame teikti paraiškas.",
            evidence_section=None,
            what_to_verify="x",
            rule_code="llm_classifier",
        )

    monkeypatch.setattr(pipeline_module, "classify_eligibility", fake_classify)

    source = _source()
    db_session.add(source)
    db_session.commit()

    settings = Settings(anthropic_api_key="sk-fake", llm_model="claude-sonnet-5")
    result = process_candidate(
        db_session,
        source,
        "Mokymų konkursas",
        "https://testine.lt/2",
        AMBIGUOUS_TEXT,
        [],
        settings=settings,
    )
    db_session.commit()

    assert result.opportunity.eligibility.verdict == "taip"
    assert result.opportunity.eligibility.assessed_by == "llm"


def test_llm_ignored_when_it_also_returns_neaisku(db_session, monkeypatch):
    def fake_classify(text, source_url, settings, client=None):
        return EligibilityResult(
            verdict="neaisku",
            explanation_lt="LLM taip pat neaišku.",
            confidence=20,
            evidence_quote=None,
            evidence_section=None,
            what_to_verify="x",
            rule_code="llm_classifier",
        )

    monkeypatch.setattr(pipeline_module, "classify_eligibility", fake_classify)

    source = _source()
    db_session.add(source)
    db_session.commit()

    settings = Settings(anthropic_api_key="sk-fake", llm_model="claude-sonnet-5")
    result = process_candidate(
        db_session,
        source,
        "Mokymų konkursas",
        "https://testine.lt/3",
        AMBIGUOUS_TEXT,
        [],
        settings=settings,
    )
    db_session.commit()

    # Rezultatas lieka taisyklių variklio "neaisku", assessed_by="rules" (LLM neįrodė nieko naujo).
    assert result.opportunity.eligibility.verdict == "neaisku"
    assert result.opportunity.eligibility.assessed_by == "rules"
