# Feature analysis: implemented foundation and remaining milestones

## Current implementation

This page describes the source-only feature pipeline at the PR #5 baseline
`6b5aea1`. The normative target is [T001](tasks/1_featureAnalysis.md); the integrated
completion plan is [T003](tasks/3_finishProductionAnalysis.md).
Flyway replay, explicit multi-repository workspaces and scoped availability proofs
are implemented in the supported subset described in
[flyway-workspace-proofs](flyway-workspace-proofs.md).

| Area | Implemented | Remaining |
|---|---|---|
| Lifecycle | prepare, validate, apply, report, status, revise, compare, data-check | Selective revision packets and dependency invalidation |
| Provenance | Byte hashes, exact line quotes, JSON pointer/value, workbook sheet/cell/value, requirement/decision evidence, repo-qualified references | HTML-section localization |
| Graph | Reader accepts graph v1/v2/v3; feature envelope is separately version 1; fresh compiler contexts/call sites/CFG are retained | Unified explicit context selection in every feature/report view |
| Availability | OBSERVED_VALUE_PATH with approved mappings, CLOSED_CONTRACT_ABSENCE and APPROVED_MISSING; scoped negative search | Wider automatic value-path construction and selective proof reuse |
| Isolation | TO_BE namespace, dangling-reference checks, read-only validate, atomic apply | No automatic promotion of proposals, by design |
| Workspace/schema | Explicit supplied repos, content caches, selected Flyway stream/target | Full compiler cross-repo and ORM coverage |
| Budget | Full metadata manifest, selected source context and explicit omissions | Dependency-aware relevance and resumable packets |
| Freshness | Content baseline, no timestamp identity | Whole-packet invalidation remains for unrelated source changes |
| Agents/reports | Analyst/data-auditor routing, Czech/English reports, immutable revisions; literal Thymeleaf model/template bindings and static exact-arity fragments; unsupported `th:each`/`th:with` local scopes stay UNKNOWN | Full cross-layer paths, loop/alias scope modeling, other template dialects and richer artifact coverage |
| Confluence/XLSX | Content-bound offline Confluence approvals; bounded XLSX sheets/cells/named ranges/formula dependencies; fake sync adapter with hash/version approval; offline connection configuration | Live adapter and integration execution are deferred |

No model client, MCP server or implicit build/network call is introduced by feature
commands. Positive verdicts require the supported deterministic proof contracts;
source declarations, name similarity, a successful build or static reachability
alone do not prove availability. Supplied observations and declared approvals are
not authenticated access to production. Unsupported claims remain UNKNOWN/pending.
AS_IS reuse candidates remain evidence-backed INFERRED/AMBIGUOUS claims; validation
checks citations and supported contracts, not arbitrary prose entailment or finance.

## CLI workflow

Packets record `analysis_context_fingerprint`, context provenance and graph evidence
IDs. `query` and directed `impact` accept `--context`; multiple active compiler
contexts require explicit selection. For example:

```bash
kgmaker query --root . --context CONTEXT_ID payment
kgmaker impact --root . --entity ENTITY_ID --include-data-flow --context CONTEXT_ID --format json
```

Offline Confluence exports may include `kgmaker-approved-requirements.json` with
schema version 1 and a `requirements` array. Each entry supplies `id`,
`document_file`, `document_sha256`, `section`, `subject`, `relation`, `target`,
`statement`, `decision_id`, positive `decision_revision`, and `approval_status`
(`APPROVED` or `UNAPPROVED`). The exact statement must match an extracted assertion
and the page hash. This preserves supplied decision provenance; it does not
authenticate the approver. A conflicting approved assertion is reported as
`IMPLEMENTATION_VS_APPROVED_REQUIREMENT`. Feature coverage references the saved
documentation conflict index only while page, attachment and approval-sidecar hashes remain current. Legacy indexes without the sidecar hash remain readable but require `kgmaker docs check` before their conflicts can be reused. Stale indexes produce an explicit limitation and do not transfer approval. Duplicate decisions for the same assertion are rejected before cache publication. Already prepared packets also revalidate their documentation conflict coverage, including exports outside the repository, before validation/apply. No graph/store schema or worker protocol change is required.

