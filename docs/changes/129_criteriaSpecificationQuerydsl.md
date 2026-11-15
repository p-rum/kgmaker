# T003-S06-W07 — statický záměr Criteria, Specification a QueryDSL

Datum: 2026-11-15. Task/Step: `T003-S06-W07`, kroky 1–5 zadání.
AC: `T003-S06-W07-AC01–04`, nadřazené `T003-AC06` zůstává PARTIAL.
Dodání IN_PROGRESS, ověření PARTIAL. Specifikace je cílová, nikoli důkaz dodání:
[W07](../tasks/T003-S06-07-criteriaSpecificationQuerydsl.md).

## Krok 1 — rekognoskace a červená skutečná fixture (AC01, AC03, AC04)

Baseline `9f538634807957abe1004dde43450271b77f1bb5`; rodiče `8e7dff5b` a
`8f023bc6`, tree `990f9de74320da19466b8400cdb6224e3975e072`. Závislosti
S04-W04 `ec333966`, S06-W05 `2bebab00`, W06 `9f88d846` jsou ancestry baseline
(`git merge-base --is-ancestor` všechny PASS). Izolace `/tmp/kgmaker-criteria-queries`.
Root checkout nebyl změněn. Registry/spec/profile/AGENTS/instructions/progress
přečteny; změna nepotřebuje nový Task ID. Note129 rezervoval koordinátor po
kontrole main max127 a otevřených PR (W09 note128).

`PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m kgmaker status`, `query` a
`memory recall`: NOT_RUN z hlediska grafových výsledků, příkazy skončily
„No readable graph“. Pre-task graph.json chybí; nebyl zpětně vyráběn. Tracked
GRAPH/NOTES sloužily navigaci, kontrakty ověřeny v framework/inspection/worker/
return_flow/field_flow a named-query testech. Architektonická rekognoskace přímo
podle kgmaker-architect (sdílené sloty); koordinátor potvrdil dva malé inspection
extension pointy. Runtime workflow task `00f84d244868100da462b8a85dfe885e6b5c17fd1195363f706991e257bef50b`.

Přidány `fixtures/criteria-queries/src/main/java/demo/Order.java`, `Queries.java`
a `tests/test_criteria_queries.py`. Skutečné Jakarta Persistence3.1,
Spring Data JPA3.4.2 a QueryDSL5.1 JARy. Explicitní fixture setup spouští skutečný
`com.querydsl.apt.QuerydslAnnotationProcessor` a generuje QOrder; není součástí
scan/inspect. Jediná chybějící závislost připravena explicitním Maven
`dependency:get -Dartifact=com.querydsl:querydsl-jpa:5.1.0:jar:jakarta -Dtransitive=false`.
Nepoužívají se falešné API téhož jména.

Kontroly: první fixture setup ERROR (PATH ukazoval JRE, přestože JAVA_HOME byl
nastaven); opraven PATH na skutečné JDK21. Následující
`PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 KGMAKER_WORKERS_HOME=/tmp/kgmaker-pr97-reconciled/workers KGMAKER_REQUIRE_WORKERS=1 PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_criteria_queries.py --maxfail=1`
vrátil očekávaný **FAIL1 /2.70s**: všechny tři programmatic query families chybějí.

## Krok 2 — additive producer a bounded projekce (AC01–03)

Stejný baseline; `JavaFrontend.java` doplňuje compiler class literal, qualified
expression type, field receiver, source parameter binding, lambda interface
identity a ověřenou QueryDSL member factory. Nový `criteria_queries.py` validuje
přítomné payloady i při chybějící/neznámé verzi, používá skutečná call-site a
binding IDs, vytváří bounded source intent a znovu ověřuje provenance při replay.
`inspection.py` volá validator před publikací a capture po existujícím field flow;
`framework.py` provádí query projekci až po finálním ORM XML/access/realm modelu.

Veřejný kontrakt reuse `orm_query`, `declares_query`, `query_reads`, `filters_by`;
`repository_uses_fragment` je deklarovaná možnost kompozice, ne runtime dispatch.
`query=None` vždy, evidence FRAMEWORK_DERIVED s původními compiler witnesses.
Dynamický root/field/predicate, větvení, reassignment a multiple roots jsou
konkrétní gaps. Dostupnost UNKNOWN, execution NOT_OBSERVED. Staré vstupy bez
rozšíření zůstávají čitelné, graph/store schema zůstává1/2/3 bez migrace.

Worker byl skutečně rebuilt výhradně do lokálního `workers/jvm/target` (žádný
symlink/shared output) příkazem
`python3 workers/jvm/build.py --kotlin-home /tmp/kgmaker-kotlin-official/kotlinc --maven-repository /home/petra/.m2/repository --java-home /usr/lib/jvm/java-21-openjdk-amd64`.
Build PASS. První validator odhalil syntetický Javac `super()` bez zdrojového
rozsahu; producer pro něj nepublikuje query type proof. Následný actual test
**PASS1 /2.67s**. Další testy/provenance přidány před konečným předáním; každý
rebuild používal matching source, konečný checksum a běhy níže.

