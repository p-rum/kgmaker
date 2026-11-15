# Unified flow views

T003-S07-W09 renders JSON, Markdown and Mermaid from the same existing CFG/process
report (`schema_version: 1`, additive `flow_model_version: flow-view-1`). Entity,
CFG and process occurrence IDs remain unchanged. All formats retain the same
nodes, edges, source origins, evidence references, coverage gaps and truncation.
See [implementation and verification](changes/128_unifiedFlowViews.md).

After explicit inspection, select an existing method ID and context:

```sh
kgmaker flow render --root project --entry METHOD_ID --context CONTEXT_ID --view process --format json
kgmaker flow render --root project --entry METHOD_ID --context CONTEXT_ID --view process --format mermaid
kgmaker flow render --root project --entry METHOD_ID --context CONTEXT_ID --view process --format markdown --output .kgmaker/flows/process.md --timeout 30
```

`control-flow` is the default view and Mermaid the default format. `integrations`
and `data-flow` also support all three formats, preserving their previous JSON
nodes/edges and supplemental binding/integration records. Their ordering is
`RELATIONSHIP_ONLY`, which supplies no executable CFG evidence.

`ordering.display_order` is deterministic adjacency traversal for presentation.
`CFG_PARTIAL_ORDER` means edges retain their syntax: branch alternatives are not
consecutive actions, loop-back edges remain cycles, and async boundaries do not
establish global scheduling or completion order. JSON arrays and diagram source
use that same display order. Mermaid safe hashed visual IDs map to original IDs
in structured comments; comments also carry complete node/edge provenance and
report metadata. Markdown embeds the identical diagram.

Source CFG remains syntax evidence. Interprocedural expansion additionally needs
current compiler inspection authority, executable call-site kind, exact current
caller/site/target witnesses and current source-body proofs of both the caller
and callee CFG. Every root or nested expansion checks that the call-site belongs
to that exact CFG method/context/scope and matches the block's path, checksum and
source range inside the captured body. Foreign, missing or stale caller proof
retains the original local structure and explicit boundary without call/return
expansion. Static argument/return binding details whose source occurrence still
matches may remain as `binding_projection: REFERENCE_ONLY`, with original proof
freshness, `NOT_OBSERVED` execution and coverage gaps; these are not execution
witnesses. The shared W08 admission rules apply; SOURCE_ONLY, stale proofs, type/test/config references and
runtime samples do not manufacture a static call path. Incomplete dispatch,
recursive calls, unsupported bodies and async/proxy boundaries stay explicit.
Execution is `NOT_OBSERVED` and availability `UNKNOWN` throughout.

Missing supported CFG yields an `UNKNOWN` report with `CFG_UNAVAILABLE`. Invalid
IDs/references or malformed snapshots fail before rendering; they are not empty
successful reports. Graph/store v1/v2/v3 remain readable. V1 lacks source scope
classification; use `--scope all` to inspect its unknown legacy entities. The
previous missing-CFG error is now a report; `--strict` returns 4 for either PARTIAL
or UNKNOWN in every format. Invalid input returns 2; stale provider input returns
3. Existing context ambiguity still requires explicit selection.

`--max-nodes` includes visible boundary nodes. Omitted control-flow endpoints retain
original IDs; a budget too small for a truthful prefix produces an opaque root.
`--max-depth` bounds process expansion. Neither limit rewires branches to invented
steps. Missing compiler/CFG support remains a gap rather than a guessed sequence.

`--output` atomically publishes a single report under `.kgmaker/flows/` in the
selected root. Absolute paths inside that directory are accepted. Source/store
paths, symlinks, hardlinks and input/cancel aliases are rejected. Stdout remains
the default. `--timeout` is a positive finite cooperative local deadline;
`--cancel-file` is checked before processing and immediately before replacement.
On invalid input, timeout, cancellation or interruption the last valid file is
preserved, temporary files are removed, and only empty directories created by
that attempt are cleaned. Pre-existing directories and concurrent contents remain.
Before replacement, publication rechecks the exact loaded index bytes, the
scanner's bounded source inventory, raw source bytes, classification inputs and
existing compiler snapshot bindings. This also protects SOURCE_ONLY/legacy
reports: changed/new readable sources cannot be adopted by an older index.
Indexed XLS/XLSX inputs retain their producer's streaming raw checksum; workbook
add/change/delete is detected using the producer's unchanged discovery scope,
without parsing workbooks during rendering. Workbooks absent from the index are
only inventoried for change detection and gain no flow evidence. A stale snapshot
returns exit 3 and preserves the last valid output. This check does not lock out
independent writers after the final validation.
Valid PARTIAL/UNKNOWN reports may be published, including with strict exit 4.
Rendering never starts a compiler, build, model, network request or application.

The bounded native acceptance uses Javac/JDK21 with if/else, a loop, a static callee
and unresolved code. Model golden coverage separately exercises branch/async/loop
and limit/provenance behavior; Mermaid11.4.1 is actually parsed and its vertices,
edges, order and structured metadata compared with JSON. Existing K1/K2/TS binding
regressions are not a new general native CFG support claim. Whole T003-S07 and
runtime scheduling remain outside this work package.

Merged BEFE compatibility uses the existing dataflow FORWARD/REVERSE relation
sets without reversing stored edges. An actual single-context frontend capture
retains its HTTP-response→state→JSX path in all formats. Selecting that context
does not import a second compiler variant or a mixed-context backend bridge;
such omitted claims remain explicit context-boundary gaps.
