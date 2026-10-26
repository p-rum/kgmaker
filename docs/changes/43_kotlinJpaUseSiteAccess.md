# Změna 43: Kotlin JPA use-site a access

T003-S06-W01 doplňuje stávající JPA projekci o Kotlin constructor properties a
K2 `@field:`/`@get:` targety. Worker používá K2 annotation identity/constant
facts a JVM light field/getter typy; frameworková vrstva tak vybírá FIELD nebo
PROPERTY jen z jednoznačného `@Id`/`@EmbeddedId` targetu nebo explicitního
`@Access`. Změna nepřidává graph typ ani nemění JPA rules `annotation-source-v4`.

Nejednoznačné constructor `@Id`, foreign anotace se stejným short name a
konflikt mezi explicitním `@Access` a identity targetem nevytvoří nesprávný
persistent attribute. Nevyřešená nebo částečně vyřešená explicitní hodnota
`@Table`, `@Column` či `@AttributeOverride` nevytvoří výchozí fyzické mapování;
diagnostika zachová hranici neznámého. Vnořený `@Column` v reálném
`@AttributeOverride` a class literal se serializují z compiler values; pole
array hodnot se nepovažuje za úplné, pokud je některý člen nevyřešen. Konstantní
annotation argumenty se čtou jako compiler values; import aliasy zachovávají
FQ identity. Pole/getter a typy pocházejí z Kotlin JVM light PSI, takže
importované typy nevznikají odhadem z package aktuálního zdroje. Fixture používá
JPA `@Id`/`@EmbeddedId`/`@Column` cíle FIELD/METHOD, ověřuje implicitní FIELD
default a samostatnou nejednoznačnost `@field:` plus `@get:`.
Nevyřešené explicitní `@Access` nedovolí odvodit přístup z identity placementu;
neznámá tabulka s odpovídajícím schema column zůstává bezpečně bez dereference
či fyzického bindingu. Embeddable member annotations jsou filtrovány podle
Jakarta/Javax FQ identity. Implicitní embeddable access se vyhodnocuje přes
všechny container usage sites; jen jednoznačný FIELD inheritance může ponechat
field default, zatímco PROPERTY, mixed, chybějící nebo nevyřešený přístup zůstává
UNKNOWN.
Namespace checks require a known annotation name directly in
`jakarta.persistence` or `javax.persistence`; aliased annotations in
`jakarta.persistence.fake` cannot impersonate `@Entity`, `@Id`, or `@Column`.

Přímá acceptance evidence:

- **AC01:** `tests/test_k2_backend.py::test_k2_jpa_use_site_access_and_ambiguity_are_compiler_attributed` ověřuje skutečný K2 worker, `@field:EmbeddedId`, `@get:Id`, explicitní PROPERTY access, implicitní FIELD, skutečnou `@field:` + `@get:` nejednoznačnost, mismatched targets, foreign `fake.Id`/`fake.Column` i aliased `jakarta.persistence.fake.Id/Column/Entity`, import alias, `const val` column name, nested `@AttributeOverride`, class literal, importovaný `java.time.Instant` a Kotlin `@Embeddable` column v FIELD, PROPERTY a mixed-container scope.
- **AC02:** Stejný fixture ověřuje existující `orm_attribute`/`orm_embeddable` projection; Java JPA regression `tests/test_build_aware.py::BuildAwareContractsTest::test_hb01_embedded_id_and_bidirectional_association_preserve_roles` zůstává zelená.
- **AC03:** Nejednoznačný, foreign a konfliktní identity target nevytvoří `orm_attribute`; nevyřešené explicitní `@Table`/`@Column` nevydávají default fyzické názvy, ani když existuje odpovídající schema column; nevyřešené `@Access` nevytvoří atributy z identity placementu; nepodložený či mixed embeddable access nevydá field/getter column binding. Přísné selhání a zachování uloženého grafu nadále ověřuje `tests/test_k2_backend.py::test_k2_store_refresh_is_offline_and_strict_failure_preserves_graph`.
- **AC04:** Stav zůstává PARTIAL; zbývající K2 execution model, XML override a širší persistence rozsah se tím neuzavírají.

Ověření v izolovaném worktree `/workspace/s06-jpa`:

```text
python workers/jvm/build.py --backend k2 --kotlin-home /workspace/tools/kotlinc --maven-repository /workspace/tools/m2 --java-home /workspace/tools/jdk-21.0.6+7 --analysis-api-home /workspace/tools/k2
# SUCCESS; worker SHA-256 1be4e94b8fe6ef0d902955c8a8c8cbbc9c86f90f3a686053bac3b54abc0a777a

JAVA_HOME=/workspace/tools/jdk-21.0.6+7 PATH=/workspace/tools/jdk-21.0.6+7/bin:$PATH PYTHONPATH=src KGMAKER_REQUIRE_K2=1 /workspace/kgmaker-venv/bin/python -m pytest -q tests/test_k2_backend.py::test_k2_jpa_use_site_access_and_ambiguity_are_compiler_attributed tests/test_build_aware.py::BuildAwareContractsTest::test_hb01_embedded_id_and_bidirectional_association_preserve_roles
# 2 passed

flock /workspace/kgmaker-heavy-tests.lock env JAVA_HOME=/workspace/tools/jdk-21.0.6+7 PATH=/workspace/tools/jdk-21.0.6+7/bin:$PATH PYTHONPATH=src KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 /workspace/kgmaker-venv/bin/python -m pytest -q
# 379 passed, 9 skipped in 144.12s (final suite after canonical JPA package guard)
```

