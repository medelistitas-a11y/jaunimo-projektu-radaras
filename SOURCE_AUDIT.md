# SOURCE_AUDIT.md — Šaltinių auditas

Paskutinis rankinis patikrinimas: **2026-09-02**, iš Claude Code debesies sesijos (per HTTPS
proxy). Visi žemiau esantys HTTP statusai yra realūs `curl` atsakymai (User-Agent
`Mozilla/5.0 (compatible; MostaiRadaras/0.1; +mailto:info@example.com)` arba galutinis
programos UA `MostaiGalimybiuRadaras/<ver> (+ADMIN_CONTACT_EMAIL)`), ne prielaidos. Kur
svetainė grąžina Cloudflare „Just a moment...“ JS iššūkio puslapį (HTTP 403, `cf-mitigated:
challenge`), tai pažymėta `blocked_bot_protection` — instrukcijos aiškiai draudžia apeiti
CAPTCHA/JS iššūkius, todėl šie šaltiniai NĖRA automatiškai crawlinami. Vietoj to programoje
yra „Rankinė peržiūra“ nuoroda (atidaro originalų URL) ir DB laukas apie blokavimą, matomas
Šaltinių sveikatos puslapyje.

## Privalomas pradinis rinkinys (5 punktai iš užduoties)

| # | Šaltinis | URL | Tipas | robots.txt | Būsena | Pastabos |
|---|---|---|---|---|---|---|
| 1 | Jaunimo reikalų agentūra, finansavimo konkursai | https://jra.lrv.lt/lt/finansavimo-konkursai/ | HTML sąrašas | Nepasiekiamas (CF iššūkis grąžinamas ir `/robots.txt`) | **blocked_bot_protection** | HTTP 403, `cf-mitigated: challenge`, Ray ID matomas atsakyme. Rankinė peržiūra registre. |
| 2 | Vilniaus konkursų sistema (jaunimo sritis įskaitant) | https://konkursai.vilnius.lt/konkursai | HTML/galimai JS | Nepasiekiamas (CF iššūkis) | **blocked_bot_protection** | HTTP 403 tiek pačiam puslapiui, tiek `vilnius.lt` domenui apskritai. |
| 3 | 60 savivaldybių svetainės | žr. lentelę žemiau | HTML/API | mišru | **12/60 pasiekiama tiesiogiai, 46/60 blocked_bot_protection, 2/60 tinklo klaida (reikia patikrinti rankiniu būdu iš kito tinklo)** | Žr. pilną lentelę. |
| 4 | LSA narių (savivaldybių) sąrašas | https://www.lsa.lt/nariai-savivaldybes/ | HTML | neblokuota (per Anthropic web fetch pavyko nuskaityti; nepatikrinta tiesioginiu HTTP) | **verified (via fetch tool)** | Naudotas kaip 60 savivaldybių domenų šaltinis (žr. žemiau, sąrašas įrašytas į `sources.yaml`). Reikėtų periodiškai perpatikrinti tiesioginiu HTTP kliento naudojimu produkcijoje. |
| 5 | Lietuvos kultūros taryba, organizacijoms | https://www.ltkt.lt/organizacijoms | HTML | leidžiama (WordPress/CMS, ne CF) | **verified (HTTP 200)** | Pasiekiama tiesioginiu `curl`. Jaunimo tema nėra pagrindinis fokusas (bendra kultūros/meno finansavimo institucija), todėl registre pažymėta kaip antrinis/stebimas šaltinis — aktualu, jei atsiranda konkreti su jaunimu susijusi programa (pvz. bendruomeniškumo, neformaliojo ugdymo kryptys). |
| 6 | Lietuvos kultūros kongresas | — | — | — | **neaktyvus / nepatikrintas šioje sesijoje** | Instrukcijos leidžia palikti kaip stebimą, jei nepatvirtinta, kad tai produktyvus finansavimo šaltinis. Šioje sesijoje neradome oficialaus, nuolat atnaujinamo kvietimų archyvo po šiuo pavadinimu (nesame tikri dėl domeno — nesugalvojame URL). **Veiksmas**: registre įrašytas kaip `status=needs_verification`, `source_type=unknown`, be `base_url` – administratorius turi įvesti tikrą URL, jei nori jį aktyvinti. Tai atitinka taisyklę „neišgalvoti URL“. |

