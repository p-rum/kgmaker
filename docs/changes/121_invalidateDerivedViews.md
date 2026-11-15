# T037 — invalidace odvozených pohledů

Baseline: `14d7f7cefab2fa5c9cf8c6d939d3b92e838faea8` (`main`, 2026-11-15).
Task: [T037](../tasks/T-037_invalidate-derived-views.md), kroky S01–S05,
acceptance AC01–AC06. Historický stav při původním checkpointu IN_PROGRESS; ověření
VERIFIED_IN_SCOPE pro AC01–AC05 po níže uvedených opravách a PARTIAL pro AC06.
První review nad `43d7010c4c3f3f632c41b68bbf4f1efa53018712` vrátilo REQUEST_CHANGES;
opakované review a PR/publication tehdy byly NOT_RUN. Aktuální PR103/integrace
je uvedena v závěrečném kroku níže. T004 se tímto krokem neuzavírá.

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


## Oprava review 1 — T037-S03/S04/S05, AC04/AC06: transakční CLI cache

Výchozí SHA: `43d7010c4c3f3f632c41b68bbf4f1efa53018712`. Problém: veřejné CLI
publikovalo cache před `filter_topology`, expected-fingerprint a output validací;
neplatný request mohl vytvořit cache nebo přepsat poslední validní soubor, včetně
capture při stejné vstupní/výstupní cestě.

Skutečná změna: `view_cache.prepare_view` a `prepare_snapshot_view` vracejí
`PreparedView`, který odděluje výpočet od `.publish()`. `service_topology` dodává
stejnou přípravu pro T016 handoff; původní okamžitě zapisující API je zachováno.
`architecture_cli` připraví cache, provede filter/fingerprint/safe-output/size
kontroly, zapíše a flushne stdout a teprve při exit 0 publikuje. Exit 4 nic
nepublikuje. Cache cíle odmítají symlinky včetně rodičů, hardlinky a ne-regulární
soubor. CLI navíc chrání explicitní vstupy a při local capture omezuje cache
uvnitř zdrojového repozitáře na `.kgmaker/views/`. Selhání atomické výměny zachová
starou cache a uklidí nově vzniklé prázdné rodiče.

Dotčené soubory: `src/kgmaker/view_cache.py`, `src/kgmaker/service_topology.py`,
`src/kgmaker/architecture_cli.py`, `tests/test_t037_invalidate_derived_views.py`.
Kompatibilita: stejné JSON view/envelope a exit codes; cache-only cesty mají
přísnější ochranu aliasů. Stdout není rollbackovatelný export: při pozdějším
selhání cache commit může obsahovat validní view, ale CLI vrátí 2 a poslední cache
se nemění. Consumers musí vyhodnotit exit code. Širší T038 export transakce a
souběžní nezávislí zapisovatelé nejsou implementováni.

Veřejné negativní testy: `test_cli_rejected_request_preserves_inputs_and_cache`
(missing/stale/hit × invalid filter/focus/size/expected fingerprint/format/strict),
`test_cli_late_output_failure_never_publishes` (output limit, sanitization,
write/flush, cancel), `test_cli_failed_atomic_publication_preserves_files_and_removes_temporary_paths`,
`test_cli_cache_input_aliases_are_rejected_without_writes`,
`test_local_capture_cache_cannot_overwrite_workspace_or_source`. Pozitivní
`test_local_capture_explicit_cache_directory_preserves_all_source_inputs` používá
skutečný parser a explicitní `.kgmaker/views/`; stdout cached/uncached shodu
zachovává existující CLI test. Filesystem assertions zahrnují bytes, mtime i
seznam adresářů. Výsledek všech těchto případů: PASS v níže uvedené cílené sadě.

Dokumentační plochy: README, architecture capability, `docs/view-cache.md`
(API a prepare/publish příklad), `docs/architecture-json-cli.md` (negativní CLI
příklad a stdout/commit limit), production progress i AC04/AC06 řádky aktualizovány
v této opravě a odkazují na change121. Registr: bez dopadu, identita/revize ani
závislosti T037 se nemění. Instalované instrukce/templates: bez dopadu, žádná změna.

## Oprava review 2 — T037-S03/S04/S05, AC04/AC05: původní snapshot

Výchozí SHA: `43d7010c4c3f3f632c41b68bbf4f1efa53018712`. Jednorázové
`dict(snapshot)` skrývalo top-level mutaci původního vstupu během builderu.
`view_cache` nyní váže původní snapshot, včetně nested/list struktur, a znovu
vypočte dependency fingerprint po builderu a těsně před publish. Stejný guard
používá původní `context_selection`. Změna vstupu vrátí
`VIEW_CACHE_INPUT_CHANGED_DURING_BUILD` a cache se nepřepíše.

