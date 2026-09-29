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
kgmaker build [--root PATH]
kgmaker update [--root PATH]
kgmaker status [--root PATH]
kgmaker check [--root PATH]
kgmaker docs [--root PATH]
kgmaker impact [--root PATH] FILE [FILE ...]
kgmaker semantic prepare [--root PATH]
kgmaker semantic update [--root PATH] [--base REF] [--note PATH]
kgmaker semantic apply [--root PATH]
kgmaker semantic validate [--root PATH]
kgmaker query [--root PATH] [--limit N] WORD [WORD ...]
```

- `scan` writes `.kgmaker/graph.json` and a readable `.kgmaker/GRAPH.md`; verified human or Copilot notes are kept separately in `.kgmaker/NOTES.md`.
- `build` and `update` currently perform a full scan, like `scan`.
- `status` compares local indexed source hashes with the current repository. `check` rescans and verifies the committed Markdown graph snapshot, so it works in CI without `.kgmaker/graph.json`.
- `docs` regenerates `.kgmaker/GRAPH.md` from the local machine index.
- `impact FILE` lists transitive dependents through imports and name-based calls. Imports are exact path matches; `calls` are candidates and may be wrong when names collide.
- `semantic prepare` writes a local inventory of stable graph IDs and per-file hashes, without copying source contents. The `kgmaker-extract` Copilot agent uses it for the first `.kgmaker/semantic.json` extraction.
- `semantic update --base REF` creates a bounded change packet and a review note from Git diff, changed declarations, their immediate graph neighborhood, and only affected semantic entries. Use `--note path/to/change-note.md` to add intent that is not apparent from the diff. The custom agent writes `.kgmaker/semantic-patch.json`; `semantic apply` replaces only affected entries, and `semantic validate` verifies the result. Unrelated relationships survive unchanged. Generated update files stay local and are ignored by Git.
- Semantic artifacts track evidence per source-file hash, so a change in one file does not invalidate every relationship. If an evidence file changes, its relationships are skipped until the focused update is applied. Commit `.kgmaker/semantic.json` if the project wants to share agent-authored knowledge.
- `query` ranks relevant files and declarations, then includes one-hop graph neighbors.
- The Copilot hook calls `hook-context`, which refreshes the index and emits the session context in Copilot's hook format. Hook errors fail open so they do not interrupt a Copilot session.

## What gets indexed

Python, Java, Kotlin, JavaScript, TypeScript, Go, Rust, Markdown, reStructuredText, SQL, YAML, properties, and JSON files are scanned. Generated output, dependency folders, virtual environments, common credential files, and files over 1 MB are skipped.

The scanner extracts Kotlin/Java declarations, TypeScript declarations and file-based app routes, SQL tables and columns, Spring Data entity/repository mappings, Kafka listener/producer/config topic references, Spring/Ktor HTTP routes, common HTTP client calls, and OpenAPI paths from YAML or JSON. It links matching HTTP method/path pairs across backend declarations, OpenAPI contracts, and frontend calls. It also recognizes PostgreSQL connection markers and common Kafka imports/configuration.

`imports` are parsed from source. `calls` are heuristic and can be wrong when names collide. SQL, YAML, Kotlin, and TypeScript support is pattern-based rather than a full language compiler or database parser. Dynamic URLs, custom frameworks, indirect Kafka topic names, jOOQ-generated schemas, and complex OpenAPI YAML may not resolve. The graph is a navigation aid; inspect source before relying on it. Raw file contents are not copied into the graph. `.kgmaker/graph.json` is intended to stay local; the human-readable map can be committed if the repository wants a shared snapshot.

## Copilot workflow

The generated `.github/agents/kgmaker.agent.md` provides an optional specialist for architecture questions. `.github/agents/kgmaker-extract.agent.md` runs the initial and incremental semantic extraction workflows. After a code change, run `kgmaker semantic update --base <merge-base>` and give the agent `.kgmaker/semantic-update.md` plus `.kgmaker/semantic-update.json`; it produces a scoped patch rather than rereading the repository. Both are ordinary Copilot CLI custom agents and can be edited or used alongside a repository's own agents. Verified semantic notes live in `.kgmaker/NOTES.md`. kgmaker does not install agents into other products or make model API calls itself.

The repository hook uses the `sessionStart` event from GitHub Copilot CLI. To remove automatic integration, delete `.github/hooks/kgmaker.json`; the generated graph and CLI can still be used manually.

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

The application is intentionally dependency-free at runtime. The Markdown graph is deterministic; the ignored JSON index also records its generation time.
