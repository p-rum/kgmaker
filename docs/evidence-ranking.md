# Evidence ranking — execution-2 / impact-2

T003-S07-W08 supplies read-only priorities over an existing graph. A score is
neither probability nor business importance, runtime execution, data availability,
or proof that a static path is feasible. Delivery/test evidence and limitations:
[change126](changes/126_evidenceRanking.md).

```sh
kgmaker graph rank --root . --profile execution --explain --format json
kgmaker graph rank --root . --profile impact --format markdown
# Use actual IDs from the selected index, not source names:
kgmaker graph rank --root . --context "$CONTEXT_ID" --entry "$SYMBOL_ID" --format markdown
```

JSON remains the default. `--explain` remains accepted; both formats always expose
the explanation. `--scope production` is the default; test/unknown inventory
requires an explicit scope. Compiler variants require the existing explicit
`--context` selection when ambiguous. A stale compiler index is rejected by the
existing public index validation; no inspection, build, installation or application
is launched by ranking. The existing source-only fallback remains in memory.

## Terms and witnesses

| Breakdown term | Weight / rule | Contribution records |
|---|---|---|
| `entry_relevance` | 10 for the selected executable entry only when a call/side-effect witness exists | entry ID and incident evidence |
| `execution_path` | 5 for an entity on a directed witness from the entry | deterministic shortest path, node IDs and every graph edge |
| `execution_centrality` | one per admissible incident call relation, capped at 10 | incoming and outgoing edges |
| `side_effects` | one per existing source-owned persistence/write/delete/publish/consume/HTTP side-effect relation, capped at 10 | exact graph edges; no inferred operation completion |
| `type_reference_impact` | unique type/constant reference witnesses, only in `impact` | reference edges, independently from execution |
| `incompleteness_penalty` | negative `min(raw score, 10, sum(gap penalties))` | every localized gap and its penalty |

The score is the sum of the breakdown, with zero as its floor. A witness is
identified by source, target, relation, evidence kind, context IDs and evidence
IDs. Repeated ingestion, changed confidence scores or presentation text do not
add weight. `shared_references` retains the raw stored reference count for
compatibility; it is not an execution term. Results sort by descending score,
then entity ID; paths and witness/gap lists have stable ordering.

Only resolved/candidate/framework/runtime call families with executable endpoints
contribute. An unresolved `declares_call`, method reference, invokedynamic
boundary, legacy name-match `calls`, `contains`, configuration or type reference
adds no execution weight. Calls crossing test/production scope do not add
production execution weight even in the all-scope inventory. Enum methods can
have execution evidence while the enum type itself has zero execution score.
The graph validator checks references before scope filtering; invalid input
cannot hide in an omitted scope. Legacy confidence is never a replacement for
evidence IDs.

## Incompleteness and compatibility

Rows include `coverage.status`, `coverage.gaps`, `penalty_points`,
`penalty_applied`, `path` and `contributions`. Existing top-level/row keys remain.
The algorithm version deliberately changes from `execution-1`/`impact-1` to
`execution-2`/`impact-2`; consumers must not compare old/new numeric scores as the
same metric. No persisted graph schema or compiler worker protocol changes.

Gap penalties are: missing context 3, unknown freshness 2, SOURCE_ONLY 3,
partial/unknown context coverage 2, legacy missing call-site inventory 2,
no execution witness 3, unresolved relation 3, unresolved call 5,
incomplete dispatch 2, ambiguous dispatch 3, stale context/relation 5,
runtime-only sample 2, and relevant provider diagnostics 1. Repeated identical
gaps count once; distinct causes remain distinct. A path inherits its call-site
gaps, not unrelated calls in another method. Provider diagnostics use their
context/path/line bounds when available. Unknown source locations remain explicit
in their original diagnostic. Stale relations add no execution or impact weight.

A row without admissible evidence is `UNKNOWN`; an evidenced row with gaps is
`PARTIAL`. `COMPLETE_WITHIN_INDEXED_SCOPE` is limited to that row's supplied
witness/coverage inventory. The overall result remains `PARTIAL` when evidence
exists and `UNKNOWN` when none exists. `--strict` returns 4 for either status;
invalid input returns 2. A runtime edge always reports
`dispatch_complete=false` in callgraph navigation: an observation is a sample.
An independently complete current static call site retains its completeness;
it is not overwritten by the runtime record.

Graph/store v1, v2 and v3 remain readable through the existing reader. V1 retains
unknown scope/role and does not acquire compiler proof. V2 resolved edges remain
usable with valid context/evidence references, but lack per-site completeness.
V3 retains unresolved/candidate boundaries. Selecting a compiler variant now also
preserves SOURCE_ONLY contexts actually referenced by retained structural edges,
so the projected snapshot can round-trip. `graph_selection` still selects exactly
one compiler variant; this is provenance retention, not extra compiler selection.

## Verified scope

`tests/test_evidence_ranking.py` covers schema fixtures, invalid refs, ambiguous
and stale evidence, runtime/static separation, duplicate/confidence invariance,
non-execution references, score accounting, deterministic ordering, scope and
variant isolation, read-only failures and both CLI formats.
`fixtures/evidence-ranking` exercises an actual Javac/JDK21 inspection, including
an enum method, production/test/config/type references, interface dispatch and an
intentionally missing target. The test executes inspection explicitly once and
then forbids subprocesses during both rank CLI calls. It does not run the Java
application. Framework side-effect scoring is tested with a valid graph model
fixture; it does not expand any framework extractor's supported matrix.

General callgraph completeness, Kotlin/TypeScript ranking-specific native
acceptance, cross-service business importance, unified flow views (W09), complete
analytical reporting (S09-W05), and the whole T003-S07 milestone are not claimed.
The existing feature-analysis report is unchanged; the new Markdown report is
exposed directly by `graph rank --format markdown`.
