# Zachování compiler důkazů při offline refreshi

Datum: 2026-10-15. Baseline: `d9a89fe` a existující rozpracovaný tree.
Vazby: T003-S02, dílčí T003-AC02, T003-R05/R07/R09. Nejde o dokončení S02.

## Problém a změny

Scan/hook přepisovaly compiler index. Nový `graph_provider.py` sdílí validaci
snapshotu s compiler CLI a zachovává compiler symboly, hrany, call sites, CFG a
evidence v single-root scan/hook/feature projekci. Validuje zdroje včetně nových
souborů, classifier konfiguraci, project inputs, classpath a worker distribuci.
Dotčený stale kontext ztratí compiler fakta a zůstane jako explicitní marker s
důvodem a next command; ostatní module/profile kontexty zůstávají použitelné.
Proces compileru ani buildu se při refreshi nespouští. Workspace schema v3 navíc
přenáší compiler kolekce s repo-qualified symbol/context/evidence/CFG identitami.

## Kompatibilita a příklad

Store zůstává stejný, legacy source-only grafy se obnovují původním způsobem.
Nové compiler důkazy nevznikají z heuristických hran ani semantic confidence.
Příklad: `inspect code --classpath ...`, následně `scan`, `hook-context` a
single-root `feature prepare` zachovají čerstvé compiler výsledky. Po změně
compiler vstupu výstup uvede konkrétní nový příkaz explicitní inspection.

## Ověření

- `python3 -m pytest -q`: **184 passed**, 15.93 s; lokální Python 3.12.
- `python3 -m pytest -q tests/test_compiler_workers.py tests/test_graph_provider.py tests/test_build_aware.py`:
  **17 passed**, 10.16 s; skutečný JVM worker a existující build fixture,
  zachované call sites/CFG přes scan a hook, procesní sentinel v offline cestě.
- `python3 -m pytest -q tests/test_graph_provider.py tests/test_workspace.py tests/test_inspection_contract.py`:
  **24 passed**, 1.63 s; selective stale a workspace compiler schema v3.
- `mvn -q -DskipTests package` ve `workers/jvm`: PASS.

## Neprovedené kontroly a zbývající práce

T003-AC02 v celém rozsahu není splněno: chybí jednotný explicitní context selection
pro query/impact/feature/report a celý skutečný end-to-end sled s profilem,
classpath a packet invalidací. Module/profile kontexty se akumulují podle selection
key; worker identity obsahuje context a neplatný modul B nemaže A. Řádkový
acceptance inventář T001/T002 je v `docs/acceptance-inventory.md`; viditelně uvádí
PARTIAL a NOT_IMPLEMENTED mezery ostatních etap T003.

Lokální číslo změny 5 je volné v tree a známých refs. Kontrola otevřených PR
nebyla provedena: `gh` není nainstalováno. Číslo před publikací znovu ověřit;
PR zatím nebyl publikován a nic nebylo mergováno.

## Offline XLSX, Thymeleaf a Confluence boundary

Navazující změny pokrývají části T003-S09/AC09 a T003-S12/AC12:

- `workbooks.py` bezpečně čte bounded `.xlsx` ZIP/XML, vytváří sheets, cells,
  named ranges a statické formula dependencies. Cached value je oddělená a má
  freshness `UNKNOWN`; vzorce se nevyhodnocují. `.xls`, shared formula, INDIRECT,
  external link, traversal a překročení limitu mají explicitní diagnostiku.
- Feature/data-check přijímá hashově svázaný `workbook_cell` locator a při
  validaci znovu ověří sheet, cell, formula a cached value. Falešná hodnota je
  odmítnuta.
- `templates.py` v podporovaném Thymeleaf subsetu propojuje literal MVC model key,
  vrácenou šablonu a `${variable.path}`. Explicitní PDF renderer zůstává external
  boundary.
- `confluence_sync.py` definuje adapter interface a `FAKE_TEST_ONLY`: explicitní
  pull, managed-section diff, payload/base-version approval, optimistic concurrency,
  TO_BE re-import a audit bez obsahu. Živý konektor není tvrzen ani implementován.
- `semantic.apply_semantic_layer` již nemutuje vstupní graph. Tím je opravena
  duplicita, která blokovala `memory capture` po sloučení semantic konceptů.

Nové kontroly: `tests/test_workbooks.py`, `tests/test_templates.py` a
`tests/test_confluence_sync.py`. T003-S09 zůstává PARTIAL kvůli širším template
variantám, schválené metodice a plnému scénáři. Offline S12/AC12 je ověřeno ve
fake scope; live připojení je samostatně NOT_RUN bez doloženého host/API kontraktu.

Předchozí `semantic apply` + `semantic validate` a `scan` + `check` výsledky platily
pro starší mezikrok; po tomto rozšíření budou obnoveny a uvedeny s finálními počty.
`semantic.apply_semantic_layer` už nemutuje structural graph a regresní
`tests/test_memory.py` pokrývá původní duplicate-node selhání. Finální memory capture
a diff check jsou uvedeny po skutečném provedení, nikoli předem jako PASS.
