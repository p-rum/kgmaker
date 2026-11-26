# Publikace izolovaného JVM kontextu při zastarání jiného modulu

[T003-S10-W02](../tasks/T003-S10-02-reverseDependencyIndexes.md), kroky 1–5,
AC01–AC04 a T003-AC10. Výchozí `main` je
`49bab32c50436782a2009455a36ada41c06be42f`.

## Krok 1 — reprodukce přerušení publikace

Se skutečným JDK 21.0.6+7 a oběma Kotlin backendy vrátí worker pro
vybraný modul nový platný call site. Kontrola jiného zachyceného modulu
se změněným zdrojem přerušila celý pokus s `STALE`. Graph JSON a oba
lidské výstupy zůstaly bajtově shodné s předchozí generací. Offline
`kgmaker scan` následovaný druhou inspekcí označil starý kontext, uložil
nový vybraný výsledek a zachoval důkaz nezávislého třetího modulu.
Přímý běh na základní revizi má pro každý backend očekávaný exit 1.
SHA-256 nezávislé reprodukce v implementačním worktree je
`da23701a0a4d74d8e69a8fc9ed11a1bd1d01cb08c5b0ed4b3276de4808653ad6` pro K1 a
`5b9b2503bbf3065300491dc2e370bc01f92e4f91c2b1dd7ef219f89f39f8b05f` pro K2.

## Kroky 2 a 3 — oddělený důkaz a atomická publikace

`graph_provider.py` rozlišuje změnu bajtů existujících zachycených
`.java` nebo `.kt` souborů současného raw JVM formátu při shodné množině
cest. Používá ji pouze pod výslovným modelem s výhradním vlastnictvím souborů
jednotlivými moduly, bez společných cest, bytecode a build manifestu.
Každý povolený classpath záznam musí odpovídat skutečné cestě a SHA-256
knihovny ze stejné ověřené distribuce workeru. Propletené grafové vazby,
důkazy a anotace blokují tuto omezenou obnovu.

Stávající `STALE_COMPILER_CONTEXT` marker označí starý kontext a jeho
compiler důkazy a cache se vyřadí ve stávajícím složení grafu.
`inspection.py` zachovává kontrolu vybraného i všech ponechaných platných
kontextů a CAS před výměnou výstupů. Dodatečná bajtová kontrola porovnává
s počátečním scanem pouze vstupy kontextů právě označených jako `STALE`.
Pozdější LF↔CRLF změna v těchto vstupech spustí rollback. Uložené grafy
v1–v3 a formát cache zůstávají čitelné.

## Krok 4 — kontroly

Zpětnou kompatibilitu ověřuje skutečný K1 při pozdní změně LF→CRLF mimo
vstupy všech zachycených kontextů. Kód výchozí revize publikoval, exit 0.
První kandidát s příliš širokou kontrolou vrátil `STALE`, exit 1. JUnit
SHA-256 obou kontrol je
`1225cd37cc784eca451d3118e730a006e2beff32afe74b4af7b46250e587e0c9` a
`ec018e23e6ddf3f229824ff2bc4f592f1b1c10ec93488e6653cfb0322f5dd984`.

V Cloud Environment prošlo **36 PASS / 0 SKIP** za 154,69 s v CPython 3.12.14 s JDK 21.0.6+7.
K1 i K2 v jednom volání publikovaly nový cíl, označily starý nezávislý
kontext, odstranily jeho symboly, volání, CFG, důkazy i cache a zachovaly
celou compiler vrstvu třetího modulu. Obě varianty odmítly pozdní změnu
vybraného modulu, pozměněný SHA-256 classpath, knihovnu se shodnými bajty
mimo distribuci a smíšenou anotaci. Pozdní úprava LF→CRLF v již
zastaralém modulu po skutečné výměně Mermaid obnovila předchozí diagram
a zachovala všechny bajty store. Samostatný K1 případ ověřil odmítnutí
skutečně překrytých vlastnictví. Výběr zahrnuje také Javac změnu signatury
s tranzitivními callery a stávající provider a souběžnou publikační sadu.
K1 znovu publikoval při pozdní změně LF→CRLF mimo zachycené vstupy,
samostatně s vyřazeným kontextem i bez něj. Souběžní skuteční workeři
zachovali novější uloženou generaci.

Pytest, sestavení manifestu a jeho porovnání mají exit 0. JUnit SHA-256
`9a92ea73ea4e21fb2b99ab243a1246a3feb5cb90af0c5ff37d654feac17f898b`.
Shodné 452řádkové manifesty mají SHA-256
`2ccf26de4c378f841ab289997fbad0dd92e7b559180d7b24ae74e3bef8d24ce7`.
Plánovač na tomto základu načetl 119 položek. W02 je `MERGED/PARTIAL`
a W03 vyžaduje `VERIFIED_IN_SCOPE`. SHA-256 výřezu plánu je
`a1951de16b98f03eeb44196e0052bace05e92e38b1f9ae586d01dea223f5aef2`.

