# Flyway, local workspaces and scoped availability proofs

All commands are offline. No clone/pull, build, test, migration execution or DB
connection is performed. Source repositories and semantic/AS_IS artifacts are
read-only during feature analysis. `--root` is the coordination/output directory;
`--workspace` selects only explicitly declared checkout roots. Missing checkouts
remain visible as coverage gaps, never evidence that business data does not exist.

## Flyway schema reconstruction

```bash
kgmaker schema inspect --root backend --target latest --format json
kgmaker schema diff --root backend --from 2 --to 10 --format json
kgmaker schema inspect --workspace kgmaker.workspace.json --repo backend --stream main --target latest
```

Explicit JSON configuration can be supplied using `--config`, and workspace
repositories can provide one `flyway` object or a list of independent stream
objects. Supported settings: database_id, stream_id, dialect=postgresql, locations,
target, default_schema, schemas, prefix, repeatable_prefix, baseline_prefix,
undo_prefix, separator, suffixes, placeholders, profile, mode, baseline_version,
initial_snapshot. Explicit settings override selected-profile and base config.
Properties, scoped scalar Spring YAML, Flyway TOML, literal Gradle assignments and
Flyway Maven-plugin XML are inspected without executing build scripts. Conflicting
settings, dynamic expressions, remote/JAR locations and missing roots are diagnostics.
Credentials are not extracted; model context redacts sensitive config lines.

Versions use numeric dotted/underscore ordering with trailing-zero equivalence.
Equivalent duplicates within one migration kind/stream invalidate the plan.
Numeric gaps alone are not diagnosed as missing history. Repeatables follow
versioned migrations in description order for clean bootstrap. Current repeatable
contents are not silently applied to historical targets. Baseline-script mode uses
the latest applicable B script, then strictly newer V scripts; undo scripts never
participate in forward replay. Snapshot mode requires an explicit initial schema
JSON (`schema_version: 1`, `objects`) and baseline_version. A baseline marker is
not treated as a baseline migration script.

The lexer respects comments, quoted identifiers, strings and dollar-quoted bodies.
Replay supports explicit CREATE TABLE columns and constraints; ALTER add/drop/rename
column, rename table/schema/index, type/nullability/default; schemas, simple indexes,
sequences and simple SELECT-projection views. Unknown DDL, programmatic migrations,
callbacks, DO/function/trigger bodies and unsupported expressions make the stream
PARTIAL. A failed statement rolls back its model effects; other known statements
can still be inventoried. DML is a transformation/backfill operation, not current
populated-data evidence. Lifecycle tracks origin, last change, old names and drops;
only active objects enter the current graph. Quoted dots cannot collide with schema
qualification. Views and constraints have explicit source dependencies.

Results are MIGRATION_DERIVED, never DEPLOYMENT_VERIFIED. COMPLETE means complete
within the supported offline declaration plan, not an actual deployed database.
Prefix checkpoints reuse unchanged parsed prefixes in Python API/diff runs; changing
old migrations, configuration or initial snapshot invalidates dependent prefixes.
Workspace repository caches persist in the coordination directory and avoid
reparsing unchanged repositories across CLI processes. Validation reads caches but
does not write them. Cache entries are versioned and content-integrity checked.

Explicit Kotlin @Table/@Column mappings are compared with the selected schema for
missing fields, type, nullability and declared precision/scale. Unsupported Java
annotation layouts or implicit naming conventions remain unproven. Test INSERT
fixtures are checked against an unambiguous selected backend schema. Diagnostics
reference the test source, schema target and migration scope; no automatic fix occurs.

## Workspace manifest

```json
{
  "schema_version": 1,
  "workspace_id": "exposure",
  "repositories": [
    {"id":"backend","role":"backend","path":"../backend","flyway":{"database_id":"client-db","stream_id":"main","target":"latest"}},
    {"id":"frontend","role":"frontend","path":"../frontend"},
    {"id":"tests","role":"automated-tests","path":"../tests"}
  ],
  "services": [{
    "id":"exposure-api","backend_repo":"backend","frontend_repos":["frontend"],"test_repos":["tests"],
    "contract":{"repo_id":"backend","path":"contracts/exposure.json"},
    "consumer_path_prefix":"/api","provider_path_prefix":""
  }]
}
```

Paths are relative to the manifest. Duplicate IDs, overlapping or symlink roots
and invalid references are rejected. Optional repository revision and expected_remote
checks never switch branches or fetch remote state. Globally qualified IDs are
`repo:<escaped-repo>:<escaped-local-ID>`; source keys are `@repo/path`, while citations
carry explicit repo_id and the repository-relative path. Original single-root IDs
are unchanged. Preparation compares inventories before/after reading and refuses
a mixed snapshot. Adding/removing a checkout or editing the manifest invalidates
the workspace baseline. Release/deployment compatibility remains unknown without
explicit release mapping; no deployment is inferred from matching names or paths.

scan/build/update/status/query/impact/docs and all feature subcommands accept
`--workspace`. Workspace graph writes go only to the coordinator. Workspace docs
renders the federated graph; Confluence checks remain per-repository. Feature
commands retain the workspace binding of their packet and reject a different
manifest supplied later. Plain query never includes proposal nodes.

