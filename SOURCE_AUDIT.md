# SOURCE_AUDIT.md — Šaltinių auditas

Paskutinis rankinis patikrinimas: **2026-09-02**, iš Claude Code debesies sesijos (per HTTPS
proxy). Visi žemiau esantys HTTP statusai yra realūs `curl` atsakymai (User-Agent
`Mozilla/5.0 (compatible; MostaiRadaras/0.1; +mailto:info@example.com)` arba galutinis
programos UA `MostaiGalimybiuRadaras/<ver> (+ADMIN_CONTACT_EMAIL)`), ne prielaidos. Kur
svetainė grąžina Cloudflare „Just a moment...“ JS iššūkio puslapį (HTTP 403, `cf-mitigated:
challenge`), tai pažymėta `blocked_in_current_runtime` — instrukcijos aiškiai draudžia apeiti
CAPTCHA/JS iššūkius, todėl šie šaltiniai NĖRA automatiškai crawlinami. Vietoj to programoje
yra „Rankinė peržiūra“ nuoroda (atidaro originalų URL) ir DB laukas apie blokavimą, matomas
Šaltinių sveikatos puslapyje.

## Produkcinio patikimumo ir duomenų kokybės etapas (2026-09-02, atskira šaka)

**Svarbiausia išvada iš anksčiau šiame faile užfiksuoto „65 realios galimybės“ paleidimo:
tai buvo NETEISINGAS, per daug pasitikintis apibūdinimas.** Rankinis auditas (žr. žemiau)
parodė, kad dauguma tų 65 (ir vėlesnio, prieš taisymus perkrautų 83) įrašų buvo TIK
raktažodžių sutapimai, ne realios MB „Mostai“ aktualios galimybės. Šis skyrius dokumentuoja
auditą, rastas klaidas, jų taisymus ir PAKARTOTINĮ auditą po taisymų.

### 1. Duomenų kokybės auditas — 1 raundas (prieš taisymus)

Prieš bet kokius pakeitimus paleistas realus scrape prieš `kaunas_naujienos`, `skuodas_wp_api`
ir naują `ltkt_organizacijoms` (LTKT) šaltinius: iš viso **83 Opportunity įrašai** (5 iš
kaunas.lt, 60 iš skuodas.lt, 18 iš ltkt.lt). Proporcinga, bet praktiškai PILNA imtis: visi 5
kaunas.lt įrašai + atsitiktinai (seed=42) parinkti 10/18 ltkt.lt + 15/60 skuodas.lt = **30
įrašų**, kiekvienas rankiniu būdu palygintas su realiu ištrauktu to paties puslapio tekstu
(saugomu `Document`/`Evidence` lentelėse, patikrintu pakartotiniu HTTP užklausimu prieš tą
patį URL).

