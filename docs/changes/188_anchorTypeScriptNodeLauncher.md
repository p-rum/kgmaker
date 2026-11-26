# Relativní cesta k Node při inspekci TypeScriptu

[T003-S10-W01](../tasks/T003-S10-01-stageContentCache.md), kroky 1–5,
AC03–AC04, T003-AC10 a [#116](https://github.com/p-rum/kgmaker/issues/116).
Výchozí `main` je `18ce70a077f603f1800036dc97c38553f91a506a`.

## Krok 1 — reprodukce

`inspect frontend` vybral `tools/node` podle `PATH` v pracovním
adresáři KGMAKERu. Worker se spouštěl v adresáři analyzovaného projektu,
kde tato relativní cesta neexistovala. Před opravou skutečný Node spustil
TypeScript worker při absolutní položce `PATH`. Po změně zdroje skončil
další příkaz s relativní položkou kódem 3 a stavem `TOOLCHAIN_UNAVAILABLE`.
Uložený graf JSON a oba odvozené pohledy měly stejné bajty jako před pokusem.

## Kroky 2 a 3 — cesta ke spuštění a k otisku

`src/kgmaker/inspection.py` převádí vybranou cestu k Node na absolutní cestu
stejně jako u Javy. Vyhledávání respektuje pořadí `PATH`. Absolutní cesta
zachová vybraný symbolický odkaz a worker dál běží v adresáři projektu.
Stejnou cestu používá stávající otisk launcheru. Workery, protokol,
formáty grafu v1–v3 a cache envelope v1 používají dosavadní rozhraní.

## Krok 4 — ověření

Regrese `test_actual_typescript_anchors_relative_node_path_before_worker_cwd`
spouští veřejné CLI ze samostatného adresáře a ověřuje skutečný Node a
TypeScript worker. Kontrola používá Node 24.22.3 a TypeScript 5.7.3 na Linuxu
s CPython 3.12.14.

```bash
KGMAKER_REQUIRE_WORKERS=1 python -m pytest -q -p no:cacheprovider \
  tests/test_stage_content_cache_actual.py -k anchors_relative_node_path_before_worker_cwd
```

Na výchozím kódu skončila kontrola očekávaným **FAIL**, exit 1 za 6,37 s.
JUnit SHA-256 `0b12e119fcbc5ae6459f460c912245ba649d600779af334e9ad30323476ee7e5`.

Po opravě publikovaly absolutní i relativní volby Node jeden skutečně
rozlišený call site. Relativní volba publikovala kontext změněného zdroje,
uložený klíč obsahoval požadovaný symbolický odkaz a fáze hlásily
`BYPASS/UNVERIFIED_REPLAY`. Spolu s dosavadními kontrolami launcheru Java,
Javacu, K1, K2, TypeScriptu, kandidátů evidence a ochrany při přerušení
prošlo **18 PASS / 0 SKIP**, exit 0 za 87,27 s. JUnit SHA-256
`aab3d232aef0171ec3efd487bd073899a213726b23c26faf81eb08aa7c5c56ef`.
Manifest sledovaných vstupů zdrojů a workerů má před a po testu stejný
SHA-256 `93c044bf2b097584e590ed4508abd7df0bdc8a19cd457f1e8f118a849c12d614`.

```bash
KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 JAVA_TOOL_OPTIONS=-XX:-UsePerfData \
  python -m pytest -n 2 --dist load -q -p no:cacheprovider \
  -o tmp_path_retention_policy=failed tests/test_stage_content_cache.py \
  tests/test_stage_content_cache_actual.py \
  -k 'anchors_relative_node_path or relative_java_path or public_inspect_cold_warm or rehashed_cached_graph or hash_rewritten_foreign or actual_jvm_cold_warm or actual_typescript_preflight or warm_inspection_honors_abort or actual_jvm_cyclic_launcher'
```

## Krok 5 — příklad a stav

Spusťte příkaz z adresáře s připraveným `./tools/node` a se sestaveným
TypeScript workerem.

```bash
PATH="./tools:$PATH" kgmaker inspect frontend --root ./ui --tsconfig tsconfig.json
```

[README](../../README.md#obsahová-cache-explicitní-inspekce-t003-s10-w01),
[inspekce](../compiler-inspection.md#obsahová-cache-inspekčních-stupňů-t003-s10-w01),
[kontrakt cache](../stage-content-cache.md), [inventář](../acceptance-inventory.md#t003-s10-w01--obsahová-cache-explicitních-inspekčních-stupňů)
a [stav](../production-analysis-progress.md) popisují stejný rozsah.
Identita zadání a jeho závislosti zůstávají v existujícím registru.
Úplná standardní sada, skutečná inspekce na Windows a GitHub Actions mají
v tomto implementačním předání stav `NOT_RUN`.
T003-S10-W01 zůstává `PARTIAL`. Ověřený persistentní `HIT` závisí na
úplném otisku běhových vstupů a nezávisle ověřitelném dokladu o původu
výsledku. Živá inspekce v ověřeném scénáři hlásí `BYPASS/UNVERIFIED_REPLAY`.