Supported cross-repo linkage is deliberately narrow: OpenAPI JSON response fields,
literal GET fetch/axios/request calls under explicit service and prefix mappings,
single-response JSX field displays with literal data-testid, Playwright declarations
and field assertions, JUnit/REST-Assured HTTP/body patterns, and imported helpers.
Field/display/assertion mappings are INFERRED unless explicit extraction proves
the relationship. Multiple service candidates, unsupported fetch options, dynamic
selectors and complex mappings are unresolved. Literal/comment examples do not
become calls. A request-only test is relevant but is not field assertion coverage.
No static test node implies runtime PASS or sufficient business-rule coverage.

Optional `generated_clients` service entries have repo_id, path, metadata_path and
consumers. The cited generation metadata must contain an exact source_contract
`{repo_id,path,sha256}` and generated_files list. A stale contract hash breaks the
link. Generated code is not independent evidence of the original contract.

## Positive availability proofs

InputRequirement optionally contains `availability_proof`. Its result must match
the deterministic checker exactly, including usability and verification_scope.
No LLM confidence, DTO declaration, schema existence or fuzzy search proves data
availability. Version 1 implements three explicit proof categories:

| Kind | Required evidence | Result |
|---|---|---|
| OBSERVED_VALUE_PATH | Fresh supplied populated observation, fully EXTRACTED value path, current source hashes, approved exact business mapping | AVAILABLE/FIT if metadata/type/freshness and dependencies are supported; otherwise PARTIAL/UNASSESSED or rejected |
| CLOSED_CONTRACT_ABSENCE | Validated JSON-pointer citation to a closed object schema, absent property | CONFIRMED_MISSING only in that exact contract version/pointer |
| APPROVED_MISSING | Explicit approved structured decision with input ID and exact limited scope, human-decision citation | CONFIRMED_MISSING only in the declared decision scope |

Observation proof fields: kind, source_entity_id, target_entity_id,
observation_evidence_id, mapping_decision_id. The target must be a source_id of the
input. Evidence must be cited by that input. Its JSON-pointer value is an object:

```json
{
  "schema_version":1,"kind":"SUPPLIED_DATA_OBSERVATION",
  "entity_id":"data_field:Account.kt:Account.balance",
  "scope":"sandbox / explicitly supplied dataset only","value":100.0,
  "key_values":{"accountId":1},
  "source_hashes":{"Account.kt":"actual-current-byte-sha256"},
  "collected_at":"2026-10-12T07:00:00Z","max_age_seconds":3600,
  "metadata":{"definition":"...","data_type":"Double","freshness":"PT1H"}
}
```

The metadata object uses InputRequirement's explicit metadata contract. AVAILABLE
requires every required metadata value to be known and matched, a compatible
parsed/runtime type and supported ISO PT hours/minutes/seconds freshness. Omitted
metadata yields PARTIAL; contradictions are rejected. max_age_seconds cannot weaken
the requested freshness. Explicit required identifier keys must have populated
key_values. Supported nonnegative/positive/nonempty quality rules are checked
against the value; arbitrary free-text quality policies remain partial.
All value-path source hashes must match current packet
sources. Additional unobserved calculation dependencies prevent AVAILABLE.
The observation is supplied evidence, **not independently authenticated production
data or a deployment snapshot**. Its collection/source scope is part of the claim.

Business approval uses the existing revise workflow. The approved answer is JSON:
`{"input_id":"...","entity_id":"...","metadata":{all exact requested metadata}}`.
It must match the input definition; a bare “yes”, unapproved answer or different
mapping is insufficient. Approval remains declared provenance, not authenticated
identity. Expired observations are STALE even without source changes; historical
reports clearly label prior availability as invalid for the present.

Contract absence proof fields: kind, evidence_id, field. The cited object must have
additionalProperties=false and an explicit properties object. Approved missing
proof fields: kind, decision_id, scope; answer JSON is
`{"input_id":"...","scope":"...","confirmed_missing":true}`. Neither category
proves missing data throughout an organization.

DataRequirementSet may provide `evidence_references` (id/path/location/quote or
value, plus repo_id for workspace). The command computes hashes and delegates
citations to the usual validator. Inputs can carry availability_proof but not a
chosen availability result. `data-check` classifies supported proofs, leaves
unsupported claims UNKNOWN/pending and separates confirmed scoped delivery gaps
from business ambiguities and tool coverage. Normal validate/apply/report still
owns lifecycle, receipts and proposal isolation.

## Verified coverage and boundaries

Offline tests use three synthetic Git checkout directories (no network), manually
specified V1/V2/V10 schema expectations, matching path/name collision fixtures,
frontend displays, HTTP/UI assertions and stale SQL fixtures. They cover fake
citations/mapping approvals, incomplete metadata, stale observations and source
drift, cache reuse, coherent snapshot rejection, scoped absence, and single-root
compatibility. There is no claim of complete SQL grammar, full TypeScript/JVM
interprocedural analysis, arbitrary UI frameworks, runtime instrumentation,
automatic business equivalence or live deployment verification.

Flyway references verified during implementation:
- https://documentation.red-gate.com/flyway/flyway-concepts/migrations/versioned-migrations
- https://documentation.red-gate.com/flyway/flyway-concepts/migrations/repeatable-migrations
- https://documentation.red-gate.com/flyway/flyway-concepts/migrations/baseline-migrations
