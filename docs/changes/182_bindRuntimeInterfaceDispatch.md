# Vazba pozorovaného Java příjemce na místo volání

[T003-S13-W02](../tasks/T003-S13-02-runtimeRtaImport.md), výchozí `main`
`5ff2c0846056353605ccb9ab271bd86847c6e661`, tree `aa395d1ebe8dcf55b4173a520a6f4e43e26780ab`.

## Krok 1 — zjištění mezery v evidence

T003-S13-W02-AC01 a AC03. Schéma v2 zná označené konce volání. Skutečný běh
Alpha a Beta přes `invoke(Service)` doložil různé příjemce a cíle s přiřazením
k jediné compiler instrukci pro každou vybranou variantu. Současná validace
odmítla přesný typovaný fact. Samostatná fixture s JDK 21.0.6+7, Javacem a JVM
workerem skončila očekávaným kódem 1 se 2 FAIL a 6 PASS bez přeskočení.
JUnit SHA-256 `cc6661f850c84d42c11dd2ed002eafc029f7ce3212025509deb3f99270d5cb46`.

## Krok 2 — protokol a ověření compiler kontextu

T003-S13-W02-AC01 a AC02. `RuntimeTrace.observeInterfaceDispatch(this)` zachytí
typ instance, JVM signatury aktuální metody a volajícího frame a jeho řádek.
Stávající opt-in `runtime produce` použije RuntimeManifest v3 pouze při
`interface_dispatch`. Volné vstupy, argumenty a hodnoty se nezaznamenávají.
Offline validace použije jedinou fyzickou instrukci na zaznamenaném řádku
jako `INTERFACE` call site, ověří vykonanou Java metodu a skutečného příjemce
proti zdrojům, kandidátům a bytecode vybraného kontextu. `observations` ve
v3 exportu je prázdné. Import odvozuje pozorování znovu. V1 a v2 přijímají své
dosavadní mapy pozorování a graph/store zůstává ve schématu v3.
[Producer a import](../../src/kgmaker/runtime_evidence.py) · [SDK](../../tooling/runtime/java/org/kgmaker/runtime/RuntimeTrace.java).

## Krok 3 — publikace a čtení důkazů

T003-S13-W02-AC01 a AC03. Import přidá `call_site` a `receiver_type` do
stávajícího dokladu `RUNTIME_OBSERVED`. `callers` a `callees` poskytují tyto
údaje pro v3. Statické analýzy provádějí původní průchod a v grafu zůstávají
všichni statičtí kandidáti. Stejná generační kontrola a opakovaná validace
vybraných vstupů chrání publikaci. Změna bytecode mezi výstupy vrátí původní
bajty grafu a odvozených výstupů. [Navigace](../../src/kgmaker/callgraph.py).

## Krok 4 — lokální ověření

T003-S13-W02-AC01–AC04. Při použití Temurin JDK 21.0.6+7 a připraveného
JVM workeru proběhl cílený výběr s výsledkem 123 PASS, 0 FAIL, 0 SKIP,
2 položky mimo výběr, raw exit 0 a 116,67 s. Shodné manifesty kódu, testu,
SDK a fixture před a po mají SHA-256
`bb8cb0ce2c5c13d8810c925a75442af4d707867ad12dae46d45f4f7fafde70df`.
JUnit SHA-256 `62a8128fa25341f90158bd28af8347c262a667c1aebdc84a277c273a75e98661`.

```sh
export JAVA_HOME=/workspace/kgmaker-tools/jdk-21.0.6+7
export PATH="$JAVA_HOME/bin:$PATH"
export KGMAKER_WORKERS_HOME=/workspace/kgmaker-tools/worker-dist KGMAKER_REQUIRE_WORKERS=1
export PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 JAVA_TOOL_OPTIONS=-XX:-UsePerfData
python -m pytest -q -p no:cacheprovider --tb=short \
  tests/test_runtime_trace_producer.py tests/test_graph_publication_concurrency.py \
  tests/test_build_aware.py tests/test_availability.py -k 'not maven'
```

Testy provedly skutečné spuštění obou variant přes veřejné CLI, offline import
bez spuštění procesu, odmítnutí dvou typů kolize instrukcí na řádku, pozměněného
typu, cíle či řádku, neodpovídající konfigurace, v3 vstupu vydávaného za v2 a
změny zdroje nebo bytecode. [Fixture](../../tests/fixtures/runtime-trace/DispatchApplication.java)
· [Regrese](../../tests/test_runtime_trace_producer.py).

Samostatný skutečný Maven 3.9.9 a JDK 21.0.6+7 ověřil původní veřejnou cestu
s konfigurací vybranou z BuildManifestu. Test
`tests/test_runtime_trace_producer.py::test_actual_maven_public_runtime_uses_selected_build_configuration`
prošel offline za 28,34 s s 1 PASS, 0 SKIP a raw exit 0. Použil stejné prostředí
a launcher Maven se stávajícím lokálním repozitářem na `PATH`. Pro samotný
test byl použitý stejný příkaz pytest bez filtru `-k`. JUnit SHA-256
`3db953c3103ce95345adb4f2b4da6d68d32edd27e80e55fefd2019f4a14a2bc3`.

Úplná sada pro kandidátní strom, Windows a GitHub Actions mají v tomto záznamu
stav `NOT_RUN`. Cílená nativní sada je doklad podporovaného rozsahu.

## Krok 5 — použití a hranice

T003-S13-W02-AC04. Příklad opt-in instrumentace je v
[runtime návodu](../runtime-trace.md#synchronní-dispatch-java-rozhraní),
výstup uvádí [dokumentace compileru](../compiler-inspection.md#pozorované-hrany-a-statické-cesty)
a [README](../../README.md). Rozsah testů uvádí [acceptance inventář](../acceptance-inventory.md)
a [stavová matice](../production-analysis-progress.md). Evidovaný typ je přímá
implementace z aktuálně vybraných Java zdrojů se synchronním call stackem.
Děděné a výchozí implementace, proxy, reflexe, asynchronní běh, hodnotové toky
a nasazení mají vlastní kontrakty. Celý W02 a T003-AC13 zůstávají `PARTIAL`.

## Přenos po sloučení #164

T003-S13-W02-AC01–AC04. Nový základ je
`49bab32c50436782a2009455a36ada41c06be42f`, tree
`117ad84524a9c18ef1832471e3651f8bb41094b6`. Přenos zachoval implementaci a
testy W02 i změněný otisk nativních knihoven JDK z
[Change180](180_bindLinuxJdkNativeInputs.md). Se stejným JDK a povinným
compiler workerem prošlo 30 testů za 149,95 s bez chyb nebo přeskočení,
95 položek bylo mimo výběr. Znovu běžely obě skutečné Java varianty, importní
guardy, souběžní zapisovači i legacy CLI se skutečným offline Mavenem 3.9.9.
JUnit SHA-256 `b27e4cd96eaa8ad9ddb5dd4d7d549e310d953a286537ffcaa70415c3cf8b793f`.
Otisk vstupů před a po včetně `extraction_cache.py` je
`a3dbf76e869575f8119f13357aa481e446159aa25dc4ace27d2146f95b74de78`.

```sh
python -m pytest -q -p no:cacheprovider --tb=short \
  tests/test_runtime_trace_producer.py tests/test_graph_publication_concurrency.py \
  tests/test_build_aware.py tests/test_availability.py \
  -k 'interface_dispatch or runtime_import_validates_payload_once or runtime_keeps_callable or runtime_observation_stays_visible or runtime_import_is_bound_to_context or actual_maven_public_runtime or concurrency'
```
