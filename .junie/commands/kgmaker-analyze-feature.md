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

For the KGMAKER PR #5 baseline, scan/hook replace compiler indices and feature
packets rebuild a source-only graph. Until T003-S02 is implemented, inspect saved
compiler context/source freshness before refreshing; do not claim it survives a scan.
