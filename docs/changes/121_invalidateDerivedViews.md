# T037 — invalidace odvozených pohledů

Baseline: `14d7f7cefab2fa5c9cf8c6d939d3b92e838faea8` (`main`, 2026-11-15).
Task: [T037](../tasks/T-037_invalidate-derived-views.md), kroky S01–S05,
acceptance AC01–AC06. Delivery při tomto checkpointu IN_PROGRESS; ověření
VERIFIED_IN_SCOPE pro AC01–AC05 a PARTIAL pro AC06. PR/review/publication jsou
ještě NOT_RUN. T004 se tímto krokem neuzavírá.

## T037-S01 — dependency fingerprint a graph context binding

Problém: žádný společný kontrakt nevázal uložený view na všechny vstupy, které
mohou změnit jeho obsah. Úzce vybraný seznam nalezených providerů by navíc
neodhalil dříve chybějícího providera.

Změny: `view_cache.dependency_binding` fingerprintuje public workspace i celý
graph snapshot, contexts, pravidla, scope, context selection a explicitní
annotations/review snapshot. `graph_provider.view_context_fingerprint` samostatně
normalizuje pořadí úplného context inventory; generated timestamp není závislost.
Úplné workspace/graph inventories zachytí nově nalezené provider deklarace i
negativní lookup prostor. Souborům `.kgmaker/graph.json` se nemění schéma.

Dotčené soubory: `src/kgmaker/view_cache.py`, `src/kgmaker/graph_provider.py`,
`tests/test_t037_invalidate_derived_views.py`.

Ověření: `test_dependency_mutations_force_rebuild_without_reusing_cached_approval`
mění service, contract, context, rule, annotation a workspace provider mapping;
každá změna vyvolá builder. `test_cache_hits_same_exact_scope_context_and_dependency_snapshot`
ověřuje přesný hit. Výsledek: PASS v souhrnné cílené sadě.

Kompatibilita: formáty graph v1/v2/v3, ViewDocument a jejich veřejné IDs zůstávají
beze změny. Nový lokální cache envelope má vlastní `schema_version: 1`.
Omezení: volající musí uvést všechny verze pravidel použitých builderem a dodat
obsahově odpovídající snapshot.

## T037-S02 — invalidace negativních lookupů

Problém: nový provider může vyřešit dříve unresolved binding, přestože dříve
neexistoval identifikátor provideru v dependency seznamu.

Změny: klíč cache zahrnuje úplný explicitní graph/workspace snapshot; invalidace
je záměrně široká a každá změna inventory způsobí miss. Není přidán samostatný
resolver, graph store ani discovery.

Dotčené soubory: `src/kgmaker/view_cache.py`,
`tests/test_t037_invalidate_derived_views.py`.

Ověření: `test_negative_lookup_new_provider_and_unrelated_edit_invalidate_conservatively`
přidá nového providera do původně prázdného provider inventory a ověřuje nový
builder call; druhá část dokládá dovolenou invalidaci při nesouvisející editaci.
Výsledek: PASS v souhrnné cílené sadě.

## T037-S03 — bezpečný rebuild a nepřenášení approval

Problém: invalidní snapshot, selhání builderu, změna vstupů během builderu nebo
zastaralý callback nesmí přepsat poslední validní view. Review status není
technická evidence ani oprávnění znovu použít starý cache hit.

Změny: cache publikuje až po round-trip validaci ViewDocument přes existující
`analysis_model.atomic_write`; vyžaduje `expected_baseline_fingerprint` a ověřuje
jej před publikací i při hitu. Znovu kontroluje dependency fingerprint po builderu.
Nevalidní/corrupt cache zůstává při selhání nedotčena. Symlink target/parent se
odmítne před spuštěním builderu. `aggregate_service_topology_cached` používá
validovaný T016 handoff a baseline odvozený z aktuálního capture ID. Explicitní
T032 review snapshot (`annotations`) invaliduje cache, ale nevkládá review payload
do technického topology view. CLI integrace je volitelná přes `--view-cache`;
výchozí CLI zůstává cache-free.

Dotčené soubory: `src/kgmaker/view_cache.py`, `src/kgmaker/service_topology.py`,
`src/kgmaker/architecture_cli.py`, `tests/test_t037_invalidate_derived_views.py`.

Ověření: testy `test_invalid_inputs_and_builder_failure_leave_input_and_last_valid_artifact_unchanged`,
`test_dependency_change_during_builder_does_not_publish_candidate`,
`test_stale_builder_result_cannot_be_published_under_a_new_dependency_binding`,
`test_corrupt_cache_is_a_miss_and_failed_rebuild_preserves_corrupt_bytes`,
`test_symlinked_cache_parent_is_rejected_before_builder_or_write` a
`test_public_topology_projection_cache_is_used_and_review_transition_invalidates`.
Poslední test volá skutečný T032 `read_process_reviews`: po změně explicitního
process baseline se efektivní status mění APPROVED → NEEDS_REVALIDATION a aktivní
anotace jsou prázdné; topology cache se znovu sestaví a výstup neobsahuje approval.
Výsledek: PASS v souhrnné cílené sadě.

