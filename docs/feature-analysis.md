# Feature analysis: implemented foundation and remaining milestones

This page describes implemented behavior. The complete target remains
[implementation-feature-analysis.md](implementation-feature-analysis.md).

## Delivery status

This change delivers the **milestone A foundation and initial milestone B field/impact support**, plus basic host installation,
answer revisions, explicit mixed query and alternative inspection. It does **not**
claim that the full milestone A–E acceptance suite or analytical core A–D is done.

| Area | Implemented | Remaining |
|---|---|---|
| Lifecycle | prepare, validate, apply, report, status, revise, compare | Selective revision packets and dependency invalidation |
| Provenance | Byte SHA-256, exact quoted line ranges, JSON pointer/value, explicit requirement/decision evidence | HTML-section and workbook-cell localization |
| Graph compatibility | Existing version 1 defaults remain; model rejects newer versions | Broader graph/evidence migration with new data-flow model |
| Availability | UNKNOWN and scoped NOT_FOUND_IN_SCOPE; negative searches require complete supplied context and inventory fingerprint | Positive source-path and complete-contract proofs in milestone B |
| Isolation | Proposal namespace, dangling-reference checks, read-only validation, atomic analysis.json replacement | No automatic implementation promotion, by design |
| Budget | Source context selection, full manifest, estimator and omitted-source pending | Relevance by fields/dependencies rather than path keyword ranking |
| Freshness | Full working-tree inventory and deterministic graph fingerprints, no timestamp identity | Selective invalidation; unrelated source changes currently stale the packet |
| Agents | Analyst instructions and JetBrains command template, idempotent init | Richer data-flow routing as milestone B/D matures |
| Reports | Czech/English deterministic sections, delivery table, validated static impact paths, evidence index, stale labels | Richer business prose and full cross-layer coverage |
| Confluence | Existing offline export workflow unchanged | Approved-methodology authority rules, adapter/fake/publish workflow and real integration |

No new dependency, model client, MCP server or network operation is introduced.
The first validator intentionally rejects `AVAILABLE`, `PARTIAL` and
`CONFIRMED_MISSING`, because the required runtime-path/contract proof checker
is not implemented yet. Static impact paths are validated against current directed graph edges. Use `UNKNOWN` and concrete pending work; do not claim a
positive result just to satisfy a schema. AS_IS reuse candidates must be INFERRED
or AMBIGUOUS with source evidence; the tool verifies citations, not arbitrary
natural-language entailment or financial correctness.

## CLI workflow

```bash
kgmaker feature prepare --root . --requirement requirements/new-hedge.md --id additional-hedge --token-budget 8000
# Agent reads packet.json and candidate-template.json, writes candidate.json.
kgmaker feature validate --root . --analysis additional-hedge --candidate .kgmaker/analyses/additional-hedge/candidate.json
kgmaker feature apply --root . --analysis additional-hedge --candidate .kgmaker/analyses/additional-hedge/candidate.json
kgmaker feature report --root . --analysis additional-hedge
kgmaker feature status --root . --analysis additional-hedge
kgmaker feature revise --root . --analysis additional-hedge --answers requirements/additional-hedge-answers.json
kgmaker feature compare --root . --analysis additional-hedge --variant no-new-api
kgmaker query --root . --analysis additional-hedge liquidity
```

`prepare` builds an up-to-date graph **in memory**, preserving existing graph and
semantic files. It works without Git, a diff, or a semantic change packet.
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

Evidence kind must match the packet source manifest. Source and cited location must
exist and the quote/value must match; hash or location errors reject apply.
File SHA-256 uses raw bytes, including CRLF; graph fingerprints separately retain
the legacy scanner's normalized-text hashes. HTML section and workbook locators
are unsupported and rejected, rather than treated as verified.

REQUIREMENT evidence needs exact `quote` and `sha256` from the original requirement.
HUMAN_DECISION evidence needs `decision_id`, `answer`, `revision`, `approval_status`
matching a supplied packet answer. File kinds are CODE/CONTRACT/SCHEMA/CONFIG/
DOCUMENTATION; WORKBOOK is reserved for the later parser.

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

Only one repository root is supported. Hidden/sensitive paths, symlinks, generated
outputs and over-limit files are excluded; unsupported artifacts are inventoried.
The dependency-free scanner remains conservative and full-scan. No field-level
availability claim, mathematical equivalence, complete interprocedural analysis,
Excel evaluation or Confluence synchronization is implemented by this change.

## Host invocation and tests

Run `kgmaker init` to install `kgmaker-analyst` and
`.junie/commands/kgmaker-analyze-feature.md`. Existing files are preserved unless
`--force` is used. Select the custom agent using the host's actual supported UI or
command, or explicitly ask it to follow the installed file. `/kgmaker analyze-feature`
is an intent routing convention, not a guaranteed Copilot-native slash command.
Existing `/kgmaker`, semantic extract and semantic patch flows remain independent.

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
kgmaker scan
kgmaker check
```

Tests cover packet idempotence, source/requirement drift, zero mutation on rejected
apply, proposal isolation, malformed input, fake quotes/hashes/JSON fields/approval,
small-budget behavior, business readiness vs processing, revision history, agent
file preservation and the prepared fixture CLI lifecycle. FA-14/15/24 selective
incremental equivalence, full FA-16 selective conclusions, full cross-layer field proofs FA-01/03/08/09,
XLSX/Confluence FA-20–23/28–30 remain outstanding. No live Confluence host/version or
API credentials were provided, so a real adapter cannot be claimed.

## Implemented field and impact patterns (initial milestone B)

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
