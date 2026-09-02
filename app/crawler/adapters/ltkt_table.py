"""Lietuvos kultūros tarybos (ltkt.lt) finansavimo konkursų lentelės adapteris.

LTKT sąrašo puslapis (organizacijoms/konkursai) yra HTML LENTELĖ (<tr>/<td>),
ne straipsnių sąrašas — bendras generic_html adapteris jai netinka (žr.
SOURCE_AUDIT.md, 2026-09-02 pastaba apie klaidingą pirmą bandymą). Kiekviena
eilutė: [data (paraiškų terminas), sritis/pavadinimas, kvietimo būklė,
nuoroda į detalės puslapį].

SVARBU: LTKT fokusas yra kultūra/menas apskritai, NE jaunimas. Šis adapteris
TIK atranda kandidatus (lentelės eilutes) — aktualumo filtravimą (jaunimo/
mokymų/psichikos sveikatos/prevencijos/specialistų kompetencijų signalas)
atlieka bendras app.normalize.keywords_lt.is_relevant_candidate, kuris jau
kviečiamas app.crawler.pipeline.process_candidate visiems šaltiniams — čia
atskiros taisyklės NEDUBLIUOJAMOS, kad nebūtų dviejų nesutampančių filtrų.
"""

from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.crawler.adapters.base import DiscoveredItem
from app.crawler.http_client import PoliteHttpClient
from app.models.source import Source


def discover_items(
    client: PoliteHttpClient, source: Source, max_items: int = 60
) -> list[DiscoveredItem]:
    items: list[DiscoveredItem] = []
    seen_urls: set[str] = set()

    for start_url in source.start_urls:
        result = client.get(start_url)
        if result.not_modified or not result.text:
            continue

        soup = BeautifulSoup(result.text, "lxml")

        # SVARBU: ltkt.lt puslapiuose yra <base href="https://www.ltkt.lt">, kuris
        # pakeičia santykinių nuorodų (pvz. href="organizacijoms/konkursai/995")
        # skaičiavimo pagrindą — jos skaičiuojamos NUO <base>, o NE nuo dabartinio
        # puslapio URL (kuris turi kitą kelią be baigiamojo "/"). Ignoravus <base>,
        # urljoin(result.url, href) sudubliuodavo kelio segmentą
        # (.../organizacijoms/organizacijoms/konkursai/995) — tikra nuoroda tada
        # grąžindavo KITOKĮ (trumpesnį, ne konkretų) puslapį, sugadindamas citatos
        # šaltinio URL. Rasta realiu HTTP palyginimu 2026-09-02, žr. SOURCE_AUDIT.md.
        base_tag = soup.find("base", href=True)
        link_base = base_tag["href"] if base_tag else result.url

        for row in soup.select("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) < 3:
                continue

            date_text = cells[0].get_text(strip=True)
            title_text = cells[1].get_text(strip=True)
            status_text = cells[2].get_text(strip=True) if len(cells) > 2 else ""

            link = row.find("a", href=True)
            if link is None or not title_text:
                continue  # antraštės eilutė ("Data"/"Pavadinimas"/...) neturi nuorodos

            url = urljoin(link_base, link["href"])
            if url in seen_urls:
                continue
            seen_urls.add(url)

            full_title = f"{title_text} ({status_text})" if status_text else title_text
            items.append(
                DiscoveredItem(title=full_title, url=url, published_hint=date_text or None)
            )
            if len(items) >= max_items:
                return items

    return items
