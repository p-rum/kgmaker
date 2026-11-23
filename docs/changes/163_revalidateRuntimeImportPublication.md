# Čerstvost runtime evidence při publikaci grafu

T003-S13-W02, kroky 3–5, AC01 a AC03. Nadřazená acceptance T003-AC13.

## Reprodukce na výchozím stromu

Na `0dbe9a754f06cf67f5fe40db0aaa31944497fe19` prošel
načtený manifest v2 první validací. Po následné změně vybraného zdroje
import uložil zastaralou dispatch evidenci. Stejný výsledek měla změna
těsně před zápisem i po nahrazení prvního odvozeného pohledu.

`test_real_jdk21_runtime_import_rejects_source_edit_after_validation`
kompiluje instrumentovaný Java fixture a zachytí manifest skutečným
JDK 21. Do manifestu přidá typovanou dispatch observation s identifikátory
z fixture. Test pokryje editaci před voláním store a editaci po skutečném
nahrazení Mermaid výstupu. Po opravě očekává `STALE_RUNTIME: source changed`,
stejné bajty v uloženém grafu, Mermaid, Markdown a v capture artefaktu,
úklid dočasných souborů a nulové spuštění procesů během importu.
[JDK 21 test](../../tests/test_runtime_trace_producer.py)

## Oprava

`runtime import` používá stávající validaci manifestu při vstupu
a prostřednictvím `save_graph(before_replace=…)` také při publikaci.
Obě verze manifestu znovu kontrolují zdrojové hashe a distribuci workeru.
Import v2 ověřuje i vazbu načteného capture na compiler kontext a
čerstvost zachycených vstupů. Store ověřuje očekávanou generaci pod
zámkem, při chybě obnoví již nahrazené soubory a zachová dříve publikovaný
graf. Import pracuje s manifestem načteným do paměti. Schémata zůstávají
v1 a v2 pro manifest a v3 pro graf.
[Import a validace](../../src/kgmaker/runtime_evidence.py) · [Publikace](../../src/kgmaker/store.py)

Příklad `kgmaker runtime import --root PROJECT --manifest PROJECT/.kgmaker/runtime/trace.json`
využije poslední platný graf. Když import během publikace zjistí změnu
zachyceného zdroje, skončí s kódem 3 a v grafu zůstane předchozí
generace. Pokryta je publikační část AC01 a AC03. Receiver/type
dispatch a celková acceptance T003-S13-W02 zůstávají otevřené.
[Příklad příkazu](../runtime-trace.md#spuštění) · [README](../../README.md) · [Compiler kontext](../compiler-inspection.md) · [Zadání](../tasks/T003-S13-02-runtimeRtaImport.md) · [Acceptance](../acceptance-inventory.md) · [Stav](../production-analysis-progress.md)

## Lokální ověření

Pro výběr s reálným workerem používalo prostředí `PYTHONPATH=src`,
`JAVA_HOME` s Temurin JDK 21.0.6+7, distribuované workery z
`KGMAKER_WORKERS_HOME`, `KGMAKER_REQUIRE_WORKERS=1`,
`KGMAKER_REQUIRE_K2=1` a `JAVA_TOOL_OPTIONS=-XX:-UsePerfData`.

- **Výchozí produktový kód.** `python -m pytest -p no:cacheprovider -q --tb=short tests/test_runtime_trace_producer.py -k runtime_import_rejects_source_edit_after_validation`
  se dvěma novými případy skončil kódem 1. Oba případy selhaly očekávaným
  `DID NOT RAISE`, 71 testů bylo mimo výběr. JUnit SHA-256
  `fb87a53850be9ae2dc609b6850a5c710d160deb46a35fc52694160b17f97a380`.
- **Opravený produktový kód, Python 3.12.14.**
  `python -m pytest -p no:cacheprovider -q --tb=short tests/test_runtime_trace_producer.py tests/test_build_aware.py tests/test_graph_provider.py tests/test_t032_persist_process_review.py tests/test_graph_publication_concurrency.py`
  skončil kódem 0, 150 PASS a 0 SKIP. JUnit SHA-256
  `307af009e9d7014ae162e0929ea37767ce6ddb9ca5410e990751ca0d36721b91`.
  SHA-256 vstupního i výstupního manifestu sledovaného kódu, testů
  a nástrojů je `9711e74939f6fe9f931b8c78865f48e2286ce8ec86fd866c204c307c3c04ef9f`.
- **Aktuální capture, JDK 21.** Lokální doplňkový výběr
  `PYTHONPATH=src:tests python -m pytest -p no:cacheprovider -q --tb=short runtime-publication-main-current-test.py`
  ověřil 1 PASS a 0 SKIP. Do grafu přibyla jedna dispatch observation
  se shodným kontextem. Předchozí hrany i bajty capture zůstaly zachovány.
  SHA-256 lokálního testu je
  `585ee8c2b15b3e44e7dc3b65e2f1bbe6130f0db439f5d53afd943b7b691f73ec`
  a SHA-256 JUnit je `74abfe2e83a781d7ce6dc44df39afd0f0076f4fa70616e705bbbdd6df1dc3157`.
- **Úplná standardní sada, Python 3.13.18.**
  `PYTHONPATH=src python -m pytest -p no:cacheprovider -q --tb=short`
  skončil kódem 0. Výsledek je 2 466 PASS, 1 296 SKIP a jeden
  očekávaný strict XFAIL `test_comment_does_not_change_logical_identity`
  pro T047-S02. Oba nové případy se bez explicitního JDK 21 přeskočily
  a prošly v běhu s reálným workerem výše. JUnit SHA-256
  `79f970ea174fda4ec52758780193729f7a861be8653a5ffeda535ff9c6aae06e`.
  Sledované vstupy mají před a po běhu stejný SHA-256 jako výběr s JDK 21.
- **Příprava testgen.**
  `kgmaker testgen prepare --id runtime-publication-main --target src/kgmaker/runtime_evidence.py --scope production --framework pytest --token-budget 100000`
  skončil kódem 2 `Token budget cannot hold target evidence`.
  Regrese používá stávající fixture a ověřený compiler context.

GitHub Actions, Windows a úplné scénáře receiver/type dispatch jsou
`NOT_RUN`. Dalším krokem W02 je ověření zbývajícího kontraktu
ve [specifikaci](../tasks/T003-S13-02-runtimeRtaImport.md).
