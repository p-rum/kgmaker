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


## Review oprava citlivých property references (2026-10-27)

Root publikoval DraftPR51 z kandidáta `8dd2d58` nad explicitním stacked baseline
`78d7968`; žádné CI/merge tím není doložené. Nezávislý actual review našel P1:
`orders.topic=${spring.kafka.password}` v aktivním application-blue.properties
rozbalil existující syntetické heslo jako RESOLVED topic a vytvořil match.
Předchozí613PASS tento pozdější negativní případ nepokrývá. Public regression
před opravou: **23 FAIL, 1 PASS v2.22s** (benign případ prošel).

`kafka-binding-2` před každým destination/binder lookupem odmítá citlivý key,
včetně transitive aliases a captured overrides. Normalizuje case/separators pro
password/passwd/secret/credential/authorization/API-key/token/username/JAAS a
bootstrap-server families; stejné bounded16-step/cycle guard. Žádný citlivý value
se nečte pro odvození topic/cluster identity, nevstupuje do diagnostiky a nevytvoří
match. Výsledek zůstává UNKNOWN s obecným unresolved reason.

Read-only kontrola současně potvrdila, že workspace původně kopíroval celé
captured Spring property mapy do veřejného graph.contexts. Parent schválil
narrow Kafka-only postvalidation projection: původní kontext se nejprve vybere
a ověří; až veřejná deep-copy reprezentace nahradí citlivé values `<redacted>`
a reuse inspection sanitization. `spring_properties_projection` uchovává
original_context_id, hash původní mapy a redacted:true. Původní selection key,
condition hash, source hashes i persisted index/cache zůstávají beze změny.
Redigovaná mapa se nevydává za vstup ověřující původní hash. Stejná ochrana mapy
platí i u non-JVM kontextu, bez změny selectoru/framework metadat; workspace bez
Kafka zachová původní chování. Žádná globální freshness/selector migrace.

Offline focused po první opravě: **78 PASS, 2 DESELECTED v6.79s**. Rozšířená
public workspace/availability sada: **90 PASS, 2 DESELECTED v8.23s**. Testy
kontrolují přímé/nested references z properties i captured input, binder alias,
benign topic/binder positive, úplný export bez syntetického hesla, původní bytes
a cache, původní validaci kontextu a non-JVM selection identity. Jsou offline
fixtures zachycených vstupů, nikoli falešný compiler/toolchain PASS. Dva actual
K1/K2 případy jsou zde úmyslně deselected; jejich novou validaci/full nelze
vydávat za provedenou. Golden full vlastní shared lock, žádný souběžný heavy
test ani přerušení cizího testu neproběhlo.

Příkaz focused:

```bash
PYTHONPATH=/workspace/kafka-bindings/src /workspace/kgmaker-venv/bin/python \
  -m pytest -q --tb=short tests/test_kafka_bindings.py -k 'not actual' \
  tests/test_workspace.py tests/test_availability.py
```

Aktuální oprava zůstává local-only pro root review před push; žádný vlastní
publikační retry, CI retry nebo merge. Změna upřesňuje existující AC03, nepřidává
nový task/milník ani runtime/data availability proof.


### Zachování public T006 selection po redakci

Nezávislé review `2fff818` potvrdilo opravu sensitive expansion, ale odhalilo
kompatibilitu: T006 validoval redigovanou property mapu proti původnímu condition
hash a vracel STALE_CONTEXT. Vlastní full byl stále pouze queued a byl bezpečně
zrušen před pytest child; neproběhl žádný test ani PASS. Persistent stop reason
je ve validation adresáři. Po opravě collection typo v novém testu (1 collection
error, žádný PASS) actual public pozitivní regression před runtime opravou:
**1 FAIL, 81 DESELECTED v0.27s**, přesné STALE_CONTEXT z T006.

