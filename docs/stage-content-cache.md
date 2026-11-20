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
[compiler inspection](compiler-inspection.md). Každý explicitní příkaz ověří
handshake a provede skutečný worker analyze a compiler projekci. Frontend
provede project preflight, JVM framework augmentation. Příkazy scan, hook,
feature a data-check zachovávají dosavadní offline chování.

Výsledek JSON obsahuje `cache.version = extraction-stages-1`
a `cache.stages`. Každá fáze hlásí `BYPASS` s důvodem
`UNVERIFIED_REPLAY`, `INCOMPLETE_INPUT_CLOSURE`
nebo `CACHE_SIZE_LIMIT`. Coverage, diagnostics a exit code
zachovávají svůj význam.

## Úplný klíč a kontrola odvozených údajů

Klíč obsahuje actual confined root, repo/module/source-set/variant/scope a celý
captured selected context. Tím se váže source/JPA XML/TS config a discovery closure,
classification/config, options/build/project/manifest/dependency model, skutečný
worker handshake/distribution a classpath/bytecode obsah. Přidává se konkrétní
launcher a JDK platform bytes, verze/obsah lokálních extractorů, stage, normalized
base graph a konkrétní upstream response. Stejná zobrazovaná jména nenahrazují
identity varianty. Z base graph se vynechávají pouze cache a generation timestamp.

Worker a graph validátory kontrolují čerstvé výsledky vůči vybranému
kontextu, scope, upstream odpovědi a workeru. Digest uložený vedle cache je
kontrola integrity formátu. Autoritu konkrétní hrany nebo coverage určuje
aktuální worker a projekce. Celá použitá closure se ověří před commit.
Změna source/config/worker/classpath během inspekce vrací STALE.

Předchozí uložené kontexty vyžadují pro obnovu evidence explicitní inspekci
konkrétního kontextu. Při jejím sloučení má čerstvý důkaz stejné identity
přednost před uloženým. Replay je pozastavený i při úplné closure.

## Store, kompatibilita a limity

Index `graph.json` má aditivní `extraction_cache` envelope v1; nejsou to graph facts.
V1/v2/v3 bez cache zůstávají čitelné. Unknown/corrupt envelope se ignoruje a graph facts se čtou samostatně. Public `KnowledgeGraph.to_dict()`
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

Historický scope před konzervativní opravou: Java+Kotlin přes připravené JDK21/K1/K2 workery a TypeScript
5.7.3; explicitní classpath/config mutace a warm callcounts. Konkrétní běhy a
NOT_RUN kontroly jsou v [change133](changes/133_stageContentCache.md). Celý T003-S10
zůstává PARTIAL; cache není inkrementální build compileru ani production latency slib.

Aktuální ověřený scope opravy a zbývající práce jsou v [change135](changes/135_bindCachedCompilerEvidence.md).

## Selektivní dopad změn

Uložte výchozí graf pomocí `kgmaker scan` nebo explicitní inspekce, proveďte
změnu a spusťte report ještě před obnovením indexu.

```bash
kgmaker impact --root ./service --evidence-only --format json \
  src/main/java/Api.java src/main/resources/db/migration/V1__schema.sql openapi.json
```

Režim pokrývá všechny uložené kontexty lokálního repozitáře. Vstupy jsou relativní
cesty k souborům. Podporuje odstranění zachycených souborů. `--scope` přijímá
`all`, kombinace s `--context`, `--entity` nebo `--include-data-flow` vrátí chybu.

JSON v1 uvádí SHA-256 jedné uložené generace `graph_sha256`, pole `changed_sources`
s předchozím a zjištěným hashem (při odstranění `after_sha256: null`), pole
`affected` a `diagnostics`. Každý dotčený záznam má stávající identitu `id`, druh,
cestu (u závěru feature `null`), stav a seznam `reasons`:

| Druh | Stav | Důvod |
|---|---|---|
| `COMPILER_CALLER` | `RECHECK` | Přímý lokální `declared_target` s dvojicí compiler důkazů ze stejného obsahově ověřeného kontextu. Report uvádí identitu kontextu, call site a obou důkazů. Přenos dopadu sleduje přesnou identitu zasaženého symbolu přes volání uvnitř souboru i mezi soubory. |
| `SCHEMA_DEPENDENT` | `RECHECK` | Cizí klíč k tabulce nebo explicitní projekce view k jeho zdrojovému sloupci ve stejném deterministicky přehrávaném Flyway streamu. Report uvádí grafovou vazbu, identitu objektu a řádek migrace. |
| `CONTRACT_DECLARATION` | `RECHECK` | Doložená deklarace endpointu v zachycené OpenAPI JSON/YAML se shodným hashem zdroje, použitelnou variantou a jejím fingerprintem. |
| `FEATURE_CONCLUSION` | `STALE` | Přímá platná citace z požadavku na vstup, capability match, impact path nebo test plan v existující použité lokální revizi. Report uvádí identitu citace, revizi a starý i aktuální hash. Použitá revize vyžaduje souhlas kandidáta, receipt a původního packetu. |

Výstup má `coverage: PARTIAL`. Obsahuje pozitivní historické vazby a může uvést
diagnostiku pro chybějící nebo nečitelný zdroj, starší graph, neověřenou compiler
vrstvu či nedostupnou revizi feature. Záznamy revizí se čtou pouze z běžných souborů.
Při nečitelném nebo nesprávně strukturovaném uloženém grafu příkaz skončí kódem
1 a bez výstupu JSON. Nečitelný změněný zdroj vrací `DEPENDENCY_PATH_UNAVAILABLE`.
Nové soubory mimo zachycený rozsah, negativní
lookupy, dynamický dispatch, cross-workspace vazby, aktuální platnost starého
compiler rozlišení a nasazení nebo dostupnost dat vyžadují vlastní důkaz.
Report je vodítko k revalidaci. Uložený graf, stav feature a pravidla jejího
`apply` ani `revise` se příkazem nemění. Příkaz nespouští workery, buildy, instalaci,
migrace ani aplikaci. Graph/store nadále čte v1/v2/v3 bez migrace. Dosavadní
formáty příkazu `impact` se používají stejně. [Ověření a limity](changes/145_buildReverseDependencyIndexes.md).
