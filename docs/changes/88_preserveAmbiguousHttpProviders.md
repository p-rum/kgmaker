# Zachování nejednoznačných HTTP provider variant

T010-AC03–06, T004-R01/R02: dvě deklarace OpenAPI POST /orders/{id}
a/orders/{name} mají stejnou normalizovanou route, SHA a nulový source line.
Emitoval se duplicitní ViewNode ID a katalog selhal DUPLICATE_NODE_ID.

Dvoufázová projekce zachovává logical/variant identitu, všechny candidate
attributes, původní route/IDs a proof refs v jednom AMBIGUOUS objektu. Konfliktní
scalar fields jsou None; service edge je také AMBIGUOUS a používá existující
T009 agregaci důkazů. Jedna varianta se nikdy nevybírá a ostatní rozhraní
nezmizí. Exact duplicates zůstávají idempotentní, jiné service/method/context
realm a YAML source locátory se neslévají. Confidence, dostupnost ani
CONTRACT_ONLY/handler status se nezvyšují; nejde o validaci celé OpenAPI.

Reused interfaces/ViewDocument/T009; žádný store, resolver, I/O nebo worker
změna. Graph1/2/3 čtení a stávající nekolidující IDs se nemění. Adaptační
rule je http-providers-2-ambiguous-variants; baseline fingerprint tím změnu
rozlišuje. Counts.found počítá výsledné HTTP objekty, každý ambiguity objekt
stále nese všechny registrace. Příklad stávající veřejné API:

```python
view = project_http_providers(workspace, graph, source_coverage=coverage)
# node.resolution_status == 'AMBIGUOUS'; node.attributes['original_routes']
# obsahuje obě deklarace; deployment/runtime zůstává UNKNOWN.
```

Architektonickou kontrolu provedl nezávislý architect před kódem. Nový actual
explicit JSON/YAML pure RED3FAIL1PASS1.88s zachytil duplicateID. Opravený
public/provider focus34PASS2.12s. Testy zachovávají skutečné soubory, dva service
realms, GET/POST a sourozence, exact duplicates/pořadí i nulovou mutaci vstupů.
Actual compiler regresní matice a jediný full dosud PENDING; tato čísla nejsou
jejich PASS. Main baseline9442114, vlastní note88 bez kolize ověřena přes57
worktrees;84–87 jsou souběžné explicitní rezervace. T013 dependency nález zůstává
dohledatelný, ale jeho contract attachment tato větev neimplementuje.

## Skutečný compiler focus a aktuální rodič

Sourcead8db56: **149PASS0SKIP50.92s**, všech2097source/native/tool/fixture
vstupů aHEAD před/po beze změny. Běžel skutečný compiler provider/T011 a
T006/T008/T009 i nové JSON/YAML případy. Původní worker/donor132licencovaných
artefaktů zůstává byte-exact, žádný nový build.

Integrován main8e81e63 (PR67), mění pouze prerequisite testy/metadata; src,
workers a fixtures protiad8 zůstávají byte-exact. Aktuální coalescedpure
nových25prerequisite+34provider případů **59PASS3.01s**. Full následuje
na tomto current-parent source; dosud není PASS. Parent216immutableepisodes
se zachovává; finalreview/merge zůstává samostatný krok.
