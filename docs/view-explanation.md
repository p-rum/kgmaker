# Snapshot-bound view explanation (T018 draft)

```python
from kgmaker.view_explanation import explain_view_element, capture_explanation_source_status
report = explain_view_element(view, element_id, captured=topology_capture,
                              graph=original_public_graph, filtering=optional_filter_envelope)
# Explicit optional local I/O, using reference IDs from the bound public graph:
status = capture_explanation_source_status(workspace, original_public_graph,
    captured=topology_capture, reference_ids=selected_original_reference_ids)
report = explain_view_element(view, element_id, captured=topology_capture,
                              graph=original_public_graph, source_status=status)
```

Pure explanation rederives the original T016 topology from its trusted common
capture. A T017 filtered view must match a full filter-envelope rederivation using
its original criteria. Exact view and element IDs apply only to that supplied
snapshot; an unknown element returns UNKNOWN_ELEMENT. No newer graph/private
LATEST/name lookup repairs missing provenance. This API never calls source loaders,
projectors/capture/worker/build/model/network or a store.

Reports retain original view/baseline/content/capture/graph fingerprints, rule
versions, scope/context refs and realm/topic/group. Expansion follows exact input
interface/mapping/release/edge/binding and evidence IDs. Candidate bindings retain
omitted alternatives even when a filtered view displays one ambiguous sibling.
Original supporting/contradicting/unknown buckets, evidence kind and freshness
remain distinct from static remote SOURCE_ONLY declaration proof. No JVM/process
edge, runtime/payload availability or confidence is invented. Missing refs/graph
or unsupported canonical locator contracts remain explicit unavailable boundaries.

Sanitized topology payload hashes cannot recreate a source range. An optional
PUBLIC graph must match the original common-capture graph fingerprint. Source
locators require exact selected canonical Node plus symbol/call-site/context,
repo/path/scope and graph.files == context.source_files == captured source SHA.
Ranges come only from matching captured canonical metadata; no line1/default end,
same-name search or current-source parsing. Missing ranges remain null. Legacy or
unsupported proof contracts remain ref-only UNKNOWN; the presence of a reference
is not a new compiler verification claim.

Source-status capture is a SEPARATE explicit read phase. Caller supplies graph
reference IDs, never free paths. Every locator is derived and checked against the
same bound graph and actual selected context first. Loaded declared workspace,
raw manifest hash and declarative fingerprint must match; actual loaded roots,
not caller-forged private root fields, determine repo membership. Shared safe_path
rejects unsafe paths/symlinks; bounded descriptor-relative NOFOLLOW reads retain
confinement, regular-file checks and per-file/total limits. Manifest reads are
bounded/hash checked too. Unsupported safe-reader capability or oversized sources
are unavailable, never a content-match proof. No bytes/excerpts or absolute roots
are exported; results contain only typed original locators, hashes and statuses.
No file/cache/store is written.

Without explicit source status, report current_source_status is NOT_CHECKED,
never CURRENT. A supplied status handoff is consistency-bound to original capture,
graph and exact locator inventory. CONTENT_MATCH means only that file's explicit
local read matched captured bytes; it does not upgrade a stale compiler context or
UNKNOWN/CAPTURE_TIME_ONLY remote mapping. Changed/deleted files give SOURCE_STALE/
SOURCE_MISSING while original fingerprints/source SHA remain unchanged. Mixed
file results are visible individually. Supplied local handoffs/self-hashes are not
cryptographic authentication against replacing all inputs coherently.

Bounds apply before copy/JSON and to complete output/reference inventories;
unsafe recognized credential/userinfo IDs fail with fixed nonsecret errors.
Arbitrary labels/config/SQL/schema/source/proof payloads are omitted or hashed.
All inputs remain unchanged on success/error. Current source checkpoint uses
hand-labelled graph protocol fixtures plus real temporary filesystem observations,
not a new compiler or service run. Current4e4fcd6 preserves merged T014/T016/T017/
Common/T012/T013/W07/process source and CI. Owned source/tests are exactapproved299
and accepted2df; all59own PASS in the one2587PASS10SKIP full. Current2563-case union
maps2553PASS10sameSKIP via exact source/per-ID/native transfer, not a new full on
this head. Current independent final-pair review remains a gate.

Canonical repository namespaces are decoded once for known unsafe URI/auth or
credential syntax; existing typed field name:descriptor IDs remain IDs and gain
no source authority from that lexical check. Exact-ID lookup tables are ephemeral
within the supplied graph; unsupported reference contracts remain unavailable.
Preparatory source checkpoint:262purePASS/0SKIP,10actualcasesDESELECTED.
