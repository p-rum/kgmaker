# T003-S07-W03 — doložený field a mapper tok

Datum 2026-11-15. Zadání: [T003-S07-W03](../tasks/T003-S07-03-fieldAndMappingFlow.md),
parent T003-S07 / T003-AC07. Výchozí SHA všech kroků:
`14d7f7cefab2fa5c9cf8c6d939d3b92e838faea8`. Samostatná větev
`feat/t003-s07-03-field-and-mapping-flow`. Historické dodání při tomto checkpointu
IN_PROGRESS (lokální implementace k předání PR), ověření VERIFIED_IN_SCOPE pro níže uvedené Javac testy;
celá milníková/produkční acceptance PARTIAL. Závislosti W01/W02 a S06-W02 jsou
v baseline merged; původní výsledky se nepřejmenovávají na nový PASS.

## Krok 1 — rekognoskace a reprodukce (AC01, AC04)

Problém: `dataflow.py` měl lokální SOURCE_ONLY mapping a compiler argument/return
proofs; z field bindingů se nevytvářel explicitní getter → helper → setter přenos.
Existující `JavaFrontend.java` a `return_flow.validate_return_ir` již dodávají a
validují potřebné binding identity, source rozsahy a SHA. Použitý extension point
je `inspection.graph_from_response` před publikací. V checkoutu nebyl čitelný
store: status/query/memory recall to pravdivě ohlásily; historické GRAPH.md/NOTES.md
byly jen navigace ověřená ve zdroji. SOURCE_ONLY/domain/JPA názvy nejsou join klíč.

RED: skutečný `test_public_manual_and_actual_generated_mapper` selhal na
`Missing compiler-proven explicit field mappings` (1 FAIL), po explicitním
Javac+MapStruct buildu. První pokus měl nesprávný PATH na JRE a byl FAIL toolchain,
nikoli PASS. Opraven PATH na plný JDK21. Dokumentace podpory před rozšířením:
[matice](../field-mapping.md). Bez změny veřejných schémat.

## Krok 2 — existující model a kompatibilita (AC02)

`src/kgmaker/field_flow.py` používá existující Node/Edge/evidence; `dataflow.py`
zveřejňuje `field_mapping_bindings` také v directional impact JSON. `inspection.py`
přidává pouze JVM `field_flow_rule_version=field-mapping-1` do content-bound contextu
plus projekční hook. `graph_provider.py` offline odmítá nekompatibilní zaznamenanou
verzi jako STALE. `workspace.py` kvalifikuje occurrence metadata a vnořené provenance.

Worker protocol v1 ani graph/store v1/v2/v3 se nemění; žádné nové compiler IR pole,
žádný nový store ani migrace. Staré grafy zůstanou čitelné bez nové W03 evidence.
`domain.py`: bez dopadu, záměrně se nevytváří name-only DTO/JPA mapování.
Kompatibilita ověřena v1/v2/v3 roundtripem a W01/W02 regresí níže (PASS).

## Krok 3 — field projekce, diagnostika, atomicita (AC01–AC03)

Javac source field read/write má vlastní occurrence. Přímé assignment mapy nesou
field identity, owner method, SHA/ranges, průchod helper metodami/call sites a guards.
Přímé source helpers jsou omezeny na static/private/final dispatch a straight-line
tělo; parametry váže přesná W01 `DIRECT` argument→parameter evidence; vararg packing se neoznačí za direct transfer.
Business transformace, chybějící tělo, otevřený dispatch, rekurze a rozdílné branch
hodnoty nevytvářejí silnější mapping. Limity: 50 000 expression kroků, 16 helper
vnoření, 64 control vnoření a 256 provenance lokátorů; překročení je UNKNOWN.

`availability` i `business_equivalence` zůstávají UNKNOWN,
`runtime_execution=NOT_OBSERVED`. Mapy jsou deklarativní závislosti fieldů, ne
instance/alias/order nebo type-conversion safety proof. Třídy/metody bez field
relevance nedostávají nové mapper diagnostiky. Malformed actual compiler response
se odmítne před projekcí; timeout/cancel orchestrace zachová byte-for-byte uložený
index. Existující transport testy skutečně testují timeout/cancel procesů.
Offline scan a SOURCE_ONLY se testují s procesy zakázanými. PASS, viz příkaz níže.

## Krok 4 — skutečná fixture a testy (AC01–AC03)

