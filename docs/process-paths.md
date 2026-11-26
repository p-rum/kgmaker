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

Selection must handle an empty trigger inventory explicitly. The existing
`flow render --view process` uses its CFG report schema and bounds oversized root CFGs as well as
callee expansion. An oversized root becomes one explicit node-limit boundary;
it is not copied in full or converted into a misleading linear prefix.

## Read-only process render (T034)

```bash
kgmaker process render --entry "$ENTRY_ID" --workspace workspace.json \
  --context-selection contexts.json --format json > process.json
kgmaker process render --process "$PROCESS_ID" --process-view process.json \
  --workspace workspace.json --context-selection contexts.json --format json
```

`ENTRY_ID` is an exact `trigger:` ID from the T024 inventory. The rendered
revision is 1, with `process:` followed by that trigger's digest as its local ID.
Take `PROCESS_ID` from the resulting `process_id` field. This ID follows the
selected trigger snapshot and carries no business identity. The caller saves the
JSON. `--process` requires `--process-view`, which supplies a single-trigger T025
document. The same provider rebuilds the supplied ID and revision and checks
the entire canonical content, omitting generation metadata as defined by
`ProcessView`. Other revisions in an external store are outside this check.

`--workspace` is required. `--root` resolves relative input paths and defaults
to the current directory. `--scope` defaults to `production` and also accepts
`test`, `test_fixture`, `development` and `unknown`. Optional `--context-selection`
uses the [architecture selection JSON](architecture-json-cli.md) schema 1 with
`service_id`, `repo_id`, `module`, and `context_id`. Every supplied pin must
match a `CURRENT` row in the selected scope, even for services outside the
rendered path. Use the same selection on replay. Existing original indexes are
required in every workspace checkout.
Local replay reads those files and current sources through the shared provider.
Read-only Git may check checkout identity. Rendering issues no worker, build,
network request or store/cache write. T025 defaults bound the traversal to depth
3 and 500 nodes. Input files and output use the architecture limits of 32 MB
per file and 4 million output characters respectively.

The only format is `json`. Exit 0 returns a canonical `ProcessView` schema 1.
`--strict` returns the same JSON with exit 4 for incomplete coverage. Malformed
inputs or invalid selections return exit 2. Stale canonical content or a mismatch
with `--expected-fingerprint` (64 lowercase hexadecimal characters) returns exit
3. Errors 2 and 3 write a JSON diagnostic to stderr and leave stdout empty.
The T025 result retains its technical status, selected context and provenance.
List, packet generation, validation, apply, review and other formats remain
outside this slice. [Implementation evidence](changes/193_renderLocalProcess.md) ·
[Verified merge and remaining acceptance](changes/196_recordProcessRenderMerge.md).

## Input and evidence boundaries

Pass the matching T024 inventory and provider graph. The function validates the
selected trigger's exact identity, canonical method/endpoint, selected current
context, scope, source hash and original declaration edge/proof tuple. Existing
source-CFG witnesses must bind that same canonical method/context/snapshot.
Caller-to-site `declares_call` and site-to-declaration `resolves_to` edges and
proofs must agree with the original call-site/context/source/range. Mutation of
an unrelated target, scope or proof cannot borrow a different method's body.

The definition and technical view share the selected trigger's current compiler
context. Services bound to that context retain their original matching context
rows and coverage rows without a selected context. The input inventory remains
part of the baseline fingerprint. Other fields of the supplied selection
envelope are preserved for downstream validation. This lets [T030](process-label-packets.md)
prepare a packet for one local trigger in a workspace that has other current
compiler contexts. [T025/T030 regression evidence](changes/190_bindLocalProcessContext.md).

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
content hash. Javac LF and CRLF proofs retain their original byte hash during
T025 replay. Local graphs check the normalized scanner hash alongside it.
Missing, stale, foreign, borrowed or tampered operation evidence
cannot authorize a resolved node or mutate the last valid store.
Scope projection retains malformed optional block metadata for validation. Only
version 1 metadata with a single string reference can contribute an operation
reference to evidence selection, subject to the existing scope and context checks.

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

