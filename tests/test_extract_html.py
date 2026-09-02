from pathlib import Path

from app.extraction.html_extract import extract_list_items, extract_page

FIXTURES = Path(__file__).parent / "fixtures"


def test_extract_list_items():
    html = (FIXTURES / "list_page.html").read_text(encoding="utf-8")
    items = extract_list_items(html, base_url="https://testine-savivaldybe.lt/naujienos")
    urls = [i.url for i in items]
    assert "https://testine-savivaldybe.lt/naujiena/jaunimo-mokymu-konkursas" in urls
    assert any("mokymų konkursas" in i.title for i in items)


def test_extract_detail_page_text_and_documents():
    html = (FIXTURES / "detail_page.html").read_text(encoding="utf-8")
    page = extract_page(html, base_url="https://testine-savivaldybe.lt/naujiena/x")
    assert "jaunimo darbuotojų mokymų konkursas" in page.text.lower()
    assert any(url.endswith("konkurso-nuostatai.pdf") for url in page.document_links)
    assert any(url.endswith("forma.docx") for url in page.document_links)
    assert page.title is not None


def test_scripts_and_styles_removed():
    html = "<html><body><script>evil()</script><p>Tekstas</p></body></html>"
    page = extract_page(html, base_url="https://x.lt/")
    assert "evil" not in page.text
    assert "Tekstas" in page.text


def test_nav_header_footer_aside_excluded_from_extracted_text():
    """Regresija: svetainės be <main> žymos (realus atvejis - kaunas.lt) be šio
    filtro grąžindavo VISĄ svetainės meniu kaip straipsnio tekstą, sugadindami
    aktualumo raktažodžių filtrą (žr. git istoriją, sources.yaml pastabas).
    """
    html = (
        "<html><body>"
        "<nav><a href='/a'>Projektai</a><a href='/b'>Konkursai</a><a href='/c'>Partneriai</a></nav>"
        "<header><p>Antraštės meniu turinys</p></header>"
        "<main><h1>Tikras straipsnis</h1><p>Realus straipsnio turinys apie miesto šventę.</p></main>"
        "<footer><p>Pėdinės nuorodos ir kontaktai</p></footer>"
        "</body></html>"
    )
    page = extract_page(html, base_url="https://x.lt/naujiena/1")
    assert "Realus straipsnio turinys" in page.text
    assert "Projektai" not in page.text
    assert "Konkursai" not in page.text
    assert "Antraštės meniu" not in page.text
    assert "Pėdinės nuorodos" not in page.text


def test_content_selector_overrides_default_heuristic():
    html = (
        "<html><body>"
        "<div class='sidebar'><p>Šalutinis turinys, kurio nenorime</p></div>"
        "<div class='article-body'><h1>Antraštė</h1><p>Tikras straipsnio tekstas.</p></div>"
        "</body></html>"
    )
    page = extract_page(html, base_url="https://x.lt/naujiena/1", content_selector=".article-body")
    assert "Tikras straipsnio tekstas" in page.text
    assert "Šalutinis turinys" not in page.text
