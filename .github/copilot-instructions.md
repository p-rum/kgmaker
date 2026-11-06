# kgmaker repository context

This repository uses kgmaker with GitHub Copilot CLI. `.kgmaker/GRAPH.md` is the generated graph; `.kgmaker/NOTES.md` contains verified semantic notes. Use both to navigate, then verify every conclusion in source. Run `kgmaker scan` after structural changes. Do not treat heuristic call edges as confirmed behavior.

## Before implementation

For every request to add a feature, change behavior, refactor, or modify a cross-cutting area, consult the `kgmaker-architect` custom agent before planning or editing. It must inspect the current graph, query relevant concepts, and verify the likely implementation path in source and tests, then return a concise implementation brief. Treat that brief as required repository context. If custom-agent delegation is unavailable, perform the same read-only reconnaissance directly before editing. Skip only typo-only or formatting-only changes.

Use `kgmaker task add` for durable multi-role work. The orchestrator advances the task through analyze, plan, implement, test, and review; each role reads a bounded `kgmaker task context` packet and records a validated artifact. Run `kgmaker memory recall` before implementation and capture a validated implementation episode before the final scan.

For initial agent-authored semantic relationships, use `kgmaker-extract` with `kgmaker semantic prepare`. For changes, run `kgmaker semantic update --base <merge-base>`, let the agent write a scoped `.kgmaker/semantic-patch.json`, then run `kgmaker semantic apply`, `kgmaker semantic validate`, and `kgmaker scan`. Do not replace unrelated semantic entries. The graph is generated locally and must not contain secrets, credentials, or external links.

Local Confluence HTML is an optional, read-only knowledge source. Use `kgmaker docs check --confluence-dir <path>` for documentation validation. When documentation conflicts with deterministic code facts, code wins and the conflict is recorded in `docs/generated/confluence-inconsistencies.md`.

For `/kgmaker analyze-feature` intent, use the `kgmaker-analyst` instructions and
isolated `feature` packets. Supported static data-flow paths are not runtime
availability proofs. Do not use semantic apply for feature candidates.

For data prerequisites or "/kgmaker check-data" intent, use kgmaker-data-auditor.
Reuse feature prepare/validate/apply/report, query and directed impact commands.
Limit model work to requirement meaning and business ambiguity; preserve
UNKNOWN/pending for unsupported proofs. Do not edit application code in an audit.


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

## Výslovná konvence T004 a jeho atomických úkolů (2026-10-20)

Na požadavek uživatele mají atomické implementační úkoly T005–T044 soubor
`docs/tasks/T-<NNN>_<kebab-case-slug>.md`, např. `T-005_add-view-model.md`.
Je to stejná globální číselná řada (T-005 = T005), nikoli nový namespace.
Nadřazený plán zůstává `docs/tasks/4_addHighLevelProjectViews.md`.
Každý podúkol obsahuje podrobný rozsah, vlastní acceptance/testy, dependencies,
přesnou větev `feat/t<NNN>-<slug>` a povinnost samostatného push/PR.
Tato konvence má pro tento balík přednost před staršími naming odstavci
i jejich kopiemi v agent templates. Historické T001–T003 soubory se nemění.
Další ID alokuj nad maximem všech formátů v registru/main/open PRs; mezery nerecykluj.
Change notes nadále používají nezávislou řadu `<N>_<lowerCamelCase>.md`.


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
