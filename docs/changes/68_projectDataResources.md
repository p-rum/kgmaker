# Projekce explicitních databázových resources

T015, kroky S01–S05, AC01–AC06. Explicitní dependency base je T009/PR48
`d0932d9c3f7de9827ea590b6f981aa29e5b39349`, obsahující T008/T009 kontrakty;
původní implementace začala na cbf17b1.
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
- Public suite nyní36 případů pokrývá všechna AC01–AC05. Root read-only review
  reprodukoval polarity `[]` TypeError; fix a pět variant mají explicitní UNKNOWN
  a nezměněné vstupy. Stale/malformed freshness mají čtyři další varianty.
- `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q --tb=short
  tests/test_t015_project_data_resources.py tests/test_t008_project_service_inventory.py
  tests/test_t009_propagate_view_evidence.py tests/test_flyway.py tests/test_workspace.py
  tests/test_dataflow.py`: **115 PASS v6.79s**.
- Skutečné SQL scripts, workspace snapshot a reconstruct se připravují před
  subprocess zákazem. Access cases dodávají veřejný bounded upstream Graph/Edge
  kontrakt; nejde o tvrzení nového compiler worker acceptance.
- Jeden focused příkaz omylem uvedl neexistující test_schema_replay.py: nespustil
  žádné testy a byl nahrazen existujícím test_flyway.py. Pozdější mapping fixture
  nesměla zahodit inherited graph evidence; oprava fixture nemění runtime.
- Actual runtime prerequisites byly explicitně zkopírovány z source-identického
  `default-body` checkoutu (celý JVM source diff bez rozdílu). Read-only prerequisite
  preflight PASS. Instalace/build/fetch ani Maven/Gradle execution nebyly vyvolány.

Opravený strict full zatím nebyl spuštěn, nikoli PASS. Příkaz pod sdíleným flockem používá
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
validaci. Parent vlastní nezávislé review, remote CI a publikaci. Lokálně nebyl proveden
merge do main ani CI retry; dřívější billing pause byla uživatelem odblokována.

## Oprava target scope/context a finální dependency metadata

Vlastní následné read-only probe nad9445f81 a potvrzení parentem našlo P1:
ORM node mohl tvrdit production, ale odkazovat na skutečný test/unknown file.
Sdílený validní migration resource maskoval chybějící target context proof.
Před jakoukoli editací byl zastaven jen vlastní full pytest63637 a jeho worker68416,
oba následně ověřeny jako ukončené. Přerušený log/XML/status zůstávají jako
`/workspace/t015-validation/interrupted-9445f81.*`: **487 PASS, 9 SKIP**,
346.36s, exit2 KeyboardInterrupt. XML496 tests/0errors/0failures/9skips je validní
část běhu, nikoli celý PASS. Žádný jiný queued/running suite nebyl ukončen.

Fix vyžaduje scope a SHA obou endpoint files ze stejného selected contextu,
explicitní endpoint metadata nesmí tvrdit jiný context. Unselected/foreign ORM
tables se nepřenášejí ani jako drill-down proof; invalid access nevytváří unused
foreign provenance. View proof nyní uchovává source i target snapshot hash.
Čtyři negativní varianty a platný production round-trip doplňují36 public cases;
broad focused **115 PASS v6.79s**. Durable feedback přechází test→implement,
iteration1; neprobíhá self-approval.

Před novým full byla integrována finální metadata T009
`d0932d9c3f7de9827ea590b6f981aa29e5b39349`; produkce/testy/workers/pyproject jsou
proti původnímu cbf17b1 byte-identické. Přesný parent prefix113 episodes je
zachován, poté přidán původní nezměněný child capture. Finální base je d0932d9.

## Skutečný upstream framework kontrakt

Actual Javac probe odhalil, že existující native/JPQL framework evidence nemá
volitelné fact SHA a že JPQL query target je entity, nikoli přímo table. Silnější
syntetický kontrakt tuto integrační hranici nezachytil. Před změnou byl zastaven
pouze vlastní neplatný full nad75027d2: **168 PASS, 2 SKIP v250.25s**, exit2;
XML170 tests/0errors/0failures/2skips a log/status/process evidence zůstávají
v `interrupted-75027d2.*`. Nejde o dokončený full PASS.

Chybějící fact SHA se odvozuje pouze z totožného selected-context source_files,
graph.files a aktuálního souboru. Výstup výslovně uvádí
`hash_provenance=VALIDATED_CONTEXT_SOURCE`; existující SHA zůstává
`ORIGINAL_FACT_SHA`. Stale nebo malformed dodané SHA nevytvoří access.
JPQL může využít jedinou existující exact entity→maps_to_table edge, pokud oba
kroky splní stejné scope/context/realm/evidence guards. Zachovávají se obě
původní composite edge identity a evidence refs; žádný name match, parser nebo
nový resolver nevzniká. Ambiguity nebo foreign mezikrok zůstávají UNKNOWN.

Pure public cases: **45 PASS, 2 actual deselected v1.32s**. Nové actual K1/K2
fixture používají offline hashované skutečné JPA/Spring API, dva explicitní
Flyway realms a Javac native read/write + JPQL; obě actual varianty jsou GREEN. Strict focused batch celé public module + T008/T009,
Flyway/workspace/dataflow: **126 PASS v7.94s**, bez skips. Čistý batch bez actual
variant: **124 PASS, 2 deselected v8.65s**. Strict full stále není PASS.
