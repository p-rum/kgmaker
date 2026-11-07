# Local technical process paths (T025)

Delivery status (2026-11-07): T025/T026 is MERGED in [PR66](https://github.com/p-rum/kgmaker/pull/66) (`9442114`).
Current full acceptance is NOT_RUN in this documentation audit. Historical
checkpoint results and pre-merge review gates below describe their stated SHA.
Use the [current delivery inventory](production-analysis-progress.md) and
[change111](changes/111_reconcileDeliveryStatus.md) for present status.

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
Finally continuations sharing one lexical call-site receive distinct structural
callee clones; transition `caller_block` and original references preserve each
normal/exception continuation without creating a cross-branch join.

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
process claim. Current supplied SOURCE CFG must match the imported builder VERSION; an older
unsupported body stays opaque until provider reinspection. No schema/store
migration is required. T026+ grouping, cross-service
projection, business labels, catalog, CLI and rendering remain separate tasks.

## Compiler-bound local operations

T025 revision2 (`local-process-path-2-operations`) introduces a separate optional
`java-local-operations-1` proof for named Java methods without source-file compiler
errors. Supported operations are literal evaluation and assignment of a literal
to a compiler-attributed LOCAL_VARIABLE with a primitive or canonical
java.lang.String type. Field/parameter/boxed/array/call/cast/arithmetic assignments,
Kotlin/bytecode/initializer/lambda and legacy bodies are not certified. Literal
evaluation inside an otherwise unsupported assignment does not certify the
assignment itself. No method body or application is executed by this projection.

The producer retains existing Arg and HTTP IR. The materializer validates the
selected source/caller/context/hash, typed IR path and escaped canonical JSON
IR/body digest, then binds each occurrence to its precise CFG block. Finally
clones receive distinct proof IDs. Graph schema3 remains unchanged; optional
worker/body versions absent in old inputs yield no operation proof.

A certified operation node carries only its admitted SYMBOL_RESOLVED operation
proof as resolution evidence. Its original CFG refs remain in
`attributes.cfg_evidence_refs`; transitions include these original syntax refs
and remain UNRESOLVED. Entry/exit, call and boundary nodes are not upgraded.
Workspace wrapping qualifies the new references without rewriting their original
content hash. Missing, stale, foreign, borrowed or tampered operation evidence
cannot authorize a resolved node or mutate the last valid store.

Existing read-only usage is unchanged:

```bash
kgmaker inspect code --root /repo --kotlin-backend k1 --kotlin-version 2.1.10
kgmaker flow render --root /repo --entry METHOD_ID --view process --format json
```

The T025 ProcessView adapter consumes the existing selected trigger inventory and
provider graph; no new implicit inspection or CLI apply path is added. This is an
upstream prerequisite for T026, whose business-step grouping remains a separate
task. Corrected actual focus passed341 tests. A descendant superset full passed1566
tests (10 explicit skips), including all1471 passing parent cases; change79
records exact source hashes, pre/post closure and remaining limitations.

## Reversible business-step projection (T026 candidate)

`kgmaker.business_process.collapse_business_steps(process)` groups maximal
acyclic chains of at least two adjacent certified local-operation basic blocks.
It consumes the explicit T025 `ProcessView`, checks the embedded existing
certificate's content identity and exact method/context/scope/CFG tuple, and
reuses the shared process/view validators. It does not re-attest the physical
checkout or issue new compiler certificates. Missing legacy certificates remain
ungrouped. PR65 (runtime `a6170c18`) is merged as main `32a3bca` and integrated here.

```python
from kgmaker.business_process import collapse_business_steps, expand_business_steps

business = collapse_business_steps(process)
assert expand_business_steps(business).to_json() == process.to_json()
print([(node.id, node.kind) for node in business.steps])
```

Only same-method/owner/context/scope single-entry/single-exit normal adjacency
is eligible. Decisions, calls, side effects, unknown/service/transaction/async
boundaries, cycles and finally continuations stay visible. Equal DTO names,
labels and semantic approvals do not supply eligibility. Annotated and explicit
entry/exit/outcome targets are retained. A group has a neutral `action` label,
versioned `attributes.business_group` records containing ordered complete origin
nodes/internal edges and original external transitions. Its ID hashes those
records. Expansion verifies the supported deterministic projection, including
digest-consistent tampering; all external parallel edges and the unused
exceptional exit survive. Canonical `ProcessView` order is restored exactly;
member order follows CFG adjacency, not lexical sorting of node IDs.

Normal CFG edges still carry UNRESOLVED/SYNTAX_CANDIDATE evidence. Aggregation
preserves all operation and internal-edge evidence, polarity and freshness and
keeps the action UNRESOLVED and the process PARTIAL. This proves static grouping,
not execution, feasibility, business equivalence or semantic approval.

Both APIs are pure, do not execute workers or perform I/O, and leave inputs
unchanged on invalid/stale/foreign/tampered evidence. Invalid input raises
`BusinessProcessError` with `diagnostic`. Bounds reject cyclic/deep metadata,
more than 500,000 structural occurrences, depth above80, text above32 million
characters, collections above50,000, or topology above10,000 nodes/30,000 edges.
Expanded/grouped outputs obey the same structure limits. There is no new CLI,
persistence format migration or runtime observation. Older documents without
group metadata remain readable and expand unchanged.
