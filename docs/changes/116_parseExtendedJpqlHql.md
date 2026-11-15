# T003-S06-W05 — rozšířená JPQL/HQL gramatika

## Zadání a podporovaný rozsah

- Work package: [T003-S06-W05](../tasks/T003-S06-05-jpqlHqlGrammar.md),
  T003-S06 / T003-AC06.
- Výchozí main: `193c89b4d461047fd3330fd74892c5830ba8ac81`.
- PR [#97](https://github.com/p-rum/kgmaker/pull/97); první implementační head
  `1f6f0a9ee63d77d5abb853dd6db057d5b0d15da9`, tree
  `fbc521331a7a68a94768d636f52552917008bfba`.
- JPA rules: `annotation-source-v8-jpql-hql-grammar`; graph/store schema zůstává
  v1/v2/v3 beze změny.

Bounded parser pracuje pouze nad statickou compiler-owned hodnotou Spring Data
`@Query`. Rozlišuje query roots a association joins, subquery reads, bulk
`UPDATE`/`DELETE`, plně kvalifikovanou `select new` DTO projekci a path role pro
SELECT/WHERE/ON/WITH/GROUP/ORDER/SET. Entity, relationship, atribut i DTO musí
ukazovat na jedinou compiler-owned JPA identitu; repository generic ani shoda
simple name není náhradní důkaz.

Hibernate `join ... with` je podporovaný provider extension. `lateral`, direct
entity join mimo association grammar, set/window operace, `treat`, collection
index funkce a insert-select zůstávají PARTIAL s query offsetem, řádkem, sloupcem
a důvodem. Neznámá identita je UNKNOWN. Lexikální chyba, neukončený komentář či
literál nebo nevyvážené závorky nepublikují žádnou query read/write/path hranu.
Jde o statický persistence intent, nikoli runtime SQL, commit nebo data availability.

## Změny a kompatibilita

- `src/kgmaker/framework.py` přidává bounded tokenizer/parser a přesné
  `query_reads`, `query_writes`, `query_deletes`, `joins_by`,
  `projects_attribute`, `filters_by`, `orders_by`, `groups_by`,
  `updates_attribute` a `reads_attribute` hrany.
- Implicitní association traversal přidá read jen pro jednoznačný compiler-owned
  target. Ambiguous alias/entity, unknown path a constructor DTO bez přesné
  identity nevytvoří silnější edge a nastaví `analysis_status=UNKNOWN`.
- Staré v6/v7 snapshoty zůstávají datově čitelné, ale provider vyžádá explicitní
  reinspection. Realm-aware pure projection dál přijímá historické známé stamps;
  neznámý nebo malformed stamp zůstává odmítnutý.
- Native SQL, single named-query definice a v1/v2/v3 loader se nemění. Named query
  containers patří do W06; Criteria/Specification/QueryDSL do W07.

## Skutečné kontroly

- `python -m pytest -q tests/test_jpql_hql_grammar.py`: **5 passed, 1 skipped**.
- Relevantní JPQL/JPA/schema sada: **31 passed, 5 skipped**; skipy jsou explicitní
  nepřipravené compiler/toolchain prerequisite varianty.
- `python -m pytest -q`: **1651 passed, 1058 skipped, 76 subtests passed** za
  45.65 s.
- `test_actual_javac_extended_jpql_fixture`: **SKIP / TOOLCHAIN_UNAVAILABLE**,
  protože JVM worker není v prostředí připraven; nejde o PASS.
- `compileall` a `git diff --check`: PASS. Semantic patch: **42 konceptů /135
  vztahů**; semantic validate: **322 konceptů /30 204 vztahů**; scan/check:
  **547 souborů /6179 uzlů /43 644 vztahů**.

Širší provider-specific HQL, container annotations/XML named queries, dynamic
query builders, execution plan, runtime dispatch a deployment/data availability
zůstávají PARTIAL/UNKNOWN. Celý T003-S06 ani T003 nejsou tímto uzavřené.

## Oprava po review #5907376141

- `T003-S06-W05-S02 / AC01, AC03`: bounded parser nyní odmítá neúplné
  projekce, klauzule a pravé strany porovnání jako `UNKNOWN`; doplněné testy
  nepřipouštějí trailing tokeny ani neúplný bulk DML.
- `T003-S06-W05-S03 / AC01, AC03`: aliasy se porovnávají case-insensitive a
  bindingy jsou vedené po subquery scope s korelovaným lookupem do vnějšího
  scope. Neznámý dotted alias zůstává bez silnější evidence a invaliduje query
  při compiler-owned resolution.
- `T003-S06-W05-S04 / AC01, AC03`: query blocks dostaly stabilní lexical scope
  identity; sibling subqueries tedy mohou znovu použít alias a korelované
  vnější bindingy se zachovají. Doplňující augmented-graph testy pokrývají
  neúplný UPDATE/DELETE/ORDER BY, bare undeclared alias, sibling scopes a
  korelovaný `Customer.id` filter.
- Výchozí baseline tohoto kroku: `6a54640cbd3dc06de2e193df642dea89964364c2`.
- Výchozí opravný head: `878eabc25f3ddb0066213ad00928c4a7b5cfeb76`.
- Kontroly: `PYTHONPATH=src python3 -m pytest -q tests/test_jpql_hql_grammar.py`
  **11 passed, 1 skipped**; relevantní sada
  `tests/test_jpql_hql_grammar.py tests/test_build_aware.py tests/test_compiler_workers.py`
  **16 passed, 16 skipped**; `git diff --check` **PASS**.
- Izolovaný full běh s `PYTHONPATH=src:/tmp/kgmaker-python-test-deps`:
  **1605 passed, 1017 skipped, 44 errors**. Errors jsou environmentální
  toolchain/install prerequisites (Snap Kotlin, chybějící setuptools a externí
  worker artefakty), nikoli fail tohoto work package.
- Celý `PYTHONPATH=src python3 -m pytest -q` **FAIL při collection** kvůli
  nekompatibilnímu lokálnímu `referencing`/Python 3.12 (`TypeError: default is
  an invalid keyword argument for typevar()`); tento výsledek není vydáván jako
  PASS. `PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH
  KGMAKER_WORKERS_HOME=/tmp/kgmaker-review-pr97/workers PYTHONPATH=src python3
  -m pytest -q tests/test_jpql_hql_grammar.py::test_actual_javac_extended_jpql_fixture`
  je **1 passed** proti pinned workeru `sha256=6de50becda4dd0bdb81babf8a638c074a94bac3cb4742bb197c63bfe870d3eae`.

## Ucelená oprava gramatiky po druhém review — 2026-11-15

- Krok `T003-S06-W05-S03`, acceptance `AC01–AC04`, baseline
  `a42a54a2d2b78f034794c261a104b4b5e6e7f1bf`.
- Problém: dílčí blacklisty přijímaly neplatné operátory, neúplné přiřazení,
  neznámé skalární aliasy a prázdné predikáty. Depth-based zpracování navíc
  zaměňovalo běžné závorky za scope a části dotted path za nový alias.
- `src/kgmaker/framework.py`: konzumující recursive-descent gramatika pro
  SELECT/UPDATE/DELETE, pořadí klauzulí, skalární/predikátové výrazy, aritu
  podporovaných funkcí a úplné spotřebování tokenů. Rekurzivní query-block
  scope zachová korelaci, shadowing i nezávislost sibling poddotazů.
  Reference aliasů se ověří před publikací persistence hran. Unsupported
  funkce/provider syntax zůstávají PARTIAL s locatorem; invalidní gramatika
  a nerozvázaný alias jsou UNKNOWN bez read/write/path hran.
- `tests/test_jpql_hql_grammar.py`: všech 10 reprodukcí posledního review bylo
  před změnou **FAIL**; nyní **PASS**. Přibylo 18 kladných/záporných příkladů
  bounded výrazů, funkcí, klauzulí a izolace aliasů.
- Kompatibilita: veřejné CLI/API a graph/store/worker v1/v2/v3 beze změny.
  Reuse stejného JPA pravidla v8 z tohoto dosud nesloučeného PR. Nejde o
  providerovou validaci typů, constructor signature ani runtime SQL.
- README a `docs/compiler-inspection.md` popisují skutečný grammar scope,
  funkce a limity a odkazují sem. CLI příkazy/parametry beze změny: příklad
  `kgmaker query --root app --scope production JPQL PurchaseOrder` platí dál.
  Registr zadání bez dopadu: identita/revize/závislosti se nemění.
  Instalované agent instrukce/templates bez dopadu: nebyly změněny.
- Kontroly: `PYTHONPATH=src:/tmp/kgmaker-python-test-deps python3 -m pytest -q
  tests/test_jpql_hql_grammar.py tests/test_build_aware.py
  tests/test_persistence_realms.py tests/test_schema_compatibility.py
  tests/test_orm_xml_overrides.py tests/test_compiler_workers.py` — **89 PASS /
  70 SKIP**. Samotný W05 corpus s explicitním JDK21 a
  `KGMAKER_WORKERS_HOME=/tmp/kgmaker-review-pr97/workers` — **40 PASS /0 SKIP**,
  včetně actual-javac fixture proti pinned workeru
  `6de50becda4dd0bdb81babf8a638c074a94bac3cb4742bb197c63bfe870d3eae`.
- Izolované Python závislosti v `/tmp/kgmaker-python-test-deps` nahrazují
  chybějící typing_extensions/setuptools; globální prostředí se nemění.
  Celý pytest byl při tomto historickém checkpointu rozpracovaný;
  konečné výsledky a porovnání baseline jsou v závěrečném záznamu níže. GH CI nad lokálními opravami **NOT_RUN**.
- Publikace **BLOCKED**: automatická kontrola zamítla
  `git push origin feat/t003-s06-05-jpql-hql-grammar` kvůli chybějícímu
  výslovnému potvrzení důvěryhodnosti cíle a odeslání. Alternativní cesta
  nebyla použita. PR97 stále obsahuje původní head `878eabc`; lokální opravy
  vyžadují nové nezávislé review i případnou autorizaci push.
- K tomuto checkpointu zbýval konečný receipt a review; viz závěrečný
  záznam níže. W06/W07, další provider syntax a runtime/data dostupnost
  nejsou dodané.

## Kompatibilita entity Order — 2026-11-15

- Krok `T003-S06-W05-S02/S03`, `AC01–AC03`, baseline `f0e5665`.
- První nový úplný běh: **7 FAIL /1894 PASS /752 SKIP /41 ERROR**, 436.28 s,
  log `/tmp/kgmaker-w05-full-final.log`. Není to úspěšná kontrola.
  `Order` bylo chybně odmítnuto jako klíčové slovo v entity-name pozici;
  selhal skutečný T015 JPA integrační test.
- `src/kgmaker/framework.py`: identifikátor entity a segment qualified path
  mohou používat kontextová klíčová slova. Ověření přesného compiler JPA
  owneru zůstává povinné; pravidla aliasů ani klauzulí se neuvolňují.
  `tests/test_jpql_hql_grammar.py` přidává `Order` i `example.Order`.
- Kontrola W05 +
  `tests/test_t015_project_data_resources.py::test_actual_existing_jpa_native_and_entity_query_facts_project_offline[k1]`
  s JDK21/pinned workerem: **41 PASS** před přidáním dvou čistě parserových
  parametrů. Existující T015 skutečný test není nahrazen mockem.
- Stejných sedm selhaných testů nad čistým main `193c89b` se stejným pinned
  workerem a prostředím: **6 FAIL /1 PASS**, 11.29 s. T015 na main prochází;
  zbývají čtyři K2 prerequisite failure a dvě existující Spring injection
  StopIteration. Tyto baseline chyby nejsou tvrzené jako PASS ani jako
  prokázaná chyba našeho parseru. Log `/tmp/kgmaker-w05-main-fail-comparison.log`.
- ERROR skupina prvního běhu obsahuje chybějící externí HTTP capture
  `/workspace/t011-validation/captured-k1.json` a offline wheel prerequisite
  `pkg_resources`. Ta byla doplněna ze systémové knihovny pouze do `/tmp`;
  nový celý pytest nad opraveným runtime je popsán v závěrečném záznamu.
- Kompatibilita schémat/CLI beze změny; README/capability limity gramatiky
  platí, registr a instalované instrukce bez dopadu. Publikace nadále BLOCKED.


## Lokální ověření před novým souhlasem uživatele — 2026-11-15

- Krok `T003-S06-W05-S05`, `AC01–AC04`; runtime commit
  `1dcf9ff24b549b2c5ae240ee6ff7c855cfb86053`, base PR
  `193c89b4d461047fd3330fd74892c5830ba8ac81`. Finální metadata commit nemění
  runtime; SHA256 souborů framework.py a corpus byl před/po kontrolách shodný.
- Nezávislé code review tohoto runtime: bez otevřeného nálezu. Reviewer
  provedl **42 PASS /0 SKIP** včetně skutečného připnutého workeru s
  `KGMAKER_REQUIRE_WORKERS=1` a původní T015 actual JPA kontrolu **1 PASS**.
  Celkový T045 verdikt je **BLOCKED**, nikoli APPROVE pro merge.
- Finální širší kontrola s explicitním JDK21, `KGMAKER_WORKERS_HOME` a
  izolovanými Python deps: **130 PASS /32 SKIP** za 51.06 s. Příkaz:
  `python3 -m pytest -q tests/test_jpql_hql_grammar.py tests/test_build_aware.py
  tests/test_persistence_realms.py tests/test_schema_compatibility.py
  tests/test_orm_xml_overrides.py tests/test_compiler_workers.py
  'tests/test_t015_project_data_resources.py::test_actual_existing_jpa_native_and_entity_query_facts_project_offline[k1]'`.
  Log `/tmp/kgmaker-w05-jpa-final.log`. SKIP nepokrývá nepřipravené K2/Maven
  fixture prerequisites a není PASS.
- Finální úplný běh:
  `PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:/home/petra/.pyenv/versions/3.12.0/bin:/usr/local/bin:/usr/bin:/bin
  PYTHONPATH=src:/tmp/kgmaker-python-test-deps GRADLE_USER_HOME=/tmp/kgmaker-gradle-home
  python3 -m pytest -q` — **FAIL: 6 failed, 1897 passed, 752 skipped, 41 errors**,
  425.70 s. Log `/tmp/kgmaker-w05-full-soft-keywords.log`.
  Kód/testy zůstaly obsahově shodné s uvedeným runtime commitem.
- Šest FAIL je stejných jako v doloženém srovnání s main: čtyři chybějící K2
  worker varianty v dependency-dispatch testech a dvě existující Spring
  injection StopIteration. Původní sedmá chyba T015 `Order` je opravena.
  ERROR zahrnují chybějící externí `/workspace/t011-validation/captured-k1.json`
  a nekompatibilní systémový setuptools v offline wheel buildu
  (`AttributeError: install_layout`). Tyto prerequisites/baseline chyby nejsou
  dodané ani vydávané za PASS; celý povinný test gate zůstává nesplněný.
- JDK: OpenJDK/javac `21.0.13.0.3`. Pinned worker byl sestaven explicitně
  přes `workers/jvm/build.py` z checksumově ověřených lock dependencies;
  `kotlin-reflect-2.1.10` SHA256
  `d019d3d615f3e55a2ea1299b619c26a73e227b250376e529aea1e1adbc65a4e4`.
  Žádné implicitní buildy/instalace v scan/hook cestě nepřibyly.
- `compileall` a `git diff --check`: **PASS**. Scoped semantic update/apply
  obnovil 13 existujících konceptů /70 vztahů a přesné declaration ID po
  posunu řádků; nepřidal nedoložené vazby. `semantic validate`, validovaná
  implementation memory a generovaný `scan/check` jsou součástí finálního
  lokálního receipt. Při neúspěchu by předání zůstalo BLOCKED.
- Dokumentace: README, compiler guide, acceptance inventory a stavová matice
  odkazují na tento záznam; příkazy/schema ani instalované instrukce/templates
  se nemění. Registr zadání bez dopadu (stejné ID/revize/dependencies).
- PR97 zůstává otevřený na publikovaném headu `878eabc25f3ddb0066213ad00928c4a7b5cfeb76`.
  Lokální opravy nebyly pushnuty: automatická bezpečnostní kontrola zamítla
  odeslání obsahu do `github.com/p-rum/kgmaker`, protože podle ní chybí výslovné
  potvrzení důvěryhodnosti cíle a tohoto egressu. Vyžaduje informovaný souhlas
  uživatele; jiná cesta nebyla použita. GH CI nových lokálních oprav **NOT_RUN**.
- Zbývající práce: připravit chybějící capture/toolchain/packaging prostředí,
  vyřešit baseline Spring testy a získat úspěšné povinné kontroly; autorizovaně
  publikovat opravy a znovu provést exact-pair review před případným merge.
  W06/W07, další provider syntax a runtime/data dostupnost zůstávají mimo dodávku.


## Autorizovaná publikace oprav — 2026-11-15

- Krok `T003-S06-W05-S05`, `AC04`; výchozí lokální SHA
  `7369e2d29b7522f990c9056cf840d6a1be4dc354`.
- Uživatel po vysvětlení důvodu zamítnutí výslovně schválil push, PR,
  nové review a podmíněný merge po schválení. Předchozí push BLOCKED byl
  historický stav před tímto souhlasem; nejde již o chybějící autorizaci.
- HTTPS CLI push **FAIL** kvůli chybějícím přihlašovacím údajům. Následný
  autorizovaný SSH push stejného commitu bez force **PASS**:
  `git -c core.sshCommand='ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=15'
  push git@github.com:p-rum/kgmaker.git HEAD:refs/heads/feat/t003-s06-05-jpql-hql-grammar`.
  GitHub read-back potvrdil head `7369e2d`, base `193c89b`, ready/open/unmerged.
- Aktualizuje se existující [PR97](https://github.com/p-rum/kgmaker/pull/97),
  duplicitní PR nevzniká. Dokumentační publikace nemění runtime ani testy;
  ověřené runtime SHA zůstává `1dcf9ff`. Code review bez nálezu nenahrazuje
  nesplněnou úplnou sadu **FAIL: 1897 PASS /752 SKIP /6 FAIL /41 ERROR**.
- README, compiler guide, CLI/API, schémata, templates a registr zadání:
  bez dopadu, protože jde pouze o stav publikace. Acceptance inventory a
  stavová matice odstraňují již neplatnou aktuální push blokaci. Scope,
  podporované varianty a omezení se nemění.
- Kontroly tohoto metadata kroku: shodnost `src/`, `tests/`, `workers/`
  vůči `1dcf9ff`, `git diff --check`, scoped semantic validate a generovaný
  scan/check; finální výsledky se ověřují před předáním reviewerovi.
  Nový plný pytest se neopakuje kvůli metadata změně. GH CI se ověřuje
  samostatně nad publikovaným headem; bez nového výsledku je NOT_RUN.
- Zbývá nové nezávislé review přesného publikovaného base/head. Merge je
  povolen pouze po APPROVE a všech ostatních povinných kontrolách; aktuální
  full-suite FAIL nadále blokuje merge. T003-S06 tím není uzavřen.
