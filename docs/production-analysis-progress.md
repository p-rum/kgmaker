# Produkční analýza: inventura a průběh

Ověřená cílová větev `origin/main`: `8ac80ca30f6f680539deb7fb3590519d3a5c1460`.
Historická reference je stejný commit. Baseline regrese: Python 3.12.14,
`PYTHONPATH=src python -m unittest discover -s tests -q`: 98 testů PASS.
Tabulka popisuje skutečný stav, ne deklaraci dokončení celého zadání.

| Požadavek / milník | Existující implementace | Chybějící část | Důkaz baseline | Plánovaný PR |
|---|---|---|---|---|
| P0, původní M0: compiler pilot | Žádný worker | Mixed JVM, TS compiler, CFG, měření a matice | scanner.py používá CALL_TOKEN; žádné worker adresáře | compiler spike |
| P1 / CL-01–05, EV-01, BC-01 | Schema v1, společný index | Nezávislé osy, scope před resolution, migrace | model.py, scanner.py, test_scanner.py | evidence production scope |
| P2 / M1 / BL-01–05 | Offline čtení Flyway konfigurace | Effective Maven/Gradle model, runner, build/result/manifest | flyway.py není build adaptér | build context |
| P3 / M2 / JV-01–05 | Heuristická volání ze souboru | Compiler symboly, bytecode, CHA, CFG, def-use | scanner.py, dataflow.py | JVM resolution |
| P4 / M3 / SP-01–04 | Anotační vzory | Symbolové Spring wiring, podmínky, proxy | domain.py | Spring evidence |
| P5 / M4 / DB-01–04 | Flyway replay, schema scope, omezené ORM porovnání | Java/Kotlin entity model, query resolution | schema_replay.py, test_flyway.py | persistence evidence |
| P6 / IN-01–04 | Kafka/REST literály, explicitní workspace service mapping | Framework verze, execution/subscription, cluster scope | domain.py, test_analysis.py | integrations |
| P7 / TS-01–04 | TS syntaktické vzory a explicitní kontrakty | Program/TypeChecker, callback resolution, UI adaptér | scanner.py, test_analysis.py | TypeScript worker |
| P8 / RK-01–04, FLOW-01–04 | Navigační skóre, architecture Mermaid | Execution ranking, CFG/process views a parser ověření | store.py | evidence views |
| P9 / M5 / EV-01–04, BC-01–03 | Obsahové feature/workspace cache, strict availability | Worker atomická publikace, build/context invalidace, CI/benchmark | feature.py, workspace.py, availability.py | release integration |
| P10 / M6 / RT-01–03 | Omezené supplied observations | Oddělený runtime import | availability.py | volitelný runtime import |

Povinnosti původního M0–M5 zůstávají otevřené, pokud nejsou doložené konkrétním testem.
Existující Flyway, workspace a availability se rozšiřují; nevzniká druhá implementace.

| Milník | Stav | Evidence |
|---|---|---|
| P0 | PARTIAL | Baseline a gap matrix ověřeny; compiler pilot dosud nedokončen |
| P1 | PARTIAL | Schema v2, scope partition, classifier; 110 Python testů PASS, CL-01/02 metamorfní test PASS; ostatní CL pouze source-only podmnožina |
| P2 | NOT_STARTED | Effective build model a execution dosud nejsou implementovány |
| P3 | NOT_STARTED | Žádné compiler-resolved JVM facts |
| P4 | NOT_STARTED | Žádný symbolový Spring adaptér |
| P5 | PARTIAL | Zachovaný baseline Flyway; rozšíření ORM dosud chybí |
| P6 | NOT_STARTED | Nové integrační adaptéry chybí |
| P7 | NOT_STARTED | TS compiler worker dosud chybí |
| P8 | PARTIAL | Explicitní ranking profil a ranking invariants PASS; CFG renderer dosud chybí |
| P9 | PARTIAL | Evidence refs, mixed snapshot rejection a atomický zápis test PASS; úplná acceptance suite dosud chybí |
| P10 | NOT_STARTED | Volitelný milník |
