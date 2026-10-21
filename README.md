# kgmaker

**A local knowledge graph for GitHub Copilot CLI.** kgmaker maps files, declarations, imports, database tables, Kafka topics, API endpoints, frontend routes, and likely cross-file calls. Copilot receives a lean bootstrap at session start and retrieves task-specific graph locations and prior implementation episodes on demand. The source-only Python core runs locally using the standard library. Optional compiler inspection requires separately installed JDK/Node workers. JVM inspection adds an evidence-backed subset of Spring bean/entrypoint/proxy and JPA/Spring Data bindings; it does not start the application or connect to a database.

kgmaker is designed for one host: GitHub Copilot CLI. Repository hooks handle automatic refresh and context. A repository custom agent can enrich architectural explanations using Copilot itself. There is no model API key, provider configuration, MCP server, or external graph service.

## Documentation and implementation tasks

Start with the [current status](docs/production-analysis-progress.md),
[task registry](docs/tasks/README.md) and [completion specification T003](docs/tasks/3_finishProductionAnalysis.md).
Agents must follow [AGENTS.md](AGENTS.md), including stable task IDs and mandatory
`docs/tasks/<N>_<lowerCamelCase>.md` / `docs/changes/<N>_<lowerCamelCase>.md` names.
These two number sequences are independent of each other and GitHub PR numbers.

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
includes unknown/test inventory. Without a valid compiler index these are partial source-only analyses. Explicit `inspect` adds compiler-backed calls/CFG for the supported matrix. See [implementation progress](docs/production-analysis-progress.md).

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
- JetBrains integration includes `.junie/commands/kgmaker.md` for the `/kgmaker` slash command and `.agents/skills/kgmaker/SKILL.md` for the standard `$kgmaker` Agent Skill invocation. Both route implementation requests through graph reconnaissance, source verification, scoped semantic updates, validation, and tests.

## What gets indexed

Python, Java, Kotlin, JavaScript, TypeScript, Go, Rust, Markdown, reStructuredText, SQL, YAML, properties, and JSON files are scanned. Generated output, dependency folders, virtual environments, common credential files, and files over 1 MB are skipped.

The scanner extracts Kotlin/Java declarations, TypeScript declarations and file-based app routes, SQL tables and columns, Spring Data entity/repository mappings, Kafka listener/producer/config topic references, Spring/Ktor HTTP routes, common HTTP client calls, and OpenAPI paths from YAML or JSON. It links matching HTTP method/path pairs across backend declarations, OpenAPI contracts, and frontend calls. It also recognizes PostgreSQL connection markers and common Kafka imports/configuration.

`imports` are parsed from source. `calls` are heuristic and can be wrong when names collide. The default scanner uses pattern-based SQL, YAML, Kotlin and TypeScript extraction. Separate opt-in JVM/TypeScript workers use compiler APIs; they are not invoked by scan/hook/feature. Explicit JVM inspection can project imported Spring/JPA annotations into `FRAMEWORK_DERIVED` nodes and edges, including bean candidates, HTTP/listener entrypoints, proxy boundaries, entity/table/column bindings, and simple Spring Data repository/query declarations. Dynamic URLs, custom frameworks, indirect Kafka topic names, jOOQ-generated schemas, and complex OpenAPI YAML may not resolve. The graph is a navigation aid; inspect source before relying on it. Raw file contents are not copied into the graph. `.kgmaker/graph.json` is intended to stay local; the human-readable map can be committed if the repository wants a shared snapshot.

## Copilot workflow

Vývoj tohoto repozitáře má navíc projektové Codex implementační agenty v
`.codex/agents`. Každý agent je vyhrazen jednomu atomickému work package T003,
má explicitně nastavený model `gpt-5.6-luna` a reasoning effort `medium` a vede
implementaci přes vlastní větev, testy a samostatný pull request. Tyto profily
jsou konfigurací přispěvatelů tohoto repozitáře; příkaz `kgmaker init` je
neinstaluje do uživatelských projektů.

The generated `.github/agents/kgmaker.agent.md` provides a specialist for graph questions. The architect, implementation, test-expert, review, and orchestrator agents use the durable `task` workflow and role-specific context packets. `.github/agents/kgmaker-extract.agent.md` runs the initial and incremental semantic extraction workflows. After a code change, run `kgmaker semantic update --base <merge-base>` and give the extraction agent `.kgmaker/semantic-update.md` plus `.kgmaker/semantic-update.json`; it produces a scoped patch rather than rereading the repository. These are ordinary Copilot CLI custom agents and can be edited or used alongside a repository's own agents. Verified semantic notes live in `.kgmaker/NOTES.md`. kgmaker does not install agents into other products or make model API calls itself.

## Implementation memory and workflow

`memory capture` records one deterministic episode from a Git baseline, the stored pre-task graph, a fresh graph, changed file hashes, affected node IDs, and bounded validation statuses. It stores no source text, raw diff, prompt transcript, test output, or sensitive path content. Repeating capture for the same Git/worktree fingerprint is idempotent. Semantic schema v1 and v2 remain readable; the first capture writes schema v3 while preserving valid concepts and relationships.

`memory recall` ranks current graph locations and prior episodes against the implementation request. It labels changed or removed episode evidence as historical, applies result and token bounds, and reports the estimated reduction from the broad legacy graph context.

