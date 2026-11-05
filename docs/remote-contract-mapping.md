# Explicit remote contract/release declarations (W07 draft)

`remote-contract-mapping-2` adds a separate optional workspace `remote_mapping`
manifest field. It does not change the existing artifact `release_mapping`, which
proves selected build-output/classpath content rather than API deployment.

The strict declaration has `schema_version: 1`, `releases`, `compatibilities` and
`mappings`. A release binds an existing service/interface variant/context/scope to
an explicit release selector and contract repo/path/raw SHA/JSON pointer. A mapping
pairs two release IDs and transport HTTP or KAFKA. Default compatibility requires
exact SHA, operation/schema pointer and release selector. Different versions need
an exact directed `DECLARED_OPERATION_COMPATIBILITY` pair, never semver inference.
See [revision2 schema](tasks/T003-S07-07-crossServiceContractMapping.md).

```python
from kgmaker.remote_mapping import capture_remote_mapping_inputs, resolve_remote_mappings
captured = capture_remote_mapping_inputs(workspace, graph, scope="production",
                                         selected_contexts=selected_contexts,
                                         source_coverage=coverage)
report = resolve_remote_mappings(workspace, graph, captured["canonical_interfaces"],
                                 captured=captured, scope="production",
                                 selected_contexts=selected_contexts)
```

Capture is an explicit local I/O phase: it checks manifest bytes, runs existing
canonical HTTP/Kafka projections and T013 contract capture/attachments with exact
scope/context selectors, then checks the manifest again. No compiler, build,
application, service/broker discovery or model runs. The handoff binds the complete
workspace/graph/selection and canonical interface documents. Contract summary has
file hash/status and bounded pointer inventory; raw JSON examples/descriptions/
credentials are omitted. The original private T013 capture is used during local
validation; its hash is retained, without copying raw schema payloads.

Resolution performs no I/O or upstream projection/attachment, including its first
invocation after importing the public API. Dependency initialization happens at
module import; route normalization and rule version remain unchanged. A fresh
Python-process audit regression checks file, process and network denial without
preloading the normalizer. This protocol test is not native or runtime evidence.
Its hashes check
consistency with the supplied **trusted local capture handoff**, not authenticity
of arbitrary untrusted JSON. Replacing every input and capture coherently is not
an authenticated origin proof. Freshness remains capture-time only. Stale or
changed inputs require a new explicit capture; resolution never repairs hashes.

A RESOLVED record means one eligible static declared mapping. AMBIGUOUS retains
all authorized candidate interfaces/releases/groups. Missing/incompatible/unproven
facts remain UNRESOLVED with reasons. Hard input/depth/fanout limits fail rather
than silently return a unique target from a truncated set. A partially unresolved
mapping set cannot masquerade as a complete unique binding.

HTTP validates known request method/path against the explicitly selected contract
operation. The manifest supplies an ordinary client's contract **expectation**;
a provider still needs the existing T013 current declaration binding. This is not
a typed request/response payload join. Request definition, unsubscribed state and
static execution intent remain distinct. Kotlin HTTP body proof is currently
unsupported upstream and must stay UNKNOWN. Java within K1/K2 uses actual Javac.

Kafka requires current canonical code/binding, explicit broker realm, exact topic
and contract/release authority. Groups stay separate; regex/dynamic/config-only
facts cannot establish delivery. HTTP request/response and Kafka asynchronous
publish/subscribe are different transition kinds; neither is a JVM `calls` edge.
Runtime execution/delivery is NOT_OBSERVED and deployment, data availability and
payload compatibility remain UNKNOWN, including with explicit compatibility pairs.

Accepted source7d55ab0 (production92e96c5): source-specific cohort334 unique PASS
comprises33 unchanged prior passes and301 failed/unreached continuation passes,
with explicit per-ID attribution and all1381 continuation inputs unchanged.
Combined descendant2df55ff8 full2587PASS/10approvedoptionalSKIP covers all1973
W07-parent cases (1963PASS/10SKIP); this is one combined-source run, not a
standalone W07 full. All4897 inputs and five member inventories remained exact.
Historical failures remain in note91. Current-parent/dependency refresh and final
independent exact-pair review remain pending; no runtime claim follows.

Kafka canonical interface summaries may retain UNKNOWN freshness even when their
selected code/context/contract binding is verified. Rule 2 accepts only the exact
canonical service declaration edge under those existing guards; STALE, ambiguous
or contradictory evidence remains ineligible. Original source and target interface
freshness is retained separately from static mapping resolution. HTTP still
requires CURRENT. One release cannot be referenced with conflicting transports
(`REMOTE_TRANSPORT_CONFLICT`). Rule 1 captures require explicit recapture.
