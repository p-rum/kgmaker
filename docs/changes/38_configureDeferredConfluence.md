# Konfigurovatelná příprava odloženého Confluence připojení

## Problém a skutečná změna

Zadání [T003-S12-W01](../tasks/T003-S12-01-liveConfluenceConnector.md) čekalo
na konkrétní host/API/auth kontrakt. Uživatel 2026-10-26 výslovně odložil živý
běh a požádal o konfigurovatelné parametry. Revize 2 tuto změnu rozsahu zachovává
odděleně od skutečného live integračního důkazu.

`confluence_sync_config.py` čte JSON subsection `documentation.confluence.connection`:
host, explicitní API `cloud-v1`/`cloud-v2`/`server-v1`, sandbox prostor, enabled
a pouze jména proměnných prostředí pro bearer nebo basic autentizaci. Nečte
žádné připojené secret soubory ani neposílá hodnoty autentizace do výstupu.
`kgmaker confluence config --root . [--config-file settings.json]` vrací
deterministický stav a vždy `live_status: NOT_RUN`, bez síťového volání, procesu
nebo zápisu. Neplatné, duplicitní nebo nadměrné vstupy selžou bez mutace.

První explicitní connection subsection v `.kgmaker/config.json`, potom
`kgmaker.json`, má přednost; nesouvisející konfigurace nezakryje druhý soubor.
Disabled connection je autoritativní. Explicitně zvolený neexistující či
neplatný soubor nemá fallback. Stávající export `directory` a graph/store
v1/v2/v3 zůstávají beze změn. Nový store, live adapter ani publish CLI nevzniká.

## Acceptance a ověření

- AC01: status zůstává `NOT_RUN` i při přítomných auth references; žádný live PASS.
- AC02: pět existujících `test_confluence_sync.py` scénářů prošlo beze změny;
  konfigurace nemění graph/store ani offline export workflow.
- AC03/AC05: `test_confluence_configuration.py` ověřuje nulové síťové/procesní
  volání, byte-identický poslední graf, nevypsání secret hodnot, duplicitní JSON,
  precedence, invalidní host/auth/API a základní auth s oběma referencemi.
- `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q tests/test_confluence_configuration.py tests/test_confluence_sync.py`:
  **28 PASS** (0.24 s) po nezávislém review.
- `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q`:
  **281 PASS / 23 SKIP** (12.90 s), Python 3.12.14 nad main `aa9e64b`.
  SKIP patří nepřipraveným Maven/Gradle/JDK/worker variantám; nejsou tvrzeny jako
  PASS. Tato změna compiler, renderer ani build workflow nemění.
- Živá Confluence integrace a autentizace vůči skutečnému hostu: **NOT_RUN**, na
  explicitní pokyn uživatele odloženo. Chování API není touto konfigurací ověřené.

Nezávislé review odhalilo mezní vstupy standardního JSON parseru. Doplněno je
odmítnutí NaN/Infinity, strukturovaná chyba při nadměrném zanoření či integer
limitu parseru a odmítnutí řídicích znaků v URL hostu. Konkrétní reprodukce
mají regresní testy; chyby nevypisují vstupní data ani secret hodnoty.

Scoped `semantic update --base aa9e64b` / apply / validate: PASS; původní
koncepty a vztahy zůstávají zachovány a README evidence je ověřena na nových
řádcích. `memory capture` se skutečnými výsledky, příkazem generovaný scan,
`kgmaker check` a `git diff --check`: PASS. Nevzniká domyšlená sémantická vazba.

Integrace po XLS PR #21 proti main `35033096e8a2ea5d74ae8d2195a7b27d22c7590a`
zachovává oba bloky dokumentace i sémantickou historii. Konfigurační runtime a
testy jsou beze změny vůči nezávisle schválenému `525779a`. Úplná integrovaná
sada: **297 PASS / 23 SKIP** (12.32 s); příslušné live ověření zůstává odložené.

Po integraci exporter main `e656b8ef4c174d3d60600037d7c0d78fc514e39d` zůstávají
konfigurační zdroje/testy beze změny; focused config/boundary/exporter contracts
mají **36 PASS / 2 DESELECTED** (0.27 s). Dva skutečné exporter buildy nejsou
součástí této konfigurační kontroly; jejich důkaz patří do change note 37.

Finální integrace s T006/T007 proti main `3a393e451b0d7b8f83de93f05f07d2307ba66ec3`:
**331 PASS / 25 toolchain SKIP** (17.15 s). Konfigurační runtime/testy se nemění.
Při slučování sémantické vrstvy byly zachovány také dva dříve ověřené vztahy
`implements`/`validates`, které předchozí integrace omylem vynechala. Skutečný
scanner stále vrací cíle `apply_semantic_patch::440` a `validate_semantic_data::100`;
zdrojové definice/evidence zůstávají na řádcích 442/102 v `semantic.py`.
Nejde o nové inference, ale o obnovu původních doložených vazeb při zachování
všech současných konceptů a historie.

## Příklad a zbývající práce

Úplný příklad je v [capability dokumentaci](../feature-analysis.md#deferred-confluence-connection-configuration).
Bez konfigurace je connection disabled a neprovádí žádnou komunikaci.
Budoucí live adapter musí použít explicitní verzi API a schválený sandbox,
zachovat hash/version approval a ověřit skutečný integrační běh samostatně.
Úplný live konektor ani produkční Confluence připravenost nejsou hotové.
