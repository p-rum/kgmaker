# kgmaker

**A local knowledge graph for GitHub Copilot CLI.** kgmaker maps files, declarations, imports, database tables, Kafka topics, API endpoints, frontend routes, and likely cross-file calls, then gives Copilot a compact repository map at the start of each session. The index runs locally and uses only Python's standard library.

kgmaker is designed for one host: GitHub Copilot CLI. Repository hooks handle automatic refresh and context. A repository custom agent can enrich architectural explanations using Copilot itself. There is no model API key, provider configuration, MCP server, or external graph service.

## Requirements

- Python 3.11 or newer
- GitHub Copilot CLI for automatic Copilot integration

## Install

From the repository root:

```bash
python -m pip install -e .
kgmaker init
kgmaker scan
```

`kgmaker init` creates repository-level Copilot hooks, knowledge-graph and read-only architecture agents, repository instructions, and a local-index ignore rule. The instructions tell Copilot to consult `kgmaker-architect` before every substantive implementation request; it checks the graph and relevant source/tests, then gives the primary agent a focused implementation brief. Existing files are preserved. Pass `--force` only when you want to replace the kgmaker-managed Copilot files.

Restart Copilot CLI after installing the hook. Each new session refreshes the graph and injects a compact map as `additionalContext`.

## Commands

Offline production classification, graph schema v2 and scoped evidence views are
documented in [production scope](docs/production-scope.md). Use `kgmaker project
classify --root . --explain --format json`, `kgmaker graph rank --profile execution
--explain` and `kgmaker coverage report --format json`. Default query, generated
architecture views and hook context use production scope; `query --scope all`
includes unknown/test inventory. These are partial source-only analyses, not
compiler-resolved calls or CFG. See [implementation progress](docs/production-analysis-progress.md).

```text
kgmaker init [--root PATH] [--force]
kgmaker scan [--root PATH] [--no-docs] [--confluence-dir PATH] [--confluence-report PATH]
kgmaker build [--root PATH] [--no-docs] [--confluence-dir PATH] [--confluence-report PATH]
kgmaker update [--root PATH] [--no-docs] [--confluence-dir PATH] [--confluence-report PATH]
kgmaker status [--root PATH]
kgmaker check [--root PATH]
kgmaker docs [check|report] [--root PATH] [--confluence-dir PATH] [--confluence-report PATH]
kgmaker impact [--root PATH] FILE [FILE ...]
kgmaker semantic prepare [--root PATH]
kgmaker semantic extract [--root PATH] [--base REF] [--note PATH] [--token-budget TOKENS]
kgmaker semantic update [--root PATH] [--base REF] [--note PATH] [--token-budget TOKENS]
kgmaker semantic apply [--root PATH]
kgmaker semantic validate [--root PATH]
kgmaker query [--root PATH] [--limit N] WORD [WORD ...]
```

