# T003-S07-W04 — Kafka binding a identita topicu

- Work package ID: `T003-S07-W04`
- Milník: `T003-S07`
- Revision: 2
- Datum: 2026-11-03
- Stav: SPECIFICATION; tento soubor popisuje cílové chování, nikoli hotovou implementaci.
- Baseline revize2: merged PR51/main `ef3ab4050289aafd557caa5414c594698da006ea`. Původní draft stack0797 byl před kódem aktualizován na tento merged parent. Revize1 dodává pouze deklarované config bindingy; její původní důkazy zůstávají oddělené. PR51 je merged; tato revize má samostatný PR a vlastní acceptance.
- Závislosti: T003-S05-W03; revize1 PR51; merged T003-S07-W01 argument proof a T024 pinned Spring Kafka3.3.2 API fixture; průřezové požadavky `T003-R01–R10`.
- Nadřazená acceptance: `T003-AC07`.

## Cíl

Mapovat producer/consumer binding, topic, cluster, service realm a payload z podporované konfigurace.

## Rozsah a konkrétní kontrakty

- Primární místa změny: `src/kgmaker/domain.py, src/kgmaker/framework.py, src/kgmaker/workspace.py`.
- Reuse existující model/store/provider/workspace/evidence vrstvy; nevytvářej paralelní katalog ani odlišnou identitu entity.
- Zachovej SOURCE_ONLY, nulové implicitní spouštění buildů, instalací, migrací a aplikace a atomickou publikaci poslední validní generace.
- Výsledek s neúplnou evidencí musí být PARTIAL/UNKNOWN s konkrétním důvodem; confidence nesmí nahrazovat chybějící důkaz.
- Veřejnou změnu současně promítni do README, capability dokumentace, CLI příkladů a stavové/acceptance matice.

## Implementační kroky

1. Před kódem ověř současný kontrakt ve zdroji, testech a knowledge graphu; zapiš přesnou podporovanou matici a failing acceptance.
2. Rozšiř stávající datový model a versioned protocol pouze o pole nutná pro tento work package; popiš migraci a kompatibilitu v1/v2/v3.
3. Implementuj pozitivní cestu, lokalizovanou diagnostiku a nulovou mutaci při invalidním vstupu, timeoutu nebo zrušení.
4. Přidej produkčně věrnou fixture a negativní/ambiguous variantu: dva clustery se stejným topicem, profile override a dynamic topic.
5. Aktualizuj acceptance inventář, `docs/production-analysis-progress.md` a nový český `docs/changes/<N>_<shortName>.md` skutečnými výsledky.

## Požadavky na testování

- Test musí ověřit: dva clustery se stejným topicem, profile override a dynamic topic.
- Spusť nejmenší relevantní testy, potom celý `python3 -m pytest -q`; worker/build task navíc spustí příslušný skutečný toolchain test.
- Ověř `git diff --check`, nulové implicitní procesy v offline cestách a nulovou mutaci store při chybě.
- Chybějící povinný toolchain je FAIL/BLOCKED/SKIP dle matice, nikdy PASS. Do change note napiš přesné příkazy, výsledky a neprovedené kontroly.

## Akceptační kritéria

- **T003-S07-W04-AC01:** Shoda vyžaduje cluster+topic+contract/release; dynamic hodnota je unresolved.
- **T003-S07-W04-AC02:** Staré podporované vstupy a graph/store schema zůstávají čitelné nebo mají výslovně otestovanou migraci.
- **T003-S07-W04-AC03:** Negativní a nejednoznačný případ nevytvoří silnější evidence ani dostupnost, než dovolují vstupy.
- **T003-S07-W04-AC04:** Stavová matice odkazuje na konkrétní test/fixture/verzi a nepovýší celý milník nad skutečně ověřený scope.

## Větev, PR a Definition of Done

