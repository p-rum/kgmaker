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

## Přenos kroku 4 / T003-S05-W04-AC01 a AC03, 2026-11-20

Cílový main při ověření `8ff2529ffb50b42ed2209d97478ea3e4cbf46042`,
Git tree `c869302cdc2a7d9982d64058b6267ae603382e06`. Testovací soubor je
bajtově shodný s původním headem [#124](https://github.com/p-rum/kgmaker/pull/124)
`3eaf793af7b578ffc566d4548ff24be87894cb97`. Celý produkční zdrojový
strom byl převzat z tohoto main. Rozsah příkladu s kanonickou anotací ani
kontrakt testu se při přenosu nerozšiřují.

V izolovaném snapshotu běžel připravený Python test venv, JDK
21.0.13.1, Kotlin 2.1.10, Node 22.22.1 a TypeScript 5.7.3 s lokální
Maven fixture a fyzickou kopií React závislostí. Proměnné
`KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1` a
`JAVA_TOOL_OPTIONS=-XX:-UsePerfData` platily pro všechny následující výběry.
Příkazy používaly oddělený lokální `--basetemp` pro každý výběr.

- `python -m pytest -p no:cacheprovider -q --tb=short tests/test_compiler_workers.py::CompilerWorkerTests::test_ac05_spring_profiles_conditions_qualifier_primary_and_short_name_guard`
  na samotném main **1 FAIL** za 9,27 s s `KeyError: 'Consumer.gateway'`.
- `python -m pytest -p no:cacheprovider -q --tb=short tests/test_compiler_workers.py`
  na přenesené fixture **15 PASS / 0 SKIP** za 55,49 s.
- `python -m pytest -p no:cacheprovider -q --tb=short tests/test_k2_backend.py::test_k1_and_k2_contexts_accumulate_without_replacement`
  na kandidátu **1 PASS / 0 SKIP** za 13,55 s. Tento samostatný případ
  dokládá skutečné K1/K2 oba v izolovaném testu.
- `python -m pytest -p no:cacheprovider -q --tb=short 'tests/test_local_operation_proofs.py::test_scope_projection_preserves_invalid_operation_shape_for_fail_closed_validation[None]'`
  na standalone kandidátu **1 FAIL** za 0,10 s. Při projekci evidence
  je `local_operation_evidence_ids=null` neiterovatelný v `views.project`.
  Oprava je samostatný rozsah T025 v [#122](https://github.com/p-rum/kgmaker/pull/122).

## Přenos kroku 5 / T003-S05-W04-AC04, 2026-11-20

[Acceptance inventář](../acceptance-inventory.md) a
[stavová matice](../production-analysis-progress.md) aktualizují nový
cílený výsledek a zachovávají původní stav #95. README, veřejná capability,
API, CLI příklady a registr zadání jsou bez dopadu, protože se mění pouze
syntetický vstup existujícího testu a jeho přesné assertion. Úplný samostatný
běh na této revizi, review nového publikovaného páru a GitHub Actions
zůstávají NOT_RUN. Reprodukované selhání T025 blokuje úplnou merge kontrolu.

### Kontroly grafu / T003-S05-W04-AC04

Při přípravě headu `5f4bb2436c54e12f2f0aa2237e17681590068a34` na uvedeném
main proběhly v izolovaném snapshotu tyto příkazy s `PYTHONPATH=src`
a Pythonem z testovacího venv.

- `python -m kgmaker semantic apply` — **PASS**. Zachoval tři dotčené
  vztahy a přesměroval jedinou existující hranu na aktuální ID Javac JPA
  testu `test_ac06_real_javac_embedded_id_and_association_roles`
  z `::461` na `::473`. Výsledek měl 55 konceptů a 185 uložených vztahů.
- `python -m kgmaker semantic validate` — **PASS**. Ověřil 384 konceptů
  a 33 253 vztahů včetně projekce zachovaných epizod.
- `python -m kgmaker memory capture --base HEAD --validation baseline-spring=failed --validation compiler-workers=passed --validation k1-k2-coexistence=passed --validation existing-t025=failed --validation full=unknown`
  — **PASS**. V lokálním snapshotu `HEAD` odpovídal výchozímu Git tree
  `c869302cdc2a7d9982d64058b6267ae603382e06`. Zůstalo zachováno 329
  starších epizod a vznikla
  `episode:075dc502a5c638d642b732f31e1cae0bdfedbbbd3f81c41603d1b621e0ae9dc7`.
- `python -m kgmaker scan`, `python -m kgmaker status` a
  `python -m kgmaker check` — **PASS**. Scan obnovil zdrojový graf
  a dokumentaci. Obě následné kontroly potvrdily aktuálnost.
- `git diff --check` a `git diff --cached --check` — **PASS**.