## Krok 3 — integrace skutečného PR107 main (AC02, AC04)

Baseline `7bb8b8d389c461c684197704203a99dcb2b83724`, rodiče `9f538634` +
`61f1d6c`, tree `8542cbdeb0339af20b52d1448baf878866e76e92`. Izolovaná větev
fast-forwardována před prvním commitem; vlastní rozpracovaný diff bezpečně
obnoven, inspection hooks čistě sloučeny. BEFE frontend validator/capture,
dataflow a TS worker beze změny. Tracked semantic historie48concepts/157edges/
310episodes je výchozí množina pro následný scoped update.

## Krok 4 — negativní evidence a kompatibilita (AC01–04)

Baseline `7bb8b8d389c461c684197704203a99dcb2b83724`. Rozšířeny cílené testy:
invalid/missing IR marker, foreign source/call/binding, stale replay, candidate
tamper, source API místo dependency, staré schema1/2/3 a starý worker,
ambiguous fragment, application API stejného jména, conditional builder,
offline scan/hook, strict/cancel/timeout a poslední platný store.

Průběžný příkaz s lokálním matching workerem
`PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 KGMAKER_WORKERS_HOME=/tmp/kgmaker-criteria-queries/workers KGMAKER_REQUIRE_WORKERS=1 PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_criteria_queries.py --maxfail=1 --tb=short`
vrátil **21 PASS /0SKIP /15.07s**. Následující rozšířený běh měl21PASS +1FAIL
kvůli nesprávnému názvu testovacího argumentu inspect_jvm; veřejné persistence
selectors patří do `build_context`, test opraven. Toto není runtime/DB PASS.

## Dokumentační plochy a zbývající práce

README, compiler capability/CLI příklady, progress a acceptance matice jsou
aktualizovány ve stejném PR; odkazy a příklady viz krok5. Registr beze změny: totožnost/revize/
závislosti zadání se nemění. Instalované instrukce/Python templates bez dopadu:
API procesu init se nemění. dataflow bez změny: stávající compiler flow a
`filters_by`/`query_reads` již spotřebují společné projekce; nevzniká druhý katalog.
K1/K2, obecné Criteria/QueryDSL provider operace, DB/runtime, full pytest a GHCI
NOT_RUN. Full až celý balík dle výslovného pokynu uživatele.

## Krok 5 — finální ORM scope a dokumentační matice (AC01, AC03, AC04)

Baseline `7bb8b8d389c461c684197704203a99dcb2b83724`. Actual testy rozšířeny
o vybranou persistence unit s XML overrides, stejnojmennou entitu v jiném
package, skutečný generated Qfield s neplatným factory property, PROPERTY
access a inherited atribut. Původní PROPERTY fixture kombinovala FIELD ID
v mapped superclass s PROPERTY entity; existující ORM vrstva správně označila
konflikt, takže W07 nepřidal žádný attribute proof. Test nyní samostatně ověřuje
konzistentní PROPERTY pozitivní a tuto konfliktní negativní variantu. APT se po
změně source fixture explicitně opakuje. XML default `META-INF/orm.xml` patří
všem units; původní chybná testovací domněnka byla opravena na explicitní
`META-INF/orders.xml` jen v unit orders, nikoli změnou produkčního XML kontraktu.

README, `docs/compiler-inspection.md`, `docs/programmatic-queries.md`, fixture
README, progress a acceptance inventory aktualizovány. `inspect code --help`
ověřil aktuální CLI; starý text `inspect jvm` byl na dotčené README ploše opraven.
`--classpath` je opakovatelné `append`. Podporovaný subset byl výslovně zúžen na
`equal`/`eq`, `getResultList`/`fetch`, String/Number Qfactory a select(root).
Nepoužité selectory ani projection-only pole nedávají `filters_by`.

Cílený běh W07 před následujícím where-fixem: **28 PASS /0SKIP /37.23s**.
Není zaměnitelný s pozdějšími výsledky ani dokladem runtime/DB.

## Krok 6 — replacement/clear a neznámá mutace query builderu (AC01, AC03)

Baseline `7bb8b8d389c461c684197704203a99dcb2b83724`. Koordinační source audit
odhalil rozdílný kontrakt CriteriaQuery.where a QueryDSL.where. Actual Javac
reprodukce `test_actual_criteria_where_replaces_querydsl_where_accumulates_and_helpers_are_unknown`
vrátila **FAIL1 /3.05s**: `q.where(statusPredicate); q.where()` chybně zachovalo
status filter. `criteria_queries.py` má nyní oddělený aktuální predicate state:
Criteria nahrazuje/maže, QueryDSL přidává; lokální alias sdílí builder state.
Neznámý helper a escape query state jsou UNKNOWN bez query_reads/filters_by.
Test ověřuje clear, replace status→id, alias clear, helper a QueryDSL accumulation.
Změna nemění již dodané named/JPQL dotazy ani compiler value-flow kontrakty.

