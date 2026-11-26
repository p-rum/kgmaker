# Explicitní runtime capture — T003-S13-W01 až W03

Dodán je omezený synchronní producer pro **JDK 21 na POSIX**, zdroj
[`RuntimeTrace.java`](../tooling/runtime/java/org/kgmaker/runtime/RuntimeTrace.java).
Implementace a přesné kontroly jsou v [change122](changes/122_runtimeTraceProducer.md).
SDK je zdroj v checkoutu, není automaticky instalovaným Java agentem ani součástí
Python wheelu. Přeložte jej explicitně spolu s instrumentovanou aplikací.
Nepotřebuje externí Java závislosti.

`RuntimeTrace.call(callerId, targetId, Supplier)` skutečně zavolá callback a zaznamená
`RETURNED` nebo `THREW`. `bean(factoryId, typeId, Supplier)` zaznamená dokončení
factory jako `CREATED` (nenulový výsledek), `NULL` nebo `THREW`; netvrdí novou alokaci
ani registraci do Spring kontejneru. `condition(ownerId, predicateId, BooleanSupplier)`
vyhodnotí predikát a zachytí boolean. `mapping(router, ownerId, handlerId, method,
route, Supplier)` skutečně vloží handler do předané `Map<String, Supplier<T>>`
a teprve poté zachytí registraci. Tyto identifikátory musí pocházet ze symbolů
vybraného compiler kontextu. Správné přiřazení callbacku k symbolu je odpovědnost
instrumentace; nejde o automatickou analýzu libovolného frameworku.

SDK zapisuje pouze při `KGMAKER_RUNTIME_TRACE=1` a explicitním
`trace.writeTo(System.out)`. Bez opt-in normálně vykonává aplikaci, ale nevydá trace.
`runtime produce` nastaví opt-in jen svému potomkovi. Scan, hook, feature,
data-check a runtime import producer nevolají. Zachycené argumenty, návratové
hodnoty, výjimky, env a logy se do JSON nekopírují. V SDK je metoda i boolean typová
hodnota; z route se odstraní autorita včetně user-info, query a fragment, potom se
exportuje pouze SHA-256 cesty. Hash není anonymizace: instrumentujte neosobní
šablony cest, metadata a symboly musí být neobsahující tajné údaje.

## Spuštění

Nejprve proveďte explicitní build/inspection běžným build workflow projektu.
Vybraný uložený schema-3 compiler context musí mít `build_id`,
`config_fingerprint`, zdrojový snapshot a symboly. Již zachycené bytecode/classpath
artefakty se kontrolují pomocí sdílené validace snapshotu. Identita buildu a
konfigurace musí přesně odpovídat kontextu; service/version jsou povinné deklarované
identifikátory. Nejde o ověření nasazené verze, úplného prostředí procesu nebo dat.

Před importem doplňte `config_fingerprint` do zvolené položky `contexts[]`
BuildManifestu v1. Hodnota je 64 malých hexadecimálních znaků SHA-256
deklarované netajné konfigurace. Níže je výřez položky pro `root:main`.

```json
{
  "id": "root:main",
  "config_fingerprint": "c3516db82491fcad01be61b4de37706d372452cd15fb93fb22452dc285ab1662"
}
```

```sh
kgmaker project build-import --root PROJECT --manifest /path/to/configured-manifest.json
kgmaker inspect code --root PROJECT --build-id BUILD_ID --context root:main
```

Inspekce přebírá digest výhradně z vybrané položky. Build import označuje dodaný
export jako `SUPPLIED_EXPORT_UNVERIFIED`. Manifest bez pole funguje pro
build import a compiler inspekci. Runtime v2 a v3 vyžadují shodnou deklarovanou
hodnotu v uloženém kontextu a v `--config-fingerprint`.

Příklad explicitní kompilace SDK a aplikace:

```sh
javac --release 21 -d PROJECT/classes \
  tooling/runtime/java/org/kgmaker/runtime/RuntimeTrace.java \
  PROJECT/src/main/java/example/TraceApplication.java
```

Po přípravě odpovídajícího compiler kontextu spusťte pouze zvolenou aplikaci.
Hodnoty `CONTEXT_ID`, `BUILD_ID`, `CONFIG_FINGERPRINT` a argumenty symbolů nahraďte
aktuálními identitami z jejího uloženého kontextu. Argumenty za `--` tvoří argv,
žádný shell se nevytváří:

