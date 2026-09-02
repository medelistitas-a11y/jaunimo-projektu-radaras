from app.normalize.contacts_lt import find_emails, find_phones, normalize_phone


def test_normalize_plus370_format():
    result = normalize_phone("+370 612 34567")
    assert result.normalized == "+37061234567"


def test_normalize_8_prefix_mobile():
    result = normalize_phone("8 686 12345")
    assert result.normalized == "+37068612345"
    assert result.raw == "8 686 12345"


def test_normalize_8_prefix_with_dashes():
    result = normalize_phone("8-686-12345")
    assert result.normalized == "+37068612345"


def test_invalid_phone_returns_none_normalized():
    result = normalize_phone("123")
    assert result.normalized is None


def test_find_emails_multiple():
    text = "Kontaktai: jonas.jonaitis@savivaldybe.lt, info@pavyzdys.lt"
    emails = find_emails(text)
    assert emails == ["jonas.jonaitis@savivaldybe.lt", "info@pavyzdys.lt"]


def test_find_phones_in_text():
    text = "Skambinti tel. 8 686 12345 arba +370 5 219 6800"
    phones = find_phones(text)
    normalized = [p.normalized for p in phones]
    assert "+37068612345" in normalized
    assert "+37052196800" in normalized
