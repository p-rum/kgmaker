# Společná integrace čtyř oprav compiler evidence

Výchozí `main` je `8ff2529ffb50b42ed2209d97478ea3e4cbf46042`, Git tree
`c869302cdc2a7d9982d64058b6267ae603382e06`. Uživatel výslovně povolil jednorázový
společný integrační PR pro nejmenší skupinu nutnou k ověření a sloučení.
Původní rozsahy a review jsou v dílčích PR. Pro společný PR se podle
[T045](../tasks/45_addCodeReviewAgent.md) ověřuje přesný pár base/head.

| Dílčí PR | Přesný head | Podrobný záznam |
| --- | --- | --- |
| [#119](https://github.com/p-rum/kgmaker/pull/119) | `3a6716efba956d9f13e6031c2b1f844a95e5759e` | [W01](135_bindCachedCompilerEvidence.md) |
| [#122](https://github.com/p-rum/kgmaker/pull/122) | `2c9cc44babbdf2cb0dd3a59fc6dbbd61ec88e015` | [T025](136_preserveMalformedCfgEvidence.md) |
| [#124](https://github.com/p-rum/kgmaker/pull/124) | `d52973cc5b6e79143f55e9c6d14fb0669d66f966` | [Spring W04](139_validateCanonicalInjectionFixture.md) |
| [#126](https://github.com/p-rum/kgmaker/pull/126) | `8ebbf4c40884ce58dc908a47aa6d68dec398326c` | [Kafka W05](141_handleInvalidKafkaPolicyContext.md) |

## T003-S10-W01 kroky 1–5 a AC01–AC04

Obsah uložené cache s přepočítaným digestem mohl nahradit ověřená fakta.
`extraction_cache.py`, `graph_provider.py` a `inspection.py` nyní vyžadují
živou evidenci pro explicitní inspekci. Existující test Spring registrace
`test_factory_invalid_context_and_timeout_preserve_store[k1-owner]`
na výchozí revizi hlásil FAIL a na společném kódu PASS. Dílčí PR má 97 PASS
s JDK21/K1/K2 a TypeScriptem bez SKIP. Kompatibilita grafu v1/v2/v3 a cache
envelope v1 je zachována. Uživatel v `kgmaker inspect code --root ./service
--module core --source-set main` uvidí `cache.stages` se stavem BYPASS.
[README](../../README.md), [CLI a omezení](../stage-content-cache.md) a
[podpora compiler inspection](../compiler-inspection.md) popisují aktuální chování.
Měření přínosu replay a work packages W02/W06 mají samostatnou acceptance.

## T025-S04, S05, S07 a T025-AC04, AC05, AC06, AC08, AC09

Projekce `views.project` nyní kontroluje volitelná CFG metadata
`local_operation_evidence_ids`. Vadná metadata zachová v bloku pro fail-closed
validaci a jako referenci uznává pouze platný tvar. Například `null` zůstane
viditelné pro validátor. Test
`test_scope_projection_preserves_invalid_operation_shape_for_fail_closed_validation[None]`
na výchozí revizi hlásil FAIL a na společném kódu PASS. Dílčí PR má 113 PASS / 0 SKIP
se skutečnými JDK21/K1/K2. Výstupní tvar CFG a hranice procesního reportu viz
[process API a příklady](../process-paths.md) a [README](../../README.md).

## T003-S05-W04 kroky 4–5, AC01, AC03, AC04 a T003-AC05

Javac fixture v `tests/test_compiler_workers.py` explicitně anotuje kladná
injekční pole `@Autowired`. Neanotované pole a pole pouze s `@Qualifier`
jsou negativní případy. Test
`test_ac05_spring_profiles_conditions_qualifier_primary_and_short_name_guard`
na výchozí revizi hlásil FAIL pro chybějící `Consumer.gateway` a na společném
kódu PASS. Dílčí PR má 15 compiler-worker PASS bez SKIP a samostatný skutečný
test K1/K2. Změna se týká fixture. Veřejné API, CLI a runtime závěry se tím
nerozšiřují.

## T003-S07-W05 a T003-S07-W05-AC01, AC03, AC04

Dříve mohl seznam nebo objekt v `context_id` vyvolat TypeError.
`views.project` vyloučí vadný policy uzel z vybraného grafu. Procesní report
přesto zachová UNKNOWN pro odpovídajícího callera. Stejný soubor současně
obsahuje nezávislou kontrolu CFG pro T025. Test
`test_policy_markdown_keeps_framework_intent_separate_from_cfg[java]`
na výchozí revizi hlásil FAIL kvůli tvaru výstupu a na společném kódu PASS.
Dílčí PR má 240 PASS / 0 SKIP s reálnou Java/Kotlin a související HTTP fixture.
[Kafka capability a příklady](../kafka-retry-dlt.md) a [README](../../README.md)
popisují statickou hranici. Aktivace, doručení a dostupnost zůstávají UNKNOWN
nebo NOT_OBSERVED podle příslušné vrstvy.

## Společný důkaz a zbývající kontroly

Původní reprodukce pro CFG a Spring skončila 2 FAIL za 9,11 s. Pro cache a
Kafka skončila 2 FAIL za 24,47 s. Totéž ověření nad kombinovaným kódem
`44cc37cbe1f7e4bb0f8f03794bdd15c7f606a9e9` skončilo 2 PASS za 17,62 s a
2 PASS za 21,63 s. Samostatný W05 reprodukoval obě chyby CFG a Spring.
Následující cílené příkazy s JDK21, připnutými Maven vstupy, K1, K2 a TypeScript
workery uvádějí přesný výběr.

```bash
python -m pytest -p no:cacheprovider -q --tb=short \
  'tests/test_local_operation_proofs.py::test_scope_projection_preserves_invalid_operation_shape_for_fail_closed_validation[None]' \
  'tests/test_compiler_workers.py::CompilerWorkerTests::test_ac05_spring_profiles_conditions_qualifier_primary_and_short_name_guard'
python -m pytest -p no:cacheprovider -q --tb=short \
  'tests/test_spring_registrations.py::test_factory_invalid_context_and_timeout_preserve_store[k1-owner]' \
  'tests/test_kafka_retry_dlt.py::test_policy_markdown_keeps_framework_intent_separate_from_cfg[java]'
```

Na kombinovaném kódu poskytly předchozí dílčí běhy ověření 3643 z 3645 různých
případů. První úplný pokus přerušila disková kvóta. Závěrečná část měla 195 PASS
a Windows smoke SKIP. Dodatečné Maven kontroly měly 3 PASS a test dvou JDK 21+
SKIP. Úplný nepřerušený běh nad zveřejňovanou revizí, aktuální GitHub CI a
T045 review jsou zde ve stavu NOT_RUN při přípravě. Výsledky patří k přesnému
páru revizí v PR a příslušných výpisech.

[Stavová matice](../production-analysis-progress.md) a
[acceptance inventář](../acceptance-inventory.md) oddělují dodání a ověření.
Rozsahy T047 a T021 mají vlastní PR. Odkazy na oracle a test T047 v matici
míří na jejich dostupnou revizi v #121. Registr, instalované instrukce a šablony
init nemají změnu kontraktu.
