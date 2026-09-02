"""Patikrina Playwright/Chromium adapterį prieš lokalų sintetinį JS puslapį.

Praleidžiama (skip), jei Playwright arba Chromium binarinis failas nėra
įdiegtas šioje aplinkoje (pvz. be interneto prieigos naršyklės atsisiuntimui) —
tai NEBŪTINAS gyvo diegimo testas, žr. SOURCE_AUDIT.md dėl paaiškinimo, kodėl
šis adapteris nenaudojamas jokiam šiuo metu įjungtam šaltiniui.
"""

from __future__ import annotations

import http.server
import threading
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _chromium_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception:
        return False


@pytest.fixture()
def local_server():
    handler = http.server.SimpleHTTPRequestHandler

    class _Handler(handler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(FIXTURES), **kwargs)

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)


@pytest.mark.skipif(
    not _chromium_available(), reason="Playwright/Chromium neįdiegtas šioje aplinkoje"
)
def test_js_adapter_extracts_item_rendered_by_javascript(local_server):
    from app.crawler.adapters.js_playwright import discover_items
    from app.models.source import Source

    source = Source(
        code="test_js_source",
        name="Testinis JS šaltinis",
        institution_name="Testinė institucija",
        official_domain="127.0.0.1",
        start_urls=[f"{local_server}/js_rendered.html"],
        source_type="js",
        adapter="js_playwright",
        adapter_config={"wait_selector": "article"},
        status="active",
        enabled=True,
    )

    items = discover_items(source)
    assert len(items) == 1
    assert "bendruomeniškumo" in items[0].title.lower()
    assert items[0].url.endswith("/konkursas/js-jaunimo-projektas")
