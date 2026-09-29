# Architecture

kgmaker has four small layers:

1. `scanner.py` walks the repository, skips generated and sensitive paths, and extracts files, declarations, local imports, and conservative call candidates.
2. `domain.py` extracts PostgreSQL schema objects, Kotlin/JVM persistence links, Kafka topics, service/API references, OpenAPI endpoints, and TypeScript app routes.
3. `model.py` holds stable node and edge records.
4. `store.py` writes the machine-readable graph and a readable Markdown map, and prepares a compact session context.
5. `cli.py` exposes `init`, `scan`, `status`, `query`, and the Copilot hook command.

The local index is built from repository source. No source files are sent to a service by kgmaker. The Copilot hook reads the index generation from the local process and writes JSON context to standard output. Graph JSON stays ignored by Git; `.kgmaker/GRAPH.md` and `.kgmaker/NOTES.md` may be shared if the repository wants them committed.

## Relationship confidence

- `contains` is a structural edge from a file to a declaration found in that file.
- `imports` is an internal path match from a parsed import statement. Ambiguous basename matches are omitted.
- `calls` is a name-based candidate only when there is a single matching declaration elsewhere. It is never proof that the call resolves to that declaration.
- `defines_table`, `contains_column`, and `references_table` come from SQL DDL; JPA and Spring Data edges come from annotations and repository generics.
- `consumes`, `produces`, and `configures_topic` come from Kafka annotations, client calls, or explicit configuration values.
- `declares_endpoint` and `calls_endpoint` come from Spring/Ktor annotations, common HTTP client calls, or OpenAPI paths. Matching method/path pairs share one endpoint node.
- `defines_route` comes from TypeScript/JavaScript `app/` or `pages/` file conventions.

These are source-pattern parsers, not Kotlin/TypeScript compilers, SQL engines, or complete YAML parsers. Dynamic URLs, indirect topic names, custom annotations, complex OpenAPI documents, and generated schemas may be missed. The `kgmaker` Copilot custom agent can explain behavior from source and keep semantic notes in `.kgmaker/NOTES.md`.

## Hook lifecycle

The generated repository hook subscribes to Copilot CLI `sessionStart`. It refreshes the graph and returns `additionalContext`. A failed scan returns empty context and a diagnostic on standard error, allowing the Copilot session to continue.

## Extension points

Add language-specific declaration/import extraction in `scanner.py`. Keep new edge types explicit about their evidence and confidence. Add renderers or graph storage backends only when there is a concrete user need; the current data contract is deliberately plain JSON and requires no database.
