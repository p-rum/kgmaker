# Odvozené pohledy: cache a invalidace (T037)

T037 přidává explicitní Python API pro opakované použití už vytvořeného
`ViewDocument`. Cache je jeden verzovaný JSON artefakt. `get_or_build_view()`
vyžaduje úplný public workspace snapshot, graph snapshot, mapu verzí pravidel,
scope a vybraný context. Změna kterékoliv z těchto závislostí je cache miss a
spustí builder. První implementace invaliduje celý pohled; neprovádí selektivní
recompute.

```python
from pathlib import Path

from kgmaker.view_cache import get_or_build_view

view = get_or_build_view(
    Path(".kgmaker/views/topology.json"),
    workspace=workspace_snapshot,
    graph=graph_snapshot,
    rules={"topology": "service-topology-view-1", "ownership": "service-ownership-1"},
    scope="production",
    context_selection=selection,
    expected_baseline_fingerprint=expected_baseline_fingerprint,
    builder=lambda: build_topology(workspace_snapshot, graph_snapshot, selection),
)
```

`expected_baseline_fingerprint` is required and must be derived from the same
current inputs used by `builder`. This rejects an old builder result even when
its scope and rule version happen to match. The cache recomputes the dependency
binding after the builder returns and refuses publication if the builder changed
the captured inputs.

Workspace binding zahrnuje služby, ownership, contract/release mapping a všechny
explicitní provider deklarace. Graph binding zahrnuje celý graph včetně kontextů,
anotací, evidence a provider uzlů; generovaný čas není závislost. Úplný snapshot
znamená, že i dříve chybějící provider změní fingerprint a unresolved lookup se
znovu vyhodnotí. Změna pravidel je explicitní přes `rules`; volající musí předat
každou verzi pravidla použitého builderem.

Cache vrací pouze `ViewDocument` se stejným fingerprintem, scope a context
selection. Dokument se validuje před publikací; zápis používá existující
`analysis_model.atomic_write`. Neplatný vstup nebo selhání builderu zachová vstupy
a poslední artefakt. Poškozená cache je miss a zůstává beze změny, dokud builder
nevrátí validní view. Starší/unknown cache schema se nepřevádí ani nepovažuje za
čerstvou.

Tato cache neuchovává approval store ani nezvyšuje evidence kind, freshness,
scope či runtime status. T032 zůstává autoritou pro persisted process reviews.
Pokud výsledný pohled závisí na approval, caller předá čerstvý výsledek
`read_process_reviews(...)` přes `annotations`; APPROVED → NEEDS_REVALIDATION pak
způsobí miss, ale review payload se nekopíruje do technického topology view.
Integrovaný `aggregate_service_topology_cached(...)` používá validovaný T016
handoff jako plný vstupní snapshot a ověřuje baseline výstupu proti aktuálnímu
capture ID. Topology CLI nabízí stejnou cestu jen přes explicitní `--view-cache`:

```sh
kgmaker architecture topology --capture-snapshot topology-inputs.json \
  --view-cache .kgmaker/views/topology.json
```

Bez `--view-cache` jsou view renderery a CLI cache-free; T019 replay zůstává
read-only ve výchozím stavu. Existující CLI exit codes ani JSON envelope se
nemění.

Limity: artefakt je lokální a single-file, ne distribuovaná cache. Fingerprint
záměrně invaliduje i při nesouvisející změně graph/workspace snapshotu. Builder
odpovídá za to, že jeho vstupy skutečně odpovídají předaným snapshotům a mapě
pravidel; cache sama nečte checkout ani neobnovuje graph. Pro atomickou publikaci
uživatelských exportů a širší locking kontrakt viz samostatné T038.

Implementační výsledky T037 a přesná omezení jsou v
[change121](changes/121_invalidateDerivedViews.md).
