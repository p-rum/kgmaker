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
the caller's original captured inputs (top-level key changes and nested/list changes
are included); the wrapper does not keep a one-time top-level copy. The same check
runs immediately before publication.

Workspace binding zahrnuje služby, ownership, contract/release mapping a všechny
explicitní provider deklarace. Graph binding zahrnuje celý graph včetně kontextů,
anotací, evidence a provider uzlů; generovaný čas není závislost. Úplný snapshot
znamená, že i dříve chybějící provider změní fingerprint a unresolved lookup se
znovu vyhodnotí. Změna pravidel je explicitní přes `rules`; volající musí předat
každou verzi pravidla použitého builderem.

Pro navazující validaci existují `prepare_view(...)`, `prepare_snapshot_view(...)`
a `service_topology.prepare_service_topology_cache(...)`. Mají stejné vstupy jako
odpovídající okamžitě zapisující wrappery a vracejí `PreparedView`: `.document` je
validovaný pohled, `.publish()` provede kontrolu původních závislostí a atomický
zápis. Příprava nevytváří soubor ani adresář. Cache hit při publish nic nepřepisuje.

```python
from kgmaker.service_topology import prepare_service_topology_cache

pending = prepare_service_topology_cache(captured, Path(".kgmaker/views/topology.json"))
validate_consumer_requirements(pending.document)
view = pending.publish()  # Explicit commit after consumer validation succeeds.
```

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
nemění. CLI publikuje až po validaci filtru, očekávaného fingerprintu, bezpečnosti
výstupu a jeho velikosti a po úspěšném stdout write/flush, pouze pro exit 0.
Chybný formát/filtr, fingerprint konflikt, zrušení, strict exit 4 ani selhání stdout
nemění capture ani poslední cache. Publikace znovu ověří původní závislosti.

Cíl musí být vyhrazený cache soubor. CLI odmítá shodu s capture, selectors,
workspace manifestem či cancel souborem; API i CLI odmítají symlink cíle/rodiče,
hardlinky a ne-regulární cíle. Při `--capture-local` může cesta uvnitř zdrojového
repozitáře ležet pouze v `.kgmaker/views/`; source a původní index se nepřepisují.
Selhání atomické výměny zachová poslední obsah a odstraní dočasný soubor i nově
vzniklé prázdné adresáře. V tom případě CLI vrátí 2; validní view už mohlo odejít
na stdout, proto příjemce musí kontrolovat exit code. Stdout a cache nejsou společná
atomická transakce exportu. Kód nevrací zpět vedlejší efekty, které vyvolá samotný
uživatelský builder; detekuje změnu jeho vstupů a zabrání publikaci výsledku.

Limity: artefakt je lokální a single-file, ne distribuovaná cache. Fingerprint
záměrně invaliduje i při nesouvisející změně graph/workspace snapshotu. Builder
odpovídá za to, že jeho vstupy skutečně odpovídají předaným snapshotům a mapě
pravidel; cache sama nečte checkout ani neobnovuje graph. Pro atomickou publikaci
uživatelských exportů a širší locking kontrakt viz samostatné T038.

Implementační výsledky T037 a přesná omezení jsou v
[change121](changes/121_invalidateDerivedViews.md).
