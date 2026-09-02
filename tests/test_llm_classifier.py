"""Testai naudoja fake Anthropic klientą (jokių tikrų API užklausų) — tikrina
struktūrizuoto JSON validavimą ir, svarbiausia, kad be pažodinės citatos
originaliame tekste NIEKADA negrąžinamas TAIP/NE.
"""

import json

from app.config import Settings
from app.llm.classifier import classify_eligibility

SOURCE_TEXT = (
    "Paraiškas gali teikti visi juridiniai asmenys, neatsižvelgiant į teisinę formą. "
    "Finansavimas iki 10 000 Eur."
)


class _FakeContentBlock:
    def __init__(self, text: str):
        self.text = text


class _FakeMessage:
    def __init__(self, text: str):
        self.content = [_FakeContentBlock(text)]


class _FakeAnthropicClient:
    def __init__(self, response_text: str):
        self._response_text = response_text
        self.messages = self

    def create(self, **kwargs):
        return _FakeMessage(self._response_text)


class _RaisingClient:
    def __init__(self):
        self.messages = self

    def create(self, **kwargs):
        raise RuntimeError("simuliuota tinklo/API klaida")


def _settings_with_key() -> Settings:
    return Settings(anthropic_api_key="sk-test-fake", llm_model="claude-sonnet-5")


def test_returns_none_when_not_configured():
    settings = Settings(anthropic_api_key="")
    result = classify_eligibility(SOURCE_TEXT, "https://x.lt", settings, client=object())
    assert result is None


def test_valid_response_with_real_quote_is_accepted():
    payload = json.dumps(
        {
            "verdict": "taip",
            "explanation_lt": "Aiškiai leidžiama visiems juridiniams asmenims.",
            "confidence": 85,
            "evidence_quote": "Paraiškas gali teikti visi juridiniai asmenys, neatsižvelgiant į teisinę formą.",
            "what_to_verify": "Patikrinti papildomus reikalavimus.",
        }
    )
    client = _FakeAnthropicClient(payload)
    result = classify_eligibility(SOURCE_TEXT, "https://x.lt", _settings_with_key(), client=client)
    assert result is not None
    assert result.verdict == "taip"
    assert result.rule_code == "llm_classifier"
    assert result.evidence_quote in SOURCE_TEXT


def test_taip_without_matching_quote_is_downgraded_to_neaisku():
    payload = json.dumps(
        {
            "verdict": "taip",
            "explanation_lt": "Tariamai leidžiama.",
            "confidence": 90,
            "evidence_quote": "Šios citatos tekste NĖRA.",
            "what_to_verify": "x",
        }
    )
    client = _FakeAnthropicClient(payload)
    result = classify_eligibility(SOURCE_TEXT, "https://x.lt", _settings_with_key(), client=client)
    assert result is not None
    assert result.verdict == "neaisku"
    assert result.evidence_quote is None


def test_invalid_json_returns_none():
    client = _FakeAnthropicClient("Tai NĖRA json.")
    result = classify_eligibility(SOURCE_TEXT, "https://x.lt", _settings_with_key(), client=client)
    assert result is None


def test_invalid_verdict_value_returns_none():
    payload = json.dumps({"verdict": "galbut", "confidence": 10})
    client = _FakeAnthropicClient(payload)
    result = classify_eligibility(SOURCE_TEXT, "https://x.lt", _settings_with_key(), client=client)
    assert result is None


def test_api_exception_returns_none_not_raises():
    result = classify_eligibility(
        SOURCE_TEXT, "https://x.lt", _settings_with_key(), client=_RaisingClient()
    )
    assert result is None


def test_empty_text_returns_none():
    result = classify_eligibility("", "https://x.lt", _settings_with_key(), client=object())
    assert result is None
