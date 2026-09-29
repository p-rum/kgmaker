# Project scope

kgmaker is a custom, repository-local knowledge graph tool designed specifically for GitHub Copilot CLI.

## Goals

- Build and refresh a navigable graph of files, symbols, and relationships.
- Put useful repository context into Copilot CLI sessions through native repository hooks.
- Keep documentation, prompts, hook configuration, and the implementation in the same repository.
- Offer an optional GitHub Copilot custom agent that users can adapt or pair with their own agents.
- Keep graph generation local, inspectable, and independent of model API keys.

## Out of scope

- MCP server or MCP-based runtime.
- Model-provider abstraction, API-key management, or remote inference backends.
- Installation into multiple unrelated agent products.
- External graph database or hosted service.
- External URLs in generated graph content.

## Initial implementation

The initial CLI scans Python, Java, Kotlin, JavaScript, TypeScript, Go, Rust, Markdown, and reStructuredText. It creates file/declaration nodes and `contains`, `imports`, and heuristic `calls` edges. It saves a local JSON index and a readable Markdown graph. Copilot CLI receives a compact context at session start; users can ask the optional custom agent to explain architecture and maintain verified semantic notes.

The index is a navigation aid rather than a substitute for source inspection. Ambiguous references are omitted and heuristic relationships are labeled as such.
