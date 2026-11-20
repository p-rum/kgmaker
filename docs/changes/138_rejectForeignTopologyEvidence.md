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
