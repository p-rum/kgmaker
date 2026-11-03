# Zděděné JPA persistence atributy

Datum: 2026-10-26. Zadání: [T003-S06-W02](../tasks/T003-S06-02-jpaInheritedAttributes.md),
T003-S06 a T003-AC06. Acceptance: T003-S06-W02-AC01–AC04.

Dosavadní frameworková projekce zachytila deklaraci `@MappedSuperclass` a
inheritance hranu, ale jeho persistence properties nevystavila na efektivní
entity. Nyní `orm_attribute` zachovává `declaring_owner` a `effective_owner`,
deklarující uzel propojuje hranou `inherits_attribute` a mapuje výsledek na
tabulku podle root `@Inheritance` strategie. Zděděné FIELD/PROPERTY access
vychází z compiler-attributed ID placement. Přesné type identity, nejbližší
`@AttributeOverride`, jmenná kolize a unresolved hodnoty jsou řešeny fail-closed.
Runtime graph/store schema zůstává v3; nové atributy metadata jsou aditivní.

Příklady ověřené fixture:

```kotlin
@MappedSuperclass
open class AuditBase(@field:Id val id: Long,
                     @field:Column(name = "created_on") open val created: String)

@Entity
@AttributeOverride(name = "created", column = Column(name = "entity_created"))
class OrderEntity : AuditBase(1, "now")
```

Čtenář používá stejný explicitní offline inspection příkaz; nová CLI volba není
potřeba:

```bash
kgmaker inspect jvm --root project --kotlin-backend k2
```

Přímé kontroly na Linuxu, Python 3.12, JDK 21.0.6 a připravených K1/K2 workers:

- `PATH=/workspace/tools/jdk-21.0.6+7/bin:$PATH KGMAKER_REQUIRE_K2=1 PYTHONPATH=src /workspace/kgmaker-venv/bin/pytest -q tests/test_k2_backend.py::test_k2_jpa_use_site_access_and_ambiguity_are_compiler_attributed tests/test_k2_backend.py::test_k2_jpa_mapped_superclass_attributes_keep_declaring_and_effective_owners tests/test_k2_backend.py::test_java_jpa_mapped_superclass_fields_and_properties_are_projected` — 3 passed.
- `PATH=/workspace/tools/jdk-21.0.6+7/bin:$PATH KGMAKER_REQUIRE_WORKERS=1 PYTHONPATH=src /workspace/kgmaker-venv/bin/pytest -q tests/test_compiler_workers.py::CompilerWorkerTests::test_ac06_real_javac_embedded_id_and_association_roles` — 1 passed.
- `PATH=/workspace/tools/jdk-21.0.6+7/bin:$PATH PYTHONPATH=src /workspace/kgmaker-venv/bin/pytest -q tests/test_k2_backend.py::test_existing_graph_loader_is_unchanged tests/test_k2_backend.py::test_k2_store_refresh_is_offline_and_strict_failure_preserves_graph tests/test_build_aware.py::BuildAwareContractsTest::test_hb01_embedded_id_and_bidirectional_association_preserve_roles` — 5 passed.

Celý `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q` —
483 passed, 64 skipped in 234.08 s; skips jsou volitelné toolchain-dependent
scénáře bez jejich přísného režimu. Finální sémantická validace, scan/check a
`git diff --check` proběhly po této kontrole. Entity-declared
attributes inherited across entity superclasses, ORM XML override priority,
provider-specific rules, širší query grammar a schema/deployment availability
zůstávají mimo ověřený scope; T003-S06 zůstává PARTIAL.

## Oprava přesné identity entity v repository query (2026-10-27)

Read-only audit odhalil, že dva compiler-owned `Thing` entity z různých package
sdílely `entity_attributes["Thing"]`: `right.ThingRepository` proto chybně
validoval `findByLeftId` proti `left.Thing.leftId`. Nově repository generic
vybírá model výhradně z compiler-resolved generic supertype, který obsahuje
exact entity owner. Attribute, embedded/association lookup a inheritance table
index používají canonical owner; neúplný vstup dostane jen opaque declaration
key a nemůže se účastnit repository model resolution. Neprokázaný generic owner
zůstane unresolved bez simple-name fallbacku. Graph/store schema zůstává v3.

