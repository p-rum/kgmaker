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
  Výsledek zachovává zadaný context ID.
- Nevalidní nebo duplicitní deklarace se odmítne při načtení manifestu. Resolver
  nic nezapisuje a nepovyšuje kind evidence.

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
- Finální `PYTHONPATH=src /workspace/kgmaker-venv/bin/python3 -m pytest -q tests/test_t007_define_service_ownership.py tests/test_workspace.py tests/test_t005_add_view_model.py` po integraci a zpřesnění module selectorů — **43 passed**.
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

`resolve_service_ownership({"repo_id":"backend","path":"orders/Order.kt"},
declaration, context_id="jvm:orders")` vrátí vlastníka pouze tehdy, pokud jediná
explicitní deklarace odpovídá. Překryv zůstává nejednoznačný.

## Zbývající práce a omezení

T007 implementuje deklaraci a čistou symbol ownership projekci; neobjevuje služby,
neagreguje topologii a nedokončuje T004. Skutečné deployment boundary identity
musí dodat explicitní manifest. Toolchain skips zůstávají mimo testovaný kontrakt.
