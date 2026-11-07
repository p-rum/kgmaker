# Static remote interface topology (T014)

Delivery status (2026-11-07): T014 is MERGED in [PR80](https://github.com/p-rum/kgmaker/pull/80) (`ec6a127`).
Current full acceptance is NOT_RUN in this documentation audit. Historical
checkpoint results and pre-merge review gates below describe their stated SHA.
Use the [current delivery inventory](production-analysis-progress.md) and
[change111](changes/111_reconcileDeliveryStatus.md) for present status.

```python
from kgmaker.remote_interfaces import project_remote_interfaces
view = project_remote_interfaces(workspace, graph, interfaces,
    captured=captured, scope="production", selected_contexts=selected_contexts)
```

Supply the existing trusted W07 local capture handoff and its canonical interfaces.
This pure adapter invokes W07's offline resolver; it does not capture, read sources,
run projectors/workers, call services or write a store. Capture hashes prove
consistency of supplied inputs, not authentication of replacement JSON or current
physical checkout freshness. Changed inputs need new explicit capture outside API.

The topology retains original interface/service/proof IDs, code call/terminal refs,
broker/topic/group, and a binding object with the entire candidate set, mapping
IDs and incomplete/unresolved selectors. Missing mapping or missing selected
endpoint stays an explicit unresolved boundary. Same URL cannot select a service.
Ambiguous candidates stay ambiguous; one known plus one unresolved mapping is not
unique RESOLVED. Derived edge IDs separate mapping/release/transport/context pairs.

Relations remote_http_request_response and remote_kafka_publish_subscribe describe
static declarations. They are never JVM calls, CFG/process continuation or observed
responses/delivery. Ordinary HTTP client contract authority is MANIFEST_EXPECTATION;
provider remains BOUND_DECLARATION. Original endpoint compiler/framework proofs keep
their kind and polarity. New remote mapping proof is SOURCE_ONLY, UNKNOWN polarity.
Original evidence references are retained separately, without promoting their meaning.

Derived freshness is UNKNOWN with capture_freshness=CAPTURE_TIME_ONLY. Original
endpoint freshness remains original. Runtime execution/delivery NOT_OBSERVED;
deployment/runtime availability/payload compatibility UNKNOWN. Coverage remains
PARTIAL/UNKNOWN; upstream diagnostic/coverage hashes and counts stay visible. Raw
labels/proof/config/schema payloads are omitted; safe IDs and explicit fields are
preserved with payload hashes. Invalid identities/malformed inputs have fixed
nonsecret errors, no input mutation. Hard bounds reject before returning a view;
there is no silently truncated candidate set.

## Historical validation checkpoint

T014 public pure/protocol tests are distinct from actual compiler acceptance.
Merged T013/W07/Common and process bodies are preserved on current509. Owned
source/tests are exact accepted2df; all24own cases PASS in that one2587PASS10SKIP
full. Current2425-case parent union reuses2415PASS10allowedSKIP with explicit source
and per-ID proof, not a new full on this head. Exact-pair independent review remains
a gate. No new native build is required solely for this pure projection. T027/T028
process continuation and remote runtime observations are separate future tasks.
