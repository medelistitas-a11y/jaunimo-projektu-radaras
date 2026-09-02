"""Bendras HTML sąrašo adapteris, konfigūruojamas per Source.adapter_config.

Naudojamas, kai svetainė turi paprastą naujienų/konkursų sąrašo puslapį be
JavaScript. Pavyzdys: kaunas.lt/kategorija/naujienos/.
"""

from __future__ import annotations

from urllib.parse import urlparse

from app.crawler.adapters.base import DiscoveredItem
from app.crawler.http_client import PoliteHttpClient
from app.crawler.ssrf_guard import domain_matches
from app.extraction.html_extract import extract_list_items
from app.models.source import Source


def discover_items(
    client: PoliteHttpClient, source: Source, max_items: int = 60
) -> list[DiscoveredItem]:
    config = source.adapter_config or {}
    list_item_selector = config.get("list_item_selector", "article")
    link_selector = config.get("link_selector", "a")

    items: list[DiscoveredItem] = []
    seen_urls: set[str] = set()

    for start_url in source.start_urls:
        result = client.get(start_url)
        if result.not_modified or not result.text:
            continue
        list_items = extract_list_items(
            result.text,
            base_url=start_url,
            list_item_selector=list_item_selector,
            link_selector=link_selector,
        )
        for li in list_items:
            if li.url in seen_urls:
                continue
            host = urlparse(li.url).hostname or ""
            if not domain_matches(host, source.official_domain):
                continue  # nuoroda į kitą domeną (reklama, socialiniai tinklai ir pan.)
            if source.ignored_path_hints and any(
                hint in li.url for hint in source.ignored_path_hints
            ):
                continue
            seen_urls.add(li.url)
            items.append(DiscoveredItem(title=li.title, url=li.url))
            if len(items) >= max_items:
                return items
    return items