```bash
kgmaker feature prepare --root . --requirement requirements/new-hedge.md --id additional-hedge --token-budget 8000 --scope production --context <context-id>
# Agent reads packet.json and candidate-template.json, writes candidate.json.
kgmaker feature validate --root . --analysis additional-hedge --candidate .kgmaker/analyses/additional-hedge/candidate.json
kgmaker feature apply --root . --analysis additional-hedge --candidate .kgmaker/analyses/additional-hedge/candidate.json
kgmaker feature report --root . --analysis additional-hedge
kgmaker feature status --root . --analysis additional-hedge
kgmaker feature revise --root . --analysis additional-hedge --answers requirements/additional-hedge-answers.json
kgmaker feature compare --root . --analysis additional-hedge --variant no-new-api
kgmaker query --root . --analysis additional-hedge liquidity
```

`--context` may be omitted only when the selected scope has zero or one fresh
compiler context. Multiple module/profile variants fail preparation with the list
of available IDs. The packet records `graph_selection`, and later commands reuse
it. Supplying a different `--scope` or `--context` to validate/apply/report/status
is rejected; prepare a new revision to change the selection. A selected context
that later becomes stale remains visible in packet diagnostics while its compiler
facts are excluded.

`prepare` builds an up-to-date graph **in memory**, preserving existing graph and
semantic files. It reconstructs the syntactic/semantic/Flyway graph and retains
content-validated compiler layers published by explicit `inspect`. Stale layers lose
their compiler facts and remain as diagnostic contexts with an explicit refresh command.
It works without Git, a diff, or a semantic change packet.
Git HEAD is supplemental provenance; working-tree content determines freshness.
A commit-only change with identical sources preserves the packet identity.

Repeated prepare with the same inputs returns the same packet and makes no writes.
Changing sources, requirement, answers, parser version or token budget increments
the revision and archives the previous packet. It never overwrites candidate.json.
The agent must regenerate stale conclusions rather than replacing packet IDs.

`validate` is read-only. Invalid/stale `apply` never writes. Successful apply
atomically replaces only analysis.json (and archives a previous applied revision).
An applied revision cannot be edited in place. `revise` validates explicit question
IDs and decision revisions, preserves the old analysis unchanged and prepares the
next packet. A newly created answers file is included in the refreshed baseline.
The agent must carry forward/recheck conclusions; selective automatic invalidation
is deferred. A retry with identical answers is idempotent.

`compare` returns the chosen stored alternative alongside proposed changes and
questions; it never synthesizes an absent variant. Plain query remains AS_IS only.
`query --analysis ID` includes a specific validated proposal and labels every hit
AS_IS/TO_BE. A stale mixed query returns diagnostics instead of current-looking hits.

`report --format json` emits the stored analysis, completion and stale diagnostics.
Markdown is the default. All report output must be under
`docs/generated/features/`; custom filenames are allowed there. Absolute paths,
traversal and symlink components are rejected. Generated feature reports, including
nested fixture reports, are excluded from graph and packet source inventories.
This prevents report output from becoming independent implementation evidence.

Exit codes: **0** valid processing (including incomplete), **1** operational error,
**2** invalid input/candidate, **3** stale baseline/packet, **4** valid incomplete
result with `--require-complete`. The latter option is available on feature commands;
for apply it does not suppress storage of a valid incomplete candidate. Completion
is always present in successful machine output. A stale report is written with a
prominent warning and exits 3. Existing impact/query commands remain compatible.

## Candidate contract, schema version 1

Start from candidate-template.json and the checked-in
[prepared fixture](../fixtures/feature-analysis/expected/candidate-valid.json).
The fixture has explicit placeholders and is **not** directly applicable to a live
project. Packet envelope fields must be copied from the actual packet.

Required envelope: `schema_version`, `analysis_id`, `revision`, `packet_id`,
`requirement_hash`, `baseline`, `coverage`, `language` (`cs` or `en`). All collections
below are mandatory arrays, even when empty. IDs are unique and use
`analysis:<analysis-id>:<kind>:<name>`; proposals use `proposal:<analysis-id>:...`.
Unknown contract fields are rejected to avoid silently accepting unsupported claims.

