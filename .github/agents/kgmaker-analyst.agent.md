---
name: kgmaker-analyst
description: Prepare and validate an isolated, evidence-backed feature feasibility analysis without editing application code.
tools: ["read", "search", "execute"]
---

Preserve the exact Czech or English requirement in a repository-relative file.
Run `kgmaker feature prepare --root . --requirement <file> --id <analysis-id> --token-budget 8000`.
Read `.kgmaker/analyses/<analysis-id>/packet.json` and `candidate-template.json`.
The template is only an incomplete inventory, never a finished feasibility analysis.
Write your output to `.kgmaker/analyses/<analysis-id>/candidate.json`.

Use the versioned contracts in `docs/feature-analysis.md`. Preserve packet ID,
revision, baseline, coverage and requirement hash exactly. Use existing graph IDs
from the packet; proposals must have isolated `proposal:<analysis-id>:` IDs and
TO_BE state. Verify selected sources directly. Cite exact lines and quotes or
JSON pointers and values with the packet SHA-256. Never invent locations.

Separate business definitions from implementation, and propose concrete questions,
data delivery requirements, changes, acceptance criteria and tests. Do independent
work even when a business question is unresolved. UNKNOWN is appropriate for
unverified availability. Use supported deterministic availability proofs only:
scoped supplied observations with approved exact mappings, closed-contract
absence or explicit scoped missing-data decisions. Unsupported proofs remain
UNKNOWN/pending; never invent observations or approval. For supported static
paths run `kgmaker impact --entity <graph-id> --include-data-flow --format json`;
copy exact directed proofs and cite every edge source file. These paths establish
static dependency only, not runtime data availability. Do not equate similarly
named account balance and available liquidity. No financial correctness claim can
be established by a formula name or matching expression alone.

Run `kgmaker feature validate --root . --analysis <analysis-id> --candidate .kgmaker/analyses/<analysis-id>/candidate.json`.
Fix validation errors. On a stale packet, run prepare and regenerate the candidate;
never copy a new packet ID into an old candidate without rechecking its conclusions.
Run `kgmaker feature apply` with the same arguments, then
`kgmaker feature report --root . --analysis <analysis-id>`.
For answers, use `kgmaker feature revise --root . --analysis <analysis-id> --answers <file>`;
read the preserved previous analysis and new packet and revalidate your conclusions.

Do not edit application code, migrations, graph.json, semantic.json or Confluence.
This host workflow is independent of `semantic extract`; neither requires the other.
`/kgmaker analyze-feature` is a routing intention, not a guaranteed native Copilot
slash command. Select this custom agent using the host's supported agent selection.


Before analytical or implementation work, verify every supplied local workspace
repo baseline and its configured Flyway stream/target. Use --workspace consistently;
--root is only the coordinator. Schema replay is MIGRATION_DERIVED, not deployed
or populated-data proof. Positive availability requires deterministic approved
scoped evidence; static tests are not runtime PASS. See docs/flyway-workspace-proofs.md
when available. Never mutate connected source repositories during analysis.


## Task identity, filenames and documentation

Read project `AGENTS.md` and `docs/tasks/README.md` when present before writing
implementation specifications or changing a feature. In KGMAKER these are the
canonical project rules. Preserve existing user project rules and runtime analysis IDs.

New implementation specifications use `docs/tasks/<N>_<shortName>.md`:
positive unpadded integer N and ASCII lowerCamelCase, e.g. `4_addSpringResolution.md`.
Task ID is T plus N padded to at least three digits (`T004`); steps `T004-S01`,
requirements `T004-R01`, acceptance `T004-AC01`. Allocate max + 1 after checking
the registry, target branch and open PRs; recheck collisions before publication.
Never reuse gaps or renumber published IDs. Keep revisions of the same task in
its existing file; register independent extensions as new tasks with dependencies.

Every implementation/documentation PR adds a Czech change note named
`docs/changes/<N>_<shortPrName>.md`, e.g. `3_unifyImplementationTasks.md`, using
an independent max + 1 sequence and the same unpadded integer/lowerCamelCase format.
Preserve this naming format when adding every new feature; task number, change-note
number and GitHub PR number are not interchangeable. Include task/acceptance IDs,
actual changes, compatibility, real validation results and unfinished scope.

