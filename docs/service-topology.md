# Service/resource/channel topology (T016 draft)

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

Current parent is verified main ec6a127 with T014/T015/Common/T012/T013/W07v2
and process stack merged. Owned source/tests exactly match accepted2df; all46own
cases PASS in that one2587PASS10allowedSKIP full. Current2471-case union transfers
2461PASS10sameSKIP with explicit source/per-ID/native proof, not a new full on
this head. Independent current-pair review remains a gate. Pure protocol and file-
backed capture do not become new compiler/runtime observations. No new native build.