Bounded follow-up verification after the final fail-closed compiler-value fix:

```text
python workers/jvm/build.py --backend k2 --kotlin-home /workspace/tools/kotlinc --maven-repository /workspace/tools/m2 --java-home /workspace/tools/jdk-21.0.6+7 --analysis-api-home /workspace/tools/k2
# SUCCESS; worker SHA-256 1be4e94b8fe6ef0d902955c8a8c8cbbc9c86f90f3a686053bac3b54abc0a777a

JAVA_HOME=/workspace/tools/jdk-21.0.6+7 PATH=/workspace/tools/jdk-21.0.6+7/bin:$PATH PYTHONPATH=src KGMAKER_REQUIRE_K2=1 /workspace/kgmaker-venv/bin/python -m pytest -q tests/test_k2_backend.py tests/test_build_aware.py
# 36 passed
```

The 36-test focused suite above predates the canonical-package guard. The final
full suite above ran after that guard and the aliased subpackage regression were
added.

Final inherited-embeddable access review added a PROPERTY container, a FIELD
container sharing the same key type, and a GET-only embeddable annotation. The
latest actual K2 fixture and Java embedded-ID regression were rerun together:

```text
JAVA_HOME=/workspace/tools/jdk-21.0.6+7 PATH=/workspace/tools/jdk-21.0.6+7/bin:$PATH PYTHONPATH=src KGMAKER_REQUIRE_K2=1 /workspace/kgmaker-venv/bin/python -m pytest -q tests/test_k2_backend.py::test_k2_jpa_use_site_access_and_ambiguity_are_compiler_attributed tests/test_build_aware.py::BuildAwareContractsTest::test_hb01_embedded_id_and_bidirectional_association_preserve_roles
# 2 passed
```

The final compatibility rerun also enabled the unchanged, byte-verified Maven
fixture and K1/TypeScript worker resources from the prepared local worktree. It
ran the actual Javac JPA fixture (not the source-level projection only):

```text
JAVA_HOME=/workspace/tools/jdk-21.0.6+7 PATH=/workspace/tools/jdk-21.0.6+7/bin:$PATH PYTHONPATH=src KGMAKER_REQUIRE_WORKERS=1 /workspace/kgmaker-venv/bin/python -m pytest -q tests/test_compiler_workers.py::CompilerWorkerTests::test_ac06_real_javac_embedded_id_and_association_roles tests/test_k2_backend.py::test_k2_jpa_use_site_access_and_ambiguity_are_compiler_attributed
# 2 passed
```

The worker was built explicitly from the pinned local compiler/dependency set;
the Maven fixture was copied byte-identically without rebuilding. No application
build, migration, database access, install or external publication was
performed. K2 general source CFG, constructor ABI, Spring metadata and non-JPA
property execution remain outside this package.

Semantic maintenance initially used `semantic update --base eff0d3d5d7620b017fe42a65a54f672af8068667`, a scoped patch with update ID
`7026f91390828803a276b29c7bf204261c160dc00c6e1306b6f3dc43166f1aae`,
`semantic apply`, and `semantic validate` (**PASS**). The update refreshes the
README citation and records compiler annotation facts → JPA projection → real
compiler fixture links. Memory capture recorded the original implementation
episode `episode:075463522afbeba788927e1d945c0d088a28ceda090e1df7c386ea33a0600210`.
The follow-up refreshed the affected semantic entries for nested annotation
values, fail-closed JPA mappings, embeddable access, the canonical JPA package
guard, and actual Javac/K2 tests.
`semantic apply`, `semantic validate`, final `kgmaker scan`, `kgmaker check`,
and `git diff --check` passed; memory capture recorded the follow-up review.

Mainline integration was checked on `a83dbab6263eb2fe225f0da51f2f2549c0ab162e`.
The S06 framework and K2 worker files are byte-identical to the reviewed core;
mainline's Windows JDK-selection change is preserved. Actual K2/Javac compatibility,
worker protocol/install, and Windows install slices passed (36 passed, 1 skipped
across the two focused runs); the full S06 suite remains the recorded 379 passed,
9 skipped run before this unrelated Windows integration.

Integration against current main `1091330b67a7ff67db329ffbbb2eaba162313b3f`
preserves the reviewed S06 `framework.py`, K2 frontend, and K2 JPA tests
byte-identically. Mainline TypeScript project-reference/context, XLSX formula/cache,
workspace fingerprint, worker protocol, and Windows changes are retained. Actual
K2/Javac JPA plus worker protocol checks: **13 passed** with prepared JDK 21,
K1/K2 workers and fixtures. The full-suite result remains 379 passed, 9 skipped
before this independent mainline refresh; no full suite was repeated.
Semantic history has the exact current-main 93-episode prefix followed by four
S06 episodes. README semantic workflow citations and compiler-inspection JPA
architecture citations were rechecked against the merged line locations.

