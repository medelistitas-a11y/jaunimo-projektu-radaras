"""LTKT (Lietuvos kultūros taryba) lentelės adapterio testai.

Fixture testai naudoja mažus sintetinius HTML failus (tests/fixtures/ltkt_*),
sukurtus šios sesijos metu pagal realaus puslapio struktūrą (patikrinta
rankiniu būdu prieš https://www.ltkt.lt/organizacijoms/konkursai
2026-09-02) — jokių tikrų LTKT duomenų fixture'uose nėra.

Gyvas (live) smoke testas praeina TIK jei tinklas leidžia pasiekti ltkt.lt —
NĖRA privalomas CI aplinkoje (žr. @pytest.mark.live).
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

import app.crawler.http_client as http_client_module
import app.crawler.robots as robots_module
import app.crawler.ssrf_guard as ssrf_guard_module
from app.crawler.adapters.ltkt_table import discover_items
from app.crawler.http_client import PoliteHttpClient
from app.crawler.pipeline import process_candidate
from app.extraction.html_extract import extract_page
from app.models.source import Source

FIXTURES = Path(__file__).parent / "fixtures"


class _FakeRobotsResponse:
    status_code = 404
    text = ""


@pytest.fixture(autouse=True)
def _no_real_robots(monkeypatch):
    monkeypatch.setattr(robots_module.httpx, "get", lambda *a, **k: _FakeRobotsResponse())


@pytest.fixture(autouse=True)
def _fake_public_dns(monkeypatch):
    def fake_getaddrinfo(host, *a, **k):
        return [(2, 1, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr(ssrf_guard_module.socket, "getaddrinfo", fake_getaddrinfo)


def _ltkt_source() -> Source:
    return Source(
        code="test_ltkt",
        name="LTKT testinis",
        institution_name="Lietuvos kultūros taryba",
        official_domain="ltkt.lt",
        start_urls=["https://www.ltkt.lt/organizacijoms/konkursai"],
        source_type="html",
        allowed_document_domains=["ltkt.lt"],
        adapter="ltkt_table",
        status="active",
        enabled=True,
    )


def test_discover_items_parses_table_rows_not_header(monkeypatch):
    table_html = (FIXTURES / "ltkt_table.html").read_text(encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=table_html, headers={"content-type": "text/html"})

    transport = httpx.MockTransport(handler)
    original_client = http_client_module.httpx.Client
    monkeypatch.setattr(
        http_client_module.httpx,
        "Client",
        lambda **kw: original_client(**{**kw, "transport": transport}),
    )

    client = PoliteHttpClient(user_agent="test", allowed_domains=["ltkt.lt"], min_delay_seconds=0.0)
    items = discover_items(client, _ltkt_source())

    assert len(items) == 2
    titles = [i.title for i in items]
    assert any("Architektūra" in t for t in titles)
    assert any("Bendruomenių kultūrinės iniciatyvos" in t for t in titles)
    assert all(i.url.startswith("https://www.ltkt.lt/organizacijoms/konkursai/") for i in items)
    # Antraštės eilutė ("Data"/"Pavadinimas"/...) neturi būti tarp rezultatų.
    assert not any(t == "Data" for t in titles)

    # Regresija: puslapis turi <base href="https://www.ltkt.lt"> ir santykines
    # nuorodas be pradinio "/" (pvz. href="organizacijoms/konkursai/995"), o
    # start_url NETURI baigiamojo "/" ("...konkursai", ne "...konkursai/").
    # Ignoravus <base> ir naudojant urljoin(start_url, href) tiesiogiai, kelio
    # segmentas "organizacijoms" būdavo sudubliuojamas
    # (.../organizacijoms/organizacijoms/konkursai/995) ir nuoroda vesdavo į
    # KITĄ (bendrą, ne konkretaus kvietimo) puslapį — patikrinta realiu HTTP
    # palyginimu prieš www.ltkt.lt 2026-09-02, žr. SOURCE_AUDIT.md.
    urls = {i.url for i in items}
    assert urls == {
        "https://www.ltkt.lt/organizacijoms/konkursai/995",
        "https://www.ltkt.lt/organizacijoms/konkursai/1002",
    }
    assert not any("organizacijoms/organizacijoms" in i.url for i in items)


def test_arts_only_call_is_not_relevant_candidate(db_session):
    """Pagrindinis reikalavimas: vien menų sritis (be jaunimo/mokymų/prevencijos
    signalo) NETURI tapti Opportunity įrašu."""
    html = (FIXTURES / "ltkt_detail_arts_only.html").read_text(encoding="utf-8")
    text = extract_page(html, base_url="https://www.ltkt.lt/organizacijoms/konkursai/995").text

    source = _ltkt_source()
    db_session.add(source)
    db_session.commit()

    result = process_candidate(
        db_session,
        source,
        "Architektūra (Vykstantis kvietimas)",
        "https://www.ltkt.lt/organizacijoms/konkursai/995",
        text,
        [],
    )
    assert result is None  # is_relevant_candidate turėjo atmesti


def test_youth_relevant_community_call_is_processed(db_session):
    html = (FIXTURES / "ltkt_detail_youth_relevant.html").read_text(encoding="utf-8")
    text = extract_page(html, base_url="https://www.ltkt.lt/organizacijoms/konkursai/1002").text

    source = _ltkt_source()
    db_session.add(source)
    db_session.commit()

    result = process_candidate(
        db_session,
        source,
        "Bendruomenių kultūrinės iniciatyvos (Vykstantis kvietimas)",
        "https://www.ltkt.lt/organizacijoms/konkursai/1002",
        text,
        [],
    )
    assert result is not None
    assert result.is_new is True


@pytest.mark.live
def test_live_ltkt_table_is_reachable_and_parseable():
    """Neprivalomas gyvas smoke testas — praleidžiamas, jei nėra tinklo."""
    client = PoliteHttpClient(
        user_agent="MostaiGalimybiuRadaras/0.1-test (+mailto:test@example.lt)",
        allowed_domains=["ltkt.lt"],
        min_delay_seconds=1.0,
    )
    try:
        source = _ltkt_source()
        items = discover_items(client, source)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"ltkt.lt nepasiekiamas šioje aplinkoje: {exc}")
    assert len(items) > 0
