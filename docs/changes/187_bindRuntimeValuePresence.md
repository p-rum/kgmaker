# Přítomnost hodnoty po přímém přiřazení v Javě

[T003-S13-W03](../tasks/T003-S13-03-runtimeValueFlow.md), výchozí `main`
`4dc8f657b891f1716f7d134f97c1e6098cbb50b5`, strom
`aac868f1e0a5176b813f5be15a73d7d05f6dda9f`.

## Krok 1 — doložení mezery

T003-S13-W03-AC01 a AC03. Skutečný Javac, JDK 21 a JVM worker doložily přímé
přiřazení mezi dvěma poli. V2/v3 capture a offline import na výchozím kódu
odmítly tři pokusy o nový fact, včetně `PRESENT`, `ABSENT` a dalšího pole
s hodnotou. Dosavadní call observation zachovala statickou vazbu a dostupnost
`UNKNOWN`. Výchozí sonda potvrdila očekávanou mezeru s exit 0 a se shodnými
bajty grafu, pohledů a capture při odmítnutí. Výsledek SHA-256
`5442396c9107dee4237fcb21486d9bbaae263063483ef2e19a348ce6ee43d7d0`.

## Krok 2 — typovaný runtime doklad

T003-S13-W03-AC01–AC03. `observeValuePresence` přidá příznak přítomnosti až po
přímém Java `String` přiřazení. Ověřuje se správný rámec, jeden konkrétní
compiler zápis a po něm jediné volání SDK na témže řádku s přesnými dvěma
čteními polí. Ověření čte stávající přiřazení, call sites, argumenty, snapshot a
bytecode. V4 zachová jen typovaný příznak a provenance včetně UTC začátku
běhu. V1–v3 si ponechávají své formáty a běžnou volbu produceru.
[Runtime validator](../../src/kgmaker/runtime_value.py) ·
[SDK](../../tooling/runtime/java/org/kgmaker/runtime/RuntimeTrace.java).

## Krok 3 — graf a živé ověření

T003-S13-W03-AC01 a AC03. Existující runtime store ukládá oddělený vztah
`runtime_value_presence` svázaný s compiler dokladem a zachová statické cesty.
Neshodné opakování téhož běhu a přiřazení se odmítne před zápisem. V4 capture
opakovaně zkontroluje vstupy i před výměnou artefaktu. Živý `feature data-check`
použije přesné ID dokladu z aktuálního vybraného grafu, efektivní schválené
mapování, očekávané `String` pole a čerstvost. `PRESENT` poskytne nejvýš
`PARTIAL/UNASSESSED`. `ABSENT`, obyčejné volání, chybné či prošlé doklady
ponechají vstup na `UNKNOWN`. V4 popisuje dodaný lokální vzorek.
`feature apply` odmítne zapsat runtime-presence proof do analýzy.
[Availability](../../src/kgmaker/availability.py) ·
[Data-check](../../src/kgmaker/data_check.py).

## Krok 4 — cílené lokální kontroly

T003-S13-W03-AC01–AC04. Přesný výběr prošel s Temurin JDK 21.0.6+7, povinným
JVM workerem a offline Mavenem 3.9.9. Výsledek je 17 PASS, 0 FAIL, 0 SKIP,
92 mimo výběr, raw exit 0 a 203,05 s. Pokryl skutečný v4 capture, offline
import, veřejný `data-check`, odmítnutí špatných bindingů a porovnání bajtů i
při pozdní změně zdroje. Zahrnul původní file-based availability, v3 dispatch a
v2 konfiguraci se skutečným Mavenem. JUnit SHA-256
`7a79ac268294d4590f449b32738007cbb71b7c1fe24f86ff88a97086b78104ed`.
Shodné vstupy před a po mají SHA-256
`7e97de54519dd8bdda3252698b5d5969afcc4f660a8ebacb2f845cd405916959`.

```sh
export JAVA_HOME=/workspace/kgmaker-tools/jdk-21.0.6+7
export PATH="/workspace/kgmaker-evidence/runtime-build-config-tools:$JAVA_HOME/bin:$PATH"
export KGMAKER_WORKERS_HOME=/workspace/kgmaker-tools/worker-dist KGMAKER_REQUIRE_WORKERS=1
export PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 JAVA_TOOL_OPTIONS=-XX:-UsePerfData
python -m pytest -q -p no:cacheprovider --tb=short \
  tests/test_runtime_value_presence.py tests/test_availability.py tests/test_runtime_trace_producer.py \
  -k 'test_runtime_value_presence or test_availability or interface_dispatch_binds_concrete or runtime_keeps_callable or runtime_import_validates_payload_once or actual_maven_public_runtime'
```

