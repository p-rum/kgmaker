# Backend→frontend value flow (T003-S08-W05)

`snapshot_workspace(manifest)` consumes existing, content-validated compiler
indexes and explicitly declared local contracts. It never starts an inspection,
build, package install, application or network request. The bounded implementation
is recorded in [change125](changes/125_backendFrontendValueFlow.md).

The current TypeScript 5.7.3 worker preserves source/hash/range/context-bound
`value_occurrence` identities for a literal, compiler-bound DOM `fetch` GET,
`await response.json()`, immutable local assignments, object property reads,
object destructuring/renaming and explicit object mappings. The request and JSON
occurrences lead to the exact field projection. A separately evidenced backend
field → contract field → projection bridge joins that ancestry; a route or field
name alone cannot create this bridge.

Reference aliases share a compiler-binding identity group. A property write,
unknown call/receiver, container storage or return escape invalidates the entire
group, including chained aliases. The audit is flow-insensitive: even an earlier
read can be withheld if a later use mutates or escapes the object. `const`,
`Readonly<T>` and casts are not immutability evidence. Proven primitive copies
remain separate; reading local aliases without mutation or escape is supported.
Unknown alias-producing conditional expressions, heap containers and returned
references are conservatively excluded, not modeled as safe heap flow.

For React 18.3.1 with `@types/react` 18.3.18 and the pinned declaration hash, the
compiler-selected `useState` declaration pairs the state and setter bindings.
Exactly one direct setter call can carry a projected field to an intrinsic JSX
expression consumer. Setter names are irrelevant. The adapter is enabled with
`--ui-framework react`; setters, state and properties have distinct occurrence
IDs. Test repositories expose the exact compiler-resolved call argument consumer,
including its call-site ID and argument index. The result does not certify an
assertion framework or a passing test.

The backend side requires an existing current compiler field/property symbol,
for example a Javac field. In the selected OpenAPI JSON property, declare:

```json
{
  "type": "number",
  "x-kgmaker-source": "<exact current backend compiler field ID>",
  "x-kgmaker-source-sha256": "<current backend source SHA-256>"
}
```

Reuse the service's `generated_clients` declaration (`repo_id`, `path`,
`metadata_path`, `consumers`). Its metadata retains the existing
`source_contract`/`generated_files` contract and optionally adds W05 evidence:

```json
{
  "source_contract": {"repo_id": "backend", "path": "contracts/exposure.json", "sha256": "<contract SHA-256>"},
  "generated_files": ["generated/client.ts"],
  "generated_sha256": {"generated/client.ts": "<generated file SHA-256>"},
  "release": "v1"
}
```

The metadata release must equal OpenAPI `info.version`. Exactly one declaration
must cover the consumer source, both hashes must match captured bytes, and the
TypeChecker field declaration must belong to that exact generated file. A local
same-name type cannot substitute for the generated contract.
Generation provenance remains `LOCAL_DECLARED`: it is neither a generator
execution receipt nor proof of payload/business equivalence or a deployed
release. W07 remote-mapping APIs remain unchanged; this bounded bridge uses the
existing generation-origin contract, not an automatically inferred remote binding.

Example explicit workflow (each repo already has its dependencies/toolchain):

```bash
kgmaker inspect code --root /workspace/backend --repo-id backend
kgmaker inspect frontend --root /workspace/frontend --repo-id frontend --tsconfig tsconfig.json --ui-framework react
kgmaker inspect frontend --root /workspace/tests --repo-id tests --tsconfig tsconfig.json
kgmaker scan --root /workspace/coordinator --workspace /workspace/workspace.json
# A mutable/escaped response reports VALUE_FLOW_CONSUMER_UNPROVEN; it has no value consumer path.
kgmaker impact --root /workspace/coordinator --workspace /workspace/workspace.json --entity '<repo-qualified backend field ID>' --include-data-flow --format json
```

The public `impact_paths` result adds `frontend_value_bindings` alongside the
existing argument/return evidence. Existing path fields remain compatible;
proof records retain their evidence and context IDs, source ranges, request
call-site identity, generation hashes and `availability=UNKNOWN`.

Native value edges are `SYMBOL_RESOLVED`; React state writes and declared contract
bridges are `FRAMEWORK_DERIVED`. All report `runtime_execution=NOT_OBSERVED` and
`availability=UNKNOWN`. Missing checkout, stale compiler input, mismatched
contract/generated hash or release, ambiguous service/generation declaration,
missing backend field and an unproven consumer produce localized `VALUE_FLOW_*`
coverage gaps. Cached contexts are revalidated against captured dependency/distribution inputs;
final snapshot validation also checks them again. A cached STALE compiler result
is reloaded from the original explicit index. Restoring the exact captured
dependency bytes can recover its original proof; still-invalid inputs remain
STALE. This read does not inspect/build or replace the stored index. No last-valid graph is replaced
on worker protocol failure. Every fact touching a frontend value occurrence
must carry the supported integer `value_flow_version=1`, with two valid v1
endpoints. Removing a marker does not make an edge legacy; missing/unknown/mixed
versions or role/identity mismatches are rejected before publishing.

Graph/store v1/v2/v3 and old worker responses remain readable. Disconnected legacy
facts without frontend value occurrences still publish unchanged. Older generation
metadata still supports its existing declaration inventory but supplies no W05
value bridge. SOURCE_ONLY still inventories endpoint/UI/assertion syntax; the
old name-only `displayed_in`/`asserts_field` shortcuts are removed because an
unrelated object/promise/assertion could otherwise appear to consume a response.
SOURCE_ONLY therefore remains PARTIAL/UNKNOWN.

Current limits: await/local-const flow only; no Promise callbacks, branch/loop/try
merging, mutable/escaped objects, dynamic-eval source files, setter aliases/updater callbacks, multiple state
writes, custom JSX components, Axios/Playwright transport adapters, dynamic URLs,
interprocedural mapping or arbitrary UI frameworks. Type assertions are syntax,
not payload validation. Kotlin backend and arbitrary production repositories are
not covered by the Javac fixture. The parent S08/T003-AC08 remains PARTIAL.