`fixtures/field-mapping` + `tests/test_field_mapping_flow.py`: handwritten public
field copy a private field přes final getter → identity helper → final setter;
MapStruct1.6.3 skutečně generuje implementaci v dočasném source rootu explicitním
`javac -processorpath ... -s ...` a veřejná `inspect_jvm` ji analyzuje. Nejde o ručně
předstíraný manifest ani checked-in generated mapper. Test nedělá network/install.

Negativní fixture obsahuje `trim` transformaci, rozdílné branch hodnoty, open virtual
dispatch, rekurzi, přepis lokálu a smyčku. Negativní vararg packing nevydává scalar→array za přímý transfer. Pozitivní overload používá druhý String
argument a compiler-selected descriptor. Store roundtrip/offline retention,
workspace qualified locators, source/rule STALE, v1/v2/v3, kontrolované timeout/cancel
publikace a poškozená skutečná compiler evidence jsou samostatné assertions.

Finální cílený příkaz (JDK21 + nezměněné K1/K2 worker JARy z baseline; existující
TypeScript5.7.3 dependency strom pouze připojen jako lokální ignorovaný symlink):

```bash
PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH \
JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 \
KGMAKER_WORKERS_HOME=/tmp/kgmaker-w03/workers KGMAKER_REQUIRE_WORKERS=1 \
PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest -q \
  tests/test_field_mapping_flow.py tests/test_dataflow.py \
  tests/test_argument_parameter_flow.py tests/test_return_consumer_flow.py \
  tests/test_worker_protocol.py --tb=line
```

**PASS: 163 passed, 0 skipped, 0 failed (63.09 s; finální vararg guard a actual negativní fixture zahrnuty).**
Před finálním vararg guardem stejná cílená sada: 163 PASS /0 SKIP /0 FAIL, 66.22 s. Obsahuje skutečný Javac,
MapStruct, K1/K2 Java a relevantní W01/W02 TypeScript/Kotlin regresi. Samostatný
předchozí field/dataflow/transport běh: 31 PASS. První širší pokus: 86 PASS,
24 FAIL/53 ERROR kvůli chybějícím TypeScript dependencies v zvoleném worker HOME;
po připojení lokální dependency složky byly ještě 3 FAIL/160 PASS kvůli odlišnému
HOME u W01 testů. Finální jednotný worker HOME výše vše vyřešil bez instalace.

Doplňující oprava kroku 4: failure test používá stejný
`KGMAKER_MAPSTRUCT_REPOSITORY` jako pozitivní fixture (původně měl v tomto jednom
místě pevnou default cestu). Defaultní chování beze změny. Následný příkaz se
stejnými env hodnotami a `python -m pytest -q tests/test_field_mapping_flow.py --tb=line`:
**14 PASS**, bez SKIP/FAIL. Žádná změna produkčního kontraktu.

Worker zdroje beze změny, nový worker build bez dopadu. Javac fixture build je
součást explicitního cíleného testu. Plná suite **NOT_RUN** dle uživatelského pokynu
(full až celý balík). GitHub Actions **NOT_RUN** pro tento lokální commit;
žádné tvrzení o PASS CI. Production corpus, instance alias analysis, obecné
MapStruct konverze, Kotlin/TS field projection a runtime/data důkazy **NOT_RUN**.

## Krok 5 — dokumentace, graf a předání (AC04)

README odkazuje na novou omezenou capability; `docs/field-mapping.md` obsahuje
veřejná pole, limity a CLI příklad; `docs/compiler-inspection.md`,
`docs/production-analysis-progress.md`, `docs/acceptance-inventory.md` a fixture
README odkazují na tuto změnu. Registr/zadání beze změny identity/revize/závislostí;
SPECIFICATION dál popisuje cíl. Instalované instrukce/templates bez dopadu:
nepřidává se příkaz ani init soubor. CLI parser bez dopadu: používá stávající
`inspect code`, `query` a `impact --include-data-flow --format json`.

