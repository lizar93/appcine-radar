# Radar cinematogràfic mundial — instruccions de l'edició diària

Aquest repositori publica cada dia l'edició del **Radar** que llegeix l'app AppCine (iPhone):

- `ca/latest.json` — l'edició en català.
- `en/latest.json` — la mateixa edició en anglès.
- `arxiu/ca/AAAA-MM-DD.json` i `arxiu/en/AAAA-MM-DD.json` — còpia de cada edició.
- `arxiu/index.json` — la llista de dates amb edició (`{"dates": ["AAAA-MM-DD", …]}`, la més nova primer).

L'app les baixa de `https://raw.githubusercontent.com/lizar93/appcine-radar/main/{ca|en}/latest.json` quan s'obre. Les escriu una tasca programada de Claude cada matí seguint aquest document. Aquest document és l'adaptació del prompt original del Radar (versió del 25/10/2026) a l'app: el contingut és el mateix, però el resultat és el JSON que l'app llegeix, no un text per a un xat.

## 1. Pas a pas de cada execució

1. **Data de l'edició:** el dia d'avui a Europe/Madrid (`AAAA-MM-DD`). Si avui ja hi ha `arxiu/ca/<avui>.json`, s'actualitza la mateixa edició (mateix dia).
2. **Què s'ha publicat:** llegeix les edicions dels darrers 7 dies a `arxiu/ca/` per no repetir notícies. Una notícia ja publicada només torna si hi ha una novetat real (nova data, nou repartiment, nova confirmació…) i s'explica què ha canviat.
3. **Recerca web actualitzada** (apartats 2–6): cerca àmplia, multilingüe i contrastada. Llegeix les pàgines, no només els titulars de la cerca. Res de memòria ni de coneixements generals: cada fet ha de tenir una font d'aquesta edició.
4. **Escriu l'edició en català** a `ca/latest.json` i **la mateixa en anglès** a `en/latest.json` (apartat 8): mateixos reportatges, en el mateix ordre, amb els mateixos `id`, fonts, dates, estat i evidència. Només canvia el text (`headline`, `deck`, `paragraphs`, `name` de les fonts si cal). L'anglès ha de ser natural, no una traducció literal.
5. **Còpia a l'arxiu:** `arxiu/ca/<data>.json` i `arxiu/en/<data>.json`, idèntiques a `latest.json`, i la data al principi de la llista `dates` d'`arxiu/index.json` (de la més nova a la més antiga, sense repetir). L'app hi llegeix les edicions anteriors.
6. **Comprova:** `python3 eines/validar.py` ha de dir «TOT CORRECTE». Si dona errors, corregeix-los i torna-hi. No pugis mai una edició que no passi la comprovació.
7. **Puja-ho:** un commit «Edició AAAA-MM-DD» a `main` i `git push`. Si el push falla perquè hi ha canvis a GitHub, `git pull --rebase` i torna a pujar.
8. **Si un dia no surt bé** (poques fonts, errors que no se solucionen): publica menys reportatges abans que inventar res. Si no es pot fer una edició vàlida, no toquis `latest.json` (l'app continua mostrant l'anterior).

No hi ha cap secret ni clau en aquest repositori ni n'hi ha de posar mai cap. És públic.

## 2. Perfil i criteri curatorial

Personalitza la selecció per a una persona interessada especialment en:

- Cinema històric i d'època.
- Terror en totes les variants: gòtic, sobrenatural, psicològic, folklòric, corporal, slasher i experimental.
- Comèdies intel·ligents i de relacions humanes, amb afinitat pel cinema de Woody Allen.
- Drames, aventures, thrillers de qualitat i cinema d'autor.
- Cinematografies internacionals minoritàries i descobertes de festivals.
- Blockbusters de Hollywood quan tinguin interès artístic, narratiu o industrial.
- Teatre britànic, Shakespeare, dramatúrgia clàssica i contemporània, història teatral i òpera.

**No incloguis cinema indi** (hindi, tàmil, telugu, malaiàlam, etc.): decisió del lector. La resta de cinematografies asiàtiques sí (Japó, Corea, Àsia oriental i sud-oriental).

Mirada geogràfica global i equilibrada: Catalunya i Espanya, resta d'Europa, Àsia oriental i sud-oriental, Orient Mitjà, Àfrica, Llatinoamèrica, Oceania i Amèrica del Nord. No amaguis produccions petites darrere dels grans llançaments, però tampoc forcis una regió si no hi ha novetats verificables.

## 3. Cobertura

Inclou, quan hi hagi informació contrastada:

