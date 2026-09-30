# Project scope

kgmaker is a custom, repository-local knowledge graph tool designed specifically for GitHub Copilot CLI.

## Goals

- Build and refresh a navigable graph of files, symbols, and relationships.
- Put useful repository context into Copilot CLI sessions through native repository hooks.
- Keep documentation, prompts, hook configuration, and the implementation in the same repository.
- Offer an optional GitHub Copilot custom agent that users can adapt or pair with their own agents.
- Offer an optional agent-authored semantic layer, separate from deterministic source extraction and validated against stable graph IDs and file hashes.
- Keep graph generation local, inspectable, and independent of model API keys.

## Out of scope

- MCP server or MCP-based runtime.
- Model-provider abstraction, API-key management, or remote inference backends.
- Installation into multiple unrelated agent products.
- External graph database or hosted service.
- External URLs in generated graph content.

## Initial implementation

The CLI scans Python, Java, Kotlin, JavaScript, TypeScript, Go, Rust, Markdown, reStructuredText, SQL, YAML, properties, and OpenAPI JSON. It creates file/declaration nodes plus database tables/columns, JPA mappings, Kafka topics, API endpoints, and TypeScript file-based routes. Copilot CLI receives a compact context at session start. The optional `kgmaker-extract` agent can create concepts and semantic links to stable structural nodes; per-file hashes preserve valid semantics when unrelated files change. `kgmaker semantic update` prepares a focused Git-diff packet for changed files, nearby graph nodes, and affected semantic entries; `--token-budget N` bounds the changed-file context using an approximate four-characters-per-token estimate. The agent returns a scoped patch that kgmaker validates and merges. This agent workflow uses the host Copilot session and does not add a model API client to kgmaker.

The index is a navigation aid rather than a substitute for source inspection. Ambiguous references are omitted and heuristic relationships are labeled as such. Kotlin, SQL, OpenAPI YAML, and framework integration are supported with conservative pattern-based parsing, not full language grammars.

## Graph workflows

`kgmaker impact FILE` walks reverse import relationships and name-based call candidates to show likely dependents of changed files. Import edges are path-resolved; call edges remain heuristic. `kgmaker scan` and `kgmaker docs` generate `.kgmaker/GRAPH.md` (readable repository map with a GitHub-renderable Mermaid architecture diagram) and `.kgmaker/GRAPH.mmd` (standalone Mermaid source). `kgmaker check` rebuilds the graph in memory and verifies both committed views, so GitHub Actions can reject stale documentation without access to the ignored local JSON index. `build` and `update` currently perform a full scan; incremental parsing and rename detection remain future work.
