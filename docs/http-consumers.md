# HTTP consumer catalogue

`kgmaker.interfaces.project_http_consumers` projects existing, selected W06 typed
client facts into the shared `interfaces` ViewDocument. It reads the explicit
workspace snapshot and never invokes a worker, client, network or application.

```python
from pathlib import Path
from kgmaker.workspace import load_workspace, snapshot_workspace
from kgmaker.interfaces import project_http_consumers

manifest = Path("workspace.json")
workspace = load_workspace(manifest)
_, coverage, _, graph, _ = snapshot_workspace(manifest)
view = project_http_consumers(workspace, graph, scope="production",
                              source_coverage=coverage)
print(view.to_json())
```

Inspection that creates compiler facts is a separate explicit prerequisite.
`selected_contexts` uses the same `(service_id, repo_id, module) -> context_id`
mapping as the existing service inventory. Historical/unselected captures cannot
supply current consumer evidence. No new CLI command or persistent format exists.

Each `http_interface` has `direction=CONSUMER`, the original request definition,
caller, origin and optional terminal call-site IDs, captured method/path and URI
provenance. Distinct source occurrences retain distinct IDs even for the same
route. A Feign declaration shared by two callers produces two terminal occurrences;
it never borrows the interface declaration's owner as the consuming caller.
A shared publisher with two terminals likewise retains both occurrences.

`UNSUBSCRIBED_WITHIN_SCOPE` and `DEFINITION_ONLY` remain definitions.
`STATIC_TRIGGER`, `CONDITIONAL_STATIC_TRIGGER` and `FEIGN_INVOCATION_INTENT` remain
static intent. They do not prove a network request or response. Dynamic/missing
URIs keep `route_expression=None`, origin references and unresolved reasons.
Request/response contract references and `service_binding` remain `None` because
W06 supplies no proved remote binding or schema contract; URL/name/DTO similarity
never fills those fields. Runtime execution is `NOT_OBSERVED`, runtime/data and
deployment availability remain `UNKNOWN`, coverage is at most `PARTIAL`.

The projection verifies the canonical caller/source tuple, exact call-site range
and identity, originating request identity, chain/terminal ownership and original
edge/evidence tuples against the selected content snapshot. Existing supporting,
contradicting and unknown evidence buckets remain distinct. Malformed relevant
facts raise `InterfaceProjectionError`; unsupported rule versions remain visible
boundaries. Existing provider APIs and IDs are unchanged.

Supported scope is the upstream W06 pinned Java WebClient/RestClient/Feign subset.
There is no new source parser, URI evaluator, cross-service join, client proxy
bootstrap or runtime observation importer. Technical occurrence IDs are bound to
the supplied compiler snapshot; no business identity match across changed source
snapshots is inferred.
