# T046 — Šablony, testovací návrhy a dohledatelnost změn

- Task ID: T046
- Revision: 4
- Datum: 2026-11-06
- Stav zadání: SPECIFICATION; skutečná implementace a kontroly jsou v change notes a stavové matici.
- Baseline: `33dc239a6d2eca2f42364a7b314aeb377e4b441a`.
- Zadavatel: uživatel této relace; osobní identita nebyla poskytnuta. Schvalovatel implementace: UNKNOWN.
- Závislosti: existující feature packet/revision/receipt, workflow, graph provider,
  scope/context/workspace, source inventory a safe-path/atomické JSON primitives.
  Celé T003 ani plánované pohledy T004 nejsou release dependency.

## Rozsah a kontrakty

| Požadavek | Cíl | Acceptance |
|---|---|---|
| T046-R01 | Projektové šablony požadavků, analýz, testů, názvů a tasků | T046-AC01 |
| T046-R02 | Návrhy cases/dat/kódu pro existující funkci bez diffu | T046-AC02, T046-AC03 |
| T046-R03 | Obousměrné reference požadavek–analýza–task–změna–test | T046-AC05 |
| T046-R04 | Lokální zadavatel/schvalovatel a volitelné brány | T046-AC06 |
| T046-R05 | Kompatibilita, evidence, žádné implicitní spouštění | T046-AC04, T046-AC07, T046-AC08 |

Šablony jsou verzované projektové JSON manifesty a UTF-8 obsah. Renderer nepoužívá
spustitelné výrazy. Použití zachovává ID/revizi/hash. Výběr explicitní šablony má
přednost před projektovým defaults a dodaným výchozím obsahem. Neplatná explicitní
volba je chyba, názvy musí být přenositelné a relativní. Existující soubory se nepřepisují.

Testgen připraví omezený packet existující funkcionality se zdroji, grafovými vazbami,
testy, kontextem, baseline a volitelnou aplikovanou analýzou. Hostitelský LLM agent
vytvoří kandidáta. Deterministický validátor ověří strukturu, citace, datová omezení,
reference a freshness. Očekávání z kódu označí CODE_CHARACTERIZATION. JSON/CSV data
jsou SYNTHETIC; návrh, validace a export jsou NOT_RUN. Spuštění používá existující
projektový runner a samostatný workflow test artefakt.

Reference obsahují druh/ID/revizi/repozitář/hash/snapshot a volitelný lokátor.
Journal uchovává explicitní vazby a append-only události s deklarovanou osobou,
časem, akcí, důvodem a předchozím event hashem. Nenahrazuje workflow task katalog.
Brány jsou standardně vypnuté. Zapnutá brána před implementací vyžaduje aktuální
požadavek a plán; před dokončením navíc aktuální review APPROVE a lokální schválení.
Obsah změněný od review nebo odvolané rozhodnutí bránu nesplní.

Non-goals: globální knihovna šablon, model API klient, nový runner, autentizace lidí,
digitální podpisy, automatický merge, nasazování dat do DB a deklarace univerzální
podpory testovacích frameworků. Omezení source/compiler evidence se nezvyšují.

## Implementační kroky

1. **T046-S01 — Kontrakty a kompatibilita.** Přidat `provenance` do workflow prostoru,
   obsahové reference, atomický journal a kontrolu souběhu. Workflow čte v1 a v2;
   nové bindings revizí nesmějí měnit publikovaná runtime ID. Unknown historie zůstává UNKNOWN.
2. **T046-S02 — Šablony.** Přidat `artifact_templates`, safe renderer, instalaci defaults,
   konvenci názvů a obsahově vázanou evidenci generování. Nezaměnit s aplikačním `templates`.
3. **T046-S03 — Testgen.** Přidat prepare/validate/apply/report/export nad existujícím
   providerem a workspace; přesný target, explicitní řešení víceznačnosti frameworku,
   nezávislé neměnné revize a přiznané mezery.
4. **T046-S04 — Syntetická data.** Ověřit podporovaný JSON-schema subset, negativní
   případy a foreign keys; JSON/CSV export musí předem odhalit kolize.