Dotčené soubory: `src/kgmaker/view_cache.py`,
`tests/test_t037_invalidate_derived_views.py`. Testy:
`test_snapshot_wrapper_detects_original_input_mutations` (replace/add/delete/
nested/list), `test_snapshot_wrapper_unchanged_build_hit_and_deferred_guard`,
`test_deferred_snapshot_miss_rechecks_original_before_publication` (missing/stale).
Výsledky PASS. Ochrana nezvrací vedlejší efekty samotného uživatelského builderu;
zabraňuje publikaci artefaktu pod neodpovídající vazbou. Schéma a fingerprint
pro nezměněný vstup jsou kompatibilní.

Dokumentace: `docs/view-cache.md` explicitně popisuje původní objekt a odložený
guard; architecture, README, CLI/progress a AC04 odkazují na stejný kontrakt.
CLI syntax/příklady mají stejné parametry (bez dopadu navíc oproti opravě 1).
Registr a init templates jsou bez dopadu.

## Oprava review 3 — T037-S05, AC06: zachovaná sémantická evidence

Výchozí SHA: `43d7010c4c3f3f632c41b68bbf4f1efa53018712`. Původní scoped patch
zachoval nový cache koncept, ale vypustil 9 původních konceptů a 27 vazeb ze
změněných dokumentů/modulů. Historický výsledek `semantic validate PASS` výše
ověřoval validitu zbylého obsahu, nikoli zachování původních faktů.

Oprava obnovuje původní entries z baseline `14d7f7c`, ověřuje jejich aktuální
source tvrzení a novým scoped patchem reanchoruje lokace/IDs změněných deklarací.
Zůstává například explicit service inventory, realm-bound data resources,
workspace ownership/context boundary a optional agent-authored semantic layer.
Read-only architecture koncept popisuje výchozí cestu a explicitní opt-in cache.
Historické implementation episodes se nemažou. `.kgmaker/GRAPH.md` a GRAPH.mmd
se obnovují pouze příkazem, žádný generated graf se needituje ručně.

Dotčené soubory: `.kgmaker/semantic.json`, `.kgmaker/GRAPH.md`, `.kgmaker/GRAPH.mmd`.
Kompatibilita: původní concept IDs, confidence a historical episodes zůstávají;
posuny symbolových ID jsou reanchor stejné deklarace. Runtime/build evidence se
nemění. README/API/CLI/progress/acceptance obsahují odkazy na tento change note;
uživatelské příkazy a task registry nemají touto opravou další dopad.

### Kontroly oprav a zbývající práce

`python3 -m pytest -q tests/test_t037_invalidate_derived_views.py` při první iteraci:
**FAIL, 3 failed / 68 passed** — nový test nesprávně pokládal neznámý focus za
invalidní vstup; stávající T017 kontrakt vrací přiznaný unresolved výsledek.
Fixture byla změněna na skutečně neplatný focus, veřejné chování se nezměnilo.
Následně byl spuštěn přesný sedmimodulový příkaz uvedený v T037-S04 výše:
**PASS, 296 passed in 10.96s, 0 failed, 0 skipped** (T037 modul obsahuje 74 případů).
`git diff --check`: PASS po opravách kódu/testů.

Full `python3 -m pytest -q`: NOT_RUN na výslovný pokyn cílených kontrol pro tento
balík. JVM/TS worker/runtime: NOT_RUN, změna se týká lokální Python cache a
nezvyšuje podporovaný compiler/runtime rozsah. Opakované nezávislé review, push/PR,
GH Actions a merge: NOT_RUN, zajišťuje nadřazený agent po předání opravy.


Finální doplnění opravy 1 zachovává cleanup nových prázdných adresářů i při
`KeyboardInterrupt` v atomickém zápisu. Po této změně byl opakován pouze přímo
dotčený modul: `python3 -m pytest -q tests/test_t037_invalidate_derived_views.py`
→ **PASS, 76 passed in 4.65s, 0 failed/skipped**. Původní 296-testová regrese
zůstává výše časově přiřazená; znovu se bez důvodu nespouštěla.

Sémantická oprava: `./kgmaker semantic update --base
14d7f7cefab2fa5c9cf8c6d939d3b92e838faea8 --note
docs/changes/121_invalidateDerivedViews.md` připravil 12 cest a 300 nearby nodes.
První `./kgmaker semantic apply` byl **FAIL** (`unknown node ID`): reanchor
použil zastaralý lokální strojový index pro posunutou funkci `architecture_cli.run`.
Soubor se při odmítnutí nepublikoval. Po `./kgmaker scan --no-docs` a reanchoru
podle aktuálních deklarací byl `./kgmaker semantic apply` **PASS**, 43 concepts /
138 relationships v source-authored vrstvě; `./kgmaker semantic validate` **PASS**.
Následující audit **PASS** zachoval všech 42 původních concept IDs, 135 vazeb včetně
confidence (s normalizací pouze koncového čísla řádku symbolu) a všech 286 původních
episodes jako nezměněné záznamy. K tomu zůstalo 5 již existujících T037 episodes.

