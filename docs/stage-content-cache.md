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
# Node je dostupný přes ./tools/node v adresáři, odkud spouštíte KGMAKER.
PATH="./tools:$PATH" kgmaker inspect frontend --root ./ui --tsconfig tsconfig.json
# Příklad s ASCII cestami na POSIX, Javac 21 a starší sadou platformních symbolů.
LC_ALL=C kgmaker inspect code --root ./service --java-release 17
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

## Klíč a kontrola odvozených údajů

Klíč obsahuje actual confined root, repo/module/source-set/variant/scope a celý
captured selected context. Tím se váže source/JPA XML/TS config a discovery closure,
classification/config, options/build/project/manifest/dependency model, skutečný
worker handshake/distribution a classpath/bytecode obsah. Přidává se konkrétní
launcher a JDK platform bytes, verze/obsah lokálních extractorů, stage, normalized
base graph a konkrétní upstream response. Stejná zobrazovaná jména nenahrazují
identity varianty. Z base graph se vynechávají pouze cache a generation timestamp.

Klíč aktuální JVM inspekce obsahuje identitu výběru compiler vstupů, přesné
bajty v `source_files` a normalizovaný otisk odlišných souborů z
`normalized_source_files`. Offline kontrola compiler kontextu zjistí změnu
samotných konců řádků i změnu uloženého výběru bez odpovídající nové inspekce.
[JVM source byte fingerprints](compiler-inspection.md#jvm-source-byte-fingerprints).

Java otisk zahrnuje `lib/ct.sym` a na POSIX přesné bajty `LANG`, `LC_ALL`
a `LC_CTYPE` včetně hodnot mimo UTF-8 a rozdílu mezi nepřítomnou a prázdnou hodnotou. V uloženém
klíči je jen SHA-256 prostředí. Na Linuxu se do otisku přidává obsah
`lib/libjli.so` a `lib/server/libjvm.so` ve standardním rozložení JDK.
[Ověření nativních vstupů](changes/180_bindLinuxJdkNativeInputs.md).
Chybějící nebo nečitelný vstup otisku
znamená `INCOMPLETE_INPUT_CLOSURE`, pokud živá inspekce proběhne úspěšně.
Při výběru přes symbolický odkaz `java` tvoří otisk bajty cílové binárky
a její JDK vstupy, i když má cílová binárka jiné jméno. Spustitelná binárka
bez práva čtení může provést živou inspekci s `BYPASS/INCOMPLETE_INPUT_CLOSURE`.
Výběr `java` i `node` z relativního `PATH` se ukotví v pracovním adresáři
KGMAKERu. Stejná absolutní cesta včetně symbolického odkazu vstupuje do
spuštění workeru i do otisku, takže změnu cíle lze zjistit.
[Ověření relativní cesty k Node](changes/188_anchorTypeScriptNodeLauncher.md).
Prostředí předávané workerům a compiler volby se řídí stávajícím launcherem.

Worker a graph validátory kontrolují čerstvé výsledky vůči vybranému
kontextu, scope, upstream odpovědi a workeru. Digest uložený vedle cache je
kontrola integrity formátu. Autoritu konkrétní hrany nebo coverage určuje
aktuální worker a projekce. Zaznamenané vstupy se ověří znovu před commit.
Otisk launcheru a platformních souborů čte při každé kontrole všechny jejich
bajty průběžně. Grafová fáze při živém běhu použije objekt z jediné kontroly
svého výstupu. [Měření a ověření](changes/178_reduceLiveInspectionOverhead.md).
Změna zdroje, konfigurace, workeru, classpath nebo zachyceného otisku
launcheru během inspekce vrací `STALE`.
Cyklický odkaz při další kontrole launcheru zneplatní dříve dostupný otisk.
Pokud už publikace nahradila některý odvozený výstup, store obnoví jeho
předchozí bajty.

Předchozí uložené kontexty vyžadují pro obnovu evidence explicitní inspekci
konkrétního kontextu. Při jejím sloučení má čerstvý důkaz stejné identity
přednost před uloženým. Replay uložených kandidátů zůstává vypnutý.
Persistentní warm HIT vyžaduje nezávislý doklad vydavatele a úplně vymezené
běhové vstupy. [Ověřený rozsah tohoto dílčího kroku](changes/164_bindJavaLaunchInputs.md).

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

## Souběžná publikace grafu a build snapshotu

T003-S10-W06 vyhrazuje publikaci grafu atomickým vytvořením
`.kgmaker/workflow/graph-publication.lock`. Souběžný zapisovač končí kódem 3
a jeho graf se neuloží. `scan`, `inspect code` / `inspect frontend`, runtime
import, `graph migrate` a zapisující workspace příkazy odmítnou výsledek,
pokud se během práce změnila generace `graph.json`. Explicitní inspekce
hlásí `STALE`. Session hook při konfliktu vrátí bezpečný prázdný kontext.
Zastaralý `scan` nezmění Confluence index ani report. `scan --confluence-dir export
--confluence-report /path/to/report.md` připraví oba výstupy se stejnou publikací
grafu. Při chybě výměny grafu se vrátí jejich předchozí obsah nebo stav bez souboru.
Report lze zadat relativně k repozitáři i absolutně. Temp a rollback kopie leží
v adresáři cíle. Přímé i zanořené kolize s indexem, reporty grafu nebo značkou
zapisovače se odmítají. Explicitní schema 3 objekt pro runtime import musí
odpovídat čitelné uložené generaci, pokud store existuje. Při prvním importu
bez store funguje jako seed. Workspace může zapsat
samostatné cache záznamy podle jejich obsahového klíče i při odmítnutém grafu.
Čtení a offline analýzy workery nespouštějí.

Autoritativní `graph.json` se nadále vyměňuje jako poslední a při běžné
výjimce se odvoditelné pohledy a výstupy Confluence z `scan` vrátí pouze tehdy,
pokud je stále vlastní tento zapisovač. Značka ponechaná po tvrdém přerušení zápis bezpečně
zablokuje. Po ověření, že žádný zapisovač neběží, lze značku odstranit a
zopakovat příkaz. Běžný souběh spolupracujících zapisovačů nespoléhá na
ruční úklid. Obnova po pádu mezi zápisy lidských pohledů má samostatný
rozsah. Build runner obsadí adresář konkrétního plánu atomicky před
vytvořením jeho snapshotu. Druhý pokus se stejným `build_id` dostane
diagnostiku jako při opakovaném spuštění.

[Změna a kontroly W06](changes/144_serializeGraphPublication.md).
W01 a W06 nadále zachovávají existující provider omezení: nový rule selector
nelze publikovat vedle zachovaného stale selectoru bez jeho vyřešení.
Reverse dependencies, negative lookup invalidace a selective revise mají
samostatná zadání.

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
`all`. Kombinace s `--workspace`, `--context`, `--entity` nebo
`--include-data-flow` vrátí chybu použití s kódem 2. Kontrola `--workspace`
proběhne před načtením jeho manifestu.

Po reportu lze samostatně obnovit vybraný modul explicitní JVM inspekcí.
Pokud nezávislý modul přišel o dříve zachycený vstup se stále deklarovaným
jediným vlastníkem, inspekce může jeho starou compiler vrstvu vyřadit i při
současné úpravě jiného zachyceného vstupu téhož modulu. Pro čtecí report
zadejte obě cesty, například `kgmaker impact --evidence-only --format json
edited/src/main/kotlin/Example.kt edited/src/main/kotlin/Caller.kt`.
[Rozsah Python API a příklad](compiler-inspection.md#obnova-izolovaného-jvm-kontextu).

JSON v1 uvádí SHA-256 jedné uložené generace `graph_sha256`, pole `changed_sources`
s předchozím a zjištěným hashem (při odstranění `after_sha256: null`), pole
`affected` a `diagnostics`. Každý dotčený záznam má stávající identitu `id`, druh,
cestu (u závěru feature `null`), stav a seznam `reasons`:

| Druh | Stav | Důvod |
|---|---|---|
| `COMPILER_CALLER` | `RECHECK` | Přímý lokální `declared_target` s dvojicí compiler důkazů ze stejného obsahově ověřeného kontextu. Report uvádí identitu kontextu, call site a obou důkazů. Přenos dopadu sleduje přesnou identitu zasaženého symbolu přes volání uvnitř souboru i mezi soubory. |
| `SCHEMA_DEPENDENT` | `RECHECK` | Cizí klíč k tabulce nebo explicitní projekce view k jeho zdrojovému sloupci ve stejném deterministicky přehrávaném Flyway streamu. Uložená vazba `foreign_key_references_column` označí celý cizí klíč včetně důvodu pro každý doložený pojmenovaný sloupec. Report uvádí grafovou vazbu a identitu objektu. Pro uloženou vazbu `operation_targets` uvádí i identitu a řádek migrační operace, včetně zachycených operací před poslední změnou objektu. |
| `CONTRACT_DECLARATION` | `RECHECK` | Doložená deklarace endpointu v zachycené OpenAPI JSON/YAML se zdrojovou grafovou vazbou, použitelnou variantou a jejím fingerprintem. Porovnává se hash původních bajtů z registrace. |
| `FEATURE_CONCLUSION` | `STALE` | Přímá platná citace souboru z požadavku na vstup, capability match, impact path nebo test plan v použité lokální revizi. Report uvádí identitu citace, revizi a starý i aktuální hash původních bajtů. Použitá revize vyžaduje souhlas kandidáta, receipt a původního packetu. Lidské rozhodnutí odkazuje na odpověď v packetu. |

Při úplném lokálním přehrání verzovaných migrací ukládá `kgmaker scan` vazby
`REFERENCES parent(col)` i pro složené klíče se všemi přesně rozlišenými sloupci.
Pro důvod ve výstupu se musí shodovat uložená tabulka, sloupec, cizí klíč a
migrační operace v jednom otisku replaye a databázovém streamu. Uložený
záznam operace musí uvádět přesný sloupec mezi svými cíli a doložit svou
identitu, zdrojovou cestu a řádek. Starší grafy mohou uvádět důvody pro
tabulky a view. Nové doklady pro sloupce vytvoří `scan`. Například po
změně dříve uložené operace `ALTER COLUMN` spusťte
`kgmaker impact --evidence-only --format json src/main/resources/db/migration/V3__alter.sql`.
Neúplné přehrání, dodaný snapshot nebo implicitní `REFERENCES parent`
mohou používat původní vazbu na tabulku. [Ověření](changes/191_indexNamedForeignKeyColumns.md).

`changed_sources` porovnává soubory stejným způsobem jako uložený graf.
U textových zdrojů scanneru je to hash textu s normalizovanými konci řádků.
Při samotné změně LF↔CRLF může report označit v `affected` přímé i tranzitivní
callery. Uložený lokátor cíle musí uvádět přesnou cestu a hash
původních bajtů. V raw JVM kontextu report ověří identitu capture a zvlášť
porovná normalizovaný grafový otisk a bajtový otisk obou compiler důkazů callera.
Při shodném normalizovaném textu porovná aktuální bajty s uloženým bajtovým
otiskem cíle. Běžná změna textu dál použije dříve doložené vazby také při
chybějícím nebo neshodném lokátoru cíle. Report načítá bajty jen zadaných cest.
Cesta požadavku se pro porovnání normalizuje a původní packet drží svou identitu.
[Ověřená regrese po #145](changes/145_buildReverseDependencyIndexes.md).

Výstup má `coverage: PARTIAL`. Obsahuje pozitivní historické vazby a může uvést
diagnostiku pro chybějící nebo nečitelný zdroj, starší graph, neověřenou compiler
vrstvu či nedostupnou revizi feature. Záznamy revizí se čtou pouze z běžných souborů.
Každá hodnota raw i normalizované mapy JVM capture musí být 64 malých
hexadecimálních znaků SHA-256. Při neplatném otisku report vynechá compiler
důkazy poškozeného kontextu a zachová doložené výsledky z ostatních kontextů.
Při nečitelném nebo nesprávně strukturovaném uloženém grafu příkaz skončí kódem
1 a bez výstupu JSON. Nečitelný změněný zdroj vrací `DEPENDENCY_PATH_UNAVAILABLE`.
Nové soubory mimo zachycený rozsah, negativní
lookupy, dynamický dispatch, cross-workspace vazby, aktuální platnost starého
compiler rozlišení a nasazení nebo dostupnost dat vyžadují vlastní důkaz.
Report je vodítko k revalidaci. Uložený graf, stav feature a pravidla jejího
`apply` ani `revise` se příkazem nemění. Příkaz nespouští workery, buildy, instalaci,
migrace ani aplikaci. Graph/store nadále čte v1/v2/v3 bez migrace. Dosavadní
formáty příkazu `impact` se používají stejně. [Ověření a limity](changes/145_buildReverseDependencyIndexes.md).
