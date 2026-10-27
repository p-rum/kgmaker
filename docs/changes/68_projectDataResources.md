# Projekce explicitních databázových resources

T015, kroky S01–S05, AC01–AC06. Explicitní dependency base je T009/PR48
`cbf17b1d57719c05c4e918851647c375811e8b07`, obsahující T008/T009 kontrakty.
Stávající podporovaný S06 persistence subset se pouze čte; celý S06/W08, T004
ani produkční připravenost nejsou prohlášeny za dokončené.

## Problém a skutečná změna

Chyběla oddělená identita databázového resource nad tabulkami a persistence fakty.
Nový čistý `data_resources.project_data_resources` reuse T008 service inventory,
T009 ViewDocument/evidence buckets a skutečné `snapshot_workspace` schemas/graph.
Workspace/repo/explicit database/stream vytváří resource identity; tabulky jsou
pouze drill-down IDs. Neexistuje nový store, DB konektor ani parser query.

Schema inventory/config fingerprint, explicitní workspace overrides, table IDs,
source classification a aktuální SHA musejí souhlasit. Samotný JDBC URL, DTO,
schema ani entity mapping není read/write proof. Pouze existující selected-context
`query_reads/writes/deletes` s odpovídajícím realmem, vlastnictvím, evidence a SHA
vytvoří access claim. `maps_to_table` a migrations vytváří nejvýše dependency.

Flyway ponechává MIGRATION_DERIVED v atributu; nepřidává nový T009 evidence kind.
SOURCE_ONLY, UNKNOWN a původní FRAMEWORK_DERIVED se neslévají na runtime důkaz.
Explicitní polarity/conflicts se zachovávají, malformed polarity je UNKNOWN s
lokalizovanou diagnostikou. Stale/malformed proof freshness nevytvoří current
access. Deployment i populated-data availability zůstávají UNKNOWN.

Unknown file scope se nepromuje podle repo; default Flyway mapping bez explicitní
DB identity zůstane unresolved. Chybějící, cizí a konfliktní realm ani nepodporovaný
S06 adapter se nehádá. Výstup je PARTIAL, prázdná resource coverage UNKNOWN.
Schema/store v1/v2/v3, stávající CLI, loader a renderery se nemění.

## Ověření a akceptace

- Architecture brief od parenta ověřen ve views/workspace/schema_replay/framework;
  durable task `task:f7895e5fea5cdfe5862b60e65361cf0e647f1da2c879d8a5c108b267217d16c0`
  má skutečný analyze/plan artifact a bounded packet; memory recall proběhl.
- RED: nový public module import chyběl (collection ERROR); po implementaci prvních
  deset skutečných public workspace/replay a negativních kontraktů GREEN0.66s.
- Public suite nyní31 případů pokrývá všechna AC01–AC05. Root read-only review
  reprodukoval polarity `[]` TypeError; fix a pět variant mají explicitní UNKNOWN
  a nezměněné vstupy. Stale/malformed freshness mají čtyři další varianty.
- `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q --tb=short
  tests/test_t015_project_data_resources.py tests/test_t008_project_service_inventory.py
  tests/test_t009_propagate_view_evidence.py tests/test_flyway.py tests/test_workspace.py
  tests/test_dataflow.py`: **110 PASS v6.80s**.
- Skutečné SQL scripts, workspace snapshot a reconstruct se připravují před
  subprocess zákazem. Access cases dodávají veřejný bounded upstream Graph/Edge
  kontrakt; nejde o tvrzení nového compiler worker acceptance.
- Jeden focused příkaz omylem uvedl neexistující test_schema_replay.py: nespustil
  žádné testy a byl nahrazen existujícím test_flyway.py. Pozdější mapping fixture
  nesměla zahodit inherited graph evidence; oprava fixture nemění runtime.
- Actual runtime prerequisites byly explicitně zkopírovány z source-identického
  `default-body` checkoutu (celý JVM source diff bez rozdílu). Read-only prerequisite
  preflight PASS. Instalace/build/fetch ani Maven/Gradle execution nebyly vyvolány.

Strict full je zatím QUEUED, nikoli PASS. Příkaz pod sdíleným flockem používá
JDK21.0.6+7/Kotlin2.1.10, vlastní K1/K2 resources, skutečnou Maven fixture a API
cache. Log/XML/temp jsou v `/workspace/t015-validation/`, mimo malý `/tmp` tmpfs.

```bash
flock /workspace/kgmaker-heavy-tests.lock env \
  JAVA_HOME=/workspace/tools/jdk-21.0.6+7 \
  PATH=/workspace/tools/jdk-21.0.6+7/bin:/workspace/tools/kotlinc/bin:$PATH \
  PYTHONPATH=/workspace/t015/src KGMAKER_WORKERS_HOME=/workspace/t015/workers \
  KGMAKER_TEST_MAVEN_REPOSITORY=/workspace/tools/m2 KGMAKER_REQUIRE_WORKERS=1 \
  KGMAKER_REQUIRE_K2=1 KGMAKER_REQUIRE_SPRING_IMPORTS=1 \
  TMPDIR=/workspace/t015-validation/tmp /workspace/kgmaker-venv/bin/python \
  -m pytest -q -rs --tb=short --basetemp=/workspace/t015-validation/pytest \
  --junitxml=/workspace/t015-validation/full.xml
```

## Použití a zbývající hranice

Po explicitním `snapshot_workspace` předej jeho loaded workspace/graph/coverage
funkci `project_data_resources(..., scope="production")`; vrací validovaný topology
ViewDocument a nic nezapisuje. Databáze se nekontaktuje. README a capability docs
uvádí stejný Python příklad; nový CLI command neexistuje.

Sémantická aktualizace, memory a finální scan/check se zaznamenají po finální
validaci. Required CI je nadále externě BLOCKED billing limitem a jeho řešení
uživatel pozastavil. Parent vlastní nezávislé review/publikaci; žádný merge ani
CI retry nebyl proveden.
