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