Po opravě celá tehdejší W07 sada: **29 PASS /0SKIP /41.07s** stejným cíleným
příkazem z kroku4. Širší cílený běh: **127 PASS +2 setup ERROR /54.91s**.
Dvě vybrané `CompilerWorkerTests` mají společný TS+Maven setup; v izolaci chyběly
připravené artefakty. Nešlo o PASS těchto dvou testů. Explicitně doplněny read-only
symlinky na existující pinned TS dependencies a spuštěn lokální fixture build:
`PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 /tmp/apache-maven-3.9.9/apache-maven-3.9.9/bin/mvn -o -q -f fixtures/build-inspection/maven/pom.xml package -DskipTests`
— **PASS**. Builduje jen testovací fixture, žádná offline analytická cesta.

## Krok 7 — nejednoznačný compiler input (AC01–03)

Baseline `7bb8b8d389c461c684197704203a99dcb2b83724`. Duplicate qualified entity
může způsobit Javac chybu v jiném souboru než query metoda. JavaFrontend nyní
query IR označuje UNAVAILABLE při jakékoli Javac error v selected source setu;
ostatní argument/value/local-operation klasifikace zůstávají beze změny. Actual
duplicate entity test požaduje UNKNOWN a žádný root/filter proof. Je to záměrná
konzervativní hranice; částečně zkompilovaný projekt není W07 COMPLETE.

Matching worker build PASS, lokální JAR SHA256
`a900aea5c213546ac76326f0124fa853cdb5a23c9d62ead069d1487cc9bd426b`.
Následný společný targeted běh níže: **132 PASS /0SKIP /65.13s**; raw
`/tmp/kgmaker-w07-final.xml`, `/tmp/kgmaker-w07-final.log`. Obsahuje30W07 a
návazné named/JPQL/field/inspection/Java binding/ORM/protocol případy.

## Krok 8 — úplnost validace nového IR (AC02, AC03)

Baseline `7bb8b8d389c461c684197704203a99dcb2b83724`. Vlastní adversarial audit
přidal source `binding_ref` identity a malformed `query_ir_status` shape.
První cílený běh `-k 'binding_reference or malformed_status'`: **FAIL2 /3.89s**;
cizí binding ID nebyl odmítnut a status array vyvolalo TypeError místo
INVALID_PROTOCOL. Validator nyní rekonstruuje binding ID ze source/context/hash/
range, kontroluje field symbol vůči deklaraci a validuje status type před
membership testem. Nové pole se tím nemůže vyhnout předpublikační kontrole.
Worker source/JAR se tímto krokem nemění. Následná opakovaná dotčená sada je níže.

## Cílený source/test checkpoint před escape fixem (AC01–04)

Po kroku8: **134 PASS /0FAIL /0SKIP /65.87s**. Z toho32W07, ostatní současné
named-query/JPQL/field/inspection/Java return-binding/ORM/handshake regrese.
Přesný příkaz (výstup `/tmp/kgmaker-w07-final2.log`, JUnit
`/tmp/kgmaker-w07-final2.xml`):

```bash
PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH \
JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 \
KGMAKER_WORKERS_HOME=/tmp/kgmaker-criteria-queries/workers \
KGMAKER_REQUIRE_WORKERS=1 PYTHONPATH=src \
/tmp/kgmaker-test-venv/bin/python -m pytest -q \
  tests/test_criteria_queries.py tests/test_named_query_containers.py \
  tests/test_jpql_hql_grammar.py tests/test_field_mapping_flow.py \
  tests/test_inspection_contract.py \
  'tests/test_return_consumer_flow.py::test_java_branch_returns_assignment_and_chained_receiver[k1]' \
  'tests/test_return_consumer_flow.py::test_actual_java_ir_preserves_both_binding_consumers[k1]' \
  tests/test_compiler_workers.py::CompilerWorkerTests::test_ac06_real_javac_embedded_id_and_association_roles \
  tests/test_compiler_workers.py::CompilerWorkerTests::test_repository_generic_uses_exact_entity_owner_for_same_simple_names \
  tests/test_compiler_workers.py::CompilerWorkerTests::test_protocol_handshakes_are_versioned_and_log_free \
  --junitxml=/tmp/kgmaker-w07-final2.xml --tb=short
```