## Explicit HTTP process boundary (T027)

`kgmaker.business_process.project_http_process_boundary(local_process,
remote_interfaces, target_processes=())` joins a local T025 `ProcessView` to a
remote T014 topology snapshot. It matches the consumer's exact
`origin_call_site` to the local process callsite, then follows only a T014
`remote_http_request_response` binding whose release, contract, service, scope,
and selected context passed the upstream resolver. A supplied target process is
eligible only when its selected service/context and trigger handler match the
bound provider interface.

```python
from kgmaker.business_process import project_http_process_boundary
from kgmaker.remote_interfaces import project_remote_interfaces

remote = project_remote_interfaces(workspace, graph, interfaces,
    captured=remote_capture, scope="production")
cross_service = project_http_process_boundary(
    checkout_process, remote, target_processes=[orders_process])
print([(step.kind, step.attributes.get("target_service_id"))
       for step in cross_service.steps if step.kind == "service_boundary"])
```

The projection is pure and consumes only supplied snapshots. A missing target
process/CFG, unresolved or incompatible binding, ambiguous candidate set,
or context mismatch remains an external boundary; the local continuation remains
in the result. An unmatched callsite leaves the original process unchanged. The boundary records HTTP
request/response and a separate `TRANSPORT_BOUNDARY_ONLY` error meaning. It
does not create a business failure outcome, promote runtime/data availability,
or infer an unrelated handler. Imported target steps preserve their evidence
and receive source-process provenance. The composed view remains `PARTIAL`; no
CLI or persistent format is introduced. See
[T027](tasks/T-027_cross-http-process-boundary.md) and
[change123](changes/123_crossHttpProcessBoundary.md).


Review corrections (see [change123](changes/123_crossHttpProcessBoundary.md)):

- Only the supported T014 `rules_version` is admitted. Expansion requires a
  resolved, non-STALE HTTP binding and provider, `PROVIDED`/`PROVIDER` direction,
  matching endpoint scope/context and a target service/context selection in the
  same scope. T014's normal UNKNOWN freshness is retained; it is not upgraded to
  observed current state. Unsupported versions reject without input mutation;
  stale or incompatible candidates remain external.
- REQUEST originates only at the single matching local call node. T025 annotates
  `call`, `returns_to` and `exception` transitions with the same lexical callsite;
  callee exit nodes are not new request origins. This applies equally to resolved,
  ambiguous and unresolved-selector boundaries.
- RESPONSE edges join only normal target `exit` nodes to explicit normal caller
  continuations (or matching original `returns_to` witnesses). Original local
  exception paths remain unchanged. Target exceptional exits do not establish a
  client error or HTTP response mapping: they stay visible with
  `HTTP_TARGET_ERROR_BOUNDARY` diagnostics. Terminal-only targets have no CFG body.
  Each response retains its original continuation ID and attributes.
- Imported target diagnostics retain their code and carry source process/revision;
  original limits are combined without dropping local/remote limits. Output
  truncation is the OR of local, remote and imported-target truncation. Full remote
  and imported target coverage remains in `coverage.http_upstream_coverage` with
  document fingerprints; local counters are not relabelled as combined counts.

These checks validate supplied snapshots, not a live deployment or arbitrary
replacement JSON authenticity. No transport failure is converted into a proved
business outcome. `ProcessView` and `ViewDocument` schema versions remain unchanged;
new metadata uses their existing extensible attributes/coverage fields.

## Potential asynchronous process paths (T028)

`kgmaker.business_process.project_async_process_boundary(local_process,
remote_interfaces, *, target_processes=(), max_depth=4, max_expansions=32)` consumes
explicit T025 `ProcessView` documents and the current T014 remote topology. It is a
pure API: it performs no capture, I/O, worker invocation, application execution or
artifact publication. A caller supplies already validated snapshots; their
consistency is not authentication or a fresh physical checkout check.

