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
