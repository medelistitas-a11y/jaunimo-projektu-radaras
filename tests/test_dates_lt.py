import datetime as dt

from app.normalize.dates_lt import find_all_dates, parse_first_date


def test_single_deadline_iki_menesio_diena():
    result = parse_first_date("Paraiškas teikti iki rugsėjo 15 d.", reference_year=2026)
    assert result is not None
    assert result.start == dt.date(2026, 9, 15)
    assert result.is_deadline is True


def test_date_range_same_month():
    result = parse_first_date("Veiklos vyks 2026 m. rugsėjo 2–15 d.")
    assert result is not None
    assert result.start == dt.date(2026, 9, 2)
    assert result.end == dt.date(2026, 9, 15)


def test_date_range_ascii_hyphen():
    result = parse_first_date("2026 m. rugsėjo 2-15 d.")
    assert result is not None
    assert result.end == dt.date(2026, 9, 15)


def test_numeric_iso_date():
    result = parse_first_date("Skelbimo data: 2026-09-15")
    assert result is not None
    assert result.start == dt.date(2026, 9, 15)


def test_no_date_found_returns_none():
    assert parse_first_date("Šiame tekste datos nėra.") is None


def test_find_all_dates_multiple():
    text = (
        "Paraiškos priimamos nuo 2026 m. rugsėjo 2–15 d., "
        "o veiklos turi baigtis iki spalio 20 d."
    )
    results = find_all_dates(text, reference_year=2026)
    assert len(results) == 2
    assert results[0].start == dt.date(2026, 9, 2)
    assert results[0].end == dt.date(2026, 9, 15)
    assert results[1].start == dt.date(2026, 10, 20)
    assert results[1].is_deadline is True


def test_invalid_date_ignored():
    # 32-oji diena neegzistuoja — turi būti praleista, ne sukelti klaidą.
    assert parse_first_date("iki rugsėjo 32 d.") is None
