# T021 — Mermaid schéma služeb

## Stav

Task `T021`, Revision 1. Implementation base `83999fb2e08c6d9d67449687c95b2217eee08b09`; current PR base `84f94d4462437fe1228f07d0ba8f51071224952e`.
Delivery `PR_OPEN` ([#113](https://github.com/p-rum/kgmaker/pull/113)); verification
`PARTIAL` pending independent review and any requested fixes. The branch is pushed and remote parity was verified when opening the PR; the active head is shown on the PR. T017 merge `64e56d0efaa20830e7ecc3dbd86779a5a05c84f3`, T019 merge
`0dcbf4a0fb23cc5d860f93aeee8da9b86bab4e40` and W09 merge `cceb1109` are verified
ancestors of the implementation base; report/T029 main integrations are recorded below.

## Problém a hranice

T019 exposed the filtered T017 topology only as JSON. This change adds a pure Mermaid
projection and `architecture topology --format mermaid`. It uses the captured model
as supplied: it does not capture, refilter, add runtime/data availability, start a
process, access the network, or publish a file. T022 topology Markdown and other T004
items remain outside this change.

## Kroky a evidence

### T021-S01 — service/resource/channel and relationship rendering

- Base: `83999fb2e08c6d9d67449687c95b2217eee08b09`.
- Changes: `src/kgmaker/architecture_render.py`; golden source in
  `tests/test_t021_render_topology_mermaid.py`.
- Rendered model node kinds carry distinct textual prefixes. HTTP request/response,
  Kafka publish/consume and resource read/write relations have distinct labels.
  Title states captured scope, evidence kinds, coverage and truncation. No synthetic
  legend/truncation entity is added.
- Compatibility: consumes schema-v1 topology views and the exact T017
  `schema_version=1`, `rules_version=topology-filter-1` envelope; JSON remains default.
- AC: T021-AC01, AC05 — `test_t021_golden_projects_exact_http_kafka_and_db_model_without_fake_vertices`
  PASS; actual parser endpoint/node bijection PASS.
- Remaining limitation: renderer supports existing `ViewDocument` topology v1 and
  T017 filter v1 envelope. It does not create or revise model schemas.

### T021-S02 — hashed identities and safe Mermaid text

- Base: `83999fb2e08c6d9d67449687c95b2217eee08b09`.
- Changes: `src/kgmaker/architecture_render.py`,
  `tests/test_t021_render_topology_mermaid.py`,
  `tests/rendering/validate_t021_topology.mjs`.
- Node IDs hash captured logical identity; explicit `logical_id` includes realm,
  scope, selected contexts and owner. Edge endpoints reference those hashed nodes.
  Mermaid labels encode quote/entity/directive metacharacters; metadata comments are
  compact JSON with HTML and Mermaid directive delimiters escaped. No links, click
  actions, raw markup or external imports are emitted.
- AC: T021-AC02, AC03 — realm-separated same-name hash test PASS; actual Mermaid
  parser and jsdom renderer hostile-label test PASS.
- Toolchain: Node `v24.22.1`, Mermaid `11.4.1`, jsdom `26.0.0`. Dependencies were
  reused read-only via a symlink from the existing workspace; no install was run.

### T021-S03 — explicit uncertainty and async semantics

- Base: `83999fb2e08c6d9d67449687c95b2217eee08b09`.
- Changes: `src/kgmaker/architecture_render.py` and golden coverage in
  `tests/test_t021_render_topology_mermaid.py`.
- `UNKNOWN` relations and unresolved execution remain textual. Kafka publish/consume
  edges say `ASYNC; delivery UNKNOWN`; diagram title says runtime/data availability is
  `UNKNOWN` and ordering/delivery are `NOT_OBSERVED`. Scope, context, evidence,
  freshness and filter omission/provenance payload round-trip in safe comments.
- AC: T021-AC01, AC05 — golden relation/status/title assertions and full metadata
  round-trip PASS. Source fixture remains SOURCE_ONLY; no runtime observation is
  inferred.

### T021-S04 — CLI format and failure isolation

- Base: `83999fb2e08c6d9d67449687c95b2217eee08b09`.
- Changes: `src/kgmaker/architecture_cli.py` and
  `tests/test_t021_render_topology_mermaid.py`.
- Added topology-only `--format mermaid` dispatch on the same T019/T017 result.
  Rendering happens before stdout/cache publication; existing explicit `--view-cache`
  behavior remains responsible for cache publication after successful output.
- AC: T021-AC04 — CLI snapshot replay PASS; invalid render yields no stdout, leaves a
  seeded last-valid artifact unchanged and never invokes its publisher. Pure renderer
  forbids subprocess/socket creation and leaves valid/invalid input unchanged.
- CLI/API example and exact options are documented in README and
  `docs/architecture-json-cli.md`.

### T021-S05 — user docs and acceptance status

- Base: `83999fb2e08c6d9d67449687c95b2217eee08b09`.
- Changes: `README.md`, `docs/architecture.md`, `docs/architecture-json-cli.md`,
  `docs/service-topology.md`, `docs/production-analysis-progress.md`,
  `docs/acceptance-inventory.md` and this note.
- Existing T004 task identity and registry remain unchanged. Status is `IN_PROGRESS`
  / `PARTIAL`; `T022` and broader T004 are not marked complete.
- AC: T021-AC06 — documentation and matrix updated. PR URL/review/merge are
  `NOT_RUN` at this checkpoint; implementation agent does not merge.

### T021-S06 — semantic continuity audit

- Base: `83999fb2e08c6d9d67449687c95b2217eee08b09`.
- The initial semantic validation found stale citations because T021 updates the
  cited architecture/CLI/topology documentation and moves two code entry points
  (`kgmaker semantic validate --root .` initially returned `nodes[12] is stale
  because docs/service-topology.md changed`).
  The scoped update identifies 10 existing concepts and 27 existing relationships.
  I verified their claims against current source text and graph IDs; their meanings
  remain supported. The patch will reanchor those existing entries, add no new
  speculative relationship, retain all 50 concepts/170 relationships and preserve
  all 319 immutable implementation episodes byte-for-byte.
- Scoped semantic preflight PASS using fresh source scan: 50 concepts, 170
  relationships, 319 episodes; the canonical episode-array SHA256 remained
  `5bc5882924958941c84b823560c981999e9d7caabd3209a9d65c374b107aaf09` (raw
  canonical JSON SHA256 `fa0cfaf5659c7f49ac96aacff60490dfe597ffc95761a8cee5a162bdcc13f5e2`).
- `kgmaker semantic apply --root .` PASS — 50 concepts / 170 relationships.
- `kgmaker semantic validate --root .` PASS — 369 merged graph concepts / 33,855
  relationships.
- `kgmaker scan --root .` PASS — 618 files, 6,550 declarations/sections, 49,053
  relationships; generated GRAPH.md/GRAPH.mmd via CLI. Semantic artifact remains
  exactly 50 concepts / 170 relationships / 319 episodes with the same episode hash.
- Reanchoring preserved all semantic identities and relationship count; no node or
  relationship removal or speculative addition. At the original baseline checkpoint, `semantic update --base
  83999fb2e08c6d9d67449687c95b2217eee08b09` and the scoped patch/apply/validate/scan
  passed. Subsequent ordinary integrations and final semantic evidence are recorded
  separately in T021-S07 and T021-S09.

## Kontroly

| Příkaz / kontrola | Výsledek |
|---|---|
| `PYTHONPATH=src:/tmp/kgmaker-t021/tests /tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_t021_render_topology_mermaid.py` | PASS — 9 passed, 0 skipped, 1.72 s; includes real T016 HTTP/Kafka diagram parser/SVG checks |
| `PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_t017_filter_topology_scope.py tests/test_t019_add_architecture_json_cli.py tests/test_t020_render_interface_markdown.py tests/test_t021_render_topology_mermaid.py tests/test_t005_add_view_model.py::test_existing_graph_loader_still_accepts_legacy_schema_versions` | PASS — 129 passed, 0 skipped, 5.77 s |
| `PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_t005_add_view_model.py::test_existing_graph_loader_still_accepts_legacy_schema_versions` | PASS — graph schema versions 1, 2 and 3 |
| `node --version` | PASS — v24.22.1 |
| `node -p "require('./tests/rendering/node_modules/mermaid/package.json').version"` | PASS — 11.4.1 |
| `node -p "require('./tests/rendering/node_modules/jsdom/package.json').version"` | PASS — 26.0.0 |
| Mermaid `parse` + actual `render` via `tests/rendering/validate_t021_topology.mjs` | PASS — compared hashed node IDs and edge endpoints for malicious golden (5/4) and actual T016 HTTP (2/1) and Kafka (3/2) outputs; DOM contains no script, image, link or event-handler nodes/attributes |
| `git diff --check` | PASS — clean |
| implementation memory capture | PASS — `episode:45dbd0b78a458f82bfd57b89c6ac607aab4486a576dfc95c910b407048e8a2e7`, base `9c86d29fc267014e2bee4b197c7692f17a1cda93`; 51/173/323 with parent episodes preserved |
| `python3 -m pytest -q` | NOT_RUN — celé pytest se spouští až po dokončení balíčku dle pokynu uživatele |
| GitHub Actions | FAIL / UNCLASSIFIED — PR run `43765496906` has failing `gradle-build-export`, `windows-user-install`, `rendering`, Python 3.11/3.12 and `compiler-workers` jobs; Python 3.13 was cancelled. Connector returned empty step lists and `BlobNotFound` for job logs, so no code-vs-infrastructure cause could be established. Local targeted acceptance remains PASS; reviewer should inspect/retry the failed run if required. |
| Full W09 producer/compiler and runtime/data tests | NOT_RUN — T021 consumes their merged captured topology contract and adds no producer or runtime behavior |

## Kompatibilita, změna/konflikty a zbývající práce

No serialized schema, graph/store, cache, worker or migration format changed; no
migration is needed. T017 omission/frontier state is retained in the diagram's
escaped metadata comment and is not rendered as a false topology node. The graph
remains a static selected snapshot. Broader production coverage and runtime/data
availability are not established by these renderer/parser fixtures. Remaining work: merge the current T029 main when its exact SHA is provided, repeat focused integration checks, refresh semantic capture/scan and status, commit/push, verify remote diff and then hand to independent review.

### Workflow provenance

The T021 task runtime record is `task:58d9577d5d7598ce17925f8e3a2fcf7ee24f96e1aa1983297d8ba4663eb5f558`. The source/architecture audit and T016/T017/T019 contract verification were performed before code changes. The task runtime's analyze and plan artifacts were recorded after implementation had begun; they document the verified decisions and are not represented as pre-implementation gates. The implementation and targeted-test artifacts contain the actual changed paths and outcomes; independent review is still pending.

### T021-S07 — report-main integration and preservation audit

- Report-main `9c86d29fc267014e2bee4b197c7692f17a1cda93` (tree `a9bc1d2c39b96342bf919e9c5b50e6237b92359a`, parents `83999fb2e08c6d9d67449687c95b2217eee08b09` and `edb5cff914e210b05482f2a84b01259f45efcd6c`) was verified and ordinary-merged. Generated graph files were recreated by `kgmaker scan`.
- Fresh semantic update identified 10 concepts/27 relationships. Citations were source-verified and reanchored with zero removals. All report-main episodes and all base83999 episodes were preserved. A T021 memory episode was captured later against 9c86: `episode:45dbd0b78a458f82bfd57b89c6ac607aab4486a576dfc95c910b407048e8a2e7`.

### T021-S08 — renderer ID contract correction

- The task requires hash-based renderer IDs and distinct identities across realms. This renderer hashes node IDs; Mermaid output does not assign a separate model-edge ID. Original edge IDs remain in escaped metadata comments, while parsed edge endpoints and relation labels preserve the model.
- Removed an unused edge-hash map and corrected the docstring and README. Emitted diagram syntax is unchanged. AC01/02 are verified by actual parser comparison of node IDs and edge endpoints.

### T021-S09 — current T029 main integration

- Main merge `84f94d4462437fe1228f07d0ba8f51071224952e` (tree `623cae88df34b54c456177b0a8afe8e2a76280c6`, parents `9c86d29fc267014e2bee4b197c7692f17a1cda93` and `e95ebf6ed04ca0f6041f04c2c8d1f93cb4ae7e83`) was verified and ordinary-merged into this branch; no history rewrite.
- Semantic resolution starts with main's 52 concepts/176 relationships/328 episodes and adds only the captured T021 episode. Final state is 52/176/329; every episode from current main plus the T021 episode is present. Final canonical episode-array SHA256: `c80ff5996b687236ffe11d7f6352d7dfe466f54d60674e1fbd1089b303078541`.
- `kgmaker semantic apply` PASS (52/176, no removals); `kgmaker semantic validate` PASS (381 merged concepts/35,639 relationships); CLI-generated scan PASS (626 files, 6,672 declarations/sections, 51,156 relationships). `git diff --exit-code 84f94d4462437fe1228f07d0ba8f51071224952e -- src/kgmaker/business_process.py tests/test_t029_project_process_failures.py tests/test_t028_cross_async_process_boundary.py docs/changes/130_projectProcessFailures.md` PASS: T029 source identity is unchanged.
- Post-integration targeted run: combined T017/T019/T020/T021/legacy graph compatibility 129 passed / 0 skipped / 5.69 s; T021-only 9 passed / 0 skipped / 1.70 s. Actual Mermaid 11.4.1 parser and jsdom 26.0.0 renderer ran under Node 24.22.1 for hostile golden and actual T016 HTTP/Kafka topologies. The report source identity test was attempted but SKIP because the prebuilt JVM worker is unavailable; no worker was built.

### Workflow provenance

Task runtime record: `task:58d9577d5d7598ce17925f8e3a2fcf7ee24f96e1aa1983297d8ba4663eb5f558`. Source/architecture reconnaissance and T016/T017/T019 contract verification happened before code changes. Runtime analyze/plan artifacts were recorded after implementation began; they document decisions but are not presented as pre-implementation gates. Implementation/test artifacts contain actual changed paths/outcomes. Independent review remains pending.
