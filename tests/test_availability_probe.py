import datetime as dt

import httpx
import pytest

import app.crawler.http_client as http_client_module
import app.crawler.robots as robots_module
import app.crawler.ssrf_guard as ssrf_guard_module
from app.crawler.availability_probe import (
    probe_source_availability,
    run_weekly_availability_probes,
)
from app.models.assessment import Notification
from app.models.source import Source


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


def _patch_transport(monkeypatch, handler):
    transport = httpx.MockTransport(handler)
    original_client = http_client_module.httpx.Client

    def fake_client(**kwargs):
        kwargs["transport"] = transport
        return original_client(**kwargs)

    monkeypatch.setattr(http_client_module.httpx, "Client", fake_client)


def _blocked_source(code="test_blocked") -> Source:
    return Source(
        code=code,
        name="Testinis blokuotas šaltinis",
        institution_name="Testinė institucija",
        official_domain="blokuotas.lt",
        start_urls=["https://blokuotas.lt/konkursai/"],
        source_type="html",
        adapter="generic_html",
        status="blocked_in_current_runtime",
        enabled=False,
    )


def test_probe_detects_cloudflare_signature(monkeypatch):
    cf_challenge_html = "<html><head><title>Just a moment...</title></head><body></body></html>"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            text=cf_challenge_html,
            headers={"server": "cloudflare", "cf-mitigated": "challenge"},
        )

    _patch_transport(monkeypatch, handler)

    from app.config import Settings

    source = _blocked_source()
    diag = probe_source_availability(source, Settings(crawler_min_delay_seconds=0.0))

    assert diag["http_status_code"] == 403
    assert "cloudflare" in diag["bot_protection_signature"].lower()
    assert diag["now_accessible"] is False


def test_probe_detects_now_accessible(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html><body>Realus turinys</body></html>")

    _patch_transport(monkeypatch, handler)

    from app.config import Settings

    source = _blocked_source()
    diag = probe_source_availability(source, Settings(crawler_min_delay_seconds=0.0))

    assert diag["http_status_code"] == 200
    assert diag["bot_protection_signature"] is None
    assert diag["now_accessible"] is True


def test_weekly_probe_flips_status_and_notifies_when_now_accessible(db_session, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html><body>Realus turinys</body></html>")

    _patch_transport(monkeypatch, handler)

    from app.config import Settings

    source = _blocked_source()
    db_session.add(source)
    db_session.commit()

    checked = run_weekly_availability_probes(db_session, Settings(crawler_min_delay_seconds=0.0))

    assert checked == 1
    db_session.refresh(source)
    assert source.status == "needs_verification"
    assert source.last_http_status_code == 200
    notif = db_session.query(Notification).filter_by(kind="source_now_accessible").one()
    assert source.code in notif.dedup_key


def test_weekly_probe_skips_recently_checked_sources(db_session, monkeypatch):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(403, headers={"server": "cloudflare", "cf-mitigated": "challenge"})

    _patch_transport(monkeypatch, handler)

    from app.config import Settings

    source = _blocked_source()
    source.last_probe_at = dt.datetime.now(dt.UTC) - dt.timedelta(days=1)  # patikrinta vakar
    db_session.add(source)
    db_session.commit()

    checked = run_weekly_availability_probes(db_session, Settings(crawler_min_delay_seconds=0.0))
    assert checked == 0
    assert calls["n"] == 0


def test_weekly_probe_still_blocked_stays_blocked(db_session, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, headers={"server": "cloudflare", "cf-mitigated": "challenge"})

    _patch_transport(monkeypatch, handler)

    from app.config import Settings

    source = _blocked_source()
    db_session.add(source)
    db_session.commit()

    run_weekly_availability_probes(db_session, Settings(crawler_min_delay_seconds=0.0))
    db_session.refresh(source)
    assert source.status == "blocked_in_current_runtime"
    assert db_session.query(Notification).count() == 0