## Cloudflare / bot-apsaugos pastaba (svarbu architektūrai)

Patikrinimo metu (žr. lentelę) **dauguma** `.lt` savivaldybių svetainių serveriuose veikia
Cloudflare su JS/„managed challenge“ apsauga, kuri grąžina HTTP 403 su „Just a moment...“
puslapiu net paprastam `robots.txt` užklausimui. Tai reiškia:

- Paprastas `httpx`/`curl` klientas šių svetainių nepasiekia.
- Playwright/Chromium *galėtų* techniškai praeiti dalį tokių iššūkių, tačiau tai laikytina
  bot-apsaugos apėjimu ir yra tiesiogiai draudžiama užduoties instrukcijose
  („Neapeik prisijungimo, CAPTCHA ar techninių blokavimų“). **Programa to nedaro.**
- Todėl architektūra numato trečią būseną (šalia „veikia“/„klaida“) — **„blocked_bot_protection“**
  — su aiškiu UI keliu: mygtukas „Atidaryti originalų puslapį“ + galimybė žmogui įrašyti radinį
  rankiniu būdu (planuojama `UserReview`/rankinio įrašo forma, MVP apimtyje: nuoroda + laukas
  pastaboms; pilna rankinio Opportunity kūrimo forma — tolimesnio etapo darbas, žymima README
  žinomuose apribojimuose).

## Visų 60 savivaldybių prieinamumo lentelė

