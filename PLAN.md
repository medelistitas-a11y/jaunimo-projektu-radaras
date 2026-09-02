# PLAN.md — „Mostai galimybių radaras“

## 0. Kontekstas ir tikslas

Programa kasdien renka viešai skelbiamą informaciją apie Lietuvos jaunimo srities projektus,
konkursus ir finansavimo kvietimus, ir kiekvienam įrašui pateikia **du atskirus** vertinimus:

- **A. Paraiškos tinkamumas** — ar MB „Mostai“ pati gali teikti paraišką.
- **B. Pardavimo galimybė** — ar dabar racionalu skambinti ir siūlyti mokymų paslaugas.

Tai pardavimo įrankis, ne vien dotacijų katalogas. Švieso­foro spalva pirmiausia atspindi
pardavimo veiksmą (žr. `app/rules/`).

Projektas pradedamas nuo tuščios repozitorijos, todėl migracijos klausimas (7 punktas
instrukcijose) netaikomas — architektūra pasirenkama nuo nulio pagal TECHNOLOGINĖ KRYPTIS skyrių.

## 1. Architektūra

```
                 ┌────────────────────┐
                 │   PostgreSQL 16    │◄────────────┐
                 └─────────▲──────────┘              │
                           │ SQLAlchemy 2 / Alembic   │
        ┌──────────────────┴───────────────┐         │
        │            app/ (shared)         │         │
        │  models, rules, extraction,      │         │
        │  normalize, crawler, notify       │         │
        └───────┬───────────────────┬───────┘         │
                 │                   │                 │
        ┌────────▼────────┐  ┌───────▼─────────┐       │
        │ FastAPI web app │  │ APScheduler cron │───────┘
        │ (Jinja2 UI + API)│  │ (daily crawl job)│
        └─────────────────┘  └──────────────────┘
```

- **Vienas Python monorepo** (`app/`), du procesai: `web` (uvicorn) ir `worker` (APScheduler
  blocking scheduler paleidžia kasdienį `run_daily_crawl()`). Abu naudoja tą pačią PostgreSQL DB.
- UI: **serverio generuojami Jinja2 šablonai** + nedaug „vanilla“ JS (fetch į JSON API mygtukams:
  žymos, „Tikrinti dabar“, CSV eksportas). Pasirinkta vietoj atskiro React/Vite SPA, nes
  vartotojo patirtis (lentelė + filtrai + detalė) pilnai pasiekiama paprasčiau, o instrukcijos tai
  aiškiai leidžia („Nesukurk dviejų sudėtingų aplikacijų, jeigu tą pačią vartotojo patirtį galima
  pasiekti paprasčiau“).
- Testams — SQLite failas arba in-memory nenaudojamas dėl JSONB/array laukų; naudojame tikrą
  PostgreSQL per `docker compose` testų servisą **arba** SQLite su suderinamais tipais testams,
  kurie nenaudoja PG specifinių tipų (žr. 4 skyrių — pasirinkta SQLite testams su generic tipais,
  kad testai veiktų be Docker CI aplinkoje).

## 2. Duomenų schema (santrauka)

Pilnos lentelės su laukais — žr. `app/models/`. Pagrindinės esybės (kaip nurodyta užduotyje):

- `Source` — šaltinio registras (žr. `sources.yaml` + DB lentelė `sources`, seedinama paleidimo metu).
- `CrawlRun` — vienas tikrinimo paleidimas (visas arba vieno šaltinio), būsena, statistika.
- `SourceCheckResult` — vieno šaltinio patikrinimo per CrawlRun rezultatas (sėkmė/klaida, trukmė).
- `CrawledPage` — atsiųstas HTML puslapis (URL, hash, ETag/Last-Modified, ištraukta esmė).
- `Document` — priedas (PDF/DOCX/XLSX/DOC), originalas atskirtas nuo ištraukto teksto.
- `Opportunity` — pagrindinė esybė (galimybė/konkursas/kvietimas).
- `Organization` — institucija/organizatorius/pareiškėjas/vykdytojas.
- `Contact` — kontaktinis asmuo, susietas su Opportunity ir/ar Organization.
- `EligibilityAssessment` — A vertinimas su citata, URL, pasitikėjimu.
- `SalesAssessment` — B vertinimas (spalva, reason_code, next_action, next_action_date).
- `Evidence` — cituojama teksto ištrauka + šaltinis (naudojama abiejų vertinimų pagrindimui).
- `ChangeEvent` — pakeitimų istorija (Opportunity/Document lygiu).
- `UserReview` — žmogaus žymos (peržiūrėta/domina/nedomina/susisiekta/atidėti) + pastabos.
- `Notification` — pranešimų centro įrašai (in-app), su dedup raktu.

