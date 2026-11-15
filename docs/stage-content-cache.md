# Cache explicitních inspekčních stupňů

T003-S10-W01 přidává obsahově vázané replay candidates do stávajícího graph
indexu. [Přesné změny a provedené kontroly](changes/133_stageContentCache.md).
Cache nesvědčí o runtime execution, dostupnosti dat ani správnosti business pravidel.

## Použití

Opakujte stejnou výslovnou inspekci se stejným modulem, source-setem a podporovaným
captured build contextem. Nový příkaz ani automatický build není potřeba:

```bash
kgmaker inspect code --root ./service --repo-id service --module core --source-set main --scope production
kgmaker inspect code --root ./service --repo-id service --module core --source-set main --scope production
kgmaker inspect frontend --root ./ui --repo-id ui --module app --source-set main --scope production --tsconfig tsconfig.json
```

Připravené workery a jejich toolchain musí být dostupné podle
[compiler inspection](compiler-inspection.md). Každý explicitní příkaz nadále
ověří handshake; frontend rovněž skutečný project preflight. Warm cache neznamená
nulový počet procesů v explicitní inspekci, ale vynechání worker `analyze` a
příslušných graph/framework projekcí. `scan`, hook, feature a data-check workery
nezapínají; zachovávají jejich dosavadní offline freshness kontrakt.

JSON výsledek má aditivní `cache.version = extraction-stages-1` a `cache.stages`:

| Stage | Cesta | Co hit přeskočí |
|---|---|---|
| worker-analysis | JVM, TypeScript | worker analyze; protocol, exact context a worker metadata se znovu validují |
| compiler-graph | JVM, TypeScript | existující compiler/CFG/return/field/typed-operation projekci |
| framework-graph | JVM | existující Spring/JPA/HTTP/Kafka/retry augmentation |

Každý záznam má `stage`, `status` (`HIT`, `MISS`, `BYPASS`) a konkrétní `reason`.
`COMPLETE_KEY_MATCH` pouze potvrzuje obsahovou shodu cache. Missing entry má
`NO_MATCH`, odmítnutý decoded payload `INVALID_CACHED_PAYLOAD`, neúplná closure
`INCOMPLETE_INPUT_CLOSURE`, nadlimitní payload `CACHE_SIZE_LIMIT`. Ostatní inspection
status, coverage, diagnostics a exit code si zachovávají svůj význam.

## Úplný klíč a kontrola odvozených údajů

Klíč obsahuje actual confined root, repo/module/source-set/variant/scope a celý
captured selected context. Tím se váže source/JPA XML/TS config a discovery closure,
classification/config, options/build/project/manifest/dependency model, skutečný
worker handshake/distribution a classpath/bytecode obsah. Přidává se konkrétní
launcher a JDK platform bytes, verze/obsah lokálních extractorů, stage, normalized
base graph a konkrétní upstream response. Stejná zobrazovaná jména nenahrazují
identity varianty. Z base graph se vynechávají pouze cache a generation timestamp.

Hit znovu validuje payload vůči vybranému contextu, scope a workeru. Cached graph
má shodné odvozené project/coverage/status/diagnostics s validated response.
Přepočtený hash cizího payloadu proto nestačí. Celá použitá closure se ověří také
před commit; late source/config/worker/classpath drift vrací STALE.

Nepodporované dodatečné runtime options, neúplná legacy closure nebo nadlimitní
cache znamenají BYPASS. Explicitní inspekce může stále provést původní cestu;
cache neodhaduje chybějící inputs. Cache používá konzervativní celý base graph:
změna jiného zdroje může zneplatnit graph stage, i když compiler stage vybrané
source-set zůstane shodný. Selective per-file extraction není W01.

## Store, kompatibilita a limity

Index `graph.json` má aditivní `extraction_cache` envelope v1; nejsou to graph facts.
V1/v2/v3 bez cache zůstávají čitelné. Unknown/corrupt envelope se ignoruje jako
cache miss, bez povýšení či smazání validních facts. Public `KnowledgeGraph.to_dict()`
a scoped graph outputs metadata neobsahují. Store používá explicitní
`to_dict(include_cache=True)` a cache se publikuje spolu s graph JSON.

Limit je 24 entries a 16 MiB pro celý envelope. Starší eligible entries se mohou
odložit; graph facts ostatních module/source-set/variant contexts se zachovají.
Podporované selected contexty nemají nové entity IDs ani runtime evidence.

Store nejdřív validuje/serializuje graph a oba generated render výstupy. Po
přípravě všech temp souborů je autoritativní graph JSON vyměněn poslední. Při
běžné výjimce se obnoví jen vlastní dosud nezměněné generated soubory a odstraní
vlastní prázdné adresáře; souběžně změněný obsah se nepřepisuje. Poslední validní
graph/cache generace zůstává čitelná. `publish=False`, strict PARTIAL, invalidní
payload, STALE, timeout či cancellation nic nepublikují. Změny uživatelských
zdrojů způsobující abort se samy nevracejí.

Jde o single-writer exception safety. W01 netvrdí crash-recovery, vícewriterový
commit, reverse dependencies, negative lookup invalidaci, selective revise ani
W02–W06. Zachovává existující provider omezení: nový rule selector nelze publikovat
vedle zachovaného stale selectoru bez jeho vyřešení. Cache to neobchází.

Ověřený actual scope: Java+Kotlin přes připravené JDK21/K1/K2 workery a TypeScript
5.7.3; explicitní classpath/config mutace a warm callcounts. Konkrétní běhy a
NOT_RUN kontroly jsou v [change133](changes/133_stageContentCache.md). Celý T003-S10
zůstává PARTIAL; cache není inkrementální build compileru ani production latency slib.
