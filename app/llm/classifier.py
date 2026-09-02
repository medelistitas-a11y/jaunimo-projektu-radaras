"""Pasirenkamas LLM klasifikatorius sudėtingesniam paraiškos tinkamumo (A)
vertinimui, naudojant oficialų Anthropic SDK.

Veikia TIK jei `.env` nustatytas ANTHROPIC_API_KEY — priešingu atveju
`classify_eligibility` iškart grąžina None ir kviečiančioji pusė (crawl
pipeline) naudoja tik taisyklių variklio rezultatą. Sistema visada veikia
pilnai be šio modulio.

Griežtos taisyklės:
- Modelio pavadinimas NIEKADA nekoduojamas — visada `settings.llm_model`.
- Siunčiamas tik jau viešai ištrauktas tekstas (jokių papildomų šaltinių),
  apkarpytas iki protingo ilgio, kad ribotume kaštus.
- Atsakymas turi būti struktūrizuotas JSON su PRIVALOMA citata.
- Jei JSON nepavyksta validuoti ARBA citata nerandama pažodžiui originaliame
  tekste, rezultatas atmetamas (grąžinamas "neaisku", niekada TAIP/NE be
  patikrintos citatos) — LLM negali "prigalvoti" faktų.
"""

from __future__ import annotations

import json
import logging

from app.config import Settings
from app.rules.eligibility import EligibilityResult

logger = logging.getLogger("app.llm.classifier")

MAX_INPUT_CHARS = 8000

_VALID_VERDICTS = {"taip", "ne", "su_salygomis", "neaisku"}

_SYSTEM_PROMPT = (
    "Tu esi teisinis/administracinis analitikas, vertinantis, ar mažoji bendrija "
    "(MB) gali teikti paraišką konkrečiame finansavimo konkurse pagal pateiktą teksto "
    "ištrauką. Atsakyk TIK JSON formatu pagal nurodytą schemą, lietuvių kalba "
    "'explanation_lt' ir 'what_to_verify' laukuose. 'evidence_quote' PRIVALO būti "
    "TIKSLI (pažodinė) citata iš pateikto teksto — jei tokios citatos nėra, "
    "'verdict' turi būti 'neaisku' ir 'evidence_quote' turi būti null. Niekada "
    "neišgalvok faktų, kurių nėra pateiktame tekste."
)

_JSON_SCHEMA_HINT = """
Grąžink TIK JSON objektą (be papildomo teksto), tokios formos:
{
  "verdict": "taip" | "ne" | "su_salygomis" | "neaisku",
  "explanation_lt": "trumpas paaiškinimas lietuvių kalba",
  "confidence": 0-100,
  "evidence_quote": "tiksli citata iš teksto arba null",
  "what_to_verify": "ką žmogus turėtų papildomai patikrinti"
}
"""


def _build_prompt(text: str) -> str:
    truncated = text[:MAX_INPUT_CHARS]
    return (
        f"Teksto ištrauka apie finansavimo konkursą:\n\n---\n{truncated}\n---\n\n"
        f"Ar šiame tekste aiškiai nurodyta, kokios teisinės formos organizacijos gali "
        f"teikti paraišką, ir ar mažoji bendrija (MB) tarp jų?\n{_JSON_SCHEMA_HINT}"
    )


def _parse_and_validate(raw_response: str, source_text: str) -> dict | None:
    try:
        data = json.loads(raw_response)
    except json.JSONDecodeError:
        logger.warning("LLM atsakymas nėra validus JSON.")
        return None

    if not isinstance(data, dict):
        return None

    verdict = data.get("verdict")
    if verdict not in _VALID_VERDICTS:
        return None

    quote = data.get("evidence_quote")
    quote_missing_or_unverifiable = (
        not quote or not isinstance(quote, str) or quote.strip() not in source_text
    )
    if verdict in ("taip", "ne") and quote_missing_or_unverifiable:
        # Be pažodinės citatos originaliame tekste negalima TAIP/NE — nuvertinama
        # iki "neaisku", kad LLM negalėtų "prigalvoti" pagrindimo.
        logger.info(
            "LLM pateikė %s be patikrinamos citatos originaliame tekste — nuvertinama iki 'neaisku'.",
            verdict,
        )
        data = {**data, "verdict": "neaisku", "evidence_quote": None}

    confidence = data.get("confidence", 0)
    if not isinstance(confidence, int | float) or confidence < 0 or confidence > 100:
        data["confidence"] = 0

    return data


def classify_eligibility(
    text: str, source_url: str, settings: Settings, client=None
) -> EligibilityResult | None:
    """Grąžina None, jei LLM nesukonfigūruotas, nepasiekiamas arba atsakymas
    nevalidus — kviečiančioji pusė tokiu atveju naudoja taisyklių rezultatą.
    """
    if not settings.llm_configured:
        return None
    if not text or not text.strip():
        return None

    try:
        if client is None:
            import anthropic

            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        response = client.messages.create(
            model=settings.llm_model,
            max_tokens=500,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_prompt(text)}],
        )
        raw_text = response.content[0].text
    except Exception as exc:  # noqa: BLE001 - bet kokia LLM klaida = graceful fallback
        logger.warning("LLM užklausa nepavyko, naudojamas taisyklių rezultatas: %s", exc)
        return None

    validated = _parse_and_validate(raw_text, text)
    if validated is None:
        return None

    return EligibilityResult(
        verdict=validated["verdict"],
        explanation_lt=str(validated.get("explanation_lt", "")),
        confidence=int(validated.get("confidence", 0)),
        evidence_quote=validated.get("evidence_quote"),
        evidence_section=None,
        what_to_verify=str(validated.get("what_to_verify", "")),
        rule_code="llm_classifier",
    )