Datos/pinigų laukai visada saugomi porom: `*_raw` (originalus tekstas) + `*_normalized`
(ISO data / centai EUR), leidžiant NULL, kai nežinoma — niekada 0 ar išgalvota data.

## 3. Šaltinių žvalgymo (crawl) logika

`app/crawler/http_client.py` — vienas bendras httpx klientas su:

- SSRF apsauga (`ssrf_guard.py`): leidžia tik `http(s)`, tik domenus iš `Source.allowed_domains`
  registro, blokuoja privačius/loopback/link-local IP (patikrina po DNS rezoliucijos), blokuoja
  redirect į neleistiną domeną.
- `robots.py`: nuskaito ir cache'uoja `robots.txt`, gerbia `Disallow`, naudoja aiškų
  `User-Agent: MostaiGalimybiuRadaras/<versija> (+<ADMIN_CONTACT_EMAIL>)`.
- Rate limit: per domeną — semaphore(1), min. 1.5s pauzė tarp užklausų, exponential backoff
  (3 bandymai), timeout 20s.
- ETag/Last-Modified/turinio hash — `CrawledPage.content_hash`, praleidžiama pakartotinė analizė,
  jei nepasikeitė.

Adapteriai (`app/crawler/adapters/`):

- `generic_html.py` — sąrašo/naujienų puslapis: CSS/XPath konfigūruojama per `Source` lauką
  `adapter_config` (JSON): sąrašo elemento selektorius, nuorodos selektorius, paginacijos šablonas.
- `wp_json.py` — WordPress REST API (`/wp-json/wp/v2/posts?search=...`) — naudojama, kai svetainė
  turi `wp-json` (aptinkama arba nurodoma registre). Realus pavyzdys: skuodas.lt.
- `js_playwright.py` — Playwright/Chromium, naudojamas TIK kai `Source.source_type == "js"`.
  Niekada nenaudojamas bot-apsaugos (Cloudflare iššūkių) apeiti — tai draudžiama instrukcijose.
- `sitemap.py`, `rss.py` — bendri adapteriai, kai šaltinis juos turi.

Vieno šaltinio klaida (`try/except` per šaltinį `runner.py` viduje) tik pažymima
`SourceCheckResult.status = "error"` ir nenutraukia viso `CrawlRun`.

## 4. Testų strategija

- SQLite (per `sqlite+pysqlite` su JSON tipu vietoj PG `JSONB`) — greiti unit/integraciniai testai
  be Docker. `docker-compose.yml` turi atskirą `db_test` PostgreSQL servisą realiems smoke testams
  (`pytest -m live`, neprivalomi CI).
- Fixture failai `tests/fixtures/`: mažas sintetinis HTML sąrašas, tekstinis PDF, nuskenuotas
  (be teksto sluoksnio) PDF, DOCX — visi sukurti šios sesijos metu, jokių realių organizacijų
  duomenų juose nėra.
- `tests/live/` — pažymėti `@pytest.mark.live`, praleidžiami numatytai, paleidžiami tik rankiniu
  `make smoke`.

## 5. Rizikos ir jų valdymas