Actual Javac fixture
`CompilerWorkerTests.test_repository_generic_uses_exact_entity_owner_for_same_simple_names`
nejprve selhal s `findByLeftId.validated == True`; po opravě ověřuje, že
`findByLeftId` nemá `filters_by` ani attribute ID, `findByRightId` míří pouze na
`right.Thing.rightId` a `repository_for` cílí na přesný right entity class.
Hand-built framework fixture nyní nese explicitní compiler owner/generic facts,
jako je vyžaduje tento kontrakt. Revalidace zahrnuje actual Javac AC06 a K2/Javac
W01/W02 access/inheritance cases.

Focused příkaz:

```bash
JAVA_HOME=/workspace/tools/jdk-21.0.6+7 \
PATH=/workspace/tools/jdk-21.0.6+7/bin:/workspace/tools/kotlinc/bin:$PATH \
PYTHONPATH=src KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 \
/workspace/kgmaker-venv/bin/python -m pytest -q \
  tests/test_compiler_workers.py::CompilerWorkerTests::test_repository_generic_uses_exact_entity_owner_for_same_simple_names \
  tests/test_compiler_workers.py::CompilerWorkerTests::test_ac06_real_javac_embedded_id_and_association_roles \
  tests/test_build_aware.py::BuildAwareContractsTest::test_framework_projection_keeps_framework_evidence_separate \
  tests/test_k2_backend.py::test_k2_jpa_mapped_superclass_attributes_keep_declaring_and_effective_owners \
  tests/test_k2_backend.py::test_java_jpa_mapped_superclass_fields_and_properties_are_projected \
  tests/test_k2_backend.py::test_k2_jpa_use_site_access_and_ambiguity_are_compiler_attributed
```

Focused revalidation — 6 passed in 51.48 s. Final serialized full suite after
the defensive-index and synthetic-fixture correction — 538 passed, 10 skipped
in 489.03 s. T003-S06 remains PARTIAL.

První serialized full run po zavedení canonical-owner indexu skončil
`1 failed, 537 passed, 10 skipped in 414.29 s`. Jediná chyba byla v
`BuildAwareContractsTest.test_framework_projection_keeps_framework_evidence_separate`:
ručně sestavené symboly fixture neobsahovaly `owner` ani compiler generic
`supertypes`, takže obranné zpracování neúplné entity deklarace skončilo
`KeyError`. Je to skutečný integration robustness bug, který test odhalil.
Oprava přiřazuje neúplným deklaracím jen opaque node-index (bez možnosti
repository generic resolution) a doplňuje synthetic fixture explicitními
compiler owner/generic facts. Source identity guard se neuvolnil. Následný
serialized full retry prošel: 538 passed, 10 skipped in 489.03 s.

## JPQL entity a return identity guard (2026-10-27)

Následný actual Javac probe našel, že explicitní JPQL `from left.Thing` mohlo
zdědit repository owner `right.Thing`; return type `right.Thing` se navíc
vybíral podle prvního uzlu se simple name `Thing`. Projekce nyní mapuje přesné
compiler `@Entity(name)` (při chybějícím či prázdném name používá JPA default
class name) a vyžaduje jediného entity ownera. Repository domain už nepřebíjí
query entity; neznámý nebo duplicitní JPQL name označí query UNKNOWN bez
`query_reads`/`filters_by`. Návratový typ nejprve vybírá přes owner identity;
prosté jméno se použije pouze při jediném compiler type match.

Stejný actual Javac fixture ověřuje qualified `right.Thing` positive, qualified
`left.Thing` query vedle compiler return `right.Thing`, a ambiguous unqualified
`Thing` negative. FQ query a compiler return nesdílejí identity podle simple
name; ambiguity nevytvoří první-match edge. Existing AC06 a hand-built
framework fixture zůstávají green.

