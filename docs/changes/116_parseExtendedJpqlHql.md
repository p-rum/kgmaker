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