Další source/test změna je samostatně doložena v kroku10. Worker i
pinned dependencies prošly skutečnou inspekcí a handshake; existence JARu sama
nebyla výsledkem PASS. Žádný full pytest, Kubernetes/DB/JPA provider runtime,
Spring application context, nové Kotlin programmatic queries nebo GH CI nebyly
spuštěny. Bounded Java fixture test není libovolný production-project acceptance.

Aktuální veřejné dokumentační plochy: README, compiler-inspection,
programmatic-queries, fixture README, production-analysis-progress a
acceptance-inventory odkazují na tuto změnu. Registr/spec, init/installed
instructions a Python templates jsou bez dopadu z důvodů uvedených výše.
Příklad: `q.where(statusPredicate); q.where(idPredicate)` dává pouze ID filter;
`q.where()` odstraní všechny filters_by. Dynamické pole zachová známý query root
jen jako PARTIAL intent, žádný smyšlený text či údaj o přítomnosti dat.

## Krok 9 — semantic, aktuální paměť a předání (AC02, AC04)

Baseline `7bb8b8d389c461c684197704203a99dcb2b83724`. Skill kgmaker-semantic:
`semantic update --base 7bb8b8d389c461c684197704203a99dcb2b83724` připravil14changed
paths; relevantní source byl přečten přímo i při oříznutí packet contextu.
První validator správně odmítl starou source snapshot mapu compiler-inspection;
nejde o ztracenou historii. Current packet
`7cb5b82f89d3183d74d9c3f8e5c9eef9020867e46635c9394d884916fb9fc342` obsahuje
14konceptů/74vztahů k apply (13/71 reanchored +1/3 nové). Zachované vztahy mají
stejné evidence/confidence/meaning, pouze aktuální source line/structural ID.
`semantic apply` PASS:49concepts/160edges; `semantic validate` PASS.
Historických48concepts/157edges/310episodes zachováno, žádné unrelated deletion.

První `memory capture --base 7bb... --validation targeted=passed` před scan:
**NOT_CAPTURED**, chybí skutečný pre-task graph.json. Po explicitním current
`scan` (606files,6398declarations) následoval stejný oficiální capture příkaz
s `--validation targeted=passed --validation worker_build=passed`: **PASS**,
episode `6ceb136f3097331f15b348670576ffaa08a6d425d0a80efdde086ae597bb1dd6`.
Tato311. epizoda je CURRENT post-change Git/worktree capture nad prvním současným
indexem. Není pre-task recall ani zpětně vyrobená baseline/delta. Všech310starších
epizod zůstalo přesně stejných. Finální graf je znovu generovaný příkazem scan;
GRAPH.md/mmd nebyly ručně editovány. `git diff --check` PASS.

Číslo129 znovu ověřeno proti main max127 a otevřeným PR (pouze historický draft4
v okamžiku kontroly; W09 má koordinátorem rezervované128). Spec/Task ID beze změny.
PR bude předán ready k nezávislému code_review; implementer jej nemerguje.
Zbývá nezávislé review/merge a mimo scoped DoD celý S06, širší provider/Kotlin
matice, runtime/data proof, full suite a GHCI. Tyto kontroly jsou NOT_RUN.

## Krok 10 — captured/cast/dependency escape před publikací (AC01, AC03)

Baseline stále `7bb8b8d389c461c684197704203a99dcb2b83724`; předešlé134PASS je
samostatný pre-fix checkpoint. Poslední source audit našel chybějící hranici pro
query zachycené do Runnable/lambda nebo skryté unsupported castem. Actual
reprodukce rozšířeného builder-mutation testu: **FAIL1 /3.40s**, zachovala status
filter po `Runnable reset=()->q.where(); reset.run()`.

`criteria_queries.py` nyní označuje query state v captured/referenced compiler
bindings jako escape; nejde o obecný alias resolver. Koordinační audit doplnil
stejnou hranici pro neznámý, byť compiler-resolved dependency call. Pouze
explicitně podporované API je výjimka; `List.of(q).get(0).where()` není známý
query builder kontrakt. Actual test pokrývá closure, cast přes Object, source
helper, dependency wrapper, alias clear a rozlišení Criteria/QueryDSL. Výsledek
escape je UNKNOWN bez root/filter hran. JVM producer/JAR a jiné value-flow
kontrakty se tímto krokem nemění. Nový cílený běh je evidován níže.


Po kroku10 zopakován celý přesný příkaz z předchozího source/test checkpointu,
pouze JUnit cesta nyní `/tmp/kgmaker-w07-final3.xml` a log
`/tmp/kgmaker-w07-final3.log`: **134 PASS /0FAIL /0SKIP /64.98s**. Je to nový
skutečný běh nad finálním zdrojovým stavem, nikoli součet historických výsledků.
Matching JAR nadále `a900aea5c213546ac76326f0124fa853cdb5a23c9d62ead069d1487cc9bd426b`.
Po tomto běhu následují pouze dokumentační/sémantické a Git publikační kroky.

