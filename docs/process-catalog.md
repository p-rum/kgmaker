# Explicit process catalog (T033)

Delivery status (2026-11-07): T033 is MERGED in [PR79](https://github.com/p-rum/kgmaker/pull/79) (`5095343`).
Current full acceptance is NOT_RUN in this documentation audit. Historical
checkpoint results and pre-merge review gates below describe their stated SHA.
Use the [current delivery inventory](production-analysis-progress.md) and
[change111](changes/111_reconcileDeliveryStatus.md) for present status.

`kgmaker.process_catalog.catalog_business_processes` projects current T024 trigger
inventory and explicitly supplied current/historical ProcessViews, reading validated
T032 review history. It never discovers a project, expands a technical path or
writes a catalog/store/source file.

```python
from kgmaker.process_catalog import catalog_business_processes
catalog = catalog_business_processes(
    root, current_trigger_inventory,
    current_processes=[current_process], historical_processes=[previous_process],
    review_inputs=[{"process_id": current_process.process_id,
                    "documents": captures, "conflicts": captured_conflicts}],
    aliases=[],
)
```

ProcessViews can be dictionaries or model instances; trigger inventory can be a
validated dictionary or ViewDocument. Root is an existing approved directory. Its
review files are read via T032; a supplied `approved=True` bundle is not accepted.
Missing review input means empty explicit documents/conflicts, potentially requiring
revalidation of an approval bound to other captures. No document is fetched.

Rows have stable `selection_id` from exact canonical process ID and scope, original
member IDs, and per-member current/historical revision records with fingerprints,
trigger IDs, owner/evidence states, outcomes and technical uncertainty. Labels are
not identity; two processes with the same approved label remain separate. Exact
canonical duplicates deduplicate; conflicting snapshots of the same revision and
multiple distinct explicitly current snapshots fail without first/last selection.
A historical revision must be supplied explicitly: T032 is a semantic review store,
not an archive of all past technical ProcessViews. No reconstruction is invented.

A current member is CANDIDATE until T032 reports APPROVED, then REVIEWED while
retaining supplied technical coverage and UNKNOWN runtime/data availability.
NEEDS_REVALIDATION retains immutable prior decisions without active labels. REJECT
creates no approval. As in T032, a later REJECT does not delete a baseline-matching
older approval. An explicit historical snapshot always has no active labels/path.

Per-trigger `presence` is exact PRESENT, CONTEXT_NOT_SELECTED or
NOT_IN_CURRENT_INVENTORY. A missing/stale/nonselected trigger makes that revision
HISTORICAL/inactive within this selected inventory; the original CURRENT/HISTORICAL
designation is preserved separately. PARTIAL/UNKNOWN T024 coverage means absence
is not proof of universal deletion. No fallback to a matching label/entry symbol
or implied registration/execution. Some missing refs remain individually visible.
`in_current_selection` is static inventory membership/freshness, not runtime proof.

Aliases are optional one-hop records with exactly `alias_process_id` and
`canonical_process_id`. Both identities must be supplied with exact same scope,
context IDs and context selection across their supplied revisions. Unknown/self/
chained/cyclic/multiple-target mappings fail. Every original member, revision,
trigger and review status stays separate inside the group. No group-level approved
label, availability or arbitrary payload winner exists; one member's approval
never authorizes another member. Selection identity is the explicit canonical ID.

Raw technical labels/diagnostics/proof/config/document prose are omitted and bound
by hashes. Only validated T032 semantic payload text is exposed under its separate
local review authority; it does not become technical evidence or authenticated
human identity. Original valid Unicode/path-space IDs remain unchanged; recognized
credential/control forms fail with generic ProcessCatalogError codes and no raw
exception paths/chains. Opaque IDs retain the explicit privacy limits of T030.

Format1 bounds input before model copies, allows at most256 supplied snapshots,
256 alias/capture rows and4096 trigger nodes, and hard-fails above2MiB final canonical
JSON. No silent truncation, filesystem mutation, model/network/subprocess/build,
CLI T034 or physical-freshness guarantee. Empty valid inventory/history is an empty
catalog, not evidence of universal absence. Corrupt T032 storage fails closed.

Evidence: public absent-API RED6FAIL0.49s; current37ownPASS1.62s. Coalesced pure
regression306PASS94SKIP9.48s. All intermediate failures retained; skipped compiler
cases are unverified. Those pure checks were historical; completed descendant source validation follows below.

## Completed descendant validation

Base7e6c83 contains merged T030/T031/T032. Whole catalog module, testfile and five
process dependencies are exactactual2df55. All37owncases XMLPASS in ONEcombined
strict full2587PASS10allowedoptionalSKIP2042.93sJUnit,4897hashes/five member sets
unchanged. Original2139parentIDs2129PASS10SKIP; currentmain2364+37source/IDunion
2401 has2391PASS10sameSKIP in thatXML. No standalone parent run/new collection.
See [bounded proof](validation/t033-descendant-proof.json). Finalexactpairreview/
merge separate; no new tests/build/fullrepeat.
