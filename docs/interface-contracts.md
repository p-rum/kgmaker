# Explicit interface contract attachments

Delivery status (2026-11-07): T013 is MERGED in [PR74](https://github.com/p-rum/kgmaker/pull/74) (`2a38706`).
Current full acceptance is NOT_RUN in this documentation audit. Historical
checkpoint results and pre-merge review gates below describe their stated SHA.
Use the [current delivery inventory](production-analysis-progress.md) and
[change111](changes/111_reconcileDeliveryStatus.md) for present status.

`capture_interface_contracts(workspace, graph)` reads only manifest-declared
OpenAPI JSON, Kafka JSON message contracts, generated-client metadata and generated
source files. Each bounded capture retains raw byte SHA, normalized source SHA and
parsed declaration; it is an in-memory input, not another registry or cache.

```python
from kgmaker.interfaces import capture_interface_contracts, attach_interface_contracts

captured = capture_interface_contracts(workspace, graph)
attached = attach_interface_contracts(workspace, graph, catalogue, captured=captured)
```

The input catalogue must already be selected and validated by T010/T011/T012.
Attachment preserves interface IDs, original IDs, technical resolution and evidence
buckets. A type reference requires both a canonical selected TYPE declaration and
a versioned upstream payload-reference proof. Current HTTP/Kafka facts do not
supply the latter, so supplied type IDs remain `None` with `TYPE_REFERENCE_UNKNOWN`.
A real class alone, DTO name, return type, wrapper or serialization guess does not
create a payload binding. Explicit file/operation/schema declarations still bind. Provider declarations and
client expectations remain separate roles. `payload_compatibility=UNKNOWN`: this
API does not contain a schema compatibility validator.

A contract binding carries explicit repo/path, raw SHA, declared revision/release,
exact operation pointer, schema references and its own revision fingerprint.
HTTP operations require the existing service realm, normalized method/route and
original captured registration/request tuple. Ambiguous operations remain unknown;
external or malformed schema references are not followed. Only existing bounded
local schema pointers are referenced. Kafka references retain explicit realm/group
separation and add a contract-independent logical anchor while preserving original
upstream occurrence/subscription IDs.

Generated source and metadata must be inventoried with the explicit source-contract
repo/path/SHA tuple and generated-file membership. The file's raw hash and metadata
hash bind the declaration capture. This is declared generation origin, not a
receipt proving generator execution. A changed contract invalidates the binding
and preserves the client ID and original generation tuple, even when the legacy
workspace linker omits its stale generated-client graph node. A SOURCE_ONLY client
file can support a declaration while module/compiler coverage remains unknown;
this does not become compiler, runtime or compatibility proof.

The same explicit workspace files must remain available. Attachment rereads only
these files and original interface source/config inputs, with bounded before/after
hash checks. It does not inspect, scan, build, execute a generator, contact a
service, fetch schemas, write a cache or query a latest compiler index. Missing,
symlinked, oversized and changed inputs remain unknown/stale or fail closed without
mutating input catalogues or the caller's last valid artifact. At most256 explicit
contract/generation files are captured; each uses the existing scanner file-size
limit. Unknown capture versions fail closed.

OpenAPI3.0/3.1 JSON and explicit JSON message documents form the bounded file matrix.
YAML schema resolution, compatibility validation, remote service discovery,
serialization, delivery, deployment and data availability are outside this API.
Original graph1/2/3 and catalogues without attachment fields remain readable.
