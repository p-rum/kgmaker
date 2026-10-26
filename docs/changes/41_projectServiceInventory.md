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
  PARTIAL a module coverage UNKNOWN. U skutečného `snapshot_workspace` SOURCE_ONLY výstupu se repo-qualified artifacty a odpovídající provider source nodes porovnají s explicitními T007 roots; service zůstává PARTIAL bez odvozeného module ID. Test ověřuje vyloučení test fixture, zachování external ledger jako UNKNOWN bez endpointů a nulovou mutaci. Neznámé/stale/ambiguous hranice a provider truncation zůstanou diagnostikou nebo coverage.
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
- `PYTHONPATH=src /workspace/kgmaker-venv/bin/python3 -m pytest -q tests/test_t008_project_service_inventory.py tests/test_t007_define_service_ownership.py tests/test_t006_select_service_contexts.py tests/test_workspace.py tests/test_t005_add_view_model.py tests/test_cross_repo_artifacts.py` — **82 passed**.
- `PYTHONPATH=src /workspace/kgmaker-venv/bin/python3 -m pytest -q -rs` — **319 passed, 25 skipped**. Skips: Maven/JDK exporter, two JDK 21+ with Maven, 14 prepared Maven fixtures, real Maven/Gradle exporters, Gradle 8.13, Kotlin Gradle cache, JVM worker and TypeScript worker. They remain SKIP/BLOCKED, not PASS.
- Alias fixture starts with a default `repo_id="local"` compiler context and symbol, wraps it with `snapshot_workspace` under `backend`, then verifies exact qualified context selection and symbol enrichment. Dependency symbol without a matching source snapshot path is not emitted in the service inventory. An additional real `snapshot_workspace` with no compiler index verifies root-only SOURCE_ONLY inventory, production scope filtering, PARTIAL status, UNKNOWN module coverage and external declaration preservation.
- Invalid snapshot regression compares the manifest, source file, workspace object and provider graph before/after failure. Offline projection test rejects any subprocess call.
- `PYTHONPATH=src /workspace/kgmaker-venv/bin/kgmaker semantic update --root . --base origin/main --note docs/changes/41_projectServiceInventory.md`, scoped `semantic apply` and `semantic validate` — PASS; 72 concepts and 11,521 relationships.
- `PYTHONPATH=src /workspace/kgmaker-venv/bin/kgmaker scan --root .` — PASS; 288 files, 2,351 declarations/sections and 16,761 relationships. `kgmaker check --root .` — PASS; generated docs current at 288 files, 2,639 nodes and 16,761 relationships. `git diff --check` — PASS.
- `kgmaker memory recall --root . T008 explicit service inventory selected workspace contexts ownership limitations verification --token-budget 500` — PASS. `kgmaker memory capture --root . --base origin/main` with focused/full/toolchain/semantic/scan/check/diff validation labels — PASS; episode `episode:d31fbd6844ef8701e95c9c839955c6a9d2ed13814ae531fe348e7856f29ad53f`.
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