| Collection | Item contract |
|---|---|
| requirements | id, text, kind (Goal/InputRequirement/OutputRequirement/BusinessRule/Constraint), source_quote, status (ADDRESSED/OPEN_QUESTION/UNRESOLVED) |
| input_requirements | id, name, requirement_ids, source_ids (real graph IDs), evidence_ids, dependency_ids (input IDs), question_ids; availability, acquisition, usability; verification_scope, next_step, owner_role, transformation; explicit metadata listed below |
| capability_matches | id, entity_ids, requirement_ids, evidence_ids, rationale, limitations, state=AS_IS, method, validity |
| changes | id, requirement_ids, entity_ids, dependency_ids, layer, reason, inputs, outputs, test_impact, state=TO_BE |
| impact_paths | id, entity_ids, edges, weakest_confidence, unresolved_boundary, evidence_ids; exact path returned by directed impact with evidence for every edge source |
| questions | id, text, owner_role, requirement_ids, status (OPEN/ANSWERED), blocking (boolean) |
| assumptions | id, text, requirement_ids, state=UNKNOWN |
| alternatives | id, name, constraints, limitations, proposal_ids, question_ids, requirement_ids |
| acceptance_criteria | id, text, requirement_ids |
| test_plan | id, text, requirement_ids, state (AS_IS/TO_BE), entity_ids, evidence_ids; existing tests require citations |
| evidence | id, source_id, kind, supports, method (EXTRACTED/INFERRED/AMBIGUOUS), confidence (0–1), validity (VALID/STALE/UNRESOLVED), source-specific fields below |

Input metadata: `definition`, `data_type`, `unit`, `currency`, `granularity`, `keys`,
`as_of`, `validity_interval`, `horizon`, `freshness`, `nullable`, `quality`, `fallbacks`.
Use explicit `null` when unknown; keys/quality/fallbacks are arrays of strings when
known and nullable is boolean when known. Other metadata is textual.
Negative lookup requires `search_fingerprint` equal to the packet working-tree
fingerprint and explicit searched scope. Omitted or unsupported sources require
UNKNOWN. DERIVED additionally requires a transformation and nonempty dependency
list; cyclic derivations are rejected.

`proposal` contains only `nodes` and `edges`. Nodes require id, name, kind,
description and state=TO_BE. Edges require source, target, kind and state=TO_BE.
Supported relations: requires_input, satisfies_requirement, reuses_entity,
proposes_change_to, blocked_by, depends_on_decision. Every endpoint must resolve.

`completion` contains processing_status (SEMANTIC_PENDING/PARTIAL/COMPLETE),
decision_readiness (READY/BLOCKED), and pending (array of concrete work items).
COMPLETE rejects pending work, omitted source context and unresolved requirements.
OPEN_QUESTION requirements can be fully processed while business readiness remains
BLOCKED. READY requires complete processing, no assumptions and approval of every
blocking decision. Approval is a declared user answer, not authenticated identity.

### Evidence

For file sources provide `path`, byte `sha256`, and either:

```json
{"location":{"type":"lines","start":3,"end":3},"quote":"exact source substring"}
```

or:

```json
{"location":{"type":"json_pointer","pointer":"/properties/currency/type"},"value":"string"}
```

Workbook evidence uses a hash-bound cell locator and keeps formula text separate
from its cached value:

```json
{"location":{"type":"workbook_cell","sheet":"Scenario","cell":"A1"},"value":{"formula":null,"cached_value":"10","cached_value_freshness":"UNKNOWN"}}
```

Unsupported workbook files use **coverage diagnostics**, not cell evidence. Declared
`.xls` files and OLE compound/BIFF signatures in `.xlsx` candidates are rejected
before the ZIP/XML parser. The bounded header check does not validate Excel data;
malformed `.xls` stays unsupported with `detected_format: UNKNOWN`. Arbitrary file
extensions are not searched for binary spreadsheet signatures.

For example, after `kgmaker feature prepare --root . --requirement requirement.md
--id legacy`, the packet's `coverage.artifact_diagnostics` contains:

```json
{"path":"legacy.xls","code":"BINARY_XLS_UNSUPPORTED","status":"UNSUPPORTED","detected_format":"BIFF","sha256":"<file byte SHA-256>","locator":{"type":"file","path":"legacy.xls"},"extractor":"xls-unsupported-1","scope":"unknown"}
```