5. **T046-S05 — Schvalování.** Lokální člověk/agent, rozhodnutí nad přesnou referencí,
   volitelné policy, brány v knihovním save i advance rozhraní a source-bound review.
6. **T046-S06 — Dohledání a předání.** CLI, kontextové pakety, instalované i zdrojové
   instrukce agentů, dokumentace, acceptance, regresní a citlivý E2E test.

Závislosti: S01 → S02/S05; S01+S02 → S03 → S04; S03+S04+S05 → S06.
Každý krok má samostatný commit/větev a PR; závislé PR výslovně uvádějí base.

## Acceptance a ověření

| ID | Ověřitelný výsledek |
|---|---|
| T046-AC01 | Vlastní šablona, defaults precedence, hash provenance, ochrana upravených souborů, symlink/path/kolize fail-closed. |
| T046-AC02 | Bez diffu vznikne validovaný návrh cases/dat/kódu se skutečnými citacemi; exportovaný unittest projde a po změně chování selže. |
| T046-AC03 | Nejednoznačný target/framework vyžaduje výběr; chybějící framework blokuje kód a neblokuje cases/data. |
| T046-AC04 | Pozitivní data splní podporovaná omezení; negativní deklarují přesně zjištěné porušení; foreign key není pouhá podobnost jmen. |
| T046-AC05 | Stejná propojená množina je dohledatelná od požadavku i testu; report obsahuje osoby, revize, chybějící vazby a stale stav. |
| T046-AC06 | Vypnutá policy zachová v1 postup; zapnutá odmítne chybějící či stale rozhodnutí, změněný zdroj i pokus agenta o lidské schválení. |
| T046-AC07 | Zachování ID při v1→v2, integrita journalu, CAS a lock konflikt bez přepsání dat; chybný kandidát nemění soubory. |
| T046-AC08 | Offline cesty spouštějí pouze existující Git metadata reads; žádný model, build, test, migrace nebo aplikace. |

## Migrace, DoD a omezení

V1 se čte beze změny; při zaznamenání implementace/review vznikne v2 binding,
identity zůstávají stejné. Starší verze kgmakeru v2 nepřečte: je nutný upgrade
čteček, není podporován destruktivní downgrade. Šablony jsou verzovatelné,
workflow journal a testgen state jsou lokální a ignorované Gitem.

DoD: konkrétní výsledky acceptance a regresí, aktualizované příklady/README/stavová
matice, české change notes a reviewovatelné PR. Neprovedené pytest/toolchain/CI
kontroly musí být označeny NOT_RUN/SKIP/BLOCKED. Lokální hash není podpis,
frameworkový návrh není důkaz spuštění a charakterizační test není business oracle.

## Revize 2 — opravy nezávislého review

T046-AC01 navíc vyžaduje kanonickou cestu před validací i exportem, zákaz
segmentů .git/.github/.kgmaker bez ohledu na case a odmítnutí aliasů `./`.
T046-AC04 rozlišuje boolean a number rekurzivně, dovoluje ekvivalentní JSON
čísla 1/1.0 a rozlišuje chybějící FK cíl od explicitního null. T046-AC06
kontroluje fázi každého nového artefaktu i při přímém save; historie a bindings
jsou neměnné. T046-AC07 zahrnuje atomické create-or-load a CAS pro všechny
mutující trace příkazy včetně sync-analysis/sync-testgen/capture-change.
Regresní důkazy jsou v test_provenance, test_delivery a test_synthetic_data.

## Revize 3 — integrace aktuálního main

Integrační baseline je `250e7c16250a97b9f8df5256b9894c8119dc64d9`. Zachovává
nové main capabilities, worker/package data a instrukce T045 revize 2; GH CI
je doplňující evidence, nikoli povinná brána. T046 acceptance se nemění.
Přesné aktuální výsledky a omezení jsou v change notes 56–61 a PR review.

## Revize 4 — aktuální CLI integrace

Zachovává architecture registration/early dispatch a delivery CLI současně. Runtime ID, acceptance a historie se nemění. Nové baseline/head review a výsledky jsou v change61 a PR.
