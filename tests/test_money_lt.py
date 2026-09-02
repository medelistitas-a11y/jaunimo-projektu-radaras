from app.normalize.money_lt import parse_first_money


def test_plain_amount_with_thousands_space():
    result = parse_first_money("Skiriama 10 000 Eur.")
    assert result is not None
    assert result.amount_cents == 1_000_000
    assert result.amount == 10_000.0


def test_tukst_multiplier():
    result = parse_first_money("Vieno projekto suma – iki 5 tūkst. eurų.")
    assert result is not None
    assert result.amount_cents == 500_000
    assert result.is_upper_bound is True


def test_mln_multiplier():
    result = parse_first_money("Programos biudžetas 2 mln. Eur.")
    assert result is not None
    assert result.amount_cents == 200_000_000


def test_decimal_comma():
    result = parse_first_money("Suma 1 500,50 Eur")
    assert result is not None
    assert result.amount_cents == 150_050


def test_no_money_found():
    assert parse_first_money("Čia nėra sumos.") is None