Reprodukce preservation auditu z rootu checkoutu:

```sh
python3 - <<'PYCODE'
import json, re, subprocess
from pathlib import Path
old = json.loads(subprocess.check_output(['git', 'show', '14d7f7c:.kgmaker/semantic.json']))
new = json.loads(Path('.kgmaker/semantic.json').read_text())
def key(edge):
    return (re.sub(r'::\d+$', '', edge['source']),
            re.sub(r'::\d+$', '', edge['target']), edge['kind'],
            edge['confidence'], edge['confidence_score'])
assert {n['id'] for n in old['nodes']} <= {n['id'] for n in new['nodes']}
assert {key(e) for e in old['edges']} <= {key(e) for e in new['edges']}
assert all(episode in new['episodes'] for episode in old['episodes'])
print('PASS: baseline concepts, relationships/confidence and historical episodes preserved')
PYCODE
```

Po finálních dokumentačních/cleanup změnách se packet připravuje znovu; scoped
patch znovu deklaruje všechny dotčené a zdrojově ověřené entries bez removals.
Finální `semantic apply`, `semantic validate`, `memory capture`, `scan` a
`git diff --check` jsou závěrečné lokální kontroly před čistým předáním. Nemění
výsledek neprovedeného full pytest ani neznamenají nezávislé APPROVE.


Závěrečné skutečné výsledky (2026-11-15): obnovený packet + `semantic apply`
**PASS** (43 source-authored concepts / 138 edges), `semantic validate` **PASS**
(334 concepts / 31204 relationships včetně tehdejších episodes).
`./kgmaker memory capture --base 43d7010c4c3f3f632c41b68bbf4f1efa53018712
--validation targeted-pytest=passed --validation diff-check=passed --validation
full-suite=skipped --validation runtime-toolchain=skipped` **PASS**, episode
`489168b638284536fe917209617f960bbe0c2ce541b51d455d624ed604d67c11`.
`./kgmaker scan` **PASS**, 563 files, 5847 declarations/sections,
45127 relationships (včetně 335 semantic concepts / 31544 relationships).
Opakovaný preservation audit **PASS**, celkem 43 concepts / 138 edges / 292 episodes;
všechny baseline entries zachovány. `git diff --check 14d7f7c` **PASS**.
Generated views se po tomto závěrečném textovém záznamu obnovují stejným příkazem;
výsledky Python testů se tím nerozšiřují na další scope.


## Integrace po PR102 — T037-S03/S04/S05, AC04–AC06 (2026-11-15)

Výchozí T037 HEAD `ed79c3b078514f7914d11431a6b5e30847cecf59` má nezávislé
APPROVE a otevřený PR103. Integrační main
`9f88d8463b3c968592f0f1937736b752dfccee1d` je ověřený dvourodičový merge
PR102, obsahuje MERGED PR101 runtime a W06. `git merge --no-ff --no-commit
9f88d8463b3c968592f0f1937736b752dfccee1d` zachovává historii bez rebase/force.
Dodání T037 zůstává PR_OPEN; nový HEAD čeká na nezávislé review a merge.

Rekognoskace dle kgmaker-context ověřila status/query/memory recall a zdrojové
kontrakty. T037 mění cache/architecture/topology/provider; runtime/W06 mění
jiné funkční moduly. Překryv je pouze v README, architecture dokumentaci,
acceptance/progress a semantic/generated artefaktech. Konflikt architecture
zachovává oba odstavce: explicitní cache prepare→validate/output→publish i
opt-in runtime producer. Žádný funkční integrační patch nebyl potřeba; původní
snapshot guard, vstupní alias ochrana a poslední validní cache se nemění.

Semantic konflikt spojuje již schválené fakty obou rodičů: 43 konceptů,
138 vztahů a union 293 původních epizod. W06 text současné JPA rule v9 i T037
read-only-default/explicit-cache hranice zůstávají. Následující aktuální packet
reanchoruje source lines/IDs; žádný vztah ani historická epizoda se nemaže.
Generované GRAPH.md/mmd jsou obnovovány výhradně příkazem scan.

Dokumentace: tento krok, production progress a acceptance odlišují PR101/102
MERGED od PR103 PR_OPEN. V change120 je opravena pouze kotva odkazu na aktuální
W06 acceptance sekci, historické výsledky zůstávají. README, `docs/view-cache.md`,
`docs/architecture-json-cli.md`, compiler/runtime příručky a CLI příklady jsou
bez nové změny veřejného chování: oba dodané kontrakty jsou zachovány. Registry,
API/schémata, installed templates a worker protocol jsou bez dopadu. Širší T038
export transakce, souběžní zapisovatelé a celý T004 nejsou tímto merge dodány.