- `scan` writes `.kgmaker/graph.json`, generated architecture documentation in `.kgmaker/GRAPH.md`, and a standalone Mermaid diagram in `.kgmaker/GRAPH.mmd`. The Markdown embeds the diagram for GitHub rendering; verified human or Copilot notes are kept separately in `.kgmaker/NOTES.md`. Use `--no-docs` to update only the machine index and skip both generated views; `kgmaker docs` can create them later.
- `build` and `update` currently perform a full scan, like `scan`.
- `--confluence-dir` adds a local, read-only multi-file Confluence HTML export. The path may be absolute or relative to the repository root; configuration under `documentation.confluence.directory` is used when the flag is absent. No Confluence API, credentials, crawling, or write-back is performed. Code-derived implementation facts take precedence over documentation.
- `docs check` (or `docs report`) validates the export without requiring a full graph rebuild. It parses HTML structurally, resolves local links, detects Mermaid/Draw.io/XML and image attachments, writes `docs/generated/confluence-inconsistencies.md` by default, and keeps `.kgmaker/confluence-index.json` hashes plus a reverse documentation index for focused revalidation. HTML and diagrams remain unchanged.
- `status` compares local indexed source hashes with the current repository. `check` rescans and verifies the committed Markdown documentation and Mermaid diagram, so it works in CI without `.kgmaker/graph.json`.
- `docs` regenerates `.kgmaker/GRAPH.md` and `.kgmaker/GRAPH.mmd` from the local machine index. The diagram groups code declarations by file and shows imports plus detected database, Kafka, API, frontend, and semantic relationships. Heuristic call edges are left out to keep the architecture view readable.
- `impact FILE` lists transitive dependents through imports and name-based calls. Imports are exact path matches; `calls` are candidates and may be wrong when names collide.
- `semantic prepare` writes a local inventory of stable graph IDs and per-file hashes, without copying source contents. The `kgmaker-extract` Copilot agent uses it for the first `.kgmaker/semantic.json` extraction.
- `semantic extract` starts semantic extraction independently from an implementation request. With no `.kgmaker/semantic.json`, it prepares the initial manifest; with an existing artifact, it prepares the incremental packet. It writes `.kgmaker/semantic-extract.md` with the exact agent input/output and never calls a model API itself.
- `semantic update --base REF` creates a bounded change packet and a review note from Git diff, changed declarations, their immediate graph neighborhood, and only affected semantic entries. Use `--note path/to/change-note.md` to add intent that is not apparent from the diff. Use `--token-budget N` to cap the changed-file context (approximately four characters per token; the default is about 4,000 tokens). This controls the packet generated by kgmaker, not the host Copilot model's billing or output limit. The custom agent writes `.kgmaker/semantic-patch.json`; `semantic apply` replaces only affected entries, and `semantic validate` verifies the result. Unrelated relationships survive unchanged. Generated update files stay local and are ignored by Git.
- Semantic artifacts track evidence per source-file hash, so a change in one file does not invalidate every relationship. If an evidence file changes, its relationships are skipped until the focused update is applied. Commit `.kgmaker/semantic.json` if the project wants to share agent-authored knowledge.
- `query` ranks relevant files and declarations, then includes one-hop graph neighbors.
- The Copilot hook calls `hook-context`, which refreshes the index and emits the session context in Copilot's hook format. You can run `kgmaker hook-context --token-budget N` to cap that injected context (approximately four characters per token). Hook errors fail open so they do not interrupt a Copilot session.
- JetBrains integration includes `.junie/commands/kgmaker.md` for the `/kgmaker` slash command and `.agents/skills/kgmaker/SKILL.md` for the standard `$kgmaker` Agent Skill invocation. Both route implementation requests through graph reconnaissance, source verification, scoped semantic updates, validation, and tests.

## What gets indexed

Python, Java, Kotlin, JavaScript, TypeScript, Go, Rust, Markdown, reStructuredText, SQL, YAML, properties, and JSON files are scanned. Generated output, dependency folders, virtual environments, common credential files, and files over 1 MB are skipped.

The scanner extracts Kotlin/Java declarations, TypeScript declarations and file-based app routes, SQL tables and columns, Spring Data entity/repository mappings, Kafka listener/producer/config topic references, Spring/Ktor HTTP routes, common HTTP client calls, and OpenAPI paths from YAML or JSON. It links matching HTTP method/path pairs across backend declarations, OpenAPI contracts, and frontend calls. It also recognizes PostgreSQL connection markers and common Kafka imports/configuration.

`imports` are parsed from source. `calls` are heuristic and can be wrong when names collide. SQL, YAML, Kotlin, and TypeScript support is pattern-based rather than a full language compiler or database parser. Dynamic URLs, custom frameworks, indirect Kafka topic names, jOOQ-generated schemas, and complex OpenAPI YAML may not resolve. The graph is a navigation aid; inspect source before relying on it. Raw file contents are not copied into the graph. `.kgmaker/graph.json` is intended to stay local; the human-readable map can be committed if the repository wants a shared snapshot.

## Copilot workflow

