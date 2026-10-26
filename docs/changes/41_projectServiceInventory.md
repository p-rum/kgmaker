# T008 — Inventář služeb a externích systémů

## Problém

T007 validoval explicitní ownership a čistě rozhodoval o vlastnictví jednoho
symbolu; T006 vybíral service/repo/module kontext. Nebyl však společný pohled,
který by tyto kontrakty spojil do stabilního přehledu deklarovaných služeb a
externích systémů bez odvozování deployable služby z repozitáře, konfigurační
hodnoty nebo Spring bean anotace.

## Změny

- `views.project_service_inventory` vytváří T005 `ViewDocument` typu `topology`
  výhradně z načteného workspace manifestu s T007 `service_ownership` a párového
  provider snapshotu. ID služby vychází z explicitního manifest ID; `service_labels`
  mění pouze zobrazovaný text.
- Workspace symbol se spojuje s provider context podle přesného `context_id`.
  Repo a module se doplní z ověřeného contextu před voláním T007 resolveru.
  Dependency/bytecode symbol bez lokální cesty v source snapshotu ownership
  nezíská. T006 vybírá compiler kontext, vrací nejednoznačnost a validuje freshness.
- Production pohled vynechá test/development/unknown scope. SOURCE_ONLY zůstává
  PARTIAL a module coverage UNKNOWN. U skutečného `snapshot_workspace` SOURCE_ONLY výstupu se repo-qualified artifacty a odpovídající provider file nodes stejného repository a přesného context scope porovnají s explicitními T007 roots; service zůstává PARTIAL bez odvozeného module ID. Reálný mixed-scope test v jednom checkoutu ověřuje, že production a test source kořeny nekontaminují jeden druhý; test fixture je vyloučen z production a dostupný jen v test view. External ledger zůstává UNKNOWN bez endpointů a vstupy se nemění. Neznámé/stale/ambiguous hranice a provider truncation zůstanou diagnostikou nebo coverage.
- Externí systém se zobrazí jen podle explicitního T007 ID, i když nemá checkout.
  Jeho interní implementace, endpointy a runtime zůstávají UNKNOWN; vzniká jen
  deklarativní vztah service → external system.
- Projekce nevytváří store ani CLI command a nezapisuje do checkoutu. Vstupní
  workspace se znovu načte read-only a manifest hash se porovná s provider graph.

Související zadání: T008-S01–S05; acceptance T008-AC01–AC06.

## Kompatibilita

View zůstává `kind: topology`; T005 verze, graph v1/v2/v3 a T006/T007 workspace
schémata se nemění. Legacy workspace bez ownership zůstává čitelný a vytvoří
UNKNOWN prázdný inventory s diagnostikou. Migrace není potřeba. Neexistuje nový
CLI command ani persistent katalog.

## Ověření

- `PYTHONPATH=src /workspace/kgmaker-venv/bin/python3 -m pytest -q tests/test_t008_project_service_inventory.py` — **11 passed**.
- `PYTHONPATH=src /workspace/kgmaker-venv/bin/python3 -m pytest -q tests/test_t008_project_service_inventory.py tests/test_t007_define_service_ownership.py tests/test_t006_select_service_contexts.py tests/test_workspace.py tests/test_t005_add_view_model.py tests/test_cross_repo_artifacts.py` — **83 passed**.
- `PYTHONPATH=src /workspace/kgmaker-venv/bin/python3 -m pytest -q -rs` — **320 passed, 25 skipped**. Skips: Maven/JDK exporter, two JDK 21+ with Maven, 14 prepared Maven fixtures, real Maven/Gradle exporters, Gradle 8.13, Kotlin Gradle cache, JVM worker and TypeScript worker. They remain SKIP/BLOCKED, not PASS.
- Alias fixture starts with a default `repo_id="local"` compiler context and symbol, wraps it with `snapshot_workspace` under `backend`, then verifies exact qualified context selection and symbol enrichment. Dependency symbol without a matching source snapshot path is not emitted in the service inventory. Additional real `snapshot_workspace` fixtures with no compiler index verify root-only SOURCE_ONLY inventory and mixed production/test roots in the same checkout; exact scope filtering, PARTIAL status, UNKNOWN module coverage, external declaration preservation and no mutation.
- Invalid snapshot regression compares the manifest, source file, workspace object and provider graph before/after failure. Offline projection test rejects any subprocess call.
- `PYTHONPATH=src /workspace/kgmaker-venv/bin/kgmaker semantic update --root . --base origin/main --note docs/changes/41_projectServiceInventory.md`, scoped `semantic apply` and `semantic validate` — PASS; 73 concepts and 11,607 relationships.
- `PYTHONPATH=src /workspace/kgmaker-venv/bin/kgmaker scan --root .` — PASS; 288 files, 2,353 declarations/sections and 16,850 relationships. `kgmaker check --root .` — PASS; generated docs current at 288 files, 2,641 nodes and 16,850 relationships. `git diff --check` — PASS.
- `kgmaker memory recall --root . T008 explicit service inventory selected workspace contexts ownership limitations verification --token-budget 500` — PASS. `kgmaker memory capture --root . --base origin/main` with focused/full/toolchain/semantic/scan/check/diff validation labels — PASS; episode `episode:d2387d71c812ae3d4549a781122e644a9d4bf6838029913080fbb634487dee2a`.
- Compiler build, actual framework worker, Mermaid renderer and runtime observation were not run: T008 adds no compiler/parser/renderer or runtime path. Existing suite toolchain skips remain visible above.

