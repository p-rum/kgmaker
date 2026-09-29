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

`kgmaker init` creates repository-level Copilot hooks, a knowledge-graph custom agent, repository instructions, and a local-index ignore rule. Existing files are preserved. Pass `--force` only when you want to replace the kgmaker-managed Copilot files.

Restart Copilot CLI after installing the hook. Each new session refreshes the graph and injects a compact map as `additionalContext`.

## Commands

```text
kgmaker init [--root PATH] [--force]
kgmaker scan [--root PATH]
kgmaker status [--root PATH]
kgmaker query [--root PATH] [--limit N] WORD [WORD ...]
```

- `scan` writes `.kgmaker/graph.json` and a readable `.kgmaker/GRAPH.md`; verified human or Copilot notes are kept separately in `.kgmaker/NOTES.md`.
- `status` compares indexed source hashes with the current repository.
- `query` ranks relevant files and declarations, then includes one-hop graph neighbors.
- The Copilot hook calls `hook-context`, which refreshes the index and emits the session context in Copilot's hook format. Hook errors fail open so they do not interrupt a Copilot session.

## What gets indexed

Python, Java, Kotlin, JavaScript, TypeScript, Go, Rust, Markdown, reStructuredText, SQL, YAML, properties, and JSON files are scanned. Generated output, dependency folders, virtual environments, common credential files, and files over 1 MB are skipped.

The scanner extracts Kotlin/Java declarations, TypeScript declarations and file-based app routes, SQL tables and columns, Spring Data entity/repository mappings, Kafka listener/producer/config topic references, Spring/Ktor HTTP routes, common HTTP client calls, and OpenAPI paths from YAML or JSON. It links matching HTTP method/path pairs across backend declarations, OpenAPI contracts, and frontend calls. It also recognizes PostgreSQL connection markers and common Kafka imports/configuration.

`imports` are parsed from source. `calls` are heuristic and can be wrong when names collide. SQL, YAML, Kotlin, and TypeScript support is pattern-based rather than a full language compiler or database parser. Dynamic URLs, custom frameworks, indirect Kafka topic names, jOOQ-generated schemas, and complex OpenAPI YAML may not resolve. The graph is a navigation aid; inspect source before relying on it. Raw file contents are not copied into the graph. `.kgmaker/graph.json` is intended to stay local; the human-readable map can be committed if the repository wants a shared snapshot.

## Copilot workflow

The generated `.github/agents/kgmaker.agent.md` provides an optional specialist agent for architecture questions and graph maintenance. It is an ordinary Copilot CLI custom agent, so it can be edited or used alongside a repository's own custom agents. Verified semantic notes live in `.kgmaker/NOTES.md` and are included in session context. kgmaker does not install agents into other products.

The repository hook uses the `sessionStart` event from GitHub Copilot CLI. To remove automatic integration, delete `.github/hooks/kgmaker.json`; the generated graph and CLI can still be used manually.

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

The application is intentionally dependency-free at runtime. Graph output is deterministic apart from its generation timestamp.