- Implementuj výhradně v samostatné větvi, doporučeně `feat/t003-s07-04-kafka-binding-identity`; do stejné větve nepřidávej jiný work package.
- Na konci vytvoř samostatný pull request do aktuálně určené cílové větve. PR musí odkázat na tento soubor, `T003-S07`, nadřazenou acceptance a nový change note; bez explicitního pokynu jej nemerguj.
- Hotovo znamená implementovaný omezený kontrakt, zelené požadované kontroly, aktualizované docs, validní sémantický patch/scan podle projektových instrukcí a zdokumentované zbývající hranice.


## Explicitní rozšíření revize2 — code binding a subscription metadata

Tato sekce je SPECIFICATION cílové dodávky; není tvrzením implementace ani
splnění T012. Důvod: revize1 správně uvádí code_binding UNPROVEN a nemá groups,
original listener/send IDs ani regex subscriptions, takže sama nesplní T012-AC02.
Rozšíření vzniká v samostatném PR/větvi `feat/t003-s07-04-kafka-code-bindings`;
nevkládá se do již schváleného rozsahu PR51 ani dovnitř T012.

### Kontrakty a hranice

- `T003-S07-W04-R01`: Zachovat schema1 a výstupy kafka-binding-2 čitelné. Nová
  aditivní výstupní verze kafka-binding-3 odděluje declared config, compiler/code
  fact, framework inference a runtime. Config-only zůstává code UNPROVEN.
- `T003-S07-W04-R02`: Consumer config group pochází pouze z přesného explicitního
  `spring.cloud.stream.bindings.<binding>.group`, přes stávající bounded property
  resolver/profile precedence/privacy a content hashes. Uchovat value/status/origin,
  exact key a input provenance. Missing/dynamic/sensitive group zůstává UNKNOWN;
  group se neodvozuje z binding/service/topic/broker jména nebo počtu consumerů.
- `T003-S07-W04-R03`: Exact canonical
  `org.springframework.kafka.annotation.KafkaListener` raw typed method annotation
  může dodat versioned FRAMEWORK_DERIVED listener fact: original method/listener ID,
  optional explicit annotation id, explicit nonempty groupId, topics array nebo
  topicPattern a original context/path/SHA/range/owner/name/descriptor/scope.
  Všechna pole se musí shodovat s canonical Node, compiler metadata a captured
  source_files. Values unresolved, compiler errors, cizí FQCN, scope nebo SHA
  nevytvoří current registration proof. Bez explicit groupId se v této revizi
  nehádá idIsGroup/containerFactory/default group. Repeatable/meta annotations,
  SpEL a dynamická registrace jsou přiznané UNKNOWN hranice.
- `T003-S07-W04-R04`: Aditivní manifest schema2 smí mít explicit code_ref na již
  existující selected-context listener method fact nebo producer callsite.
  Selector samotný není důkaz: ověřit origin ID, context, source hash/range,
  canonical scope, service ownership a topic/group agreement. Žádný join podle
  podobného názvu či samotného topicu. Schema1 code refs nemá a dál zůstává
  code UNPROVEN. Literal listener fact smí existovat i bez config joinu; broker
  realm je pak UNKNOWN, nikoli odvozený z bootstrap URL.
- `T003-S07-W04-R05`: Producer proof vyžaduje skutečný Javac compiler callsite na
  exact dependency KafkaOperations/KafkaTemplate.send contract a typed literal
  topic argument z existujícího validovaného call/argument IR. Zachovat call ID,
  source/SHA/range/context a symbol evidence. NewTopic, ProducerRecord construction,
  custom wrappers, nepodporované overloads a Kotlin K1/K2 producer argument proof jsou
  UNKNOWN/configuration-only, nikdy publisher execution.
- `T003-S07-W04-R06`: Subscription identity reuse graph/workspace evidence
  konvence a zachovává broker realm, original listener logical identity, selector
  a explicit group. Dvě groups vytvářejí odlišné subscription identity; dva realms
  se stejným topicem se nesloučí. Context/content vytvoří revision/evidence,
  nenahrazují origin code IDs. Regex selector je pouze REGEX candidate: uchovat,
  neexpandovat na topics a nematchovat jako exact producer delivery.
