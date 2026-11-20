# Skutečná Spring fixture s kanonickou injekční anotací

Zadání [T003-S05-W04](../tasks/T003-S05-04-springProxyAsyncSemantics.md),
T003-AC05 a T003-S05-W04-AC01/AC03. Zdrojová baseline
`465b121992aad50c2885acef0fd038531a31293a`.
Nové ověření opravuje očekávání testovací fixture po zpřesnění inference
v commitu `bc77c3be2c51d6f7e89b3c018f1e2825df619a0c`.

## Ověření fixture / T003-S05-W04-AC01, AC03

[Fixture](../../tests/test_compiler_workers.py) deklarovala Consumer fields bez
kanonické injekční anotace a očekávala jejich rozlišení. Klíč
`Consumer.gateway` v rozsahu skutečného Javac workeru chyběl. Test nyní
označuje kladné vstupy `@Autowired` a ponechává pole bez anotace a pole
označené samotnou `@Qualifier` jako negativní případy. Kontroly profilů,
primary/qualifier, kolekcí, Map, Optional, ObjectProvider, ambiguit a
scope zůstaly součástí stejného testu.

Uživatelská inference, CLI, graph formát, init a capability předpoklady
zůstávají stejné, proto README a provozní compiler návod neměníme.
[Acceptance inventář](../acceptance-inventory.md) a [stav](../production-analysis-progress.md)
zaznamenávají nový ověřený případ. Příklad je `@Autowired @Qualifier("blueGateway") Gateway qualified;`.

- Cílená dvojice `tests/test_compiler_workers.py` testů
  `CompilerWorkerTests::test_ac05_spring_profiles_conditions_qualifier_primary_and_short_name_guard`
  a `CompilerWorkerTests::test_ts01_ts02_react_handler_and_overloads_use_typechecker_symbols`
  nad původní fixture v auditním checkoutu: 2 FAIL. Spring selhal na chybějícím
  injection node, React fixture neměla lokální balíčky.
- Stejné dvě plné pytest node ID s JDK 21, předem sestavenými Javac/Kotlin
  worker artefakty a připravenými React 18 závislostmi: 2 PASS, 0 SKIP (17.76 s).
  Ekivalentní příkaz je `pytest -q tests/test_compiler_workers.py::CompilerWorkerTests::test_ac05_spring_profiles_conditions_qualifier_primary_and_short_name_guard tests/test_compiler_workers.py::CompilerWorkerTests::test_ts01_ts02_react_handler_and_overloads_use_typechecker_symbols`. React package.json, lockfile, tsconfig a App.tsx
  jsou byte-identické s připraveným původním checkoutem. TypeScript fixture
  potřebovala pouze připravené lokální prostředí.
- `git diff --check` PASS. Nový úplný běh a publikované exact-pair review
  zůstávají NOT_RUN. Runtime chování Spring aplikace z tohoto testu nevzniká.
