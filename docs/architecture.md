# Architecture

Graph schema v3 extends v2 with compiler symbols, call sites and CFG. Schema v2 introduced independent classification, scope-specific content contexts
and a referenced evidence inventory. `classification.py` owns explicit overrides
and conservative source-set/path rules; `views.py` projects scope before ranking
and exposes versioned execution/impact profiles. `project_cli.py` provides offline
inventory, classification, projections, ranking, migration and coverage. Scanner
partitions symbol, persistence and dataflow indexes before candidate selection.
Store validates and publishes JSON atomically. [Production scope](production-scope.md)
defines the new contracts and limits; [progress](production-analysis-progress.md)
records unfinished compiler/build/CFG milestones. Source patterns remain candidates.

The source-only core and its extensions are organized as follows:

1. `scanner.py` walks the repository, skips generated and sensitive paths, and extracts files, declarations, local imports, and conservative call candidates.
2. `domain.py` extracts PostgreSQL schema objects, Kotlin/JVM persistence links, Kafka topics, service/API references, OpenAPI endpoints, and TypeScript app routes.
3. `model.py` holds stable node and edge records.
4. `semantic.py` prepares stable node inventories, tracks source hashes per file, prepares Git-diff update packets with a configurable approximate token budget, validates scoped agent patches, and merges only affected changes while preserving unrelated semantics.
5. `store.py` writes the machine-readable graph, generated Markdown architecture documentation with an embedded Mermaid view, a standalone Mermaid diagram, broad comparison context, and a lean session bootstrap.
6. `memory.py` validates deterministic Git-provenanced implementation episodes, projects them into the graph, and provides bounded request-time recall. `workflow.py` stores durable task state and role artifacts separately from source-derived facts; `context.py` builds role-specific RAG packets from graph, memory, impact, tests, and prior artifacts.
7. `cli.py` exposes `init`, full-scan `build`/`update`, `scan`, local `status`, deterministic CI `check`, `impact`, `query`, `docs`, semantic prepare/update/apply/validation, implementation `memory`, durable `task`, and the Copilot hook command. Semantic updates, task packets, recall, and hook context accept approximate token budgets.
8. `confluence.py` ingests an optional local multi-file Confluence HTML export using structural parsing, resolves internal links and attachments, parses Mermaid and Draw.io/XML diagrams deterministically, caches artifact hashes, merges documentation evidence into the unified graph, and validates claims against the code graph. The source code is authoritative; contradictions are retained as evidence and rendered to a Markdown report.

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

The baseline scanner/domain modules are source-pattern parsers, not SQL engines or complete YAML parsers. Separate optional JVM/TypeScript workers use real compiler APIs; they do not replace the default scanner workflow. Dynamic URLs, indirect topic names, custom annotations, complex OpenAPI documents, and generated schemas may be missed. The `kgmaker` Copilot custom agent can explain behavior from source and keep semantic notes in `.kgmaker/NOTES.md`.

## Hook lifecycle

The generated repository hook subscribes to Copilot CLI `sessionStart`. It refreshes the graph and returns a lean `additionalContext` bootstrap. Request-specific repository locations and implementation history are retrieved with `kgmaker memory recall`; multi-role agents use bounded `kgmaker task context` packets. A failed scan returns empty context and a diagnostic on standard error, allowing the Copilot session to continue.

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
for supported scoped proof contracts, remaining parser gaps and the mandatory-manifest budget exception.

`dataflow.py` contributes field nodes and conservative local Kotlin value edges to
the existing graph. Typed impact follows dependency-specific direction and stops
at external-system boundaries. Feature candidates may cite only exact computed
paths with source evidence; arbitrary agent-authored paths are rejected. This is
initial milestone B support, not complete cross-layer or availability resolution.

`data_check.py` is a read-only orchestration layer over feature packets. It shares
AS_IS graph construction, query ranking (`store.query_nodes`), directed impacts,
feature validation and report rendering. It accepts semantic specifications rather
than caller-provided hashes or availability, then returns an unapplied candidate.
Business ambiguity and parser/access/proof coverage gaps are separate outputs.

`workbooks.py` reads `.xlsx` through bounded ZIP/XML parsing, creates workbook,
sheet, cell and named-range nodes, and records static formula dependencies. It
never evaluates formulas or loads external links. Cached values are separate and
always carry unknown freshness; `.xls`, shared formulas, INDIRECT and external
references produce explicit diagnostics. Workbook citations are re-read and
hash-checked by the normal feature validator.

`templates.py` supports a bounded Thymeleaf dialect: `${variable.path}` usage,
literal MVC model keys, literal returned template names and explicit PDF renderer
calls. It links the backend method, template variable and external PDF boundary
without evaluating expressions or treating the renderer as local code.

`confluence_sync.py` is separate from read-only HTML ingestion. It defines an
adapter protocol and an explicitly non-live fake adapter. A publish package owns
one managed section, preserves the rest of the page and carries an exact diff,
payload hash, base version and TO_BE state. Approval binds those values; publish
checks package integrity and optimistic concurrency and emits a content-free audit.
No live URL/auth/API convention is present without a documented connector.

`flyway.py` constructs explicit offline migration plans; `schema_replay.py`
tokenizes SQL, reconstructs active objects/lifecycle and reuses valid prefix
checkpoints. Unknown effects taint the declaration model. `workspace.py` wraps
existing graph IDs with repo-qualified identities, performs coherent per-repo
snapshots and uses versioned content-addressed coordinator caches. `test_analysis.py`
links explicit service contracts, supported consumer/test patterns and checks
test SQL against declared schema targets. `availability.py` verifies scoped
observations/approved mappings or contract/decision absence, without executing
tests, queries or migrations. All feed the same feature validator and renderer.