## Příklad

```python
from pathlib import Path
from kgmaker.workspace import load_workspace, snapshot_workspace
from kgmaker.views import project_service_inventory

manifest = Path("workspace.json")
workspace = load_workspace(manifest)
_, coverage, _, graph, _ = snapshot_workspace(manifest)
view = project_service_inventory(workspace, graph, scope="production",
                                 source_coverage=coverage,
                                 service_labels={"orders": "Orders API"})
```

## Zbývající práce a omezení

T008 dodává pouze deklarovaný service inventory. Neobjevuje služby ani rozhraní,
neřeší deployment compatibility a nezjišťuje externí checkouty/endpoints. T004,
interface catalogs, další topology aggregation a runtime availability zůstávají
mimo tento rozsah.

## Integrace s aktuálním main

Po T008 implementaci byl `origin/main` `7b9a9ea` (PR #25) sloučen do této
větve. T008 `views.py` a `test_t008_project_service_inventory.py` zůstaly
byte-identické s předchozím schváleným HEAD; ověřeno přes
`git diff --exit-code HEAD -- src/kgmaker/views.py tests/test_t008_project_service_inventory.py`.
Semantic artifact zachovává koncepty a vztahy z obou historií i union 72
implementation episodes; aktuální validace uvádí 77 concepts a 11,955 relationships.
Po regeneraci grafu: 291 files, 2,387 declarations/sections, 17,265 relationships;
`kgmaker check`, semantic validation a `git diff --check` prošly.
Integrační běh `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q
tests/test_t008_project_service_inventory.py tests/test_t007_define_service_ownership.py
tests/test_t006_select_service_contexts.py tests/test_workspace.py
tests/test_t005_add_view_model.py tests/test_cross_repo_artifacts.py
tests/test_confluence_configuration.py tests/test_workbooks.py` — **110 passed**.

### Integrace K2 základu

Integrace s main `eff0d3d5d7620b017fe42a65a54f672af8068667` zachovává
schválený inventář i jeho testy byte-identické s `0c5c9ac`.
Sada inventory/context/ownership/workspace/cross-repo/config/scanner:
**106 PASS / 2.14 s**. Zachováno 5 konceptů/9 vztahů; původní main epizody
jsou přesným prefixem, vlastní epizody následují beze změny obsahu.
Duplicitní semantic.py vztahy používají původní ověřené formulace z main.
README prepare/update evidence odpovídá řádkům 156/158; architecture inventory
odstavec zůstává na řádku 151. Scoped semantic apply/validate,
generovaný scan/check a diff check: PASS. Plná sada se pouze kvůli této
integraci neopakuje; nové vzdálené CI ověřuje aktuální HEAD.

### Integrace Windows mainline

Integrovaný base `a83dbab6263eb2fe225f0da51f2f2549c0ab162e` zachovává
`src/kgmaker/views.py` a `tests/test_t008_project_service_inventory.py` byte-identické
s T008 schváleným HEAD `23e75d5dbf17f1909c0ba17e88820a2f6fde44b0`.
Focused T005–T008/workspace/Windows worker sady: **84 passed, 5 skipped**
(4 skutečné compiler workery nejsou v tomto prostředí připravené; Windows
non-admin smoke vyžaduje Windows CI). Celá sada se kvůli nezávislé Windows
změně neopakovala. Semantic artifact má současný main episode prefix 80 záznamů
plus 3 T008 epizody; README semantic prepare/update evidence nyní cituje řádky
162 a 164. `semantic validate`, regenerace `kgmaker scan`, `kgmaker check` a
`git diff --check`: PASS; vygenerovaný graf obsahuje 301 souborů, 2,829 uzlů a 18,020 vztahů.
