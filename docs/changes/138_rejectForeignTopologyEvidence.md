# Kontrola scope a kontextu v T021 Mermaid

[T021](../tasks/T-021_render-topology-mermaid.md) / T021-AC04, AC05 a AC06.
Výchozí HEAD [#113](https://github.com/p-rum/kgmaker/pull/113)
`52e8e25b3378ebe0f2dfc5acba81edf8a90c725c`. Follow-up [#115](https://github.com/p-rum/kgmaker/issues/115).
Oprava a přenos zdrojů testovány nad lokální baseline `465b121992aad50c2885acef0fd038531a31293a`. GitHub main `8f362471a8254ff9a0e44870c490a1dcb6b067b1` přidává samostatný review workflow. Ověření PARTIAL.

T021-S01 a T021-S03 kontrolují před renderováním scope obálky T017 a všech
uzlů a hran. Explicitně vybrané kontexty omezují seznamy u konkrétních
uzlů/hran. Neznámý scope a chybějící kontext jsou přípustné. Použitý je stávající
parser referencí T017. Bez druhého filtrování, s původní metadata a omissions.
Cizí scope/kontext vyvolá `TOPOLOGY_MERMAID_FOREIGN_SCOPE` nebo
`TOPOLOGY_MERMAID_FOREIGN_CONTEXT`. Parametry CLI a verze dokumentu jsou kompatibilní.

Příklad `kgmaker architecture topology --capture-snapshot topology-inputs.json --format mermaid`
odmítne uzel `scope=test` v produkčním snapshotu a zachová poslední
validní export.

T021-S04 a T021-S05 aktualizují [testy](../../tests/test_t021_render_topology_mermaid.py),
[README](../../README.md), [API a CLI](../architecture-json-cli.md),
[acceptance](../acceptance-inventory.md) a [stav](../production-analysis-progress.md).
Historický [change132](132_renderTopologyMermaid.md) odkazuje na tuto revizi.

- `pytest -p no:cacheprovider -q --tb=short tests/test_t021_render_topology_mermaid.py -k 'foreign_scope or foreign_claim'`
  — RED na původním rendereru, 8 FAIL, 10 deselected.
- `pytest -p no:cacheprovider -q --tb=short tests/test_t021_render_topology_mermaid.py tests/test_t017_filter_topology_scope.py tests/test_t016_aggregate_service_topology.py tests/test_t019_add_architecture_json_cli.py tests/test_t020_render_interface_markdown.py`
  — 181 PASS, 0 SKIP nad přesnou větví #113 i nad zdrojově integrovanou lokální baseline. Skutečný Node 22.22.1, Mermaid 11.4.1 a jsdom 26.
  Součástí actual hostile label, HTTP a Kafka parse/render.
- `git diff --check` PASS. Přenos a ověření sémantické historie, úplná sada, GitHub CI a publikované exact-pair review NOT_RUN. Oprava přímo nepovyšuje static evidence.


## Ověření po T052 / T021-S01, S03, S04 a S05

Přenesený zdrojový a testovací diff #123 byl ověřen nad main
`8ff2529ffb50b42ed2209d97478ea3e4cbf46042` s tree
`c869302cdc2a7d9982d64058b6267ae603382e06`. Pět testovacích souborů z
výše uvedeného příkazu ověřilo kontrakty T016/T017/T019/T020 i T021.
S Node 22.22.1, Mermaid 11.4.1 a jsdom 26.0.0 prošlo
**181 PASS / 0 SKIP**, 8,11 s. CLI nad explicitním snapshotem, formát
a režim bez publikace jsou beze změny. Relevantní upstream T017/T019/W09
již eviduje původní checkpoint. Registr a init nemají nový dopad.

Samostatná úplná sada, T045 review přesného nového páru a GitHub Actions
nadále čekají na ověření. Tento výběr prokazuje rozsah a kontext rendereru.

## T021-S01 / T021-AC05 — validace přímé provenance po review

Výchozí main `8ff2529ffb50b42ed2209d97478ea3e4cbf46042`, tree
`c869302cdc2a7d9982d64058b6267ae603382e06`. Lokální kandidát před opravou měl
tree `a34d21954fec0d28d50c8f6a8d79d8883c0a2315`. Review reprodukovalo, že uzel
nebo hrana s korektním scope a kontextem mohly v diagramu citovat cizí proof.

[Renderer](../../src/kgmaker/architecture_render.py) kontroluje také kontext
a scope záznamů, na které odkazují `evidence_refs` vykreslených uzlů a hran.
Například vybraný `ctx:prod` odmítne přímo citovaný `proof:channel` s
`context_ids: ["ctx:foreign"]` a produkční dokument odmítne přímo citovaný
proof se `scope: test`. Použije stávající chyby `TOPOLOGY_MERMAID_FOREIGN_CONTEXT`
a `TOPOLOGY_MERMAID_FOREIGN_SCOPE`. Chybějící scope nebo kontext zůstává
nedoložený. Záznamy citované pouze vynechanými hranami se dále zobrazují
v metadatech frontier podle kontraktu [T017](../tasks/T-017_filter-topology-scope.md).
Schéma, CLI argumenty a struktura metadata komentářů zůstávají kompatibilní.

## T021-S04 / T021-AC04 a AC05 — regrese a zachování frontier

[Test](../../tests/test_t021_render_topology_mermaid.py) samostatně ověřuje
scope a kontext pro proof citovaný uzlem nebo hranou, neměnnost vstupu
při chybě, `unknown` a chybějící hodnoty. Skutečný filtr T017 ověřuje
zachovaný `CONTEXT_FILTER` frontier s dokladem, jejž žádný viditelný prvek
necituje. Test porovnává původní a serializované důkazy bez změny obsahu.

- RED — `python -m pytest -p no:cacheprovider -q --tb=short tests/test_t021_render_topology_mermaid.py -k 'visible_provenance or omitted_frontier'`
  na předchozím rendereru. 8 očekávaných FAIL a 2 PASS, 18 deselected.
- První běh stejné pětice souborů bez markdown-it měl 141 PASS a 1 SKIP
  na úrovni celého modulu T020. Kontrola `--collect-only` potvrdila 0
  vybraných případů T020 bez parseru a 50 s nainstalovaným parserem.
- PASS — `KGMAKER_REQUIRE_MARKDOWN_PARSER=1 PYTHONPATH=src python -m pytest -p no:cacheprovider -q --tb=short --basetemp .kgmaker/workflow/scoped-provenance-pytest tests/test_t021_render_topology_mermaid.py tests/test_t017_filter_topology_scope.py tests/test_t016_aggregate_service_topology.py tests/test_t019_add_architecture_json_cli.py tests/test_t020_render_interface_markdown.py`.
  191 PASS, 0 SKIP za 7.40 s s markdown-it-py 3.0.0, Node 22.22.1, Mermaid 11.4.1
  a jsdom 26.0.0 včetně reálného parse/render a ověření původního CLI artefaktu.
- PASS — `kgmaker semantic update --base HEAD --note docs/changes/138_rejectForeignTopologyEvidence.md`,
  `kgmaker semantic apply`, `kgmaker semantic validate`,
  `kgmaker memory capture --base HEAD --validation t021-provenance-scoped=passed --validation t021-semantic=passed`
  a `kgmaker scan`, `kgmaker status`, `kgmaker check` v izolovaném checkoutu.
  Předchozí 187 vztahů včetně dvou vazeb T021 a historické epizody jsou zachované.
- PASS — `git diff --cached --check`.
- NOT_RUN — úplná projektová sada nad touto revizí, GitHub Actions a aktuální
  exact-pair T045 re-review. Draft zůstává nedokončený.

## T021-S05 / T021-AC06 — synchronizace dokumentace

Rozsah přímých důkazů a omitted frontier doplněn v [README](../../README.md),
[architektuře](../architecture.md), [CLI kontraktu](../architecture-json-cli.md),
[topologii](../service-topology.md), [acceptance inventáři](../acceptance-inventory.md)
a [stavové matici](../production-analysis-progress.md). Dokumentovaný CLI
příkaz a formát výstupu zůstávají kompatibilní. Registr a instalované
instrukce nemají změnu, protože jde o opravu už registrovaného T021-AC05.

## Přenos na main po #127 a #128

Výchozí GitHub main `17e9e7368e6cc2d6550983c3039eb39debd65424`, tree
`dfb0a247ec329196190a3db182b5d1e8c549b3db`. Dva zdrojové a dva testovací
bloby jsou shodné s ověřeným headem [#123](https://github.com/p-rum/kgmaker/pull/123)
`3446a3153a6fd3df168e8b50e996635363bb32b8`. GitHub Compare potvrdil jako předky
T017 `4e4fcd65e94b855ac4aee2e76fa4a25084940da7`, T019
`a60f02d2a36f0d826ea340541966028d818efd5d` a W09
`cceb1109df6d88e4f46107f9f9ad12f5e563c0d3`.

- **T021-S01 / AC01, AC05.** `architecture_render.py` zachovává model uzlů a hran,
  scope a kontext u zobrazených tvrzení i přímo citovaných důkazů. Testy
  `test_t021_golden_projects_exact_http_kafka_and_db_model_without_fake_vertices`,
  `test_t021_rejects_foreign_scope_in_visible_provenance` a
  `test_t021_preserves_provenance_only_referenced_by_omitted_frontier` ověřily
  počet prvků, odmítnutí cizího důkazu a zachování omitted frontier.
- **T021-S02 / AC02, AC03.** `test_t021_hashes_logical_identity_with_realm_and_keeps_provenance`
  ověřuje různé hashe pro stejnou logickou identitu ve dvou realmech.
  `test_t021_real_mermaid_114_parser_and_renderer_accepts_malicious_labels` a
  `test_t021_real_t016_http_kafka_topology_parses_and_renders` používají skutečný
  Mermaid parser i renderer přes `tests/rendering/validate_t021_topology.mjs`.
- **T021-S03 / AC05.** Golden test ověřuje text `ASYNC; delivery UNKNOWN`,
  `PARTIAL`, truncation a celý serializovaný provenance envelope. Jde o výstup
  ze statického modelu, runtime a dostupnost dat zůstávají nedoložené.
- **T021-S04 / AC04.** `architecture_cli.py` volí formát nad filtrovaným výsledkem.
  `test_t021_cli_render_failure_preserves_last_valid_artifact_and_skips_publish`,
  `test_t021_invalid_inputs_are_read_only_and_rejected` a
  `test_t021_pure_renderer_never_starts_process_or_network` ověřují zachování
  artefaktu, nulovou mutaci hodnoty a absenci procesů a sítě v rendereru.
- **T021-S05 / AC06.** Aktualizovány [README](../../README.md),
  [CLI a API příklady](../architecture-json-cli.md#architecture-topology-mermaid-t021),
  [architektura](../architecture.md), [topologie](../service-topology.md),
  [stavová matice](../production-analysis-progress.md) a
  [acceptance](../acceptance-inventory.md#t021--topology-mermaid-pr-123).
  Původní [change132](132_renderTopologyMermaid.md) zachovává historické kroky.
  Registr a init šablony nemění dříve evidované zadání ani instalační chování.
  JSON zůstává výchozí. Schéma není rozšířené a test ověřil čtení grafů v1/v2/v3.
  Výstup Mermaid vzniká na stdout a zápis cache je výslovný přes `--view-cache`.

Cílená sada **194 PASS / 0 SKIP**, 6,85 s, Node 22.22.1, Mermaid 11.4.1,
jsdom 26.0.0 a markdown-it-py 3.0.0:

```sh
KGMAKER_REQUIRE_MARKDOWN_PARSER=1 PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest \
  -p no:cacheprovider -q --tb=short -r fEs --basetemp .kgmaker/workflow/scoped-t021-pytest \
  tests/test_t021_render_topology_mermaid.py tests/test_t017_filter_topology_scope.py \
  tests/test_t016_aggregate_service_topology.py tests/test_t019_add_architecture_json_cli.py \
  tests/test_t020_render_interface_markdown.py \
  tests/test_t005_add_view_model.py::test_existing_graph_loader_still_accepts_legacy_schema_versions
```

Úplná sada nad tímto kandidátem, GitHub Actions a nové T045 review mají pro
přenos stav NOT_RUN. T022 a produkční runtime acceptance mají vlastní rozsahy.
