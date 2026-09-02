"""HTML sąrašo ir detalės puslapių ištraukimas su BeautifulSoup/lxml."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

_DOC_EXTENSIONS = (".pdf", ".docx", ".doc", ".xlsx", ".xls")


@dataclass
class ListItem:
    title: str
    url: str


@dataclass
class ExtractedPage:
    title: str | None
    text: str
    document_links: list[str] = field(default_factory=list)
    all_links: list[str] = field(default_factory=list)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _clean_soup(soup: BeautifulSoup) -> None:
    # nav/header/footer/aside pašalinami, kad svetainių meniu (dažnai dešimtys nuorodų su
    # bendriniais žodžiais kaip "projektai", "prevencija", "partneriai") nebūtų klaidingai
    # laikomi straipsnio turiniu — realus rastas atvejis: kaunas.lt puslapiuose nėra <main>,
    # todėl be šio filtro visas <body> (įskaitant pilną meniu) patekdavo į ištrauktą tekstą,
    # sugadindamas ir aktualumo raktažodžių filtrą, ir citatų paiešką.
    for tag in soup(
        ["script", "style", "noscript", "iframe", "svg", "nav", "header", "footer", "aside"]
    ):
        tag.decompose()


def extract_list_items(
    html: str,
    base_url: str,
    list_item_selector: str = "article",
    link_selector: str = "a",
) -> list[ListItem]:
    """Ištraukia sąrašo elementus (pvz. naujienų/konkursų sąrašo puslapį)."""
    soup = BeautifulSoup(html, "lxml")
    _clean_soup(soup)
    items: list[ListItem] = []
    seen_urls: set[str] = set()

    containers = soup.select(list_item_selector) or [soup]
    for container in containers:
        link = container.select_one(link_selector)
        if link is None or not link.get("href"):
            continue
        url = urljoin(base_url, link["href"])
        if url in seen_urls:
            continue
        title = link.get_text(strip=True) or container.get_text(strip=True)[:200]
        if not title:
            continue
        seen_urls.add(url)
        items.append(ListItem(title=title, url=url))
    return items


_BLOCK_TAGS = ["p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "td", "th", "blockquote"]


def _block_text(container) -> str:
    """Ištraukia tekstą blokas-po-bloko, kad ne-paragrafiniai naujos eilutės
    simboliai HTML šaltinyje (dekoratyviniai line-wrap'ai) nesukurtų klaidingų
    sakinio ribų. Kiekvienos blokinės žymos vidinis whitespace suvienodinamas
    į vieną tarpą, blokai sujungiami "\\n".
    """
    blocks = container.find_all(_BLOCK_TAGS)
    if not blocks:
        return re.sub(r"\s+", " ", container.get_text(" ", strip=True)).strip()
    lines = []
    for b in blocks:
        line = re.sub(r"\s+", " ", b.get_text(" ", strip=True)).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def extract_page(html: str, base_url: str, content_selector: str | None = None) -> ExtractedPage:
    """Ištraukia pagrindinį teksto turinį iš detalės/naujienos puslapio.

    `content_selector` — pasirenkamas CSS selektorius konkrečiam šaltiniui
    (Source.adapter_config["detail_content_selector"]), leidžiantis tiksliai
    apriboti straipsnio kūno konteinerį svetainėms, kuriose <main>/<article>
    žymos nenaudojamos arba apima per daug šalutinio turinio (meniu, šoninės
    juostos). Be jo naudojama bendra heuristika.
    """
    soup = BeautifulSoup(html, "lxml")
    _clean_soup(soup)

    title_tag = soup.find(["h1", "title"])
    title = title_tag.get_text(strip=True) if title_tag else None

    main = None
    if content_selector:
        main = soup.select_one(content_selector)
    if main is None:
        main = soup.find("main") or soup.find("article") or soup.body or soup
    text = _block_text(main) if main else ""

    doc_links: list[str] = []
    all_links: list[str] = []
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"])
        parsed = urlparse(href)
        if parsed.scheme not in ("http", "https"):
            continue
        all_links.append(href)
        if any(parsed.path.lower().endswith(ext) for ext in _DOC_EXTENSIONS):
            doc_links.append(href)

    return ExtractedPage(
        title=title,
        text=text,
        document_links=list(dict.fromkeys(doc_links)),
        all_links=list(dict.fromkeys(all_links)),
    )