| Rizika | Poveikis | Valdymas |
|---|---|---|
| Dauguma savivaldybių svetainių (patikrinta 2026-09-02: ~48/60) naudoja Cloudflare JS iššūkį, kuris blokuoja paprastus HTTP klientus, taip pat ir `robots.txt`. | Negalime automatiškai tikrinti daugumos savivaldybių. | Instrukcijos aiškiai draudžia apeiti CAPTCHA/JS iššūkius. Tokie šaltiniai registre pažymimi `status=blocked_bot_protection`, sukuriamas „Rankinė peržiūra“ mygtukas (atidaro šaltinio URL naujame lange, leidžia žmogui pačiam įvesti pastabą / pažymėti patikrinta). Neplanuojame Playwright naudoti šiems domenams. |
| JRA (`jra.lrv.lt`) ir Vilniaus konkursų sistema (`konkursai.vilnius.lt`) — abu privalomi minimalaus pjūvio šaltiniai — taip pat už Cloudflare. | Vertikalus pjūvis negali jų naudoti automatiniam crawl'ui. | Registruoti kaip šaltinius su `status=blocked_bot_protection`, dokumentuota SOURCE_AUDIT.md, vertikaliame pjūvyje pakeičiami dviem REALIAIS pasiekiamais savivaldybių šaltiniais (Kaunas – bendras HTML adapteris, Skuodas – WordPress REST API adapteris), o JRA/Vilnius palieka rankinės peržiūros sąrašui. |
| LLM gali „prigalvoti“ faktus. | Klaidingas tinkamumo/biudžeto teiginys. | LLM sąsaja tik pasirenkama (reikalauja `ANTHROPIC_API_KEY`), struktūrizuotas JSON su privaloma citata; nepavykus validuoti — „NEAIŠKU“. Taisyklių variklis (be LLM) yra pagrindinis ir visada veikia. |
| Nuskenuoti PDF be teksto sluoksnio. | Negalime automatiškai ištraukti teksto. | OCRmyPDF/Tesseract (lit+eng) Docker konteineryje; jei OCR nepavyksta arba neįdiegtas — dokumentas pažymimas `needs_human_review=True`, tekstas NULL, niekas neišgalvojama. |
| SSRF per dokumentų/nuorodų atsisiuntimą. | Saugumo pažeidimas. | `ssrf_guard.py` leidžia tik registre nurodytus domenus/subdomenus, blokuoja privačius IP po DNS rezoliucijos, tikrina MIME + failo parašą, riboja dydį. |
| Vienas serveris kasdieniam scrape (APScheduler) nesuderinamas su keliais web replikomis. | Dvigubas paleidimas. | PostgreSQL advisory lock (`pg_try_advisory_lock`) prieš pradedant `CrawlRun`; jei užimta — praleidžiama, log. |

## 6a. Įgyvendinimo būsena (atnaujinta po pilno paleidimo)

Visi 12 etapų iš 6-o skyriaus įgyvendinti ir patikrinti realiais veiksmais (ne tik kodo
peržiūra):

- `docker compose up --build -d` realiai paleistas šioje aplinkoje prieš tikrą PostgreSQL —
  migracijos, web servisas (FastAPI) ir worker servisas (APScheduler, Europe/Vilnius) paleidžia
  sėkmingai.
- Rankinis tikrinimas paleistas DAUG KARTŲ prieš REALIUS kaunas.lt ir skuodas.lt per visą šį
  etapą — galutiniame paleidime surinkta 65 realios galimybės iš abiejų šaltinių (2/2 šaltiniai
  be klaidų, 9 nauji pranešimai), su realiais A/B vertinimais, kontaktais, biudžetais, terminais.
  Pirmas bandymas ("60 galimybių") pasirodė esąs klaidingas — beveik visos jos buvo iš
  skuodas.lt, nes kaunas.lt adapterio selektorius buvo spėtas, ne patikrintas; žr. SOURCE_AUDIT.md
  „Realaus paleidimo rezultatai“ dėl pilnos, sąžiningos šio radinio ir taisymo istorijos.
