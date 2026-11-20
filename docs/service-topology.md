# Service/resource/channel topology (T016)

Delivery status (2026-11-07): T016 is MERGED in [PR81](https://github.com/p-rum/kgmaker/pull/81) (`130720f`).
Current full acceptance is NOT_RUN in this documentation audit. Historical
checkpoint results and pre-merge review gates below describe their stated SHA.
Use the [current delivery inventory](production-analysis-progress.md) and
[change111](changes/111_reconcileDeliveryStatus.md) for present status.

```python
from kgmaker.service_topology import capture_topology_inputs, aggregate_service_topology
captured = capture_topology_inputs(manifest, scope="production", selected_contexts=selected_contexts)
view = aggregate_service_topology(captured)
```

Capture is the explicit local I/O boundary. One workspace/snapshot/coverage closure
feeds T015, W07 capture and T014. W07's literal canonical interface documents and
capture object feed T014; all actual inventory selections must match T015. T014's
separate W07 normalized selection must equal the remote capture selection, rather
than being compared directly to T015's different inventory representation. Both
original baselines/content fingerprints remain independent. The manifest and
whole source/schema/graph/coverage closure are reread after both consumers; changed
inputs fail before a capture is returned. No compiler/build/application or cache
publication is performed. Migration derivation is not a database observation.

The versioned capture binds only the declarative input fingerprints, selectors,
canonical upstream views and explicit release records; no raw graph, source files,
SQL/schema/config contents or private compiler stores are copied. A trusted local
handoff is required: its digest checks consistency, not authentication against a
party able to replace every document and its hashes coherently. Physical checkout
freshness is not inferred by the offline consumer.

Aggregation is pure. It never calls capture, source loaders/snapshot/projectors,
private replay, workers/model/network/DB or a store. Services/resources come only
from existing catalogs; DTO/enum centrality cannot invent topology. Unknown or
ambiguous ownership stays a boundary, without parsing labels or names as service IDs.

HTTP summary groups preserve service pair, relation, scope/context, exact contract
content boundary and release selectors. Every summary expands to exact original
interface/mapping/release/input-edge IDs and per-occurrence operation pointers.
Multiple alternatives/incomplete mappings remain ambiguous/unresolved. Kafka uses
workspace+explicit broker realm+exact topic channels, distinct publish and consume
relations, and separate groups. Unknown realms/patterns do not become real channels
or direct synchronous service calls. No JVM calls/CFG/process continuation is added.

Original resource proof buckets/kinds/freshness remain distinct from remote
SOURCE_ONLY declaration proof. Remote freshness UNKNOWN with CAPTURE_TIME_ONLY;
runtime/delivery NOT_OBSERVED; deployment/payload/runtime availability UNKNOWN.
Coverage cannot exceed either input. Upstream UNKNOWN remains UNKNOWN; truncation
is visible and prevents unique RESOLVED remote summaries. Hard input/object limits
fail instead of dropping candidates silently. Unsafe required credential/userinfo
IDs or malformed data have fixed nonsecret errors, no mutation/publication.
Output uses safe typed summaries and hashes of omitted prose/payloads.

## Mermaid rendering (T021)

`kgmaker.architecture_render.render_topology_mermaid` is a pure projection of a
topology `ViewDocument` or T017 filter result. The architecture CLI also accepts
`--format mermaid` for topology snapshots. It consumes the already filtered
document and does not recapture, refilter, perform I/O or publish files.

Renderer node IDs are SHA-256 hashes of each captured logical model identity. An
explicit `logical_id` is combined with realm, scope, context selection and owner;
without it the model node ID is hashed. Therefore repeated labels and even repeated
logical names in distinct realms remain separate. Edge direction and relation names
come from the model; HTTP request/response, Kafka publish/consume and resource
read/write relations have distinct text labels. Kafka publish/consume is marked
`ASYNC; delivery UNKNOWN`. An unrecognized relation remains `UNKNOWN` and unresolved
edges say execution is unknown. Node/edge status, evidence kinds, IDs, context,
provenance and T017 omission inventories are retained in Mermaid-safe JSON comments.
Before rendering, the selected scope and any explicit context filter are checked
for each displayed claim and its directly cited provenance. Absent or unknown
scope and absent context metadata stay eligible. Provenance cited only by omitted
frontier entries remains available in the metadata.

The diagram title carries scope, evidence kinds, coverage and truncation, plus the
`runtime/data availability: UNKNOWN` and `ordering/delivery: NOT_OBSERVED` limits.
The renderer does not add legend or truncation nodes, so displayed model nodes and
edges remain in one-to-one correspondence with the supplied filtered document.
Labels encode Mermaid metacharacters and JSON comments escape HTML/script delimiter
characters. There are no click directives, raw HTML labels or remote resources.

See the [T021 CLI contract and example](architecture-json-cli.md#architecture-topology-mermaid-t021)
and [change132](changes/132_renderTopologyMermaid.md) for acceptance and current
parser/render results. T022's topology Markdown remains a separate renderer.

## Historical validation checkpoint

Current parent is verified main ec6a127 with T014/T015/Common/T012/T013/W07v2
and process stack merged. Owned source/tests exactly match accepted2df; all46own
cases PASS in that one2587PASS10allowedSKIP full. Current2471-case union transfers
2461PASS10sameSKIP with explicit source/per-ID/native proof, not a new full on
this head. Independent current-pair review remains a gate. Pure protocol and file-
backed capture do not become new compiler/runtime observations. No new native build.