## Build-aware JVM inspection implementation task

See [T002](tasks/2_buildAwareInspection.md) for the required
compiler/bytecode call graph, isolated Maven build workflow, Spring Boot resolution,
and Hibernate/Spring Data inspection. The task defines milestones, acceptance tests,
and a mandatory numbered Markdown change document for every implementation PR in
`docs/changes/<N>_<shortPrName>.md`, starting at 1. The specification itself does not
implement these capabilities. Existing `build` remains a graph scan; analytical commands remain
offline. Build success, static reachability, runtime observations and data availability
retain separate evidence contracts.

Optional compiler inspection uses the existing Python graph/store through `inspection.py`
and bounded `worker_protocol.py`. JVM and TypeScript workers own symbol/call-site/AST
facts; `framework.py` adds only annotation-backed Spring/JPA projections with separate
`FRAMEWORK_DERIVED` evidence; `runtime_evidence.py` imports separately scoped
`RUNTIME_OBSERVED` edges. `control_flow.py` constructs CFG and `flow.py` renders it
without LLM ordering. Schema v3 extends v2 while old source-only indices stay readable. `build_runner.py`
executes only an explicit content-bound plan; `build_model.py` validates/imports the
same manifest path. Maven EventSpy and Gradle source-set exports belong to that
execution workflow, while `build_maven.py` provides a read-only declared Maven model
for project inspection. This is a partial supported matrix, documented in
[compiler inspection](compiler-inspection.md); complete Spring conditions, Hibernate
semantics and integration adapters remain open.

## High-level view model foundation

`architecture_model.py` defines deterministic schema-v1 JSON documents for
interface, topology and process projections. It validates node/edge identity,
endpoints, provenance references and coverage status without writing to or
changing the graph. This model is an API foundation; view discovery, CLI
commands, renderers and cross-service aggregation remain specified work in
[T004](tasks/4_addHighLevelProjectViews.md).

Workspace v1 optionally accepts a separate `service_ownership` schema v1.
Each declaration attaches explicit repository-relative roots and/or exact
repo-qualified module IDs to an already declared legacy service ID, with separately listed external
system IDs. The pure `workspace.resolve_service_ownership` function requires a
caller selected context and returns `RESOLVED` only for one matching declaration;
multiple matches are `AMBIGUOUS`, and no match is `UNASSIGNED`. Existing
`backend_repo` mappings and service IDs remain unchanged. A repository, Maven
module, or Spring `@Service` annotation alone does not establish ownership.
Repo-qualified compiler context IDs and workspace `@repo/path` symbols are checked
against the same repository ID before matching roots or module IDs.

`views.project_service_inventory` composes that ownership declaration with the
selected provider contexts as a service-only `ViewDocument` of kind `topology`.
Service IDs come from the manifest; display labels are not identity. Production
excludes contexts classified as test/development, and unclassified scope is not
promoted into production. Source-only matches remain `PARTIAL` with module coverage
`UNKNOWN`. SOURCE_ONLY repository contexts resolve roots only from qualified source
artifacts and file nodes in the same repository and exact scope in the supplied
provider snapshot; production and test roots in one checkout remain separate. They
retain no module
identity and remain `PARTIAL`. Only explicitly declared external-system IDs are
projected; their checkout, internal implementation and endpoints remain `UNKNOWN`. The projection
uses T007 ownership and T006 context selection, does not infer service boundaries
from repository names, configuration or framework beans, and does not persist a
parallel catalog. No CLI subcommand is added.
`views.select_service_contexts(graph, requests, scope=...)` projects explicit
service/repo/module selections onto compiler contexts already present in a graph.
Requests may pin `context_id`; a module with multiple profiles requires that
choice. The result includes content fingerprints and context freshness. Pass
`source_coverage` to request `mode: SOURCE_ONLY`; its selected artifacts remain
PARTIAL. A workspace release declaration and its snapshot report can identify
CONTENT_VERIFIED producer/consumer artifact pairs. That proves the declared
output bytes match the consumer classpath; deployment and environment
compatibility remain UNKNOWN. This is a Python library API; no CLI command has
been added. Workspace source inventory is repository-wide, so SOURCE_ONLY also
leaves module-level coverage UNKNOWN.


## Compiler lifecycle provider

`graph_provider.py` shares offline snapshot validation with compiler navigation.
Single-root feature, scan and hook refresh syntax and semantic/Flyway projections
while retaining fresh compiler nodes, edges, evidence, symbols, call sites and CFG
in the existing store. A stale compiler layer is projected out without publishing
its facts; its context records the reason and explicit inspection command. Other
valid module/profile contexts remain available. No process execution is needed.

Inspection starts from a fresh syntactic baseline, then atomically merges the new
module/profile selection with other validated compiler contexts. Workers include
the context ID in symbol identity, preventing cross-variant collapse. Workspace
schema v3 qualifies and preserves compiler symbols, call sites, CFG internals,
evidence and annotations per repository. Unified higher-level context selection and
the complete T003-AC02 sequence remain required.

Task identities and historical milestone aliases are defined only by
[the registry](tasks/README.md). [Current status](production-analysis-progress.md)
distinguishes existing capabilities from the normative [completion plan](tasks/3_finishProductionAnalysis.md).

Fresh SOURCE_ONLY scans redact URI credentials/query/fragment values in persisted
signatures, documentation summaries and heading identities. This privacy transform
supplies no semantic HTTP values: compiler-bound request origins and terminal
intent are projected separately by `http_execution`, with runtime availability
UNKNOWN. See the scoped [HTTP matrix](compiler-inspection.md#http-client-intent).
