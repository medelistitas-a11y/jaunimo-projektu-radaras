from pathlib import Path

import httpx
import pytest

import app.crawler.http_client as http_client_module
import app.crawler.robots as robots_module
import app.crawler.ssrf_guard as ssrf_guard_module
from app.crawler.runner import run_crawl
from app.models.opportunity import Opportunity
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
    """SSRF guard tikrina DNS rezoliuciją — testuose naudojame išgalvotus
    .lt domenus, todėl imituojame, kad jie rezoliuoja į viešą IP adresą.
    """

    def fake_getaddrinfo(host, *args, **kwargs):
        if "neveikiantis" in host:
            raise OSError("simuliuota DNS klaida testui")
        return [(2, 1, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr(ssrf_guard_module.socket, "getaddrinfo", fake_getaddrinfo)


def _mock_transport() -> httpx.MockTransport:
    list_html = (FIXTURES / "list_page.html").read_text(encoding="utf-8")
    detail_html = (FIXTURES / "detail_page.html").read_text(encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/naujienos/") or path.endswith("/naujienos"):
            return httpx.Response(200, text=list_html, headers={"content-type": "text/html"})
        if "jaunimo-mokymu-konkursas" in path:
            return httpx.Response(200, text=detail_html, headers={"content-type": "text/html"})
        if "eismo-remontas" in path:
            return httpx.Response(
                200,
                text="<html><body><main><p>Vyks eismo remonto darbai.</p></main></body></html>",
                headers={"content-type": "text/html"},
            )
        return httpx.Response(404, text="not found")

    return httpx.MockTransport(handler)


@pytest.fixture(autouse=True)
def _patch_http_client_transport(monkeypatch):
    transport = _mock_transport()
    original_client = http_client_module.httpx.Client

    def fake_client(**kwargs):
        kwargs["transport"] = transport
        return original_client(**kwargs)

    monkeypatch.setattr(http_client_module.httpx, "Client", fake_client)


def _make_html_source() -> Source:
    return Source(
        code="test_muni_naujienos",
        name="Testinė savivaldybė naujienos",
        institution_name="Testinė savivaldybė",
        municipality="Testinė sav.",
        official_domain="testine-savivaldybe.lt",
        start_urls=["https://testine-savivaldybe.lt/naujienos/"],
        source_type="html",
        allowed_document_domains=["testine-savivaldybe.lt"],
        adapter="generic_html",
        adapter_config={"list_item_selector": "article", "link_selector": "h2 a, a"},
        status="active",
        enabled=True,
    )


def _make_broken_source() -> Source:
    return Source(
        code="test_broken_source",
        name="Sugedęs šaltinis",
        institution_name="Nežinoma institucija",
        official_domain="neveikiantis-domenas.lt",
        start_urls=["https://neveikiantis-domenas.lt/konkursai/"],
        source_type="html",
        allowed_document_domains=["neveikiantis-domenas.lt"],
        adapter="generic_html",
        status="active",
        enabled=True,
    )


def test_run_crawl_creates_opportunity_from_relevant_item(db_session, test_settings):
    db_session.add(_make_html_source())
    db_session.commit()

    run = run_crawl(db_session, test_settings, trigger="manual")

    assert run.status in ("completed", "completed_with_errors")
    assert run.sources_total == 1
    assert run.sources_ok == 1

    opportunities = db_session.query(Opportunity).all()
    assert len(opportunities) == 1
    opp = opportunities[0]
    assert "mokymų konkursas" in opp.title.lower()
    assert opp.eligibility is not None
    assert opp.sales is not None
    # Netinkamas ("eismo remontas") elementas neturėjo sukurti Opportunity.
    titles = [o.title for o in opportunities]
    assert not any("remonto" in t.lower() for t in titles)


def test_run_crawl_single_source_error_does_not_abort_run(db_session, test_settings):
    db_session.add(_make_html_source())
    db_session.add(_make_broken_source())
    db_session.commit()

    run = run_crawl(db_session, test_settings, trigger="manual")

    assert run.sources_total == 2
    assert run.sources_ok == 1
    assert run.sources_error == 1
    assert run.status == "completed_with_errors"
    # Bent viena galimybė vis tiek turėjo būti sukurta iš veikiančio šaltinio.
    assert db_session.query(Opportunity).count() == 1


def test_unchanged_page_is_not_reanalyzed_on_second_run(db_session, test_settings):
    from app.models.assessment import ChangeEvent
    from app.models.document import CrawledPage

    db_session.add(_make_html_source())
    db_session.commit()

    run1 = run_crawl(db_session, test_settings, trigger="manual")
    assert run1.sources_ok == 1
    opp_count_after_first = db_session.query(Opportunity).count()
    change_events_after_first = db_session.query(ChangeEvent).count()
    pages_after_first = db_session.query(CrawledPage).count()
    assert pages_after_first > 0

    run2 = run_crawl(db_session, test_settings, trigger="manual")
    check2 = run2.check_results[0]
    # Turinys nepasikeitė — puslapiai pažymėti kaip "unchanged", nesukurta naujų
    # Opportunity įrašų ir jokių papildomų ChangeEvent (t. y. neanalizuota iš naujo).
    assert check2.pages_unchanged > 0
    assert db_session.query(Opportunity).count() == opp_count_after_first
    assert db_session.query(ChangeEvent).count() == change_events_after_first


def test_blocked_bot_protection_source_is_skipped_not_errored(db_session, test_settings):
    src = _make_html_source()
    src.code = "test_blocked"
    src.status = "blocked_bot_protection"
    src.notes = "Cloudflare iššūkis"
    db_session.add(src)
    db_session.commit()

    run = run_crawl(db_session, test_settings, trigger="manual")
    assert run.sources_blocked == 1
    assert run.sources_error == 0
