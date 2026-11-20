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