Úplná sada, Windows a GitHub Actions jsou v tomto kroku `NOT_RUN`.
[Skutečná fixture](../../tests/fixtures/runtime-trace/ValuePresenceApplication.java)
· [Testy](../../tests/test_runtime_value_presence.py).

## Krok 5 — veřejné použití a hranice

T003-S13-W03-AC04. [README](../../README.md), [runtime capture](../runtime-trace.md#přítomnost-hodnoty-po-přímém-přiřazení-v-javě),
[data-check](../feature-analysis.md#runtime-presence-in-data-check),
[acceptance](../acceptance-inventory.md) a [stav](../production-analysis-progress.md)
uvádějí dílčí rozsah. Stav je `PARTIAL` pro jeden vybraný compiler kontext a
jeden skutečně pozorovaný běh. Měření kvality, klíče, zpracování dalších Java
typů a jazyků, workspace, sestavené hodnotové cesty a trvalé použití v
aplikovaném reportu mají vlastní acceptance.

## Přenos po #170 a kontrola uloženého hooku

T003-S13-W03-AC01 a AC03. První rodič je
`3a72078b5f9fbb48986e219ea19e0381b56f6f34` a aktuální `main` je
`18ce70a077f603f1800036dc97c38553f91a506a`. [Change186](186_reconcileInstallationCompletionInventory.md)
rozšířil inventář o šest instalačních a skill kroků. Přenesený plán má 135
položek. 134 položek je shodných s `main`, mění se jen W03 na `IN_PROGRESS/PARTIAL`.
Pořadí dispatch je shodné.

V původním čtení skutečného projektovaného W03 grafu prošel doklad i po
odebrání hooku, nahrazení ID hookem z jiné metody a změně označení služby
na hodnotu s neplatným znakem. Tyto sondy měnily graf pouze v paměti a
potvrdily dřívější chování. SHA-256 sondy
`9d93543915cc65b3bace2f23fb1163c855acc330e8228b615e085f83af7e16b0`.

Čtení nyní znovu vyhledá přesné compiler přiřazení, hook a pořadí argumentů
stejným ověřením jako při capture. Uložené označení běhu a služby podléhá
stejnému omezení jako při importu. Sonda na skutečném vybraném grafu zachovala
kladný rozsah `PARTIAL/UNASSESSED` a odmítla chybějící i jiný hook, chybné
pořadí a neplatná označení. SHA-256 sondy
`94c60ca3f7f45d04ed895d151b59a080389b65278af0ba0b8bfec0840d636a2e`.

Opravený přenos prošel s reálným JDK 21 a povinným JVM workerem. Výběr má
5 PASS, 0 FAIL, 0 SKIP, 7 mimo výběr, raw exit 0 a 136,19 s. Zahrnuje tři
nativní W03 případy a dva původní testy schváleného mapování. JUnit SHA-256
`52ca10c3a9b54317cba43f3e536b93a8eb3a4d1cc2e8d9836e0ccf5e6989aaa9`.
Shodné manifesty vstupů před a po mají SHA-256
`74a7cf7b706015b9fab9d4f940c5af2640b562a3fefe2e01360297ce47178e8b`.

```sh
python -m pytest -q -p no:cacheprovider --tb=short \
  tests/test_runtime_value_presence.py tests/test_availability.py \
  -k 'test_runtime_value_presence or observed_approved_input or unapproved_or_different_business_mapping'
```

## Krok 6 — dvě deklarace statických polí

T003-S13-W03-AC01 a AC03. Obě revize nad #171 ověřily, že existující vazby
rozlišují deklarace polí, ale ne jejich příjemce. Nad publikovaným HEAD
`b407b6be741124342d50779164c64bf0642d724c`, stromem
`fee2ba2e2dc8d4d12ffb0fc15622dea47a388fc6`, původní přiřazení skutečně
zkopírovalo `null`. Hook na stejném řádku načetl shodný nenulový odkaz ze
dvou jiných objektů a veřejný `data-check` chybně vrátil `PARTIAL/UNASSESSED`.
Reprodukce se skutečným Javac, JVM workerem a veřejným CLI má SHA-256
`238f5222bba738ce89635cea7bc2a6ecd8f370491bca5e84ac4e44ba333164a1` a raw exit 0.
Přidaná regrese očekávala odmítnutí a na původní implementaci skutečně
selhala v capture i offline importu. JUnit má 0 PASS, 2 FAIL, 0 SKIP,
3 mimo výběr, raw exit 1 a SHA-256
`00b299823eee2807308b163993fe15320b3be0416992f49d7630fdd753c954de`.

V4 vyžaduje dvě skutečné statické deklarace Java `String` z aktuálně
vybraných a obsahově ověřených zdrojů. Každá deklarace označuje jedno sdílené
pole v kontextu zvolených tříd. `runtime produce`, `runtime import` i živé
čtení znovu ověřují společnou vazbu. U instančního pole odmítnou důkaz jako
`RUNTIME_VALUE_BINDING`. `PRESENT` zůstává vzorkem čtení v hooku po přiřazení
v kooperačním lokálním běhu. Rovnost hodnot mimo vzorek a souběžné zápisy
vyžadují vlastní důkaz. Formáty v1–v3, statické cesty a pravidla schváleného
mapování používají původní kontrakty.
[Validator](../../src/kgmaker/runtime_value.py) ·
[Fixture a regresní test](../../tests/test_runtime_value_presence.py).

Cílený výběr z kroku 4 s novou regresí prošel na Temurin JDK 21.0.6+7,
povinném JVM workeru a offline Mavenu 3.9.9. Výsledek je 19 PASS, 0 FAIL,
0 SKIP, 92 mimo výběr, raw exit 0 a 228,48 s. Obě odmítnuté cesty porovnaly
capture, graf a oba pohledy po bajtech. Kladný `PRESENT`, `ABSENT`, prošlý
doklad, cizí hook, chybějící statická deklarace a starší runtime vstupy jsou
součástí stejného výběru. JUnit SHA-256
`42c4ac20a5a39900e463c20594f375ea77976c61fe4ba038986750e70982ea7d`.
Ověřený manifest vstupů má SHA-256
`4b6910b8a255a045c58a4d3ad8959445b8ab01c434a542bcb54e9f01654d54f9`.
Výpis Javap dokládá `getstatic`/`putstatic` v kladné fixture a odlišné
parametry příjemce u `getfield`/`putfield` v záporné fixture. SHA-256
`f84a5c67fbac24bd11639027b13f5404d4a198f0feeb4fc9a10f11ed8a330320`.
Úplná sada, Windows a GitHub Actions jsou pro tuto opravu v tomto kroku
`NOT_RUN`. W03 zůstává `IN_PROGRESS / PARTIAL`.

## Krok 7 — přenos po #169

T003-S13-W03-AC01–AC04. Opravený první rodič
`26d172ac7604ad8ed2786d2919517e14691614e4` je přenesen nad skutečný `main`
`346536495db749a6a1d79f89b388b55f9db3da83`. Přenos zachovává publikaci
izolovaného JVM kontextu z [Change185](185_publishIsolatedJvmContext.md)
a volbu absolutní cesty Node z [Change188](188_anchorTypeScriptNodeLauncher.md).
Příslušné soubory implementace a testů na obou stranách mají stejné bajty
jako u svých rodičů. Plánovač zachovává 134 ze 135 řádků a všech 32 položek
dispatch ve stejném pořadí. S13-W03 zůstává `IN_PROGRESS / PARTIAL`.
S10-W03 nadále čeká na ověření S10-W02 v požadovaném rozsahu.

Přesný přenesený výběr má 10 PASS, 0 FAIL, 0 SKIP, 101 mimo výběr,
raw exit 0 a 249,37 s s Temurin JDK 21.0.6+7 a povinným JVM workerem.
Zahrnuje kladné statické čtení, skutečný případ jiných příjemců přes capture
i offline import, časovou platnost, schválení mapování a runtime doklady v1–v3.
JUnit má SHA-256 `b74566800502ecee3f96ca0ef96e3809eba1531d4eecf9e3bc344baeb6541482`.
Vstupy se během běhu nezměnily a jejich manifest má SHA-256
`67f2df312afc06276a5bed39270982590fc8477398fb278ea2e7899769d20313`.
Úplná sada, Windows a GitHub Actions jsou v tomto kroku `NOT_RUN`.

```sh
python -m pytest -q -p no:cacheprovider --tb=short \
  tests/test_runtime_value_presence.py tests/test_availability.py tests/test_runtime_trace_producer.py \
  -k 'test_runtime_value_presence or observed_approved_input or unapproved_or_different_business_mapping or interface_dispatch_binds_concrete or runtime_keeps_callable'
```