Finální corrective semantic packet `e4df87f82426fae6a5e6d78287497f09b0d73fd2ce4adfa5e0b505cee2cb281c`
reanchored tytéž49concepts/160edges, nic nesmazal. Po current scan nový oficiální
capture přidal epizodu `episode:fc6221f29a12c550e5a43e1b5f97558a15e94641882df50885f8a70c7b37d8e5`;
celkem312epizod. Původních310 je přesně zachováno;311. zůstává historický
pre-escape current checkpoint a poslední je finální corrective current capture.
Obě jsou post-change evidence, nikoli retrospektivní pre-task graf.

## Krok 11 — oprava executable snapshotu po review (AC01, AC03)

T003-S06-W07, implementační kroky1/3/4. Výchozí HEAD
`baaf573c6c5ad8a3ba24141c4a3d668e303be090`, tree
`2c4b8aea2b7b1430f9be71ad2b3f5628206ea68d`; base main zůstává
`7bb8b8d389c461c684197704203a99dcb2b83724`. Nezávislé review PR111
REQUEST_CHANGES odhalilo tři P1 přes čtyři chybné COMPLETE výstupy.
Původních134PASS/64.98s (autor) a134PASS/64.39s (reviewer) byly pravdivé
historické testy, ale nepokrývaly tyto adversarial scénáře. Nové actual testy
`test_actual_review_query_state_and_callable_boundaries` reprodukovaly
**4 FAIL /12.14s**, vždy bez Javac errors; log `/tmp/kgmaker-w07-review-red.log`.
Příkaz byl stejný environment jako krok14, pytest pouze tento test, `--tb=short`.

`criteria_queries.py` nově pořídí samostatnou kopii builder definition při
`EntityManager.createQuery`, takže následné `q.where()` nevymaže status filter
již vytvořeného TypedQuery. Odpovídá
[Jakarta Persistence3.1 §6.9](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1):
pozdější změna Criteria definition neovlivní existující executable dotaz.
QueryDSL fetch obdobně zachytí intent v místě callsite. Dva executable snapshoty
ze stejného builderu v jednom těle se neslijí: každý má vlastní range/witnesses,
oba jsou UNKNOWN s `MULTIPLE_QUERIES_UNSUPPORTED`, bez query_reads/filters_by.
Nejde o nové runtime execution proof. Tests obsahují Criteria clear-after-create,
Criteria opakované create/execution a analogické QueryDSL single/repeated fetch.
Kompatibilita: schema grafu beze změny; queryintent v2 popisuje krok13.
Limity: vícenásobné dotazy nejsou přesně vyřešeny, pouze poctivě ohraničeny.
Ověření: první W07 opravený běh41PASS/57.11s, finální rozšíření v kroku14.

## Krok 12 — neměnná QueryDSL member autorita (AC01, AC03)

T003-S06-W07, implementační kroky3/4, výchozí HEAD `baaf573c6c5ad8a3ba24141c4a3d668e303be090`.
Legal custom Qtype může změnit původní `status` field na
`Expressions.stringPath("unrelated")`; initializer pak není důkaz aktuálního
atributu. `criteria_queries.py` přijímá factory-backed attribute pouze na
compiler memberu s modifierem final. Mutable člen zůstane PARTIAL s
`QUERYDSL_MUTABLE_PATH_UNSUPPORTED` a bez filters_by. Konzervativní hranice platí
i bez viditelného zápisu, takže nespoléhá na lokální sledování všech field writes.
Replay ověřuje final/source/factory dependency identity znovu. Test mění skutečně
vygenerovaný QOrder, odstraní final a provede legal reassignment; zero Javac errors
je explicitní assertion. Pozitivní genuine APT final String/Number cesty zůstávají.
Další dva replay negativy odeberou final nebo změní factory origin na source.
Kompatibilita/omezení: mutable QueryDSL metamodel je mimo podporovaný subset;
žádná nová dostupnost nebo SQL. Ověření: RED je součást4FAIL kroku11, první zelená
matice41PASS a konečný běh v kroku14. Dotčené soubory helper/tests a veřejná matice.

## Krok 13 — skutečný Specification override a bezpečný replay (AC01–03)

T003-S06-W07, implementační kroky2/3/4, výchozí HEAD `baaf573c6c5ad8a3ba24141c4a3d668e303be090`.
Pouhé jméno `toPredicate` na třídě implementující Specification přidělovalo autoritu
nesprávnému dvouargumentovému overloadu. JavaFrontend nyní vydá additive
`query_override` pouze při kladném Javac `Elements.overrides` vůči skutečné
source-absent dependency Specification metodě. Python validator/capture ověří
compiler target owner/name/descriptor, public instance method a generic root;
source `@Override` anotace není požadována. Replay kontroluje tentýž dependency
contract witness a odmítne odstraněný/source-origin contract.
Actual fixture obsahuje pravý tříargumentový override bez anotace i dvouargumentový
overload: pouze první získá query intent. Malformed target/descriptor jsou
INVALID_PROTOCOL bez mutace posledního validního grafu.

