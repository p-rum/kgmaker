# kgmaker

**A local knowledge graph for GitHub Copilot CLI.** kgmaker maps files, declarations, imports, database tables, Kafka topics, API endpoints, frontend routes, and likely cross-file calls. Copilot receives a lean bootstrap at session start and retrieves task-specific graph locations and prior implementation episodes on demand. The source-only Python core runs locally using the standard library. Optional compiler inspection requires separately installed JDK/Node workers. JVM inspection adds an evidence-backed subset of Spring bean/entrypoint/proxy-policy and JPA/Spring Data bindings; it does not start the application or connect to a database.

Automatic repository hooks target GitHub Copilot CLI. Standalone Agent Skills also provide workflows for compatible hosts, with manual file-based invocation when discovery is unavailable. Repository hooks handle automatic refresh and context. A repository custom agent can enrich architectural explanations using Copilot itself. There is no model API key, provider configuration, MCP server, or external graph service.

## Documentation and implementation tasks

Start with the [current per-task delivery inventory](docs/production-analysis-progress.md),
[task registry](docs/tasks/README.md) and [completion specification T003](docs/tasks/3_finishProductionAnalysis.md).
Agents must follow [AGENTS.md](AGENTS.md), including stable task IDs and mandatory
`docs/tasks/<N>_<lowerCamelCase>.md` / `docs/changes/<N>_<lowerCamelCase>.md` names.
These two number sequences are independent of each other and GitHub PR numbers.
For the agent handoff and dependency-aware completion order, see
[T048 completion plan](docs/tasks/48_completeImplementationHandoff.md). Each
implementation step includes a traceable change-note entry and updates to all
affected current documentation; see the documentation gate in AGENTS.md.

## Planned high-level project views