```python
from kgmaker.business_process import project_async_process_boundary

async_process = project_async_process_boundary(
    publisher_process, remote, target_processes=[billing_process, audit_process],
    max_depth=4, max_expansions=32)
subscriptions = [step for step in async_process.steps
                 if step.attributes.get("async_role") == "subscription"]
print([(step.attributes["consumer_group"], step.attributes["boundary_reason"])
       for step in subscriptions])
# Original remote proof IDs remain inspectable, including rejected authority.
print([step.attributes["remote_evidence_refs"] for step in subscriptions])
```

The example uses the same explicit `remote` snapshot creation shown in the T027
example above. T028 adds no CLI command; existing `graph view` and `flow render`
commands retain their contracts. Extended process lifecycle/export CLI belongs to T034/T038.

The projection matches producer `original_ids` to concrete T025 node call-site IDs,
then matches a consumer's original listener symbol to the selected target trigger.
It requires the same service, scope and context, current non-STALE endpoints, and
an exact individually supported T014 candidate/mapping/release membership. T012
origin/subscription identity survives T014 sanitization; older T014 documents can
still join through `original_ids`. Topic equality alone creates no membership.

For downstream failure projection, each verified subscription now carries the
bounded additive `membership_witness` schema1: exact T014 source, target, binding
and edge documents, with their rules/capture identity. It carries only existing
refs, not a duplicate proof catalog or a new resolver. T028/T029 reuse one pure
membership guard: canonical edge/candidate and declaration IDs, mapping/capture,
selected contexts, scope, endpoint pair and contract/release identity must agree.
The raw SOURCE_ONLY/UNKNOWN declaration is distinct from FRAMEWORK_DERIVED endpoint
or reference-only envelope evidence. Reusing an endpoint proof as a mapping proof
cannot establish membership. Original IDs, provenance and async ordering stay
unchanged. See [change130 step9](changes/130_projectProcessFailures.md) for this
necessary T028 addition and the second T029 review correction.

Each admitted publication retains separate `async_boundary` steps with
`async_role=publish|channel|subscription`, connected by `async` transitions. A
subscription can enter a supplied consumer CFG through `CONSUMER_POTENTIAL`; its
exits never connect back to the publisher. Existing local success/exception edges
remain unchanged. Two consumer branches have no A-before-B path. Consumers in the
same group remain separate potential alternatives; the static view does not claim
that both receive the message. A generic T014 AMBIGUOUS status is not proof of
fan-out: every membership is checked independently. Duplicate members, conflicting
release selectors, stale/proof/context conflicts retain unresolved subscriptions.

`delivery=NOT_OBSERVED`, `processing_completion=UNKNOWN`, `exactly_once=UNKNOWN`
and `runtime_execution=NOT_OBSERVED` apply to derived steps/transitions. Supported
inputs contain **no instance-correlation mapping contract**. Consequently every
boundary records `instance_correlation=UNKNOWN` and `correlation_evidence_refs=[]`;
`membership_evidence_refs` documents a static binding, never correlation of one
business instance. Missing correlation never hides or removes a boundary.

Missing consumer/CFG, unknown membership, async ancestry loops, depth and expansion
limits retain reachable subscription boundaries and diagnostics. `max_depth` accepts
0–32 and `max_expansions` 0–128 (integers; zero preserves all immediate boundaries
without expanding targets). Loop/depth/expansion stops set `coverage.truncated`;
selected target diagnostics/limits/coverage survive even when expansion stops.
Root coverage counters remain root counters; `async_upstream_coverage` records
upstream contributions without presenting their sum as execution coverage. Output
is PARTIAL, with original evidence kinds/provenance and context IDs retained.
Malformed documents, unsupported T014 versions and hard topology/structure budget
overflows reject without mutation. At most 128 target process documents are accepted;
their combined structure/text budget is checked before copying (500,000 items,
32,000,000 text characters, depth 80). The output topology bound is 10,000 nodes and
30,000 edges; it never silently drops a candidate to fit that bound.

