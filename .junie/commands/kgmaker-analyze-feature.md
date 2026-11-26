# KGMAKER feature analysis

For the intent `/kgmaker analyze-feature`, follow
`.github/agents/kgmaker-analyst.agent.md`. Preserve the original requirement,
prepare the feature packet, verify sources, write candidate.json, validate, apply,
and report. Keep TO_BE proposals isolated. Do not invoke semantic apply or change
application code. Host command discovery depends on the installed JetBrains agent;
when unavailable, explicitly open and follow the analyst instructions.


## Task identity, filenames and documentation

Read project `AGENTS.md` and `docs/tasks/README.md` when present before writing
implementation specifications or changing a feature. In KGMAKER these are the
canonical project rules. Preserve existing user project rules and runtime analysis IDs.

Use the assigned task ID exactly as provided, preserving its letters, hyphens,
digits, case, and leading zeros. Begin the task title with that ID, then append
a hyphen and a concise, descriptive English name, for example
`ABC-007-fix-empty-input`. Use the same form for the filename stem when writing a
task specification. If no task ID has been assigned, ask for it before naming
the task. Keep revisions of an existing task in its existing file.

For PR change notes, follow the target project's conventions and include
task/acceptance IDs, actual changes, compatibility, real validation results and
unfinished scope.

Every implementation step, including fixes, refactors and integrations, must
have its own traceable entry in the PR's change note with Task/Step/AC IDs,
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
Update current documentation when code changes and retain historical notes and
legacy task aliases. Preserve runtime `analysis_id`, packet IDs, requirements
and existing feature names.

For the KGMAKER PR #5 baseline, scan/hook replace compiler indices and feature
packets rebuild a source-only graph. Until T003-S02 is implemented, inspect saved
compiler context/source freshness before refreshing; do not claim it survives a scan.

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
