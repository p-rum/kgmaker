# NamedQueries a named native queries

Datum: 2026-11-15; Task `T003-S06-W06`, kroky `T003-S06-W06-S01` až `S03`, acceptance `T003-S06-W06-AC01` až `AC04`.
Výchozí SHA: `14d7f7cefab2fa5c9cf8c6d939d3b92e838faea8`.

Následující první čtyři sekce zachovávají historický stav commitů před
`06b20a9109f93ed89b17a4602add6354164fc9d6`; tehdejší 17/18 PASS s 20 SKIP
nedokládaly veřejné reference ani actual JVM containers. Aktuální oprava a
výsledky jsou v navazujících sekcích níže.

## Historický dílčí stav S01 — XML deklarace a společný katalog

Problémem byla absence deklarací `named-query` a `named-native-query` z ORM XML
v existujícím katalogu JPA named queries. `src/kgmaker/framework.py` nyní čte
kořenové XML deklarace v omezeném, hashovaném vstupu, zachovává jazyk JPQL nebo
NATIVE_SQL a jejich původ. Deklarace se připojují ke stejnému katalogu jako
anotační `@NamedQuery`; nevytváří se paralelní model ani se nespouští provider.

## Historický dílčí stav S02 — fail-closed duplicity a neúplné vstupy

Prázdné jméno nebo tělo vytváří `ORM_XML_NAMED_QUERY_UNRESOLVED`. Duplicitní XML
jména a kolize s anotační deklarací vytvářejí `ORM_XML_NAMED_QUERY_AMBIGUOUS` a
nevyberou jednu definici. Tím se zachovává UNKNOWN/PARTIAL důkazní vrstva a
nulová mutace při chybě.

## Historický dílčí stav S03 — testy a dokumentace

`tests/test_named_query_containers.py` pokrývá oba jazyky, provenance, duplicitu
a chybějící tělo. `docs/acceptance-inventory.md` a
`docs/production-analysis-progress.md` uvádějí přesný rozsah. README, CLI a
capability API nemají dopad: jde o interní compiler projection bez nového příkazu.

Kontroly:

- `PYTHONPATH=src pytest -q tests/test_named_query_containers.py tests/test_orm_xml_overrides.py`: **PASS, 17 passed, 20 skipped**; skip jsou existující toolchain-dependent XML worker scénáře.
- `python -m compileall -q src/kgmaker/framework.py`: **PASS**.
- `git diff --check`: **PASS**.
- Skutečný JVM/compiler provider fixture: **NOT_RUN** (worker/toolchain není v tomto izolovaném běhu připraven); není vydáván za PASS.

Kompatibilita: staré anotační named queries, v1/v2/v3 graph identity a XML
precedence zůstávají čitelné. Omezení: XML named query se zatím nepropojuje na
entity bez jednoznačného compiler důkazu; runtime SQL/provider semantics,
Criteria/Specification/QueryDSL a plná produkční matice zůstávají mimo rozsah.

## Historická oprava S02 — repeatable containers a kolize neúplných jmen

Anotační `@NamedQueries` a `@NamedNativeQueries` se nyní rozbalují do stejného
katalogu jako jednotlivé anotace. XML jméno se označí jako nejednoznačné i tehdy,
když jedna z jeho duplicitních deklarací nemá tělo; platná deklarace tedy nemůže
umlčet chybný protějšek. README popisuje veřejně viditelnou rozšířenou projekci.

Dodatečný cílený test `test_xml_incomplete_duplicate_name_cannot_fall_back_to_valid_definition`
je PASS; opakovaná sada nyní hlásí **18 passed, 20 skipped**. JVM actual fixture
zůstává NOT_RUN: `fixtures/build-inspection` není v tomto repozitářovém checkoutu
přítomná ani po nastavení připraveného worker home.

## Dokončení po kontrole veřejného průchodu — 2026-11-15

Výchozí SHA všech následujících kroků:
`06b20a9109f93ed89b17a4602add6354164fc9d6` (base PR
`14d7f7cefab2fa5c9cf8c6d939d3b92e838faea8`). Dodání: **IN_PROGRESS** při lokálním
předání orchestrátorovi, který zajistí publikaci, nezávislé review a merge.
Ověření: **VERIFIED_IN_SCOPE** níže; nejde o dokončení celého T003-S06.