```sh
kgmaker runtime produce --root PROJECT --context CONTEXT_ID --runtime-id run-1 \
  --build-id BUILD_ID --config-fingerprint CONFIG_FINGERPRINT \
  --service-id orders --service-version 1.2.3 --timeout 120 \
  --cancel-file .kgmaker/runtime/cancel --output .kgmaker/runtime/trace.json \
  -- java -cp classes example.TraceApplication MAIN_ID FACTORY_ID TYPE_ID CONDITION_ID HANDLER_ID
kgmaker runtime import --root PROJECT --manifest PROJECT/.kgmaker/runtime/trace.json
```

`--output` je volitelný; bez něj CLI vrátí JSON na stdout. Výstupní soubor musí být
`.json` pod `PROJECT/.kgmaker/runtime/`, mimo zachycené vstupy, bez symlinků.
Tak export nezneplatní compiler snapshot přidáním nového projektového config JSON.
Před spuštěním se kontrolují všechny parametry, výstupní cesta, build/config,
source/worker/classpath snapshot a cancellation. Po procesu se znovu kontroluje
uložený graf i snapshot a až potom se artefakt atomicky nahradí. Producer sám
nezapisuje graph store; import je oddělená operace.

Import ověří načtený manifest jednou před publikací. Před nahrazením
každého výstupu znovu ověří zdrojové hashe a distribuci workeru. U v2 a v3
znovu ověří i zachycené vstupy vybraného compiler kontextu včetně bytecode.
Zjištěný zastaralý vstup zastaví publikaci. Store obnoví dříve nahrazené
výstupy téže publikace. Současné publikace do grafu hlídá kontrola
očekávané generace. [Regresní ověření](changes/163_revalidateRuntimeImportPublication.md).

Limit je 50 000 facts, 8 MiB stdout a timeout `(0, 900]` sekund. Chybný JSON,
exit, neplatný fact, stale stav, timeout nebo cancellation nepublikuje nový
artefakt. Existující cancel soubor zabrání spuštění; jeho vytvoření během běhu
zruší capture. POSIX procesní skupina se ukončí i při `KeyboardInterrupt` a po
odchodu leaderu. Ověřeni jsou běžní potomci ve stejné skupině; démony, které se
odpojí přes novou session, tento bounded runner neizoluje. Nejde o sandbox ani
rollback vedlejších účinků uživatelem spuštěné aplikace.

## Uzavřený protokol

Stdout produceru smí obsahovat právě objekt s `facts`, `status`, `diagnostics`.
Bare array, další pole, libovolný diagnostický text a URL se odmítnou bez jejich
kopírování do výstupu nebo chybové zprávy. Obecná sanitizace volného textu se
neslibuje. Povolená pole factu jsou přesná:

| kind | Povinná pole kromě kind |
|---|---|
| call | caller, target (method/function/constructor IDs), outcome (`RETURNED`/`THREW`) |
| bean | factory (method ID), bean_type (class/interface/object ID), outcome (`CREATED`/`NULL`/`THREW`) |
| condition | owner (class nebo method ID), predicate (method ID), matched (boolean) |
| mapping | owner, handler (method ID), method (GET/POST/PUT/PATCH/DELETE/HEAD/OPTIONS), route_sha256 |
| interface_dispatch (v3) | caller_owner, caller_name, caller_descriptor, source_line, receiver_type, target_owner, target_name, target_descriptor |
| value_presence (v4) | caller_owner, caller_name, caller_descriptor, source_line, presence (`PRESENT`/`ABSENT`) |

Všechny symboly musí být ve vybraném kontextu i graph nodes a mít cestu v jeho
source snapshotu. `status` je `COMPLETE`, `PARTIAL` nebo `UNKNOWN` a nikdy se
neodvozuje z pouhé existence facts. PARTIAL/UNKNOWN vyžaduje diagnostiku.
COMPLETE vyžaduje neprázdné facts bez diagnostik a označuje pouze dodaný capture.
SDK vždy vydá **PARTIAL / INSTRUMENTED_SCOPE_ONLY**, protože zachycuje pouze
explicitně instrumentované místo a vykonanou větev. Další povolené kódy jsou
`NO_FACTS`, `CAPTURE_INCOMPLETE`, `CAPTURE_UNKNOWN`, `FACT_LIMIT`.

Envelope v2 přidává runtime/context/build/config/service/version identity,
`source_hashes`, `worker_distribution`, `source_identity` (SHA-256 kanonického
uloženého kontextu a source manifestu), `producer` (`command_fingerprint`, `opt_in`)
a prázdné `observations`. Command argv, stderr a název executable se neexportují.
Label identity jsou neprázdné, do 200 znaků, znaky ASCII alfanumerické plus
`_.:+-`; service/version nejsou místo pro tajné hodnoty.

