# Read-only process annotation validation (T031)

`validate_process_annotations` extends the same pure `process_semantics` module as
T030. It accepts an explicit current ProcessView, its T030 packet and a semantic
candidate. It never loads a source/provider, calls a model/compiler/build/Git,
reads/writes files, applies annotations or certifies grouping. Current means
content supplied by the caller, not an independently fresh physical checkout.

```python
from kgmaker.process_semantics import (
    prepare_process_label_packet, validate_process_annotations,
)
packet = prepare_process_label_packet(process_view)['packet']
target = process_view.steps[0].id  # caller chooses an existing target
candidate = {
    'schema_version': 1, 'packet_hash': packet['packet_hash'],
    'annotations': [{
        'id': 'proposal:label-1', 'target_id': target,
        'label': 'Ověřit objednávku', 'source_refs': [target],
        'semantic_review_status': 'PROPOSED',
    }],
}
report = validate_process_annotations(process_view, packet, candidate)
# report['valid'] means structural/content validation, never human approval.
```

For a packet prepared with documents/conflicts, pass the same CURRENT explicit
captures to validation. Missing/changed captures invalidate binding; they are
not discovered from disk or recovered from omitted prose. Supplied documentary
hashes remain supplied rather than newly physically verified.

## Full current binding, not a self-signed allowlist

The validator bounds all input before copying/JSON, then rebuilds the complete
T030 packet using its validated original token/character budgets. Exact canonical
packet equality binds rules/version/hash, current definition/technical/content
fingerprints, revision/baseline/scope/context, full allowed targets/refs, coverage,
uncertainty, documents and candidate schema. A forged allowlist with a recomputed
self-hash is rejected. Generation-only metadata and unordered records retain the
same T030 identity; changes to omitted raw labels/ordered expansion still alter it.
This is consistency, not authentication against replacement of every input.

Top-level candidate keys are exactly `schema_version`, `packet_hash`, `annotations`.
Version is int1 (not bool), annotations a plain list of at most256records. IDs
are unique and cannot collide with process/technical targets. Records use only
T030's rederived allowed/required schema and fixed PROPOSED status. At least one
label, description or grouping proposal is required. Labels are nonblank Unicode
strings up to512characters; descriptions up to4096, allowing ordinary newline/tab.
Text is preserved as proposed. Recognized credential/URI/control payloads are
rejected without echo; arbitrary unlabeled secret detection is not claimed.

Sources are unique existing allowed refs, including explicit captured documents;
original compiler refs are not an alternate allowlist. Empty citations remain an
explicit PENDING review item. Grouping members are unique existing step IDs, not
transitions, evidence or source IDs. Grouping is a proposal set, not a certified
T026 collapse, equivalence, topology or execution order. Existing outcomes can be
labelled; new outcome/node/edge/condition/availability/context/confidence fields
are rejected. There is no technical mutation or inferred runtime observation.

## Reports and review

Expected malformed/stale/unsafe/over-limit data returns a fixed-code report with
`valid=False`, `validation_status=REJECTED`, empty annotations and no reflected
untrusted values/keys/errors. Binding is null until the packet is rederived; later
candidate rejection may cite only that already-validated current binding. Normal
invalid input does not throw. Unexpected programmer/infrastructure failures
outside the supported validation are not disguised as business results.

Structurally valid candidates return `validation_status=VALID`, normalized PROPOSED
annotations and `review_status=PENDING` or `CONFLICT`, always `requires_review=True`.
Passing validation is not approval, publication or an applied ProcessView.
Every proposal remains a review item. Different values of an overlapping field
for the same target retain all proposals and produce CONFLICT; complementary or
identical proposals remain pending. Duplicate annotation IDs are rejected even
when content matches. No arbitrary first/last winner is selected.

Captured documentary CONFLICT/UNKNOWN remains cited separately. Natural-language
comparison is always NOT_EVALUATED; the validator neither interprets an 'approved'
label as approval nor invents a doc/code NLP contradiction detector. Known technical
status, fingerprints and unresolved/truncated coverage are carried unchanged.
T032 review/apply and T034 CLI remain separate pending tasks. Existing process and
graph readers are unchanged; the separate versioned report creates no new store.