- `T003-S07-W04-R07`: Reuse existing Graph/Node/Edge/evidence/workspace/store,
  Kafka resolver a captured compiler metadata/IR. Žádný druhý store, nový source
  parser, broker/registry klient, Spring context, implicit build/install/network
  nebo runtime/data availability důkaz. Placeholder resolving pouze z explicitně
  captured properties se stejnou privacy/content hranicí.

### Implementační kroky revize2

6. `T003-S07-W04-S06`: Upravit toto zadání/registr/change note, durable analyze/plan,
   ověřit current contracts a skutečný RED před implementací; poslat bounded brief.
7. `T003-S07-W04-S07`: Versioned canonical listener/send adapter nad raw annotations
   a validovaným Javac IR; explicitní UNKNOWN a evidence/context guards.
8. `T003-S07-W04-S08`: Version3 group config, schema2 code refs a current verified
   join/subscription identity přes existující workspace/Kafka pipeline.
9. `T003-S07-W04-S09`: Actual API fixture + negativy, focused/full checks a public
   docs/semantic/memory; samostatný PR a exact-pair review po merged PR51.

### Nová acceptance revize2

- `T003-S07-W04-AC05`: Actual canonical Java a podporované K1/K2 annotation capture
  s topics array, dvěma explicit groupId, optional explicit listener id a regex;
  zachovat origin code IDs a separate groups/realms. Fake FQCN a compiler errors
  zůstanou UNKNOWN. Backend bez potřebného annotation proof se nepovyšuje.
- `T003-S07-W04-AC06`: Schema1 regression a explicit schema2 exact code ref ověří
  current context/SHA/scope/ownership/subscription agreement; foreign/stale/
  malformed/config-only nevytvoří code binding ani runtime claim. Selected profile
  override, unresolved/sensitive group a alias-chain privacy mají skutečné testy.
- `T003-S07-W04-AC07`: Actual Javac canonical send literal topic vytvoří pouze
  statický producer-origin proof v obou worker backendech (oba reuse Javac JavaFrontend); NewTopic/ProducerRecord/custom wrapper a
  unsupported Kotlin producer zůstanou UNKNOWN. Regex nevytvoří exact topic match.
- `T003-S07-W04-AC08`: Source/config mutation invaliduje proof bez implicitního
  procesu/transportu a se zachováním vstupů/poslední validní generace. Input and
  evidence hashes zůstávají content-bound; legacy graph/store v1/v2/v3 čitelné.
- `T003-S07-W04-AC09`: README/capability/acceptance/progress/change note popisují
  skutečný subset a výsledky. T012 může vzniknout až po schváleném upstream
  kontraktu; jeho vlastní AC01–05 nejsou touto revizí automaticky splněné.

Ověření: explicitní API-only fixture z process-triggers pinne skutečné Spring
Kafka3.3.2 a Spring6.2.2 JAR/POM/license hashes. Příprava/běh compiler testů je
explicitní; nic nespouští broker, Spring aplikaci ani vlastní app code. Nejprve
nejmenší skutečný RED/positive/negative matrix, pak relevantní integrace a jeden
strict full s required toolchains, --maxfail=1, immutable input receipt a shared
heavy lock. Missing mandatory fixture není PASS. Před merge je potřeba splnit
původní AC01–04 i AC05–09; GH CI je doplňující dle T045, ostatní gates zůstávají.

### Upřesnění skutečné vstupní matice revize2

Python adapter dodává listener facts pouze tam, kde aktuální compiler zachytil
canonical method annotations: Java/Javac v obou backendech a Kotlin K1. Pinned
Kotlin K2 backend zachytí metody bez annotations a explicitně hlásí
`K2_SOURCE_MODEL_PARTIAL`; tento vstup zůstává UNKNOWN bez source parser fallback.
Producer je omezen na Java/Javac v obou backendech, přesný dvouargumentový
`send(String,Object)` s přímým ASCII string literal topicem. Named constants,
escaped literals, Kotlin bodies, wrappers, ProducerRecord a NewTopic nejsou
pozitivním code proof v této revizi. Rozšíření workeru je samostatná budoucí práce.