- Šio (pratęsto) galutinio patikrinimo etapo metu rasta ir ištaisyta SEPTYNI realūs klaidos
  atvejai (ne hipotetiniai, kiekvienas su atskiru testu, apsaugančiu nuo regresijos):
  1. pinigų parseris nesutvarkydavo standartinio "neskaidomo tarpo" (\xa0) tūkstančių skirtuko;
  2. `crawl_runs.status` PostgreSQL stulpelis buvo per trumpas ("completed_with_errors" >
     VARCHAR(20)) — SQLite to nematė, nes netikrina VARCHAR ilgio;
  3. `passlib`+`bcrypt>=4.1` nesuderinamumas visiškai sugadindavo slaptažodžio hash generavimą;
  4. Docker Compose interpoliuoja "$" ženklus .env faile — bcrypt hash (visada prasideda "$2b$")
     būdavo sugadinamas, kol nepridėtas "$$" dvigubinimas;
  5. `color`+`eligibility` filtrų derinys sukeldavo Dekarto sandaugą (klaidingus rezultatus
     turint kelis įrašus), nes JOIN buvo praleidžiamas, kai `color` jau nustatytas;
  6. dokumento (PDF/DOCX) ekstrakcija/OCR būdavo vykdoma PRIEŠ dedup-pagal-hash patikrą, taigi
     patikra niekada realiai neišvengdavo pakartotinio darbo;
  7. kaunas_naujienos adapterio selektorius buvo spėtas (ne patikrintas) ir neatitiko realios
     svetainės struktūros; papildomai `extract_page` neturėjo apsaugos nuo `<nav>/<header>
     /<footer>/<aside>` turinio patekimo į "straipsnio tekstą", kai `<main>` žymos nėra.
- 88 pytest testai praeina + 1 praleidžiamas (Playwright, jei nėra Chromium binarinio failo).
- `ruff check` ir `ruff format --check` be klaidų.

## 6. Darbo etapai ir priėmimo kriterijai

Sekama pagal užduoties 12 etapų. Kiekvienam etapui priėmimo kriterijus:

1. **Inventorizacija/PLAN.md** — šis failas + SOURCE_AUDIT.md egzistuoja ir atspindi realiai
   patikrintus faktus (ne prielaidas).
2. **Architektūra/DB/Docker/UI karkasas** — `docker compose up --build` pakelia `db`, `web`,
   migracijos pritaikomos be klaidų, `/` grąžina 200.
3. **Šaltinių registras/HTTP klientas/CrawlRun apskaita** — `sources.yaml` seedinamas į DB,
   `python -m app.scripts.manual_scrape --source <kodas>` sukuria `CrawlRun` įrašą.
4. **HTML/dokumentų ištraukimas** — unit testai fixture failams praeina.
5. **Opportunity normalizavimas/įrodymai/dublikatai** — testai praeina, matoma UI detalėje.
6. **Vertinimai (A/B)** — taisyklių testai praeina, įskaitant kraštinius atvejus iš instrukcijų.
7. **Vertikalus pjūvis + testai** — bent 2 realūs savivaldybių šaltiniai + JRA/Vilnius kaip
   „blocked/manual“, PDF+DOCX fixture testai, git commit.
8. **UI/filtrai/CSV** — rankinis patikrinimas naršyklėje (per `make up`), CSV atsidaro Excel su
   lietuviškais simboliais (UTF-8 BOM).
9. **Scheduler/pranešimai** — `APScheduler` konfigūruotas `DAILY_CRAWL_TIME`+`Europe/Vilnius`;
   pranešimų centras rodo naujus žalius/geltonus/terminus/klaidas.
10. **60 savivaldybių auditas** — `SOURCE_AUDIT.md` turi visų 60 eilutę su realiu HTTP statusu.
11. **Testai/lint/migracijos/smoke** — `make test`, `make lint` be klaidų.
12. **README/ataskaita** — komandos patikrintos iš švaraus klono.

## 7. Ne tikslai (MVP ribos, sąmoningai paliekama vėlesniam etapui)

- Pilna automatinė visų Cloudflare apsaugotų svetainių integracija (reikalautų CAPTCHA/bot
  apėjimo — draudžiama).
- Celery/Redis (paruošta vietos, bet MVP naudoja APScheduler vieno proceso rėžime).
- Automatinis SOPAS/CVP IS turinio nuskaitymas už prisijungimo (saugome tik viešai matomą dalį
  ir nuorodą).
