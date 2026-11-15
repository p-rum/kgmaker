# Architecture JSON CLI (T019 source checkpoint)

Delivery status (2026-11-07): T019 is MERGED in [PR84](https://github.com/p-rum/kgmaker/pull/84) (`a60f02d`).
Current full acceptance is NOT_RUN in this documentation audit. Historical
checkpoint results and pre-merge review gates below describe their stated SHA.
Use the [current delivery inventory](production-analysis-progress.md) and
[change111](changes/111_reconcileDeliveryStatus.md) for present status.

Default commands replay explicit captured JSON. They do not read a live workspace,
run workers, build indexes, publish caches, or execute applications. The topology
command may explicitly read or publish one derived-view cache artifact with
`--view-cache PATH`; without that option the command stays cache-free. This flag
does not capture a new workspace or graph and is not a worker/build instruction.
Publication occurs only for exit 0, after filter, expected fingerprint, output safety,
size and stdout write/flush checks. Invalid format/filter/fingerprint, cancellation,
strict exit 4 or an output failure leaves the previous cache and inputs unchanged.
The target must be a dedicated cache path: input/selector/manifest/cancel-file aliases,
symlinks (including parents), hardlinks and non-regular targets are rejected. For
local capture, destinations inside a source repository are limited to `.kgmaker/views/`.
A failed final atomic cache write returns 2 and preserves previous bytes/removes
new empty cache directories; stdout may already contain the valid view. Consumers
must check the exit status; stdout and cache are not one atomic export transaction.
Python callers may use the same [derived-view cache API](view-cache.md). See
[T037 implementation evidence](changes/121_invalidateDerivedViews.md).

```sh
kgmaker architecture interfaces --root /repo --catalog http-providers --interface-capture interfaces.json
kgmaker architecture topology --root /repo --capture-snapshot topology-inputs.json --max-nodes 50
kgmaker architecture topology --root /repo --capture-snapshot topology-inputs.json --max-nodes 50 --format mermaid
kgmaker architecture explain --root /repo --snapshot filtered.json --capture-snapshot topology-inputs.json --element service:checkout
kgmaker architecture topology --root /repo --capture-snapshot topology-inputs.json --view-cache .kgmaker/views/topology.json
# Rejected context returns 2 and leaves the capture and last valid cache unchanged:
kgmaker architecture topology --root /repo --capture-snapshot topology-inputs.json --view-cache .kgmaker/views/topology.json --filter-contexts ctx-that-does-not-exist
```

Interfaces input is a versioned transport bundle with exactly `schema_version: 1`,
`rules_version: "architecture-interface-inputs-1"`, `workspace` (public normalized
manifest), `graph` (original public graph), and `captured` (W07 handoff). The output
is the exact requested canonical catalog ViewDocument, preserving IDs and evidence.
Topology input is the T016 capture handoff; output preserves the complete T017
`document` plus `filtering` envelope, including omissions/frontier. Explain accepts
the original T016 view or that full envelope and preserves the original T018 handoff.
Optional `--graph-snapshot` supplies the exact original graph, never a newer repair.

`--context-selection` reads `{schema_version:1, contexts:[{service_id,repo_id,module,
context_id}]}`. In replay it asserts captured pins; `--scope` likewise asserts scope.
Neither option reselects or rewrites a snapshot. `--expected-fingerprint` asserts its
existing view fingerprint; mismatch returns 3 without output or repair.

Explicit `--capture-local --workspace workspace.json` is available for interfaces
and topology. Every declared repository must already have a valid original
`.kgmaker/graph.json` BEFORE parser/capture work begins. Missing/corrupt originals
return fixed actionable errors; capture never creates them. Capture reads local
sources/parsers, uses existing bounded APIs and disables workspace/index cache publication.
Only topology with `--view-cache` may separately publish its derived-view cache. This
is source replay, not a compiler, application, deployment or runtime proof.

Explain's separate `--check-source --workspace workspace.json --graph-snapshot graph.json`
observes confined original source hashes through T018. Default pure explanation is
NOT_CHECKED. A supplied `--source-status` replays that explicit sidecar rather than
checking files now. Neither changes original view fingerprints or context freshness.

Successful default stdout is one JSON document. T020 adds interfaces-only
`--format markdown` over that same validated catalog. T021 adds topology-only
`--format mermaid` over the same validated T017 envelope; JSON remains the default.
Neither format performs another capture. The [interface Markdown contract](interface-markdown.md)
and [topology Mermaid contract](#architecture-topology-mermaid-t021) preserve the
same evidence and exit semantics. Explain remains JSON-only. Diagnostics use fixed JSON on stderr and
never echo raw argument values. Exits: 0 valid (including partial), 4 valid partial
with `--strict`, 2 invalid input/original index, 3 typed baseline/capture conflict,
130 cancellation, 141 broken pipe, 1 controlled unexpected internal error.
`--cancel-file` checks an explicit cancellation marker before/after computation.
Inputs/output are bounded; unsafe output fails without partial stdout or ID rewriting.
Legacy `graph view`, `flow render`, and global version behavior remain available.

## Architecture topology Mermaid (T021)

`--format mermaid` renders the existing topology result after T017 filtering. It
does not call capture, filter again, reopen source files, or write an artifact. The
diagram node IDs are SHA-256 hashes of the model logical ID; where a node supplies
`attributes.logical_id`, the identity also includes its realm facets, scope, selected
contexts and owner. This keeps equal display/logical names in separate realms distinct.
Each edge uses the corresponding hashed endpoint IDs; model edge IDs and complete
edge/node/provenance records remain in escaped JSON Mermaid comments.

Each rendered entity includes its model kind, label, resolution, freshness and
evidence kinds. Relations have distinct text labels (HTTP request/response, Kafka
publish/consume, resource reads/writes); unknown relations remain explicitly
`UNKNOWN`. Async relations include `ASYNC; delivery UNKNOWN`. The title reports the
captured scope, evidence kinds, coverage and truncation and states that runtime/data
availability and ordering/delivery are not observed. Filtering omissions and the
entire provenance/context envelope remain in the comments. No synthetic legend or
truncation nodes, click directives, raw HTML or external resource references are emitted.

```sh
kgmaker architecture topology --root /repo --capture-snapshot topology-inputs.json --format mermaid
```

The pure `kgmaker.architecture_render.render_topology_mermaid(document_or_t017_result)`
API accepts a topology `ViewDocument`, its serialized document, or the T017 filter
result. It does not spawn processes, use the network, mutate input, or publish files.
T021 parser/render coverage is in `tests/test_t021_render_topology_mermaid.py` and
`tests/rendering/validate_t021_topology.mjs`. Current delivery and test results are
recorded in [change132](changes/132_renderTopologyMermaid.md).

## Historical validation checkpoint

Current1005b9f includes merged T014/T016/T017/T018/Common/T012/T013/W07/process
dependencies and exact CI. Owned architecture_cli, five CLI registration/dispatch
lines and34tests are exactabad/accepted2df. Current2597-case union equals the whole
acceptedfull set (2587PASS10allowedSKIP there); all302present runtime/test/fixture/
workflow files match that descendant, with no CLI exception remaining. This is
source/per-ID transfer, not a new full on this head. Independent current-pair
review remains a gate. T020/21formats are NOT in this JSON-only implementation
or acceptedfull. See [note99](changes/99_addArchitectureJsonCli.md).
