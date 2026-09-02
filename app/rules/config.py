"""Taisyklių konfigūracija: raktažodžiai ir reason_code aprašymai lietuvių kalba.

Laikoma atskirai nuo sprendimo logikos (eligibility.py / sales.py), kad
raktažodžius/reason_code'us būtų galima keisti be pačios logikos perrašymo.
"""

from __future__ import annotations

# --- Paraiškos tinkamumo (A) žodynas ---

ELIGIBILITY_SENTENCE_HINTS = ["paraišk", "pareiškėj"]

OPEN_ELIGIBILITY_MARKERS = [
    "mažoji bendrija",
    "mažąją bendriją",
    "mažąsias bendrijas",
    "mažosios bendrijos",
    "privatūs juridiniai asmenys",
    "privatus juridinis asmuo",
    "visi juridiniai asmenys",
    "bet kuris juridinis asmuo",
    "neatsižvelgiant į jų teisinę formą",
    "neatsižvelgiant į teisinę formą",
    "juridiniai asmenys, neatsižvelgiant",
]

RESTRICTED_APPLICANT_TYPES = [
    "viešosios įstaigos",
    "viešoji įstaiga",
    "všį",
    "asociacij",
    "biudžetin",
    "jaunimo organizacij",
    "jaunimo centr",
    "nevyriausybin",
    "religin",
    "savivaldyb",
]

RESTRICTIVE_LANGUAGE = ["tik", "išskirtinai", "tiktai"]

NEGATION_WORDS = ["negali", "netinka", "neturi teisės", "negalima", "negalės", "nėra tinkam"]

PARTNERSHIP_MARKERS = [
    "kaip partner",
    "su partneriu",
    "partnerystės pagrindais",
    "jungtin",
]

VENDOR_ROLE_MARKERS = [
    "paslaugų teikėj",
    "mokymų paslaugų teikėj",
    "gali būti pasitelkt",
    "gali būti pasitelkta",
    "sudarant paslaugų sutartį",
    "perkant paslaugas",
]

# --- Pardavimo galimybės (B) žodynas ---

TRAINING_FIT_MARKERS = [
    "mokym",
    "seminar",
    "dirbtuv",
    "kompetenc",
    "kvalifikacij",
    "superviz",
    "konsultacij",
    "prevenc",
    "psichikos sveikat",
    "emoc",
]

DEADLINE_PASSED_HINTS = [
    "jau pasibaigęs",
    "jau pasibaigusi",
    "konkursas baigėsi",
    "konkursas pasibaigė",
    "rezultatai paskelbti",
    "laimėtojai paskelbti",
    "archyvuot",
]

PROCUREMENT_MARKERS = [
    "viešasis pirkimas",
    "viešojo pirkimo",
    "pirkimo procedūr",
    "cvp is",
    "cvpis",
    "skelbiamas pirkimas",
    "apklausos būdu",
]

ACCREDITATION_MARKERS = [
    "akreditacij",
    "licenc",
    "kvalifikacinis reikalavim",
    "patirties įrodym",
    "registracij",
    "registruotis iki",
]

BUNDLED_LOGISTICS_MARKERS = [
    "patalpų",
    "dalyvių surinkim",
    "maitinim",
    "kelion",
    "apgyvendinim",
]

# --- reason_code -> žmogui skaitomas trumpas aprašymas (naudojama UI ir pranešimuose) ---

SALES_REASON_DESCRIPTIONS: dict[str, str] = {
    "concrete_opportunity_with_contact": "Konkretus projektas, mokymai dera su veiklomis, yra kontaktas.",
    "concrete_opportunity_needs_contact_search": (
        "Konkretus projektas, mokymai dera, bet kontaktą dar reikia surasti."
    ),
    "needs_partner_or_condition": "Galimybė reali, bet reikia partnerio arba sąlygos įvykdymo.",
    "needs_procurement": "Gali reikėti dalyvauti viešajame pirkime.",
    "needs_accreditation_or_registration": "Reikia akreditacijos, registracijos ar patirties įrodymo.",
    "unclear_purchase_window": "Neaišku, ar paslaugą pirks atskirai / trūksta biudžeto ar kontakto.",
    "bundled_logistics": "Kartu su mokymais gali tekti organizuoti patalpas/dalyvius/maitinimą.",
    "deadline_passed": "Terminas ir pardavimo langas jau pasibaigęs.",
    "not_relevant": "Turinys nesusijęs su „Mostai“ paslaugomis.",
    "no_commercial_value": "Kontaktavimas neturėtų pagrįstos komercinės vertės.",
    "planned_early_stage": "Projektas dar tik planuojamas / kvietimo stadijoje — galima susisiekti iš anksto.",
}
