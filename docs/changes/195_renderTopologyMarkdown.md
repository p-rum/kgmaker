# Change 195 — Markdown report topologie

[T022](../tasks/T-022_render-topology-markdown.md), revize 1. Výchozí `main`
`8290606eace7d7c94497cca143fa8e70c0042d38`. Ověření před implementací našlo
funkční JSON a Mermaid, ale veřejný příkaz s Markdownem vracel `INVALID_ARGUMENTS`
(exit 2). Podklady T018 jsou sloučené v #83 (`1005b9f950102d2d5fd0e74735bc0577c2e30c0b`),
T021 v #123 (`61a554174b1c23257878fffae0e125f146223d79`). Obě revize jsou předky výchozího `main`.

## T022-S01 — Obsah reportu (AC01, AC02, AC05)

`src/kgmaker/architecture_render.py` sestaví Markdown s diagramem, inventářem
služeb, vazbami a důkazy z dodaného dokumentu. Zobrazuje zachycená ID, vztahy,
druh a čerstvost důkazu i původní reference. První tříformátový test na výchozím
kódu skončil `FAIL` (1 test, exit 1, JUnit SHA-256
`21240ecb7d574551db7d400211b1d256306e781fa30fa62e17b9ef65e70dec48`).
`test_public_topology_three_formats_share_model_and_ids` na kandidátovi prošel.

## T022-S02 — Společný model a kompatibilita (AC01, AC03)

`src/kgmaker/architecture_cli.py` předá Markdownu stejný filtrovaný výsledek T017
jako JSON a Mermaid. Oba renderery používají dosavadní validaci a generování
diagramu. Vložený diagram má stejné bytes jako samostatný výstup Mermaid.
Před a po změně souhlasí všech 13 porovnávaných výstupů JSON a Mermaid pro
HTTP, Kafka, běžné a striktní čtení, limit uzlů a původní golden Mermaid
(manifest SHA-256 `ddbe1513000b790f976cf82826bfda51a3a53735e6ae87476f57c7fc13bc2784`).
Migrace není potřeba. Výchozí formát JSON, stávající API i grafy v1/v2/v3 zůstávají
podporované. `test_report_is_pure_deterministic_and_abstains_on_missing_source`
potvrdil determinismus, shodu vstupu a zákaz I/O během renderu.

## T022-S03 — Scope, hranice a dostupnost zdrojů (AC02, AC04, AC05)

Report zachová vybrané kontexty, nevyřešené prvky, známé vynechané hranice i
neúplnost inventáře při upstream truncation. Cizí scope nebo kontext viditelného
prvku či jeho důkazu zůstává důvodem k odmítnutí. Zachycené zdrojové reference
jsou k dispozici v provenance. Protože topologický podklad T016 nemá svázaný
zdrojový lokátor T018, report uvádí `SOURCE_LOCATOR_UNAVAILABLE` a `NOT_CHECKED`.
`test_public_partial_topology_exposes_all_frontiers_and_preserves_cache` potvrdil
viditelná ID všech známých hranic i striktní exit 4. Testy cizího důkazu,
otisku a skutečné chyby limitu renderu potvrdily odmítnutí, zachování vstupu
a posledního uloženého artefaktu.

## T022-S04 — Provedené kontroly (AC01–AC05)

```sh
KGMAKER_REQUIRE_MARKDOWN_PARSER=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider \
  tests/test_t022_render_topology_markdown.py \
  tests/test_t019_add_architecture_json_cli.py \
  tests/test_t020_render_interface_markdown.py \
  tests/test_t021_render_topology_mermaid.py \
  tests/test_t037_invalidate_derived_views.py \
  tests/test_t017_filter_topology_scope.py \
  tests/test_t005_add_view_model.py::test_existing_graph_loader_still_accepts_legacy_schema_versions
```

**235 PASS / 0 SKIP / 0 FAIL, exit 0**, z toho 12 T022. JUnit SHA-256
`fb1249d777124b2fccbb0fdab671cb3ee4a109cd4c1881fcd23026b180b479c2`.
`test_markdown_parser_keeps_exact_embedded_diagram_and_escapes_captured_labels`
použil Markdown-it 3.0.0 a Mermaid 11.4.1 s jsdom 26.0.0 na Node v24.22.3.
Ověřen byl vložený diagram i původní T021 s HTTP a Kafka. Omezení CLI `explain`
na JSON dále ověřuje `test_explain_remains_json_only_and_preserves_last_artifact`.

## T022-S05 — Příklad a stav dodání (AC06)

```sh
kgmaker architecture topology --capture-snapshot topology-inputs.json --max-nodes 50 --format markdown
```

Aktualizované jsou README, [CLI](../architecture-json-cli.md#architecture-topology-markdown-t022),
[architektura](../architecture.md), [topologie](../service-topology.md#markdown-report-t022),
[stav](../production-analysis-progress.md) a [acceptance](../acceptance-inventory.md).
Úplná sada a nezávislé posudky jsou `NOT_RUN`, samostatné PR a jeho integrace
čekají na aktuální ověření a schválení. Jde o statický report nad existujícím
podkladem. Běh cílové aplikace ani dostupnost dat tento výstup nedokládá.