Kompatibilita: T016 pure `aggregate_service_topology` zůstává beze změny; cache
wrapper je samostatný a opt-in. `architecture topology` bez `--view-cache` zachovává
stejný JSON. Omezení: cache je single-file, local-only a není distribuována ani
zamykána napříč nezávislými procesy. Stale entries jsou misses; T038 atomická
publikace uživatelských exportů zde není implementována.

## T037-S04 — reprodukční, pozitivní, negativní a mutation testy

Před implementací API byl spuštěn `python3 -m pytest -q
tests/test_t037_invalidate_derived_views.py`; výsledek byl reprodukovatelný
collection ERROR `ModuleNotFoundError: kgmaker.view_cache` (požadovaný RED).
Po implementaci `python3 -m pytest -q tests/test_t037_invalidate_derived_views.py`
dokončil 22 passed.

Konečný příkaz pro všech 7 cílených modulů:

```sh
python3 -m pytest -q tests/test_t037_invalidate_derived_views.py tests/test_graph_provider.py tests/test_t016_aggregate_service_topology.py tests/test_t018_explain_view_elements.py tests/test_t019_add_architecture_json_cli.py tests/test_t032_persist_process_review.py tests/test_t033_catalog_business_processes.py
```

Výsledek: **244 passed in 7.36s**, 0 failed, 0 skipped. Tato sada zahrnuje
T037 nové API/CLI, T018/T032/T033 kontrakty a upstream T016/T019 integraci.

`test_mutation_refresh_matches_independent_full_rebuild` pro create/edit/delete/rename
porovnává výsledný obsah s nezávislým builderem, nikoliv funkcí cache.
`test_architecture_topology_cli_uses_only_explicit_cache_flag` ověřuje shodu
výstupu s uncached cestou a nezměněný artefakt při hitu. Všechny výsledky jsou
lokální Python testy; nejde o runtime observation ani produkční coverage.

## T037-S05 — uživatelská dokumentace a předání

Aktualizováno: README (API/CLI usage), `docs/architecture.md`,
`docs/architecture-json-cli.md`, nový [cache API a limity](../view-cache.md),
`docs/production-analysis-progress.md` a `docs/acceptance-inventory.md`.
Příklady byly porovnány s `get_or_build_view`, `aggregate_service_topology_cached`
a skutečným parserem `architecture topology --view-cache PATH`. Nezměnil se task
registry, protože identita/revize/dependencies zůstaly stejné. `./kgmaker semantic
update --base 14d7f7cefab2fa5c9cf8c6d939d3b92e838faea8 --note
docs/changes/121_invalidateDerivedViews.md --token-budget 12000` připravil packet
pro 12 changed paths/300 nearby graph nodes. Předchozí `memory recall` při prázdném
graph indexu bylo nedostupné; po `./kgmaker scan --no-docs` recall vrátil nové
source/test locations. Scoped `.kgmaker/semantic-patch.json` obsahoval jeden nový
koncept a tři přesné source-backed `implements/uses` vazby: cache modul,
T016 wrapper a explicitní CLI callsite. `./kgmaker semantic apply` PASS,
`./kgmaker semantic validate` PASS (322 concepts, 29999 relationships) před
memory capture. Následný `./kgmaker scan` PASS po explicitní capture validované
implementation episode; indexoval 563 files. Declaration/relationship totals
zahrnují novou generated episode a scan je deterministicky přegeneroval. Finální
`./kgmaker semantic validate` PASS po scan.
Po cílených kontrolách `./kgmaker memory capture --base
14d7f7cefab2fa5c9cf8c6d939d3b92e838faea8 --validation targeted-pytest=passed
--validation diff-check=passed --validation full-suite=skipped --validation
runtime-toolchain=skipped` PASS zachytil validovanou implementation episode do
`.kgmaker/semantic.json`. Předchozí lokální captures po RED/mutation-oracle/help
iteracích zůstaly jako historické episodes; finální graph byl po aktuální capture
znovu vygenerován. Žádná episode ID ani generated graph nebyly ručně přepsány.

Kompatibilita/limity: cache nemění confidence/freshness/availability, procesní
approval, graph store ani podporované parsery. CLI write je pouze explicitní přes
`--view-cache`; Python API path je volající určuje výslovně. Neexistuje cache
migrace staršího formátu, protože T037 zavádí nový samostatný `schema_version: 1`.

Přesné zbylé kontroly:

- `python3 -m pytest -q` full suite: NOT_RUN (tento checkpoint používá cílenou
  sadu; žádný full acceptance se z 244 testů nevyvozuje).
- Skutečný compiler/framework worker, native/toolchain a runtime observation:
  NOT_RUN / mimo scope; T037 nemění compiler frameworky ani nespouští aplikaci.
- Skutečný Mermaid/browser render: NOT_RUN / mimo scope; T037 nemění renderer.
- Nezávislé review, remote diff, povinné CI a PR URL: NOT_RUN při vytvoření
  checkpointu; vyžadují samostatné remote publikování/review.
- Celý T004 a libovolný produkční workspace: stále nedokončeno / NOT_RUN.