Saved intent je nyní `programmatic-query-2`/candidate version2. Staré v1 kandidáty
zůstávají čitelné v grafu, ale nemohou přehrát neopravenou autoritu; explicitní
inspection je obnoví. Body IR zůstává optional strict v1, graph/store1/2/3 a staré
payloady bez query fields fungují dál. Test rehashuje starý candidate version1,
aby rejection nebyla jen následkem integrity mismatch.

Vlastní izolovaný worker rebuild (žádné shared outputs):

```bash
python3 workers/jvm/build.py --kotlin-home /tmp/kgmaker-kotlin-official/kotlinc \
  --maven-repository /home/petra/.m2/repository \
  --java-home /usr/lib/jvm/java-21-openjdk-amd64
```

**PASS**, `/tmp/kgmaker-w07-review-build.log`, matching JAR SHA256
`651468ee0743057ead245e57c2d36cc1b20633655853079a25f33d3bc05cc3fb`.
Pyproject distribuce již zahrnuje všechny `jvm/src/main/java/.../*.java` i lokální
`jvm/target/kgmaker-jvm-worker*.jar`; nový soubor, manifest formát ani dependency
lock nevznikly. Skutečné handshakes/inspection běží nad tímto novým artifactem.
Kotlin K1/K2 programmatic support ani provider/DB runtime se nedeklaruje.

## Krok 14 — cílená korekční acceptance a dokumentace (AC01–04)

T003-S06-W07, implementační krok5; source baseline `baaf573c6c5ad8a3ba24141c4a3d668e303be090`,
base main7bb8b8d ověřen opět přes `git ls-remote`. První sandbox remote lookup
nemohl použít systémový SSH config; stejný read-only příkaz s autorizovaným
network přístupem PASS, main i PR HEAD souhlasily. Root checkout beze změn.

Časové checkpointy se nesčítají:41PASS/57.11s (`review-green`) po prvních opravách;
143PASS/76.94s (`review-final`) před posledními QueryDSL snapshot/replay negativy;
145PASS/84.62s (`review-final2`) před doplněním dvou replay negativů.
Finální přesný příkaz je následující; výsledek a semantic navazují níže.

```bash
PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH \
JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 \
KGMAKER_WORKERS_HOME=/tmp/kgmaker-criteria-queries/workers \
KGMAKER_REQUIRE_WORKERS=1 PYTHONPATH=src \
/tmp/kgmaker-test-venv/bin/python -m pytest -q \
  tests/test_criteria_queries.py tests/test_named_query_containers.py \
  tests/test_jpql_hql_grammar.py tests/test_field_mapping_flow.py \
  tests/test_inspection_contract.py \
  'tests/test_return_consumer_flow.py::test_java_branch_returns_assignment_and_chained_receiver[k1]' \
  'tests/test_return_consumer_flow.py::test_actual_java_ir_preserves_both_binding_consumers[k1]' \
  tests/test_compiler_workers.py::CompilerWorkerTests::test_ac06_real_javac_embedded_id_and_association_roles \
  tests/test_compiler_workers.py::CompilerWorkerTests::test_repository_generic_uses_exact_entity_owner_for_same_simple_names \
  tests/test_compiler_workers.py::CompilerWorkerTests::test_protocol_handshakes_are_versioned_and_log_free \
  --junitxml=/tmp/kgmaker-w07-review-final3.xml --tb=short
```

README, capability/CLI matice programmatic-queries, compiler-inspection, fixture
README, production-analysis-progress a acceptance-inventory reflektují všechny
hranice těchto oprav a odkazují na change129. CLI parametry jsou beze změny;
příklad nadále používá explicitní inspect. Spec/registry identity/revision/deps
jsou beze změny, žádný nový Task ID. Init/installed templates bez dopadu, jejich
chování ani obsah nebyl měněn. dataflow/inspection hooks a cizí W09/T029 moduly
beze změny. Full suite, GH CI, provider/DB/application runtime, další Kotlin
programmatic corpus jsou **NOT_RUN**; cílené testování má výslovnou prioritu.
Zbývá nové nezávislé review aktuálního HEAD, opravy případných nových nálezů a merge
reviewerem; implementer nemerguje.