| # | Pavadinimas (sutrumpinta) | Šaltinis | Realus konkursas/projektas? | Aktualu „Mostai“? | Reali pardavimo galimybė? | Spalva teisinga? | Terminas/biudžetas/kontaktas teisingi? | Klaidos priežastis |
|---|---|---|---|---|---|---|---|---|
| 1 | Skulptūros simpoziumas | kaunas.lt | Ne (naujiena) | Ne | Ne | Ne (geltona vietoj –) | – | Bendras naujienų straipsnis, jokio finansavimo/mokymų signalo |
| 2 | „Audra“ meno paroda | kaunas.lt | Ne (naujiena) | Ne | Ne | Ne | – | Tas pats |
| 3 | Darželio „Vėjukai“ atidarymas | kaunas.lt | Ne (naujiena) | Ne | Ne | Ne | – | Silpnas vieno žodžio „vaik“ sutapimas |
| 4 | Apžvalgos ratas Kaune | kaunas.lt | Ne (naujiena) | Ne | Ne | Ne | – | Silpni sutapimai („šeim“, „konsultacij“) be konteksto |
| 5 | Interviu apie parketą | kaunas.lt | Ne (naujiena) | Ne | Ne | Ne | – | Homonimas „pedagog“ (ne apie mokymus) |
| 6 | LTKT „Literatūra“ | ltkt.lt | Taip | Ne (meno finansavimas) | Ne | Ne (žalia, turėtų būti bent geltona/neaišku) | Terminas teisingas | Bendras kontaktų blokas „specialistė“ sukėlė aktualumą |
| 7 | LTKT „Architektūra“ | ltkt.lt | Taip | Ne | Ne | Ne (žalia) | Terminas teisingas | Tas pats bendrinis kontaktų blokas |
| 8 | LTKT „Profesionaliojo scenos meno sklaida“ | ltkt.lt | Taip | Ne | Ne | Ne (žalia) | Terminas teisingas | Bendrinis prijungtas vertinimo kriterijų PDF |
| 9 | LTKT „Strateginis finansavimas: asociacijos“ | ltkt.lt | Taip | Ne | Neaišku | Iš dalies (geltona pagrįsta) | Terminas teisingas | – |
| 10 | LTKT „Tinklaveika“ | ltkt.lt | Taip | Iš dalies (mini mokymus/seminarus) | Taip (su partneriu) | Taip | Terminas teisingas | – |
| 11 | LTKT „Dizainas ir taikomieji menai“ | ltkt.lt | Taip | Ne | Ne | Ne (žalia) | Terminas teisingas | Bendrinis kontaktų blokas |
| 12 | LTKT „Atminties institucijos“ | ltkt.lt | Taip | Ne | Ne | Ne (žalia) | Terminas teisingas | Bendrinis kontaktų blokas |
| 13 | LTKT „Cirkas ir šokis“ | ltkt.lt | Taip | Ne | Ne | Ne (žalia) | Terminas teisingas | Bendrinis kontaktų blokas |
| 14 | LTKT „Strateginis finansavimas: tarptautiniai renginiai“ | ltkt.lt | Taip | Ne | Neaišku | Iš dalies | Terminas teisingas | – |
| 15 | LTKT „Strateginis meno kūrėjų organizacijų finansavimas“ | ltkt.lt | Taip | Ne | Ne | Ne (žalia) | Terminas teisingas | Homonimas „priklausom“ = „priklausomai nuo“, ne priklausomybė |
| 16 | Vandens saugumo prevencija | skuodas.lt | Ne (informacinis pranešimas) | Ne | Ne | Ne | – | Silpnas „prevenc“ sutapimas be tikro pardavimo pagrindo |
| 17 | Žemės ūkio programos paraiškos | skuodas.lt | Taip | Ne | Ne | Ne | Terminas teisingas | Prijungti bendriniai dokumentai (formos) sukėlė aktualumą |
| 18 | Sveikatos/savijautos veiklos | skuodas.lt | Ne (informacinis) | Iš dalies | Ne | Ne | – | Silpni sutapimai |
| 19 | **NVO veiklos stiprinimo kvietimas** | skuodas.lt | **Taip** | **Taip** | **Taip** | **Taip** | Taip | — TEISINGAS ĮRAŠAS (eligibility=ne teisingai, sales nepriklausomai geltona) |
| 20 | Rūkymo metimo linija | skuodas.lt | Ne (PSA) | Ne | Ne | Ne | – | Silpni sutapimai |
| 21 | Sporto projektų konkursas | skuodas.lt | Taip | Ne (sportas, ne mokymai) | Ne | Iš dalies | **NE — terminas „iki kovo 26 d.“ virto „2025-05-18“** | Bendrinio dokumento data nustelbė teisingą |
| 22 | Religinių bendruomenių finansavimas | skuodas.lt | Taip | Ne | Ne | Ne | Terminas teisingas | – |
| 23 | Lietuvių kalbos dienos | skuodas.lt | Ne (renginys) | Ne | Ne | Ne | – | – |
| 24 | „Miško maudynės“ suaugusiems | skuodas.lt | Ne (renginys suaugusiems) | Ne | Ne | Ne | – | – |
| 25 | Suaugusiųjų mokymosi savaitė | skuodas.lt | Iš dalies (renginys) | Iš dalies | Ne (per bendra) | Iš dalies | – | – |
| 26 | Žemės ūkio ataskaita (jau baigta) | skuodas.lt | Ne (ataskaita, ne kvietimas) | Ne | Ne | Ne | **NE — ta pati klaidinga „2025-05-18“ data** | – |
| 27 | Piešinių konkursas vaikams (saugumo projektas) | skuodas.lt | Taip (bet vaikams, ne „Mostai“ mokymams) | Ne | Ne | Ne | – | – |
| 28 | Deinstitucionalizacijos susitikimo ataskaita | skuodas.lt | Ne (jau įvykęs susitikimas) | Ne | Ne | Ne | – | – |
| 29 | „Paaiškėjo, kuriems projektams skirtas finansavimas“ | skuodas.lt | **Ne — rezultatai JAU paskelbti**, ne atviras kvietimas | Ne | Ne | **Ne — turėtų būti raudona/„reikia peržiūros“, ne geltona kaip aktyvi galimybė** | – | Tekstas praeityje, sistema to nepastebėjo |
| 30 | **VSRSP sveikatos konkursas** | skuodas.lt | **Taip** | **Taip** (prevencija/sveikata) | **Taip** | Iš dalies | **NE — ta pati klaidinga „2025-05-18“ data** | Bendrinio dokumento data |

