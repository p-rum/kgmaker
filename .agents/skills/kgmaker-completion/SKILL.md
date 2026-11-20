---
name: kgmaker-completion
description: Run or resume the KGMAKER repository completion backlog with native host agents, local workflow artifacts, independent review and T045 integration.
---

# KGMAKER completion

Use this repository-only skill when asked to run or resume T052. Read AGENTS.md,
the T052/T045 specifications and the applicable task before dispatch. Use
`kgmaker completion plan --jobs N` in the coordinator checkout to read the
priority order, dependencies and work already attached to PRs. Use the GitHub
connector when available for remote reads. Verify current target SHA independently
of PR metadata, then check actual source, changed paths, acceptance and review
threads. Resolve unknown dependencies with source evidence before dispatch.
A documented MERGED dependency can still lack a required acceptance result.
Check and reconcile the canonical inventory before relying on changed statuses.

## Run work locally

1. Prefer known failures and then unfinished PRs. Reuse their branch and worktree
   when safe and authorized. Skip historical or duplicate PRs only with evidence.
   Never dispatch a shared implementation a second time. Reserve a separate
   worktree per active item. Dispatch independent implementations concurrently
   only after their scopes and planned paths are compatible. Serialize overlapping
   writes and integration. Limit concurrency to the host's actual capacity.
2. In each worktree read `kgmaker workflow list`. Use its existing task if the
   task request names the same registry item. Otherwise create a task with
   `kgmaker task add REQUEST --title TASK-ID --workflow bugfix` for a repair
   or `existing-feature` for planned work. Keep the actual workflow task ID.
   Use `kgmaker completion handoff ID --root WORKTREE --apply` for each role.
   Without `--apply`, it previews the next handoff without writes. Read the
   returned `role`, `packet`, `feedback` and `diagnostic` before dispatch.
3. Invoke the active host's specialist agents with the worktree path, exact task
   ID, requested role, packet, acceptance IDs and scope. The architect records
   analyze and plan, the implementer records the minimal change, and the tester
   records real results. Record artifacts via `kgmaker task record`. Advance only
   after the persisted artifact and transition gates validate. Use trace links
   for requirement, change and test evidence. Verify current source freshness
   when packaging context. Keep missing toolchains and unrun checks explicit.
   If parallel execution is unavailable, continue sequentially. If distinct
   review agents are unavailable, leave the task awaiting independent review.
4. In review, independently delegate a correctness/acceptance review and a
   steelman review to distinct host agents that did not implement the change.
   The steelman compares the smallest sufficient fix, existing functionality,
   unrelated changes and the cost of new abstractions. Ask both to inspect the
   same exact base, head and, for dirty local work, source fingerprint. Keep
   stable IDs, source locations and concrete impacts for all open findings.
   Reject a self-review, stale receipt, missing evidence or duplicate actor.
   Record one existing workflow review artifact containing the combined decision
   and references to both actual host reviews. An unresolved blocking finding
   from either review prevents approval. Agents' role labels and text alone
   are local evidence, not authenticated identities.
5. On failed tests or REQUEST_CHANGES, use the existing bounded transition back
   to implement. The handoff returns exact findings or validation entries from
   the persisted artifact. Send that feedback alongside the new implementation packet.
   Test and review the new revision again. Once the cap is reached, record the
   failure or blocker with its reason. Read the latest task before retrying an
   interrupted handoff. If a process died while holding the shared journal lock,
   verify lock ownership before recovery. Reuse an artifact for its matching revision
   and stop on a competing task update until the current persisted state is read.

## Integration and recovery

- Keep repository write permissions and commit/push authorization separate
  from local work and approval. Use the project code_review agent under T045
  for remote review and any authorized merge. Publish through the permitted
  Git/connector path. Use fresh base/head, ready and mergeable state, passed
  acceptance and required toolchain checks, independent approval, current
  dependencies, clean diff and actual server rules. GH CI can be unavailable
  under T045; concrete failures remain blockers. Do not mark done or merged
  as a substitute for the actual merge receipt. Verify the expected head,
  merge parents, merged state and target ref following T045.
- Update the existing production progress and acceptance inventory plus the
  Czech per-step change record with the actual delivery and verification
  evidence. Replan when the base, PR or source evidence moves. Continue with
  the next eligible item unless every item is complete or concretely blocked.
- Find interrupted work using `git worktree list --porcelain` and
  `kgmaker task list --root WORKTREE`. Resume by pinned task ID using
  `task show`; never recreate it just because HEAD or the profile has changed.
  Record a stopping checkpoint in the existing progress document or change
  record. Include observed target SHA, worktree/task ID, active PRs, artifact
  or test results, blockers and the exact next action. Recheck refs, dirty
  worktrees and accepted artifacts before dispatching further work.