The `task` commands persist workflow state under ignored `.kgmaker/workflow/`. A task follows `intake → analyze → plan → implement → test → review → done`; bounded retries may return test or review to implementation. Architect, implementation, test-expert, review, and orchestrator artifacts have strict role-specific JSON contracts. `task context` assembles a bounded packet from current graph nodes, semantic hits, implementation memory, impact candidates, tests, and prior task artifacts without modifying the graph or semantic layer.
The generated `.github/agents/kgmaker.agent.md` provides a specialist for graph questions. `.github/agents/kgmaker-architect.agent.md` is the read-only reconnaissance specialist that Copilot should consult before implementation. `.github/agents/kgmaker-extract.agent.md` runs the initial and incremental semantic extraction workflows. After a code change, run `kgmaker semantic update --base <merge-base>` and give the extraction agent `.kgmaker/semantic-update.md` plus `.kgmaker/semantic-update.json`; it produces a scoped patch rather than rereading the repository. These are ordinary Copilot CLI custom agents and can be edited or used alongside a repository's own agents. Verified semantic notes live in `.kgmaker/NOTES.md`. JetBrains command files and an Agent Skill are also supplied in this repository; `init` installs the analyst/data-auditor command templates listed in its output. kgmaker makes no model API calls itself.

The repository hook uses the `sessionStart` event from GitHub Copilot CLI. To remove automatic integration, delete `.github/hooks/kgmaker.json`; the generated graph and CLI can still be used manually.

## Development

```bash
python -m pip install -e . pytest==8.3.4
python -m pytest -q
```

The Python core is intentionally dependency-free at runtime. The development suite requires pytest; compiler integration requires the optional toolchains. Missing workers skip optional local integration tests, while CI requires them in its worker job. The Markdown graph is deterministic; the ignored JSON index also records its generation time.

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
for Java, TypeScript and JSON contracts. Parser limitations are explicit in feature
coverage; a static path does not prove runtime availability or financial validity.
`.xlsx` workbooks contribute sheets, cells, named ranges, formula dependencies and
hash-bound cell evidence. Formulas are not evaluated and cached values retain
`UNKNOWN` freshness. Shared/dynamic/external constructs and binary `.xls` are
explicit diagnostics.
Supported Thymeleaf templates contribute `${variable.path}` nodes. Literal
`addAttribute`/`setVariable` keys and literal controller template returns create
evidenced backend bindings; an explicit `pdfService`/`pdfRenderer` call remains an
external PDF boundary.

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

Volitelné compiler workery a samostatný explicitní build workflow popisuje
[compiler inspection](docs/compiler-inspection.md). Maven POM discovery is
source-only; effective classpaths and fresh outputs require an explicit build
plan/import. Explicitní Maven session export v2 navíc přenáší parent/BOM,
effective dependencies a dependency management, aktivní i inherited profily,
generated source roots, compiler release a konkrétní Java/Maven toolchain.
Manifest, dependency model, toolchain a generated roots vstupují do identity
compiler kontextu. Zdroje vytvořené annotation processorem se přijímají pouze z
explicitního úspěšného buildu, zůstávají v jeho izolovaném run adresáři a každý je
svázán hashem, execution ID a vstupním snapshotem; compiler symboly zachovají
`origin=generated`. Runtime import accepts only a supplied, hash-bound observation
manifest and never starts the application. Implementace je stále částečná;
přesný rozsah a otevřené acceptance jsou v [progress dokumentu](docs/production-analysis-progress.md).

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
Custom Kotlin getter/setter mají vlastní method/CFG a property access používá přesný
`ACCESSOR` call site. Class property initializers a `init` bloky patří ve zdrojovém
pořadí do primary-constructor CFG. Top-level properties používají file-facade
`<clinit>()V`; object/companion initializers zůstávají v constructor realm svého objektu.

Spring projection v podporovaném annotation subsetu rozlišuje aktivní, neaktivní
a neznámé `@Profile`, `@ConditionalOnProperty`, `@ConditionalOnClass` a custom
`@Conditional`. Pouze jediný aktivní kandidát dostane `injects_bean`; neznámé nebo
víceznačné varianty zůstávají `may_inject_bean`. Qualifier/Primary, short-name guard
a self-invocation proxy boundary jsou součástí stejného context-bound výsledku.
Compiler-symbol meta-anotace se rozvíjejí nejvýše osm kroků a explicitní
`spring_component_packages` určuje ACTIVE/INACTIVE scan scope; bez něj je dostupnost UNKNOWN.
Collection/map injection zachovává všechny aktivní členy, Optional může vybrat
unikátní aktivní bean a ObjectProvider/Provider zůstává lazy `may_inject_bean`.
Pravidla v3 navíc počítají dosažitelnost `@Configuration` přes component scan a
statické `@Import`: importovaná konfigurace může ležet mimo scan scope, její
class condition se přenese na `@Bean` metody a `@Bean` mimo konfiguraci nevytvoří
bean. ImportSelector a registrar se nespouštějí a zůstávají diagnostickou hranicí.

JPA rules v4 oddělují `@Entity`, `@Embeddable` a `@MappedSuperclass`, určují
FIELD/PROPERTY access podle umístění identity, modelují `@EmbeddedId` a přesný
`@AttributeOverride` a rozlišují owning/inverse asociace přes `mappedBy`.
Vztahový atribut nevytváří smyšlený scalar column; explicitní JoinColumn/JoinTable
zůstává samostatným mapovacím objektem.
Bounded Spring Data parser ověřuje derived query properties proti entity,
association a embedded atributům, zachovává operátory a `OrderBy` a rozlišuje
čtení od delete intentu. Neznámá property nevytvoří resolved hranu.
Compiler-owned `@Query` rozlišuje JPQL a native SQL, kontroluje named parametry,
návratovou entitu/projekci a váže statické dotazy na entity, atributy nebo přesné
ORM tabulky. Statické `@NamedQuery`/`@NamedNativeQuery` mají vlastní definici a
repository metoda se na ni váže přes `uses_named_query`.


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