- **Estrenes a cinemes.** Prioritza Catalunya i Espanya i separa sempre les dates internacionals. No dedueixis mai una estrena espanyola d'una data dels EUA, Corea o un festival. Distingeix estrena festivalera, comercial, preestrena, reestrena i exhibició limitada.
- **Plataformes i sèries:** Filmin, MUBI, Netflix, Prime Video, HBO Max, Disney+, Apple TV+, Movistar Plus+, SkyShowtime, RTVE Play, 3Cat i altres. Estrenes, temporades noves, adquisicions, obres recuperades i caducitats. Verifica data i disponibilitat a Espanya; si només consta un altre país, digues quin.
- **DVD, Blu-ray i 4K UHD:** edicions noves, restauracions, reedicions i edicions de col·leccionista. Separa el mercat espanyol de les importacions; subtítols, llengües, regió, HDR i preu només amb font fiable.
- **Projectes i indústria:** adaptacions, guions, càstings, inici i final de rodatge, primeres imatges, tràilers, vendes de drets, canvis de data. Diferencia confirmat, anunciat sense data, negociació i rumor. No atribueixis repartiment, direcció ni estrenes a partir de rumors.
- **Festivals:** Sitges, Sant Sebastià, Cannes, Berlinale, Venècia, Locarno, Toronto, Sundance, Rotterdam, BFI London, Seminci, D'A, Gijón, Cinemed, Morelia, festivals asiàtics, llatinoamericans, africans i d'Oceania: seleccions, estrenes, premis, adquisicions i continguts en línia accessibles des d'Espanya. Quan un festival publiqui la programació oficial, usa `festivalProgramme` (apartat 8) amb `selectedHighlights` i l'enllaç al programa complet; no presentis mai una selecció parcial com si fos completa.

## 4. Teatre i òpera filmats (obligatori cada dia)

Cada edició porta **almenys un reportatge `stage`**. Cerca enregistraments audiovisuals **complets** d'obres de teatre i d'òpera, nous o històrics que arribin a catàlegs o es reeditin:

- Teatre: National Theatre at Home, NT Live, RSC, Shakespeare's Globe, BroadwayHD, Digital Theatre, Marquee TV.
- Òpera: Met Opera (Live in HD i on Demand), Royal Ballet and Opera, Liceu (LiceuOPERA+), Teatro Real, La Scala, Opéra de Paris, Wiener Staatsoper, Bayerische Staatsoper, Staatsoper Unter den Linden, Glyndebourne.
- Plataformes i arxius: OperaVision, ARTE Concert, medici.tv, Mezzo, Filmin, RTVE Play, 3Cat, canals oficials.
- Formats físics: DVD, Blu-ray, 4K.

Prioritza Shakespeare, teatre europeu i britànic, grans tragèdies, comèdies de relacions, drama històric i repertori operístic. Per a cada captació completa recomanada, omple `filmedPerformance` només amb dades contrastades: obra, autor o compositor i llibretista, teatre, producció, direcció, intèrprets, **any de l'enregistrament** (mai l'any de l'obra o de la composició en lloc seu), data d'estrena audiovisual, llengua, subtítols, durada i **accés des d'Espanya** (gratuït, subscripció, lloguer, compra, directe o físic, amb dates i font). No confonguis una funció en directe, un tràiler o un fragment amb una captació completa. Si no hi ha cap novetat verificable, el reportatge `stage` ho diu breument i enllaça el catàleg oficial consultat.

## 5. Fitxa d'una obra destacada

Per a les pel·lícules i sèries destacades, als paràgrafs, en la mesura que consti: títol original i títol en català o castellà, any verificat, país, llengua, format, direcció o creació, repartiment confirmat, gènere, sinopsi breu **sense espòilers**, estil i comparacions pertinents (sense inventar influències), per què encaixa o no amb el perfil, **afinitat editorial de 0 a 5 amb confiança alta, mitjana o baixa** (deixant clar que no és la nota de la crítica ni del públic), estat industrial i on i quan es podrà veure. No facis veure que has vist una obra si només n'has llegit sinopsis o crítiques; si cites la crítica, atribueix-la.

## 6. Fonts i verificació

