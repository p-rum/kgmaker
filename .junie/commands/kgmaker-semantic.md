---
description: Run kgmaker semantic extraction independently from implementation work
allowPromptArgument: true
---

Run standalone kgmaker semantic extraction. This command is intentionally separate from feature implementation.

1. Run `kgmaker semantic extract --base HEAD~1` (or use the actual `git merge-base HEAD origin/main` when available). Never pass literal angle-bracket placeholders.
2. Read `.kgmaker/semantic-extract.md` and the referenced JSON input directly from disk.
3. If the mode is `initial`, inspect source files and write the complete `.kgmaker/semantic.json`.
4. If the mode is `incremental`, inspect only changed files and affected graph context, then write `.kgmaker/semantic-patch.json` with the exact `update_id` from the current `.kgmaker/semantic-update.json`.
5. Verify the two update IDs from disk before applying. Run `kgmaker semantic apply`, `kgmaker semantic validate`, and `kgmaker scan` only after they match.
6. Run the relevant tests and summarize extracted or updated relationships, evidence, confidence, and unresolved items.

Do not implement unrelated features, invent relationships, or modify generated graph views by hand. Source code remains authoritative.
