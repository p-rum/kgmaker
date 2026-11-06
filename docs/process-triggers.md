# Proven trigger inventory (T024)

`kgmaker.process_triggers.discover_process_triggers` projects existing selected-context
Spring HTTP, Kafka listener and scheduled-method facts into a shared
`ViewDocument(kind="process")` inventory. It does not assign business process
identities, expand CFG paths, infer ordering, or execute workers/applications.

```python
from pathlib import Path
from kgmaker.workspace import load_workspace, snapshot_workspace
from kgmaker.process_triggers import discover_process_triggers

manifest = Path("workspace.json")
workspace = load_workspace(manifest)
_, coverage, _, graph, _ = snapshot_workspace(manifest)
inventory = discover_process_triggers(workspace, graph, source_coverage=coverage,
    scope="production")
print([(node.attributes["trigger_kind"], node.owner_id) for node in inventory.nodes])
```

The existing workspace snapshot must already contain captured compiler/framework
facts; this code performs no implicit build, dependency fetch, inspection or network
access. Projection reads the workspace manifest and verifies accepted source hashes
before and after processing. Invalid input raises `TriggerInventoryError` carrying
structured `diagnostic`; no store or source files are written.

Candidates preserve entry symbol, endpoint/entrypoint, context, source hash, owner
and original evidence IDs. Canonical symbol identity, endpoint scope and exact
edge/proof tuples must agree. Annotation names alone, method names and Async do
not create triggers. Missing or unsupported facts remain diagnostics and UNKNOWN;
output is at most PARTIAL. Framework derivation is not runtime registration,
execution, scheduling or data availability.

Body availability is independent of declaration presence. Missing, ambiguous,
malformed or unsupported SOURCE CFG does not remove a proved candidate; it adds
an unavailable/partial-body diagnostic. No process edges are invented. K1 expression
bodies with an unlocated synthetic return retain their trigger but report body
UNAVAILABLE. K2 currently lacks authoritative per-symbol annotation capture and
SOURCE CFG: legacy framework hints, including annotations misattributed to later
ordinary methods, are rejected; the actual K2 fixture produces UNKNOWN with no
trigger claims. This is a compiler limitation, not a new fallback parser.

Unsupported scheduler kinds, source scopes and foreign/stale contexts cannot borrow
another trigger's evidence. Explicit `selected_contexts` uses the existing T008
selection contract. Returned trigger nodes can be composed by a caller into T023
explicit documents; discovery does not create or approve a business process.

No new CLI, schema/store migration, renderer, apply/review API or runtime observation
is supplied. T025+ remains separate work.
