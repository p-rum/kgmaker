# KGMAKER data prerequisite audit

For the intent `/kgmaker check-data`, follow
`.github/agents/kgmaker-data-auditor.agent.md`.

Use feature prepare/data-check/validate/apply/report/revise. Check the supplied
workspace baselines and Flyway targets. Limit model work to requirement meaning
and returned business ambiguities. Never invent observations or approvals.
Separate tool coverage from scoped data gaps; do not edit application code or
execute migrations/tests. If the host does not discover this command, explicitly
open the agent file.


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