**1 raundo rezultatas: iš 30 patikrintų įrašų tik 2 (eilutės 19, 30) buvo aiškiai teisingi,
dar ~2–3 ribiniai/iš dalies teisingi (9, 10, 14, 25), likę ~25 (≈83%) buvo klaidingi teigiami
arba turėjo neteisingą terminą.** T. y. **tikslumas (precision) ≈ 7–17%, klaidingų teigiamų
dažnis ≈ 83–90%** priklausomai nuo to, ar ribiniai atvejai skaičiuojami kaip teisingi.

### 2. Rastos ir ištaisytos šaknies priežastys

1. **Bendrinių prijungtų dokumentų tarša aktualumo sprendimui.** Prie DAUGELIO tarpusavyje
   nesusijusių skelbimų (LTKT — bendri vertinimo kriterijų PDF; skuodas.lt — bendros paraiškų
   formos) buvo prijungti TIE PATYS bendriniai dokumentai, kurių standartinė kalba
   („specialistų kompetencija“, „socialinė nauda“) klaidingai pažymėdavo VISIŠKAI nesusijusius
   skelbimus aktualiais. **Taisymas**: aktualumo sprendimas (`is_relevant_candidate`) dabar
   VISADA priimamas tik pagal PATIES puslapio tekstą (`page_text`), o ne pagal puslapį+dokumentus
   kartu — žr. `app/crawler/pipeline.py::process_candidate`. Dokumentų tekstas toliau naudojamas
   datų/pinigų/citatų ištraukimui jau priimtiems kandidatams.
2. **„specialist“ raktažodis per bendras.** LTKT kiekvieno konkurso puslapio kontaktų blokas
   („Vyriausioji specialistė ... tel. ...“) vien pats savaime pažymėdavo puslapį aktualiu.
   **Taisymas**: `specialist` perkeltas į bendrų/administracinių žodžių sąrašą (žr.
   `app/normalize/keywords_lt.py`), analogiškai anksčiau ištaisytam `kvalifikacij`.
3. **„priklausom“ per platus kamienas.** Sutapdavo su bendru žodžiu „priklausomai (nuo)“ =
   „depending (on)“, ne tik su „priklausomybė“ (narkotikų/alkoholio). **Taisymas**: kamienas
   susiaurintas iki `priklausomyb`.
4. **≥3 bendrų administracinių žodžių „pakanka“ taisyklė beveik nieko nefiltravo.** BET KURIS
   finansavimo kvietimas BET KURIA tema savaime paminės „konkursas/kvietimas/finansavimas/
   projektas/partneris“ kelis kartus vien dėl žanro. **Taisymas**: `is_relevant_candidate` DABAR
   visada reikalauja bent vieno SPECIFINIO (ne administracinio) signalo — bendrų žodžių,
   nesvarbu kiek, savaime nepakanka.
5. **Klaidingas terminas iš bendrinio dokumento.** `min()` iš VISŲ tekste (puslapis+dokumentai)
   rastų „iki <data>“ terminų klaidingai rinkdavosi bendriniame priede rastą, visiškai
   nesusijusią datą (pvz. „iki 2025-05-18“), nustelbdamas teisingą, straipsnio TEKSTE esantį
   terminą. **Taisymas**: terminas visada renkamas pirmiausia iš PATIES puslapio teksto (žr.
   `_pick_dates` su `primary_text` parametru); dokumentų tekstas naudojamas TIK jei puslapyje
   jokio termino apskritai nėra.