Compatibility: the existing ProcessView schema is unchanged; no store migration or
worker protocol change is introduced. Actual positive fixture uses Javac 21 on
prepared K1/K2 worker configurations; upstream Kotlin/unsupported annotation/CFG
limits remain boundaries, not new language support claims. See
[change127](changes/127_crossAsyncProcessBoundary.md) for exact AC tests and results.


T028 provenance and selector review corrections ([change127, steps 7–8](changes/127_crossAsyncProcessBoundary.md)):
endpoint summary UNKNOWN does not hide referenced STALE, contradictory or foreign
proofs. Every candidate's original evidence IDs must match its endpoint refs;
binding/edge declaration proofs must retain their exact T014 mapping/context/scope
and shared capture authority. Rejected memberships stay reachable boundaries.

Original proofs with compatible process scope/contexts are retained unchanged.
When an upstream record has missing/foreign scope or virtual Kafka contexts, an
explicit `REMOTE_PROOF_ENVELOPE` with `authority=PROVENANCE_REFERENCE_ONLY` retains
the entire unchanged record under `original_provenance` and its `original_id`.
Envelope scope/context describes only the derived reference's placement. Its kind
and polarity are UNKNOWN, freshness is STALE for a stale origin and otherwise
UNKNOWN. It never supplies compiler authority or bypasses the raw-proof guard;
`ASYNC_REMOTE_PROOF_REFERENCE_ONLY` preserves the original scope/context gap.
`remote_evidence_refs` lists original IDs; `membership_evidence_refs` remains only
the static declaration refs, never instance-correlation evidence.

Duplicate/conflicting release selectors for the same canonical membership are
checked across all bindings. Each subscription remains visible with
`ASYNC_MEMBERSHIP_SELECTOR_CONFLICT` and every `conflicting_selectors` entry, but no
consumer is imported from that conflict. Different canonical endpoints, contexts,
groups and explicitly compatible versioned endpoints retain independent potential
paths. No selector name alone creates another consumer or orders its execution.

## Static failure projection (T029)

`kgmaker.business_process.project_process_failures(process, graph=None, *,
compensation_proposals=(), max_policies=128)` returns the shared immutable
`ProcessView` (`process-failures-3`). Supply the original T025/T027/T028 process
and an explicit `KnowledgeGraph` snapshot or graph dictionary. A previously
projected failure view (rules v1, v2 or v3) is rejected; recompute from its original inputs.
The review correction and actual invocation regressions are recorded in
[change130, step 6](changes/130_projectProcessFailures.md).

```python
from kgmaker.business_process import project_process_failures, collapse_business_steps

failures = project_process_failures(process, graph, max_policies=128)
business = collapse_business_steps(failures)
for node in business.steps:
    if node.attributes.get("failure_role"):
        print(node.attributes["policy_status"], node.attributes["execution"])
```

Catch and distinct finally continuations retain all existing CFG edges and origin
IDs. Supplied T026 groups are expanded only through their validated stored members;
normal/return/throw continuations are not reconstructed from names. The existing
collapse contract continues to protect finally operations and exceptional edges.

