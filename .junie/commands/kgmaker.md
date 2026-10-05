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
6. For semantic relationships affected by the change, determine a real base first: use `git merge-base HEAD origin/main` when that ref exists, otherwise use `HEAD~1`. Never pass angle-bracket placeholders such as `<merge-base>` or `<budget>` to the shell. Run `kgmaker semantic update --base <resolved-base>` once for the packet you are about to process (add a positive `--token-budget N` only when requested). Read `.kgmaker/semantic-update.json` directly after the command. If it reports that an existing patch was discarded, recreate `.kgmaker/semantic-patch.json` from this newly generated packet.
7. Update only affected semantic entries in `.kgmaker/semantic-patch.json`; preserve unrelated entries. Before applying, verify the IDs from disk, not from chat history:

   ```bash
   python -c "import json; u=json.load(open('.kgmaker/semantic-update.json')); p=json.load(open('.kgmaker/semantic-patch.json')); assert p.get('update_id') == u.get('update_id'), f\"patch={p.get('update_id')} packet={u.get('update_id')}\""
   ```

   Only after this check passes, run `kgmaker semantic apply`, `kgmaker semantic validate`, and `kgmaker scan`.
8. Run the focused tests and the full test suite. Report changed files, semantic entries updated, validation results, and any pending or ambiguous semantic work.

Do not invent relationships, credentials, external URLs, or undocumented behavior. Do not edit generated graph views by hand. If the request is only a question, perform the graph/source reconnaissance and answer without modifying files.