Finální korekční běh: **147 PASS /0FAIL /0SKIP /85.27s**, z toho45 W07,
log `/tmp/kgmaker-w07-review-final3.log`, JUnit `/tmp/kgmaker-w07-review-final3.xml`.
Obsahuje všech šest actual snapshot/overload/mutable-Qfield scénářů bez Javac
errors, strict IR/replay negativy, staré graph1/2/3 a payloady, scan/hook bez
implicitních procesů, error/timeout/cancel last-valid-store i vybrané
ORM/JPQL/named-query/field/return/worker-protocol regrese. `git diff --check` PASS.
Po tomto běhu se source ani testy nemění; následuje semantic/dokumentace/publikace.

Scoped semantic correction vychází ze skutečného předchozího HEAD baaf573.
Packet `f8b41472bdb539a34b93be40ebdd49e74fefd69b902bb57f53d2140923b93957`
reanchored14 dotčených konceptů/73 vztahů; `semantic apply` a `semantic validate`
**PASS**, celkově49 konceptů/160 vztahů. Programatická kontrola proti baaf573
potvrdila totožné ID/meaning/evidence/confidence všech původních konceptů/vztahů
(pouze aktuální řádky/structural IDs) a přesnou rovnost312 historických epizod.
Oficiální `memory capture --base baaf573c6c5ad8a3ba24141c4a3d668e303be090
--validation targeted=passed --validation worker_build=passed` přidal korekční
epizodu `51c3863a5f5591b94147d34294abaad56e715a8a9b016d2c9d01cd76097a46ef`;
celkem313. Tentokrát existoval skutečný předchozí index a recall před opravou;
nejde o retrospektivní doplnění chybějícího původního pre-task graphu. Po zápisu
tohoto záznamu následuje pouze freshness refresh téhož semantic rozsahu a generovaný
scan, bez ručních změn GRAPH.md/mmd a bez nové source/test změny. Workflow iteration2
obsahuje implementation artifact a přesný actual test receipt, stav review;
nezávislé APPROVE za reviewera vytvořeno nebylo.

Freshness refresh packet `8cab5abf09e294bc7d78be1e9acd47808c6bb1bb8a357360d8a703a91a9df4ca`: apply/validate **PASS**; scan **PASS**,606files/6411declarations. Zachování49/160/312 znovu ověřeno, aktuálně49/160/313. Finální redakční upřesnění směru snapshotu nemění source/test kontrakt; graf se regeneruje po tomto zápisu.

## Krok 15 — ordinary merge skutečného W09 main (AC01–04)

T003-S06-W07, integrační implementační kroky3–5. Výchozí vlastní HEAD
`844c0abce9c68ed747edd0195081b62d12f447b4`, tree
`970bd4b4667f74a2c8c84e3a51999de57813a2c7`. Nový main po PR109 je
`cceb1109df6d88e4f46107f9f9ad12f5e563c0d3`, parents
`7bb8b8d389c461c684197704203a99dcb2b83724` a
`999e60f660c348ece85681440fd14bafff4bd26c`, tree
`0949b95f3e44ad10cf9fa33030a67f6210d7a7b4`. Přesné Git objekty ověřeny po
`git fetch origin main`; integrace použila `git merge --no-commit origin/main`,
bez rebase, force nebo zásahu do root checkoutu. Nezávislý reviewer nad844c
uzavřel všechny3 P1 jako RESOLVED, doložil147PASS/84.88s a správné původní probes;
tento historický výsledek není důkaz nové kombinace.

Source merge byl bez konfliktu. Konflikty byly pouze v generated GRAPH.md/mmd,
semantic.json a sousedních append sekcích compiler-inspection. Dokumentace
zachovává obě capability sekce W07/W09. Grafy regeneruje výhradně CLI scan.
Semantic byl sjednocen podle identity konceptů/vztahů, source reanchored vůči
přesným oběma parentům; společná immutable epizoda musí být identická.
Programatická kontrola prokázala zachování všech49/160/313 z844c i49/167/315
zcceb; union má **50 konceptů/170 vztahů/318 epizod**. Žádné unrelated fakty,
evidence/confidence ani historie nebyly odstraněny. První `semantic validate`
a `scan` PASS (615files/6511declarations); final refresh navazuje po docs.

Byte-identita byla ověřena přímým porovnáním source bytes s `git show` pro:
- W07 `criteria_queries.py`, `framework.py`, `inspection.py`, `JavaFrontend.java`,
  `test_criteria_queries.py` proti844c;
- W09 `analysis_model.py`, `flow.py`, `flow_report.py`, `inspection_cli.py`,
  `views.py`, `workbooks.py`, `test_unified_flow_views.py` proti cceb.

JavaFrontend SHA256 zůstává
`a7be5c10f437a6208d37fa37aeaadf5d65044bd45a65292ff8f3191cbbf161d1`;
matching vlastní lokální JAR z kroku13 má nadále
`651468ee0743057ead245e57c2d36cc1b20633655853079a25f33d3bc05cc3fb`.
Nový rebuild **NOT_RUN (beze změny worker source)**; skutečné aktuální testy
používají tento artifact. Žádný shared target se nepřepisuje. Pro W09 Mermaid
parser byl výslovně připojen ignored read-only symlink z lokálně připraveného
`/home/petra/wrk/tepsivo/kgmaker/tests/rendering/node_modules` do tohoto checkoutu;
verze11.4.1 ověřena. První lookup ve W09 clone připravený parser nenašel,
nejde o test FAIL ani externí blocker. Žádná instalace neběžela implicitně.