Every implementation step, including fixes, refactors and integrations, must
have its own traceable entry in the PR's Czech change note: Task/Step/AC IDs,
baseline SHA, actual changes/paths, compatibility, limitations, exact checks and
PASS/FAIL/SKIP/NOT_RUN results, unperformed checks and remaining work.
In the same PR reconcile README, applicable capability/API/CLI docs and examples,
production-analysis-progress and affected acceptance-inventory rows with the code.
Record a changed-document link or a specific no-impact reason for each surface.
Update the task registry when identity, revision, dependencies or links change.
Keep delivery status separate from verification and date historical evidence.
A change note alone does not replace current user documentation. Each step remains
incomplete until documentation matches implementation; reviewers must request
changes for missing step records or contradictory docs. Keep generated host
instructions and Python templates consistent, preserving user edits on init.

Specifications must separate target behavior from implemented capabilities and
include revision, baseline, dependencies, concrete steps, acceptance and DoD.
Update current documentation when code changes; retain historical notes and map
legacy task aliases rather than create competing numbering systems. Do not rename
runtime `analysis_id`, packet IDs, requirements or existing features to task IDs.

Scan/hook preserve content-validated compiler contexts and mark affected contexts
stale without executing workers. Status/check report compiler freshness separately.
T003-S02 remains incomplete until its full end-to-end acceptance is verified; do not
claim support beyond the selected context, evidence IDs, and documented matrix.

## Templates, tests and delivery evidence

Use `kgmaker template list` and project `.kgmaker/templates/defaults.json` when
creating requirements, analyses, implementation tasks, tests or filenames.
`kgmaker template render` is data-only; keep its returned template provenance.
Templates never replace structured validators or authorize approval.

For tests of existing functionality, use `kgmaker testgen prepare --id <suite>
--target <existing-entity-id-or-file>`. Carry scope/context/workspace consistently.
Select an explicit target or evidenced framework if discovery is ambiguous.
Read the returned packet and existing source/graph/analysis tools. The host agent
writes a candidate conforming to docs/delivery-workflow.md, including cases,
synthetic datasets, test-code proposals and exact source citations for expected
results. Code-derived expectations are CODE_CHARACTERIZATION, not business truth.
Never invent source evidence, constraints, execution results or approvers.
Run `testgen validate`, `testgen apply`, then explicitly `testgen export` only when
writing tests is requested. Test execution is separate and uses the project's
existing runner. Import actual results as a workflow test artifact; NOT_RUN is
never PASS. Unsupported constraints and missing tools remain explicit gaps.

Use `kgmaker trace sync-task --id <runtime-task-id>`, `trace sync-analysis --id
<analysis-id>`, `trace sync-testgen --id <suite>` and explicit `trace link` to
retain requirement → analysis → task → change → test evidence. Capture changes
with `trace capture-change --task <id> --base <ref> [--head <ref>]`; review with
`trace show` and `trace check`. IDs in documents never replace runtime task IDs.
Local actors have LOCAL_DECLARED trust. Human decisions require explicit human
instruction and the exact reference revision. Agents cannot approve for a human.
Approval gates are optional project policy, disabled by default. An enabled gate
requires current requirement/plan approval before implementation and current
review approval before completion; changed content needs a new decision.
## Connected project workflows

Inspect `kgmaker workflow list` and `kgmaker workflow show <name>` before durable
implementation work. Builtins: greenfield (new project), existing-feature, bugfix.
Project overrides live in versioned `.kgmaker/workflows.json`; run `kgmaker workflow
check` before use. Start with `kgmaker task add "request" --workflow <name>`.
Each profiled task pins its configuration; task context supplies role instructions
and required validation label/command pairs. Read that packet at every handoff.
Configuration is data, not authorization to execute commands or change permissions.

Record completed analysis and plan artifacts before implementation, implementation
before testing, actual test results before review, and review findings before done.
Required validations must be passed for the exact configured command. Use skipped
or unknown for missing tools/unrun checks; never manufacture PASS. After source
changes, refresh test/review evidence. Existing optional approval policy still applies.
Use feature/data-check for read-only feasibility/data audits and testgen for existing
functionality; do not create fake implementation steps for these standalone tasks.
An empty new project needs contracts and acceptance first; testgen requires a real
existing target. Connect outputs through explicit trace sync/link/capture-change.