Přesný nový T037 testový příkaz na integrovaném stromu:

```sh
PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_t037_invalidate_derived_views.py tests/test_graph_provider.py tests/test_t016_aggregate_service_topology.py tests/test_t018_explain_view_elements.py tests/test_t019_add_architecture_json_cli.py tests/test_t032_persist_process_review.py tests/test_t033_catalog_business_processes.py
```

Runtime/W06 mají předchozí důkaz nad HEAD `00603901` se stejným tree jako
merge main: implementační 205 PASS / 0 SKIP, 36.87 s a nezávislé opakování
205 PASS / 0 SKIP, 37.88 s. Tento integrační krok tyto sady znovu nespouští;
zachování kódu prokazuje byte identity proti main. Full suite, další toolchain
matice a GH CI jsou NOT_RUN dle pověření. Nový T037 výsledek a preservation
kontroly jsou zapsány níže; nejde o tvrzení nového runtime pozorování.


Výsledek nového sedmimodulového běhu: **PASS, 298 passed / 0 skipped, 11.07 s**.
Byte identity proti výchozímu T037 HEAD: `view_cache.py`, `graph_provider.py`,
`architecture_cli.py`, `service_topology.py` a T037 test **PASS**. Proti main:
`framework.py`, `named_queries.py`, `inspection_cli.py`, `runtime_evidence.py`,
named-query/runtime/JPQL testy a `RuntimeTrace.java` **PASS**. Tím je odděleno
nové ověření T037 od historických worker/runtime výsledků PR102.

## Údržba po merge — T037-S05 / AC06 (2026-11-15)

Výchozí SHA: T037 `ed79c3b078514f7914d11431a6b5e30847cecf59` a main
`9f88d8463b3c968592f0f1937736b752dfccee1d`. Řešení semantic konfliktu vychází
z aktuálních main facts, přidává existující T037 cache koncept/tři vztahy a
zachovává jeho read-only-default summary; episode union kontroluje shodné objekty
pod stejným ID. Nejde o vytváření nových vztahů. Následný scoped patch pro
10 konceptů a 30 vztahů reanchoruje původní citace dle správného rodiče a
aktuálního graph indexu. Nepřesné historické blank-line odkazy architecture CLI
jsou zpřesněny na odpovídající `run`/`_preflight` deklarace. Generated grafy
nebyly řešeny ruční editací; úplně je obnovuje scan.

```sh
./kgmaker semantic update --base 9f88d8463b3c968592f0f1937736b752dfccee1d --note docs/changes/121_invalidateDerivedViews.md
./kgmaker scan --no-docs
# Current update_id, source-backed patch; remove_nodes/remove_edges jsou prázdné.
./kgmaker semantic apply
./kgmaker semantic validate
python3 /tmp/t037-integration-preservation.py
./kgmaker memory capture --base 9f88d8463b3c968592f0f1937736b752dfccee1d --validation t037-targeted=passed --validation semantic-preservation=passed --validation source-identity=passed --validation full-suite=skipped
./kgmaker scan
./kgmaker check
git diff --check 9f88d8463b3c968592f0f1937736b752dfccee1d
git diff --check ed79c3b078514f7914d11431a6b5e30847cecf59
```

`semantic apply` a `semantic validate` **PASS**. Preservation audit **PASS**:
stejný algoritmus z opravy review 3 výše (concept IDs, relationship tuple včetně
confidence s normalizací koncového line suffixu, původní episode objekty) byl
proveden proti všem třem referencím: baseline **42/135/286**, T037 rodič
**43/138/292**, runtime/W06 main **42/135/287**. Všechny zachovány; sjednocení
obsahuje **43 konceptů / 138 vztahů / 293 původních epizod** před novou capture.
První scan před reanchor pravdivě vynechal29 stale vztahů; nejsou odstraněny.
Záznam tohoto kroku nerozšiřuje veřejné cache/CLI chování. README/API/CLI příklady
jsou bez dalšího dopadu; progress/acceptance uvádějí aktuální dodání a testy.
Full suite a GH CI NOT_RUN; zbývá nezávislé review nového HEAD a merge PR103.

Závěrečné výsledky údržby: current-packet `semantic apply/validate` **PASS**,
`memory capture` **PASS** (nová epizoda
`f5d4511dec7752fb940cdb6f5d88b7bb44e22073504a6cd32c904d1800592d80`),
celkem **43 / 138 / 294** source-authored concepts/edges/episodes. `scan` a
`check` **PASS**, žádné vynechané stale semantic entries. Oba diff checky
**PASS**; původní třístranný preservation audit i source identity po capture
**PASS**. Grafy se po tomto výsledkovém textu obnovují stejným příkazem scan.
Nová capture je jediný přidaný historický záznam tohoto integračního kroku.
