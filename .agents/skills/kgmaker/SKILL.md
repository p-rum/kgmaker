---
name: kgmaker
description: Repository-aware implementation and semantic knowledge-graph workflow for kgmaker projects. Use when the user invokes /kgmaker or $kgmaker, asks for a new implementation, needs architecture context, or wants the semantic graph updated after code changes.
---

# kgmaker semantic repository agent

Use this skill as the repository-aware agent for implementation requests. Treat deterministic source code as authoritative and the generated graph as a navigation index.

## Workflow

1. Read `AGENTS.md`, `.github/copilot-instructions.md`, and the relevant custom-agent instructions.
2. Run `kgmaker status`; run `kgmaker scan` if the graph is missing or stale.
3. Read `.kgmaker/GRAPH.md`, then use `kgmaker query "<request terms>"` to locate relevant files and declarations. Verify graph findings in source.
4. Before editing, map the request to existing modules, contracts, data flows, persistence/messaging/API boundaries, tests, and likely documentation impact. Treat heuristic `calls` edges as leads.
5. Implement the requested change using existing conventions. Keep generated graph files and Confluence HTML read-only inputs out of hand edits.
6. If code or documentation changes affect semantic relationships, prepare a bounded update:

   ```bash
   kgmaker semantic update --base <merge-base> --token-budget <N>
   ```

   Omit `--token-budget` when no explicit limit is requested. Read `.kgmaker/semantic-update.md` and `.kgmaker/semantic-update.json`; inspect only the changed files and affected graph neighborhood first.
7. Write a scoped `.kgmaker/semantic-patch.json`, run `kgmaker semantic apply`, `kgmaker semantic validate`, and `kgmaker scan`. Preserve unrelated semantic nodes and edges.
8. Run focused tests plus the full test suite. Summarize implementation, graph changes, validation, and pending semantic work.

## Truth and safety rules

- Current source code wins over stale generated views and local Confluence assertions for implementation facts.
- Do not invent calls, dependencies, endpoints, events, database relations, credentials, or external URLs.
- Business knowledge that cannot be verified statically remains documented context; do not label it false.
- Never rewrite source HTML, Draw.io files, images, or generated graph views by hand.
- If the request is a question rather than an implementation, perform read-only reconnaissance and answer without changing files.

## Invocation

JetBrains custom slash command:

```text
/kgmaker <implementation request>
```

Standard Agent Skills invocation:

```text
$kgmaker <implementation request>
```
