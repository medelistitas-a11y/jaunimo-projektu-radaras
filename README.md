# Mostai galimybių radaras

Naršyklinė programa, kuri kasdien renka viešai skelbiamą informaciją apie Lietuvos jaunimo
srities projektus, konkursus ir finansavimo kvietimus, ir kiekvienam radiniui pateikia **du
atskirus** vertinimus:

- **A. Paraiškos tinkamumas** — ar MB „Mostai“ pati gali teikti paraišką.
- **B. Pardavimo galimybė** — ar dabar racionalu skambinti ir siūlyti mokymų paslaugas
  (žaliaforo logika: žalia / geltona / raudona).

Tai **pardavimo galimybių radaras**, ne vien dotacijų katalogas. Plačiau žr. `PLAN.md`
(architektūra, etapai) ir `SOURCE_AUDIT.md` (kiekvieno šaltinio realaus patikrinimo rezultatai).

> ⚠️ **Teisinė pastaba**: automatinis tinkamumo vertinimas NĖRA teisinė išvada. Prieš teikiant
> paraišką arba pasirašant sutartį, būtina patikrinti pirminius dokumentus (konkurso nuostatus,
> kvietimo sąlygas) rankiniu būdu.

## Turinys

1. [Reikalavimai](#reikalavimai)
2. [Pirmas paleidimas nuo švaraus katalogo](#pirmas-paleidimas)
3. [Kasdienis naudojimas (Makefile)](#kasdienis-naudojimas)
4. [Rankinis scrape / vieno šaltinio paleidimas](#rankinis-scrape)
5. [Testai ir lint](#testai-ir-lint)
6. [Atsarginė kopija ir atkūrimas](#backup)
7. [Kasdienio darbo laiko keitimas](#kasdienis-laikas)
8. [SMTP ir Anthropic API įjungimas](#smtp-ir-llm)
9. [Publikavimas į Render (naršyklėje)](#publikavimas)
10. [Aplinkos kintamųjų lentelė](#env-lentele)
11. [Saugumas ir apribojimai](#saugumas)
12. [Žinomi apribojimai](#zinomi-apribojimai)

## Reikalavimai

- Docker Engine 24+ ir Docker Compose v2 (produkciniam/lokaliam pilnam paleidimui).
- Python 3.12 (jei norite paleisti be Docker — testams pakanka ir 3.11).
- ~4 GB laisvos vietos diske (LibreOffice + Tesseract + Playwright Chromium vaizdai).

## Pirmas paleidimas nuo švaraus katalogo {#pirmas-paleidimas}

```bash
git clone <repo-url> mostai-galimybiu-radaras
cd mostai-galimybiu-radaras

# 1. Sukurkite .env iš pavyzdžio
cp .env.example .env
# Redaguokite .env: bent ADMIN_CONTACT_EMAIL. Kitiems laukams numatytosios reikšmės tinka
# lokaliam bandymui. NIEKADA nekomituokite .env su tikrais slaptažodžiais/raktais.

# 2. Paleiskite visą programą
docker compose up --build -d
# arba: make up

# 3. Migracijos pritaikomos automatiškai web serviso starto komandoje
#    (žr. docker-compose.yml `command:`). Rankiniam paleidimui:
docker compose exec web alembic upgrade head

# 4. Atidarykite http://localhost:8000
```

Pirmo starto metu programa automatiškai įkelia šaltinių registrą iš `sources.yaml` (66 įrašai:
5 privalomi + LTKT + 60 savivaldybių). Rankinis paleidimas nereikalingas, bet galimas:

```bash
docker compose exec web python -m app.seed.sources_seed
```

### Administratoriaus sukūrimas

MVP skirtas vienam vartotojui. Jei programa pasiekiama tik iš `localhost`, autentifikacija
gali likti išjungta (numatytoji būsena). Prieš keliant į viešą hostingą, **būtina** nustatyti
slaptažodį:

```bash
python -m app.scripts.hash_password
# arba: make admin-password
```

Įvestą hash įrašykite į `.env` kaip `ADMIN_PASSWORD_HASH` (ir `ADMIN_USERNAME`, jei norite kitą
vardą nei `admin`). Autentifikacija reikalinga administravimo veiksmams: žymų keitimui,
tikrinimo paleidimui. Peržiūra (sąrašas, detalė, CSV) lieka vieša — jei norite ir ją apsaugoti,
pridėkite reverse-proxy su Basic Auth arba VPN prieš viešindami serverį.

## Kasdienis naudojimas (Makefile) {#kasdienis-naudojimas}

```bash
make up              # paleisti (docker compose up --build -d)
make down             # sustabdyti
make migrate          # pritaikyti migracijas
make seed             # atnaujinti šaltinių registrą iš sources.yaml
make scrape           # rankinis visų įjungtų šaltinių tikrinimas
make scrape-source SOURCE=kaunas_naujienos   # tik vienas šaltinis
make test             # testai (lokaliai, be Docker, SQLite)
make test-docker      # testai Docker konteineryje
make lint             # ruff check + format --check
make format           # automatinis formatavimas
make backup           # PostgreSQL atsarginė kopija -> backups/
make restore FILE=backups/xxx.sql.gz
make logs             # web serviso logai
make shell             # interaktyvus shell web konteineryje
```

### Windows be `make`

Jei `make` nepasiekiamas (pvz. Windows be WSL), naudokite tiesiogines komandas:

```powershell
docker compose up --build -d
docker compose exec web alembic upgrade head
docker compose exec web python -m app.scripts.manual_scrape
docker compose exec web python -m app.scripts.manual_scrape --source kaunas_naujienos
docker compose down
```

## Rankinis scrape / vieno šaltinio paleidimas {#rankinis-scrape}

UI turi mygtuką „Tikrinti dabar“ (pagrindiniame puslapyje) ir „Tikrinti“ prie kiekvieno
šaltinio (`/saltiniai`). Paspaudimas negali paleisti kelių identiškų darbų vienu metu —
tiek API (`POST /api/crawl/run`, `POST /api/sources/{code}/check`), tiek pats vykdymo variklis
(`app/crawler/runner.py`) turi apsaugą: jei jau yra `CrawlRun` su statusu `running`, naujas
paleidimas atmetamas (HTTP 409), o produkcinėje PostgreSQL aplinkoje papildomai naudojamas
`pg_try_advisory_lock`.

CLI:

```bash
python -m app.scripts.manual_scrape                       # visi įjungti šaltiniai
python -m app.scripts.manual_scrape --source skuodas_wp_api  # tik vienas šaltinis
```

## Testai ir lint {#testai-ir-lint}

```bash
python3.12 -m venv .venv && source .venv/bin/activate   # arba 3.11 – testams pakanka
pip install -r requirements-dev.txt
python -m pytest tests/ -v          # 55 testai + 1 praleidžiamas be Chromium
ruff check app tests
ruff format --check app tests
```

Testai naudoja SQLite (be Docker) ir mažus sintetinius `tests/fixtures/*` failus (HTML/PDF/DOCX),
kurie sukurti šio projekto kūrimo metu — jokių realių organizacijų duomenų juose nėra. Realaus
PDF/DOCX generavimo scenarijų galima pakartoti: `python tests/fixtures/generate_fixtures.py`.

Gyvi (`@pytest.mark.live`, jei tokių priskirsite naujiems testams) arba aplinkos priklausomi
testai (pvz. `tests/test_js_adapter.py`, kuriam reikia Chromium) automatiškai praleidžiami, jei
reikalinga priklausomybė nepasiekiama — tai NĖRA klaida.

## Atsarginė kopija ir atkūrimas {#backup}

```bash
./scripts/backup.sh                       # backups/mostai_<data>.sql.gz
./scripts/backup.sh mano_kopija.sql.gz    # su pasirinktu pavadinimu
./scripts/restore.sh backups/mostai_20260101_120000.sql.gz   # ĮSPĖJA prieš perrašant
```

## Kasdienio darbo laiko keitimas {#kasdienis-laikas}

- Lokaliai/Docker Compose: `.env` kintamieji `DAILY_CRAWL_TIME` (HH:MM) ir `TIMEZONE` (numatyta
  `Europe/Vilnius`). Naudoja `app/scheduler/run_worker.py` (APScheduler `BackgroundScheduler` su
  `CronTrigger`), veikiantis atskirame `worker` servise.
- Render: `render.yaml` cron servisas (`mostai-daily-crawl`) naudoja `schedule` lauką **UTC**
  laiku (Render reikalavimas) — žr. detalų paaiškinimą ir DST pastabą pačiame `render.yaml` faile.

## SMTP ir pasirenkamos Anthropic API įjungimas {#smtp-ir-llm}

**Kasdienė el. pašto santrauka** išjungta, kol `.env` neužpildyti `SMTP_HOST` ir `SMTP_TO`.
Užpildžius, siunčiama tik jei yra naujų pranešimų (nebent `WEEKLY_EMPTY_SUMMARY=true`), ir tik
tie pranešimai, kurie dar nebuvo išsiųsti (`Notification.emailed`), taigi dublikatų nebus.

```env
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=...
SMTP_PASSWORD=...
SMTP_FROM=Mostai galimybių radaras <noreply@example.lt>
SMTP_TO=jums@example.lt
```

**Pasirenkamas LLM klasifikatorius** (Anthropic SDK) naudojamas TIK jei `.env` nustatytas
`ANTHROPIC_API_KEY`. Modelio pavadinimas NIEKADA nekoduojamas — naudojamas `LLM_MODEL` aplinkos
kintamasis. Be šio rakto sistema pilnai veikia vien su taisyklių varikliu (`app/rules/`).

```env
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-sonnet-5
```

## Publikavimas į Render (naršyklėje) {#publikavimas}

Repozitorijoje yra patikrinta deklaratyvi konfigūracija `render.yaml` (Blueprint), sukurta ir
patikrinta pagal aktualią Render dokumentaciją 2026-09-02. **Faktinis publikavimas — atskiras
jūsų sprendimas**, šis README tik aprašo žingsnius naršyklėje:

1. Susikurkite paskyrą [render.com](https://render.com), jei dar neturite.
2. Render Dashboard → **New** → **Blueprint**.
3. Prijunkite šią GitHub repozitoriją (Render paprašys GitHub autorizacijos).
4. Render aptiks `render.yaml` ir pasiūlys sukurti: `mostai-db` (PostgreSQL), `mostai-web`
   (žiniatinklio paslauga) ir `mostai-daily-crawl` (kasdienis cron darbas).
5. Prieš patvirtinant, Render paprašys užpildyti laukus, pažymėtus `sync: false`
   (`ADMIN_PASSWORD_HASH`, `ADMIN_CONTACT_EMAIL`, pasirenkamus `SMTP_*`/`ANTHROPIC_API_KEY`).
   `ADMIN_PASSWORD_HASH` sugeneruokite lokaliai su `make admin-password` PRIEŠ šį žingsnį.
6. Patvirtinkite planus (žr. kainos pastabą žemiau) ir spauskite **Apply**.
7. Render sukurs DB, paleis pirmą `web` servisą (migracijos pritaikomos automatiškai starto
   komandoje) ir suplanuos `mostai-daily-crawl` pagal `render.yaml` nurodytą UTC tvarkaraštį.
8. Po sėkmingo diegimo `mostai-web` servisas turės viešą `*.onrender.com` adresą.

**Kainos pastaba**: Render planų kainos ir nemokamo lygio galimybės keičiasi. Šis README
NEŽADA, kad pasirinkti planai (`starter`, `basic-256mb`) yra nemokami — patikrinkite aktualias
kainas [render.com/pricing](https://render.com/pricing) prieš patvirtindami diegimą. Galite
pakeisti plano pavadinimus `render.yaml` faile prieš prijungdami repozitoriją.

**Žinomas apribojimas**: Render diskai priklauso vienam servisui ir nėra bendrinami tarp `web` ir
`cron` servisų (skirtingai nei Docker Compose, kur `documents_data` tomas bendras). Todėl
originalūs dokumentai, atsisiųsti per kasdienį cron darbą, Render aplinkoje nėra prieinami
atsisiuntimui per web sąsają — tik jų IŠTRAUKTAS TEKSTAS (kuris ir naudojamas vertinimams),
saugomas bendroje PostgreSQL DB. Pilnam originalų bendrinimui reikėtų išorinės objektų saugyklos
(pvz. S3 suderinamos) — tai tolesnio etapo darbas.

## Aplinkos kintamųjų lentelė {#env-lentele}

| Kintamasis | Tipas | Paskirtis |
|---|---|---|
| `DATABASE_URL` | **paslaptis** (turi prisijungimo duomenis) | PostgreSQL prisijungimo eilutė |
| `SECRET_KEY` | **paslaptis** | Sesijų/CSRF apsaugai (generuojama automatiškai Render) |
| `ADMIN_USERNAME` | paprastas | Administratoriaus prisijungimo vardas |
| `ADMIN_PASSWORD_HASH` | **paslaptis** | bcrypt hash (žr. `make admin-password`) |
| `ADMIN_CONTACT_EMAIL` | paprastas | Rodomas User-Agent stringe, atsakingo asmens kontaktas |
| `CRAWLER_USER_AGENT` | paprastas | HTTP User-Agent, turi turėti kontaktą |
| `TIMEZONE` | paprastas | Numatyta `Europe/Vilnius` |
| `SCHEDULER_ENABLED` | paprastas | `true`/`false` — ar worker servisas planuoja darbą |
| `DAILY_CRAWL_TIME` | paprastas | `HH:MM`, naudojama tik `SCHEDULER_ENABLED=true` |
| `CRAWLER_MAX_URLS_PER_SOURCE` | paprastas | Ribojimas vienam paleidimui |
| `CRAWLER_MAX_DEPTH` | paprastas | Naršymo gylio riba |
| `CRAWLER_MIN_DELAY_SECONDS` | paprastas | Mandagumo pauzė tarp užklausų vienam domenui |
| `CRAWLER_MAX_RETRIES` | paprastas | Pakartojimų skaičius |
| `CRAWLER_MAX_DOWNLOAD_MB` | paprastas | Puslapio/failo dydžio riba |
| `OCR_ENABLED` / `OCR_LANGUAGES` | paprastas | OCR įjungimas ir kalbos (`lit+eng`) |
| `DOCUMENT_STORAGE_DIR` | paprastas | Kelias originalams (bendras tomas Docker Compose) |
| `DOCUMENT_RETENTION_DAYS` | paprastas | Originalų saugojimo terminas dienomis |
| `ANTHROPIC_API_KEY` | **paslaptis**, pasirenkama | Įjungia LLM klasifikatorių |
| `LLM_MODEL` | paprastas | Anthropic modelio ID (niekada nekoduojamas kode) |
| `SMTP_HOST` / `SMTP_PORT` | paprastas/paslaptis | SMTP serveris; tuščias = išjungta |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | **paslaptis** | SMTP prisijungimas |
| `SMTP_FROM` / `SMTP_TO` | paprastas | El. laiško siuntėjas/gavėjas |
| `WEEKLY_EMPTY_SUMMARY` | paprastas | `true` = siųsti santrauką ir kai nieko naujo |

## Saugumas ir apribojimai {#saugumas}

- **SSRF apsauga**: crawleris leidžia tik registre nurodytus domenus ir tik viešus IP adresus
  (blokuoja localhost, privačius/link-local IP, `file://` ir kt. — žr.
  `app/crawler/ssrf_guard.py`).
- **robots.txt** gerbiamas visada; jei nepasiekiamas dėl bot-apsaugos (dažnas atvejis, žr.
  `SOURCE_AUDIT.md`), šaltinis pažymimas `blocked_bot_protection` ir NEBANDOMAS apeiti.
  Programa niekada nebando spręsti CAPTCHA ar Cloudflare JS iššūkių.
- **Failų apribojimai**: dydžio limitas (`CRAWLER_MAX_DOWNLOAD_MB`), MIME/turinio tipo
  patikra, vykdomieji failai nesaugomi.
- Žurnaluose (`CrawlRun.log`, aplikacijos logai) niekada nerodomi slaptažodžiai/API raktai.
- HTML atvaizdavime naudojami Jinja2 auto-escaping šablonai (numatytas saugus elgesys).

## Žinomi apribojimai {#zinomi-apribojimai}

- **60 savivaldybių padengimas**: patikrinimo dieną (2026-09-02) tik 12/60 savivaldybių svetainių
  buvo tiesiogiai pasiekiamos paprastu HTTP klientu — likusios naudoja Cloudflare bot-apsaugą,
  kurios instrukcijos aiškiai draudžia apeiti. Pilna lentelė: `SOURCE_AUDIT.md`. Šie šaltiniai
  registre yra, bet neįjungti automatiniam crawl (`enabled: false`), su nuoroda rankinei peržiūrai
  UI „Šaltiniai“ skiltyje.
- **JRA ir Vilniaus konkursų sistema** (privalomi pagal užduotį šaltiniai) taip pat už Cloudflare
  — tas pats principas taikomas.
- **LTKT (Lietuvos kultūros taryba)**: sąrašo puslapis yra HTML lentelė, ne straipsnių sąrašas;
  bendras adapteris jai netinka be papildomo darbo, todėl šaltinis registruotas, bet neįjungtas
  (`needs_verification`), kad nebūtų generuojami klaidingi įrašai.
- **Datų/pinigų priskyrimas konkrečiam laukui** (paraiškos terminas vs. veiklos laikotarpis;
  bendras biudžetas vs. vieno projekto suma) yra heuristinis, be LLM — sudėtingesniais atvejais
  laukas gali likti tuščias net jei tekste data/suma yra, kad nebūtų klaidingai priskirta
  netinkamam laukui. Su `ANTHROPIC_API_KEY` galima įjungti tikslesnį (bet visada citata pagrįstą)
  LLM klasifikatorių.
- **Kontaktų vardo-šalia-telefono atpažinimas** yra regex heuristika, ne NLP — kartais
  bendras/skyriaus telefonas gali likti nepriskirtas konkrečiam vardui (tokiu atveju žymimas
  `is_general_contact=True`, niekada neklaidinamas kaip konkretaus asmens kontaktas).
- **Originalių dokumentų bendrinimas Render aplinkoje** tarp web ir cron servisų — žr.
  [Publikavimas](#publikavimas) skyrių aukščiau.
- **Playwright/Chromium JS adapteris** įgyvendintas ir padengtas testu (praleidžiamas, jei
  Chromium neįdiegtas), bet nenaudojamas jokiam šiuo metu įjungtam šaltiniui — patikrinus visas
  12 pasiekiamų savivaldybių svetainių, nė viena nepasirodė esanti kliento pusėje generuojama SPA.