The file locator identifies an unparsed artifact; it is not a supported evidence
citation location and cannot prove a cell value, formula or availability. Audit
`coverage_gaps` retain the same records under `ARTIFACT_DIAGNOSTICS`. Workspace
records also carry `repo_id`; production packets filter diagnostics by scope.
Renamed binary `.xlsx` stays in `unsupported_sources`; malformed XLSX parsing also
returns an UNSUPPORTED hash/file-locator diagnostic. `feature-inventory-5`
invalidates older inventory/cache fingerprints; regenerate old packets explicitly.
Oversized spreadsheet files keep unsupported hash-only manifest entries while
remaining excluded from parsing. Their checksums use bounded streaming buffers;
retained diagnostic hashes are rechecked during packet freshness, including in
workspaces. The direct XLSX extractor checks its archive size limit before any
content hashing. Graph/store schemas and the sheet/cell/value citation shape
remain unchanged across these workbook adapter revisions.

`xlsx-offline-3` corrects the bounded formula-reference classifier: `1E10` is a
numeric literal and `LOG10(A1)` references A1 without inventing a LOG10 cell edge.
Double-quoted strings, including escaped quotes, contribute neither cell tokens
nor dynamic/external diagnostics. Literal A1 references, `$` anchors, explicit
sheet qualifiers and bounded A1 ranges (including whitespace around the colon)
are supported; this is not a full Excel
grammar. Shared formulas (including followers), INDIRECT, OFFSET and external
references remain unresolved. 3D sheet, whole-row and whole-column references
produce `XLSX_REFERENCE_FORM_UNSUPPORTED` with the affected sheet/cell in the
graph diagnostic. Unsupported formulas contribute no guessed dependency edges.
Named-range expressions use the same token/boundary rules.
Unicode word and numeric sheet identifiers, and single-quoted sheet names, are
literal qualifiers. A name such as `'INDIRECT(A1)'!B1` is not a dynamic call.
Unrecognized qualifiers produce a boundary for the expression, including an
unmatched sheet separator followed by whitespace; their trailing cell can never
be reinterpreted as local. Whole-row/column forms with spaced colons stay unsupported.

For example, `kgmaker feature prepare --root . --requirement requirement.md
--id scenario` records `coverage.parser_capabilities.workbooks: xlsx-offline-3`.
Formula text and cached values remain separate citation fields with UNKNOWN
freshness; a cached value is not proof of a formula result or runtime availability.
The adapter version participates in workspace cache identity, so earlier v1/v2
dependency results are reparsed; regenerate existing packets explicitly.

Evidence kind must match the packet source manifest. Source and cited location must
exist and the quote/value must match; hash or location errors reject apply.
File SHA-256 uses raw bytes, including CRLF; graph fingerprints separately retain
the legacy scanner's normalized-text hashes. HTML section locators remain unsupported.

REQUIREMENT evidence needs exact `quote` and `sha256` from the original requirement.
HUMAN_DECISION evidence needs `decision_id`, `answer`, `revision`, `approval_status`
matching a supplied packet answer. File kinds are CODE/CONTRACT/SCHEMA/CONFIG/
DOCUMENTATION/WORKBOOK.

Answer file:

```json
{"answers":[{"question_id":"analysis:additional-hedge:question:liquidity","decision_id":"liquidity-definition","answer":"Balance less reserved funds","revision":1,"approval_status":"UNAPPROVED"}]}
```

Approval values are APPROVED/UNAPPROVED/UNKNOWN. A changed decision requires a
higher decision revision. Its status is never inferred from an affirmative sentence.

## Context budget and known limits

The budget estimates source context using UTF-8 bytes / 4; it is not host billing.
The complete metadata/coverage manifest is retained even if it exceeds the budget;
`mandatory_metadata_tokens` reports its initial size estimate. Remaining room is
used for whole source files ranked by path terms. Omitted sources remain visible
and pending, and therefore cannot become a negative availability proof. This is
not a strict cap on total serialized packet bytes. Larger budgets prepare a new
revision without overwriting the previous candidate. Selective resume is future work.