### T003-S06-W06-S01 — rekognoskace (AC01, AC03, AC04)

Přímá kontrola dle `kgmaker-architect` a `kgmaker-context` přečetla uložené
GRAPH/NOTES, framework, inspection/store kontrakt a existující XML/JPQL testy.
`status`, `query` a `memory recall` ohlásily chybějící čitelný index; nebyl
obnovován kvůli čtení compiler evidence. Nebyl dodán žádný externí workspace ani
Flyway stream, žádná migrace ani databáze se nespouštěla. Zdroje potvrdily chyby:
Javac nested mirror je string místo očekávaného dict; katalog přepisoval
anotační duplicity; named reference přeskočila parametry/gramatiku/projekce;
definice chybně četla vlastníka anotace bez ohledu na query body.
Kontrola zdroje **PASS**; původní claim celé AC01 **FAIL**. S01 nemění veřejné API.

### T003-S06-W06-S02 — kompatibilní katalog a decoder (AC01, AC02, AC03)

`src/kgmaker/named_queries.py` normalizuje compiler-owned Javac nested strings
(včetně Java escapes) i strukturované name/values records. `framework.py`
seskupí všechny kandidáty a teprve potom publikuje jednoznačné definice.
Trojitá duplicita ani validní záznam za neúplným protějškem neobnoví binding.
Neplatné `values_resolved=false` nadřazeného containeru zablokuje i jeho vnořené
deklarace. Platí kanonická Jakarta/Javax identita, compiler context, vybraný persistence
unit, `metadata-complete` a `exclude-unlisted-classes`. XML přijímá root i
entity/mapped-superclass named query, právě jedno textové tělo a přesného
compiler vlastníka. Kolize XML/anotace je unresolved.

Schema grafu/store zůstává 3, worker protocol se nemění. V1/v2/v3 grafy jsou
čitelné; nové metadata jsou aditivní. Rule v9 zneplatňuje starou framework
projekci pro nové použití, aniž starou evidenci přejmenuje na čerstvou.
Kontroly normalizace, duplicity, identity a v1/v2/v3 roundtrip jsou **PASS** v
cílené sadě níže. Omezení: bounded compiler records, žádné regex odhadování
container anotací z nevyřešeného zdroje.

### T003-S06-W06-S03 — veřejné reference a query evidence (AC01, AC03)

`framework.py` vede `@Query(name=...)` přes existující JPQL/native analýzu.
`uses_named_query` má context/evidence a u XML hashovanou provenance. Named
reference nese named i positional parametry, nevyřešené vazby, návratový typ,
DTO constructor projection a native `resultClass`/XML `result-class`.
Parametry v literálech/komentářích se ignorují. Neexistující nebo duplicitní
jméno má UNKNOWN bez odchozích query hran; malformed JPQL nemá read/write/path
hrany. Vlastník definice sám není důkazem čtené entity. Native table binding se
provádí až po XML overrides, aby nevznikala vazba na odstraněnou annotation tabulku.
Neznámý result-set mapping je PARTIAL s lokalizovanou diagnostikou.

Kontroly veřejného grafu, skutečného Javac, finálního XML názvu tabulky,
parametrů a projekcí jsou **PASS**. SOURCE_ONLY scanner (`domain.py`) je **bez
dopadu**: nové FRAMEWORK_DERIVED vztahy vznikají pouze z explicitní inspection;
scanner nezískává compiler/runtime oprávnění. `@Param` aliasy, implicitní
repository naming convention, dynamický EntityManager a provider SQL/result-set
interpretace zůstávají mimo tento bounded kontrakt; statická evidence neprokazuje
runtime provedení ani data availability.

### T003-S06-W06-S04 — fixture a chybové publikace (AC01, AC02, AC03)

`fixtures/named-queries/Model.java`, `orm.xml` a README jsou reprodukovatelná
fixture. `tests/test_named_query_containers.py` přidá izolované API stubs a
skutečně volá JVM worker/Javac. Pokrývá jednotlivé i repeatable anotace a
explicitní kontejnery, JPQL/native/XML, parametry, DTO, trojité duplicity,
chybějící jméno/tělo, malformed JPQL/XML a foreign compiler/JPA vlastníka.
Dva publikované persistence kontexty prokazují, že chybějící query nepřebírá
stejné jméno z druhého realm. Strict odmítnutí, cancellation a skutečný timeout
zachovají původní `graph.json` byte-for-byte. Pure projection nemutuje vstup;
offline scan/hook pod zákazem `subprocess.Popen` zachovávají named bindings.
`tests/test_jpql_hql_grammar.py` ověřuje i stale rule v8. Všechny tyto kontroly
jsou **PASS**; fixture je compiler evidence, nikoli JPA runtime/provider test.

