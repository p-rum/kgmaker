# Registr implementačních zadání

Tento registr je autoritou pro identitu zadání. Implementační stav patří do
[stavové matice](../production-analysis-progress.md), technické požadavky do
níže uvedených zadání. Pravidla jsou závazná v [AGENTS.md](../../AGENTS.md).

| ID | Soubor | Úloha | Stav dokumentu |
|---|---|---|---|
| T001 | [1_featureAnalysis.md](1_featureAnalysis.md) | Feature/data analýza, artefakty, incremental, Flyway, multirepo | Normativní; částečně implementováno |
| T002 | [2_buildAwareInspection.md](2_buildAwareInspection.md) | JVM build, call graph, Spring a Hibernate | Normativní; částečně implementováno |
| T003 | [3_finishProductionAnalysis.md](3_finishProductionAnalysis.md) | Integrovaný plán dokončení T001/T002 a produkční analýzy | Normativní plán; není tvrzením dokončení |

## Jednotný formát

- Soubor zadání: `docs/tasks/<N>_<shortName>.md`, N je kladné celé číslo bez nul na začátku; shortName je ASCII lowerCamelCase.
- Task ID: `T` + N s minimálně třemi číslicemi (`T001`, `T012`, `T1000`). Číslo souboru a ID se musí shodovat.
- Etapa: `<TaskID>-S<NN>`; nový požadavek: `<TaskID>-R<NN>`; nové akceptační kritérium: `<TaskID>-AC<NN>`. Číselná část má minimálně dvě číslice.
- Čísla jsou identity, nikoli pořadí vykonávání. Závislosti se píší explicitně. Historické identity se nemění, nemažou a znovu nepřidělují.
- Při vzniku nového zadání ověř registr, soubory cílové větve a otevřené PR; použij max + 1. Před publikací ověř kolize znovu. Při kolizi přiděl nové ID pouze nepublikovanému zadání a uprav jeho odkazy.
- Nová verze stejného zadání zachová soubor/ID a zvýší pole Revision; samostatné rozšíření dostane nové ID a `Depends on`/`Supersedes` odkazy. Žádné implicitní rušení scope.
- `docs/changes/<N>_<shortPrName>.md` používá stejný styl názvu, ale **samostatnou** číselnou řadu. Číslo změny není Task ID ani GitHub PR number.
- Uživatelská feature analýza (`analysis_id`, `requirement_hash`, packet/revision) není implementační zadání a nepřečísluje se tímto registrem.

## Převod starších milníků

| Historické označení | Kanonická etapa | Rozsah |
|---|---|---|
| A | T001-S01 | Analytické jádro |
| B | T001-S02 | Datové toky a matching |
| C | T001-S03 | Artefakty a dokumentace |
| D | T001-S04 | Inkrementální analýza a host agent |
| E | T001-S05 | Confluence synchronizační boundary |
| F | T001-S06 | Flyway |
| G | T001-S07 | Multirepo |
| M0 | T002-S01 | Compiler pilot |
| M1 | T002-S02 | Maven/build kontext |
| M2 | T002-S03 | Přesná volání a dispatch |
| M3 | T002-S04 | Spring |
| M4 | T002-S05 | ORM/query/Flyway |
| M5 | T002-S06 | Integrace workflow |
| M6 | T002-S07 | Volitelný runtime import |

Historické testy zůstávají dohledatelné; v nových dokumentech a PR se píší např.
`T001-FA-14`, `T002-CG-01`, `T002-MV-02`, `T002-SP-01`, `T002-HB-01`.
Původní krátká ID uvnitř přesunutých specifikací jsou lokální aliasy v namespace
svého dokumentu. Neměň názvy existujících Python testů jen kvůli číslování.

## Převod P0–P10 z předchozích progress/change dokumentů

Úplný samostatný normativní P dokument v kontrolovaném tree nebyl přítomen.
Následující mapování zachovává témata a není prohlášením ekvivalence všech
historických acceptance ID. V novém plánu se nepoužívá druhá P číselná řada.

| Starý alias | Aktivní etapa T003 |
|---|---|
| P0 | S01, S04, S11 — matice, compiler volba a měření |
| P1 | S02, S03 — scope a kontext |
| P2 | S03 — build |
| P3 | S04 — JVM |
| P4 | S05 — Spring |
| P5 | S06 — persistence |
| P6 | S07 — integrace/dataflow |
| P7 | S08 — TypeScript/UI |
| P8 | S07, S08, S11 — ranking a pohledy |
| P9 | S02, S10, S11 — lifecycle/cache/release |
| P10 | S13 — volitelný runtime |

Označení CL/JV/BL/DB/IN/TS/RK/FLOW/EV/BC v historických změnových dokumentech
jsou historické reference, nikoli automatické PASS nových kritérií T003.
