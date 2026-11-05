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

Před startem vlastního full integrován také mainf6a6355 (Kafka PR69).
Původní vlastní unstarted/childless fronta byla auditovaně zrušena předpytest;
žádný full se neopakoval. Provider runtime zůstává stejnýad8, ostatní runtime
z rodičeKafka je již samostatně ověřený. Current-parentpure59PASS2.61s;
currentfull zůstává pending, nové zahájení bude mít vlastní manifest/receipt.

## Dokončené ověření a Return parent — 2026-11-05

Jediný strict full na `4930346` prošel **1605 PASS,10 SKIP za1683.18s**
(JUnit1615,0failure,0error). Všech2105 zachycených source/native/tool/fixture
vstupů zůstalo před/po shodných a bylo znovu nezávisle ověřeno.10SKIP jsou
explicitně nepřipravené Maven/Gradle/Windows gates; nejsou compiler PASS.
Kapacitní předchozí attempt ukončený předpytest nebyl testový běh.

Aktuální main `deb3691` (Return PR70) je integrován v `e740dac`. Vlastní
interfaces.py zůstává byte-identický s493; všechny ostatní runtime/worker/fixture
zdroje jsou přesně parent. Matching Return079 prerequisites byly zkopírované po
kontrole všech27trackedworker souborů, fixture vstupů a původních hashů871
připravených souborů. Žádný nový native build se nespouštěl.

Nezávislé source composition review Root+integrate8 APPROVE předcházelo jedné
bounded current-parent sadě: **284 PASS,0 SKIP za219.41s** (runner221.22s).
Obsahuje HTTP ambiguity/provider/compiler/T011/T006/T008/T009, celý Return a
KafkaCode, skutečné T024 K1/K2 a optional-prerequisite kontroly. Všech2113
zachycených vstupů před/po i při nezávislé kontrole zůstalo shodných. Full1605/10
platí pro493, tato284sada proe740; nový full nad finální metadata-head se netvrdí.

Všech224parent memory episodes je neměnný prefix, původní vlastní capture také
zůstává. Z dokončeného vlastního full-temp bylo po XML/exit/hash/process auditu
odstraněno pouze53748 dočasných souborů (~3.069GB), důkazy i kompletní SHA
inventář zůstávají. Tento záznam a následné memory/semantic metadata nemění
runtime/testy/native. Finální exact base/head review a guarded merge jsou
samostatný následující krok, tento záznam je nepředstírá hotové.