The generated `.github/agents/kgmaker.agent.md` provides a specialist for graph questions. `.github/agents/kgmaker-architect.agent.md` is the read-only reconnaissance specialist that Copilot should consult before implementation. `.github/agents/kgmaker-extract.agent.md` runs the initial and incremental semantic extraction workflows. After a code change, run `kgmaker semantic update --base <merge-base>` and give the extraction agent `.kgmaker/semantic-update.md` plus `.kgmaker/semantic-update.json`; it produces a scoped patch rather than rereading the repository. These are ordinary Copilot CLI custom agents and can be edited or used alongside a repository's own agents. Verified semantic notes live in `.kgmaker/NOTES.md`. kgmaker does not install agents into other products or make model API calls itself.

The repository hook uses the `sessionStart` event from GitHub Copilot CLI. To remove automatic integration, delete `.github/hooks/kgmaker.json`; the generated graph and CLI can still be used manually.

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

The application is intentionally dependency-free at runtime. The Markdown graph is deterministic; the ignored JSON index also records its generation time.

## Feature feasibility analysis (foundation)

A new isolated `kgmaker feature` workflow prepares evidence packets, validates
agent-authored candidates, stores immutable revisions and renders Czech/English
reports. It works without a diff, LLM API or semantic change packet.

```bash
kgmaker feature prepare --root . --requirement requirements/new-feature.md --id new-feature
# Follow candidate-template.json and write candidate.json with the host agent.
kgmaker feature validate --root . --analysis new-feature --candidate .kgmaker/analyses/new-feature/candidate.json
kgmaker feature apply --root . --analysis new-feature --candidate .kgmaker/analyses/new-feature/candidate.json
kgmaker feature report --root . --analysis new-feature
```

Run `kgmaker init` to install the `kgmaker-analyst` custom agent and JetBrains
analysis command instructions. See [workflow, schema and exact limitations](docs/feature-analysis.md)
and the [fixture report](docs/generated/features/additional-hedge-example.md).
This is the foundation of milestone A, not completion of the A–E roadmap:
full cross-layer availability proofs, XLSX, incremental invalidation and
Confluence synchronization remain outstanding. Positive availability claims are
rejected until their evidence validators exist.

Initial field-level impact is also available for supported static dependencies:

```bash
kgmaker impact --root . --entity '<existing-field-id>' --include-data-flow --format json
```

This includes simple Kotlin expressions/constructor mappings and field inventory
for Java, TypeScript and JSON contracts. Parser limitations are explicit in feature
coverage; a static path does not prove runtime availability or financial validity.

### Data prerequisite audit

Run `kgmaker init` to install `kgmaker-data-auditor` and the JetBrains
`kgmaker-check-data.md` command. Select the agent in the host, or ask it to follow
`.github/agents/kgmaker-data-auditor.agent.md` with your feature requirement.
The intent `/kgmaker check-data` is a routing convention.

The auditor reuses feature prepare/validate/apply/report/revise, query and
directed impact. Model work is limited to required input definitions and
business ambiguity. Current unavailable proof capabilities remain UNKNOWN;
the auditor cannot yet certify AVAILABLE or CONFIRMED_MISSING. It generates
an isolated report without changing application code or running tests.
The future deterministic data-check command is specified in
[implementation chapter 27](docs/implementation-feature-analysis.md#27-specializovaný-agent-pro-datové-předpoklady-nové-feature).


Structured data prerequisites can now be audited without a model call:

```bash
kgmaker feature data-check --root . --analysis <id> --inputs requirements/<id>-inputs.json --format json
```

The command returns a validated, unapplied candidate, static source candidates,
business ambiguities and separate tool coverage gaps. Availability remains UNKNOWN
until supported proofs exist. See [the input contract](docs/feature-analysis.md#deterministic-data-check-chapter-27-single-root-foundation).
Flyway schema replay, explicit multi-repository workspaces and scoped positive
availability proofs are implemented. See [commands, contracts and boundaries](docs/flyway-workspace-proofs.md).