Nová cílená integrační matice kombinuje dosavadní W07/ORM/protocol/return checks
s W09 public flow, caller ownership, snapshot publication, provider/workbook a
ranking/CFG/binding kontrolami. Přesný příkaz:

```bash
JAVA_TOOL_OPTIONS=-XX:-UsePerfData \
PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH \
JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 \
KGMAKER_WORKERS_HOME=/tmp/kgmaker-criteria-queries/workers \
KGMAKER_REQUIRE_WORKERS=1 PYTHONPATH=src \
/tmp/kgmaker-test-venv/bin/python -m pytest -q \
  tests/test_criteria_queries.py tests/test_named_query_containers.py \
  tests/test_jpql_hql_grammar.py tests/test_field_mapping_flow.py \
  tests/test_inspection_contract.py \
  'tests/test_return_consumer_flow.py::test_java_branch_returns_assignment_and_chained_receiver[k1]' \
  'tests/test_return_consumer_flow.py::test_actual_java_ir_preserves_both_binding_consumers[k1]' \
  tests/test_compiler_workers.py::CompilerWorkerTests::test_ac06_real_javac_embedded_id_and_association_roles \
  tests/test_compiler_workers.py::CompilerWorkerTests::test_repository_generic_uses_exact_entity_owner_for_same_simple_names \
  tests/test_compiler_workers.py::CompilerWorkerTests::test_protocol_handshakes_are_versioned_and_log_free \
  tests/test_unified_flow_views.py tests/test_control_flow.py \
  tests/test_evidence_ranking.py tests/test_graph_provider.py tests/test_workbooks.py \
  tests/test_argument_parameter_flow.py::test_graph_evidence_roundtrip_and_process_preserve_call_binding \
  tests/test_return_consumer_flow.py::test_process_and_impact_report_static_return_consumer_provenance \
  --junitxml=/tmp/kgmaker-w07-integration-cceb.xml --tb=short
```

Full suite, další Kotlin programmatic/provider/runtime matice a GH CI jsou
**NOT_RUN**. W09 originální chování je beze změny, šíře jeho historical testů se
nepřenáší jako PASS na novou kombinaci. CLI parametry, schema/version a příklady
obou capabilities se integrací nemění. README a compiler-inspection obsahují oba
návody, vlastní programmatic matrix/fixture odkazují na tento krok; relevantní
production/acceptance řádky uvádějí aktuální base a integrační ověření.
Spec/registry/init/templates bez dopadu: identity, závislosti a instalované
instrukce se nemění. Zbývá nové nezávislé review přesného current base/head;
implementer nemerguje.

Výsledek nové kombinované matice: **397 PASS /0FAIL /0SKIP /95.57s**,
raw `/tmp/kgmaker-w07-integration-cceb.log`, JUnit `/tmp/kgmaker-w07-integration-cceb.xml`.
Jde o jeden nový skutečný běh na kombinovaném source stavu, nikoli součet147
a dřívějších W09 výsledků. Testovaný source/test obsah se následně nemění.
`git diff --check` i `git diff --cached --check` PASS; unmerged paths prázdné.

Durable task zůstává iteration2/max3: nový `task advance ... implement` byl
**FAIL (limit další iterace)**, následný implementation record/test advance
odmítnut beze změny historie. Stejně jako dřívější W09 handoff se limit ani
historické artefakty nepřepisují. Skutečná integrační evidence je append-only
orchestrator artifact `37647bd6a8e0a62864883c14f89a9e8f23b1c85a14a03cb116e65fca8711edf5`
ve stávající review fázi. Není to independent APPROVE ani smyšlená implement/test
fáze; všechny provedené příkazy/výsledky jsou výše.

Current integrační semantic packet
`af01d1ecb5b6905a177969181aba86efda8c4ffa65ff0b67a6d304499b78fd70`: apply/validate
**PASS**,50/170/318. Oficiální `memory capture --base cceb1109df6d88e4f46107f9f9ad12f5e563c0d3
--validation integration=passed --validation worker_source_identity=passed`
přidal episode `e77fd586076bcae0328efa4e99471fbf7b12deb923145d00d243a5910066f472`,
celkem319. Je to CURRENT post-merge capture nad skutečným current indexem;
nepředstírá zpětně zachycený pre-task graf. Po tomto zápisu pouze freshness
refresh/validate/scan a Git publikace; nové relation facts se nevymýšlejí.
