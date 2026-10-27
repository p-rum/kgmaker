# Explicit business-process model (T023)

`kgmaker.process_model` supplies pure `ProcessDefinition` and `ProcessView`
models for explicit version1 JSON documents. It validates supplied structure;
it does not discover a business process, verify a checkout, execute a workflow,
or infer runtime/data availability. Technical freshness and evidence are supplied
input claims, preserved with their original kinds and references.

## Public API and example

From the repository root, using an environment with KGMAKER installed:

```bash
python - <<'PY'
import json
from pathlib import Path
from kgmaker.process_model import ProcessView

process = ProcessView.from_dict(json.loads(
    Path('fixtures/process-model/checkout.json').read_text()))
print(process.definition.process_id, process.definition.revision)
print([(edge.source, edge.target, edge.relation) for edge in process.transitions])
print(process.technical_status)
PY
```

The example is an explicit synthetic document for a payment choice, retry loop,
exception path and async transition. Its hashes and origin IDs illustrate the
serialization contract; they are not claims about an inspected application.
`COMPLETE_WITHIN_SELECTED_SCOPE` means that document's declared technical
structure is complete, not that payment, async dispatch or data availability has
been observed. The two payment alternatives have no card-to-cash continuation.

`ProcessDefinition.from_dict`, `ProcessView.from_dict`,
`validate_process_definition` and `validate_process_view` reject invalid input
with the shared `ViewValidationError.errors` diagnostics. They perform no file,
process or network I/O. Instances copy incoming and outgoing nested documents.

## Identity, revision and technical view

A definition contains exactly:

- `schema_version=1`, stable `process_id`, positive integer `revision`;
- `baseline_fingerprint`, `scope`, `context_selection`, explicit `context_ids`;
- `trigger_ids`, `semantic_review_status`.

`context_selection` preserves the caller's selection mapping. `context_ids` is
the explicit inventory of selected IDs used to check all technical references;
the model does not run T006 selection or infer IDs from an opaque mapping.
The caller remains responsible for obtaining a validated snapshot.

A view embeds `definition`, binds its canonical SHA-256 in
`definition_fingerprint`, and repeats `process_id`/`revision` for conflict
checking. A valid fingerprint identifies a document; it is not an authenticated
signature or proof that its claimed source hashes were observed. The view also
contains `technical_view`, `technical_status`, `entry_ids`, `exit_ids`,
`outcome_ids`, and `semantic_annotations`, with `schema_version=1`.

`technical_view` is the existing shared `ViewDocument` with `kind="process"`.
Its `view_id`, baseline, scope and full context-selection mapping must match the
definition. `ProcessView.steps` exposes its `ViewNode` values and
`ProcessView.transitions` exposes its `ViewEdge` values. No second graph store,
renderer model or execution resolver is introduced.

Every step and transition has nonempty `original_ids`. Step kinds cover explicit
trigger/action/decision/outcome nodes and bounded source-CFG kinds, including
entry/exit, condition, loop, call, exception and async/unresolved/service/transaction
boundaries. Transition relations include normal, branch/true/false/case,
exception/finally, loop/retry, async/suspend/resume, call/return and unknown.
Branch relations require an explicit `attributes.condition`. IDs come from the
input, not position or traversal order; loops and retry edges are valid.

Entry, exit, trigger and outcome targets must exist. A trigger targets a
`trigger` step listed among entries; an outcome targets an `outcome` step listed
among exits. A standalone definition only declares trigger references; these are
checked when it is composed into a `ProcessView`.

Each technical node/edge has matching `attributes.scope` and explicit
`attributes.context_ids`. Every provenance record, including unused records,
must stay within the definition scope/context inventory, and a claim's references
must stay within that claim's contexts. Shared T009 evidence-kind, polarity and
freshness checks apply. Candidate/unknown evidence cannot be labelled RESOLVED.
Missing evidence is permitted only for an explicit UNRESOLVED/UNKNOWN claim with
`attributes.boundary_reason` and no stronger kind. Such a boundary remains
PARTIAL/UNKNOWN. Diagnostics, missing entries/exits, stale/candidate/contradicting
or unknown proof also prevent COMPLETE technical coverage.

`technical_status` repeats the shared `coverage.status`, using only
`COMPLETE_WITHIN_SELECTED_SCOPE`, `PARTIAL`, or `UNKNOWN`. It does not combine
resolution, freshness, semantic review or runtime availability into confidence.

## Semantic overlay

`semantic_review_status` uses only `PROPOSED`, `APPROVED`, `REJECTED`, or
`NEEDS_REVALIDATION`. Status is supplied metadata; loading a document does not
approve it or authenticate an actor.

Each annotation requires `id`, existing `target_id`, `source_refs`, and
`semantic_review_status`. Its only optional fields are `label`, `description`,
and `grouping_proposal` (existing step IDs). At least one must be present.
Source references bind to supplied technical/original/provenance IDs. Empty
source references are an uncited semantic proposal, not technical evidence.
Unknown fields, nested technical payloads and invented targets/citations are
rejected. A grouping remains a proposal and never rewrites control-flow.

Annotations are serialized separately from `technical_view`. Adding an APPROVED
label changes process content but leaves technical bytes, evidence and
`technical_fingerprint` unchanged. No technical edge, condition, ordering,
availability or execution fact can be submitted through the overlay.

## Canonicalization and compatibility

`to_dict`, `to_json` and `content_fingerprint` preserve IDs while sorting
unordered collections by identity. Definition context/trigger IDs, view
entry/exit/outcome IDs and annotation source/group member IDs are sets serialized
in sorted order. Technical nodes/edges and provenance retain the shared view
canonicalization. Generation timestamps remain outside both content fingerprints.

The structural schema is [process-v1.schema.json](schemas/process-v1.schema.json);
it references the existing viewv1 schema. Python validation additionally enforces
cross-references, hashes and scope/evidence invariants. No graph v1/v2/v3 or
shared viewv1 migration is required; existing `graph view` and `flow render`
behavior is unchanged.

Trigger discovery, source-CFG adaptation/grouping, process annotation packets,
apply/review/history, catalogue, process CLI and render/export are separate
T024–T040 tasks. This model does not establish those capabilities or complete T004.
