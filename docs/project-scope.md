# Project scope

KGMAKER is a local knowledge graph and evidence tool for repository-aware agents.
Python 3.11+ source-only operation uses the standard library and local JSON. Copilot
hooks/custom agents are the primary integration; repository JetBrains commands and
an Agent Skill provide additional invocation instructions. Optional compiler workers
require separately installed JDK/Node toolchains. No model API key is required.

## Implemented capabilities and boundaries

- Syntactic file/symbol/import/domain extraction, scope isolation, semantic packets,
  query/impact, deterministic Markdown/Mermaid architecture maps and session hook.
- Feature/data-check lifecycle with isolated proposals, citations, revisions,
  exact supported availability-proof contracts and deterministic reports.
- Offline Flyway reconstruction for documented SQL subsets; explicit multi-repo
  workspace snapshots, IDs, service mapping and content caches.
- Local read-only Confluence HTML/diagram ingestion and code/documentation checks.
- Explicit JVM/TypeScript compiler inspection with source call sites and CFG,
  plus explicit Maven/Gradle plan/run/import in a limited tested matrix.

Compiler distributions do not imply full language support: Kotlin currently uses
K1 language/API 1.9 compatibility. Symbolic Spring wiring, full ORM/query/integration
adapters, approved-methodology comparison and selective feature invalidation remain
incomplete. Bounded XLSX parsing covers cells, named ranges and static dependencies
without formula evaluation. Single-root scan/hook/feature retain fresh compiler
layers, selectively mark invalid layers stale, and workspace snapshots propagate
compiler collections under repo-qualified identities. Unified context choice across
all higher-level commands remains incomplete. See
[current status](production-analysis-progress.md) and
[compiler inspection](compiler-inspection.md) for precise support.

## Normative target

[T001](tasks/1_featureAnalysis.md) defines analytics, artifacts, incremental,
Flyway/workspace and an independent optional-to-use Confluence synchronization
boundary. Analytical core completion requires T001-S01–04/S06–07. The full T001
scope additionally includes S05's adapter/fake/approval/concurrency work; live
integration must be reported separately and requires a concrete host/API.

[T002](tasks/2_buildAwareInspection.md) defines build-aware JVM/Spring/Hibernate
inspection. T002-S01–06 are mandatory for its supported static matrix; S07 runtime
import is an independent optional extension. [T003](tasks/3_finishProductionAnalysis.md)
integrates the remaining work, including TypeScript and production ranking, without
removing T001/T002 requirements. The [registry](tasks/README.md) is the only numbering authority.

## Execution and evidence constraints

Scan, hook, feature and data-check never run the project, migrations or database
queries. Explicit build execution is content-bound and governed by the host's
policy; a copied project directory is not a sandbox. Optional dependencies are
installed explicitly, never implicitly during source-only operations.

Code evidence describes implementation, not business approval. Migration-derived
schema is not deployed/populated database proof. A call path or build/test PASS is
not availability. Supported supplied observations/mappings/decisions remain scoped;
no authenticated production access or universal completeness is claimed.

## Out of scope

MCP server, model-provider/API-key layer, mandatory hosted graph database,
financial/mathematical proof engine, implicit runtime capture and automatic
Confluence publishing. External URLs are excluded from generated graph content;
normal documentation may link to sources. Agents must follow [AGENTS.md](../AGENTS.md).