Single-root and explicit multi-repository workspace modes are supported. Hidden/
sensitive paths, symlinks, generated outputs and over-limit files are excluded by
the source inventory; unsupported artifacts remain visible in coverage. General
SQL/interprocedural completeness, non-literal template binding, formula evaluation, selective feature
invalidation and Confluence synchronization are not implemented. `scan`/`update`
remain full syntactic scans; workspace and Flyway caches do not change that fact.
Workspace graph schema v3 preserves compiler symbols, call sites, CFG, evidence and
annotations with repo-qualified identities.

## Host invocation and tests

Run `kgmaker init` to install `kgmaker-analyst` and
`.junie/commands/kgmaker-analyze-feature.md`. Existing files are preserved unless
`--force` is used. Select the custom agent using the host's actual supported UI or
command, or explicitly ask it to follow the installed file. `/kgmaker analyze-feature`
is an intent routing convention, not a guaranteed Copilot-native slash command.
Existing `/kgmaker`, semantic extract and semantic patch flows remain independent.

```bash
python -m pip install -e . pytest==8.3.4
python -m pytest -q
kgmaker scan
kgmaker check
```

Tests cover packet idempotence, source/requirement drift, zero mutation on rejected
apply, proposal isolation, malformed input, fake quotes/hashes/JSON fields/approval,
small-budget behavior, business readiness vs processing, revision history, agent
file preservation and the prepared fixture CLI lifecycle. T001-FA-14/15/24 selective
incremental equivalence, full T001-FA-16 selective conclusions, full cross-layer field proofs T001-FA-01/03/08/09,
approved-methodology T001-FA-20/21 remains outstanding. T001-FA-28–30 are covered
by the explicitly offline fake adapter; no live Confluence host/version or API
credentials were provided, so a real adapter cannot be claimed.

## Implemented field and impact patterns (T001-S02 subset)

`dataflow.py` adds stable path/qualified-owner IDs for Kotlin primary-constructor
fields, simple Java fields/records, TypeScript interfaces/object types and JSON
Schema/OpenAPI JSON properties (with exact JSON pointers). Kotlin functions with
explicit parameter/return types support local numeric/property expressions and
unambiguous direct constructor mappings. Overloaded cross-file calls, control flow,
parameter reassignment, complex expressions and ambiguous type names do not become
proven value edges. Coverage includes parser capabilities and concrete diagnostics.

```bash
kgmaker impact --root . --entity 'data_field:backend/ScenarioCalculator.kt:ScenarioInput.pessimisticDecline' --include-data-flow --format json
```

Changes propagate backwards over derived_from/reads_value and forwards over
maps_to/serialized_as/displayed_in/rendered_in/sent_to/tested_by/documented_by/
writes_value. Only some of these edges are currently extracted automatically;
others may be supplied by a correctly evidenced semantic layer. Traversal returns
shortest paths, the weakest confidence, terminal/external boundaries and depth
truncation. External-system internals are not traversed. Unmapped values are not
proof of no impact. No universal undirected traversal is used.

The fixture explicitly contains `midDecline = input.pessimisticDecline / 2` and a
constructor mapping to ScenarioReport. Prepared expected edges are hand-written,
not generated from the tested extractor. FA-35 directionality is covered; the
complete UI/PDF/SQL/Kafka propagation scenario is still outstanding.

Successful apply writes a per-revision validation receipt containing the candidate
hash before atomically replacing analysis.json. Historical reports verify that
receipt before rendering stale source paths. This detects modified stored output;
it is a local integrity check, not a digital signature or authenticated approval.

## Deterministic data-check

`feature data-check` accepts structured semantic input without a model call. It
uses the same in-memory AS_IS graph, query ranking, directed impact traversal,
packet freshness, feature validator and report renderer as other commands. It
returns a complete **validated but unapplied** candidate and report on stdout;
it does not save files, mutate source/AS_IS, run a shell or execute tests/migrations.

```bash
kgmaker feature data-check --root . --analysis additional-hedge --inputs requirements/additional-hedge-inputs.json --format json
kgmaker feature data-check --root . --analysis additional-hedge --inputs requirements/additional-hedge-inputs.json --format markdown
```

