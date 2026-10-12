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
