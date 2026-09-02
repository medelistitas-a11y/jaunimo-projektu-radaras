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


def test_multiple_generic_words_together_are_still_not_enough():
    """Regresija (2026-09-02 duomenų kokybės auditas, žr. SOURCE_AUDIT.md): ankstesnė
    versija leisdavo ≥3 bendrus žodžius KARTU (be jokio specifinio signalo) laikyti
    pakankamu pagrindu. Realus auditas prieš www.ltkt.lt parodė, kad tai beveik nieko
    nefiltruoja — bet kuris finansavimo kvietimas BET KURIA tema (architektūra,
    dizainas ir kt., visiškai nesusiję su jaunimu) savaime paminės "konkursas",
    "kvietimas", "finansavimas", "projektas", "partneris" vien dėl žanro. Dabar
    reikalaujamas bent vienas specifinis signalas, nesvarbu kiek bendrų žodžių yra."""
    text = (
        "Skelbiamas konkursas. Kviečiame teikti paraiškas dėl finansavimo. "
        "Ieškome partnerių projektui įgyvendinti."
    )
    assert is_relevant_candidate(text) is False


def test_specific_stem_plus_generic_words_is_relevant():
    text = (
        "Skelbiamas konkursas jaunimo organizacijoms. Kviečiame teikti paraiškas "
        "dėl finansavimo. Ieškome partnerių projektui įgyvendinti."
    )
    assert is_relevant_candidate(text) is True


def test_generic_staff_contact_title_alone_is_not_enough():
    """Regresija: realus rastas atvejis — LTKT konkursų puslapiai (nesusiję su
    jaunimu, pvz. architektūros) turėjo bendrą kontaktų bloką "Vyriausioji
    specialistė ... tel. ...", kuris vienas pats klaidingai pažymėdavo puslapį
    aktualiu, nes "specialist" buvo laikomas specifiniu signalu."""
    text = "Turite klausimų? Kreipkitės! Dovilė Miliukštė. Vyriausioji specialistė."
    assert is_relevant_candidate(text) is False


def test_priklausomybe_matches_but_priklauso_nuo_does_not():
    """Regresija: realus rastas atvejis — "priklausomai nuo finansavimo dydžio"
    (bendras žodis "priklausyti/priklausomai" = "depending on") klaidingai
    suveikdavo kaip "priklausomybė" (narkotikų/alkoholio priklausomybė) signalas,
    nes kamienas "priklausom" apima abu. Dabar naudojamas siauresnis kamienas
    "priklausomyb", kuris atitinka TIK "priklausomybė/-ės/-ių" žodžio formas."""
    assert is_relevant_candidate("Priklausomybių prevencijos mokymai paaugliams.") is True
    assert (
        is_relevant_candidate(
            "Finansavimas skiriamas proporcingai organizacijoms priklausomai nuo "
            "joms skirto biudžeto einamaisiais metais."
        )
        is False
    )


def test_empty_text_is_not_relevant():
    assert is_relevant_candidate("") is False
