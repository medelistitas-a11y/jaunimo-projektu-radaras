from app.normalize.keywords_lt import is_relevant_candidate


def test_specific_signal_alone_is_relevant():
    assert is_relevant_candidate("Skelbiamas jaunimo mokymų konkursas.") is True


def test_single_generic_administrative_word_is_not_enough():
    """Regresija: realiame bandyme prieš kaunas.lt kiekvienas atsitiktinis
    savivaldybės naujienos straipsnis (turizmas, kultūros renginiai) turėjo
    bent vieną bendrą administracinį žodį (projektas/konkursas/partneris) vien
    dėl svetainės struktūros/kalbos stiliaus, o ne dėl realaus ryšio su jaunimu
    ar mokymais. Vienas toks žodis vienas pats neturi pažymėti teksto aktualiu.
    """
    text = "Miesto taryba pristatė naują infrastruktūros projektą kartu su partneriais."
    assert is_relevant_candidate(text) is False


def test_multiple_generic_words_together_are_enough():
    text = (
        "Skelbiamas konkursas. Kviečiame teikti paraiškas dėl finansavimo. "
        "Ieškome partnerių projektui įgyvendinti."
    )
    assert is_relevant_candidate(text) is True


def test_empty_text_is_not_relevant():
    assert is_relevant_candidate("") is False
