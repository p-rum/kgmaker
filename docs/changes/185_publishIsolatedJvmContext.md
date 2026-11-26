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
