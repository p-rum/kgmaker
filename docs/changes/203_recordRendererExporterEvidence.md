# Záznam sloučení Mermaid rendereru a důkazů build exporterů

Datum 2026-11-27. Výchozí `main` `e7b2f36ef764c16c566db20ec06cee82e47c84ba`,
strom `6e3fa28752b43512a862c8548df533a838cb4c8d`.
[T048-S01 / T048-AC01](../tasks/48_completeImplementationHandoff.md#3-první-krok-t048-s01--sjednotit-stav-a-vytvořit-pracovní-seznam)
· [Stav dodání](../production-analysis-progress.md).

## Krok 1 — sloučený technický Mermaid diagram T035

[PR #183](https://github.com/p-rum/kgmaker/pull/183) byl 2026-11-27 v 01:45:01 UTC
sloučen do `main` jako `e7b2f36ef764c16c566db20ec06cee82e47c84ba`.
Rodiče jsou v pořadí `1841553b2f2923f9342a1674cacc1ea36b8e9092` a
`0674336c2ffa5a94c5d6a42dda868db077f41f03`. Strom
`6e3fa28752b43512a862c8548df533a838cb4c8d` je shodný se schváleným headem.
SHA-256 dokladu T045 o sloučení
`634e7b1d2feb153bec22ad686a794eda9565bc692a6d688939829076c55e98c7`.
[Nezávislé APPROVE T045](https://github.com/p-rum/kgmaker/pull/183#issuecomment-7207543035).

- Na skutečném merge `e7b2f36` prošel přímý běh s připnutými Mermaid 11.4.1,
  jsdom 26.0.0 a Javacem 21.0.6. Výsledek je **124 PASS / 0 SKIP**, raw exit 0.
  Před a po se shodují otisky 948 sledovaných souborů, připnutého JVM worker
  JARu, npm locku a metadat balíčků Mermaid a jsdom. SHA-256 JUnit
  `1a4637dba4b69168d5a3e67cd7ed9659cfa1a385fa3963c9ad2870abf0c0b006`.
- Nezávislé T045 na schváleném headu `0674336` nad `1841553` mělo
  **14 PASS / 0 SKIP**, raw exit 0. SHA-256 JUnit
  `5b6d00bef57c92b08904e0d0614af605641c615b168effd44214998afb7aa0e4`.
- Předschvalovací běh na stejném headu měl **124 PASS / 0 SKIP**,
  raw exit 0. Standardní sada na této dvojici měla **2 682 PASS /
  1 405 SKIP / 1 očekávaný XFAIL**, raw exit 0. SHA-256 JUnit
  `5e8a0d1e3c4b39dafbbbcd058f20485d98260fb138dde707d4297f8e5a5dbb4a`
  a `f05977510f4b6f82b55ac71a16bf2af9fa45c389e070ce99ef7c931fe454dff8`.
  Starší dvojice revizí a jejich výsledky jsou v [Change199](199_renderSuppliedProcessMermaid.md).

Kanonický řádek T035 přechází z PR_OPEN na MERGED a nese ověření PARTIAL.
Čistá funkce `kgmaker.process_render.render_process_mermaid(view)` vykresluje
dodaný typovaný `ProcessView` schématu 1. Zachovává stabilní ID, všechny
orientované výskyty hran, explicitní lane vlastníky a technický původ.
T035-AC02 pro schválené popisky má stav NOT_RUN. `kgmaker process render`
poskytuje čtecí JSON podle T034. Širší CLI, vysvětlení a export mají vlastní
rozsah. [Použití a hranice](../process-paths.md#mermaid-for-a-supplied-processview-t035)
· [T035-AC01–AC06](../acceptance-inventory.md#t035--mermaid-nad-dodaným-typovaným-processview).

## Krok 2 — důkazy distribuce Maven a Gradle exporterů S11-W02

Původní #22 je v `main` jako `e656b8ef4c174d3d60600037d7c0d78fc514e39d`,
strom `6e8d5892be858c5cf143042a7b280516743fe092`. Rodiče jsou v pořadí
`35033096e8a2ea5d74ae8d2195a7b27d22c7590a` a
`2a23deb78dac228f5d7d3de8791a8bb8bd83003d`. W02 zůstává MERGED / PARTIAL.
Řádek T003-S11-W02-AC01 uvádí konkrétní běhy v doloženém Linux rozsahu.
[PR #22](https://github.com/p-rum/kgmaker/pull/22) · [Change37](37_packageBuildExporters.md)
· [T003-S11-W02-AC01](../acceptance-inventory.md#t003-s11-w02--distribuce-build-exporterů).

- Na `adca1031dede08e294c3fd1234150d27ee6379a6` po #182 a
  `1841553b2f2923f9342a1674cacc1ea36b8e9092` po #184 uspěly kroky 7–9
  vyhrazeného Linux jobu. Zahrnuly explicitní přípravu Maven exporteru, obě
  povinné varianty skutečného buildu z instalovaného wheelu mimo checkout
  a explicitní Gradle source-set export. Job používá CPython 3.12, Temurin
  21.0.6, Maven 3.9.9 a Gradle 8.12.1.
  [Job po #182](https://github.com/p-rum/kgmaker/actions/runs/45916224478/job/140235979755)
  · [job po #184](https://github.com/p-rum/kgmaker/actions/runs/45920787123/job/140250770614).
- Přímý `test_installed_exporters_run_real_builds_outside_checkout[maven]`
  na `fd8d5e958bf45b67775c04f78e817cc7d41ebfe9` měl **1 PASS / 0 SKIP**,
  raw exit 0. Linux x86_64, CPython 3.13.18, Temurin 21.0.6+7 a offline
  Maven 3.9.9. SHA-256 JUnit
  `f22d89ccfee3ae37f6d51e2940e24624d3eee5438e8987d8f7b9dcf9fff8eefc`
  a dokladu `cc2128c8e298f58fce0be6016ced2d12b9e5301e8388c1fdad54ecd00ebbd9eb`.
  Před a po ověření připravené sady byly shodné otisky. Po obnovení descriptoru
  se shodlo všech 940 sledovaných vstupů a 1 993 položek Maven cache.
  [Samostatný hostovaný Maven/Gradle job na stejné revizi](https://github.com/p-rum/kgmaker/actions/runs/45906574338/job/140204631271).

Stávající `kgmaker project build-plan` a následný explicitní
`kgmaker project build-run` používají tutéž distribuční ochranu. Windows
`BUILD_EXECUTE` vrací `UNSUPPORTED_PLATFORM`. K2 na Windows, neměnná
publikace release artefaktů a úplná acceptance a benchmark matice mají
vlastní scope. T003-S11 a T003-AC11 zůstávají PARTIAL.
[Příklad sestavení a použití](37_packageBuildExporters.md#použití-a-zbývající-práce)
· [Omezení Windows](../windows-install.md).

## Kontrola záznamu a navazující práce

Změna používá současný registr, schémata, veřejné návody a CLI. Čtecí zkouška
s přesnou kopií `e7b2f36` ověřila použití patche pouze na řádcích dodání
T035 a T003-S11-W02 a na důkazu W02-AC01. Historické Change199 a Change37
zůstaly přesně dohledatelné. `git apply --check` i aplikace ve zkušební kopii
mají raw exit 0. Úplná sada pro tento dokumentační krok má stav NOT_RUN.

Při přípravě byl spuštěn skutečný plánovač s navrženou maticí pouze v paměti.
Příkaz `kgmaker completion plan --root "$PWD" --jobs 32` pak nad pracovní
maticí vrátil shodný výsledek. Plán má 135 položek, z toho 110 MERGED,
24 PLANNED a jednu IN_PROGRESS. SHA-256 plánu
`2bb4d5bfae1773d55ad5bce59654ab03334b4a3bfdb6e5157161182a16a0cf94`.
V delegaci o 32 položkách T036 nahradilo T035 a T035 má akci `verify`.
T042 nadále čeká na T036, T038 a T040. Přísný požadavek
S10-W03 na `VERIFIED_IN_SCOPE` pro S10-W02 dál platí.

Přípravná cílená kontrola `python -m pytest --assert=plain -q -p no:cacheprovider tests/test_completion.py`
nad pracovním stavem matice má **13 PASS / 0 SKIP**, raw exit 0. SHA-256 JUnit
`f62b281a68f3b9263aa10f27917a82a4b44192640cfd9fcc1fc6824985708707`.
