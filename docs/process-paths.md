# Local technical process paths (T025)

`kgmaker.process_paths.build_local_process` adapts a selected T024 trigger and
existing compiler SOURCE CFGs into the T023 `ProcessView`. It reuses
`flow.process`, including original branch/call/return/exception topology. It does
not build another CFG, guess a business process from a method name, execute a
workflow, or infer business equivalence or runtime/data availability.

```python
from pathlib import Path
from kgmaker.workspace import load_workspace, snapshot_workspace
from kgmaker.process_triggers import discover_process_triggers
from kgmaker.process_paths import build_local_process

manifest = Path("workspace.json")
workspace = load_workspace(manifest)
_, coverage, _, graph, _ = snapshot_workspace(manifest)
triggers = discover_process_triggers(workspace, graph, source_coverage=coverage)
# The caller explicitly selects an existing trigger and process identity.
trigger_id = triggers.nodes[0].id
process = build_local_process(graph, triggers, trigger_id,
    process_id="process:caller-selected", revision=1, max_depth=3, max_nodes=200)
print(process.technical_status, process.definition.trigger_ids)
print([(edge.source, edge.target, edge.relation) for edge in process.transitions])
```

Selection must handle an empty trigger inventory explicitly. This is Python API
only; no new CLI/render/export/apply command is supplied. Existing `flow process`
continues using its report schema and now bounds oversized root CFGs as well as
callee expansion. An oversized root becomes one explicit node-limit boundary;
it is not copied in full or converted into a misleading linear prefix.

## Input and evidence boundaries

Pass the matching T024 inventory and provider graph. The function validates the
selected trigger's exact identity, canonical method/endpoint, selected current
context, scope, source hash and original declaration edge/proof tuple. Existing
source-CFG witnesses must bind that same canonical method/context/snapshot.
Caller-to-site `declares_call` and site-to-declaration `resolves_to` edges and
proofs must agree with the original call-site/context/source/range. Mutation of
an unrelated target, scope or proof cannot borrow a different method's body.

The adapter is pure and validates supplied content relationships. It does not
read, refresh, attest or authenticate a physical checkout; callers remain
responsible for obtaining current compiler/provider snapshots before projection.
The normal workspace/trigger workflow performs its own freshness checks. No
unsupported proof is promoted merely because a document declares CURRENT.

SOURCE CFG retains its original SYNTAX_CANDIDATE (or explicitly supplied symbol)
evidence kind and polarity. Static topology never means observed execution.
The trigger-to-body association is explicitly UNKNOWN; the returned technical
status is PARTIAL. Semantic annotations are empty and their review state remains
PROPOSED. Original symbols, CFG block/edge origins and call-site IDs are retained.

## Supported scope and limits

Actual Javac and K1 fixtures cover a diamond with separate left/right methods,
nested private-static/top-level calls, returns, exceptional exits, recursion or
uncertain-dispatch boundaries and root-budget overflow. Opposite if branches
never become a left-to-right execution path. Source CFG is reused, not rebuilt.

Missing or unsupported entry bodies retain the trigger plus an opaque entry
boundary. At `max_nodes=1` the trigger itself holds the node-limit boundary;
otherwise one slot is reserved for the trigger and the remaining budget bounds
the adapted CFG. Child depth/node limits, recursion and ambiguous dispatch retain
original call-site boundaries. No output step list can bypass the requested
budget. Branch condition labels, exception exits and loop metadata survive.

Current compiler call-site nodes carry canonical invocation kind, but do not
independently mirror receiver/complete-dispatch witnesses. Virtual/interface
sites without that independent proof remain boundaries even if the mutable site
table claims complete dispatch. Supported private-static/top-level calls still
expand. Async annotation hints or suspend calls remain unsupported boundaries;
no scheduling, global async order or coroutine execution is inferred. K2's
unavailable annotation/CFG trigger input remains UNKNOWN upstream.

Invalid input raises structured `ProcessPathError.diagnostic` without mutating
inputs or writing a source/store artifact. Legacy graph v1/v2/v3 decoding is
unchanged; a legacy graph without compiler witnesses cannot acquire a stronger
process claim. No schema/store migration is required. T026+ grouping, cross-service
projection, business labels, catalog, CLI and rendering remain separate tasks.