Semantic patch zachová ověřené dotčené vztahy, znovu ukotví posunuté lokátory a
přidá pouze source-backed vazby implementace a testu k dokumentovanému W03 konceptu.
Grafy se generují příkazem; žádná ruční editace generated graphů. Dokončené kontroly: `semantic apply` a `semantic validate` PASS (329 concepts,
29 798 relationships); `scan` a `check` PASS (569 files, 6 410 nodes,
43 540 relationships před posledním vararg guardem). `git diff --check` PASS.
Příkazy CLI porovnány s aktuálním `inspect code --help` a `impact --help` (PASS).
`memory capture --base 14d7f7cefab2fa5c9cf8c6d939d3b92e838faea8
--validation targeted163=passed --validation full-suite=skipped
--validation github-ci=unknown` PASS; validovaná implementační epizoda je v
semantic vrstvě. Workflow analysis/plan/implementation/test artefakty jsou lokálně
zaznamenány, fáze review čeká na nezávislého reviewera; žádné vlastní APPROVE.
Finální vararg guard spotřebovává výhradně W01 `DIRECT` bindings, nikoli vlastní
odhad pozice; regresní fixture zachytí nepřípustný scalar→vararg-array přenos.

Preservation audit vůči baseline SHA výše: **PASS**. Všech 42 původních semantic
concepts a 286 historických episodes zůstalo byte-for-byte; 135 původních edges
zůstalo zachováno (jen 3 source-line a 2 function-line identity reanchors).
Nově 1 koncept, 3 vztahy a 2 implementační epizody; celkem 43/138/288.
Audit porovnal `git show <baseline>:.kgmaker/semantic.json` s aktuálním artefaktem,
ID množiny a obsah každé původní položky; u edge ID toleroval pouze posun řádku
stejné jednoznačné deklarace. Žádná nesouvisející evidence nebyla vynechána.
Finální `semantic validate`, `scan`, `check` a `git diff --check`: **PASS**;
331 concepts /30 606 semantic relationships; 569 files /6 414 nodes /44 356
celkových relationships. Dvě implementační epizody zachovávají historické snapshoty,
nejde o zvýšení compiler/runtime důkazu ani nový test PASS.

Příklad: `target.setName(identity(source.getName()))` doloží `Source.name maps_to
Target.name` přes compiler source těla. `target.setName(business(source.getName()))`
s `trim()` nedoloží business ekvivalenci ani field mapping. Samotné `@Mapper`
bez zachyceného generated source také nevytvoří transfer.

Zbývá nezávislé PR review, případné opravy a merge autorizovaným reviewerem.
Tento krok nedeklaruje dokončení celého S07/T003 ani libovolného produkčního mapperu.


## Krok 6 — integrace po PR103 (T003-S07-W03, AC01–AC04; 2026-11-15)

Výchozí schválený HEAD PR104: `d78286ed65e137495c130e72233dd466da0dd96b`.
Skutečný main: `b1a8ba1f4234cd399de8319fcf5cde2c670dac26`, potvrzený dvourodičový
merge PR103 se stejným tree jako schválený `03aaf0d`; PR101–103 jsou MERGED.
`git merge --no-ff --no-commit b1a8ba1f4234cd399de8319fcf5cde2c670dac26` zachovává
historii bez rebase/force. PR104 zůstává PR_OPEN, nový integrační HEAD vyžaduje
samostatné nezávislé review. Žádné změny souběžné BE→FE větve se nepřebírají.

Rekognoskace kgmaker-context ověřila status, query, memory recall a zdroje.
Jediný funkční překryv je `graph_provider.py`: W03 guard pro
`field_flow_rule_version` uvnitř `validate_context_snapshot` a T037 samostatný
`view_context_fingerprint`. Git je sloučil automaticky; AST celého modulu po
odebrání pouze T037 helperu je shodné s W03 rodičem a helper s main. Všech dalších
11 W03 a 16 main source/test/fixture souborů je byte-identických s příslušným
rodičem. Žádný funkční integrační patch ani nový behavior test nebyl potřeba.

Konflikty v acceptance/progress zachovávají obě task sekce; aktuálně uvádějí
PR103 MERGED a PR104 PR_OPEN. Semantic/generated konflikt se řeší v kroku 7.
README a compiler capability se sloučily bez konfliktu; field-mapping.md,
view-cache.md, runtime-trace.md, architecture CLI, fixture README a všechny
API/CLI příklady jsou bez nové změny veřejného chování. Registry/revize zadání,
worker protocol, graph/store schéma a installed templates jsou bez dopadu.
Source-freshness, UNKNOWN business/runtime limity a veřejné příkazy zůstávají.

`inspection.graph_from_response` je doložený společný tok W03 projekce s novými
JVM named-query a runtime fixtures. Proto vedle původních pěti W03 modulů běží
jen jeden actual named-query pozitivní test a dva actual runtime capture testy;
celé dřívější sady 205/298 se neopakují.

