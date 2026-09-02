"""WordPress REST API adapteris (nestandartinis, vietoje HTML naršymo).

Naudojamas savivaldybėms, kurių svetainė paremta WordPress ir turi viešą
/wp-json/wp/v2/posts galinį tašką. Realus patikrintas pavyzdys: skuodas.lt
(žr. SOURCE_AUDIT.md, 2026-09-02: HTTP 200, ?search=jaunim grąžina realius
įrašus).
"""

from __future__ import annotations

import html
import json
import re

from app.crawler.adapters.base import DiscoveredItem
from app.crawler.http_client import PoliteHttpClient
from app.models.source import Source

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(fragment: str) -> str:
    text = _TAG_RE.sub(" ", fragment or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def discover_items(
    client: PoliteHttpClient, source: Source, max_items: int = 60
) -> list[DiscoveredItem]:
    config = source.adapter_config or {}
    search_terms: list[str] = config.get("search_terms") or [""]
    per_page = config.get("per_page", 20)

    base_url = source.start_urls[0]
    items: list[DiscoveredItem] = []
    seen_ids: set[int] = set()

    for term in search_terms:
        sep = "&" if "?" in base_url else "?"
        url = f"{base_url}{sep}per_page={per_page}"
        if term:
            url += f"&search={term}"
        result = client.get(url)
        if result.not_modified or not result.text:
            continue
        try:
            posts = json.loads(result.text)
        except json.JSONDecodeError:
            continue
        if not isinstance(posts, list):
            continue
        for post in posts:
            post_id = post.get("id")
            if post_id in seen_ids:
                continue
            seen_ids.add(post_id)
            title = _strip_html(post.get("title", {}).get("rendered", ""))
            link = post.get("link")
            content_html = post.get("content", {}).get("rendered", "")
            if not title or not link:
                continue
            items.append(
                DiscoveredItem(
                    title=title,
                    url=link,
                    detail_html=content_html,
                    published_hint=post.get("date"),
                )
            )
            if len(items) >= max_items:
                return items
    return items