### Integrace bounded Spring imports

Proti main `4113a7975451a8313321fd521252485c959908e3` byla zachována S06
K2 frontend a JPA fixture; frameworková projekce nyní obsahuje obě ověřené větve:
JPA mapování i bounded Spring `ImportSelector` selection. Merged K1/K2 workery
byly sestaveny z připnutých lokálních vstupů (K1 SHA-256
`1c9dd4585c05de861d127dd9a87b667ea7dcacc737683c8447e1ff4b9392fa6a`, K2
SHA-256 `138ffc7c732799a4c5d07e939acad8b9cc05048e03f683120e00f152e16c77e7`).
Actual K2 JPA, Javac AC06, Spring 6.2.2 selector/import fixtures a worker
protocol: **37 passed**, s požadovanými worker gates zapnutými. Full suite se
kvůli této integraci neopakovala.

### Oprava povinného K2 fixture guardu a integrace T008

GitHub unittest spouští také source-only prostředí bez JDK/K2. JPA acceptance proto
používá společný `actual_k2` fixture: bez volitelného toolchainu vykáže SKIP a při
`KGMAKER_REQUIRE_K2=1` skončí jako FAIL, nikoli jako falešný compiler test. Změna
upravuje pouze parametr testu; `framework.py` i K2 worker zůstávají byte-identické
s reviewed S06 core.

Po merge T008 na `ff26a6d74679fc38820c1f2fe711b1db20af2ca1` prošla JPA/Javac,
Spring 6.2.2 K1/K2 selector, TypeScript context a T008 inventory/workspace kontrola:
**38 passed**. Maven fixtures byly načteny z `/workspace/tools/m2` s ověřenými
SHA-256. První lokální pokus bez `KGMAKER_TEST_MAVEN_REPOSITORY` skončil 18 setup
errors, protože výchozí `~/.m2/repository` neměl připnutý Spring fixture; assertions
se nespustily. Opakovaný běh s explicitním repozitářem prošel.

Toolchain boundary pro opravený acceptance test byla ověřena zvlášť:

```text
env -u JAVA_HOME PATH=/nonexistent PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q -rs tests/test_k2_backend.py::test_k2_jpa_use_site_access_and_ambiguity_are_compiler_attributed
# 1 skipped: blocked: explicit K2 worker build and JDK required

env -u JAVA_HOME PATH=/nonexistent PYTHONPATH=src KGMAKER_REQUIRE_K2=1 /workspace/kgmaker-venv/bin/python -m pytest -q -rs tests/test_k2_backend.py::test_k2_jpa_use_site_access_and_ambiguity_are_compiler_attributed
# 1 expected setup error: mandatory K2/JDK is unavailable
```

Příkazy a výsledek skutečného integračního běhu:

```text
JAVA_HOME=/workspace/tools/jdk-21.0.6+7 PATH=/workspace/tools/jdk-21.0.6+7/bin:$PATH PYTHONPATH=src KGMAKER_TEST_MAVEN_REPOSITORY=/workspace/tools/m2 KGMAKER_REQUIRE_K2=1 KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_SPRING_IMPORTS=1 /workspace/kgmaker-venv/bin/python -m pytest -q tests/test_k2_backend.py::test_k2_jpa_use_site_access_and_ambiguity_are_compiler_attributed tests/test_build_aware.py::BuildAwareContractsTest::test_hb01_embedded_id_and_bidirectional_association_preserve_roles tests/test_spring_imports.py tests/test_spring_imports_context.py tests/test_t008_project_service_inventory.py
# 38 passed in 79.90s
```

Celá sada nebyla po této čistě testovací a mainline integrační změně opakována;
poslední kompletní S06 výsledek zůstává 379 passed, 9 skipped před integrací T008.

### Integrace mandatory-worker CI gate

Na current main `e9027e9a14e048c891aec01ca5af812fc8cf46c7` je zachován
mandatory compiler-worker gate: CI nastavuje `KGMAKER_REQUIRE_WORKERS=1`,
`KGMAKER_REQUIRE_K2=1` a `KGMAKER_REQUIRE_SPRING_IMPORTS=1`; source-only unittest
samostatně ověřuje, že chybná nebo chybějící povinná příprava není označena jako PASS.
Opravený JPA test nadále používá `actual_k2`, takže volitelný job může přeskočit
nedostupný K2/JDK, zatímco mandatory job hlásí FAIL. Integrace mění pouze CI,
testy a dokumentaci; frameworková JPA implementace a K2 worker zůstávají
byte-identické vůči schválenému core.

Cílené pure tests pro mandatory gate a T008/Spring context zachovaly nulové
spuštění workerů v offline cestách:

```text
PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q tests/test_mandatory_worker_ci.py tests/test_t008_project_service_inventory.py tests/test_spring_imports_context.py
# 29 passed in 0.20s
```

Skutečný K2/Javac/Spring běh a full suite nebyly při této CI-only refresh
opakovány; předchozí actual 38-pass integrace zůstává zdokumentována výše.