[Specification T004](docs/tasks/4_addHighLevelProjectViews.md) defines an interface
catalogue, service topology and evidence-backed business-process views.
[Tasks T005–T044](docs/tasks/README.md#high-level-zobrazení-projektu--t004) each have
their own implementation specification, acceptance criteria, tests, branch and PR.
The files are specifications of target behavior. Delivery must be checked against
code and the current status: T005–T020, T023–T026 and T030–T033 have merged
implementations in the 2026-11-06 baseline. This does not certify every acceptance
criterion or every production variant. The remaining delivery order is in T048.

## Requirements

- Python 3.11 or newer
- GitHub Copilot CLI for automatic Copilot integration

## Install

Windows user-space installation passed an actual restricted-user CI smoke with
paths containing spaces (43 passed, 2 scoped skips). It covers the core, Java/K1
Kotlin and TypeScript workers. K2 on Windows remains unverified; Windows
`BUILD_EXECUTE` reports an explicit unsupported-platform error. See
[Windows prerequisites and verification evidence](docs/windows-install.md).

From the repository root:

```bash
python -m pip install -e .
kgmaker init
kgmaker scan
```

`kgmaker init` creates Agent Skills under `.agents/skills/`, repository-level Copilot hooks, knowledge-graph and read-only architecture agents, repository instructions, and a local-index ignore rule. The instructions tell Copilot to consult `kgmaker-architect` before every substantive implementation request; it checks the graph and relevant source/tests, then gives the primary agent a focused implementation brief. Existing files are preserved. Pass `--force` only when you want to replace the kgmaker-managed instructions and skills.

The five skills cover code navigation (`kgmaker-context`), semantic graph maintenance
(`kgmaker-semantic`), requirement analysis (`kgmaker-feature-analysis`), data audits
(`kgmaker-data-audit`) and test proposals (`kgmaker-testgen`). For example, ask your
agent to use `$kgmaker-context` to find affected callers, or `$kgmaker-data-audit`
to assess a requirement's inputs. Discovery and `$` invocation depend on the host;
you can always explicitly open the installed `SKILL.md` and follow it. See the
[target-project skills guide](docs/agent-skills.md) for installation, examples,
preservation rules and limits ([T050 change117](docs/changes/117_addTargetProjectSkills.md)).

Restart Copilot CLI after installing the hook. Each new session refreshes the graph and injects a compact map as `additionalContext`.

## Commands

Offline production classification, graph schema v2 and scoped evidence views are
documented in [production scope](docs/production-scope.md). Use `kgmaker project
classify --root . --explain --format json`, `kgmaker graph rank --profile execution
--explain` and `kgmaker coverage report --format json`. Default query, generated
architecture views and hook context use production scope; `query --scope all`
includes unknown/test inventory. Without a valid compiler index these are partial source-only analyses. Explicit `inspect` adds compiler-backed calls/CFG for the supported matrix. See [implementation progress](docs/production-analysis-progress.md).

The library API `kgmaker.architecture_model.ViewDocument` provides a versioned,
deterministic JSON envelope for high-level interface, topology and process
projections. Nodes and edges retain evidence kind, resolution status, freshness,
and separate supporting, contradicting and unknown references. Their coverage
counts describe the supplied selected inventory, not the unobserved system.
`kgmaker.views.select_service_contexts` builds an explicit, read-only
service/repository/module context selection from an existing graph; it requires a
context ID when variants are ambiguous and reports SOURCE_ONLY and deployment
limits. `project_service_inventory` provides a read-only service-only topology
projection using that selection and explicit ownership. The CLI exposes `architecture interfaces`, `architecture topology` and
`architecture explain` over explicit captured inputs. Interfaces also support
`--format markdown`; topology and explain remain JSON-only. See
[the CLI contract](docs/architecture-json-cli.md) and
[interface Markdown](docs/interface-markdown.md). Evidence ranking now exposes `execution-2`/`impact-2` with witness paths, localized
penalties and `graph rank --format markdown`; see [ranking scope](docs/evidence-ranking.md)
and [change126](docs/changes/126_evidenceRanking.md). Scores are priorities, not runtime availability. Stale proof records contribute
no weight; execution requires a captured compiler inspection context, and a reference
or unsupported invocation cannot establish static dispatch completeness. Explicit context
selection omits mixed compiler-variant claims while retaining source provenance. See [architecture](docs/architecture.md), the
[T006 selection contract](docs/tasks/T-006_select-service-contexts.md), and the
[T004 plan](docs/tasks/4_addHighLevelProjectViews.md).

```python
from kgmaker.views import select_service_contexts

selection = select_service_contexts(
    graph,
    [
        {"service_id": "billing-api", "repo_id": "billing", "module": "app",
         "context_id": "repo:billing:billing-production"},
        {"service_id": "ledger-api", "repo_id": "ledger", "module": "service",
         "context_id": "repo:ledger:ledger-production"},
    ],
    scope="production",
)
```

The function is imported from `kgmaker.views`; the snippet shows the library
contract and does not add a `kgmaker` CLI command.

`views.project_service_inventory` builds a service-only `topology` document from
explicit workspace ownership and the matching provider snapshot. Stable node IDs
come from declared service IDs; `service_labels` changes display text only.
Only services with provider contexts in the selected scope enter the inventory.
Declared external systems remain visible without a local checkout, while their
implementation and endpoints remain `UNKNOWN`. Source-only evidence stays
`PARTIAL` and does not prove module completeness or deployment.

```python
from pathlib import Path
from kgmaker.workspace import load_workspace, snapshot_workspace
from kgmaker.views import project_service_inventory

manifest = Path("workspace.json")
workspace = load_workspace(manifest)
_, coverage, _, provider_graph, _ = snapshot_workspace(manifest)
inventory = project_service_inventory(
    workspace, provider_graph, scope="production", source_coverage=coverage,
    service_labels={"orders": "Orders API"},
)
```

`interfaces.project_http_providers` returns an `interfaces` ViewDocument from
that same explicit workspace snapshot. Logical HTTP identity includes the declared
service, method and case-preserving route; registrations and contract revisions
remain separate variants. Compiler Spring annotation mirrors can establish a
class/method handler declaration. Source-pattern Spring/Ktor candidates and
OpenAPI contracts retain their weaker evidence. Deployment, runtime and data
availability remain `UNKNOWN`; unsupported imported-runtime binding is diagnostic.

```python
from kgmaker.interfaces import project_http_providers

interfaces = project_http_providers(
    workspace, provider_graph, scope="production", source_coverage=coverage,
)
```

This library projection adds no CLI command. See [HTTP provider boundaries](docs/architecture.md#http-provider-projection)
and [T010 evidence](docs/changes/67_catalogHttpProviders.md). Colliding normalized
contract variants remain one explicit `AMBIGUOUS` boundary with every original
route and candidate proof; see [change88](docs/changes/88_preserveAmbiguousHttpProviders.md).

Workspace v1 can optionally carry `service_ownership` v1 with explicit service
roots, repo-qualified module IDs and external system IDs. `kgmaker.workspace.resolve_service_ownership`
returns `RESOLVED`, `AMBIGUOUS` or `UNASSIGNED` for the caller supplied context;
legacy `services` entries remain readable and do not claim ownership by themselves.
Repo-qualified compiler contexts and `@repo/path` symbol paths must match the
symbol repository. This contract does not discover deployment boundaries or infer
runtime identity.

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
kgmaker project inspect [--root PATH] [--format json]
kgmaker project build-plan [--java-home /absolute/path/to/jdk] ...
kgmaker project build-run|build-import ...
kgmaker inspect code|frontend ...
kgmaker callgraph callers|callees|path ...
kgmaker entrypoints [--root PATH] [--format json]
kgmaker runtime import --root PATH --manifest runtime-manifest.json
```

- `scan` writes `.kgmaker/graph.json`, generated architecture documentation in `.kgmaker/GRAPH.md`, and a standalone Mermaid diagram in `.kgmaker/GRAPH.mmd`. The Markdown embeds the diagram for GitHub rendering; verified human or Copilot notes are kept separately in `.kgmaker/NOTES.md`. Use `--no-docs` to update only the machine index and skip both generated views; `kgmaker docs` can create them later.
- `build` and `update` currently perform a full scan, like `scan`.
- `--confluence-dir` adds a local, read-only multi-file Confluence HTML export. The path may be absolute or relative to the repository root; configuration under `documentation.confluence.directory` is used when the flag is absent. No Confluence API, credentials, crawling, or write-back is performed. Code-derived implementation facts take precedence over documentation.
- `docs check` (or `docs report`) validates the export without requiring a full graph rebuild. It parses HTML structurally, resolves local links, detects Mermaid/Draw.io/XML and image attachments, writes `docs/generated/confluence-inconsistencies.md` by default, and keeps `.kgmaker/confluence-index.json` hashes plus a reverse documentation index for focused revalidation. HTML and diagrams remain unchanged.
- `confluence_sync.py` defines the optional write boundary. Its offline fake adapter
  supports explicit page pull, managed-section proposals, exact diffs, approvals
  bound to payload hash/base version, optimistic concurrency and bounded audits.
  It is labelled `FAKE_TEST_ONLY`; no live host/API/authentication contract is
  claimed. Publishing is possible only through an explicitly supplied adapter and
  an exact approved package, never from scan, hook, feature or data-check.
- `confluence config --root .` validates optional JSON connection settings under
  `documentation.confluence.connection` and reports environment-reference readiness
  without connecting. Host, API variant and sandbox are configurable; live adapter
  execution is deferred and always reported `NOT_RUN` by this command.
- `status` compares the indexed source graph with the repository and validates saved
  compiler contexts separately. A current source graph with a stale compiler context
  exits 2 and prints the exact explicit inspection command. `check` applies the same
  compiler gate while verifying committed Markdown and Mermaid output. Neither command
  runs a compiler, build, test, package manager, or application. Workspace status
  exposes `source_graph_current`, `compiler_contexts_current`, and bounded
  `stale_compiler_contexts` independently for repo-qualified realms.
- `docs` regenerates `.kgmaker/GRAPH.md` and `.kgmaker/GRAPH.mmd` from the local machine index. The diagram groups code declarations by file and shows imports plus detected database, Kafka, API, frontend, and semantic relationships. Heuristic call edges are left out to keep the architecture view readable.
- `impact FILE` lists transitive dependents through imports and name-based calls. Imports are exact path matches; `calls` are candidates and may be wrong when names collide.
- `semantic prepare` writes a local inventory of stable graph IDs and per-file hashes, without copying source contents. The `kgmaker-extract` Copilot agent uses it for the first `.kgmaker/semantic.json` extraction.
- `semantic extract` starts semantic extraction independently from an implementation request. With no `.kgmaker/semantic.json`, it prepares the initial manifest; with an existing artifact, it prepares the incremental packet. It writes `.kgmaker/semantic-extract.md` with the exact agent input/output and never calls a model API itself.
- `semantic update --base REF` creates a bounded change packet and a review note from Git diff, changed declarations, their immediate graph neighborhood, and only affected semantic entries. Use `--note path/to/change-note.md` to add intent that is not apparent from the diff. Use `--token-budget N` to cap the changed-file context (approximately four characters per token; the default is about 4,000 tokens). This controls the packet generated by kgmaker, not the host Copilot model's billing or output limit. The custom agent writes `.kgmaker/semantic-patch.json`; `semantic apply` replaces only affected entries, and `semantic validate` verifies the result. Unrelated relationships survive unchanged. Generated update files stay local and are ignored by Git.
- Semantic artifacts track evidence per source-file hash, so a change in one file does not invalidate every relationship. If an evidence file changes, its relationships are skipped until the focused update is applied. Commit `.kgmaker/semantic.json` if the project wants to share agent-authored knowledge.
- `query` ranks relevant files and declarations, then includes one-hop graph neighbors.
- The Copilot hook calls `hook-context`, refreshes the index, and emits a small bootstrap in Copilot's hook format. Use `memory recall` with the actual request for detailed context. You can run `kgmaker hook-context --token-budget N` to cap startup context (approximately four characters per token). Hook errors fail open so they do not interrupt a Copilot session.
- JetBrains integration includes `.junie/commands/kgmaker.md`. Host-neutral Agent Skills cover context, semantic maintenance, feature/data analysis and testgen; see [the installed skills guide](docs/agent-skills.md). Implementation handoffs use the [project workflows](docs/project-workflows.md).

## What gets indexed

Python, Java, Kotlin, JavaScript, TypeScript, Go, Rust, Markdown, reStructuredText, SQL, YAML, properties, and JSON files are scanned. Generated output, dependency folders, virtual environments, common credential files, and files over 1 MB are skipped.

The scanner extracts Kotlin/Java declarations, TypeScript declarations and file-based app routes, SQL tables and columns, Spring Data entity/repository mappings, Kafka listener/producer/config topic references, Spring/Ktor HTTP routes, common HTTP client calls, and OpenAPI paths from YAML or JSON. It links matching HTTP method/path pairs across backend declarations, OpenAPI contracts, and frontend calls. It also recognizes PostgreSQL connection markers and common Kafka imports/configuration.

Explicit workspaces can join an actual backend compiler field through a
hash/release-bound declared contract to TypeScript JSON/destructuring, a pinned
React `useState` setter and a concrete JSX or test argument consumer. This reads
existing explicit inspection indexes; scan/hook/feature never run workers.
Object mutation or escape through a local alias invalidates its response origin;
`Readonly<T>` alone does not make an escaped reference safe. Stale cache entries
reload the original captured index and revalidate its inputs without inspection.
SOURCE_ONLY inventories remain PARTIAL and no longer turn matching field names
into UI/assertion value paths. Runtime availability and payload equivalence stay
UNKNOWN. See [the supported workflow and limits](docs/backend-frontend-value-flow.md)
and [change125](docs/changes/125_backendFrontendValueFlow.md).

`imports` are parsed from source. `calls` are heuristic and can be wrong when names collide. The default scanner uses pattern-based SQL, YAML, Kotlin and TypeScript extraction. Separate opt-in JVM/TypeScript workers use compiler APIs; they are not invoked by scan/hook/feature. Explicit JVM inspection can project imported Spring/JPA annotations into `FRAMEWORK_DERIVED` nodes and edges, including bean candidates, HTTP/listener entrypoints, proxy boundaries, entity/table/column bindings, and simple Spring Data repository/query declarations. Dynamic URLs, custom frameworks, indirect Kafka topic names, jOOQ-generated schemas, and complex OpenAPI YAML may not resolve. The graph is a navigation aid; inspect source before relying on it. Raw file contents are not copied into the graph. `.kgmaker/graph.json` is intended to stay local; the human-readable map can be committed if the repository wants a shared snapshot.

Explicit `kgmaker inspect frontend --root /path/to/repo --tsconfig tsconfig.json`
also analyzes solution-style TypeScript project references within that root.
The captured project graph identifies each repo/config, follows the compiler's
source redirects without emitting outputs, and invalidates stored compiler facts
when a transitive project input changes. Missing, cyclic, outside-root or
overlapping reference graphs fail before publication. This does not add callback
resolution or cross-repository TypeScript source analysis.
Declaration identities use the owning project's checker even when consumer
options differ. Referencing configs that disable source redirects are rejected
before publication rather than trusting emitted declarations.
Preflight and analysis must read the same compiler input closure; membership
changes fail before publication. Reinspection replaces the same TypeScript
selection slot across legacy and K2-era snapshot metadata.
New TypeScript snapshots also bind effective-config inputs, negative filesystem
lookups, compiler directory discovery and package-manager lockfiles. Unrelated
config or excluded-unused content edits preserve the selected context; relevant
new dependencies/members invalidate it offline without running Node. Legacy
snapshots keep conservative validation. See [TypeScript freshness and limits](docs/typescript-freshness.md).

TypeScript worker4 preserves concrete generic/overload signatures through barrel
exports and records named/inline callback bindings. Callback parameters and union
values expose incomplete dispatch candidates; mutable/any callbacks remain unresolved.
Callee navigation includes candidates when explicitly requested. See
[callback evidence and limits](docs/typescript-callbacks.md).

## Copilot workflow

Vývoj tohoto repozitáře má navíc projektové Codex implementační agenty v
`.codex/agents`. Každý agent je vyhrazen jednomu atomickému work package T003,
má explicitně nastavený model `gpt-5.6-luna` a reasoning effort `medium` a vede
implementaci přes vlastní větev, testy a samostatný pull request. Tyto profily
jsou konfigurací přispěvatelů tohoto repozitáře; příkaz `kgmaker init` je
neinstaluje do uživatelských projektů.
Projektový [`code_review`](.codex/agents/code-review.toml) přebírá vytvořené PR,
ověřuje diff a test evidence proti zadání a vrací `APPROVE`, `REQUEST_CHANGES`
nebo `BLOCKED` pro konkrétní head SHA. Po `APPROVE` znovu ověří aktuální HEAD,
povinné lokální acceptance/toolchain kontroly, závislosti a mergeability a potom
sloučí ready PR. GH CI je doplňující evidence: jeho absence či billing blokace
sama merge neblokuje, pokud vše ostatní prošlo; konkrétní chyby z CI a skutečná
serverová pravidla zůstávají závazné.
Příklad předání: `Předej PR #12 agentovi code_review; po schválení jej merguj.`
Konkrétní pravidla a hranice jsou v [T045](docs/tasks/45_addCodeReviewAgent.md).

The generated `.github/agents/kgmaker.agent.md` provides a specialist for graph questions. The architect, implementation, test-expert, review, and orchestrator agents use the durable `task` workflow and role-specific context packets. `.github/agents/kgmaker-extract.agent.md` runs the initial and incremental semantic extraction workflows. After a code change, run `kgmaker semantic update --base <merge-base>` and give the extraction agent `.kgmaker/semantic-update.md` plus `.kgmaker/semantic-update.json`; it produces a scoped patch rather than rereading the repository. These are ordinary Copilot CLI custom agents and can be edited or used alongside a repository's own agents. Verified semantic notes live in `.kgmaker/NOTES.md`. Host-neutral Agent Skills are installed alongside them under `.agents/skills/`; automatic discovery depends on the host. kgmaker makes no model API calls itself.

## Implementation memory and workflow

Configurable profiles connect analysis, planning, implementation, testing and review:

```bash
kgmaker workflow list
kgmaker task add "Create a minimal working application" --workflow greenfield
kgmaker task add "Extend the existing export" --workflow existing-feature
kgmaker task add "Fix the empty-input regression" --workflow bugfix
```

Version `.kgmaker/workflows.json` to configure role instructions, required test
commands, iteration limits and packet budgets. Each profiled task pins its exact
configuration and requires completed role artifacts, passed required checks and
current test/review evidence before completion. Commands in a profile are data;
kgmaker does not execute them. Legacy tasks keep their existing behavior.
See the [project workflow guide](docs/project-workflows.md),
[configuration example](examples/workflows/python-project.json) and
[T051 change record](docs/changes/118_connectProjectWorkflows.md).

`memory capture` records one deterministic episode from a Git baseline, the stored pre-task graph, a fresh graph, changed file hashes, affected node IDs, and bounded validation statuses. It stores no source text, raw diff, prompt transcript, test output, or sensitive path content. Repeating capture for the same Git/worktree fingerprint is idempotent. Semantic schema v1 and v2 remain readable; the first capture writes schema v3 while preserving valid concepts and relationships.

`memory recall` ranks current graph locations and prior episodes against the implementation request. It labels changed or removed episode evidence as historical, applies result and token bounds, and reports the estimated reduction from the broad legacy graph context.

The `task` commands persist workflow state under ignored `.kgmaker/workflow/`. A task follows `intake → analyze → plan → implement → test → review → done`; bounded retries may return test or review to implementation. Architect, implementation, test-expert, review, and orchestrator artifacts have strict role-specific JSON contracts. `task context` assembles a bounded packet from current graph nodes, semantic hits, implementation memory, impact candidates, tests, and prior task artifacts without modifying the graph or semantic layer.
The generated `.github/agents/kgmaker.agent.md` provides a specialist for graph questions. `.github/agents/kgmaker-architect.agent.md` is the read-only reconnaissance specialist that Copilot should consult before implementation. `.github/agents/kgmaker-extract.agent.md` runs the initial and incremental semantic extraction workflows. After a code change, run `kgmaker semantic update --base <merge-base>` and give the extraction agent `.kgmaker/semantic-update.md` plus `.kgmaker/semantic-update.json`; it produces a scoped patch rather than rereading the repository. These are ordinary Copilot CLI custom agents and can be edited or used alongside a repository's own agents. Verified semantic notes live in `.kgmaker/NOTES.md`. JetBrains command files are also supplied; `init` installs the analyst/data-auditor commands and all five Agent Skills listed in its output. kgmaker makes no model API calls itself.

The repository hook uses the `sessionStart` event from GitHub Copilot CLI. To remove automatic integration, delete `.github/hooks/kgmaker.json`; the generated graph and CLI can still be used manually.

## Development

```bash
python -m venv .venv
source .venv/bin/activate  # POSIX; on Windows activate the venv from Scripts
python -m pip install -e . pytest==8.3.4 jsonschema==4.23.0 setuptools==84.2.1 wheel==0.48.0
python -m pip install --require-hashes -r tests/requirements-markdown.txt
python -m pytest -q
```

The Python core is intentionally dependency-free at runtime. The development suite requires pytest and the explicit setuptools/wheel tools above for offline installation tests; compiler integration requires the optional toolchains. Missing workers skip optional local integration tests, while CI requires them in its worker job. The Markdown graph is deterministic; the ignored JSON index also records its generation time. Use a clean venv rather than copying system setuptools into another Python distribution. Actual compiler/build fixtures require the documented pinned toolchains (JDK21, Kotlin2.1.10, Maven3.9.9, Gradle8.12.1/8.13); system Gradle4.4 is outside that matrix. The HTTP capture stays in pytest temporary storage. [Integration repair and current validation](docs/changes/116_parseExtendedJpqlHql.md).

The required `compiler-workers` job prepares and exercises JVM/Kotlin K1, K2,
TypeScript and the mixed Maven fixture. Its negative prerequisite matrix runs
with `python -m pytest -q tests/test_mandatory_worker_ci.py`: an absent worker,
JDK or mixed fixture fails a required gate and skips an optional local gate,
without starting a process. The separate exporter job requires actual Maven and
Gradle exports. Exploratory tests needing a second JDK remain optional.

Wheels include trusted worker scripts and pinned build inputs in the
`kgmaker_workers` resource package. A source-only installation works without
JDK/Node. Optional JVM JARs/libraries and the pinned TypeScript installation are
included only when explicitly prepared before building the wheel; installation
never downloads or builds them. See [worker distribution](docs/compiler-inspection.md#instalace-mimo-checkout)
for the supported layout and build steps. Inspection resolves `--worker-home`
first, then `KGMAKER_WORKERS_HOME`, then installed resources (or the source
checkout when running directly with `PYTHONPATH=src`). An unavailable explicit
selection fails with `TOOLCHAIN_UNAVAILABLE` and leaves the last graph intact.

Build exporter resources additionally carry a versioned `build/exporters.json`
descriptor and Apache license. Explicit `project build-plan` / `build-run`
verify the adapter bytes, descriptor and output protocol before publishing a
manifest. Release builders must run `workers/build/build.py` explicitly before
packaging the optional Maven exporter. See [exporter distribution](docs/compiler-inspection.md#distribuce-build-exporteru).

```bash
python -m pip install --no-deps /path/to/kgmaker-0.1.0-py3-none-any.whl
kgmaker scan --root /path/to/project
kgmaker inspect frontend --root /path/to/project --worker-home /path/to/trusted/workers
```

## Feature feasibility analysis (foundation)

A new isolated `kgmaker feature` workflow prepares evidence packets, validates
agent-authored candidates, stores immutable revisions and renders Czech/English
reports. It works without a diff, LLM API or semantic change packet.

```bash
kgmaker feature prepare --root . --requirement requirements/new-feature.md --id new-feature --scope production --context <context-id>
# Follow candidate-template.json and write candidate.json with the host agent.
kgmaker feature validate --root . --analysis new-feature --candidate .kgmaker/analyses/new-feature/candidate.json
kgmaker feature apply --root . --analysis new-feature --candidate .kgmaker/analyses/new-feature/candidate.json
kgmaker feature report --root . --analysis new-feature
```

`--context` is optional when the selected scope has at most one fresh compiler
context. With multiple module/profile variants, `prepare` requires the explicit
context ID and stores it with `--scope` in the packet. Validate, apply, status and
report reuse that selection; passing a different selection is rejected.

Run `kgmaker init` to install the `kgmaker-analyst` custom agent and JetBrains
analysis command instructions. See [workflow, schema and exact limitations](docs/feature-analysis.md)
and the [fixture report](docs/generated/features/additional-hedge-example.md).
This implements a subset of T001, including scoped positive availability proofs,
Flyway, explicit workspaces, bounded offline XLSX extraction and the fake Confluence
synchronization boundary. Full cross-layer paths and selective feature invalidation
remain outstanding. Positive verdicts require the
supported proof validators; existence of a field or call path alone is insufficient.

Initial field-level impact is also available for supported static dependencies:

```bash
kgmaker impact --root . --entity '<existing-field-id>' --include-data-flow --format json
```

This includes simple Kotlin expressions/constructor mappings and field inventory
for Java, TypeScript and JSON contracts. Explicit JVM inspection additionally captures
[bounded Javac field transfers and manual/generated mapper helpers](docs/field-mapping.md)
with source provenance; `field_mapping_bindings` retains UNKNOWN business equivalence
and availability ([change124](docs/changes/124_fieldAndMappingFlow.md)).
Parser limitations are explicit in feature
coverage; a static path does not prove runtime availability or financial validity.
`.xlsx` workbooks contribute sheets, cells, named ranges, formula dependencies and
hash-bound cell evidence. Formulas are not evaluated and cached values retain
`UNKNOWN` freshness. Shared/dynamic/external constructs and binary `.xls` are
explicit diagnostics. Legacy `.xls` and OLE/BIFF content renamed to `.xlsx`
produce `BINARY_XLS_UNSUPPORTED` with `status: UNSUPPORTED`, byte SHA-256 and
a file locator; no workbook values are extracted. Feature packets and data audits
retain these gaps in `coverage.artifact_diagnostics` (repo-qualified in workspaces).
A binary signature identifies a container/header, not a validated Excel workbook.
`xlsx-offline-3` extracts bounded A1/range tokens without treating exponents or
function names such as `LOG10` as cells. OFFSET, shared formulas, INDIRECT,
external references and unsupported 3D/whole-row/whole-column forms remain explicit
graph diagnostics; formulas are never evaluated and audits keep UNKNOWN availability.
Literal Unicode/quoted sheet qualifiers bind to their sheet; unrecognized qualifiers
stay unresolved and cannot fall back to local cells. Spaced A1 ranges retain all cells.
Supported Thymeleaf templates contribute `${variable.path}` nodes. Literal
`addAttribute`/`setVariable` keys and literal controller template returns create
evidenced backend bindings. Static fragment declarations and references are linked
only for a unique same-scope target with exact parameter arity; literal model-path
arguments pass through fragment-scoped parameter nodes. Conditional expressions
are PARTIAL and unsupported expressions are UNKNOWN; neither is evaluated. Dynamic
or ambiguous fragment references have diagnostics and no resolved fragment edge.
Unsupported `th:each`/`th:with` local scopes and their `data-th-*` aliases do not
bind local names as global backend model variables; those expressions stay UNKNOWN.
An explicit `pdfService`/`pdfRenderer` call remains an external PDF boundary.

### Data prerequisite audit

Run `kgmaker init` to install `kgmaker-data-auditor` and the JetBrains
`kgmaker-check-data.md` command. Select the agent in the host, or ask it to follow
`.github/agents/kgmaker-data-auditor.agent.md` with your feature requirement.
The intent `/kgmaker check-data` is a routing convention.

The auditor reuses feature prepare/validate/apply/report/revise, query and
directed impact. Model work is limited to required input definitions and
business ambiguity. Unsupported claims remain UNKNOWN. Supported observed-value,
approved-mapping and scoped absence proofs are checked deterministically; the auditor
must not invent evidence or approvals. It generates an isolated report without changing
application code or running tests. The implemented command and its contract are in
[feature analysis](docs/feature-analysis.md#deterministic-data-check).


Structured data prerequisites can now be audited without a model call:

```bash
kgmaker feature data-check --root . --analysis <id> --inputs requirements/<id>-inputs.json --format json
```

The command returns a validated, unapplied candidate, static source candidates,
business ambiguities and separate tool coverage gaps. Without valid supported proof,
availability remains UNKNOWN. See [the input contract](docs/feature-analysis.md#deterministic-data-check).
Flyway schema replay, explicit multi-repository workspaces and scoped positive
availability proofs are implemented. See [commands, contracts and boundaries](docs/flyway-workspace-proofs.md).
Workspace schema v1 also accepts a versioned `release_mapping`: it emits a
cross-repository classpath edge only when one currently valid regular-file
BuildManifest output and one regular-file entry in a fresh compiler context
contain the declared SHA-256. Directory outputs/classpaths remain `PARTIAL`;
matching GAVs, filenames or class names never establish that edge.

Volitelné compiler workery a samostatný explicitní build workflow popisuje
[compiler inspection](docs/compiler-inspection.md). Maven POM discovery is
source-only; effective classpaths and fresh outputs require an explicit build
plan/import. Explicitní Maven session export v2 navíc přenáší parent/BOM,
effective dependencies a dependency management, aktivní i inherited profily,
generated source roots, compiler release a konkrétní Java/Maven toolchain.
Maven a Gradle export navíc zachovávají task/execution-level Kotlin language/API/JVM
target, relevantní flags, opt-ins a compiler plugin provenance. Tyto hodnoty jsou
zachycená konfigurace; samy o sobě nerozšiřují ověřený K1 compatibility subset.
Maven exporter zachovává skutečné soubory a SHA-256 compiler plugin classpath;
změněný plugin JAR zneplatní manifest. Neurčené Kotlin language/API defaults
zůstanou výslovně `PARTIAL`, bez uložení nepřeloženého `${...}` placeholderu.
Manifest, compiler options, dependency model, toolchain a generated roots vstupují do identity
compiler kontextu. Zdroje vytvořené annotation processorem se přijímají pouze z
explicitního úspěšného buildu, zůstávají v jeho izolovaném run adresáři a každý je
svázán hashem, execution ID a vstupním snapshotem; compiler symboly zachovají
`origin=generated`. Runtime import accepts only a supplied, hash-bound observation
manifest and never starts the application. Implementace je stále částečná;
přesný rozsah a otevřené acceptance jsou v [progress dokumentu](docs/production-analysis-progress.md).

Explicitní `runtime produce` má opt-in JDK21 SDK pro synchronní call, factory,
condition a registraci map routeru; skutečný příklad je v
[průvodci runtime capture](docs/runtime-trace.md). Scan, hook, feature a import
aplikaci nespouštějí. Uzavřený v2 kontrakt přijímá pouze ověřené symbol IDs,
typové výsledky a diagnostické kódy; volný text, payloady a neznámá pole odmítá.
SDK nevypisuje argumenty ani návratové hodnoty a z URL odstraní credentials/query
před hashováním cesty. Jeho výsledek zůstává `PARTIAL / INSTRUMENTED_SCOPE_ONLY`.
Build/config/source/worker identity a výstupní cesta se ověří před procesem i po
něm; timeout/cancel ukončí POSIX procesní skupinu a nepřepíše platný artefakt.

```text
kgmaker runtime produce --root PROJECT --context CONTEXT_ID --runtime-id run-1 \
  --build-id BUILD_ID --config-fingerprint CONFIG_FINGERPRINT --service-id orders \
  --service-version 1.2.3 --output .kgmaker/runtime/trace.json \
  -- java -cp classes example.TraceApplication MAIN_ID FACTORY_ID TYPE_ID CONDITION_ID HANDLER_ID
```

Jde o explicitně instrumentovaný JDK21/POSIX subset; neprokazuje automatický
Spring capture, RTA/value-flow/async, nasazení ani dostupnost dat. V1 import
zůstává kompatibilní; v2 musí mít všechny identity a `PARTIAL/UNKNOWN` se
nepovýší. Výstupy jsou omezeny na `.kgmaker/runtime/*.json` a stdout.
[Změna a provedené kontroly](docs/changes/122_runtimeTraceProducer.md).

Explicitní build plan přijímá `--java-home`. Plán uloží kanonický JDK home,
SHA-256 `java` a `javac` a fingerprint volby, při spuštění nastaví `JAVA_HOME`
a JDK `bin` na začátek `PATH`. Změněná či chybějící binárka zneplatní plán ještě
před vytvořením run adresáře. Pokud Maven/Gradle exporter ohlásí jiný Java home,
výsledek je `TOOLCHAIN_UNAVAILABLE`, má diagnostiku
`EXPLICIT_TOOLCHAIN_MISMATCH` a nepublikuje čerstvé outputs.

JVM inspection v ověřeném Kotlin 1.9 compatibility subsetu zachovává přesné
constructor, lambda a callable-reference identity a compiler-resolved uživatelské
operátory. Operator call site vstupuje do source CFG; inline/default/suspend jsou
metadata, nikoli tvrzení o provedení compiler-generated body nebo coroutine state machine.
Opt-in `kgmaker inspect code --root project --kotlin-backend k2 --kotlin-version 2.1.10`
používá samostatně připravenou Standalone Analysis API/FIR distribuci. K2 backend
nepřechází na K1; jiné verze či nepodporované captured flags/plugins odmítne před
publikací. Mixed Java/Kotlin named-function calls mají compiler-owned JVM identity
a backend/version provenance. K2 source CFG, property/lambda execution a širší
Kotlin matice zůstávají PARTIAL; výchozí `--kotlin-backend k1` zachovává ověřený
compatibility subset. Explicitní builder, classpath a omezení jsou v
[compiler inspection](docs/compiler-inspection.md#t003-s04-w01--explicitní-k2-analysis-api).

Custom Kotlin getter/setter mají vlastní method/CFG a property access používá přesný
`ACCESSOR` call site. Class property initializers a `init` bloky patří ve zdrojovém
pořadí do primary-constructor CFG. Top-level properties používají file-facade
`<clinit>()V`; object/companion initializers zůstávají v constructor realm svého objektu.

Spring projection v podporovaném annotation subsetu rozlišuje aktivní, neaktivní
a neznámé `@Profile`, `@ConditionalOnProperty`, `@ConditionalOnClass` a custom
`@Conditional`. Pouze jediný aktivní kandidát dostane `injects_bean`; neznámé nebo
víceznačné varianty zůstávají `may_inject_bean`. Qualifier/Primary, short-name guard
a self-invocation proxy boundary jsou součástí stejného context-bound výsledku.
Aktuální Spring rules v9 navíc oddělují deklaraci advice od proxy-eligible cesty:
pozitivní `may_traverse_proxy`/`may_apply_advice` vyžaduje compiler call z jiného
beanu, přesnou compiler FIELD identitu receiveru shodnou s explicitně
`@Autowired`/`@Inject`/`@Resource` aktivní injection,
explicitní aktivní `Enable*` policy a
interceptable JDK interface nebo CGLIB class metodu. I tak zůstává execution
`NOT_OBSERVED` a availability `UNKNOWN`. Self-call má synchronní `bypasses_proxy`;
`@Async`, `@EventListener` a přesný Reactor Publisher return vytvářejí oddělené
boundary bez domyšleného scheduling/subscription. AspectJ mode bez doloženého
weaving artefaktu a local/new receiver bez FIELD provenance zůstávají UNKNOWN.
Process view označí Async continuation jako oddělenou pouze pro doložený proxy
path; self-invocation rozvine synchronně jen s compiler receiverem `THIS`/`SUPER`.
Stejný owner volaný přes parametr nebo jiné pole zůstává UNKNOWN, není vydáván za
self-call. Podporovaná matice a negativní případy jsou v
[compiler inspection](docs/compiler-inspection.md#t003-s05-w04--proxy-weaving-a-async-boundaries).

```bash
kgmaker inspect code --root app --manifest build-manifest.json --format json
kgmaker graph view --root app --view configuration --scope production --format json
```

První příkaz je jediný explicitní compiler krok; druhý pouze čte uložený context.
Compiler-symbol meta-anotace se rozvíjejí nejvýše osm kroků a explicitní
`spring_component_packages` určuje ACTIVE/INACTIVE scan scope; bez něj je dostupnost UNKNOWN.
Collection/map injection zachovává všechny aktivní členy, Optional může vybrat
unikátní aktivní bean a ObjectProvider/Provider zůstává lazy `may_inject_bean`.
Pravidla v5 počítají dosažitelnost `@Configuration` přes component scan a
statické `@Import`: importovaná konfigurace může ležet mimo scan scope, její
class condition se přenese na `@Bean` metody a `@Bean` mimo konfiguraci nevytvoří
bean. ImportSelector/DeferredImportSelector mají přesnou compiler-qualified
transitivní identitu. Java metoda s jediným literal `String[]` return propojí
deklarované konfigurace přes `selects_import`; neznámé tělo, custom filter/group,
chybějící target nebo překročený limit zůstává UNKNOWN / `may_select_import`.
Selektory, Spring ani aplikace se nespouštějí; registrar zůstává boundary.
Tento omezený Java subset sdílejí distribuce K1/K2 a nejde o rozšíření Kotlin
source/CFG matice nebo důkaz runtime registrace či dostupnosti dat.

V5 navíc zachytí compiler-qualified literal `ImportBeanDefinitionRegistrar`
registraci přes `registerBeanDefinition("name", new RootBeanDefinition(Type.class))`.
Podmínka pochází z importující konfigurace. `FactoryBean<T>` rozlišuje objekt
`&name` a produkt `name`; ACTIVE statická deklarace produktu vyžaduje shodný
konkrétní generic typ, jediné `return new Type()` a jediné `return Type.class`.
`@Bean` producer musí navíc přímo vracet jediný konkrétní no-argument constructor
bez anonymous overrides; proof pochází ze skutečné implementace a produceru.
Custom těla, větve, neznámé typy a abstract factories zůstávají UNKNOWN.
Žádný registrar, factory, konstruktor nebo Spring context se nespouští; statická
deklarace není runtime availability. Přesný bounded scope a testy:
[change note47](docs/changes/47_declareSpringRegistrations.md).

JPA rules `annotation-source-v8-jpql-hql-grammar` oddělují `@Entity`,
`@Embeddable` a `@MappedSuperclass`, určují
FIELD/PROPERTY access podle umístění identity, modelují `@EmbeddedId` a přesný
`@AttributeOverride` a rozlišují owning/inverse asociace přes `mappedBy`.
Vztahový atribut nevytváří smyšlený scalar column; explicitní JoinColumn/JoinTable
zůstává samostatným mapovacím objektem.
Bounded Spring Data parser ověřuje derived query properties proti entity,
association a embedded atributům, zachovává operátory a `OrderBy` a rozlišuje
čtení od delete intentu. Neznámá property nevytvoří resolved hranu.
Compiler-owned `@Query` rozlišuje JPQL a native SQL, kontroluje named parametry,
návratovou entitu/projekci a váže statické dotazy na entity, atributy nebo přesné
ORM tabulky. Bounded JPQL/HQL grammar navíc rozlišuje root a association join
aliasy, subquery reads, bulk `UPDATE`/`DELETE`, `select new` constructor projection
a clause-specific path edges (`projects_attribute`, `filters_by`, `orders_by`,
`groups_by`, `updates_attribute`). Hibernate `join ... with` je explicitní
podporované rozšíření; `lateral`, set/window operace, `treat`, collection-index
funkce a další nepodporované fragmenty zůstávají PARTIAL s query offsetem,
řádkem a sloupcem. Konzumovaná bounded gramatika ověřuje pořadí klauzulí,
projekce, přiřazení a predikáty (porovnání, AND/OR/NOT, EXISTS, IN, BETWEEN,
LIKE a IS NULL). Alias je case-insensitive a patří konkrétnímu bloku SELECT;
vnořené závorky scope nemění. Neplatný nebo nerozvázaný alias ani neúplný
výraz nevytvoří query read/write/path edge. Podporované funkce a limity
uvádí [compiler dokumentace](docs/compiler-inspection.md);
opravy a skutečné kontroly [change116](docs/changes/116_parseExtendedJpqlHql.md). Statické `@NamedQuery`/`@NamedNativeQuery` i repeatable
`@NamedQueries`/`@NamedNativeQueries` mají vlastní definici a repository metoda
se na ni váže přes `uses_named_query`. Stejný katalog přijímá ORM XML
`named-query`/`named-native-query` v kořeni i entity/mapped-superclass s hashovanou
provenance. `@Query(name="Order.byStatus")` vybere právě jednu úplnou deklaraci
ve vybraném compiler/persistence kontextu; duplicita (včetně XML/anotace), chybějící
jméno nebo tělo zůstává UNKNOWN. Named reference používá stejnou JPQL gramatiku,
kontrolu pojmenovaných a číslovaných parametrů a compiler-owned projekcí jako
přímý dotaz. Native `resultClass` a XML `result-class` se vážou na přesný compiler
typ; `resultSetMapping` zůstává PARTIAL. Native tabulky se hledají až v konečném
XML mapování a pouze mimo SQL literály a komentáře; typ operace určuje první
statement keyword za komentáři. Neúplná lexikální struktura nebo chybějící
podporovaná table reference zůstává UNKNOWN. Skutečná Javac fixture a hranice podpory jsou v
[change120](docs/changes/120_namedQueryContainers.md) a
[compiler dokumentaci](docs/compiler-inspection.md#named-query-containers-t003-s06-w06).
K2 inspection navíc zachovává compiler-resolved Kotlin annotation identity a
explicitní `@field:`/`@get:` target. JPA FIELD/PROPERTY access se z constructor
properties vybere jen z jednoznačného identity targetu nebo `@Access`; běžné
`@Id` bez jednoznačného targetu zůstává UNKNOWN s diagnostikou. Embedded Kotlin
ID tak zachovává stejné `orm_attribute`/`orm_embeddable` uzly jako Java cesta.
JPA annotation constants, nested `@AttributeOverride` columns a class literals
pocházejí z compiler values; částečně nevyřešená explicitní `@Table`, `@Column`
nebo override hodnota nevytvoří defaultní fyzické mapování. K2 fixture používá
JPA FIELD/METHOD annotation targets, aby ověřil skutečný implicitní FIELD
default i samostatnou dual-use-site ambiguity. Kotlin embeddable columns se
promítnou jen při ověřeném explicitním accessu nebo jednoznačně FIELD
inheritance; nepodložený či smíšený access zůstává UNKNOWN. JPA identity musí
patřit přímo do `jakarta.persistence` nebo `javax.persistence`; podobně
pojmenovaný subpackage není JPA evidence.
Vybraný persistence unit může doplnit standardní `META-INF/orm.xml` nebo
pořadově deklarované mapping files. XML class/table/column mapping má přednost
před annotations a evidence uchovává cestu, hash souboru, persistence unit i
pořadí; `metadata-complete` potlačí nevyjmenovaný annotation fallback. XML je
omezeno na přesné compiler class identity a podporovaný scalar subset. Neznámý
namespace/verze, nepodporovaný construct, neúplný override, DTD/entity nebo
soubor mimo repository root zůstává UNKNOWN bez fyzického annotation fallbacku.
Mapped-superclass persistent fields/methods jsou projektovány na každou ověřenou
entitu se samostatným `declaring_owner` a `effective_owner`; `inherits_attribute`
zachovává deklarující uzel. Compiler identity určuje přesný parent type a ID
placement zdědí access strategy. Fixture ověřuje K2 i Javac, řetězené mapped
superclasses, FIELD/PROPERTY access, tři JPA inheritance strategy values,
entity-level override precedence a kolizi atributu. Kolize a unresolved override
zůstávají UNKNOWN bez vybraného column edge; graph/store schema zůstává v3.
Spring Data repository generic selects its entity by exact compiler-qualified
owner. Same-simple-name entities no longer share inherited attributes; an
unresolved generic remains unbound rather than using a simple-name fallback.
Explicit JPQL entity names and repository return types also resolve by compiler
owner; simple source return names require an exact JVM method descriptor owner.
Missing qualified types and generic type variables remain UNKNOWN rather than
binding to an unrelated same-simple-name class.
Java/Javac má nyní [bounded Criteria/Specification/QueryDSL projekci](docs/programmatic-queries.md):
entity-root selection a equality predicates přes skutečné compiler API/binding
identity včetně unique repository fragments. `query` zůstává null, dynamické
části PARTIAL/UNKNOWN a dostupnost UNKNOWN. [Change129](docs/changes/129_criteriaSpecificationQuerydsl.md)
uvádí actual API/APT fixture, kompatibilitu a cílené výsledky. Širší provider
syntax, Kotlin programmatic dotazy a úplná schema/deployment availability
zůstávají mimo tento rozsah.
K2 worker zvolíte výslovně při inspekci, například
`kgmaker inspect code --root . --kotlin-backend k2`; chybějící K2 distribuce
nepřejde na K1.


## Compiler lifecycle

`scan`, `hook-context` and single-root `feature prepare` retain the saved compiler
symbols, call sites, CFG and evidence after validating source/configuration,
classpath artifacts and worker distribution hashes. They never execute a compiler
or build. When compiler inputs change, only the affected compiler layer is removed
from the current projection. Its context remains marked `STALE` with the reason and
an exact `inspect code` or `inspect frontend` command; other valid contexts remain usable.

```bash
kgmaker inspect code --root project --classpath project/target/classes
kgmaker scan --root project
kgmaker hook-context --root project
```

Module/profile contexts accumulate under distinct selection keys and compiler
symbol IDs include their context identity; refreshing one selection replaces only
that selection. Workspace snapshots preserve compiler symbols, call sites, CFG,
evidence and annotations under repo-qualified identities. Feature packets preserve
the same explicit scope/context used by query and impact. The real JVM fixture
verifies the full lifecycle, profile selection and classpath invalidation within
the published matrix in
[T003-S02](docs/tasks/3_finishProductionAnalysis.md#t003-s02--jednotný-provider-a-lifecycle-grafu).

Use `query --context CONTEXT_ID` or `impact --entity ENTITY_ID --include-data-flow
--context CONTEXT_ID` when several compiler contexts are available. Feature packets
retain context fingerprints and evidence IDs. Offline approved methodology
provenance is supplied through the hash-bound sidecar described in
[feature analysis](docs/feature-analysis.md); conflicts remain review items.

Gradle source-set exporter v2 uses model identities, with exact built-in scopes for
`main`, `test`, and `testFixtures`. For a custom set, declare its analysis scope in
the build model: `ext.kgmakerSourceSetScopes = [integration: 'test']`. Unmapped
sets (including names containing `test`) remain `unknown` with a diagnostic;
SOURCE_ONLY never executes Gradle. See [compiler inspection](docs/compiler-inspection.md).

Compiler freshness for an imported source set uses its module/source-set membership
and shared root/module configuration, including Gradle scripts and catalogs.
An edit to a sibling source set with the same scope does not invalidate the selected
variant. Changing selected resources or shared configuration still requires inspection.
`scope_origin=GRADLE_CONVENTION` accepts only main→production, test→test and
testFixtures→test_fixture; older manifests without provenance retain legacy compatibility.

Explicit Gradle composite builds inside the captured project tree now export each
included build with a build-root-qualified repository identity. Duplicate module
names remain separate; resolved dependency artifacts retain their owning realm
only when a unique execution-bound producer output matches the artifact, and retain
exact Gradle classpath order. `kgmaker project build-plan --build-system gradle
--offline --output /tmp/composite-plan.json` and explicit `project build-run`
perform the export; scan/feature/hook never launch Gradle.

Offline methodology approval is bound to the exported page and approval sidecar hashes. `kgmaker feature prepare --requirement requirement.md --id routing` omits stale documentation conflicts with an explicit limitation; run `kgmaker docs check --confluence-dir export` before preparing a fresh packet. Already prepared packets become stale when that external documentation evidence changes. Duplicate decisions for one assertion are rejected without replacing the validation cache.

Dependency dispatch používá bounded ordered classpath metadata index pro skutečné
JARy/adresáře. Javac, K1/K2 call expressions a ASM virtual/interface sites zachovávají
oddělený declared target a konzervativní kandidáty v artifact realms; nikdy tím
nedokazují runtime execution ani data availability. Reference/static/private/final
calls nejsou virtuálně rozšiřovány. Missing/corrupt/shadow/truncated hierarchy a
unsupported multi-release candidate enumeration mají konkrétní důvod, `dispatch_complete=false`.
Příklad: `kgmaker inspect code --root project --kotlin-backend k2 --kotlin-version 2.1.10`
po explicitním build-importu; [matice a limity](docs/compiler-inspection.md#t003-s04-w04--ordered-dependency-dispatch).

Source type-variable/intersection receivers zůstávají explicitně unsupported bez
kandidátů; jejich declared target se zachová. Podporovaná candidate class musí
splnit receiver i declared contract. Physical lookup odděluje source overlay,
respektuje skutečné JDK parent-first a runtime-effective MR metadata; známý
source/binary static ABI nebo repo/module/source_set/scope realm konflikt vrací
PARTIAL bez vymyšleného targetu a zachovává source canonical.

`inspect code` with an explicit execution-bound bytecode build now emits
`maps_to_source` declaration evidence for exact Java/Kotlin declarations with
compatible compiler-proven static/instance ABI,
Kotlin 2.1.10 `DefaultImpls` with verified interface/receiver structure, and
simple same-owner compiler bridges. Generated method IDs remain distinct.
Unproved mappings emit `BYTECODE_ONLY_SOURCE_MAPPING`; debug lines alone do not
prove a source call expression. See [compiler scope](docs/compiler-inspection.md#default-body-source-mapping).

Explicit compiler inspection now records version1 `argument_to_parameter` bindings
for supported Javac, K1 and TypeScript call expressions. Each proof retains its
original call site, formal index, context and direct/vararg transformation.
Named/default Kotlin arguments follow compiler binding, with omitted defaults
marked as not evaluated. These are bindings to the declared contract; dispatch
candidates remain candidates and availability stays UNKNOWN. K2 Kotlin and
unsupported/erroneous bindings expose specific UNKNOWN boundaries.
`kgmaker flow render --entry METHOD_ID --view process --format json` includes
binding status; `kgmaker impact --entity ARGUMENT_ID --include-data-flow --format json`
retains supplemental binding provenance. See [binding scope](docs/compiler-inspection.md#argument-to-parameter-bindings).

React UI inspection (`kgmaker inspect frontend --root /repo --ui-framework react`)
uses opt-in `react-jsx-events-4`: React18.3.1/@types/react18.3.18 with the pinned
compiler declaration hash. Intrinsic event props and one verified source forwarding
wrapper retain package/declaration provenance. Unknown versions, fake modules,
mutable callbacks and unproved wrappers remain UNKNOWN. No React/app code executes;
static handler binding is not a click or data-availability proof. See change69.

The React subset covers pinned standard onClick/onChange/onSubmit props, including
input/select/textarea and form. Classic official factory aliases and default
automatic runtimes are supported; explicit legacy namespace/fragment/import-source
controls and per-file JSX overrides remain UNKNOWN.

Coroutine source inspection preserves compiler-proven suspend and recognized
coroutines API boundaries, with bounded named continuation declaration mapping.
Generated instructions keep bytecode-only locations; scheduling and K2 source CFG
remain unknown. See [the coroutine contract](docs/compiler-inspection.md#coroutine-source-boundaries-t003-s04-w03).

The [hand-labelled JVM corpus](tests/fixtures/jvm-golden/README.md) compares exact
compiler source-call identities, counts and unsupported boundaries for the pinned
K1/K2 support matrices. Run `python -m pytest -q tests/test_jvm_golden_corpus.py`
after preparing compiler prerequisites. Passing this corpus is bounded static
evidence, not runtime dispatch or production-project precision.
T015 adds a pure database-resource view through
`kgmaker.data_resources.project_data_resources(workspace, graph, source_coverage=coverage)`.
Pass the loaded workspace and matching `snapshot_workspace` graph/coverage. Explicit
repository/database/stream identities remain separate from table drill-down IDs.
Only existing selected-context query facts contribute read/write/delete claims;
entity mappings and migrations contribute dependencies. Flyway is
`MIGRATION_DERIVED`, with deployment and populated-data availability `UNKNOWN`.
Missing datasource mappings remain unresolved; no database connection or new CLI
command is introduced. See [data-resource boundaries](docs/compiler-inspection.md#data-resource-projection-t015).

Compiler inspection also records static return → assignment/argument/receiver
bindings with branch guards and declared nullability. Java, K1 and TypeScript
support the bounded [return-consumer matrix](docs/compiler-inspection.md#return--consumer-bindings);
K2 Kotlin source CFG, opaque/recursive/async bodies and unsupported projections
remain UNKNOWN. Process and impact reports carry the proof without runtime values.

## Explicit business-process documents

`kgmaker.process_model.ProcessDefinition` and `ProcessView` validate version1
explicit process documents using the shared view/evidence model. Stable IDs,
branches, loops, exceptions and async boundaries survive round-trip; strict
semantic labels remain separate from technical evidence and status. See
[the Python API and example](docs/process-model.md) and
[the explicit fixture](fixtures/process-model/checkout.json).
This supplies T023's model only; process discovery, annotation review, process
CLI and rendering remain separate tasks. Existing `flow render` is unchanged.

Spring condition subset v6, zachovaný v aktuálních rules v7, preserve typed compiler annotation members. Supported
profiles include OR arrays and bounded `!`, `&`, `|`, parentheses; properties
support aliases, prefix, all names, `havingValue` and boolean `matchIfMissing`.
Class conditions compare all exact identities against an explicit context
inventory. Missing/malformed/unresolved inputs remain UNKNOWN; custom conditions
are never executed. Profile results also govern injection, so `!dev` is not
incorrectly filtered as a literal profile name. See
[the condition matrix](docs/compiler-inspection.md#t003-s05-w03--typed-condition-matrix)
for the bounded contract and explicit Python API example.


### Declared Kafka workspace bindings (T003-S07-W04)

An optional versioned `kafka_bindings` block in the existing workspace manifest
projects Cloud Stream `.properties` bindings into `kafka_binding` nodes. Services
use `transport: "kafka"` and existing explicit service ownership. Matches require
the same declared logical cluster ID, case-sensitive topic, exact JSON contract
SHA, release label and scope. Base configuration precedes explicit profile
overrides; a uniquely selected fresh JVM context can supply captured property
overrides. No compiler context is fabricated for source-only configuration.

```bash
kgmaker query --root . --workspace fixtures/kafka-bindings/workspace.json orders-blue
```

See [the fixture](fixtures/kafka-bindings/README.md) and
[the bounded contract](docs/compiler-inspection.md#t003-s07-w04--declared-kafka-binding-identity).
Dynamic, missing, ambiguous or unsupported inputs remain UNKNOWN. Cluster, release
and payload labels are declared; delivery, deployed schema and data availability
remain unproven. Revision2 optionally verifies explicit schema2 code refs against
current canonical listener/send facts and exact topic/group agreement. Config-only
bindings retain code_binding UNPROVEN. Java listener/send support uses either
worker backend; Kotlin listeners require K1 captured annotations. Regex selectors
remain candidates; Kotlin producers and K2 Kotlin listeners remain UNKNOWN. Legacy name-only Kafka hints remain separate syntax
evidence. Scan/query/feature/data checks never start a broker, application or build.


Kafka privacy rules (retained in `kafka-binding-3`) reject credential and broker-connection
property keys before alias lookup, including nested references in captured
properties. These bindings stay UNKNOWN. Public workspace contexts redact
sensitive captured Spring property values and retain an explicit projection
marker, original context identity and property-map hash. The private captured
context remains the authority for validation and selection.
### Proven trigger inventory (T024)

`kgmaker.process_triggers.discover_process_triggers(workspace, graph,
source_coverage=coverage)` returns a shared process-kind trigger inventory from
existing proved HTTP/Kafka/scheduler facts. Missing CFG retains a candidate with
an explicit body gap; unsupported K2 annotation capture remains UNKNOWN. No
process paths, business identities, worker execution or runtime availability are
inferred. See [API and boundaries](docs/process-triggers.md).

### Explicit persistence realm selection (T003-S06-W04, bounded subset)

For physical schema links, provide database_id and schema_stream_id explicitly
in the JVM build context and database_id/stream_id in each workspace repo.flyway
configuration. Distinct databases may reuse a stream name. Optional
persistence_schema and flyway_target selectors constrain the supported offline
replay target; ambiguous or missing realm evidence remains UNKNOWN. Python
inspect_jvm(..., build_context={...}) and existing imported build-manifest
inspection carry these fields; the CLI remains kgmaker inspect code --root app
--build-id BUILD_ID. Offline snapshot_workspace then joins existing fresh compiler
facts to its explicit replay schemas; it never runs a worker, app or database.
Legacy source-only @Table/@Column fields do not create new strong persisted_in
links without a proven realm. Supported physical replay binding currently covers
non-renamed table/column identities; creation-stable IDs after a rename remain
UNKNOWN pending S06-W08 lifecycle proof. See docs/changes/74_isolatePersistenceRealms.md for
actual validation and incomplete scope.

Po explicitní JVM inspekci lze uložené query uzly vyhledat bez spuštění workeru,
aplikace nebo databáze, například:

```bash
kgmaker inspect code --root app --build-id BUILD_ID
kgmaker query --root app --scope production JPQL PurchaseOrder
```

Výsledek je statický persistence intent, nikoli důkaz provedeného SQL, commitu
nebo dostupnosti dat.

HTTP client intent (T003-S07-W06): with an explicit JVM inspection, `flow render --view
integrations --format json` includes `http.requests`; process JSON/Markdown shows
request definitions separately from terminal intent. Real Spring 6.2.2 / Reactor
3.7.2 Java calls are compiler-attributed in both workers. An unused WebClient
publisher is `UNSUBSCRIBED_WITHIN_SCOPE`; a same-origin `block`/`subscribe` is a
static trigger, never observed network execution or available response data.
See [the supported HTTP matrix](docs/compiler-inspection.md#http-client-intent).

HTTP proof rule2 treats loop/try control as UNKNOWN, preserves Feign client/method
path components without guessing a composed route, and rejects URI-callback route
guesses. Prior HTTP rule1 indexes require explicit reinspection; reading never
starts a worker. See the HTTP matrix for property-file and privacy boundaries.

### Local technical process paths (T025)

`kgmaker.process_paths.build_local_process(graph, trigger_inventory, trigger_id,
process_id="process:caller-selected", max_nodes=200)` adapts existing source CFG
topology into a typed T023 ProcessView. Branches, call-sites and exception paths
are preserved; root budgets, recursion, uncertain dispatch and missing/async
bodies stay explicit boundaries. No business identity or runtime execution is
inferred. See [API, selected-snapshot proof and limits](docs/process-paths.md).

### Kafka interface catalogue

The pure [Kafka catalogue](docs/kafka-interfaces.md) projects explicit upstream
listener/send declarations and declared bindings into the shared interfaces view.
Broker realms and consumer groups remain distinct; configuration-only and regex
subscriptions retain their unresolved boundaries. Explicit workspace/private
compiler indexes are required; the projection performs no inspection or transport.
### HTTP consumer catalogue (T011)

`kgmaker.interfaces.project_http_consumers(workspace, graph, scope="production",
source_coverage=coverage)` projects selected typed W06 requests into the shared
interfaces view. Lazy definitions remain distinct from static terminal intent;
Feign caller occurrences and same-path calls keep their original IDs. No client
is run, and runtime/remote service binding stays unknown. See
[HTTP consumers](docs/http-consumers.md) for the explicit snapshot example and
proof/compatibility boundaries. No new CLI command is introduced.

T025 revision2 adds optional `java-local-operations-1` compiler evidence for a
bounded Java literal/local-variable subset. It keeps source CFG ordering as
SYNTAX_CANDIDATE and resolves only independently certified operation nodes;
transitions, execution, business meaning and data availability are not promoted.
Legacy/Kotlin/unsupported operations remain unresolved. The bounded implementation
merged in PR65 (`32a3bca`); current full acceptance has not been rerun. See
[local process scope](docs/process-paths.md#compiler-bound-local-operations).
### Kafka interface catalogue

The pure [Kafka catalogue](docs/kafka-interfaces.md) projects explicit upstream
listener/send declarations and declared bindings into the shared interfaces view.
Broker realms and consumer groups remain distinct; configuration-only and regex
subscriptions retain their unresolved boundaries. Explicit workspace/private
compiler indexes are required; the projection performs no inspection or transport.

### Explicit interface contracts (T013; merged PR74)

[Contract attachments](docs/interface-contracts.md) preserve interface identities
while adding explicit content-bound provider/client declaration references.
Generated-client origin survives stale contract hashes. Payload compatibility and
runtime/data availability remain unknown; no generator or schema fetch runs.

The pure [T026 business-step API](docs/process-paths.md#reversible-business-step-projection-t026-candidate)
reversibly groups only adjacent certified local operations in an explicit process
view. It preserves unresolved CFG adjacency and all origins; it does not approve
business semantics or observe execution. T026 merged in PR66 (`9442114`) after the PR65 prerequisite.

The [T027 HTTP process-boundary API](docs/process-paths.md#explicit-http-process-boundary-t027)
joins an exact local HTTP callsite to a T014 validated remote binding and, when
provided, the matching target service/context process snapshot. Missing or
ambiguous targets remain external boundaries while local continuation is kept;
transport failures do not become business outcomes. Each request starts at its exact caller node. Only normal target exits rejoin
proved normal caller continuations; server exceptions remain transport boundaries.
Unsupported T014 versions, stale binding/endpoints and foreign target selections
cannot authorize expansion. Imported diagnostics, limits and truncation remain visible.
It is a Python API over
explicit snapshots and adds no CLI command or persistent data format
([change123](docs/changes/123_crossHttpProcessBoundary.md)).

The [T028 asynchronous process API](docs/process-paths.md#potential-asynchronous-process-paths-t028)
projects explicit Kafka publish/channel/subscription memberships into potential
consumer paths. Fan-out branches have no order between consumers or return to the
publisher. Missing consumers, correlation, loops and truncation remain visible;
static bindings do not prove instance correlation, delivery or completed processing.
Endpoint and binding proofs gate expansion independently of summary flags; rejected
proofs and conflicting release selectors remain visible without duplicate consumer paths.
See [change127](docs/changes/127_crossAsyncProcessBoundary.md).

Service inventories distinguish compiler/source ownership from canonical
workspace-derived declarations. Kafka binding inputs may reference another
repository's schema without becoming service-owned code or compiler candidates.
`t008-service-inventory-2` retains the original full graph for downstream views;
unknown derived contracts get diagnostics, and legacy SOURCE_ONLY coverage keeps
its PARTIAL/UNKNOWN boundary. See [context-role boundaries](docs/architecture.md#workspace-derived-context-roles).
### Kafka retry/DLT declarations — T003-S07-W05 (merged PR71)

The bounded `kafka-retry-1` adapter records pinned Spring Kafka3.3.2 policy
declarations as separate async boundaries, without executing listeners or brokers.
Unsupported/custom policy stays UNKNOWN; execution/delivery remain NOT_OBSERVED.
See [scope and historical validation](docs/kafka-retry-dlt.md). The bounded
implementation merged as `3e5ef0f`; broader production acceptance remains PARTIAL.

### Schema compatibility (T003-S06-W08 bounded scope)

`kgmaker schema compatibility --root /path/to/repo --config flyway.json --database money --stream main --target 1 --context CONTEXT_ID`
uses existing offline replay and an explicitly inspected compiler context. It
reports COMPATIBLE/CONFLICT/UNKNOWN per type/nullability/decimal/key dimension;
legacy or unsupported mapping stays UNKNOWN. See [supported scope and evidence](docs/schema-compatibility.md).
W04 dependency PR62 and compatibility PR64 (`3bef611`) are merged. Historical
validation is recorded in note78; compatibility never proves deployment or
populated-data availability. No implicit worker/build/migration/DB operation.

### Pure process label packets (T030)

`kgmaker.process_semantics.prepare_process_label_packet(process_view,
token_budget=8000, char_budget=32000)` returns a content-bound packet and empty
PROPOSED candidate template for existing targets. It preserves selected identity,
provenance and uncertainty, reports complete serialized cost/mandatory overflow,
and hash-omits raw labels, documentation and proof/configuration prose. It performs
no model/compiler/file I/O or apply. See [contract and privacy limits](docs/process-label-packets.md).
T031 adds explicit validation and T032 adds local review below; T034 CLI remains planned.

## Project templates, test proposals and delivery traceability

`kgmaker template` manages project-local, versioned artifact templates for requirements,
analyses, implementation tasks, test cases/data/code and filenames. `kgmaker init`
installs editable defaults while preserving user files. `kgmaker testgen` prepares
bounded evidence for **existing functionality without a diff**; the host Copilot
agent proposes cases, synthetic data and code, then kgmaker validates citations,
constraints and freshness before an explicit export. It never calls a model API
or runs the proposed tests. Code-derived expectations are characterizations,
not independent business correctness proofs.

```bash
kgmaker template list
kgmaker testgen prepare --id regression --target src/calculator.py --scope all
kgmaker testgen validate --id regression --candidate candidate.json
kgmaker testgen apply --id regression --candidate candidate.json
kgmaker testgen export --id regression
kgmaker trace sync-task --id <runtime-task-id>
kgmaker trace sync-analysis --id <analysis-id>
kgmaker trace sync-testgen --id regression
kgmaker trace show <reference> --format markdown
```

`trace` records explicit, revision-bound links from requirements through analyses,
tasks and changes to tests. Local requested/approved/rejected/revoked decisions
show who recorded them and when, with `LOCAL_DECLARED` identity trust. Optional
approval gates are disabled by default. They can require approval of the current
request/plan before implementation and a source-bound review before completion.
Generated tests remain `NOT_RUN` until separately executed by the project runner.
See [workflow, schemas, examples and limitations](docs/delivery-workflow.md) and
[specification T046](docs/tasks/46_addTemplatesTestsAndTraceability.md).

Test/code/data exports require canonical repository-relative paths; aliases such
as `./.github/...` and reserved metadata segments are rejected. Workflow writes
preserve artifact history and require the current task revision for updates;
concurrent task creation returns the existing state. All mutating trace commands
support `--expected-revision`; a stale value fails without changing the journal.
Dataset enum and foreign-key comparison uses JSON types, distinguishing booleans
from numbers and absent target keys from explicit null values.

Etapy T046-S01 až S06 jsou sloučené; S06 zpřístupňuje jejich knihovní kontrakty
přes CLI a instalované instrukce. Přesné výsledky a omezení jsou v change notes
56–61; post-merge srovnání stavů je v [change113](docs/changes/113_reconcileT046DeliverySummary.md).

## T003-S07-W07 — explicit remote mapping (merged PR76)

See [remote mapping contract](docs/remote-contract-mapping.md)
and [note91](docs/changes/91_planRemoteContractMapping.md).
Explicit capture and pure resolution preserve service/context/contract/release
authority; HTTP and Kafka remain distinct declared boundaries, no JVM calls or
runtime/payload availability promotion. Source-specific cohort334 unique PASS;
combined descendant2df full2587PASS/10optionalSKIP includes all1973 W07-parent
cases (1963PASS/10SKIP). This historical full did not run standalone on W07. The implementation merged
as `5ffe099`; it does not certify the entire current production matrix.

### Read-only process annotation validation (T031)

`kgmaker.process_semantics.validate_process_annotations(process_view, packet,
candidate, documents=(), conflicts=())` rederives the complete current T030 packet
before checking proposed labels, descriptions, references and grouping. Invalid
input returns fixed-code diagnostics; valid proposals remain PROPOSED and
PENDING/CONFLICT for review. No apply, model/API, file I/O or technical changes.
See [the Python contract](docs/process-annotations.md). T034 CLI remains pending.

### Explicit local process review (T032; merged PR78)

`kgmaker.process_store` adds prepare/persist/read APIs for bounded immutable semantic
review history and explicit APPROVE/REJECT, with cooperating POSIX process/thread
CAS. The technical ProcessView stays unchanged; documentary citations stay separate.
See [API, limits and recovery](docs/process-review-store.md) and its verified descendant proof; there is no T034 CLI or authenticated reviewer identity.

### Explicit process catalog (T033; merged PR79)

`kgmaker.process_catalog.catalog_business_processes` combines explicit current and
historical ProcessViews with a supplied T024 inventory and validated T032 reads.
It preserves process identities/revisions and separate per-member review states;
labels/shared helpers never deduplicate operations. Optional one-hop aliases retain
all original members without approval/availability borrowing. Missing triggers
remain inactive historical within the partial current selection. See
[Python contract and limitations](docs/process-catalog.md). The bounded catalog
merged as `5095343`; current full acceptance has not been rerun. No discovery, archive reconstruction, store write or CLI.


### T014 static remote topology

`kgmaker.remote_interfaces.project_remote_interfaces(workspace, graph, interfaces,
captured=captured, scope="production")` projects the explicit W07 capture handoff
into a ViewDocument. Candidate ambiguity and unresolved boundaries remain visible;
HTTP/Kafka declaration edges are not JVM calls or observed execution. See
[contract and limits](docs/remote-interfaces.md). Merged in PR80 (`ec6a127`); historical source-qualified validation remains in
the capability document. No current full or remote execution is claimed.

### T016 common-capture topology

`kgmaker.service_topology.capture_topology_inputs(manifest, scope="production")`
uses one explicit closure for T015/W07/T014, then rereads it.
`aggregate_service_topology(captured)` is a pure ViewDocument projection with
reversible HTTP summaries and Kafka realm/topic channels plus separate groups.
No JVM/process/runtime or payload claim is added. See
[handoff and limits](docs/service-topology.md). Merged in PR81 (`130720f`); historical source-qualified results remain in
the capability document. Current full acceptance has not been rerun.

### T017 bounded topology filtering

`kgmaker.topology_filter.filter_topology(topology, focus_service="service:checkout",
direction="outgoing", max_hops=2, max_nodes=25)` filters a captured T016 view
without I/O. Its `{document, filtering}` result preserves original edges and
uncertainty and reports complete known omission IDs plus separate frontier metadata.
Kafka channels count as real hops; omitted nodes never create shortcut edges.
See [API and limits](docs/topology-filter.md). Merged in PR82 (`4e4fcd6`). T019 exposes filtering through architecture
JSON CLI; standalone filtering remains a pure Python API.

### T018 snapshot explanation

`kgmaker.view_explanation.explain_view_element(view, element_id, captured=captured,
graph=original_public_graph)` expands exact origins and evidence from the bound
T016/T017 snapshot. Optional `capture_explanation_source_status` separately reads
only validated, confined graph locators; pure mode is NOT_CHECKED, never CURRENT.
See [API and limits](docs/view-explanation.md). Missing ranges remain unavailable.
Merged in PR83 (`1005b9f`). Historical source-qualified validation is retained
in the capability document; current full acceptance has not been rerun.

### T037 derived-view cache

`kgmaker.view_cache.get_or_build_view(...)` accepts explicit workspace/graph
snapshots, rule versions, scope and context selection. It reuses a serialized
`ViewDocument` only when the complete dependency fingerprint matches; new provider
declarations therefore revalidate old unresolved lookups. Cache writes happen
only through this explicit API after builder output validates. The topology CLI
also accepts an explicit `--view-cache PATH`; its default remains cache-free.
CLI publication follows filter/fingerprint/output validation and successful stdout
write/flush, only on exit 0. Rejected requests preserve input files and the previous
cache. Cache targets cannot alias inputs, symlinks or hardlinks; with local capture,
a target inside a source repository must be under `.kgmaker/views/`.
See [cache API and limits](docs/view-cache.md) and
[T037 change note](docs/changes/121_invalidateDerivedViews.md).

### T019 architecture JSON CLI

`kgmaker architecture topology --capture-snapshot topology-inputs.json` replays
explicit snapshots and preserves the full filtering envelope. Interfaces and explain
commands share fixed safe JSON diagnostics; local capture/source checks require
explicit flags. See [commands and boundaries](docs/architecture-json-cli.md).
Merged in PR84 (`a60f02d`). T020 interface Markdown is also merged;
T021 topology Mermaid remains planned.

The W07 resolver and T014 projection also preserve the no-I/O contract on their
first call after normal API import. The cold-process regression is protocol-only;
see [the correction and remaining validation](docs/changes/108_fixColdRemoteProjection.md).

### T020 interface Markdown (merged PR87)

`kgmaker architecture interfaces --catalog http-providers --interface-capture interfaces.json --format markdown`
renders the same T019 snapshot as a bounded escaped catalog with original IDs,
contract revisions and internal evidence links. Generated/unclassified rows,
unknowns and diagnostics stay visible; no current source or runtime proof is added.
JSON stays default. See [contract and parser checks](docs/interface-markdown.md);
Merged in PR87 (`250e7c1`) with the first-call purity correction.
Topology/explain remain JSON-only; T021/T022 are planned. Historical checks and
current verification limits are in the delivery inventory.
