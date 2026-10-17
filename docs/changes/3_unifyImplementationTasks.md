# Sjednocení zadání, dokumentace a pravidel agentů

## Kontext PR

Datum: 2026-10-15. Baseline: PR #5 / `6b5aea13c150a75858973dd2e08debf802ff29ed`,
navazující na PR #4. Tento PR dokumentuje současný stav a požadované dokončení;
neimplementuje compiler lifecycle, Spring, ORM ani ostatní etapy nového zadání.
Číslo 3 navazuje na existující change notes 1 a 2; není to číslo GitHub PR.
Související zadání: T001, T002, T003; registrace/normalizace je část T003-S01,
ne dokončení celé acceptance matice T003-AC01.

## Problém a změny

Dokumentace míchala historický stav s novými schopnostmi a souběžně používala
A–G, M0–M6 a P0–P10. Některé stránky popíraly již implementované workspace a
availability důkazy. Agentům chybělo společné pravidlo pro pojmenování zadání.

- Původní úplné specifikace jsou v `docs/tasks/1_featureAnalysis.md` (T001) a
  `2_buildAwareInspection.md` (T002). Staré cesty zůstávají rozcestníky s původními
  nadpisy pro historické odkazy; původní požadavky se nezahazují.
- `3_finishProductionAnalysis.md` (T003) obsahuje 13 etap, závislosti, konkrétní
  moduly/kontrakty, průřezové požadavky, acceptance a rozdělené DoD pro statické
  jádro, Confluence boundary a volitelný runtime import.
- `docs/tasks/README.md` je jediný registr identity a převod historických milníků.
- `AGENTS.md` zavádí povinné `<N>_<lowerCamelCase>.md` pro zadání i change notes,
  dvě nezávislé řady max + 1, kontrolu kolizí a stabilní Task/Step/Acceptance ID.
- README, architecture, project scope, feature/production/compiler docs a progress
  odpovídají podporované baseline a přiznávají ztrátu compiler indexu při scan/hook
  i chybějící přenos compiler kontextů do feature pipeline.
- Instalační Python templates sdílejí `agent_rules.PROJECT_RULES`; zapsané Copilot
  a analytické/data-auditor Junie instrukce nesou stejná pravidla. Repository Junie
  implementation command odkazuje na AGENTS. Stávající Agent Skill už AGENTS čte.

## Kompatibilita a rozsah

Formát `docs/changes/1_addProductionScope.md` a `2_addCompilerWorkers.md` se nemění.
Historické změnové dokumenty zůstávají nedotčené. Čísla zadání nejsou runtime
analysis_id ani packet/revision a tyto kontrakty se nemění. Přesun specifikací
zachovává jejich požadavky; staré krátké acceptance identifikátory jsou lokální
aliasy pod T001/T002. Nové dokumenty používají kanonické prefixy.

`kgmaker init` nadále nezmění uživatelsky upravený existující soubor bez explicitního
`--force`; pravidla jsou dodána v nově instalovaných instrukcích. Změna Pythonu
upravuje obsah host instrukcí, nikoli resolution či availability algoritmus.
Generované grafy se obnovují standardním scan/check, nikoli ruční editací.

## Ověření

- `PYTHONPATH=kgmaker/src python -m pytest -q kgmaker/tests`: **133 passed, 7 skipped**. Přeskočeny skutečné compiler worker testy bez toolchainů; žádný lokální worker/build PASS se netvrdí.
- Jednorázová kontrola dokumentace: všech 74 původních acceptance řádků T001 a 22 řádků T002 zachováno; lokální odkazy v aktuálních docs a přesunutých zadáních existují; názvy a čísla jsou validní a unikátní.
- Osm instalačních Python templates odpovídá checked-in instrukcím. Fresh `cli.init(temp_root)` dodalo pravidla; opakované init zachovalo uživatelsky upravený soubor.
- `PYTHONPATH=src python -m kgmaker scan` a `PYTHONPATH=src python -m kgmaker check`: PASS; generované views se obnovily standardním příkazem.
- `PYTHONPATH=src python -m kgmaker semantic update --base HEAD --note docs/changes/3_unifyImplementationTasks.md`: připraven lokální packet proti rekonstruovanému snapshotu upstream baseline. Žádný semantic patch nebyl aplikován; nevznikla nová nedoložená tvrzení.
- Read-only architektonické review odhalilo rozpor status→scan s compiler lifecycle limitem. Agent/architect/Junie nyní nejprve ověřují uložený compiler kontext; source-only status není compiler freshness.
- `git diff --check` se provádí i nad staged novými soubory; původní trailing whitespace v přesunutých specifikacích bylo odstraněno.

## Příklad

Nová samostatná feature po T003: `docs/tasks/4_addSpringResolution.md`, Task ID
`T004`, krok `T004-S01`, acceptance `T004-AC01`. Pokud jde pouze o realizaci S05
existujícího T003, nevytvářej duplicitní zadání: odkazuj `T003-S05` a přidej další
volný change note (po kontrole registru/větví/PR), např. `4_addSpringResolution.md`
v `docs/changes/`. Číselné řady se shodovat nemusí.

## Omezení

Tento PR nesplňuje budoucí acceptance pouze sepsáním plánu. Compiler toolchainy
nejsou v lokálním ověření nainstalované; jejich upstream CI výsledek patří přesně
baseline commitu, nikoli automaticky novému PR. Kompletní řádková acceptance matice,
provider integrace a další implementace zůstávají prací T003. Živá Confluence
integrace není deklarována.