6. **`application_end_raw` nesutapdavo su realiai pasirinktu `application_end`.** Buvo imamas
   tiesiog PIRMAS rastas datos tekstas visame tekste, ne tas, kuris atitiko pasirinktą min()
   datą — UI galėjo rodyti, pvz., nesusijusią 2023 m. datą prie teisingai apskaičiuotos 2026 m.
   datos. **Taisymas**: `application_end_raw` dabar visada kildinamas iš TOS PAČIOS datos, kuri
   tapo `application_end`.
7. **Aklas `min()` renkasi SENĄ, jau praėjusią datą vietoj realios būsimos.** Kai tekste yra ir
   sena (pvz. kito dokumento patvirtinimo data), ir reali būsima paraiškų data, abi pažymėtos
   „iki“ žymeniu — aklas min() rinkdavosi absoliučiai ankstyviausią, ne aktualią. **Taisymas**:
   pirmenybė ankstyviausiam DAR NEPRAĖJUSIAM terminui, grįžtama prie absoliutaus min() tik jei
   visi rasti terminai jau praėję.
8. **Rezultatų-jau-paskelbta straipsniai rodomi kaip aktyvios galimybės.** Sistemingai
   nesprendžiama atskirai (žinomas likutinis apribojimas — žr. žemiau), BET UI lygmenyje dabar
   toks įrašas (silpnas `sales.confidence=35` numatytosios atsargios šakos signalas) automatiškai
   patenka į „Reikia žmogaus peržiūros“, o ne rodomas kaip patvirtinta galimybė (žr. 3 skyrių).

Visi 8 taisymai turi atskirus regresijos testus: `tests/test_keywords_lt.py`,
`tests/test_data_quality_fixes.py`. Pilnas testų komplektas (109 testai) praeina po taisymų.

### 3. Naujas UI/duomenų etapas: „Neapdorotas kandidatas“ / „Reikia peržiūros“ / „Patvirtinta“

Kadangi net po (2) taisymų kai kurie silpni, dviprasmiški vienažodžiai sutapimai (homonimai,
pvz. „vaik“ darželio straipsnyje, „pedagog“ interviu apie grindis) VIS TIEK sukuria Opportunity
įrašą, pridėtas **naujas, iš jau esamų vertinimo laukų IŠVESTINIS** (ne naujas DB stulpelis)
`Opportunity.processing_status` — žr. `app/rules/processing_status.py`:

- **„Neapdorotas kandidatas“** — taisyklių variklis NERADO jokios citatos tinkamumui (jokio
  `Evidence` įrašo, `EligibilityAssessment.confidence` žemiausiame „nėra signalo“ lygyje).
- **„Reikia žmogaus peržiūros“** — galimas dublikatas, arba tiek tinkamumo, tiek pardavimo
  vertinimai silpni/numatytieji-atsargūs (apima ir „rezultatai jau paskelbti“ atvejus, žr. 8
  punktą aukščiau).
- **„Patvirtinta galimybė“** — pakankamai patikimas vertinimas su realia citata; TIK šis lygis
  rodomas su žalia/geltona/raudona spalva pagrindiniame sąraše.

Dashboard (`/`) dabar turi atskirus etapo skirtukus su skaičiais, o detalės puslapyje
neapdoroti/peržiūrai skirti įrašai rodomi su aiškiu perspėjimu, NE su spalvos ženkleliu — žr.
`app/web/templates/index.html`, `detail.html`.

### 4. Duomenų kokybės auditas — 2 raundas (po taisymų, TAS PATS metodas)

Po visų aukščiau aprašytų taisymų paleistas TAS PATS scrape iš naujos, švarios DB prieš tuos
pačius 3 šaltinius:

| Šaltinis | Kandidatų PRIEŠ | Kandidatų PO | Pokytis |
|---|---|---|---|
| kaunas_naujienos | 5 | 5 | 0 (žr. žemiau — likę homonimai, dabar „neapdorota“) |
| skuodas_wp_api | 60 | 56 | −4 |
| ltkt_organizacijoms | 18 | 7 | **−11 (61% sumažėjimas)** |
| **Iš viso Opportunity įrašų** | **83** | **68** | **−15** |

Iš 68 naujų įrašų, pagal `processing_status`:

| Etapas | Kiekis | % |
|---|---|---|
| Patvirtinta galimybė (rodoma spalva) | 18 | 26% |
| Reikia žmogaus peržiūros | 3 | 4% |
| Neapdorotas kandidatas | 47 | 69% |

