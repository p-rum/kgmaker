# Pure process-label packets (T030)

Delivery status (2026-11-07): T030 is MERGED in [PR75](https://github.com/p-rum/kgmaker/pull/75) (`9eec41a`).
Current full acceptance is NOT_RUN in this documentation audit. Historical
checkpoint results and pre-merge review gates below describe their stated SHA.
Use the [current delivery inventory](production-analysis-progress.md) and
[change111](changes/111_reconcileDeliveryStatus.md) for present status.

The Python API prepares review input from an explicit existing `ProcessView` (or
its validated document). It never discovers a process, invokes a model/compiler,
loads a checkout, calls `feature.prepare`, persists a packet or applies semantics.
T031 read-only validation and T032 local review are merged. T034 CLI remains planned.

```python
from kgmaker.process_semantics import prepare_process_label_packet

# process_view is the caller's existing explicit ProcessView, e.g. T025/T026 output.
result = prepare_process_label_packet(process_view, token_budget=8000, char_budget=32000)
packet = result['packet']
candidate = result['candidate_template']  # annotations: [], bound to packet_hash
```

No new CLI command is introduced. The empty template invites only labels,
descriptions, cited source refs and grouping proposals for existing process/step/
transition targets, with fixed PROPOSED status. Existing approved prose is not
copied and this function does not establish human approval. Original target IDs,
source/evidence refs, entry/exit/outcomes, scope/context identities and captured
resolution/evidence/freshness remain explicit. Collapsed expansion is not repeated
or recomputed; its original content is bound by the ProcessView fingerprint.

`packet_hash` is SHA256 of canonical packet JSON excluding that hash. The template
binds the hash. Definition/technical/process-content fingerprints bind actual
input; a stale caller-supplied baseline alone is insufficient. Dict order,
semantically unordered technical records and generation timestamps do not change
identity. Ordered expansion, source/evidence changes and changed captured document
hashes do. No source freshness or runtime availability is newly inferred.

## Privacy and explicit documents

No raw labels, descriptions, conditions, configuration, compiler annotation values,
proof prose or document text is exported. Fixed-reason omissions retain their
existing safe IDs and content hashes. Only allowlisted typed structure, enums,
numeric confidence and reference fields leave the function. Unicode IDs and code
paths containing spaces remain unchanged. Control/format characters, recognizable
credential/URI payloads (including embedded scheme-relative userinfo and
recognized Bearer/Basic auth tokens) in required IDs are rejected with fixed non-secret error
codes; IDs are never renamed. This is not authentication or universal secret
recognition for opaque caller-declared identifiers. Mandatory selection supports
existing service context-list, explicit-row and service-inventory shapes. Raw
selection coverage/diagnostics are hash-bound instead of copied.

Captured documents use exactly `ref`, `format` (HTML/MARKDOWN/TEXT/STRUCTURED),
`content_hash` (SHA256), `scope`, `context_ids`, `selection_provenance` and optional
`content`. Provided content must match its SHA; absent content is explicitly
SUPPLIED_NOT_REVERIFIED. Provenance is ref-only: `capture_id`, `source_ref` and
optional `context_ids`; unknown prose/config fields are invalid. The source ref
must be known or the document's own captured ref. No live Confluence, file loader,
URL fetch or cache exists here.

Optional `conflicts` records have `document_ref`, existing `target_id`, known
technical `source_refs` and CONFLICT/UNKNOWN status. These explicitly supplied
review items cannot change technical topology or evidence. Natural-language
comparison remains NOT_EVALUATED, including when captured conflicts are present;
this API does not infer NO_CONFLICT from unparsed prose.

## Complete cost and uncertainty

Cost is the final canonical `{packet,candidate_template}` Unicode character count,
UTF-8 byte count and ceil(bytes/4) token estimate, including schema, omissions,
hashes, template and cost fields. Public accounted `status_padding` gives the
boolean/reason variants equal serialized width to avoid exact-boundary oscillation.
Numeric lengths converge to a checked fixed point; failure is controlled.

`mandatory_cost` measures the complete packet with all optional document summaries
omitted (and their required omission rows present); `actual_cost` measures the
returned artifacts. Optional ref-only summaries are admitted whole in ref order,
or retain an explicit BUDGET omission. Actual cost can be lower than mandatory
cost when a safe summary is shorter than its omission record. No identity,
original ref, evidence kind, captured conflict or unresolved boundary is trimmed.
A tiny soft budget reports `over_budget` and MANDATORY_IDENTITY_AND_COVERAGE rather
than inventing completeness. Hard bounds fail without returning an artifact.
Budgets reject bool/non-int/nonpositive/oversized values. Input checks count shared
objects per occurrence, detect cycles and bound depth/text/collections before any
model copy or JSON; hard packet limit is two million characters.

Unsupported/source-only process snapshots retain PARTIAL/UNKNOWN, truncated flags
and every unresolved target; packet preparation does not fill unsupported syntax
or turn a static path into observed execution. Invalid input is immutable, errors
never echo source keys/values, and there is no last-artifact write to corrupt.

## Validation attribution

All47feature cases PASS in one completed strict combined descendant run
`2df55ff8d15d790808f6a81072144eeb408a05b8` (2587PASS10allowedoptionalSKIP,
2042.93sJUnit). ALL1990T030parent cases are classified1980PASS10allowedSKIP.
Original module byteprefix/32AST/35global bindings and complete T030 testfile are
exact; appended T031 helpers have disjoint bindings. This supplies parent support
from a reviewed descendant, not a standalone T030 full command.
See [bounded source/result proof](validation/t030-descendant-proof.json).
Final exact base/head review remains separate; no new compiler build or full rerun.

Current main2a (Common/T012/T013 merged) requires all2116current-main parent
identities plus47T030 cases:2163total,2153PASS10sameallowedSKIP in actual2df.
OriginalT0301990 is also fully contained. This is an exact source/ID-union proof,
not a new parent collection/full/test execution. Original47own cases remain PASS.
