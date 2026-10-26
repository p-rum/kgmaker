# Deklarovaná Kafka binding identita ve workspace

Datum:2026-10-26. Task [T003-S07-W04](../tasks/T003-S07-04-kafkaBindingIdentity.md),
AC01–AC04; nadřazené T003-S07/AC07 zůstává PARTIAL. Číslo54 rezervoval parent.
Explicitní stacked baseline je PR34/S05-W03 commit
`78d7968ea7408adea3ec9ce783769bb799522470`; závislost zatím není merged.
Lokální source review a strict573PASS10SKIP podklad parenta není náhrada CI.

## Problém a skutečná změna

Actual config probe dvou clusterů s topicem orders ukázal jediný name-only syntax
hint bez cluster provenance. Java `send("orders-" + suffix, payload)` navíc
vytvořilo falešný literal orders-. Nové actual workspace acceptance před změnou:
**4 FAIL, 4 PASS v0.23s** (nový manifest kontrakt odmítnut, dynamic prefix chyba).

Volitelný `workspace.kafka_bindings` schema1 reuse stávající repository/service/
ownership/provider/model/store. Žádný paralelní katalog nebo nový approval flow.
Services používají explicitní `transport: kafka`; dosavadní defaultHTTP beze změny.
Logical cluster IDs, release a payload jsou DECLARED, ne observed/approvedruntime.

Podporovaný bounded scope: ordered UTF-8 `.properties` Cloud Stream destination/
binder, base a explicitní profile overrides s S05-W03 grammar, whole-property
`${key}` reference depth16/cycle guard. Zachycené properties přesně vybraného
fresh JVM contextu mají přednost. Bez compileru konvenční root/main nebo root/test
scope zůstává SOURCE_ONLY; žádná compiler annotation/proof se nevyrábí. Jiné
source-set roots vyžadují matching compiler project model. Nejednoznačný context,
repo/service/ownership mismatch nebo nebezpečný artefakt fail closed.

`kafka_binding_match` vyžaduje přesný logical cluster + case-sensitive topic +
contractSHA + release + scope v témže workspace. Contract je lokální JSON object,
nikoli validace JSON Schema/payloadclass. Source/config/contract/manifest hashes,
selected context a service jsou v nové provenance; raw properties, broker endpoints
ani credentials se nekopírují. Missing/dynamic/cyclic/unsupported input zůstává
UNKNOWN, bez match. Evidence je FRAMEWORK_DERIVED ze statické konfigurace;
`code_binding=UNPROVEN`, `delivery=NOT_OBSERVED`, žádná runtime/data availability.

Artifact bound1MB, config10000lines, bindings512, configs32/binding, clusters128;
žádné symlinks/out-of-root/hidden/sensitive paths. Před cache publication proběhne
rehash všech použitých config/contract bytes a validation zachyceného compiler
contextu. Disk cache load se nyní také publikuje až po úspěšné validaci celého
snapshotu: původní přímý insert mohl po pozdější chybě změnit in-memory cache.

Legacy name-only Kafka hints zůstávají SYNTAX_CANDIDATE oddělené od nových scoped
identit. Whole dynamic expressions již nedostávají guessed literal prefix;
`kafka_binding_boundary` označuje UNKNOWN. Žádný hint se podle jména nepromuje.
Optional schema1 workspace a graph/store v1/v2/v3 jsou nadále čitelné, schema3
nevyžaduje přepis starého store. Workspace parser cache má nový version input.

## Testy a ověření

- Projektový skill/status/query/source recon, durable analyze/plan packet a memory
  recall provedeny; parent schválil bounded brief a explicitní PR34 stack.
- První actual config sada po implementaci: **8 PASS v0.89s**.
- Expanded config/workspace sada: **44 PASS, 2 FAIL v4.00s**; placeholder bez
  literal prefix postrádal UNKNOWN node. Opraven celý config value boundary.
- Po této opravě **46 PASS v5.93s**. Další strict paths/ownership, disk cache
  rollback, profile/context, no-process a dynamic variable případy přidány.
- Aktuální čistě offline sada: **49 PASS, 2 DESELECTED v3.72s**; oba actual K1/K2
  context případy mají oddělené mandatory toolchain ověření.
