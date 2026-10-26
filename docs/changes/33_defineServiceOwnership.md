# T007 — Explicitní vlastnictví služeb

## Problém

Workspace v1 dosud nesla legacy service/repository mapování, ze kterého nelze
bezpečně určit, které symboly patří do explicitní aplikační hranice. Název
repozitáře, modulu ani Spring `@Service` sám o sobě není důkazem deployable služby.

## Změny

- Workspace může volitelně obsahovat `service_ownership` v1 navázanou na již
  existující service IDs. Deklarace uvádí explicitní repo roots, repo-qualified module IDs
  a externí system IDs. Legacy `backend_repo` a ostatní pole zůstávají beze změny.
- `resolve_service_ownership` vrací `RESOLVED` pouze pro jedinou shodu;
  více explicitních shod zůstává `AMBIGUOUS`, žádná shoda je `UNASSIGNED`.
  Výsledek zachovává zadaný context ID. Repo-qualified compiler context musí patřit
  stejnému repo ID jako symbol; workspace paths `@<repo>/<relative-path>` se
  normalizují pouze tehdy, když prefix odpovídá symbolu.
- Nevalidní nebo duplicitní deklarace se odmítne při načtení manifestu. Resolver
  také odmítne přímou deklaraci s nepodporovanou verzí; nic nezapisuje a nepovyšuje
  kind evidence.

Související zadání: T007-S01–S05; acceptance T007-AC01–AC06.

## Kompatibilita

Stávající workspace v1 bez `service_ownership` zůstává čitelný a zachovává původní
service IDs. Nové pole je volitelné a má vlastní `schema_version: 1`; graph v1/v2/v3
ani T005 view schema se nemění. Migrace starých manifestů není nutná; legacy
service mapping se nepřeklápí na ownership automaticky.

## Ověření

- `PYTHONPATH=src /workspace/kgmaker-venv/bin/python3 -m pytest -q -rs` —
  **253 passed, 23 skipped** před integrací do main `aa9e64b` a před finálním
  repo-qualified module selector. SKIP: Maven/JDK exporter, dvě JDK21+
  s Mavenem, 14 Maven fixtures, Gradle 8.13, Kotlin Gradle cache, JVM worker a
  TypeScript worker; žádný SKIP se nepočítá jako PASS.
- Finální `PYTHONPATH=src /workspace/kgmaker-venv/bin/python3 -m pytest -q tests/test_t007_define_service_ownership.py tests/test_workspace.py tests/test_t005_add_view_model.py` po review opravách — **45 passed**.
- Review regressions cover foreign repo-qualified contexts, a supported
  repo-qualified context plus `@repo/path`, and direct schema version 99
  rejection; the T007-only suite passed **8 tests**.
- Reviewer full-suite result for pre-review commit `d00dd6a`: **264 passed,
  23 skipped**. The full suite was not repeated after these narrow review fixes;
  the focused workspace/T007/T005 suite above passed on the final code.
- `kgmaker check --root .` — **PASS**.
- `git diff --check` — **PASS**.
- `kgmaker semantic update --base origin/main`, scoped semantic patch,
  `semantic apply`, `semantic validate` a následný scan — **PASS** nad aktuálním
  main `aa9e64b`; finalní `kgmaker check` zůstal PASS.
- `kgmaker memory recall` — **PASS**, vrátil historická omezení a aktuální
  resolver location. `kgmaker memory capture --base origin/main` — **PASS**;
  zaznamenal ověřené příkazy a nedostupné toolchain gates jako skipped.
- Skutečné build/compiler/render gate nejsou pro tuto změnu relevantní; změna
  nepřidává compiler/framework/parser ani renderer.

## Příklad

```json
{"service_ownership":{"schema_version":1,"services":[
  {"id":"orders","roots":[{"repo_id":"backend","path":"orders"}],
   "modules":[{"repo_id":"backend","id":"com.example.orders"}],
   "external_systems":[{"id":"ledger"}]}
]}}
```

```python
from pathlib import Path
from kgmaker.workspace import load_workspace, qualified, resolve_service_ownership

workspace = load_workspace(Path("workspace.json"))  # includes a legacy service id `orders`
declaration = workspace["service_ownership"]
context_id = qualified("backend", "jvm:orders")
symbol = {"repo_id": "backend", "path": "@backend/orders/Order.kt",
          "module": "com.example.orders", "context_id": context_id}
result = resolve_service_ownership(symbol, declaration, context_id=context_id)
```

V manifestu musí být root nebo modul explicitně deklarovaný pro `orders`.
Překryv zůstává nejednoznačný; cizí repo v context ID nebo `@` path resolver
odmítne.

## Zbývající práce a omezení

T007 implementuje deklaraci a čistou symbol ownership projekci; neobjevuje služby,
neagreguje topologii a nedokončuje T004. Skutečné deployment boundary identity
musí dodat explicitní manifest. Toolchain skips zůstávají mimo testovaný kontrakt.
