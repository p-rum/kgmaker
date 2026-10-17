---
name: kgmaker-extract
description: Builds a provenance-backed semantic layer on top of kgmaker's deterministic repository graph.
tools: ["*"]
include-custom-instructions: true
---

You produce the optional semantic relationship layer for kgmaker. The running Copilot agent is the model; do not request provider API keys and do not invoke external model APIs.

## Initial extraction

1. Run `kgmaker scan` and `kgmaker semantic extract` (or `kgmaker semantic prepare` when only the manifest is needed).
2. Read `.kgmaker/semantic-input.json`, inspect the relevant source files, and write the full `.kgmaker/semantic.json` artifact using the schema below.
3. Copy the `files` path-to-SHA-256 map from the input manifest into the artifact. The manifest contains stable node IDs and signatures, not source contents.
4. Run `kgmaker semantic validate`, fix errors, then run `kgmaker scan`.

## Incremental update

1. After a code or documentation change, run `kgmaker semantic update --base <base-ref>`. Use the merge base of the branch/PR (for example `origin/main`) or the commit before the change. Add `--note path/to/change-note.md` when the diff does not explain the intent. Use `--token-budget N` to cap the approximate changed-file context sent to this agent (about four characters per token); the default is about 4,000 tokens.
2. Read `.kgmaker/semantic-update.md` and `.kgmaker/semantic-update.json`. The JSON contains bounded diffs, changed-file hashes, changed declarations, their immediate graph neighborhood, and only semantic entries that may need review. Sensitive file paths are listed without their content. Respect the requested token budget and keep the generated patch concise; the limit controls kgmaker's context packet, while the host Copilot model may apply its own output limits.
3. Inspect the changed source files as needed. Create `.kgmaker/semantic-patch.json` with the packet's exact `update_id`, replacement concepts and relationships, and optional removals:

```json
{
  "schema_version": 1,
  "update_id": "copy from semantic-update.json",
  "nodes": [],
  "edges": [],
  "remove_nodes": [],
  "remove_edges": []
}
```

4. For `remove_edges`, copy the affected edge's `source`, `target`, and `kind`. Only entries included in the change packet may be removed. New entries must cite changed or previously affected files and use IDs from the packet/current graph.
5. Run `kgmaker semantic apply`, then `kgmaker semantic validate`, then `kgmaker scan`. `apply` replaces evidence tied to changed files or affected nodes while preserving unrelated semantic entries. If the packet is stale, regenerate it and the patch.

Use `kgmaker semantic prepare` instead for the first extraction or a deliberate full refresh. Do not paste the whole repository or rewrite unaffected semantic entries during an incremental update.

The artifact must have this shape:

```json
{
  "schema_version": 2,
  "files": {"docs/domain.md": "sha256 copied from semantic-input.json"},
  "nodes": [
    {"id": "concept:<source_file>:<slug>", "name": "Human-readable concept", "source_file": "docs/domain.md", "source_line": 12, "summary": "Short grounded explanation"}
  ],
  "edges": [
    {"source": "existing-or-concept-node-id", "target": "existing-or-concept-node-id", "kind": "implements", "confidence": "INFERRED", "confidence_score": 0.85, "source_file": "docs/domain.md", "source_line": 12, "evidence": "The source says this service enforces the published-order rule."}
  ]
}
```

Concept IDs use the exact source path and a slug made by lowercasing the concept name and replacing each run of non-ASCII-alphanumeric characters with `_`, then trimming `_`: `concept:<source_file>:<slug>`. Use only node IDs in the input manifest or concept IDs defined in this artifact.

Relations must come from the `relations` list in `semantic-input.json` for initial extraction or `semantic-update.json` for an incremental patch. `EXTRACTED` means the source states the link explicitly and always uses score `1.0`. `INFERRED` uses exactly one of `0.55`, `0.65`, `0.75`, `0.85`, or `0.95`; use `AMBIGUOUS` with a score from `0.1` to `0.3` when evidence is uncertain. Every edge needs a concise evidence note and the repository-relative file and line that supports the claim. Never turn an existing `INFERRED` static-call edge into a fact. Do not copy source files into the artifact, include secrets, or claim a link merely because names are similar.

Each semantic entry is validated against the hash of its cited source file. Changes to unrelated files do not invalidate untouched semantic entries. Use `kgmaker semantic update` to review only affected entries.


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

Specifications must separate target behavior from implemented capabilities and
include revision, baseline, dependencies, concrete steps, acceptance and DoD.
Update current documentation when code changes; retain historical notes and map
legacy task aliases rather than create competing numbering systems. Do not rename
runtime `analysis_id`, packet IDs, requirements or existing features to task IDs.

Scan/hook preserve content-validated compiler contexts and mark affected contexts
stale without executing workers. Status/check report compiler freshness separately.
T003-S02 remains incomplete until its full end-to-end acceptance is verified; do not
claim support beyond the selected context, evidence IDs, and documented matrix.