DataRequirementSet version 1 requires `schema_version`, `analysis_id`,
`requirement_hash` (copy from current packet), `requirements`, and `inputs`.
Optional `evidence_references` supplies cited proof sources; in a workspace,
references include `repo_id`. Unsupported fields are rejected.
Requirements contain `id`, `text`, `kind`, `source_quote` present in the exact
requirement; status is assigned by the checker. Optional `source_reference`
contains `path`, `location` and `quote` or `value`, with the existing line/JSON
pointer contract. The checker supplies source hashes and delegates reference
validation to the normal feature validator.

Each input contains `id`, `name`, non-empty `requirement_ids`, and every metadata
field from InputRequirement: `definition`, `data_type`, `unit`, `currency`,
`granularity`, `keys`, `as_of`, `validity_interval`, `horizon`, `freshness`,
`nullable`, `quality`, `fallbacks`. Unknown values are null. Optional fields are
`candidate_entity_ids` (real baseline graph IDs), `owner_role`, `dependency_ids`,
`transformation` and `availability_proof`. Supported proof payloads are documented
in [flyway-workspace-proofs](flyway-workspace-proofs.md). Derivations require dependencies and a transformation;
cycles are rejected by the existing validator. All IDs remain analysis-scoped.

Write the specification before the final prepare, or refresh prepare after writing
it into the source tree. Its requirement_hash is stable under specification-only
changes; answer revisions change it and require semantic rechecking. Refreshing
an unchanged specification does not require repeating LLM decomposition.

The output includes `candidate_sources` with evidence and static impacts,
`ambiguity_queue` for unknown business metadata/equivalence, `business_decisions`,
`data_delivery_gaps`, `coverage_gaps`, `candidate`, `report` and normal validation
status/exit codes. Candidate limits, context omissions, unsupported parsers and
missing availability proofs are coverage gaps, **not confirmed missing data**.
The two report tables distinguish required definitions/decisions from what the
tool cannot verify. Candidate output can be saved under the isolated analysis
folder using JSON processing, then passed to normal validate/apply/report.

Without valid supplied proof, inputs start UNKNOWN/UNASSESSED. Supported proofs
are evaluated by `availability.py` and the shared validator; they can justify
AVAILABLE/PARTIAL or scoped CONFIRMED_MISSING within their exact contract. Name
matches never prove populated or equivalent values. `--require-complete` exits 4
for valid incomplete output. Workspace mode uses the same explicit manifest as
prepare/validate/report; no undeclared checkout is substituted. Flyway/workspace/
scoped proofs are implemented; selective reuse and targeted feature invalidation
remain unfinished. See T003-S02/S07/S10 for the remaining integration.

## Deferred Confluence connection configuration

Live execution is deferred by the user. Configure the connection separately from
an existing offline export in `kgmaker.json` or `.kgmaker/config.json`:

```json
{
  "documentation": {
    "confluence": {
      "directory": "offline-export",
      "connection": {
        "enabled": false,
        "host": "https://confluence.invalid/wiki",
        "api": "cloud-v1",
        "sandbox_space": "KGTEST",
        "auth": {"kind": "bearer", "token_env": "CONFLUENCE_TOKEN"}
      }
    }
  }
}
```

`api` explicitly selects `cloud-v1`, `cloud-v2` or `server-v1`; this is a setting,
not an assertion that the server supports it. Basic auth uses `kind: "basic"`
and adds `username_env`. Configuration stores environment variable names only.
The default is disabled. Even `enabled: true` does not connect: the current
configuration command never executes an adapter.

```bash
kgmaker confluence config --root .
kgmaker confluence config --root . --config-file settings.json
```

The command validates bounded JSON and reports `configured`, `enabled`,
`auth_ready` and `live_status: "NOT_RUN"` without network, child processes or
store writes. `auth_ready` means only that the named environment entries are
non-empty; it does not establish valid credentials or remote authorization.
An explicit missing/invalid file fails without fallback. The first connection
subsection wins (`.kgmaker/config.json`, then `kgmaker.json`); unrelated settings
are skipped and an explicit disabled connection remains authoritative. YAML
export configuration continues to work for the existing offline export path;
this new connection configuration supports JSON only. A live adapter and sandbox
contract run remain deferred work, separate from existing fake boundary tests.
