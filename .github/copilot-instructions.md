# kgmaker repository context

This repository uses kgmaker with GitHub Copilot CLI. `.kgmaker/GRAPH.md` is the generated graph; `.kgmaker/NOTES.md` contains verified semantic notes. Use both to navigate, then verify every conclusion in source. Run `kgmaker scan` after structural changes. Do not treat heuristic call edges as confirmed behavior.

## Before implementation

For every request to add a feature, change behavior, refactor, or modify a cross-cutting area, consult the `kgmaker-architect` custom agent before planning or editing. It must inspect the current graph, query relevant concepts, and verify the likely implementation path in source and tests, then return a concise implementation brief. Treat that brief as required repository context. If custom-agent delegation is unavailable, perform the same read-only reconnaissance directly before editing. Skip only typo-only or formatting-only changes.

For initial agent-authored semantic relationships, use `kgmaker-extract` with `kgmaker semantic prepare`. For changes, run `kgmaker semantic update --base <merge-base> [--token-budget N]`, let the agent write a scoped `.kgmaker/semantic-patch.json`, then run `kgmaker semantic apply`, `kgmaker semantic validate`, and `kgmaker scan`. The token budget limits kgmaker's changed-file context packet; it does not control the host Copilot model's own output accounting. Do not replace unrelated semantic entries. The graph is generated locally and must not contain secrets, credentials, or external links.

## Feature feasibility analysis

For `/kgmaker analyze-feature` intent, follow `kgmaker-analyst` and the implemented
contract in `docs/feature-analysis.md`. Use the isolated `feature` packet lifecycle,
not semantic patches. Keep proposals TO_BE, verify citations and preserve explicit
UNKNOWN/pending states for currently unsupported data-flow proofs. Do not edit
application code during feasibility analysis.

For data prerequisites or "/kgmaker check-data" intent, follow
`kgmaker-data-auditor`. Reuse feature prepare/validate/apply/report, query and
directed impact; restrict model work to requirement meaning and business
ambiguity. Unsupported proofs remain UNKNOWN/pending. This is a data audit,
not authorization to edit application code or run E2E tests.