Root a architect schválili bounded gate v existujícím workspace/T006: načíst
právě jeden původní kontext z explicitního checkout graph.json, znovu odvodit
celou qualified/redacted reprezentaci a přesně ji porovnat s public kontextem
včetně repo alias. Recompute raw selector a stávající validator poté ověří
původní condition/source/classpath/worker snapshot. Marker ani hash samostatně
není důkaz. Soukromý kontext neopustí helper, nepřepisuje public context/store/cache.
Bez explicitního root, s missing/duplicitním store kontextem, forged
marker/hash/id/map/repo/selector/condition nebo stale source/classpath gate
fail closed bez procesů a bez mutace. Unprojected cesta zůstává původní.

První public Kafka/workspace/availability/T006 focused: **113 PASS, 2 DESELECTED
v11.78s**; s pozitivním repo aliasem producer→local **114 PASS, 2 DESELECTED
v14.09s**. Reálné K1/K2 případy nyní rovněž žádají T006 selection nad citlivým
captured input a hlídají private store; novou actual/full validaci nelze
vydávat za dokončenou. Žádný souběžný heavy test ani external write.


### Finální proof nad privacy/T006 opravou `581667b`

Povinný preflight prošel beze sestavení/instalace. Pod jedním shared flockem
nejprve **2 actual K1/K2 PASS v6.83s**: genuine inspect_jvm private capture →
redacted public workspace → T006 CURRENT selection a private store beze změny.
Pouze po exit0 tohoto prerequisite se spustil strict full:
**656 PASS, 10 SKIP v454.81s**, exit0. Povinné Workers/K2/SpringImports/
SpringConditions APIs skutečně běžely; deset skips je pouze optional Maven/
Gradle/exporter/variant/plugin a skutečný Windows gate, nikoli PASS.

Aktuální offline public Kafka/workspace/availability/T006 sada má **114 PASS,
2 DESELECTED v10.21s**; její dva actual případy ověřil oddělený prerequisite
a následně full. Historical613PASS i původní queued/cancelled pokus nejsou
vydávané za proof nové opravy. Root/architect source review potvrdil původní
P1 i T006 kompatibilitu; finální pair čeká na samostatné potvrzení po metadata.

Veškeré nové plné artefakty jsou v persistent
`/workspace/validation/kafka-privacy-581667b/`: preflight.log, actual.log/actual.xml,
actual-exit-status.txt, full.log/full.xml, exit-status.txt a vlastní basetemp.
Předchozí RED, collection error a cancelled queue stop reason jsou zachované v
`/workspace/validation/kafka-privacy-2fff818/`; žádný cizí validní test se nerušil.

```bash
export JAVA_HOME=/workspace/tools/jdk-21.0.6+7
export PATH="$JAVA_HOME/bin:/workspace/tools/kotlinc/bin:$PATH"
# Děděný PATH zachovává managed Node; Maven/Gradle nejsou exponované.
/workspace/kgmaker-venv/bin/python /workspace/kgmaker-test-prerequisites.py /workspace/kafka-bindings
flock /workspace/kgmaker-heavy-tests.lock env KGMAKER_REQUIRE_WORKERS=1 \
  KGMAKER_REQUIRE_K2=1 KGMAKER_REQUIRE_SPRING_IMPORTS=1 \
  KGMAKER_REQUIRE_SPRING_CONDITIONS=1 KGMAKER_TEST_MAVEN_REPOSITORY=/workspace/tools/m2 \
  KGMAKER_WORKERS_HOME=/workspace/kafka-bindings/workers \
  PYTHONPATH=/workspace/kafka-bindings/src /workspace/kgmaker-venv/bin/python \
  /workspace/validation/kafka-privacy-581667b/run.py
```

`run.py` pouze spustí explicitní pytest actual prerequisite a po exit0 tentýž
Python execne do full pytest; persistent logs/XML/basetemp má mimo `/tmp`.
Source/worker/test bytes po zahájení validace zůstaly frozen. Finální metadata
obsahují scoped semantic update/apply/validate, capture nové implementační
paměti, scan/check a diff check. Root publikuje až po review; autor nic neposílá,
neopakoval CI a nemerguje. Nadřazený S07 zůstává PARTIAL, runtime/data UNKNOWN.
