# Architecture

kgmaker has four small layers:

1. `scanner.py` walks the repository, skips generated and sensitive paths, and extracts files, declarations, local imports, and conservative call candidates.
2. `model.py` holds stable node and edge records.
3. `store.py` writes the machine-readable graph and a readable Markdown map, and prepares a compact session context.
4. `cli.py` exposes `init`, `scan`, `status`, `query`, and the Copilot hook command.

The local index is built from repository source. No source files are sent to a service by kgmaker. The Copilot hook reads the index generation from the local process and writes JSON context to standard output. Graph JSON stays ignored by Git; `.kgmaker/GRAPH.md` and `.kgmaker/NOTES.md` may be shared if the repository wants them committed.

## Relationship confidence

- `contains` is a structural edge from a file to a declaration found in that file.
- `imports` is an internal path match from a parsed import statement. Ambiguous basename matches are omitted.
- `calls` is a name-based candidate only when there is a single matching declaration elsewhere. It is never proof that the call resolves to that declaration.

The `kgmaker` Copilot custom agent can explain behavior from source and keep semantic notes in `.kgmaker/NOTES.md`. Static indexing does not try to infer business meaning from names.

## Hook lifecycle

The generated repository hook subscribes to Copilot CLI `sessionStart`. It refreshes the graph and returns `additionalContext`. A failed scan returns empty context and a diagnostic on standard error, allowing the Copilot session to continue.

## Extension points

Add language-specific declaration/import extraction in `scanner.py`. Keep new edge types explicit about their evidence and confidence. Add renderers or graph storage backends only when there is a concrete user need; the current data contract is deliberately plain JSON and requires no database.
