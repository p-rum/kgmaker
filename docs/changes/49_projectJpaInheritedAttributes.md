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
