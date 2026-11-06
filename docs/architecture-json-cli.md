# Architecture JSON CLI (T019 source checkpoint)

Default commands replay explicit captured JSON. They do not read a live workspace,
run workers, build indexes, publish caches, or execute applications.

```sh
kgmaker architecture interfaces --root /repo --catalog http-providers --interface-capture interfaces.json
kgmaker architecture topology --root /repo --capture-snapshot topology-inputs.json --max-nodes 50
kgmaker architecture explain --root /repo --snapshot filtered.json --capture-snapshot topology-inputs.json --element service:checkout
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
sources/parsers, uses existing bounded APIs and disables cache publication. This
is source replay, not a compiler, application, deployment or runtime proof.

Explain's separate `--check-source --workspace workspace.json --graph-snapshot graph.json`
observes confined original source hashes through T018. Default pure explanation is
NOT_CHECKED. A supplied `--source-status` replays that explicit sidecar rather than
checking files now. Neither changes original view fingerprints or context freshness.

Successful default stdout is one JSON document. T020 adds interfaces-only
`--format markdown` over that same validated catalog; JSON stays the default, and
[the Markdown contract](interface-markdown.md) preserves the same evidence/exit
semantics without another capture. Topology/explain remain JSON-only. Diagnostics use fixed JSON on stderr and
never echo raw argument values. Exits: 0 valid (including partial), 4 valid partial
with `--strict`, 2 invalid input/original index, 3 typed baseline/capture conflict,
130 cancellation, 141 broken pipe, 1 controlled unexpected internal error.
`--cancel-file` checks an explicit cancellation marker before/after computation.
Inputs/output are bounded; unsafe output fails without partial stdout or ID rewriting.
Legacy `graph view`, `flow render`, and global version behavior remain available.

Current1005b9f includes merged T014/T016/T017/T018/Common/T012/T013/W07/process
dependencies and exact CI. Owned architecture_cli, five CLI registration/dispatch
lines and34tests are exactabad/accepted2df. Current2597-case union equals the whole
acceptedfull set (2587PASS10allowedSKIP there); all302present runtime/test/fixture/
workflow files match that descendant, with no CLI exception remaining. This is
source/per-ID transfer, not a new full on this head. Independent current-pair
review remains a gate. T020/21formats are NOT in this JSON-only implementation
or acceptedfull. See [note99](changes/99_addArchitectureJsonCli.md).
