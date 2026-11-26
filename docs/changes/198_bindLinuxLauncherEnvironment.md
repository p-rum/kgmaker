# Otisk zděděného prostředí linuxového launcheru

26. listopadu 2026. [T003-S10-W01](../tasks/T003-S10-01-stageContentCache.md),
kroky 1–5, W01-AC01, W01-AC03, W01-AC04 a T003-AC10. Výchozí `main`
`044c461dc1c63367a50522261df70a375cccb492`, strom
`b5d1249df20e40ea81ad41561ace96c05636aa77`.

## Krok 1 — výchozí chování

Otisk launcheru na Linuxu před opravou při změně zděděné hodnoty
`LD_LIBRARY_PATH` zůstal shodný. Cílená sada na původních produkčních
bajtech měla **4 FAIL**, **1 PASS**, 68 nezvolených případů a raw exit 1.
Java i Node vytvořily jediný otisk pro nepřítomnou, prázdnou a dvě různé
ne-UTF-8 hodnoty. Stávající ochrana po analýze a při publikaci nevyvolala
`STALE`. Kontrola se simulovanou nelinuxovou platformou prošla.
SHA-256 JUnit `fa9ff441ca10a4f77406fdda93ca74e2ec7d9d9d8193de3646c5d4c45398cce2`.

## Kroky 2 a 3 — otisk a ochrana publikace

`src/kgmaker/extraction_cache.py` zahrnuje původní bajty zděděné hodnoty
`LD_LIBRARY_PATH` na Linuxu do stávajícího `environment_sha256` pro JVM i
TypeScript. Vstupní bajty se kódují stejným postupem jako locale. Chybějící
proměnná a prázdná hodnota mají samostatné otisky. Do grafové generace se
ukládá pouze souhrnný digest prostředí. Kontrola porovnává hodnotu, kterou
launcher dědí, bez zásahu do jeho prostředí a bez čtení uvedených adresářů.

`InspectionStages.guard` porovnává tento otisk po živé analýze a při
stávající atomické publikaci. Neshoda vyvolá `STALE`. Pokud už byla
vyměněna Mermaid vizualizace, uloží se zpět její původní bajty.
Autoritativní graf a jeho revize zůstávají shodné. Formát a starší graph/store
generace zůstávají kompatibilní. Nové linuxové otisky mohou změnit klíč
budoucích replay kandidátů. Živá evidence se nadále počítá při každém běhu a
hlásí `BYPASS`. Kontrola hodnoty jedné proměnné sama neprokazuje úplnost
běhových vstupů ani skutečný výběr knihoven.

## Krok 4 — ověření

Cílený výběr na CPython 3.12.14 skončil **26 PASS / 0 SKIP**, 47 nezvolených
případů a raw exit 0. Testy s inertními hodnotami používají existující
náhradní worker transport a blokují spuštění procesu. Kontrolují oba
launchery, přesné bajty, absenci hodnot v uloženém klíči, časné odmítnutí i
obnovení předchozího výstupu během publikace. Stejný běh pokryl dosavadní
launcher/locale kontroly, chování bez replaye, offline obnovu, odmítnuté nebo
nezapisující režimy a mezikroky atomického zápisu.
SHA-256 JUnit `e661a5e73437d6770b956fef3f6edd62b20c14c4320a745e628bb6fb08968fac`.

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python -m pytest --assert=plain -q \
  -p no:cacheprovider tests/test_stage_content_cache.py \
  -k 'launch or linux_library_search_path or cold_warm_reexecutes or scope_variant_retention or failure_and_read_only or each_precommit_guard_failure'
```

Samostatný Cloud běh s připnutým Temurin JDK 21.0.6+7, Node 24.22.3 a
TypeScriptem 5.7.3 má **4 PASS / 0 SKIP**, 6 nezvolených případů a raw exit 0.
Použil kopii stávajícího testovacího souboru s odkazy na právě kontrolované
Python zdroje a připravenou distribuci workerů. Ověřil dosavadní Javac
rollback při změně locale a skutečný TypeScript s opakovanou inspekcí a
relativním výběrem Node. Žádný nativní worker neběžel s hodnotami z
capture-only testů. Otisky kontrolovaných zdrojů a testu před a po běhu
souhlasí. SHA-256 JUnit `30fa9d35bc82064fe3f01b9a084d6ea175859b6bd79f4b73610ffa152182439c`.

```bash
KGMAKER_REQUIRE_WORKERS=1 JAVA_TOOL_OPTIONS=-XX:-UsePerfData \
  PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python -m pytest --assert=plain -q \
  -p no:cacheprovider tests/test_stage_content_cache_actual.py \
  -k 'actual_jvm_locale_drift or actual_typescript_preflight_and_analysis or actual_typescript_anchors_relative_node_path'
```

## Krok 5 — použití a zbývající ověření

Na Linuxu spusťte například `kgmaker inspect code --root ./service` se
stávajícím prostředím procesu. Při zachycené změně prostředí během běhu
vrátí inspekce `STALE` a čitelná zůstane předchozí generace. Syntaxe obou
CLI příkazů a instalované instrukce zůstávají použitelné beze změny.
[Příklady](../stage-content-cache.md#použití) · [Inspekce](../compiler-inspection.md#obsahová-cache-inspekčních-stupňů-t003-s10-w01)
· [Acceptance](../acceptance-inventory.md#t003-s10-w01--obsahová-cache-explicitních-inspekčních-stupňů)
· [Stavová matice](../production-analysis-progress.md).

Úplná sada na této revizi, hostované CI a nativní kontrola jiného OS mají
stav `NOT_RUN`. W01-AC01 zůstává `PARTIAL`. Ověřený persistentní warm HIT
vyžaduje samostatný důkaz původu a úplnosti běhových vstupů. [#116](https://github.com/p-rum/kgmaker/issues/116)