Focused actual Javac checks po této identity guard změně: 3 passed in 20.18 s
(new repository/JPA fixture, actual AC06, defensive hand-built framework
fixture). Před finální suite proběhl worker/toolchain preflight a source hash
freeze. Serialized full suite na tomto zdroji —
`JAVA_HOME=/workspace/tools/jdk-21.0.6+7 PATH=/workspace/tools/jdk-21.0.6+7/bin:/workspace/tools/kotlinc/bin:$PATH PYTHONPATH=src KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 KGMAKER_TEST_MAVEN_REPOSITORY=/workspace/tools/m2 /workspace/kgmaker-venv/bin/python -m pytest -q` pod `/workspace/kgmaker-heavy-tests.lock` — prošel:
538 passed, 10 skipped in 410.27 s. Skips jsou volitelné toolchain-dependent
scénáře; strict K1/K2/Javac režim byl aktivní. Tento výsledek pokrývá JPQL
identity guard. Starší full běhy v této poznámce se vztahují k předchozímu
source snapshotu.

## Compiler-proven return type owner (2026-10-27)

Další partial-index audit našel, že chybějící `foreign.Thing` se po exact-owner
lookupu ještě mohlo svázat s jediným dostupným `right.Thing`. Return projection
proto už nikdy nepadá zpět na simple-name kandidáta. Kvalifikovaný typ vyžaduje
exact owner; jednoduché source jméno může použít jen přesného ownera z JVM
method descriptoru, pokud odpovídá deklarovanému jménu. Erased generic `T`
nezíská owner z náhodné lokální třídy `T`; bez proof zůstává query UNKNOWN.

Actual Javac regresní fixture ověřuje descriptor-proven `right.Thing` positive,
partial compiler graph s nepřítomným `foreign.Thing` a jedinou lokální
`right.Thing` negative, a generic `<T> T` vedle lokálního `right.T` negative.
Chybějící return type nastaví `validated=false` a nevytvoří
`returns_entity`/`returns_projection` edge.

Focused Javac/AC06/defensive-fixture checks: 3 passed in 18.01 s. Core
prerequisite preflight passed without builds or installs. Po source/test hash
freeze serialized full suite pod `/workspace/kgmaker-heavy-tests.lock` prošel:
538 passed, 10 skipped in 618.24 s. `KGMAKER_REQUIRE_WORKERS=1` a
`KGMAKER_REQUIRE_K2=1` byly aktivní; skips jsou zbývající optional
toolchain-dependent cases. Tento výsledek pokrývá compiler-proven return owner
guard; předchozí suite shrnutí výše patří ke staršímu source snapshotu.

## Integrate refreshed W01 and T009 main `09d351d` (2026-10-27)

The refreshed W01 parent includes T009 view evidence and coverage. Its local
merge into this W02 branch leaves the JPA runtime and tests byte-identical to
the pre-integration W02 head, including `framework.py`, the K2 worker,
`test_k2_backend.py`, and `test_compiler_workers.py`; T009 contributes the view
model, schema, tests, and CI/documentation changes.

Focused compatibility checks under strict JDK/K1/K2/Javac requirements passed:
the actual same-simple-name repository/JPQL identity fixture, actual Javac
AC06, actual K2 use-site access, K2 mapped-superclass inheritance, and Java
mapped-superclass projection — **5 passed in 70.51 s**. The refreshed W01
T005/T008/T009 integration suite passed separately with 66 tests. No full suite
was repeated for this pure-base integration; the frozen W02 source full result
above remains applicable.

Semantic history preserves the exact 115-episode main prefix, seven W01-only
episodes, the W01 integration capture, and four W02-only implementation
episodes; a new current-base integration capture follows. The W01 JPA semantic
concept and W02 exact repository/JPQL identity concept are both retained with
current compiler-inspection citations. Semantic validation and regenerated
graph/check and diff checks are included in the integration validation.

