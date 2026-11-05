# Explicit local process review (T032 candidate)

The Python API in `kgmaker.process_store` persists a semantic review envelope;
it never changes the technical `ProcessView`, graph, source checkout, evidence or
`ProcessDefinition.revision`. Documentary citations retain their separate captured
binding; they are not technical provenance. Reviewer identity is a local declaration
(`LOCAL_DECLARATION_NOT_AUTHENTICATED`), not authenticated approval.

```python
from kgmaker.process_store import prepare_process_review, persist_process_review, read_process_reviews

review = prepare_process_review(process, packet, candidate, documents=documents)
receipt = persist_process_review(
    root, process, packet, candidate, documents=documents,
    action="APPROVE", reviewer="local:reviewer", operation_id="review:1",
    expected_head=None, expected_payload_hash=review["payload_hash"],
    expected_baseline_hash=review["baseline_hash"],
)
current = read_process_reviews(root, process, documents=documents)
```

`root` must be an existing approved directory. Both prepare and persist rederive
T031 against the current explicit process/documents/conflicts. Invalid input raises
`ProcessReviewError` with a fixed nonsecret diagnostic code, without partial output.
A valid prepared proposal is still PROPOSED/PENDING; only the explicit persistence
call records APPROVE or REJECT. Both conflicting same-target fields and captured
doc/code CONFLICT block APPROVE. REJECT records a decision without publishing new
labels or deleting an earlier approval. Empty proposals are rejected.

The envelope separates monotonically increasing semantic revisions from technical
process revisions. `active_annotations` is the normalized proposal payload under
an explicit APPROVE decision, retaining its original PROPOSED annotation status;
the decision history supplies review authority, never technical authority.
A later REJECT leaves earlier approved labels active if their baseline still matches.

CAS requires the exact predecessor `head` (None for empty), payload hash and baseline
hash. Operation IDs bind reviewer/action/payload/baseline/predecessor. Exact retries
return the immutable receipt without rewriting bytes/mtime; historical retries
have `is_current=False`. Reusing an operation ID differently is an error.

Reads rederive the current packet with saved validated budgets. A changed explicit
baseline, document/conflict capture, rule, source context or technical/presentation
content gives `NEEDS_REVALIDATION` and no active labels; the historical APPROVE stays
readable. Another scope has a different namespace. Explicit snapshots do not prove
physical freshness of a separately changing checkout.

Storage is a single authoritative JSON under `.kgmaker/process-reviews`, named by
a hash of exact process ID and scope. Format1 caps history at128 entries and encoded
JSON at2MiB, fails rather than prunes, rejects corrupt hashes/duplicate keys/unknown
fields, and uses private sibling temp + fsync + atomic replace. Invalid requests
publish no semantic JSON; coordination infrastructure can remain after failed writes.
A global thread lock and persistent flock coordination inode serialize cooperating
POSIX writers across threads and processes. Windows writes are controlled UNSUPPORTED.
Ordinary symlinks are rejected. There is no hostile same-privilege filesystem-race
or cryptographic tamper-proof/authentication guarantee.

Optional `cancelled` is a caller callback checked before publication. Pre-replace
failure/cancellation preserves the old JSON and removes temp. Replace is the
linearization point: later cancellation returns COMMITTED; directory-fsync failure
returns INDETERMINATE with operation identity for recovery by retry/read. Atomic
visibility/CAS do not promise power-loss durability on every filesystem. No CLI,
network, model, compiler/build, unrelated feature apply or implicit discovery runs.

Current evidence: initial absent API6FAIL0.50s; current36feature tests PASS1.93s,
including real process/thread CAS. Coalesced pure regression269PASS94SKIP8.74s;
skipped compiler cases were not executed. Those pure checks were historical; completed descendant validation follows below.

## Completed descendant validation

Base2c7b38 contains merged T030/T031. Whole store module, testfile and current
process_semantics are exactactual2df55. All36own cases XMLPASS in ONEcompleted
combined strict descendant full2587PASS10allowedoptionalSKIP2042.93sJUnit, with
4897hashes/five recursive member sets unchanged. Original2102parentIDs2092PASS10SKIP;
currentmain2328+36 source/IDunion2364 classified2354PASS10sameSKIP. This is not a
standalone parent run or a new collection. See [proof](validation/t032-descendant-proof.json).
Final exactpairreview/merge remains separate; no new tests/build/fullrepeat.
