---
description: Run the kgmaker repository semantic agent for an implementation request
allowPromptArgument: true
---

Run the kgmaker semantic repository workflow for this request:

$prompt

Follow this order:

1. Read `AGENTS.md` and the relevant kgmaker instructions in `.github/copilot-instructions.md`.
2. Run `kgmaker status`. If the graph is missing or stale, run `kgmaker scan`.
3. Read `.kgmaker/GRAPH.md` and query the graph with `kgmaker query` for the request. Verify every important finding in source code.
4. Before implementation, inspect `.github/agents/kgmaker-architect.agent.md` and produce a concise implementation brief covering affected modules, data flows, tests, and uncertain graph findings.
5. Implement the requested change with the repository's existing conventions. Keep source code authoritative over generated graph or documentation claims.
6. For semantic relationships affected by the change, run `kgmaker semantic update --base <merge-base> --token-budget <budget>` when a budget is provided. Otherwise use the default budget. Read `.kgmaker/semantic-update.md` and `.kgmaker/semantic-update.json`. Run this command once for the packet you are about to process; if it reports that an existing patch was discarded, recreate `.kgmaker/semantic-patch.json` from the newly generated packet.
7. Update only affected semantic entries in `.kgmaker/semantic-patch.json`; preserve unrelated entries. Run `kgmaker semantic apply`, `kgmaker semantic validate`, and `kgmaker scan`.
8. Run the focused tests and the full test suite. Report changed files, semantic entries updated, validation results, and any pending or ambiguous semantic work.

Do not invent relationships, credentials, external URLs, or undocumented behavior. Do not edit generated graph views by hand. If the request is only a question, perform the graph/source reconnaissance and answer without modifying files.