## Refresh W01/W02 to current main `5430388` (2026-10-27)

Current main adds selected TypeScript configuration freshness. The merge keeps
W02 JPA runtime and regression-test sources byte-identical to the pre-refresh
W02 head: `framework.py`, the K2 frontend, `test_k2_backend.py`, and
`test_compiler_workers.py`. The new main changes add TypeScript snapshot handling,
tests, documentation, and matrix entries.

Focused JDK21/Kotlin2.1.10/Javac validation passed for the exact JPQL owner and
partial-index return cases, Javac AC06, K2 use-site access, K2 mapped-superclass
inheritance, and Java mapped-superclass projection: **5 passed in 64.66 s**.
No full suite was repeated for this base refresh. Semantic history preserves the
exact 118-episode current-main prefix, the nine W01-only entries including its
current integration capture, and five W02-only implementation entries; a fresh
W02 integration capture follows. Semantic validation, graph regeneration/check,
and diff checks complete the refresh.

## Refresh W02 after W01 current-main reconciliation `1c49847` (2026-10-27)

W01's refreshed main3a7 history and documentation are integrated through its
approved local head. W02 runtime and test sources remain byte-identical to the
pre-refresh W02 head: `framework.py` `28421d7e`, K2 frontend `31210488`,
`test_k2_backend.py` `2e8d0009`, and `test_compiler_workers.py` `b753c35e`.
The current-main history remains an exact 121-episode prefix, followed by W01
implementation/integration history and the W02 task's own unique history.

The actual repository-owner JPQL fixture, K2 use-site/access fixture, and K2
mapped-superclass owner fixture passed: **3 passed in 56.73 s**. No full suite
was repeated for this parent-only refresh. Semantic validation, scan/check and
diff checks record the refreshed source graph; W03's XML overlay is integrated
separately above this W02 head.


## Current-main/W01 integrace po změně CI pravidel (2026-11-03)

Base je main966948b533a7a9417dea370733f300f91fd2b61c s merged W01. Vlastní
framework.py a oba JPA compiler test moduly zůstávají byte-identické opravenému
W02 checkpointu283987a98835462c29ac9fc39150233dc1a47b74, včetně canonical
entity/JPQL owner a generic return guards. Starý remote c65ff není aktuální
opravený source. Všechny JVM worker/build/lock soubory jsou nyní přesně z main.

Aktuální worker JARy byly převzaty výhradně z W01 po porovnání všech tracked JVM
source/build/lock souborů, všech library hashů a skutečné fresh-build receipt
`/workspace/combined-jvm-main-ec/verified-results.json`. K1 SHA e44e3dac04ba28cd8899fed0ae183f5739c4311911b1ae656e6d1db26b64e15e,
K2 SHA e2553425c3c24c310dccdc8893aa1d5acdf05dcbc7c3f07c5a3ead8751e9570a.
Porovnání je zaznamenáno v `/workspace/w02-main966-worker-receipt.json`; samotná
shoda source bez této build provenance by nestačila.

Actual owner/return, K2 inheritance/use-site, Javac a dependency dispatch focus je
připraven pod sdíleným flockem s mandatory workers/K2/Spring flags. Dokud není
skutečný pytest dokončen, nejde o PASS. Nový full pro tuto parent-only integraci
není plánován. GH CI je podle výslovné uživatelské změny volitelné, všechny
ostatní acceptance, aktuální nezávislé review a dependency kontroly zůstávají.

Actual focus dokončen: **6 PASS, 83 deselected v32.06s**, XML
`/workspace/w02-main966-actual.xml` má0 failures/errors/skips. Běžely exact
repository generic/JPQL return owner, K2 use-site a mapped-superclass, Java
mapped-superclass, Javac AC06 a dependency interface dispatch. Pure integrace
T005/T008/T009/T015/mandatory: **124 PASS, 2 actual T015 deselected v2.56s**,
XML `/workspace/w02-main966-pure.xml`. Runtime/test source zůstal po celou
frontu a actual běh beze změny.