Import v2 kontroluje celý envelope, facts a identity před zápisem. Facts zatím
nepřevádí na graph evidence. Původní `observations` může v2 obsahovat jen jako
caller/target/kind se symboly ve vybraném kontextu. Pro `call` a `dispatch`
musí být volající i cíl metoda, funkce nebo konstruktor. Vynechaný `kind`
znamená `call`. Typ `framework` zachovává vlastní typově vázaná pozorování.
Volný `scenario` a `source` v2 nepřijímá. UNKNOWN nesmí vytvořit
observation evidence. Návratový status importu zachová
status v2, ani prázdný import jej nepovýší. Historický v1 import zůstává kompatibilní
pro předem sanitizované exporty se svým původním kontraktem; nemá záruky uzavřeného
v2 formátu. Dřívější nevalidované v2 z této implementační větve je nutné vytvořit
znovu. Graph/store schema v3 se nemění.

## Synchronní dispatch Java rozhraní

Ve zvolené přímé implementaci rozhraní předejte aktuální instanci.

```java
public int greet() {
    trace.observeInterfaceDispatch(this);
    return 1;
}
```

Po explicitním překladu SDK a aplikace s údaji o řádcích zdroje použijte
stejný `runtime produce` a `runtime import` jako výše.

```bash
kgmaker runtime produce --root PROJECT --context CONTEXT_ID --runtime-id run-interface \
  --build-id BUILD_ID --config-fingerprint CONFIG_FINGERPRINT --service-id orders \
  --service-version 1.2.3 --output .kgmaker/runtime/interface.json \
  -- java -cp classes example.DispatchApplication
kgmaker runtime import --root PROJECT --manifest PROJECT/.kgmaker/runtime/interface.json
```

Při vstupu do metody JDK zjistí typ instance předané přes `this` a signatury
obou skutečných stack frames. Důvěra vychází z výslovné instrumentace.
Producer s alespoň jedním `interface_dispatch` vytvoří RuntimeManifest v3.
`observations` zůstává v souboru prázdné. Offline import z `facts` odvodí
pozorování znovu proti aktuálnímu vybranému compiler kontextu. Deklarovaný
otisk příkazu ověří formátově. Původní facts lze nadále zaznamenávat samostatně
v RuntimeManifestu v2 i společně s `interface_dispatch` ve v3.

Pro důkaz musí mít vybraný `EXECUTION_BOUND` JVM kontext aktuální bytecode.
Signatura volající metody a řádek musí označit jedinou instrukci volání
`INTERFACE`. Všechny fyzické instrukce volání ve volající metodě musí mít
kladné číslo řádku svázané s vybraným bytecode. Pokud compiler graf například
u `INVOKEDYNAMIC` řádek neobsahuje, capture i offline import vrátí
`RUNTIME_DISPATCH_SITE` pro tuto metodu a zachovají poslední výstupy.
Zaznamenaný příjemce musí být konkrétní třída z vybraných Java
zdrojů a cíl její přímá implementace ve statických kandidátech daného místa.
Nejednoznačný řádek, cizí typ nebo neshodná signatura vedou k odmítnutí.
Podporovaný vzorek dokládá vstup do metody instrumentované aplikace. Jde o
dodaný záznam vybraného běhu. Otisk konfigurace vyjadřuje deklarovanou variantu.
Děděné a výchozí metody, proxy, reflexe, async a dostupnost dat mají vlastní rozsah.
[Přeložená fixture a ověření](changes/182_bindRuntimeInterfaceDispatch.md).

## Přítomnost hodnoty po přímém přiřazení v Javě

V explicitně instrumentovaném běhu použijte přímočarou Java metodu `void` pro
přímé přiřazení mezi dvěma statickými poli `String`. Zavolejte SDK ze statického
pole třídy na stejném řádku hned po přiřazení.

```java
private static final RuntimeTrace TRACE = new RuntimeTrace();

static void copyStatus() {
    Target.status = Source.status; TRACE.observeValuePresence(Source.status, Target.status);
}
```

Vybraný `EXECUTION_BOUND` kontext musí doložit deklarace obou statických polí
a stejný tok v přeložené metodě. Ověření vyžaduje přesné pořadí čtení zdroje,
zápisu cíle, načtení SDK, čtení zdroje a cíle pro hook, volání SDK a návratu.
Větvení, obsluha výjimek, další instrukce a instanční pole jsou mimo tento
rozsah. Nepřítomný nebo nejednoznačný doklad skončí `RUNTIME_VALUE_BYTECODE`.
U dříve indexovaného buildu zopakujte explicitní inspekci vybraného buildu
a kontextu aktuálním `kgmaker inspect code`.

