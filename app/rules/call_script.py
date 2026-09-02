"""„Ką pasakyti“ lauko generavimas — trumpas, neįkyrus skambučio pagrindas,
sudarytas TIK iš rastų faktų (institucijos/projekto pavadinimo, temos,
tikslinės grupės, projekto stadijos). Jokių išgalvotų detalių.
"""

from __future__ import annotations

_TOPIC_PHRASES = {
    "psichikos sveikat": "psichikos sveikatos stiprinimo",
    "emoc": "emocijų atpažinimo ir reguliavimo",
    "prevenc": "psichoaktyviųjų medžiagų vartojimo prevencijos",
    "priklausom": "priklausomybių prevencijos",
    "smurt": "smurto prevencijos",
    "patyč": "patyčių prevencijos",
    "kriz": "krizių valdymo",
    "atsparum": "atsparumo stiprinimo",
    "kompetenc": "kompetencijų stiprinimo",
    "superviz": "supervizijos",
    "neformal": "neformaliojo ugdymo",
}

_TARGET_GROUP_PHRASES = {
    "jaunimo darbuotoj": "su jaunimu dirbančius specialistus",
    "su jaunimu dirban": "su jaunimu dirbančius specialistus",
    "pedagog": "pedagogus",
    "socialin": "socialinius darbuotojus",
    "paaugl": "paauglius",
    "šeim": "šeimas",
    "jaunim": "jaunimą",
}


def _first_match(text: str, mapping: dict[str, str], default: str) -> str:
    low = text.lower()
    for stem, phrase in mapping.items():
        if stem in low:
            return phrase
    return default


def build_call_script(
    institution_name: str,
    project_title: str,
    full_text: str,
    is_already_funded: bool,
) -> str:
    target_group = _first_match(
        full_text, _TARGET_GROUP_PHRASES, "jaunimą ir su juo dirbančius specialistus"
    )
    topic = _first_match(full_text, _TOPIC_PHRASES, "kompetencijų stiprinimo")

    if is_already_funded:
        activity_phrase = f"vykdo {project_title}"
    else:
        activity_phrase = f"planuoja arba skelbia {project_title}"

    return (
        f"Laba diena, skambinu iš MB „Mostai“. Matome, kad {institution_name} {activity_phrase}. "
        f"Dirbame su {target_group} ir vedame {topic} mokymus. Norėjau pasitikslinti, "
        "ar šiame projekte dar renkatės mokymų arba kompetencijų stiprinimo paslaugų teikėjus?"
    )