- Relevantní finální sada s mandatory K1/K2: **51 PASS v5.29s**. Actual compiler
  contexts skutečně vznikly a následná offline stale-source cesta byla odmítnuta.
  Následný full běžel až po opravě default profile popsané níže.

Fixture `fixtures/kafka-bindings` má tři skutečné lokální roots, properties base/
blue profile a JSON contract. Negatives mění consumer cluster při stejném topicu,
release/hash, dynamic/cyclic values, unsupported config/profile/contract,
repo/context ambiguity, symlink/path/budget a ownership. Race/cancellation/disk
cache tests hlídají poslední validní store/cache a nulovou mutaci source bytes;
password sentinel není v graphu. Offline cesta dovolí pouze původní Git baseline
read, nespouští compiler/build/Kafka. Actual K1/K2 fixture navíc ověřuje captured
property precedence a stale-source refusal. Data-check skutečného matched bindingu
zůstává UNKNOWN a nevyrobí data delivery gap. Mandatory compiler CI explicitně
zahrnuje novou sadu, včetně actual K1/K2 kontextů. Kafka broker API není potřeba a
nebylo spuštěno. Žádná nová package dependency/install/fetch nevzniká.

```bash
kgmaker query --root . --workspace fixtures/kafka-bindings/workspace.json orders-blue
```

Zbývá: code-to-binding compiler proof, obecné YAML/environment/default placeholders,
Spring binder discovery, retry/DLT, Avro/protobuf/remote registry a serialization
compatibility. Delivery/deployment/populated-data zůstávají UNKNOWN. GitHub Actions
billing/quota je externí blocker; Draft PR se neoznačí ready a žádný CI retry/merge
neprobíhá podle aktuálního uživatelského pokynu. Lokální suite nenahrazuje CI.


Přesný final full příkaz (děděný PATH zachovává Node, Maven/Gradle nejsou exponované):

```bash
export JAVA_HOME=/workspace/tools/jdk-21.0.6+7
export PATH="$JAVA_HOME/bin:/workspace/tools/kotlinc/bin:$PATH"
/workspace/kgmaker-venv/bin/python /workspace/kgmaker-test-prerequisites.py /workspace/kafka-bindings
flock /workspace/kgmaker-heavy-tests.lock env KGMAKER_REQUIRE_WORKERS=1 \
  KGMAKER_REQUIRE_K2=1 KGMAKER_REQUIRE_SPRING_IMPORTS=1 \
  KGMAKER_REQUIRE_SPRING_CONDITIONS=1 KGMAKER_TEST_MAVEN_REPOSITORY=/workspace/tools/m2 \
  KGMAKER_WORKERS_HOME=/workspace/kafka-bindings/workers \
  PYTHONPATH=/workspace/kafka-bindings/src /workspace/kgmaker-venv/bin/python \
  -m pytest -q -rs --tb=short --basetemp=/tmp/kgmaker-kafka-final-full \
  --junitxml=/tmp/kgmaker-kafka-final-full.xml
```


Před spuštěním final full odhalila kontrola helper callsite ještě explicitní
default profile gap: při `profiles: []` chyběl aktivní Spring profile `default`.
Actual properties regression **2 FAIL, 3 PASS v0.55s** pro default a grouped
default/prod; reuse nyní předává stejný default set jako S05-W03. Vlastní full
byl tehdy stále pouze queued a byl bezpečně zrušen před pytest child, nikoli
přerušen validní running test. Nový full běžel až nad touto opravou.
Po opravě **54 PASS, 2 DESELECTED v3.49s** (čistě offline+workspace sada).

Finální strict full s mandatoryWorkers/K2/SpringImports/SpringConditions:
**613 PASS, 10 SKIP v406.80s**; exit0, JUnit/log zachovány. Povinné K1/K2 a
pinned Spring6.2.2/Boot3.4.2 APIs skutečně běžely. Skips jsou pouze optional
Maven/Gradle/installed exporters/variants/plugins a skutečný Windows gate;
nevydávají se za PASS. Actual fixture CLI query `orders-blue` také prošel.
Scoped semantic update/apply/validate/scan/check a `git diff --check` PASS;
původních115 epizod z explicitního stacked baseline zůstává immutable prefix.
Capture implementační paměti zachovává tuto historii; žádné nové core semantic
vazby se nevymýšlejí, pouze se aktualizuje skutečně posunutý ownership target.