- Prioritza webs oficials de festivals, teatres, distribuïdores, productores, catàlegs i plataformes; contrasta amb Variety, Deadline, Screen Daily, The Hollywood Reporter, Cineuropa, Gramophone, OperaWire, Bachtrack i premsa especialitzada de cada país.
- Separa la **data de publicació** de la notícia (`publishedAt`) de la **data de l'esdeveniment** (`eventDate`).
- Verifica nom, títol, any, autoria, repartiment, premis, sessió, territori, suport i data. Si les fonts es contradiuen, explica-ho; no en triïs una a l'atzar.
- No donis per fet que una pel·lícula anunciada, premiada o seleccionada ja es pot veure a Espanya.
- No atribueixis a una font el que la font no diu. No reciclis fets d'edicions anteriors sense tornar-los a comprovar.
- Menys notícies abans que notícies inventades: entre 6 i 12 reportatges, o menys si no n'hi ha prou.
- **Text propi:** redacta-ho tot amb paraules pròpies. No copiïs paràgrafs de cap article; com a molt una cita curta (menys de 15 paraules), entre cometes i atribuïda.
- Sense espòilers. Sense notes promocionals ni text inflat.

## 7. Estructura de l'edició dins l'app

L'estructura del prompt original (A–K) es reparteix en un màxim de **12 reportatges**, en aquest ordre i amb aquestes seccions (`section`):

| Prompt original | `section` | Notes |
|---|---|---|
| A. Titulars del dia i B. Notícies amb anàlisi | `news` | Les notícies principals, de més a menys important. |
| C. Estrenes a cinemes | `cinema` | Territori explícit; Catalunya i Espanya primer. |
| D. Plataformes i sèries | `services` | `subject: "series"` per a les sèries (l'app les mostra al radar de sèries). |
| E. Edicions físiques | `physical` | Edició espanyola o importació. |
| F. Teatre i òpera filmats | `stage` | **Obligatori.** `filmedPerformance` per a cada captació completa. |
| G. Projectes, càstings, vendes, canvis de data | `projects` | Estat: confirmed / announced / negotiation / rumour. |
| H. Festivals | `festivals` | `festivalProgramme` quan hi hagi programa oficial. |
| I. Calendari | `calendar` | Pròximes estrenes i esdeveniments amb data. |
| J. Recomanacions de l'editor i K. Balanç del dia | `recommendation` | **Obligatori.** 3–5 recomanacions amb afinitat i justificació, i un paràgraf final de balanç del dia. |

- **Diumenge:** el reportatge `calendar` fa la previsió dels set dies següents i el `recommendation` inclou un balanç de la setmana (sense repetir les notícies ja explicades).
- **Dia 1 de cada mes:** el `calendar` és el calendari de tot el mes.
- **Llista de títols recomanats** (el TXT del prompt original): va dins del JSON, al camp `recommendedTitles` (apartat 8). L'app la mostra al final de l'edició i la deixa copiar o desar com a `pellicules_recomanades_AAAA-MM-DD.txt`.

### Llista de títols recomanats (`recommendedTitles`, obligatòria)

Totes les pel·lícules **recomanades explícitament** a l'edició (de qualsevol secció: notícies, plataformes, festivals, edicions físiques, calendari i recomanacions de l'editor) que tinguin l'**any d'estrena verificat** amb fonts fiables, i les **captacions completes** de teatre i òpera recomanades amb l'**any de l'enregistrament o de l'estrena audiovisual** contrastat (mai l'any de l'obra o de la composició).