**Tai yra sąžiningas, tikras skaičius: iš 68 po-taisymų surinktų kandidatų TIK 18 rodomi kaip
patvirtintos pardavimo galimybės — NE 65, NE 83, ir NET NE visi 18 nėra idealiai tikslūs (žr.
žemiau), bet UI DABAR aiškiai atskiria šį skirtumą, o ne rodo visus 68 kaip vienodai
„galimybes“.**

Pakartotinis rankinis auditas TŲ PAČIŲ kriterijų: visi 18 „patvirtinta“ įrašų + visi 3 „reikia
peržiūros“ + atsitiktinė (seed=7) 10 iš 47 „neapdorotų“ imtis = **31 įrašas**.

- **„Patvirtinta“ (18 įrašų)**: rankiniu būdu palyginus su originaliais puslapiais — **6/18
  aiškiai teisingi** (NVO veiklos stiprinimas ×2, „jaunimo ir visuomenės aktyvinimo programa“,
  „Demokratinė kultūros mokykla“, „neformaliojo vaikų švietimo programų finansavimas“, LTKT
  „Tinklaveika“ su realiu mokymų/seminarų finansavimu), **3/18 ribiniai** (sporto konkursas,
  sveikatos VSRSP konkursas, tarpkartinis IT įgūdžių NVO projektas — visų trijų DATOS DABAR
  TEISINGOS), **9/18 liko klaidingi teigiami** (dauguma likusių LTKT meno/kultūros konkursų,
  žemės ūkio, medžiojamųjų gyvūnų žalos prevencijos, religinių bendruomenių finansavimas — šie
  turi realų specifinį raktažodžio signalą PAČIAME puslapio tekste, pvz. „prevencija“
  konservavimo, ne sveikatos, prasme, arba „jaunim“ literatūros žanro kontekste — žinomas
  likutinis apribojimas, žr. 5 skyrių).
  **Tikslumas „Patvirtinta“ grupėje: ≈33–50% (6–9 iš 18), pagerėjimas nuo ≈7–17% 1 raunde.**
- **„Reikia peržiūros“ (3 įrašai)**: visi trys teisingai pažymėti kaip neaiškūs/dublikatai/
  silpni — teisinga triaža, joks NEPATEKO kaip klaidingai „patvirtintas“.
- **„Neapdorota“ (10 atsitiktinai patikrintų iš 47)**: visi 10 iš tikrųjų BUVO tik silpni
  raktažodžių sutapimai (naujienos, PSA pranešimai, ataskaitos apie jau įvykusius dalykus) — TAI
  YRA TEISINGA triaža: **0/10 klaidingai nuvertintų realių galimybių šioje imtyje.**

### 5. Sąžiningai likę apribojimai (NEIŠSPRĘSTA šiame etape)

- **Žodžių dviprasmybė be pilno konteksto.** „vaik“ (darželis), „pedagog“ (interviu apie
  grindis), „dirbtuv“ (dailininko studija vs. mokymų dirbtuvės), „prevenc“ (kultūros paveldo
  KONSERVAVIMO prevencija vs. socialinė/sveikatos prevencija), „jaunim“ (literatūros/meno ŽANRO
  apibūdinimas vs. tikslinė jaunimo grupė) — visa tai realūs lietuvių kalbos homonimai/
  daugiareikšmiai žodžiai, kurių pilnas atskyrimas reikalauja tikro NLP konteksto supratimo, ne
  vien kamienų atitikimo. Sistema šiuos atvejus dabar ARBA atmeta (jei nėra jokio kito
  specifinio signalo), ARBA pažymi „Neapdorotas kandidatas“/„Reikia peržiūros“ (jei silpnas
  pasitikėjimas) — bet retkarčiais (kaip matyti 2 raunde) vis tiek pasiekia „Patvirtinta“, jei
  citata rasta. **Rekomendacija**: pasirenkamas LLM klasifikatorius (`app/llm/`, reikalauja
  `ANTHROPIC_API_KEY`) sprendžia būtent šią klasę atvejų, bet NĖRA privalomas MVP veikimui.
- **„Rezultatai jau paskelbti“ straipsniai** nėra atskirai aptinkami kaip UŽDARYTOS (ne
  aktyvios) galimybės — jie patenka į „Reikia peržiūros“ per silpną `sales.confidence`, bet
  nėra automatiškai pažymimi raudona spalva su aiškia priežastimi „rezultatai jau paskelbti“.
