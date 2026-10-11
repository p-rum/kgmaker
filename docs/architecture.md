# Architecture

kgmaker has four small layers:

1. `scanner.py` walks the repository, skips generated and sensitive paths, and extracts files, declarations, local imports, and conservative call candidates.
2. `domain.py` extracts PostgreSQL schema objects, Kotlin/JVM persistence links, Kafka topics, service/API references, OpenAPI endpoints, and TypeScript app routes.
3. `model.py` holds stable node and edge records.
4. `semantic.py` prepares stable node inventories, tracks source hashes per file, prepares Git-diff update packets with a configurable approximate token budget, validates scoped agent patches, and merges only affected changes while preserving unrelated semantics.
5. `store.py` writes the machine-readable graph, generated Markdown architecture documentation with an embedded Mermaid view, a standalone Mermaid diagram, and compact session context.
6. `cli.py` exposes `init`, full-scan `build`/`update`, `scan`, local `status`, deterministic CI `check`, `impact`, `query`, `docs`, semantic prepare/update/apply/validation, and the Copilot hook command. Semantic update packets and hook context accept an approximate token budget.
7. `confluence.py` ingests an optional local multi-file Confluence HTML export using structural parsing, resolves internal links and attachments, parses Mermaid and Draw.io/XML diagrams deterministically, caches artifact hashes, merges documentation evidence into the unified graph, and validates claims against the code graph. The source code is authoritative; contradictions are retained as evidence and rendered to a Markdown report.

The local index is built from repository source. No source files are sent to a service by kgmaker. The Copilot hook reads the index generation from the local process and writes JSON context to standard output. Graph JSON stays ignored by Git; `.kgmaker/GRAPH.md`, `.kgmaker/GRAPH.mmd`, and `.kgmaker/NOTES.md` may be shared if the repository wants them committed. `kgmaker scan --no-docs` updates only the machine index; `kgmaker docs` can regenerate both views later. `kgmaker semantic update --token-budget N` limits the changed-file context packet using a conservative character-to-token estimate; it cannot control the separate token accounting of the host Copilot model. `kgmaker check` compares fresh Markdown and Mermaid renders against the committed snapshots and can run in CI without the local JSON index.

Confluence exports are optional and read-only. `kgmaker docs check --confluence-dir PATH` performs deterministic ingestion first, then compares assertions to current code. Verified code facts use `VERIFIED_BY_CODE`; business or external-system claims that static analysis cannot establish remain `NOT_VERIFIABLE_FROM_CODE` and are not reported as lies. The cache stores per-artifact SHA-256 values and `CodeEntity → DocumentationAssertions` reverse links so later code changes can revalidate affected documentation.

## Relationship confidence

- `contains` is a structural edge from a file to a declaration found in that file.
- `imports` is an internal path match from a parsed import statement. Ambiguous basename matches are omitted.
- `calls` is a name-based candidate only when there is a single matching declaration elsewhere. It is never proof that the call resolves to that declaration.
- `defines_table`, `contains_column`, and `references_table` come from SQL DDL; JPA and Spring Data edges come from annotations and repository generics.
- `consumes`, `produces`, and `configures_topic` come from Kafka annotations, client calls, or explicit configuration values.
- `declares_endpoint` and `calls_endpoint` come from Spring/Ktor annotations, common HTTP client calls, or OpenAPI paths. Matching method/path pairs share one endpoint node.
- `defines_route` comes from TypeScript/JavaScript `app/` or `pages/` file conventions.
- Agent-authored edges carry `EXTRACTED`, `INFERRED`, or `AMBIGUOUS` confidence, a score, a source file/line, an evidence note, and the hash of the cited file in the artifact's file map. Changing an unrelated file leaves the edge valid. Changing its cited file marks that evidence stale; `semantic update` asks Copilot to review only changed files, their nearby graph context, and affected semantic entries. The patch is scoped by an update ID and cannot remove unrelated entries.

These are source-pattern parsers, not Kotlin/TypeScript compilers, SQL engines, or complete YAML parsers. Dynamic URLs, indirect topic names, custom annotations, complex OpenAPI documents, and generated schemas may be missed. The `kgmaker` Copilot custom agent can explain behavior from source and keep semantic notes in `.kgmaker/NOTES.md`.

## Hook lifecycle

The generated repository hook subscribes to Copilot CLI `sessionStart`. It refreshes the graph and returns `additionalContext`. A failed scan returns empty context and a diagnostic on standard error, allowing the Copilot session to continue.

## Extension points

Add language-specific declaration/import extraction in `scanner.py`. Keep new edge types explicit about their evidence and confidence. Add renderers or graph storage backends only when there is a concrete user need; the current data contract is deliberately plain JSON and requires no database.

## Isolated feature-analysis foundation

`analysis_model.py` defines the versioned JSON envelope, safe paths and atomic
writes. `feature.py` builds an in-memory graph and source manifest, fingerprints
working-tree content and manages stable packets, applied revisions and answers.
`analysis_validation.py` validates references, exact citations, proposal isolation
and conservative availability/completion constraints. `analysis_report.py` renders
Czech/English reports; `feature_cli.py` adds lifecycle commands without changing
legacy semantic/impact flows. `analysis_agent.py` owns installable host templates.

The AS_IS graph and semantic artifacts are never written by feature commands.
Analysis history lives under `.kgmaker/analyses/<id>/`; report output is restricted
to `docs/generated/features/` and excluded from scanning. Source hashes use raw
bytes; graph identity removes timestamps. This first version intentionally uses
full scans and whole-packet invalidation. See [the current contract](feature-analysis.md)
for outstanding proof checkers and the mandatory-manifest budget exception.

`dataflow.py` contributes field nodes and conservative local Kotlin value edges to
the existing graph. Typed impact follows dependency-specific direction and stops
at external-system boundaries. Feature candidates may cite only exact computed
paths with source evidence; arbitrary agent-authored paths are rejected. This is
initial milestone B support, not complete cross-layer or availability resolution.
