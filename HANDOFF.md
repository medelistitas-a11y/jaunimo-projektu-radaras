# HANDOFF.md — produkcinio patikimumo / duomenų kokybės etapas

Sesija sustabdyta dėl artėjančio konteksto limito. Šis failas — tiksli būsena naujai sesijai.
Šaka: `claude/data-quality-hardening` (atšakota nuo `claude/mostai-opportunities-radar-49xpf0`,
kuri buvo sujungta į `main` per PR #1). **PR į `main` dar NĖRA sukurtas.**

## 1. Kas ATLIKTA ir patikrinta (109 testų praeina, ruff švarus)

1. **JRA/Vilnius diagnostika** — `app/crawler/availability_probe.py` (savaitinis auto-patikrinimas,
   CF signatūros aptikimas, auto-atstatymas į `needs_verification`), `app/scripts/
   smoke_test_jra_vilnius.py` (atskiras CLI smoke testas realiai hostingo aplinkai), `Source`
   modelyje naujas statusas `blocked_in_current_runtime` (NE `disabled`) + diagnostikos laukai +
   `alternative_source_of_id` FK. Rastas ir susietas alternatyvus šaltinis `socmin_projektu_konkursai`.
2. **LTKT adapteris** — `app/crawler/adapters/ltkt_table.py` (nauja, `<table>` parseris) +
   `tests/test_ltkt_adapter.py` + 3 fixture HTML failai. Rasta ir ištaisyta reali klaida: puslapis
   turi `<base href="https://www.ltkt.lt">`, ignoravus jį `urljoin` sudubliuodavo kelio segmentą.
3. **Web/cron saugyklos atskyrimas** — `app/storage/object_store.py` (pasirenkamas S3/MinIO/R2
   suderinamas interfeisas), `app/config.py`/`.env.example`/`render.yaml`/`docker-compose.yml`/
   `Dockerfile` atnaujinti (jokio bendro disko tarp web/worker). Integracinis testas
   `tests/test_storage_decoupling.py` (žymėtas `@pytest.mark.docker`, realiai paleistas ir PRAĖJO
   šioje sesijoje prieš tikrus Docker konteinerius — žr. testo docstring dėl `MOSTAI_DOCKERTEST_OVERRIDE`,
   reikalingo TIK šios sandboxo aplinkos proxy apribojimui, NE produkcijoje).
4. **DUOMENYS KOKYBĖS AUDITAS (svarbiausia dalis)** — pilnai atliktas 2 raundais (prieš/po taisymų),
   rezultatai ir pilnos 30+31 įrašų lentelės įrašytos `SOURCE_AUDIT.md` naujame skyriuje
   „Produkcinio patikimumo ir duomenų kokybės etapas“. Rasta ir ištaisyta 8 šaknies priežasčių
   klaidų (bendrinių dokumentų tarša aktualumo sprendimui, `specialist`/`priklausom` per platūs
   raktažodžiai, ≥3-bendrų-žodžių apgaulinga taisyklė, klaidingas terminas iš bendrinio dokumento,
   `application_end_raw` nesutapimas, aklas `min()` senai datai) — visos su regresijos testais
   (`tests/test_data_quality_fixes.py`, `tests/test_keywords_lt.py`).
5. **UI etapas** — naujas išvestinis (ne DB stulpelis) `Opportunity.processing_status`
   (`app/rules/processing_status.py`): `unprocessed_candidate` / `needs_review` / `confirmed`.
   Dashboard (`index.html`) turi etapo skirtukus, detalės puslapis (`detail.html`) rodo perspėjimą
   neapdorotiems/peržiūrai skirtiems įrašams vietoj spalvos ženkliuko.
6. **Rezultatas**: iš 83 pirminio scrape kandidatų, po taisymų pakartotas TAS PATS scrape davė 68
   kandidatų, iš kurių tik 18 pažymėti „confirmed“ (dar toliau: ~6-9/18 iš tų realiai tikslūs
   auditu patikrinus). Pilna, sąžininga metodika ir skaičiai — `SOURCE_AUDIT.md`.

## 2. Kas LIKO NEUŽBAIGTA

- **PLAN.md ir README.md** — pervadinta `blocked_bot_protection`→`blocked_in_current_runtime`
  visur (jau atlikta `sed`), BET NAUJAS skyrius apie šį etapą (analogiškas SOURCE_AUDIT.md 6a
  skyriui) **PLAN.md dar NEĮTRAUKTAS**. README.md „Žinomi apribojimai“ skyrius NEATNAUJINTAS
  naujoms komandoms (`make smoke-jra-vilnius`, `make test-storage-decoupling`, S3 konfigūracija,
  `processing_status` UI).
- **Pilnas priėmimo kriterijų (5 punktas iš užduoties) paleidimas NEATLIKTAS iki galo**:
  - `alembic upgrade head` prieš TIKRĄ PostgreSQL (per Docker Compose) šioje sesijoje
    NEPATIKRINTA — tik prieš SQLite (`audit.db`/`audit2.db`/`audit3.db`, visi laikini, gitignored,
    NEBUS commitinti).
  - `docker compose up` su TIKRU (ne testiniu `Dockerfile.dockertest`) image NEPALEISTAS šioje
    sesijoje po visų pakeitimų (Docker build lėtas šioje aplinkoje dėl proxy apribojimų — žr.
    `tests/test_storage_decoupling.py` docstring).
  - Green galimybių kontaktai + citatos UI/ataskaitoje atskirai NEPARENGTA (duomenys DB yra, bet
    atskiro santraukos dokumento/UI ekrano tam nesukurta).
- **PR į `main` NESUKURTAS** — vartotojas paprašė TIK saugiai commitinti/pushinti šią šaką, PR
  kūrimas — sekančios sesijos ar vartotojo sprendimas.
- **Žinomi neišspręsti apribojimai** (sąmoningai palikti, aprašyti SOURCE_AUDIT.md 5 skyriuje):
  žodžių dviprasmybė (homonimai: vaik/pedagog/dirbtuv/prevenc/jaunim), „rezultatai jau paskelbti“
  straipsniai nėra atskirai raudoni, `_pick_money` teoriškai turi tą pačią bendrinio dokumento
  taršos riziką kaip datos turėjo (bet konkretus realus atvejis NErastas, tad NEtaisyta).

## 3. Kurie failai pakeisti (žr. `git status`/`git diff` tiksliai)

Pilnas sąrašas — žr. `git log -1 --stat` po šio commit'o. Trumpai: `app/crawler/pipeline.py`,
`app/normalize/keywords_lt.py`, `app/crawler/runner.py`, `app/rules/processing_status.py` (naujas),
`app/models/opportunity.py`, `app/schemas/opportunity.py`, `app/web/routes_ui.py`,
`app/web/routes_api.py`, `app/web/templates/{index,detail,base}.html`, `app/crawler/adapters/
ltkt_table.py` (naujas), `app/crawler/availability_probe.py` (naujas), `app/storage/` (naujas),
`app/scripts/smoke_test_jra_vilnius.py` (naujas), `app/scripts/cleanup_documents.py`,
`app/models/source.py`, `app/seed/sources_seed.py`, `app/scheduler/jobs.py`, `app/config.py`,
`sources.yaml`, `render.yaml`, `docker-compose.yml`, `Dockerfile`, `.env.example`, `Makefile`,
`pyproject.toml`, `requirements.txt`, `.gitignore` (SVARBU: ištaisyta reali klaida — `storage/`
be pradinio `/` ignoravo VISĄ `app/storage/` katalogą; dabar `/storage/` ir `/data/`),
`alembic/versions/0001_initial_schema.py` (perrašytas, `0002_widen_crawl_run_status.py`
IŠTRINTAS — migracijų suglaudinimas, žr. failo docstring), testai (dauguma naujų arba pataisytų).

## 4. Ką TIKSLIAI daryti naujoje sesijoje (šia tvarka)

1. Perskaityti `SOURCE_AUDIT.md` naują skyrių (2 raundo auditas) ir šį failą.
2. Papildyti `PLAN.md` nauju skyriumi (analogiškai esamam 6a) — santrauka to, kas šiame HANDOFF
   1 skyriuje.
3. Atnaujinti `README.md` „Žinomi apribojimai“ + pridėti naujas Makefile komandas į atitinkamą
   skyrių.
4. Paleisti PILNĄ priėmimo patikrinimą: `make test` (109+ testų), `ruff check`/`ruff format --check`,
   švari PostgreSQL migracija per `docker compose` (TIKRU `Dockerfile`, ne `.dockertest` variantu —
   tas skirtas TIK šios sandboxo aplinkos proxy apribojimui), realus scrape prieš Kaunas/Skuodas/
   LTKT, atskiras `make smoke-jra-vilnius` paleidimas (jei įmanoma iš realios aplinkos).
5. Parengti trumpą green galimybių kontaktų/citatų santrauką (gali būti tiesiog SQL/Python skriptas,
   spausdinantis DB turinį — DB duomenys jau teisingi po šio etapo).
6. Sukurti Pull Request į `main` — TIK gavus aiškų vartotojo prašymą (jei jo dar nėra).

## 5. Kaip atkurti audito duomenis (jei reikia patikrinti pakartotinai)

```
rm -f audit.db && DATABASE_URL="sqlite+pysqlite:///./audit.db" alembic upgrade head
DATABASE_URL="sqlite+pysqlite:///./audit.db" python -m app.scripts.manual_scrape --source kaunas_naujienos
DATABASE_URL="sqlite+pysqlite:///./audit.db" python -m app.scripts.manual_scrape --source skuodas_wp_api
DATABASE_URL="sqlite+pysqlite:///./audit.db" python -m app.scripts.manual_scrape --source ltkt_organizacijoms
```

Šie `audit*.db` failai YRA `.gitignore`'inti (`*.db`) — niekada nebus commitinti.