- `title`: el **títol original**, exacte, sense l'any ni cap afegit (ni «òpera», ni director, ni plataforma, ni nota).
- `year`: l'any verificat (nombre).
- `kind`: `film` o `stage`.
- `knownAs` (opcional): el títol amb què es coneix aquí o en anglès quan l'original és un altre o va en un altre alfabet (p. ej. `"title": "가능한 사랑", "knownAs": "Possible Love"`). No surt al TXT; l'app el mostra a sota i l'usa per trobar la pel·lícula al servidor.
- Fora: sèries, tràilers, fragments, obres només esmentades com a comparació, títols no recomanats i qualsevol obra sense any verificat (no l'estimis ni posis l'any de producció si no és el d'estrena).
- Sense repetits. La llista és **idèntica** en ca i en (són títols originals).

## 8. Format del JSON (el que l'app accepta)

Un objecte JSON UTF-8 de **100 KB com a màxim** per idioma (millor per sota de 70 KB):

```json
{
  "schemaVersion": 1,
  "date": "2026-10-27",
  "territory": "ES",
  "generatedAt": "2026-10-27T05:58:00Z",
  "reports": [
    {
      "id": "2026-10-27-exemple",
      "section": "news",
      "subject": "film",
      "headline": "Titular (màxim 200 caràcters)",
      "deck": "Entradeta d'una o dues frases (màxim 500 caràcters).",
      "paragraphs": ["D'1 a 8 paràgrafs de text propi, de 1.500 caràcters com a màxim cadascun."],
      "publishedAt": "2026-10-26T14:30:00Z",
      "eventDate": "2026-11-14",
      "territory": "ES",
      "status": "confirmed",
      "evidence": "primarySource",
      "sources": [
        { "name": "Nom de la font", "url": "https://…", "kind": "official" }
      ],
      "titles": [
        { "title": "Títol original", "year": 2026, "kind": "film", "knownAs": "Títol a Espanya (si és diferent)" }
      ]
    }
  ],
  "recommendedTitles": [
    { "title": "Títol original", "year": 2025, "kind": "film", "knownAs": "Títol a Espanya o en anglès (si és diferent)" },
    { "title": "Títol original de l'obra", "year": 2024, "kind": "stage" }
  ]
}
```

- `id`: únic, sense espais; comença per la data de l'edició (`2026-10-27-…`) i és el mateix en ca i en.
- `section`: `news`, `cinema`, `services`, `physical`, `stage`, `projects`, `festivals`, `calendar`, `recommendation`.
- `subject`: `film` o `series` (una sèrie no pot anar a `cinema` ni a `stage`). Si s'omet, compta com a `film`.
- `status`: `confirmed`, `announced`, `negotiation`, `rumour`, `unverified`.
- `evidence`: `primarySource` (font oficial), `corroborated` (diverses fonts), `singleSource` (una sola font no oficial), `unverified`.
- `sources`: almenys una; `kind` és `official`, `catalogue`, `tradePress` o `other`. Enllaços complets `https://`, sense espais ni caràcters no ASCII (codifica'ls amb `%`), i cap enllaç repetit dins del mateix reportatge.
- Dates del dia: `AAAA-MM-DD`. Dates amb hora: ISO 8601 amb zona (`2026-10-27T05:58:00Z` o `+01:00`).
- `territory` (de l'edició i opcional a cada reportatge): dues lletres majúscules (`ES`, `US`, `GB`, `FR`…).
- `eventDate` i el `territory` del reportatge poden ser `null`.
- `titles` (opcional, però posa-ho sempre que el reportatge parli de pel·lícules o sèries concretes): les pel·lícules i sèries del reportatge que el lector podria demanar al seu servidor (estrenades o anunciades, si ja tenen fitxa a TMDB), amb el mateix format que `recommendedTitles` (`title` original, `year` d'estrena o previst si consta, `kind` `film` o `series`, `knownAs` si cal). L'app hi posa un botó «Request» al costat de cada títol i un «Request all». Màxim 12 per reportatge; sense obres de teatre o òpera (aquestes no es demanen). Idèntic en ca i en.

**Captació completa de teatre o òpera** (només a `stage`), dins del reportatge:

```json
"filmedPerformance": {
  "kind": "opera",
  "workTitle": "Títol de l'obra",
  "creators": ["Compositor", "Llibretista"],
  "workYear": 1853,
  "recordingYear": 2025,
  "completeRecordingSource": "https://… (ha de ser també a sources, amb kind official o catalogue)",
  "venue": "Teatre", "director": "Direcció escènica", "musicalDirector": "Direcció musical",
  "principalCast": ["Intèrpret"], "recordingDate": "2025-03-14", "audiovisualReleaseDate": "2026-10-20",
  "language": "Italià", "subtitles": ["Català", "Castellà"], "durationMinutes": 165,
  "access": [{ "provider": "Plataforma", "territory": "ES", "mode": "subscription",
              "sourceURL": "https://…", "checkedAt": "2026-10-27T05:40:00Z",
              "startsOn": "2026-10-20", "expiresOn": "2027-04-20" }]
}
```

`mode`: `free`, `subscription`, `rental`, `purchase`, `liveBroadcast`, `physical`. Sense `access` vol dir que l'accés des d'Espanya és desconegut.

**Programa d'un festival** (només a `festivals`):

```json
"festivalProgramme": {
  "festivalName": "Nom del festival", "editionYear": 2026, "scope": "selectedHighlights",
  "officialProgrammeURL": "https://… (ha de ser també a sources, amb kind official)",
  "entries": [{ "id": "f1", "section": "Secció oficial", "title": "Títol", "country": "FR",
                "director": "Director", "synopsis": "Sinopsi breu sense espòilers (màxim 600)",
                "sessionAt": "2026-11-02T19:00:00+01:00", "venue": "Sala", "recommended": true,
                "sourceURL": "https://…" }]
}
```

D'1 a 80 entrades; `scope` és `selectedHighlights` (selecció) o `reportedComplete` (només si el programa és realment complet).

## 9. Objectiu

Una revista de cinema diària, experta, crítica i internacional, útil per a un espectador de Catalunya; amb un radar real d'enregistraments de teatre i òpera; amb la informació confirmada separada de la provisional; i llegible de cap a peus dins de l'app, en català o en anglès.
