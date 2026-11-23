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

`runtime import` ověří načtený manifest při vstupu. Prostřednictvím
`save_graph(before_replace=…)` znovu kontroluje zdrojové hashe a
distribuci workeru u obou verzí manifestu. U v2 kontroluje i čerstvost
zachycených vstupů vybraného compiler kontextu včetně bytecode.
Store ověřuje očekávanou generaci pod
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

## Lokální ověření první revize

Výsledky po prvním kroku patří ke stromu
`7a722c2d490d7d136dbe767c4e3eff40b2e7d1a5`, commit
`193614a5ae0d65bc7d22572ece44b9c593408440`.

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

## Jedna validace manifestu při publikaci

Revize `193614a5ae0d65bc7d22572ece44b9c593408440` kromě čerstvosti
zdrojů čtyřikrát opakovala i validaci obálky, facts a observations
pod publikačním zámkem. Nezávislé steelman review u 8 500 platných
pozorování naměřilo 29,399 s ve čtyřech opakovaných validacích.

`runtime_evidence.py` provede plnou validaci před vstupem do store.
Ve stávajících publikačních kontrolách načítá jen soubory zdrojů
a distribuce workeru, u v2 ověří i zachycené vstupy compiler kontextu.
Kontrola očekávané generace a obnova výstupů probíhají ve stejném store.
Test počítá volání celé validace, validaci facts a průchody observations.
Zaznamenává stav zámku a nahrazené výstupy při každé kontrole zdrojů,
workeru a snapshotu v2. Další CLI testy mění skutečný JDK 21 bytecode
nebo testovací worker v1 po nahrazení obou odvozených výstupů. Ověří
odmítnutí s kódem 3, obnovu obou výstupů, stejné bajty grafu a capture
a nulové spuštění procesů.
[Kód](../../src/kgmaker/runtime_evidence.py) · [Testy](../../tests/test_runtime_trace_producer.py)

- **Před opravou.**
  `python -m pytest -p no:cacheprovider -q --tb=short tests/test_runtime_trace_producer.py::test_runtime_import_validates_payload_once_and_rechecks_inputs_per_publication_step`
  skončil kódem 1. Test naměřil `(5, 5, 6)`, očekává `(1, 1, 2)`.
  JUnit SHA-256 `115b2b7383dcf34390512ca9d6f7cfaba8ffc4ef3e7045644f18ca6e66546f7e`.
- **První návrh revize.** V obou sadách selhal test generačního
  konfliktu W06. Kontrola verze proběhla před kontrolou generace a
  testovací náhrada validátoru neposkytovala verzi manifestu.
  Výběr v2 při opakované kontrole se nyní provádí v callbacku
  po store CAS. Samostatně znovu prošel test generačního konfliktu
  i nový test počtů volání. JUnit SHA-256 prvního návrhu s JDK 21 je
  `60f5b191d9aef9fec474c201e981ae63c6c21e7c8e07b48056f466289f21ddc3`.
  JUnit standardní sady prvního návrhu má SHA-256
  `82c2557461270ae6e32337480622593885011e184dc11beb2812e5c4011f303d`.
- **Opravená revize s reálným JDK 21.0.6+7.**
  `PYTHONPATH=src:tests python -m pytest -p no:cacheprovider -q --tb=short tests/test_runtime_trace_producer.py tests/test_build_aware.py tests/test_graph_provider.py tests/test_t032_persist_process_review.py tests/test_graph_publication_concurrency.py runtime-publication-main-current-test.py`
  skončil kódem 0, 154 PASS a 0 SKIP. Poslední soubor je výše popsaný
  lokální test platného capture se stejným SHA-256.
  JUnit SHA-256 `8762be7c4d8555a9e00ba15155399126b90107f2a102b5da77b587b53d9a1798`.
  SHA-256 manifestu sledovaného kódu, testů a nástrojů před i po běhu
  je `cfd724210cdde8330c36413c2d06503841ac7d3a00f776d3302c195399120a76`.
- **Úplná standardní sada opravené revize, Python 3.13.18.**
  `PYTHONPATH=src python -m pytest -p no:cacheprovider -q --tb=short`
  skončil kódem 0, 2 468 PASS, 1 297 SKIP a jeden očekávaný strict XFAIL
  T047-S02. Případy se skutečným JDK 21 ověřil výběr výše.
  JUnit SHA-256 `20087500259acc8f0293ffe290a2c1c33548f2d79b47ccff606833819eeeeb75`.
  Manifest sledovaných vstupů má stejný SHA-256 jako výběr s JDK 21.
- **Měření a kompatibilita.** Lokální `PYTHONPATH=src python probe.py perf --count 8500`
  na opravené revizi změřil 9,507 s celkem. Zaznamenal jednu plnou
  validaci před zámkem. `python probe.py compat` ověřil čtyři kombinace
  v1/v2 s předchozími odvozenými pohledy i bez nich. V každé zastaralý
  worker odmítl publikaci a po obnově workeru prošel platný import.
  SHA-256 původní sondy review je
  `f58a18f76ff67872108d75cad38dd27d76f85efa1f785cfeaef5db36a7f33785`,
  měření `c0be62bb0cd2d539ed10fe6d8b78729ba4c8ee071b721b3d38fe02d16c54de68`
  a kontroly kompatibility `a6801622c54c6614c5917592521defbca837db6b1869f428fcf4804d35e8eb2d`.
- **Testgen na archivu `193614a`.**
  `kgmaker testgen prepare --id runtime-publication-retry1 --target src/kgmaker/runtime_evidence.py --scope production --framework pytest --token-budget 100000`
  vrátil kód 2 `Token budget cannot hold target evidence`.
  Cílené testy používají existující fixture a skutečné výsledky běhů výše.

GitHub Actions a Windows mají v této revizi stav `NOT_RUN`.
Zbývající receiver/type kontrakt W02 zůstává otevřený.