Pozorování platí pro hodnoty načtené v hooku daného běhu. SDK zaznamená jen
`PRESENT` pro shodný nenulový odkaz a `ABSENT` pro dvě hodnoty `null`. Při
nesouhlasu je výsledek neúplný. SDK ukládá pouze stav přítomnosti a identitu
volajícího rámce. Při spuštění předávejte data
aplikaci jejím běžným vstupem a vynechte je z argumentů příkazu capture.

`runtime produce` vytvoří RuntimeManifest v4 s právě jedním `value_presence`
a UTC časem začátku běhu. `runtime import` znovu ověří odkaz na compiler důkaz
a vrátí `value_evidence_ids`. Graf používá oddělenou hranu `runtime_value_presence`
bez vlivu na statické cesty. Pro stejný běh a přiřazení použijte stejný export
při opakovaném importu. Pro nový běh použijte nové ID. Důvěra vychází z
výslovné spolupráce instrumentované aplikace a lokálního exportu.

[Živá kontrola dostupnosti](feature-analysis.md#runtime-presence-in-data-check)
· [Změna a ověření](changes/187_bindRuntimeValuePresence.md).

## Opakovaný import a navigace

Opakovaný import pro stejnou dvojici symbolů a přesný compiler kontext uchová
připojené doklady všech zpracovaných běhů. Nový doklad v2 rozlišuje i shodné
`runtime_id` pro rozdílné
`service_id` nebo `service_version`. Ukládá také `build_id`,
`config_fingerprint` a původní `source_identity`. Doklady v jiném compiler
kontextu mají vlastní hranu. Shodný doklad se k hraně připojí jen jednou.
Opakovaný import znovu ověří vstupy, přidá diagnostiku a publikuje graf.
Existující záznamy v1 si uchovají svoji identitu a původní rozsah údajů.
V2 doklad používá ověřené konce pozorování, ověřené identity a otisky
zdrojů a kontextu. Jeho ID odpovídá těmto hodnotám. Python API před kontrolou
oddělí vstupní slovník manifestu a každé pozorování. Pozdější změna slovníku volajícího nemění
uloženou konfiguraci ani cíl volání. Import projde dodaný seznam pozorování
jednou a k sestavení grafu použije ověřené řádky.

```bash
kgmaker runtime import --root PROJECT --manifest PROJECT/.kgmaker/runtime/trace.json
kgmaker callgraph callees --root PROJECT --context CONTEXT_ID --symbol CALLER_ID
kgmaker callgraph path --root PROJECT --context CONTEXT_ID --from CALLER_ID --to TARGET_ID
```

`callers` a `callees` vracejí připojená pozorování jako `RUNTIME_OBSERVED`
s odkazy na důkazy a `dispatch_complete: false`. Pro v3 uvádějí také přesné
`call_site` a `receiver_type`. `callgraph path` a statické
cykly flow grafu sledují compiler call sites. Volba
`--include-dispatch-candidates` zahrne při hledání cesty také statické kandidáty.
Pro dvojici spojenou výhradně runtime dokladem hlásí statická cesta
`UNKNOWN`. Statické vazby se uchovají i bez pozorování.
[Rozsah opravy importu](changes/151_preserveRuntimeObservationEvidence.md).

## Ověřená hranice

[`TraceApplication.java`](../tests/fixtures/runtime-trace/TraceApplication.java)
je skutečně přeložená a spuštěná aplikace: vytvoří service, vyhodnotí přepínač,
zaregistruje handler, zavolá jej a ověří výsledek i počet volání. Integrační test
používá skutečný JVM worker a jeho symbol IDs; opačná větev nezaznamená mapping
ani call. Test obsahuje credential v argumentu a URL a ověřuje jejich nepřítomnost
v exportu. Samostatné kontraktové testy používají malé syntetické grafy a JSON;
nejsou vydávány za runtime producer.

Ověřené prostředí je Linux/POSIX s OpenJDK 21. Rozsah zahrnuje synchronní callbacky,
map router a výslovně instrumentované volání přes Java rozhraní s přímou implementací.
Spring registry, automatická instrumentace, Windows, širší RTA, hodnotové toky,
async, reflexe, nasazení a dostupnost dat mají vlastní ověření. Viz [acceptance](acceptance-inventory.md) a
[stavová matice](production-analysis-progress.md).