### T003-S06-W06-S05 — dokumentace a předání (AC04)

Aktualizované plochy: [README](../../README.md),
[capability a CLI příklad](../compiler-inspection.md#named-query-containers-t003-s06-w06),
[stavová matice](../production-analysis-progress.md),
[acceptance](../acceptance-inventory.md#t003-s06-w06--namedqueries-a-named-native-queries-in_progress--verified_in_scope)
a tento change note. Registr `docs/tasks/README.md` je **bez dopadu**: identita,
revize, závislosti a odkaz zadání zůstávají stejné. Instalované agent instrukce,
Python templates a CLI parser jsou **bez dopadu**: nový příkaz ani přepínač
nevzniká. Historické výsledky výše jsou výslovně oddělené od aktuálního důkazu.
Žádný sémantický vztah nebyl vymyšlen; strukturální vazby generuje scanner.

### Přesné provedené kontroly

Worker byl již explicitně připraven před tímto krokem; žádná instalace/build
aplikace se implicitně nespouštěla. `javac -version`: **21.0.13.0.3**.
Worker `/tmp/kgmaker-pr97-reconciled/workers/jvm/target/kgmaker-jvm-worker.jar`,
SHA256 `6de50becda4dd0bdb81babf8a638c074a94bac3cb4742bb197c63bfe870d3eae`.
Existující XML testy používají explicitní checkout workers home; ignorovaný
`workers/jvm/target` symlink odkazuje na tuto stejnou distribuci.

```bash
PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH \
JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 \
KGMAKER_REQUIRE_WORKERS=1 \
KGMAKER_WORKERS_HOME=/tmp/kgmaker-pr97-reconciled/workers \
PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest -q --tb=short \
  tests/test_named_query_containers.py \
  tests/test_orm_xml_overrides.py tests/test_jpql_hql_grammar.py
```

Výsledek před nezávislým review nad `f6a8934`: **PASS, 91 passed, 0 skipped** (26.56 s; finální opakování po kontrole unresolved container values). Předchozí aktuální
cílený běh: **90 PASS, 0 SKIP** (26.89 s), před doplněním explicitní stale-v8 varianty
a rozšířením actual fixture o jednotlivé legacy anotace.

Full suite: **NOT_RUN**, podle výslovného zadání pouze cílené testy. GitHub CI:
**NOT_RUN**, lokální agent nepublikuje PR. Samostatný actual Kotlin named-container
corpus a runtime/provider/DB: **NOT_RUN**, nejsou vydávány za PASS.

Příklad: `@NamedQueries({@NamedQuery(name="Order.byStatus", query="select o from
Order o where o.status=:status")})` + `@Query(name="Order.byStatus")` se správným
compiler parametrem `status` vytvoří jednu reference edge a ověřené statické
parametry. Druhá deklarace stejného jména, i s prázdným tělem, reference edge
odstraní a vrátí UNKNOWN. Zbývající práce při předání: zveřejnit samostatný PR,
nezávisle zkontrolovat aktuální base/head a provést autorizovaný merge.

Další kontroly: `git diff --check` **PASS**; `PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m compileall -q src/kgmaker/framework.py src/kgmaker/named_queries.py` **PASS**. `kgmaker memory capture --base 06b20a9109f93ed89b17a4602add6354164fc9d6 --validation named-query-targeted=passed` nemohl zachytit epizodu: chybí čitelný pre-task graph (**NOT_RUN**, žádná epizoda nebyla vymyšlena).

`kgmaker scan --no-docs` **PASS**: 564 souborů, 5797 deklarací/sekcí, 42770
vztahů; aktualizoval lokální machine index bez přepisování historického Markdown
grafu. `semantic update --base 06b20a9109f93ed89b17a4602add6354164fc9d6
--token-budget 1600` připravil aktuální packet. Scanner vynechal 70 starších
semantic vztahů s odstraněnými/stale uzly a stale evidence v README,
compiler dokumentaci a JPQL testu. Tyto vztahy nejsou novým důkazem W06;
nesouvisející semantic katalog se nepřepisuje a nebyl aplikován spekulativní patch.
Případná obnova historických semantic vazeb je oddělená práce. Lokální workflow
`task:0e778f28d69603b6e963871d1309fb8ce7321bcc2265afcdf1d5397c7f6cfbe2`
uchovává retrospektivní rekognoskaci/plán, skutečnou implementaci a výsledek testů;
nezávislé review do něj implementační agent nepředstírá.


## Oprava T003-S06-W06-S03 po nezávislém review — AC03 (2026-11-15)

Baseline: `f6a8934adc1e69631dbd74b7592668a92129983b`, review nad base
`14d7f7cefab2fa5c9cf8c6d939d3b92e838faea8`: **REQUEST_CHANGES**, dva P1 nálezy.
Dosavadních 91 PASS neodhalilo, že raw native SQL regex považoval text v
literálu/komentáři za tabulku a že úvodní komentář klasifikoval UPDATE jako READ.

Skutečné změny: `src/kgmaker/named_queries.py` obsahuje společnou lexikální
masku parametrů a native textu. Standardní quoted spans a komentáře nejsou
zdrojem table names; neuzavřené a dialect-dependent quoting zůstává unknown.
`framework.py` určuje native operaci z prvního skutečného statement keywordu
za komentáři a hledá tabulky v maskovaném textu. Bez podporovaného statementu,
lexikálně úplného vstupu a unquoted table reference vydá lokalizovanou
`NATIVE_QUERY_STRUCTURE_UNRESOLVED`, `validated=false`, UNKNOWN a žádnou
query read/write/delete hranu. Přímé `@Query` uchovává compiler string celou,
včetně apostrofů, takže využívá stejnou bezpečnou cestu jako named reference.
Jde o lexikální hranici existujícího native subsetu, nikoli nový SQL parser.

Regrese: `tests/test_named_query_containers.py` přes veřejný graf porovnává
named reference a inline queries pro literály, zdvojené SQL apostrofy, řádkové
/blokové komentáře, neúplné delimitery, cizí názvy tabulek v non-code textu,
leading literal a komentované UPDATE/DELETE. `fixtures/named-queries/Model.java`
přidává actual Javac literal-only/comment-only negativy a komentované DML.
Fixture README popisuje tyto případy. Aktualizované uživatelské plochy:
README, capability/CLI dokumentace, production progress a acceptance inventář.
CLI syntaxe, task registry, graph schema, worker protocol a installed templates
jsou **bez dopadu**; veřejný rozsah a důkazní limity jsou zpřesněny.

Příklad: `select 'from orders'` ani `select 1 /* from orders */` nevytváří
`query_reads`; `/* audit */ update orders set status='x'` vytváří pouze
`query_writes` na skutečnou tabulku. `-- audit` před DELETE obdobně zachová
`query_deletes`. Scalar-only SELECT a quoted table names zůstávají mimo bounded
table binding. Runtime/provider dostupnost ani široká SQL grammar nejsou tvrzeny.

Kontroly po opravě: cílený public regression běh před přidáním leading-literal
varianty **PASS, 20 passed / 13 deselected**, příkaz
`PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest -q --tb=short tests/test_named_query_containers.py -k lexical_boundaries`.
Finální cílená sada používá stejný přesný JDK/worker příkaz výše:
**PASS, 117 passed / 0 skipped, 26.87 s** (včetně quoted-identifier negativů).
Předchozí meziběh **113 PASS / 0 SKIP, 27.12 s** je historický.
`git diff --check` a `compileall` pro oba změněné Python moduly: **PASS**.
`memory capture --base f6a8934adc1e69631dbd74b7592668a92129983b
--validation named-query-review113=passed`: epizoda nevznikla (**NOT_RUN**),
protože starší semantic node22 má stale compiler-documentation evidence.
Aktuální `semantic update --base f6a8934adc1e69631dbd74b7592668a92129983b
--token-budget 1200` připravil10 změněných cest; žádný spekulativní semantic
patch nebyl aplikován. Následný lokální `scan --no-docs` obnovuje machine index. Full suite a GitHub CI: **NOT_RUN** podle rozsahu pověření.
Zbývá nezávislé opakované review aktuálního HEAD, případná integrace nového main a publikace
orchestrátorem; oprava sama nepředstírá APPROVE ani merge.