- **`_pick_money` (biudžeto suma)** naudoja tą pačią „didžiausia suma = bendras biudžetas“
  euristiką iš PILNO teksto (puslapis+dokumentai), NE tik puslapio — ta pati bendrinio dokumento
  taršos rizika, kuri buvo ištaisyta datoms, TEORIŠKAI galima ir pinigų sumoms, bet ŠIAME etape
  NEBUVO rastas konkretus realus atvejis, patvirtinantis klaidą (skirtingai nei datos atveju),
  todėl fix'as neįtrauktas — pažymima kaip žinoma rizika tolimesniam auditui.

## Privalomas pradinis rinkinys (5 punktai iš užduoties)

| # | Šaltinis | URL | Tipas | robots.txt | Būsena | Pastabos |
|---|---|---|---|---|---|---|
| 1 | Jaunimo reikalų agentūra, finansavimo konkursai | https://jra.lrv.lt/lt/finansavimo-konkursai/ | HTML sąrašas | Nepasiekiamas (CF iššūkis grąžinamas ir `/robots.txt`) | **blocked_in_current_runtime** (NE „disabled“ — žr. žemiau) | HTTP 403, `server: cloudflare`, `cf-mitigated: challenge`, „Just a moment...“ tekstas atsakyme. Alternatyvus oficialus šaltinis: `socmin_projektu_konkursai` (socmin.lrv.lt, susietas per `alternative_source_of`). Savaitinis automatinis pasiekiamumo patikrinimas — žr. `app/crawler/availability_probe.py`. Atskiras smoke testas: `make smoke-jra-vilnius`. |
| 2 | Vilniaus konkursų sistema (jaunimo sritis įskaitant) | https://konkursai.vilnius.lt/konkursai | HTML/galimai JS | Nepasiekiamas (CF iššūkis) | **blocked_in_current_runtime** (NE „disabled“) | HTTP 403 tiek pačiam puslapiui, tiek `vilnius.lt` domenui apskritai. Ieškota (bet nerasta veikianti) oficiali alternatyva — patikrinta `sopas1.sppd.lt` (tik prisijungusiems, netinka), nerasta atskira Vilniaus m. savivaldybės naujienų RSS/API be CF. Tas pats savaitinis auto-patikrinimas ir `make smoke-jra-vilnius` kaip JRA. |
| 3 | 60 savivaldybių svetainės | žr. lentelę žemiau | HTML/API | mišru | **12/60 pasiekiama tiesiogiai, 46/60 blocked_in_current_runtime, 2/60 tinklo klaida (reikia patikrinti rankiniu būdu iš kito tinklo)** | Žr. pilną lentelę. |
| 4 | LSA narių (savivaldybių) sąrašas | https://www.lsa.lt/nariai-savivaldybes/ | HTML | neblokuota (per Anthropic web fetch pavyko nuskaityti; nepatikrinta tiesioginiu HTTP) | **verified (via fetch tool)** | Naudotas kaip 60 savivaldybių domenų šaltinis (žr. žemiau, sąrašas įrašytas į `sources.yaml`). Reikėtų periodiškai perpatikrinti tiesioginiu HTTP kliento naudojimu produkcijoje. |
| 5 | Lietuvos kultūros taryba, organizacijoms | https://www.ltkt.lt/organizacijoms/konkursai | HTML lentelė | leidžiama (PHP/CMS, ne CF) | **active, verified (HTTP 200), realiai nuskaityta** | Dedikuotas `ltkt_table` adapteris (`app/crawler/adapters/ltkt_table.py`), parsina `<table>` struktūrą, gerbia `<base href>` nuorodų skaičiavimui (žr. duomenų kokybės auditą aukščiau — realus rastas nuorodų dubliavimo klaidos atvejis). Jaunimo tema NĖRA pagrindinis LTKT fokusas — reikalaujamas specifinis jaunimo/mokymų/psichikos sveikatos/prevencijos/specialistų kompetencijos signalas PAČIAME puslapio tekste, ne vien bendras kultūros/meno finansavimas (žr. duomenų kokybės auditą: po taisymų iš 18 realiai atrastų LTKT konkursų liko 7 kandidatai). Fixture testas: `tests/test_ltkt_adapter.py`; gyvas smoke testas: `@pytest.mark.live`. |
| 6 | Lietuvos kultūros kongresas | — | — | — | **neaktyvus / nepatikrintas šioje sesijoje** | Instrukcijos leidžia palikti kaip stebimą, jei nepatvirtinta, kad tai produktyvus finansavimo šaltinis. Šioje sesijoje neradome oficialaus, nuolat atnaujinamo kvietimų archyvo po šiuo pavadinimu (nesame tikri dėl domeno — nesugalvojame URL). **Veiksmas**: registre įrašytas kaip `status=needs_verification`, `source_type=unknown`, be `base_url` – administratorius turi įvesti tikrą URL, jei nori jį aktyvinti. Tai atitinka taisyklę „neišgalvoti URL“. |

