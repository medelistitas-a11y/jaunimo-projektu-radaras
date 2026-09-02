"""Playwright/Chromium adapteris puslapiams, kuriems būtinas JavaScript, kad
turinys apskritai atsirastų DOM'e (kliento pusėje generuojamos SPA).

SVARBU: šis adapteris NIEKADA nenaudojamas bot-apsaugos (pvz. Cloudflare JS
iššūkių) apeiti — tai draudžiama instrukcijose. Jis skirtas TIK legaliems
atvejams, kai svetainė tiesiog atvaizduoja turinį per JS be jokios bot
apsaugos. Naudojamas, kai Source.source_type == "js".

Jei Playwright/Chromium neįdiegtas aplinkoje, funkcija meta aiškų
PlaywrightUnavailableError, kad kviečiantis kodas galėtų šaltinį pažymėti kaip
klaidą (nesustabdydamas viso CrawlRun).
"""

from __future__ import annotations

from app.crawler.adapters.base import DiscoveredItem
from app.extraction.html_extract import extract_list_items
from app.models.source import Source


class PlaywrightUnavailableError(Exception):
    pass


def discover_items(
    source: Source, max_items: int = 60, timeout_ms: int = 20000
) -> list[DiscoveredItem]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise PlaywrightUnavailableError(
            "Playwright neįdiegtas šioje aplinkoje — JS adapteris negalimas"
        ) from exc

    config = source.adapter_config or {}
    list_item_selector = config.get("list_item_selector", "article")
    link_selector = config.get("link_selector", "a")
    wait_selector = config.get("wait_selector")

    items: list[DiscoveredItem] = []
    seen_urls: set[str] = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(
                user_agent=config.get("user_agent", "MostaiGalimybiuRadaras/0.1")
            )
            for start_url in source.start_urls:
                page.goto(start_url, timeout=timeout_ms, wait_until="networkidle")
                if wait_selector:
                    page.wait_for_selector(wait_selector, timeout=timeout_ms)
                html_content = page.content()
                list_items = extract_list_items(
                    html_content,
                    base_url=start_url,
                    list_item_selector=list_item_selector,
                    link_selector=link_selector,
                )
                for li in list_items:
                    if li.url in seen_urls:
                        continue
                    seen_urls.add(li.url)
                    items.append(DiscoveredItem(title=li.title, url=li.url))
                    if len(items) >= max_items:
                        return items
        finally:
            browser.close()
    return items