Retry/DLT uses the existing `kafka-retry-1` producer and pure policy replay. The
supported positive scope is Java/K1 with pinned Spring Kafka 3.3.2, literal attempts
and suffixes, and one owner/context-bound `DltHandler`. The declared listener's
current selected exceptional-exit CFG certificate must exactly match the supplied
graph. Admission is per invocation: the canonical Kafka trigger must enter its
exact T025 root body, or be imported through a witnessed T028 subscription and
`CONSUMER_POTENTIAL` transition. Trigger/body/exit IDs, source process revision and
original trigger/membership proofs must agree. Imported occurrences require the
exact T028 `membership_witness`, replayed against retained raw T014 declarations;
all source/target/binding/edge refs must be present. A copied witness from another
endpoint, binding or capture cannot authorize this subscription. Older T028
outputs without the tuple remain readable, but their retry policy stays UNKNOWN;
regenerate the async projection from the original T014/T025 inputs to supply it. An ordinary Java call of a listener
method does not enter its Kafka container, even when another occurrence of that
same method is a legitimate imported consumer. `RETRY_POTENTIAL` connects that exit to one bounded retry declaration;
`DLT_POTENTIAL` connects it to the declared DLT boundary. Neither edge executes a
handler, unrolls attempts, implies a retry destination, or guarantees success.
Normal exits and ordinary callee exits do not initiate retries. The latter keep
a separate UNKNOWN policy boundary, raw refs and `KAFKA_ENTRY_OCCURRENCE_UNPROVEN`.
A declared boundary exposes `kafka_entry_occurrence` with exact trigger, entry and
exceptional-exit IDs; `source_exceptional_exit` also identifies rejected occurrences.
T012 Kafka owner IDs are manifest service IDs; T025 uses the exact `service:`
namespace prefix, with no name-based identity inference. Separate listener
groups are selected by original method/policy identity, never by topic/name.

Both roles retain `execution=NOT_OBSERVED`, `delivery=NOT_OBSERVED`,
`processing_completion=UNKNOWN`, `activation=UNKNOWN` and static policy status.
Raw policy/compiler and cross-context subscription records survive exactly inside explicit UNKNOWN
`PROVENANCE_REFERENCE_ONLY` envelopes; their process scope is projection metadata,
not an upgrade of the original proof. Admission checks raw proofs and exact CFG
anchors before creating a transition. A reference envelope never authorizes a
Kafka invocation; original trigger and subscription authority is checked separately. Stale/contradicting/foreign/unsupported
inputs retain an UNKNOWN boundary and diagnostic. Missing graph or policy does not
infer retries from names, attempts attributes or annotations in a process label.
K2 Kafka annotation capture is not supported by this policy producer and stays
UNKNOWN; actual K2 capture is tested as a negative case, not a positive retry claim.

An already explicit `transaction_boundary` is a `LOCAL_DECLARATION_ONLY` scope;
actual rollback remains UNKNOWN. Existing HTTP/Kafka boundaries carry
`local_transaction_rollback=NOT_PROVEN`. No remote effect is included in local
rollback and no compensation relation is inferred from a method name.

Compensation input uses only the existing semantic annotation schema:

```python
proposal = {
    "id": "proposal:compensation", "target_id": target_step_id,
    "label": "Proposed compensation", "source_refs": [existing_source_id],
    "semantic_review_status": "PROPOSED",
}
failures = project_process_failures(process, graph, compensation_proposals=[proposal])
annotation = next(a for a in failures.to_dict()["semantic_annotations"] if a["id"] == proposal["id"])
assert annotation["semantic_review_status"] == "PROPOSED"
```

Targets/source refs must already exist in the supplied process. An APPROVED input,
unknown field, invalid ref or cyclic value fails before output; proposal acceptance
creates no technical edge or confirmed rollback. The nested witness shares the
existing bounded-input limits; cyclic or oversized metadata fails without mutation. Existing technical diagnostics,
truncation and limits remain visible. `max_policies` is an integer 0–512 (default
128); omitted policy IDs appear in `FAILURE_POLICY_LIMIT` and coverage is truncated.
There are at most 128 proposals, 10,000 output nodes and 30,000 edges, with the shared
bounded input guards. Coverage is PARTIAL because static failure feasibility and
runtime outcomes remain unknown. Schema v1/v2/v3 graph inputs stay readable;
legacy graphs without the policy contract gain no retry facts.

This pure API performs no filesystem, worker, application, network or database
operation. There is no new CLI command, store or migration. Existing `graph view`
and `flow render` arguments are unchanged; T034/T035 remain separate tasks.
[Change130](changes/130_projectProcessFailures.md) records actual tests and limits;
Spring Kafka 3.2.0 actual version-matrix regression is NOT_RUN here because that
pinned JAR is unavailable, and full suite/runtime delivery are NOT_RUN.
