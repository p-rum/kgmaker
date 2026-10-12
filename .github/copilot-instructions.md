# kgmaker repository context

This repository uses kgmaker with GitHub Copilot CLI. `.kgmaker/GRAPH.md` is the generated graph; `.kgmaker/NOTES.md` contains verified semantic notes. Use both to navigate, then verify every conclusion in source. Run `kgmaker scan` after structural changes. Do not treat heuristic call edges as confirmed behavior.

## Before implementation

For every request to add a feature, change behavior, refactor, or modify a cross-cutting area, consult the `kgmaker-architect` custom agent before planning or editing. It must inspect the current graph, query relevant concepts, and verify the likely implementation path in source and tests, then return a concise implementation brief. Treat that brief as required repository context. If custom-agent delegation is unavailable, perform the same read-only reconnaissance directly before editing. Skip only typo-only or formatting-only changes.

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