## Cloudflare / bot-apsaugos pastaba (svarbu architektūrai)

Patikrinimo metu (žr. lentelę) **dauguma** `.lt` savivaldybių svetainių serveriuose veikia
Cloudflare su JS/„managed challenge“ apsauga, kuri grąžina HTTP 403 su „Just a moment...“
puslapiu net paprastam `robots.txt` užklausimui. Tai reiškia:

- Paprastas `httpx`/`curl` klientas šių svetainių nepasiekia.
- Playwright/Chromium *galėtų* techniškai praeiti dalį tokių iššūkių, tačiau tai laikytina
  bot-apsaugos apėjimu ir yra tiesiogiai draudžiama užduoties instrukcijose
  („Neapeik prisijungimo, CAPTCHA ar techninių blokavimų“). **Programa to nedaro.**
- Todėl architektūra numato trečią būseną (šalia „veikia“/„klaida“) — **„blocked_in_current_runtime“**
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
| Akmenės r. | akmene.lt | 403 (CF) | blocked_in_current_runtime |
| Alytaus m. | ams.lt | 403 (CF) | blocked_in_current_runtime |
| Alytaus r. | arsa.lt | 403 (CF) | blocked_in_current_runtime |
| Anykščių r. | anyksciai.lt | 403 (CF) | blocked_in_current_runtime |
| Birštono | birstonas.lt | 403 (CF) | blocked_in_current_runtime |
| Biržų r. | birzai.lt | 200 | **accessible** |
| Druskininkų | druskininkusavivaldybe.lt | 200 | **accessible** |
| Elektrėnų | elektrenai.lt | 403 (CF) | blocked_in_current_runtime |
| Ignalinos r. | ignalina.lt | 403 (CF) | blocked_in_current_runtime |
| Jonavos r. | jonava.lt | 403 (CF) | blocked_in_current_runtime |
| Joniškio r. | joniskis.lt | 403 (CF) | blocked_in_current_runtime |
| Jurbarko r. | jurbarkas.lt | 403 (CF) | blocked_in_current_runtime |
| Kaišiadorių r. | kaisiadorys.lt | 200 | **accessible** |
| Kalvarijos | kalvarija.lt | 403 (CF) | blocked_in_current_runtime |
| **Kauno m.** | **kaunas.lt** | **200** | **accessible — naudota vertikaliame pjūvyje (generic HTML)** |
| Kauno r. | krs.lt | 000 (ryšio klaida) | needs_verification |
| Kazlų Rūdos | kazluruda.lt | 200 | **accessible** |
| Kelmės r. | kelme.lt | 403 (CF) | blocked_in_current_runtime |
| Kėdainių r. | kedainiai.lt | 403 (CF) | blocked_in_current_runtime |
| Klaipėdos m. | klaipeda.lt | 200 | **accessible** |
| Klaipėdos r. | klaipedos-r.lt | 403 (CF) | blocked_in_current_runtime |
| Kretingos r. | kretinga.lt | 403 (CF) | blocked_in_current_runtime |
| Kupiškio r. | kupiskis.lt | 403 (CF) | blocked_in_current_runtime |
| Lazdijų r. | lazdijai.lt | 403 (CF) | blocked_in_current_runtime |
| Marijampolės | marijampole.lt | 403 (CF) | blocked_in_current_runtime |
| Mažeikių r. | mazeikiai.lt | 403 (CF) | blocked_in_current_runtime |
| Molėtų r. | moletai.lt | 403 (CF) | blocked_in_current_runtime |
| Neringos | neringa.lt | 200 | **accessible** |
| Pagėgių | pagegiai.lt | 403 (CF) | blocked_in_current_runtime |
| Pakruojo r. | pakruojis.lt | 403 (CF) | blocked_in_current_runtime |
| Palangos m. | palanga.lt | 403 (CF) | blocked_in_current_runtime |
| Panevėžio m. | panevezys.lt | 403 (CF) | blocked_in_current_runtime |
| Panevėžio r. | panrs.lt | 403 (CF) | blocked_in_current_runtime |
| Pasvalio r. | pasvalys.lt | 200 | **accessible** |
| Plungės r. | plunge.lt | 200 | **accessible** |
| Prienų r. | prienai.lt | 403 (CF) | blocked_in_current_runtime |
| Radviliškio r. | radviliskis.lt | 403 (CF) | blocked_in_current_runtime |
| Raseinių r. | raseiniai.lt | 403 (CF) | blocked_in_current_runtime |
| Rietavo | rietavas.lt | 403 (CF) | blocked_in_current_runtime |
| Rokiškio r. | rokiskis.lt | 403 (CF) | blocked_in_current_runtime |
| **Skuodo r.** | **skuodas.lt** | **200** | **accessible — naudota vertikaliame pjūvyje (WordPress REST API adapteris, `wp-json/wp/v2/posts`)** |
| Šakių r. | sakiai.lt | 403 (CF) | blocked_in_current_runtime |
| Šalčininkų r. | salcininkai.lt | 403 (CF) | blocked_in_current_runtime |
| Šiaulių m. | siauliai.lt | 200 | **accessible** |
| Šiaulių r. | siauliuraj.lt | 403 (CF) | blocked_in_current_runtime |
| Šilalės r. | silale.lt | 403 | blocked_in_current_runtime |
| Šilutės r. | silute.lt | 403 (CF) | blocked_in_current_runtime |
| Širvintų r. | sirvintos.lt | 403 (CF) | blocked_in_current_runtime |
| Švenčionių r. | svencionys.lt | 403 (CF) | blocked_in_current_runtime |
| Tauragės r. | taurage.lt | 403 (CF) | blocked_in_current_runtime |
| Telšių r. | telsiai.lt | 403 (CF) | blocked_in_current_runtime |
| Trakų r. | trakai.lt | 403 (CF) | blocked_in_current_runtime |
| Ukmergės r. | ukmerge.lt | 403 (CF) | blocked_in_current_runtime |
| Utenos r. | utena.lt | 403 (CF) | blocked_in_current_runtime |
| Varėnos r. | varena.lt | 403 (CF) | blocked_in_current_runtime |
| Vilkaviškio r. | vilkaviskis.lt | 403 (CF) | blocked_in_current_runtime |
| Vilniaus m. | vilnius.lt | 403 (CF) | blocked_in_current_runtime |
| Vilniaus r. | vilniaus-r.lt | 000 (ryšio klaida) | needs_verification |
| Visagino m. | visaginas.lt | 200 | **accessible** |
| Zarasų r. | zarasai.lt | 403 (CF) | blocked_in_current_runtime |