Šaltinis domenams: LSA narių sąrašas (https://www.lsa.lt/nariai-savivaldybes/), patikrinta
per web-fetch įrankį 2026-09-02. HTTP statusas — tiesioginis `curl -L` patikrinimas tą pačią
dieną, `https://www.<domenas>/`, sekant redirect'us.

| Savivaldybė | Domenas | HTTP | Būsena |
|---|---|---|---|
| Akmenės r. | akmene.lt | 403 (CF) | blocked_bot_protection |
| Alytaus m. | ams.lt | 403 (CF) | blocked_bot_protection |
| Alytaus r. | arsa.lt | 403 (CF) | blocked_bot_protection |
| Anykščių r. | anyksciai.lt | 403 (CF) | blocked_bot_protection |
| Birštono | birstonas.lt | 403 (CF) | blocked_bot_protection |
| Biržų r. | birzai.lt | 200 | **accessible** |
| Druskininkų | druskininkusavivaldybe.lt | 200 | **accessible** |
| Elektrėnų | elektrenai.lt | 403 (CF) | blocked_bot_protection |
| Ignalinos r. | ignalina.lt | 403 (CF) | blocked_bot_protection |
| Jonavos r. | jonava.lt | 403 (CF) | blocked_bot_protection |
| Joniškio r. | joniskis.lt | 403 (CF) | blocked_bot_protection |
| Jurbarko r. | jurbarkas.lt | 403 (CF) | blocked_bot_protection |
| Kaišiadorių r. | kaisiadorys.lt | 200 | **accessible** |
| Kalvarijos | kalvarija.lt | 403 (CF) | blocked_bot_protection |
| **Kauno m.** | **kaunas.lt** | **200** | **accessible — naudota vertikaliame pjūvyje (generic HTML)** |
| Kauno r. | krs.lt | 000 (ryšio klaida) | needs_verification |
| Kazlų Rūdos | kazluruda.lt | 200 | **accessible** |
| Kelmės r. | kelme.lt | 403 (CF) | blocked_bot_protection |
| Kėdainių r. | kedainiai.lt | 403 (CF) | blocked_bot_protection |
| Klaipėdos m. | klaipeda.lt | 200 | **accessible** |
| Klaipėdos r. | klaipedos-r.lt | 403 (CF) | blocked_bot_protection |
| Kretingos r. | kretinga.lt | 403 (CF) | blocked_bot_protection |
| Kupiškio r. | kupiskis.lt | 403 (CF) | blocked_bot_protection |
| Lazdijų r. | lazdijai.lt | 403 (CF) | blocked_bot_protection |
| Marijampolės | marijampole.lt | 403 (CF) | blocked_bot_protection |
| Mažeikių r. | mazeikiai.lt | 403 (CF) | blocked_bot_protection |
| Molėtų r. | moletai.lt | 403 (CF) | blocked_bot_protection |
| Neringos | neringa.lt | 200 | **accessible** |
| Pagėgių | pagegiai.lt | 403 (CF) | blocked_bot_protection |
| Pakruojo r. | pakruojis.lt | 403 (CF) | blocked_bot_protection |
| Palangos m. | palanga.lt | 403 (CF) | blocked_bot_protection |
| Panevėžio m. | panevezys.lt | 403 (CF) | blocked_bot_protection |
| Panevėžio r. | panrs.lt | 403 (CF) | blocked_bot_protection |
| Pasvalio r. | pasvalys.lt | 200 | **accessible** |
| Plungės r. | plunge.lt | 200 | **accessible** |
| Prienų r. | prienai.lt | 403 (CF) | blocked_bot_protection |
| Radviliškio r. | radviliskis.lt | 403 (CF) | blocked_bot_protection |
| Raseinių r. | raseiniai.lt | 403 (CF) | blocked_bot_protection |
| Rietavo | rietavas.lt | 403 (CF) | blocked_bot_protection |
| Rokiškio r. | rokiskis.lt | 403 (CF) | blocked_bot_protection |
| **Skuodo r.** | **skuodas.lt** | **200** | **accessible — naudota vertikaliame pjūvyje (WordPress REST API adapteris, `wp-json/wp/v2/posts`)** |
| Šakių r. | sakiai.lt | 403 (CF) | blocked_bot_protection |
| Šalčininkų r. | salcininkai.lt | 403 (CF) | blocked_bot_protection |
| Šiaulių m. | siauliai.lt | 200 | **accessible** |
| Šiaulių r. | siauliuraj.lt | 403 (CF) | blocked_bot_protection |
| Šilalės r. | silale.lt | 403 | blocked_bot_protection |
| Šilutės r. | silute.lt | 403 (CF) | blocked_bot_protection |
| Širvintų r. | sirvintos.lt | 403 (CF) | blocked_bot_protection |
| Švenčionių r. | svencionys.lt | 403 (CF) | blocked_bot_protection |
| Tauragės r. | taurage.lt | 403 (CF) | blocked_bot_protection |
| Telšių r. | telsiai.lt | 403 (CF) | blocked_bot_protection |
| Trakų r. | trakai.lt | 403 (CF) | blocked_bot_protection |
| Ukmergės r. | ukmerge.lt | 403 (CF) | blocked_bot_protection |
| Utenos r. | utena.lt | 403 (CF) | blocked_bot_protection |
| Varėnos r. | varena.lt | 403 (CF) | blocked_bot_protection |
| Vilkaviškio r. | vilkaviskis.lt | 403 (CF) | blocked_bot_protection |
| Vilniaus m. | vilnius.lt | 403 (CF) | blocked_bot_protection |
| Vilniaus r. | vilniaus-r.lt | 000 (ryšio klaida) | needs_verification |
| Visagino m. | visaginas.lt | 200 | **accessible** |
| Zarasų r. | zarasai.lt | 403 (CF) | blocked_bot_protection |

**Santrauka: sėkmingai patikrinta prieinama tiesiogiai 12/60 (20%), blokuota bot-apsaugos
46/60 (77%), reikia papildomo rankinio patikrinimo 2/60 (3%, tinklo klaida iš šios aplinkos —
`krs.lt` ir `vilniaus-r.lt`, tikėtina DNS/TLS ypatumas per proxy, ne būtinai realus
blokavimas).** Šis skaičius rodomas programos „Šaltiniai“ vaizde tiksliai tokiu pavidalu
(„sėkmingai patikrinta 12/60“), o ne klaidinančiu „visi veikia“.

## Vertikalaus pjūvio šaltiniai (faktiškai įdiegti šiame etape)

| Atvejis iš instrukcijų | Pasirinktas realus šaltinis | Adapteris | Būsena |
|---|---|---|---|
| JRA finansavimo konkursai + 1 dokumentas | jra.lrv.lt/lt/finansavimo-konkursai/ | — | **blocked_bot_protection**, registruota, rankinės peržiūros nuoroda. Dokumento pavyzdys pakeistas sintetiniu PDF fixture testams (žr. žemiau). |
| Vilniaus konkursų sistema | konkursai.vilnius.lt/konkursai | — | **blocked_bot_protection**, registruota, rankinės peržiūros nuoroda. |
| Savivaldybė su paprastu HTML naujienų sąrašu | **kaunas.lt** — https://www.kaunas.lt/kategorija/naujienos/ | `generic_html` | **veikia**, realus HTTP 200, realus turinys. Selektoriai (`list_item_selector: .content_block.box_inner`, `link_selector: .content_title a`, `detail_content_selector: .content_block.box_inner`) nustatyti ir patikrinti prieš tikrą HTML 2026-09-02 po pradinio klaidingo `article` spėjimo — žr. „Realaus paleidimo rezultatai“ skyrių žemiau. |
| Savivaldybė su JS/nestandartiniu adapteriu | **skuodas.lt** — https://skuodas.lt/wp-json/wp/v2/posts | `wp_json` | **veikia**, realus HTTP 200, realus JSON turinys (patikrinta `?search=jaunim` paieška). Pasirinkta vietoj tikro JS-SPA atvejo, nes patikrinus visus 12 pasiekiamų savivaldybių svetainių, nė viena nėra kliento pusėje (React/Vue/Nuxt) generuojama SPA — visos yra serverio pusės CMS (dažniausiai WordPress arba panašus). `js_playwright.py` adapteris VIS TIEK įgyvendintas ir padengtas testu su vietiniu sintetiniu JS puslapiu (žr. `tests/fixtures/js_rendered.html` + `tests/test_js_adapter.py`), kad architektūra būtų paruošta realiam JS atvejui, jei toks atsirastų ateityje kitose (ne savivaldybių) svetainėse. |
| 1 PDF + 1 DOCX | Sintetiniai testiniai failai `tests/fixtures/sample.pdf`, `tests/fixtures/sample.docx`, `tests/fixtures/scanned_no_text.pdf` | `pdf_extract`, `docx_extract`, `ocr` | Sukurti šios sesijos metu, jokių realių organizacijų duomenų. Realaus gyvo PDF/DOCX atsisiuntimas priklauso nuo crawl rezultatų kaunas.lt/skuodas.lt — kodas tai palaiko bendrai (bet kuris rastas PDF/DOCX bus apdorotas ta pačia funkcija). |
| Atvejis, kai MB negali būti pareiškėja, bet gali būti mokymų tiekėja | Sintetinis fixture `tests/fixtures/vsi_only_call.html` (imituoja tipinį kvietimą „paraiškas gali teikti tik VšĮ, asociacijos ar biudžetinės įstaigos“) | taisyklių variklis | Testas `test_rules_eligibility.py::test_mb_cannot_apply_but_can_be_vendor`. |

## Papildomi patikrinti šaltiniai (neprivalomi, bet naudingi)

- `ltkt.lt/organizacijoms` — HTTP 200, pridėta registre kaip antrinis/stebimas šaltinis (žr. lentelę aukščiau).

## Realaus paleidimo rezultatai (2026-09-02, ta pati sesija)

Po vertikalaus pjūvio įgyvendinimo paleistas TIKRAS `POST /api/crawl/run` (per lokaliai
paleistą `uvicorn`, ne mock) prieš realius `kaunas_naujienos` ir `skuodas_wp_api` šaltinius:

- Pirmas bandymas: `{"status":"completed","new":60}` — atrodė sėkmingai, BET vėlesnė patikra
  (žr. žemiau) atskleidė, kad `kaunas_naujienos` adapterio `list_item_selector: "article"`
  buvo spėtas, o ne patikrintas prieš realų HTML, ir kaunas.lt apskritai neturi `<article>`
  žymų — adapteris arba grąžindavo 0 elementų, arba (dažniau) vieną klaidingą "elementą" iš
  viso puslapio meniu teksto. Faktiškai beveik visos tuo metu užfiksuotos 60 galimybių buvo
  iš `skuodas_wp_api`.
- **Taisymas**: rastas realus kaunas.lt naujienų kortelių selektorius (`.content_block.box_inner`
  su nuoroda `.content_title a`), patikrinus tikrą atsisiųstą HTML. Papildomai rasta ir ištaisyta:
  (a) `extract_page` neturėjo `<main>` atsarginio varianto apsaugos nuo `<nav>/<header>/<footer>
  /<aside>` turinio — be `<main>` žymos (kaip kaunas.lt atveju) visas svetainės meniu patekdavo
  į "straipsnio tekstą", klaidindamas raktažodžių filtrą (pvz. meniu punktas "Korupcijos
  prevencija" duodavo klaidingą "prevenc" signalą); (b) pridėtas `detail_content_selector`
  adapter_config laukas tiksliam turinio apribojimui; (c) vieno bendro/administracinio
  raktažodžio (pvz. vien "projektas" ar "partneris") nebepakanka aktualumo filtrui — reikia arba
  bent vieno specifinio (jaunimo/mokymų temos) signalo, arba kelių bendrų signalų kartu, nes
  realiame sraute administraciniai žodžiai pasitaiko beveik kiekviename straipsnyje.
- **Po taisymo, pakartotinis pilnas paleidimas**: `{"status":"completed","new":65}` (2 šaltiniai,
  0 klaidų, 9 nauji pranešimai). Pasiskirstymas: 8 žalios, 57 geltonos, 0 raudonų šiame konkrečiame
  paleidime. kaunas_naujienos šįkart teisingai grąžino 6 realius naujienos straipsnius (patikrinta
  rankiniu būdu, palyginus su faktiniu svetainės turiniu) — vienas iš jų (apie darželio atidarymą)
  liko pažymėtas aktualiu dėl teisėto "vaik*" signalo, likusieji filtruoti teisingai.
- **Sąžininga pastaba dėl raktažodžių filtro ribų**: net po taisymo, kai kurie straipsniai
  (pvz. interviu su grindų meistru, kuriame paminėtas "pedagogas") vis dar praeina filtrą dėl
  homonimų/atsitiktinių paminėjimų — tai grynai raktažodžių-kamienų metodo riba, ne šio konkretaus
  paleidimo klaida; sistema tokius atvejus pažymi žema pasitikėjimo geltona spalva žmogaus
  peržiūrai, niekada TAIP/NE be citatos. Pilnas NLP kontekstinis supratimas priklauso nuo
  pasirenkamo LLM klasifikatoriaus (žr. app/llm/), kuris NĖRA privalomas MVP veikimui.
- CSV eksportas patikrintas: UTF-8 BOM + lietuviški simboliai atsidaro korektiškai.
- Iš viso šio galutinio patikrinimo etapo metu rasta ir ištaisyta septyni realūs kodo trūkumai
  (pinigų normalizavimas su neskaidomu tarpu; per trumpas `crawl_runs.status` PostgreSQL
  stulpelis; sugadinta bcrypt hash dėl Docker Compose `$` interpoliacijos; Dekarto sandaugos
  klaida `color`+`eligibility` filtrų derinyje; dokumento ekstrakcija vykdavo PRIEŠ dedup
  patikrą; neteisingas kaunas.lt adapterio selektorius; trūkstamas `<nav>` turinio filtras) —
  visi aprašyti `PLAN.md` 6a skyriuje ir atitinkamuose git commit'uose.
- `docker compose up --build` realiai paleistas DU KARTUS prieš tikrą PostgreSQL (ne tik SQLite
  testuose) — migracijos (0001+0002), web ir worker servisai pasileido be klaidų; taip pat
  patikrinta pilna autentifikacijos eiga (401/401/200 be kredencialų, su neteisingais, su
  teisingais).

## Atnaujinimo tvarka

Šis failas turi būti atnaujinamas po kiekvieno reikšmingo šaltinių registro pakeitimo arba bent
kartą per 60 savivaldybių plėtros etapą (10-as darbo etapas). Kiekvienas naujas šaltinis prieš
patenkant į `sources.yaml` turi turėti bent vieną čia užfiksuotą sėkmingą rankinį patikrinimą su
data ir HTTP statusu — jokie URL neįtraukiami „iš atminties“.
