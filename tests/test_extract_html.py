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