```bash
KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 JAVA_TOOL_OPTIONS=-XX:-UsePerfData \
  python -m pytest -n 2 --dist load --maxschedchunk=1 -q --tb=short -ra \
    -p no:cacheprovider -o tmp_path_retention_policy=failed \
    tests/test_reverse_dependency_index.py tests/test_graph_provider.py \
    tests/test_graph_publication_concurrency.py tests/test_stage_content_cache_actual.py \
    -k 'test_graph_provider or test_graph_publication_concurrency or test_actual_jvm_isolated_stale_peer or test_actual_jvm_overlapping_stale_peer or test_actual_javac_signature_change or test_actual_jvm_uncaptured_eol_drift or test_overlapping_real_workers_do_not_overwrite_newer_publication'
```

## Krok 5 — použití a zbývající rozsah

[Příklad Python API](../compiler-inspection.md#obnova-izolovaného-jvm-kontextu),
[README](../../README.md#selektivní-dopad-změněných-souborů-t003-s10-w02),
[acceptance](../acceptance-inventory.md#t003-s10-w02--reverse-dependency-indexy)
a [stavová matice](../production-analysis-progress.md) popisují dílčí výsledek.
W02-AC01 zůstává `PARTIAL`. Obnova přes CLI `--manifest`, sdílené rozsahy,
frontend a selektivní přepis dalších druhů důkazů a revizí mají vlastní
ověření. Úplná standardní sada, skutečný běh mimo Linux a GitHub Actions
mají při předání stav `NOT_RUN`.

## Přenos po sloučení #167 a #166 — kroky 3 až 5

První rodič `76a343c6140ebe2feabcd31936b16c3b1b2cde88` nese předchozí
ověřenou JVM publikaci. Druhý rodič je skutečný `main`
`80db9cb63b07ca653c53801406823eb5fb61e339` se stromem
`eb814f7bad157e5166d45909490497a95bbbb298`. Runtime zdroj, Java nástroj,
fixture a testy mají bajty druhého rodiče, stejně jako Excel registry
#167. Společné README, compiler dokumentace a inventáře mají přesné
sloučení obou rodičů. Historie grafu zachovává všech 448 předchozích epizod.
[Change182](182_bindRuntimeInterfaceDispatch.md), [Change183](183_reconcileExcelCompletionInventory.md).

Nezávislý K1 test na prvním rodiči našel dva případy v načitatelném
uloženém grafu s runtime tvarem důkazu. Hrana aktivního kontextu si
ponechala důkaz s vlastníkem v právě vyřazeném kontextu, když pole
vlastníka bylo jednotné `context_id`. Výslovné `context_ids: null` vyvolalo
`TypeError` po úspěšném výpočtu workeru. SHA-256 výsledků reprodukce je
`d86a34d1d177a9bf38a77de998e03789336e563d706625f8f1916badf54e1715` a
`dec72788ed962451fa02ebdebf11ad10f7cba97a84d178de773ab6472e254d91`.

`graph_provider.py` nyní bere v úvahu obě uložené podoby kontextového
vlastníka důkazu i typovaného vlastníka uzlu v metadata. Chybné nebo
rozporné pole vlastníka a důkaz vyřazovaného modulu na nezávislé hraně
zachovají předchozí generaci s `STALE`. Odpovídající nezávislý doklad se
zachová. Kontrola používá skutečný K1 worker, jeho compiler graf a záměrně
sestavené uložené runtime záznamy pro test tvaru a vazby vlastníka. Nativní
runtime import v tomto nebuildovém API rozsahu má samostatné ověření.

Čerstvá cílená sada společného stromu má **21 PASS / 0 SKIP** za 157,07 s
se skutečnými Javacem 21.0.6+7, K1 a K2. Ověřila uvedené tvary vlastníka,
nezávislý doklad také v `callees`, izolovanou publikaci a rollback po
pozdní změně raw zdroje, běžnou pozdní změnu LF→CRLF mimo capture,
tranzitivní callery, souběh skutečných workerů a plánovač. Pytest,
sestavení a porovnání manifestu mají exit 0. SHA-256 JUnit je
`19f9a51930a5552321c2e84739ed1280cfafbc41c77d94c5bfb371cf9b711f82`.
Shodné 576řádkové manifesty mají SHA-256
`a840a0d7e3d373ebf3511658dde5bf1b524d749dac00f5482f6d0b6fcaaeb30b`.

Skutečná kontrola `kgmaker inspect code --manifest` s deklarovaným
manifestem a K1 vrací při zastaralém jiném modulu `STALE`, exit 3,
a zachovává uloženou generaci. Po offline `scan` následná inspekce uspěla.
SHA-256 JSON kontroly je
`befa35952c0e442cdfb228585ae0377bdf2a51c419987e86f070544bb47f4dd4`.
Plán načetl 129 položek, z toho 100 `MERGED` a 29 `PLANNED`.
S10-W02 a S13-W02 mají `MERGED/PARTIAL` a S10-W03 čeká na ověření W02.
SHA-256 výřezu plánu je
`a897e4f4826749e76dba7bca0beda974aecd0ea98e03d601849811f395a5182f`.

```bash
KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 JAVA_TOOL_OPTIONS=-XX:-UsePerfData \
  python -m pytest -n 2 --dist load --maxschedchunk=1 -q --tb=short -ra \
    -p no:cacheprovider -o tmp_path_retention_policy=failed \
    tests/test_reverse_dependency_index.py tests/test_completion.py \
    tests/test_stage_content_cache_actual.py \
    -k 'test_completion or test_actual_jvm_isolated_stale_peer or test_actual_jvm_overlapping_stale_peer or test_actual_javac_signature_change or test_actual_jvm_uncaptured_eol_drift or test_overlapping_real_workers_do_not_overwrite_newer_publication or test_actual_jvm_stale_peer_requires_unambiguous_runtime_proof_owner'
```

Úplná standardní sada společného stromu, skutečný běh mimo Linux a GitHub
Actions mají při lokálním předání stav `NOT_RUN`.

## Přenos po sloučení #168 — kroky 4 a 5

První rodič je `f19934cc63050280c4f5cd02f2363aff3a4fc503` se stromem
`e74a76cfab72092160e68e036f7970b12ce1dea8`. Druhý je skutečný `main`
`4dc8f657b891f1716f7d134f97c1e6098cbb50b5` se stromem
`aac868f1e0a5176b813f5be15a73d7d05f6dda9f`. Oba zdroje a testy W02 mají
bajty prvního rodiče. Soubory Excel implementace, testy a dokumentace
z #168 mají bajty druhého rodiče. Runtime kód a testy #166 i registry #167
jsou shodné v obou rodičích. Společné README, acceptance a stavová matice
odpovídají nezávislému třícestnému sloučení. Graf zachoval 452 předchozích
historických epizod. [Change184](184_preserveScopedExcelBehavior.md).

Všech pět zdrojových otisků předchozí nativní zkoušky `--manifest`
(publikace se `STALE` a následnou obnovou po `scan`) se v tomto stromu
shoduje. Plán má 129 položek, 100 `MERGED` a 29 `PLANNED`. T056-S01 až
S03, S10-W02 a S13-W02 mají `MERGED/PARTIAL`. S10-W03 vyžaduje ověřený
W02. Výřez plánu má SHA-256
`95bcf540303cd798c566d0373f57ff63a01530e2b129363876afd80bc6b14cb1`.

Čerstvá cílená sada má **24 PASS / 0 SKIP** za 125,90 s s JDK 21.0.6+7,
K1 a K2. Pokryla publikaci, rollback pozdní změny raw zdroje, čtyři
nepřípustné tvary nebo vazby vlastníka, zachování nezávislého dokladu,
plánovač a platné i odmítnuté vazby VBA v inventáři T056. Pytest,
sestavení manifestu a jeho porovnání mají exit 0. SHA-256 JUnit je
`c5e7d20fadaf10ae4ed8b7ccf2edec7e682da1d4f8e683cf122cf27adc442289`.
Shodné 579řádkové manifesty mají SHA-256
`35c3aa38c30d7775a4908559025fc0d88a87061f4d443ea91b60a79ef45710a7`.

```bash
KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 JAVA_TOOL_OPTIONS=-XX:-UsePerfData \
  python -m pytest -n 2 --dist load --maxschedchunk=1 -q --tb=short -ra \
    -p no:cacheprovider -o tmp_path_retention_policy=failed \
    tests/test_reverse_dependency_index.py tests/test_completion.py \
    tests/test_excel_migration.py \
    -k 'test_completion or test_actual_jvm_isolated_stale_peer or test_actual_jvm_stale_peer_requires_unambiguous_runtime_proof_owner or test_behavior_sheet_scope_includes_the_guard_and_its_local_definition or test_behavior_rejects_unbound_vba_context_in_loaded_inventory'
```

Úplná standardní sada nového společného stromu, nativní Excel worker,
skutečný běh mimo Linux a GitHub Actions mají při tomto předání stav `NOT_RUN`.
