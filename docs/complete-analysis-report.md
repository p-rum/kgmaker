# Complete analytical report — bounded S09-W05 contract

The feature report projects an already validated FeatureAnalysis envelope v1.
It keeps its original packet, revision, graph selection, IDs and citations. JSON
adds `report_projection.schema_version: 1`; Markdown renders the same projection.
The existing analysis object, completion and exit codes remain compatible.
See [change131](changes/131_completeAnalysisReport.md) for implementation evidence
and [the specification](tasks/T003-S09-05-completeAnalysisReport.md) for the target.

The six facets overlap. They do not replace availability, acquisition or usability:

| Facet | Exact meaning |
|---|---|
| Required | Input has explicit requirement IDs. |
| Existing | A current EXTRACTED code/contract/schema/config/workbook citation matches the packet's source entity inventory, repository, path and hash. A declaration of `acquisition=EXISTING` alone is insufficient. This is static presence, not populated data. |
| Missing | Current validated `CONFIRMED_MISSING`, limited to `verification_scope`. Search result `NOT_FOUND_IN_SCOPE`, absent worker, unsupported parser or missing checkout cannot produce this facet. |
| Derived | Declared `acquisition=DERIVED`; original transformation and dependency IDs remain visible. No expression is evaluated. |
| External | Declared `EXTERNAL` or `USER_SUPPLIED`; it does not establish access, delivery or availability. |
| Unresolved | Unknown/partial/search-only availability, unresolved/proposed acquisition, usability other than FIT, missing source confirmation or stale evidence. Reasons are explicit. |

Stale reports keep historical availability separately and show effective availability
UNKNOWN. They do not retain a current Existing or Missing claim. The complete
original analysis remains available for audit. A projection can be PARTIAL while
its legacy processing completion says COMPLETE: these answer different questions.
`VERIFIED_IN_SCOPE` describes the report's declared trace coverage, never runtime
execution or populated data. Test execution stays NOT_RUN.

Questions may add `blocker_kind: BUSINESS | TOOL | UNCLASSIFIED`. An old question
without that field projects as UNCLASSIFIED; unknown values fail validation.
The type is a declaration and grants no evidence authority. A blocking question
remains open unless its ANSWERED state has a corresponding APPROVED packet answer;
stale answers do not resolve current blockers. Packet coverage gaps are separately
listed as TOOL blockers. Business decisions never follow merely from tool gaps.

The delivery table joins only explicit `requirement_ids` on inputs, questions,
changes, acceptance criteria and test plans. It reports missing acceptance/test
links and unresolved requirements. It does not invent a change, decision, owner,
acceptance or test result. Exact impact path records remain separate from these
requirement associations; foreign artifact IDs cannot become feature path proofs.

## CLI workflow

```bash
kgmaker feature prepare --root . --requirement requirement.md --id exposure-report --context CONTEXT_ID
# Fill the generated candidate with source citations and explicit decisions.
kgmaker feature validate --root . --analysis exposure-report --candidate .kgmaker/analyses/exposure-report/candidate.json
kgmaker feature apply --root . --analysis exposure-report --candidate .kgmaker/analyses/exposure-report/candidate.json
kgmaker feature report --root . --analysis exposure-report --format json
kgmaker feature report --root . --analysis exposure-report --format markdown
```

For a workspace, pass the same explicit `--workspace workspace.json` during
preparation. Existing selection rules still require one compiler context; the
report does not silently select all variants. Output remains confined to
`docs/generated/features/`. No report operation runs inspection, a build, package
installation, a renderer, network access or a database query. Git baseline reads
and existing content-bound snapshot readers are used.

Publication uses existing `atomic_write(before_replace=...)`: loaded current and
historical packet, accepted analysis, receipt and requirement bytes are pinned;
the existing read-only source/context snapshot is compared again immediately
before replacement. Input drift exits 3 and preserves the previous report. A
late timeout or cancellation removes the temporary output and preserves the last
valid generation. Already stale source bytes changing again are also detected;
repeated identical STALE messages cannot hide such a change.

## Actual cross-layer acceptance and boundary

`tests/test_complete_analysis_report_actual.py` explicitly runs prepared Javac21
and TypeScript5.7.3 workers with pinned React18 fixture dependencies. It captures
the BE DTO field → contract/release/generation → exact request/JSON/destructuring
→ state/JSX and separate test argument path through public `snapshot_workspace`
and `dataflow.impact_paths`. It saves this result as an explicit derived JSON
artifact with source hashes, contexts, edges, evidence IDs and original IDs.

The public feature packet selects the frontend context. It cites that artifact
by its exact file hash and JSON pointer; this citation proves supplied artifact
content, not a newly validated cross-context feature path. A separate SOURCE_ONLY
controller → literal Thymeleaf template → external PDF boundary is cited as an
INFERRED capability match with exact entity/source IDs. The existing feature
impact traversal does not traverse template relations. The validated feature
impact path instead covers the local request/JSON → JSX consumer in its selected
frontend context. The artifact and template branch stay separate.
The same report includes a business question (monetary unit/policy), a TOOL
question for the single-context boundary, and binary-XLS unsupported coverage.
It is PARTIAL, all static data availability UNKNOWN, PDF output NOT_OBSERVED.
No running application, live data, generated PDF or arbitrary template dialect
is claimed. Kotlin/K1/K2 and Mermaid are unchanged and not re-executed for this
report-only work package. Broader runtime rendering and multi-context feature
selection remain outside this delivery.

Compatibility: FeatureAnalysis/packet v1 stays unchanged apart from the optional
question field; graph/store v1/v2/v3 remain readable. Existing stored candidates
and receipts are not rewritten or migrated by reporting. Unknown graph versions,
invalid evidence and foreign paths continue to fail closed.