**Santrauka: sėkmingai patikrinta prieinama tiesiogiai 12/60 (20%), blokuota bot-apsaugos
46/60 (77%), reikia papildomo rankinio patikrinimo 2/60 (3%, tinklo klaida iš šios aplinkos —
`krs.lt` ir `vilniaus-r.lt`, tikėtina DNS/TLS ypatumas per proxy, ne būtinai realus
blokavimas).** Šis skaičius rodomas programos „Šaltiniai“ vaizde tiksliai tokiu pavidalu
(„sėkmingai patikrinta 12/60“), o ne klaidinančiu „visi veikia“.

## Vertikalaus pjūvio šaltiniai (faktiškai įdiegti šiame etape)

| Atvejis iš instrukcijų | Pasirinktas realus šaltinis | Adapteris | Būsena |
|---|---|---|---|
| JRA finansavimo konkursai + 1 dokumentas | jra.lrv.lt/lt/finansavimo-konkursai/ | — | **blocked_in_current_runtime**, registruota, rankinės peržiūros nuoroda. Dokumento pavyzdys pakeistas sintetiniu PDF fixture testams (žr. žemiau). |
| Vilniaus konkursų sistema | konkursai.vilnius.lt/konkursai | — | **blocked_in_current_runtime**, registruota, rankinės peržiūros nuoroda. |
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
