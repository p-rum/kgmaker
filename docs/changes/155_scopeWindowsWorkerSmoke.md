# Rozsah Windows smoke testu podle připravených workerů

T003-S11-W03, kroky 4–5, AC01 a AC04. Výchozí `main`
`4011825b15e4b65e1f57576a0986ca05b3cf810e`. Původní W03 zůstává MERGED.
Opravený výběr je IN_PROGRESS, ověření Windows pro tuto revizi je NOT_RUN.

## Krok 4 / AC01 — přesný výběr deklarované matice

Skutečný Windows job `136921503216` běžel na
`1705305922c48551fd780139fd3cf8414920b2db` a potvrdil neadministrátorský
restricted token. Testy pak vykázaly 44 PASS / 1 SKIP / 1 FAIL. K2 test
zastavil host preflight `require_jvm("k2")` na nepřipravené cestě
`workers/jvm/target-k2`, takže test K2 z instalovaného wheelu nepokračoval.
Skript připravoval K1 a spouštěl celý modul s `KGMAKER_REQUIRE_WORKERS=1`.
[Běh 44929074862](https://github.com/p-rum/kgmaker/actions/runs/44929074862/job/136921503216)

`tests/windows/no_admin_smoke.ps1` předává pytestu právě jeden přesný
`--deselect` pro K2 wheel test. Průchod pro core, Java, K1 Kotlin a TypeScript
používá původní worker flag, kontrolu restricted tokenu, ověření wheelu
mimo checkout a ověření cest s mezerami. Povinný K2 běh zůstává v Linux jobu
`compiler-workers` s vlastní připravenou distribucí. Formát wheelu, seznam
balených souborů, sestavení workerů a ostatní workflow kroky zůstávají beze změny.

## Krok 5 / AC04 — evidence a ověření

[Příručka Windows](../windows-install.md), [README](../../README.md),
[stavová matice](../production-analysis-progress.md) a
[acceptance](../acceptance-inventory.md) uvádějí historický rozsah a stav
nového běhu. Instalace, příkazy CLI, task registry a distribuované instrukce
mají stejný kontrakt. Historický rozsah původního W03 dokládá
[Change40](40_supportWindowsUserInstall.md).

- RED — s `KGMAKER_REQUIRE_WORKERS=1` a bez `workers/jvm/target-k2` dal
  `PYTHONPATH=src python -m pytest -p no:cacheprovider -q --tb=short tests/test_worker_install.py::InstalledWorkerTests::test_packaged_k2_analyzes_outside_checkout`
  1 FAIL za 17,63 s na kontrole dostupnosti hostitelského K2.
- PASS — `--collect-only` se stejným výběrem jako níže vybral 45 z 46
  případů a vyřadil jediný K2 test.
- PASS — příkaz níže v Cloud Environment na Linuxu vykázal **44 PASS /
  1 SKIP / 1 DESELECTED** za 38,85 s. Použil skutečný JDK 21.0.6/K1 a
  Node 24.22.3/TypeScript 5.7.3 s `KGMAKER_REQUIRE_WORKERS=1`.
  SKIP je test skutečného neadministrátorského Windows. DESELECTED je K2.
- PASS — checksumově ověřený PowerShell 7.4.13 na Linuxu prošel kontrolou
  `System.Management.Automation.Language.Parser.ParseFile` nad změněným
  skriptem bez syntax errors. AST obsahuje jediný přesný `--deselect`.
- JUnit SHA-256 RED
  `f6ebe58a7e473c3493301ad86fec4e2a94a92199adf6f35f502bb8cefadbaabb`.
  JUnit SHA-256 lokálního výběru
  `4d12972d8a12e8a8ccca06759d364d5125051bbe6d814b78da2459bfdb074660`.
- NOT_RUN — skutečný Windows restricted-token běh opravené revize,
  Windows K2 a úplná sada. Windows BUILD_EXECUTE zůstává mimo W03.

```bash
KGMAKER_REQUIRE_WORKERS=1 PYTHONPATH=src python -m pytest -p no:cacheprovider \
  -q --tb=short -ra \
  '--deselect=tests/test_worker_install.py::InstalledWorkerTests::test_packaged_k2_analyzes_outside_checkout' \
  tests/test_worker_protocol.py tests/test_worker_install.py \
  tests/test_windows_install.py tests/test_t005_add_view_model.py
```