```sh
env PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH \
  JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 \
  KGMAKER_WORKERS_HOME=/tmp/kgmaker-w03/workers KGMAKER_REQUIRE_WORKERS=1 \
  PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest -q \
  tests/test_field_mapping_flow.py tests/test_dataflow.py \
  tests/test_argument_parameter_flow.py tests/test_return_consumer_flow.py \
  tests/test_worker_protocol.py \
  tests/test_named_query_containers.py::test_actual_javac_named_query_containers_reference_parameters_and_projections \
  tests/test_runtime_trace_producer.py::test_actual_jdk21_application_observes_all_four_kinds_and_no_values \
  tests/test_runtime_trace_producer.py::test_actual_jdk21_capture_is_opt_in_and_records_only_executed_branch \
  --tb=line
```

**PASS: 166 passed / 0 skipped, 67.84 s**. Použit skutečný JDK21, MapStruct1.6.3,
existující K1/K2 worker distribuce a TypeScript dependencies. Předem existující
lokální ignorované symlinky `workers/jvm/target`, `target-k2` a
`workers/typescript/node_modules` byly pouze použity; žádná instalace ani další
worker build. Výše uvedený test explicitně generuje/kompiluje fixture a spouští
dva opt-in runtime scénáře; scan/hook nemění svůj offline kontrakt.

Source identity a AST složení **PASS**. Full suite, další produkční corpus a
GH CI **NOT_RUN** dle pověření. Předchozí 163 PASS/63.09 s a 14 PASS zůstávají
historickými výsledky původního W03 HEAD; nový výsledek 166 testů je nerozšiřuje na obecné
Kotlin/TS field projection ani MapStruct business ekvivalenci.


## Krok 7 — zachování kumulativní evidence (T003-S07-W03, AC04; 2026-11-15)

Výchozí SHA jsou W03 `d78286ed65e137495c130e72233dd466da0dd96b` a main
`b1a8ba1f4234cd399de8319fcf5cde2c670dac26`. Semantic konflikt zachoval aktuální
main fakta i doložený W03 koncept/tři vztahy; epizody tvoří union podle ID s
kontrolou shodnosti objektů. Scoped patch z aktuálního packetu obsahoval 14
konceptů a 77 vztahů, bez removals. Reanchor porovnal source hash správného
rodiče, nezměněný text citované řádky a jednoznačnou deklaraci v aktuálním indexu.
Nezavádí novou technickou ani business evidence.

```sh
./kgmaker semantic update --base b1a8ba1f4234cd399de8319fcf5cde2c670dac26 --note docs/changes/124_fieldAndMappingFlow.md
./kgmaker scan --no-docs
# Source-backed patch používá právě připravené update_id, žádné removals.
./kgmaker semantic apply
./kgmaker semantic validate
python3 /tmp/w03-integration-preservation.py
./kgmaker memory capture --base b1a8ba1f4234cd399de8319fcf5cde2c670dac26 --validation w03-integration166=passed --validation semantic-preservation=passed --validation source-identity=passed --validation full-suite=skipped
./kgmaker scan
./kgmaker check
git diff --check b1a8ba1f4234cd399de8319fcf5cde2c670dac26
git diff --check d78286ed65e137495c130e72233dd466da0dd96b
```

Všechny uvedené kontroly **PASS**. První scan před reanchor pravdivě vynechal
74 stale vztahů; finální scan je již nevynechává. Audit zachoval všechny
concept IDs, relationship `(source,target,kind,confidence,confidence_score)`
s normalizací pouze koncového line suffixu `::číslo` a všechny původní episode
objekty: baseline **42/135/286**, W03 **43/138/288**, main **43/138/294**.
Union před capture je **44/141/296**, po jedné skutečné nové epizodě
`aea25d5b22a3cd1a9730c6e283a5b060dc3b4b83c3d878a48328b0daca0aebcb`
celkem **44/141/297**. Source identity všech 27 souborů a AST složení
`graph_provider.py` z kroku 6 také **PASS**. Všechny generated grafy vznikly
příkazem, po závěrečném dokumentačním textu se obnovují stejným scan/check.

Dokumentace a veřejné návody mají stejný dopad jako krok 6; tato údržba mění
pouze interní citace/generovanou navigaci. Full suite, další toolchain/produkční
corpus a GitHub CI **NOT_RUN**. Žádné vlastní APPROVE ani tvrzení MERGED PR104;
zbývá nezávislé review přesné publikované integrační revize a autorizovaný merge.
