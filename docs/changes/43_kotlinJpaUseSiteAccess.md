# Změna 43: Kotlin JPA use-site a access

T003-S06-W01 doplňuje stávající JPA projekci o Kotlin constructor properties a
K2 `@field:`/`@get:` targety. Worker používá K2 annotation identity/constant
facts a JVM light field/getter typy; frameworková vrstva tak vybírá FIELD nebo
PROPERTY jen z jednoznačného `@Id`/`@EmbeddedId` targetu nebo explicitního
`@Access`. Změna nepřidává graph typ ani nemění JPA rules `annotation-source-v4`.

Nejednoznačné constructor `@Id`, foreign anotace se stejným short name a
konflikt mezi explicitním `@Access` a identity targetem nevytvoří nesprávný
persistent attribute. Nevyřešená annotation value se neinterpretuje z textu
zdroje a zůstává diagnostikovaná. Konstantní annotation argumenty se čtou jako
compiler values; import aliasy zachovávají FQ identity. Pole/getter a typy
pocházejí z Kotlin JVM light PSI, takže importované typy nevznikají odhadem z
package aktuálního zdroje.

Přímá acceptance evidence:

- **AC01:** `tests/test_k2_backend.py::test_k2_jpa_use_site_access_and_ambiguity_are_compiler_attributed` ověřuje skutečný K2 worker, `@field:EmbeddedId`, `@get:Id`, explicitní PROPERTY access, unqualified/mismatched targets, foreign `fake.Id`, import alias, `const val` column name, importovaný `java.time.Instant` a Kotlin `@Embeddable` column.
- **AC02:** Stejný fixture ověřuje existující `orm_attribute`/`orm_embeddable` projection; Java JPA regression `tests/test_build_aware.py::BuildAwareContractsTest::test_hb01_embedded_id_and_bidirectional_association_preserve_roles` zůstává zelená.
- **AC03:** Nejednoznačný, foreign a konfliktní identity target nevytvoří `orm_attribute`; přísné selhání a zachování uloženého grafu nadále ověřuje `tests/test_k2_backend.py::test_k2_store_refresh_is_offline_and_strict_failure_preserves_graph`.
- **AC04:** Stav zůstává PARTIAL; zbývající K2 execution model, XML override a širší persistence rozsah se tím neuzavírají.

Ověření v izolovaném worktree `/workspace/s06-jpa`:

```text
python workers/jvm/build.py --backend k2 --kotlin-home /workspace/tools/kotlinc --maven-repository /workspace/tools/m2 --java-home /workspace/tools/jdk-21.0.6+7 --analysis-api-home /workspace/tools/k2-verified
# SUCCESS; worker SHA-256 aea3024ec5381f772e4604e5d9f14e6635abb64ce3483e488dc8b39ae70a7aa6

JAVA_HOME=/workspace/tools/jdk-21.0.6+7 PATH=/workspace/tools/jdk-21.0.6+7/bin:$PATH PYTHONPATH=src KGMAKER_REQUIRE_K2=1 /workspace/kgmaker-venv/bin/python -m pytest -q tests/test_k2_backend.py::test_k2_jpa_use_site_access_and_ambiguity_are_compiler_attributed tests/test_build_aware.py::BuildAwareContractsTest::test_hb01_embedded_id_and_bidirectional_association_preserve_roles
# 2 passed

JAVA_HOME=/workspace/tools/jdk-21.0.6+7 PATH=/workspace/tools/jdk-21.0.6+7/bin:$PATH PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q
# 364 passed, 24 skipped
```

The actual Maven-compiled `test_ac06_real_javac_embedded_id_and_association_roles`
fixture was unavailable in this checkout and remains an environment-gated skip;
the source-level Java regression above passed. The worker was built explicitly
from the pinned local compiler/dependency set; no application build, migration,
database access, install or external publication was performed. K2 general
source CFG, constructor ABI, Spring metadata and non-JPA property execution
remain outside this package.

Semantic maintenance used `semantic update --base eff0d3d5d7620b017fe42a65a54f672af8068667`, a scoped patch with update ID
`7026f91390828803a276b29c7bf204261c160dc00c6e1306b6f3dc43166f1aae`,
`semantic apply`, and `semantic validate` (**PASS**). The patch refreshes the
existing README semantic citation and records the K2 annotation facts → JPA
projection → actual compiler fixture links. Memory capture created episode
`episode:075463522afbeba788927e1d945c0d088a28ceda090e1df7c386ea33a0600210`.
Final `kgmaker scan` indexed 295 files, 2,432 declarations/sections and 16,728
relationships; semantic projection contains 76 concepts and 11,389
relationships. `kgmaker check` and `git diff --check` passed.
