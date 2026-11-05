# T017 — Pure bounded topology filtering

The additive Python API consumes an already built T016 ViewDocument or its JSON
document. It never captures sources, reads a checkout, runs a worker, invokes a
model/network, writes a store or reselects contexts. Inputs are a trusted local
snapshot, not authenticated by a caller-recomputable fingerprint.

```python
from kgmaker.topology_filter import filter_topology

result = filter_topology(topology, focus_service="service:checkout",
                        direction="outgoing", max_hops=2, max_nodes=25)
visible_view = result["document"]
omissions = result["filtering"]
```

No T019 architecture CLI is implemented here; do not use invented CLI flags.
The input must have the T016 `service-topology-view-1` rule. Reapply filters to
that original input, not a previously filtered partial document.

Focus is an exact service node ID. `None` means no focus restriction; an unknown
well-formed ID yields `UNKNOWN_FOCUS` and UNKNOWN coverage. An existing non-service
focus is a controlled error. Direction controls neighborhood traversal; retained
endpoints retain their original eligible edges in their original directions.
Selection is stable BFS by distance and ID, including cycles and parallel edges.
Without focus, nodes use canonical ID order.

Hops count actual edges: service→Kafka channel→service is two hops. `max_hops=0`
is focus-only. `max_nodes` bounds real returned nodes, including existing resource
or boundary nodes; newly reported frontier entries are metadata rather than graph
nodes. Node budget is integer 1–20000, hops is None or integer 0–20000; bool, float
and negative budgets fail before producing a result. Default node budget is 200.

`relations=None` allows captured relations, while `[]` allows none. Scope can only
confirm the captured scope. Context IDs must be captured IDs; restrictions keep
whole context tuples or exclude the claim. A context-free object is not a wildcard:
under an explicit context filter it needs the already supplied
`context_independent=True` role or remains excluded. This never adds a compiler
context, shrinks a tuple or rewrites the original context selection.

Returned retained nodes/edges preserve IDs, original attributes, evidence polarity,
resolution and freshness. Removing an alternative never makes AMBIGUOUS unique.
Removing B from A→B→C never creates A→C. Baseline and context selection remain the
source values; derived view/filter fingerprints bind canonical criteria and source
content, excluding generation timestamps. No runtime/data availability is inferred.

`filtering` carries complete known omitted node/edge IDs, unique expansion inventories
for original interfaces/mappings/releases and generic original IDs, distinct counts,
and per-node reasons. Expansion inventories refer to omitted claims; a shared original
interface can also participate in a retained claim. Frontier entries reference
retained anchors and actual omitted edges; detached omissions stay in the global
inventory. No raw source/config/SQL is added to frontier metadata.

Hop/node cutoffs preserve truncation, relation/context/disconnected omissions lower
coverage, and upstream UNKNOWN remains UNKNOWN. Unknown upstream omission identities
are never invented: `omission_inventory_complete=False` and a global upstream frontier
retain that limitation. Display budget does not silently truncate metadata; inputs
have the reused bounded per-occurrence/cycle guard, 20000 graph objects and a 4 MiB
serialized result cap. Exceeding the cap rejects the whole result with a fixed code.
Recognized credential/userinfo IDs are rejected even on retained expansions; valid
Unicode and spaces remain unchanged. Inputs and existing artifacts are never written.

Source checkpoint: 33 new tests and coalesced T017/T016/T014/View/T009 **149 PASS**,
no native build or full. Final dependency/main integration, required descendant full
and independent review remain pending. See change note97 for historical RED results.
