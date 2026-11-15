# T029 — Chybové větve procesu, deklarované retry/DLT a návrhy kompenzace

Výchozí main `7bb8b8d389c461c684197704203a99dcb2b83724`, tree
`8542cbdeb0339af20b52d1448baf878866e76e92`. Zadání
[T029](../tasks/T-029_project-process-failures.md), revize 1, S01–S05/AC01–AC06.
Dodání PR_OPEN; specifikace zůstává cílem. Full suite NOT_RUN podle výslovného
uživatelského targeted-only pokynu, který přebíjí starší profil/specifikaci.

## Krok 1 — source rekognoskace a RED (T029-S01–S04, AC01–AC05)

Baseline výše. Izolovaný checkout `/tmp/kgmaker-t029`; root ani ostatní pracovní
větve se nemění. `git merge-base --is-ancestor` pro T025 `32a3bca46d62f3715d1fb2d96dd6f0e92f941dc6`,
W05 `3e5ef0f0c56c406a5428e826120ca525774b373f` a T028 `8f023bc65396f1f7feec757f78effd8a0d9c33fd`
— PASS. `./kgmaker status`, query a memory recall explicitně hlásily chybějící
machine index; neexistující pre-task memory se nevymýšlí. Rekognoskace podle
kgmaker-context/architect proběhla přímo ve zdroji a existujícím GRAPH.md.
Task workflow `task:1129cf045c0c644e870a2f986e5f14b1993e35903e8013de835a602f738c4367`
obsahuje skutečný analyze/plan brief a implementační context.

`control_flow.py` již odděluje finally pokračování pro normal/return/throw;
T025 uchovává původní bloky/call-site/CFG proofs a T026 validuje uložené členství
skupin. `kafka_retry.policy_boundaries` je čistý replay `kafka-retry-1`: Java/K1,
pinned Spring Kafka 3.3.2, literal attempts/suffix a jednoznačný DltHandler.
K2 annotations a nepodporované konfigurace zůstávají UNKNOWN. `flow.process`
vrací policies odděleně od execution CFG; T029 nemění flow.py ani workery.
ProcessView má existující transaction_boundary a oddělené semantic_annotations;
žádný nový Spring transaction resolver ani store není potřeba.

Veřejné RED testy `tests/test_t029_project_process_failures.py`: finally clone
path preservation po collapse, local transaction + HTTP/Kafka, PROPOSED
kompenzace a invalid/offline/last-artifact preservation.

```sh
PYTHONPATH=src:tests PYTHONDONTWRITEBYTECODE=1 /tmp/kgmaker-test-venv/bin/python -B -m pytest -q -p no:cacheprovider tests/test_t029_project_process_failures.py
```

**FAIL 8 / 0 SKIP, 0.66 s**: veřejné API zatím neexistuje. Actual fixture první
pokus měl 3 ERROR, 8 deselected, 0.64 s: převzatý W05 helper požadoval i nepoužitý
Spring Kafka 3.2.0 JAR. T029 fixture používá jen dostupné ověřené 3.3.2 API přes
`actual_prerequisites`/`extra_api_jars`; není tím potvrzena nová W05 version matrix.
Žádná implicitní instalace ani build aplikace neproběhl. Připravené worker outputs
jsou pouze dočasně připojeny symlinky target/target-k2, obsah se nemění.

## Krok 2 — čistá failure projekce (T029-S01–S04, AC01–AC05)

Baseline `7bb8b8d389c461c684197704203a99dcb2b83724`. Změny pouze v
`src/kgmaker/business_process.py` a vlastním testu: aditivní pure API
`project_process_failures`, opětovně použitý ProcessView/KnowledgeGraph a
`kafka_retry.policy_boundaries`/T025 CFG certificates. Žádná změna flow.py,
framework produceru, process_model schématu ani workerů.

Původní CFG uzly/hrany a catch/finally continuations se nemění. T026 skupina se
rozbalí jen z validovaného uloženého členství. Policy se váže na origin method,
vybraný owner/context/scope a jeho doložený exceptional_exit; normální exit ani
callee výstup netvoří retry origin. Retry→DLT jsou statické potenciální hranice,
bez unrollingu, delivery nebo úspěchu. Graph=None/legacy/missing authority zůstane
UNKNOWN. Raw policy a compiler proofs se zachovávají přesně v UNKNOWN
PROVENANCE_REFERENCE_ONLY obálce; obálka sama není authority pro admission.
Odmítnuté proofs/policy zůstávají viditelné. Limit má explicitní omitted IDs a
truncated coverage, původní diagnostiky/limity se neztrácejí.

Transaction_boundary má LOCAL_DECLARATION_ONLY/rollback UNKNOWN; vzdálené
HTTP/Kafka hranice local_transaction_rollback NOT_PROVEN. Kompenzace používá jen
existující PROPOSED semantic annotation, exact refs a žádné technické hrany.
Migrace není potřeba, graph v1/v2/v3 zůstává čitelný bez vymyšlených policy facts.

Actual RED po zúžení API prerequisites: **2 FAIL (Java/K1 API absent), 1 ERROR
(K2 bez Kafka triggeru), 8 deselected, 8.20 s**. K2 fixture nyní explicitně ověřuje
absenci Kafka triggeru/declared policy; nepředstírá pozitivní K2 podporu. První
GREEN pokus: **2 FAIL / 9 PASS, 8.42 s** — fixture zachytila repo_id=local, ale
workspace očekával backend. Opraven pouze explicitní capture tuple fixture na
backend; upstream guard zůstal přísný. Následně **11 PASS / 0 SKIP, 9.60 s**.

Rozšířená authority matice nejprve **2 FAIL / 42 PASS, 9.76 s**: stale process
proof fixture ponechala CURRENT souhrny, správně odmítnuto validátorem. Opravena
fixture na konzistentní stale souhrny, bez oslabení modelu. Poté **2 FAIL / 44 PASS,
13.99 s**: prázdné refs vyžadují prázdný evidence_kinds, ne odhad UNKNOWN kind.
Testová agregace to zachovala. Přidaný service-selection guard první běh
**2 FAIL / 44 PASS, 14.22 s** zaměnil owner `service:orders` za manifest klíč
`orders`; opravené přesné canonical mapování nyní zachovává test/scope/stale
negativy. Nová explicitní unproved-policy regrese pokrývá i boundary bez proofs.
Tyto výsledky nejsou vydávány za aktuální finální PASS.

Všechny actual příkazy používají JDK21, připravené workery, Python test venv,
`JAVA_TOOL_OPTIONS=-XX:-UsePerfData` (test-only host nastavení), žádnou instalaci.
Přesný cílený finální příkaz a výsledek jsou zaznamenány v kroku 3.

## Krok 3 — cílená regrese a diagnostický follow-up (T029-S04, AC01–AC05)

Baseline `7bb8b8d389c461c684197704203a99dcb2b83724`; zdroj/test z kroku 2.
Přesný společný příkaz:

```sh
JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 JAVA_TOOL_OPTIONS=-XX:-UsePerfData PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 KGMAKER_WORKERS_HOME=/tmp/kgmaker-pr97-reconciled/workers PYTHONPATH=src:tests PYTHONDONTWRITEBYTECODE=1 /tmp/kgmaker-test-venv/bin/python -B -m pytest -q --tb=short -p no:cacheprovider --basetemp=/tmp/kgmaker-t029-pytest tests/test_t029_project_process_failures.py tests/test_t025_build_local_process_path.py tests/test_t026_collapse_business_steps.py tests/test_t027_cross_http_process_boundary.py tests/test_t028_cross_async_process_boundary.py
```

**PASS 281 / 0 SKIP, 44.31 s**. Včetně skutečných Javac/K1/K2 producerů,
T025 CFG/call-site vazeb, T026 certifikovaného collapse, T027 exception/request
negativů a T028 async authority/fanout regresí. Log `/tmp/t029-targeted.txt`.

Závěrečný source audit našel lokální mezeru: přenos graph diagnostics pokrýval jen
context_id/source_id, ne globální relevantní diagnostic/context_ids. Úzký follow-up
v `business_process.py` zachovává relevantní globální/selected diagnostiky a jejich
explicitní `truncated=True`; test/foreign diagnostics nejsou přimíchány.
Nový test `test_unscoped_upstream_truncation_and_selected_diagnostics_survive`
a tři malformed-graph veřejné negativy doplnily matici. Po této změně proběhla
celá dotčená T029 sada následujícím příkazem:

```sh
JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 JAVA_TOOL_OPTIONS=-XX:-UsePerfData PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 KGMAKER_WORKERS_HOME=/tmp/kgmaker-pr97-reconciled/workers PYTHONPATH=src:tests PYTHONDONTWRITEBYTECODE=1 /tmp/kgmaker-test-venv/bin/python -B -m pytest -q --tb=short -p no:cacheprovider --basetemp=/tmp/kgmaker-t029-pytest-final tests/test_t029_project_process_failures.py
```

**PASS 60 / 0 SKIP, 13.02 s**, log `/tmp/t029-final.txt`. Předchozí 281 PASS je
samostatný dřívější regresní běh, nikoli předstírané opakované ověření nového kódu.
Nezměněné moduly nebyly znovu bezdůvodně testovány. Testy používají vlastní basetemp
kvůli paralelním izolovaným agentům. Full suite NOT_RUN; runtime delivery/rollback,
broker/DB, deployment a obecná compensation inference NOT_RUN/nepodporováno.
Skutečný Spring Kafka 3.2.0 unsupported API gate NOT_RUN: pinned JAR není v dostupné
cache. Metadata/rules unsupported verze, stale/foreign/current-selection negativy
jsou ověřené; nejde o náhradu chybějící actual 3.2.0 gate.

## Krok 4 — dokumentace a kompatibilita (T029-S05, AC06)

Stejná baseline. README odkazuje na nové pure API; `docs/process-paths.md` uvádí
přesnou signaturu, příklady, explicitní UNKNOWN, limity, Java/K1 supported a K2
negative-only rozsah. CLI bez změny: nový příkaz/store/render formát se nezavádí;
T034/T035 jsou oddělené úlohy. `docs/production-analysis-progress.md` odděluje dodání
od ověření, `docs/acceptance-inventory.md` mapuje každé AC na veřejný konkrétní test.
Task registry/spec beze změny identity/revize/závislostí — bez dopadu. Instalované
instrukce/templates se nemění — bez dopadu. Framework/worker/kafka-retry capability
zůstává nezměněným upstream kontraktem, žádný nový resolver nebo runtime důkaz.
Generované grafy a skutečná semantic/memory evidence se zaznamenají v kroku 5.

## Krok 5 — source-backed semantic údržba (T029-S05, AC06)

Baseline `7bb8b8d389c461c684197704203a99dcb2b83724`, původních 48 konceptů /
157 vztahů / 310 epizod. Použit kgmaker-semantic skill, aktuální packet a skutečný
zdroj, nikoli spekulativní business data. Nový koncept popisuje pouze statickou
failure projekci; implementace/API/actual test mají tři přímé EXTRACTED vztahy.
Šest dotčených konceptů a šestnáct původních vztahů se zachovává, reanchor ověřuje
base source hash a identický citovaný řádek; nulová remove pole.

První `semantic apply` byl správně odmítnut: navržený relation kind `documents`
není v aktuálním registru. Artifact zůstal beze změny, následující validate proto
hlásilo původní stale source hashes. Patch používá doložený registrovaný `cites`
pro API dokumentaci; nový packet a source scan jsou připraveny před dalším apply.
Tento historický FAIL není vykazován jako PASS.

```sh
./kgmaker semantic update --base 7bb8b8d389c461c684197704203a99dcb2b83724 --note docs/changes/130_projectProcessFailures.md
./kgmaker scan --no-docs
python3 /tmp/t029-semantic-patch.py
./kgmaker semantic apply
./kgmaker semantic validate
```

Opravený apply/validate — **PASS**. `python3 /tmp/t029-preservation.py` — **PASS**:
všech 48 původních konceptů, 157 vztahů a 310 přesných epizod zachováno. Původní
business_process.py prefix je byte-identický; flow.py/process_model.py/
process_paths.py/framework.py/kafka_retry.py beze změny. Dočasné worker symlinky
odstraněny. Nový source-backed stav před capture: 49 konceptů / 160 vztahů / 310 epizod.

```sh
python3 /tmp/t029-preservation.py
./kgmaker memory capture --base 7bb8b8d389c461c684197704203a99dcb2b83724 --validation targeted=passed --validation semantic-preservation=passed --validation full-suite=skipped
```

Capture **PASS**, skutečná epizoda
`episode:dc8f9f9ec3f394a2e2306b852e54ff1ab044e2a5e37f08c291be9081dd3e8305`;
výsledný stav **49 konceptů / 160 vztahů / 311 epizod**. Capture je skutečná
postimplementation údržba nad explicitní Git baseline, nikoli dodatečně smyšlená
pre-task recall. Finální graf se generuje příkazem, není ručně editován.

Před publikací `git ls-remote git@github.com:p-rum/kgmaker.git refs/heads/main
refs/heads/feat/t029-project-process-failures` potvrdil main `7bb8b8d` a novou
větev bez kolize. Open PR search ukázal pouze historický draft4; W09 ještě není
merged, proto jeho nepublikovaný flow.py nepřebíráme. Main max change127; parent
rezervoval 128/W09, 129/Criteria, 130/T029. Nové Task ID ani změna revision se
nevytváří. Dodávka PR_OPEN znamená samostatný PR; nezávislé review aktuální dvojice
base/HEAD a případná následná integrace nového main jsou stále potřebné.

Finální `./kgmaker scan`, `./kgmaker check`, `./kgmaker semantic validate`,
`python3 /tmp/t029-preservation.py` a `git diff --check` — **PASS**. Workflow má
skutečné implementation/test artefakty ve fázi review. První test artifact byl
odmítnut kvůli limitu 200 znaků pro command; uložená krátká runner část odkazuje
na plné prostředí/příkaz a skutečný výsledek v kroku 3. Nejde o nový test run.
Nezávislé review nenahrazujeme vlastní deklarací APPROVE. Zbývá review přesné
publikované revize a případné opravy; implementační agent PR nemerguje.

## Krok 6 — review fix konkrétního Kafka vstupu (T029-S02/S04, AC02/AC04/AC05)

Baseline `7dee1dd144de68a90ee6c82a0ccc70f2dddb2e2b`, tree
`7c3cb7523906050a44b5132fdf115554a245fcbe`. Nezávislé
[REQUEST_CHANGES](https://github.com/p-rum/kgmaker/pull/110#issuecomment-6900482722)
našlo P1: shoda listener metody/CFG ještě nedokládá vstup přes Kafka container.
Scheduler→private listener i root listener→jiný listener obyčejným Java voláním
získávaly neoprávněnou retry/DLT cestu. Původní tvrzení kroku 2 o callee se pro
annotovaný lokální callee nepotvrdilo; oprava a aktuální rozsah jsou zde.
Nezávislých 285 PASS / 0 SKIP, 45.88 s na starém HEAD tento nový případ nepokrývalo.

Rekognoskace ověřila konkrétní T025 root/call-site CFG identity, `_selected_trigger`
a T028 subscription→consumer import. `business_process.py` nyní rozhoduje pro
každý exceptional-exit occurrence zvlášť: canonical Kafka trigger je ověřen
existujícím T025 source/proof guardem, musí mít přesnou declaration→root entry
asociaci a root exit. Imported consumer navíc vyžaduje původní T028 subscription,
CONSUMER_POTENTIAL hranu, dohledatelné membership refs a stejný source process/revision.
Běžný callee má jiné call-site CFG IDs; zachová vlastní UNKNOWN boundary/raw refs
s důvodem KAFKA_ENTRY_OCCURRENCE_UNPROVEN, bez policy transition. Jedna legitimní
occurrence neautorizuje jinou occurrence stejné metody.

Cross-context subscription proofs se přesně zachovají uvnitř existující explicitní
UNKNOWN PROVENANCE_REFERENCE_ONLY obálky. Její target process context je metadata
projekce, ne přepsání raw scope/context. Obálka není authority; admission odděleně
kontroluje původní Kafka trigger a membership. Původní provenance v ProcessView
zůstává beze změny včetně odmítnutých stale/foreign/contradicting refs.

Dotčené soubory: `business_process.py`, vlastní T029 veřejné testy, README,
`docs/process-paths.md`, progress a acceptance. Veřejná signatura a ProcessView
schema zůstávají; derivation rules jsou `process-failures-2`. Dřívější výstupy v1
se stejně jako v2 nepoužívají jako vstup nové projekce, přepočet je z originálu.
Žádný nový resolver, worker, CLI/store/migrace ani změna flow.py. Příklady nyní
vysvětlují exact occurrence IDs a UNKNOWN callee. Registry/spec/managed templates
bez dopadu (stejná identita, revize, závislosti, příkazy).

Actual fixture testy recapture provádějí jen explicitně. První spuštění reviewer
skriptů selhalo 2 FAIL / 4 deselected, 4.53 s kvůli již odstraněné reviewer worker
cestě; není vykazováno jako funkční RED. Kopie `/tmp/t029-review-scheduler.py` a
`/tmp/t029-review-callee.py` mění pouze worker home na připravené
`/tmp/kgmaker-pr97-reconciled/workers`. Jejich skutečný RED: **2 FAIL / 4 deselected,
8.49 s**, po první opravě **2 PASS / 4 deselected, 8.56 s**. JDK21 a API JARy 3.3.2
jsou skutečné, nic se neinstalovalo, sdílený worker output se neměnil.

```sh
JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 JAVA_TOOL_OPTIONS=-XX:-UsePerfData PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 KGMAKER_WORKERS_HOME=/tmp/kgmaker-pr97-reconciled/workers PYTHONPATH=src:tests PYTHONDONTWRITEBYTECODE=1 /tmp/kgmaker-test-venv/bin/python -B -m pytest -q --tb=short -p no:cacheprovider --basetemp=/tmp/kgmaker-t029-review-red2 /tmp/t029-review-scheduler.py /tmp/t029-review-callee.py -k java
```

GREEN použil stejný příkaz s basetemp `/tmp/kgmaker-t029-review-green`.
Veřejné negativy pro oba callee prošly; při sestavování nové actual T012→T014→T025→
T028 fixture byly opravovány chybné testové property odkazy ProcessView/Definition
(2 PASS / 1 ERROR, 13.50 s; 1 FAIL, 7.24 s). Následný výsledek 8 PASS / 2 FAIL,
8.53 s odhalil cross-context reference mismatch a nevalidní stale-edge fixture bez
proofu. Raw proof se nyní zachovává v reference-only obálce; fixture používá platný
missing-association input. Tyto historické FAIL nejsou aktuální PASS.

```sh
JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 JAVA_TOOL_OPTIONS=-XX:-UsePerfData PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 KGMAKER_WORKERS_HOME=/tmp/kgmaker-pr97-reconciled/workers PYTHONPATH=src:tests PYTHONDONTWRITEBYTECODE=1 /tmp/kgmaker-test-venv/bin/python -B -m pytest -q --tb=short -p no:cacheprovider --basetemp=/tmp/kgmaker-t029-review-targeted tests/test_t029_project_process_failures.py tests/test_t025_build_local_process_path.py tests/test_t026_collapse_business_steps.py tests/test_t027_cross_http_process_boundary.py tests/test_t028_cross_async_process_boundary.py /tmp/t029-review-scheduler.py /tmp/t029-review-callee.py
```

Tento checkpoint: **301 PASS / 2 FAIL / 0 SKIP, 75.67 s**. Dva FAIL byly nové
negativní fixture assertions, které vybraly nested cleanup entry namísto skutečné
trigger→entry asociace. Všech 225 existujících upstream T025–T028 testů prošlo.
Čtyři PASS parametrizace externích reprodukcí mají K1/K2 early-return; nejsou důkaz
policy a finální příkaz je výslovně vyřazuje. Opravené fixture používají skutečnou
asociaci. Dodatečný guard ověřuje exact membership refs a shodu T028 link/subscription
identity; cizí membership metadata nemohou autorizovat import.

```sh
JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 JAVA_TOOL_OPTIONS=-XX:-UsePerfData PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 KGMAKER_WORKERS_HOME=/tmp/kgmaker-pr97-reconciled/workers PYTHONPATH=src:tests PYTHONDONTWRITEBYTECODE=1 /tmp/kgmaker-test-venv/bin/python -B -m pytest -q --tb=short -p no:cacheprovider --basetemp=/tmp/kgmaker-t029-review-final tests/test_t029_project_process_failures.py '/tmp/t029-review-scheduler.py::test_scheduled_local_listener_call_does_not_enter_kafka_retry[java]' '/tmp/t029-review-callee.py::test_listener_policy_does_not_apply_to_ordinary_local_callee[java]'
```

**75 PASS / 0 SKIP, 36.24 s**: všech 73 veřejných T029 testů + 2 skutečné reviewer
Java reprodukce. Log `/tmp/t029-review-final.txt`. Root Kafka pozitivo Java/K1,
actual K2 UNKNOWN a finally zachování zůstávají. Nová actual mixed fixture je
explicitní disjoint union dvou doložených ProcessViews: publish→T028 consumer import
plus scheduler→obyčejný callee stejné metody, bez odvozeného pořadí mezi vstupy.
První má doloženou cestu k retry/DLT, druhý ji nemá. Deset negativů pokrývá chybějící/
stale subscription, cizí membership, chybějící body asociaci, jinou revision/kind,
stale/contradicting/foreign trigger proof. Zachování celých vstupů/provenance a
absence implicitního subprocess/network jsou veřejně assertovány.

Nezměněné upstream moduly po posledním úzkém guardu nebyly bezdůvodně znovu spuštěny;
celý dotčený T029 modul byl. Full suite, skutečný nepřítomný Kafka3.2.0 API gate,
runtime/broker/DB/delivery/rollback a GH CI jako test evidence NOT_RUN. Původní CI
run43754909215 na7dee1dd měl jednotlivě ověřené prázdné steps ve všech sedmi jobs;
nejde o PASS ani o reprodukovanou chybu kódu. Nezávislé review nové revize zbývá.

## Krok 7 — review-fix evidence a publikace (T029-S05, AC06)

Baseline `7dee1dd144de68a90ee6c82a0ccc70f2dddb2e2b`. Zachovat všech 49 konceptů,
160 vztahů a 311 epizod reviewed HEAD, reanchor pouze aktuální citované řádky bez
změny významu. Nepřidává se nový spekulativní koncept ani vztah. Generované grafy
výhradně příkazem. Finální výsledky údržby a čistoty jsou uvedeny níže.

```sh
./kgmaker semantic update --base 7dee1dd144de68a90ee6c82a0ccc70f2dddb2e2b --note docs/changes/130_projectProcessFailures.md
./kgmaker scan --no-docs
python3 /tmp/t029-review-semantic.py
./kgmaker semantic apply
./kgmaker semantic validate
python3 /tmp/t029-review-preservation.py
./kgmaker memory capture --base 7dee1dd144de68a90ee6c82a0ccc70f2dddb2e2b --validation targeted=passed --validation semantic-preservation=passed --validation full-suite=skipped
```

Apply/validate/preservation **PASS**: 7 source-backed nodes a 19 vztahů reanchored,
žádná removal. Všech 49 konceptů / 160 vztahů / 311 epizod reviewed HEAD zachováno;
flow.py, process_model.py, process_paths.py, kafka_retry.py, framework.py a původní
business_process prefix byte-identické. Worker symlinky target/target-k2 odstraněny.
Skutečná capture přidala pouze epizodu
`episode:d1d49425d5dcdd1aea5982d3522f0f5510f53b7b3be696707d7a28f78c161fde`;
stav 49 / 160 / 312. Žádná zpětně vymyšlená pre-task evidence.

Před fix commitem primary Git ref stále `7bb8b8d389c461c684197704203a99dcb2b83724`;
open PR109/W09, PR110/T029, PR111/Criteria a historický draft4. Change130 bez kolize,
žádné nové Task ID. Cizí nepublikované soubory se nepřebírají. Pokud main před
publikací postoupí, integrace musí mít samostatný krok a cílené testy.

Finální `./kgmaker scan`, `./kgmaker check`, `./kgmaker semantic validate`,
`python3 /tmp/t029-review-preservation.py`, `git diff --check` — PASS. Workflow
review-fix iteration1 má uložené implementation/test artifacts; první record byl
odmítnut pro chybějící povinné disposition=null, po opravě úspěšně zaznamenán.
Není to náhrada nezávislého review. Po fix commitu následuje samostatná integrace
ověřeně merged W09 z actual main, bez přebírání pracovních souborů.

## Krok 8 — integrace merged W09 (T029-S04/S05, AC01–AC06)

T029 fix parent `88617e22f99b0b4b6f0b30ea4edefd0d83c32295`; nový skutečný main
`cceb1109df6d88e4f46107f9f9ad12f5e563c0d3`, parents `7bb8b8d` + `999e60f`,
tree `0949b95f3e44ad10cf9fa33030a67f6210d7a7b4` ověřen po fetch primárního SSH
remote. Normální `git merge --no-ff --no-commit cceb1109...`, bez rebase/force.
Konflikty jen README, semantic.json a generované GRAPH.md/mmd; zdroj/testy bez
konfliktu. README zachovává obě capability, semantic union oba rodiče. Grafy se
obnovují CLI. T029 source/test z fix commitu a W09 flow.py/source z merged main
zůstávají byte-identické; nové pracovní soubory jiných agentů se nepřebírají.

W09 zpřísnil exact executable caller/callee CFG authority. Proto následuje nová
actual T025–T029 sada a oba Java reviewer repro nad integrovaným stromem. Nejde o
opakování nesouvisející full suite. Dočasně připojené target/target-k2 opět ukazují
na připravené `/tmp/kgmaker-pr97-reconciled/workers/jvm`, bez změn jejich obsahu.

```sh
JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 JAVA_TOOL_OPTIONS=-XX:-UsePerfData PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 KGMAKER_WORKERS_HOME=/tmp/kgmaker-pr97-reconciled/workers PYTHONPATH=src:tests PYTHONDONTWRITEBYTECODE=1 /tmp/kgmaker-test-venv/bin/python -B -m pytest -q --tb=short -p no:cacheprovider --basetemp=/tmp/kgmaker-t029-integrated tests/test_t029_project_process_failures.py tests/test_t025_build_local_process_path.py tests/test_t026_collapse_business_steps.py tests/test_t027_cross_http_process_boundary.py tests/test_t028_cross_async_process_boundary.py '/tmp/t029-review-scheduler.py::test_scheduled_local_listener_call_does_not_enter_kafka_retry[java]' '/tmp/t029-review-callee.py::test_listener_policy_does_not_apply_to_ordinary_local_callee[java]'
```

**301 PASS / 0 SKIP, 65.23 s**, `/tmp/t029-integrated.txt`; actual JDK21/Javac/K1/K2
v deklarovaném scope. Nepřidaly se žádné funkční integrační opravy ani nové source
chování. Exact byte audit ověřil T029 business_process.py/own test proti fix parent
a všech 14 změněných W09 source/test souborů proti main. Nový stricter flow guard
neodstranil doložený root/import Kafka entry ani finally/callee regresní korpus.
Full suite/runtime/actual nepřítomná Kafka3.2.0 gate/GH CI test evidence NOT_RUN.

README obsahuje oba kontrakty. Progress/acceptance nyní označují W09 MERGED na
skutečném SHA, T029 nadále PR_OPEN a uvádějí nový integrační běh odděleně od75PASS.
Inventářový součet je přepočten z existujících atomických řádků bez povyšování
jejich verification. Capability/API signatura a příklady z fix commitu jsou beze
změny; source integration bez dopadu na CLI/registry/templates.

```sh
./kgmaker semantic update --base cceb1109df6d88e4f46107f9f9ad12f5e563c0d3 --note docs/changes/130_projectProcessFailures.md
./kgmaker scan --no-docs
python3 /tmp/t029-integration-semantic.py patch
./kgmaker semantic apply
./kgmaker semantic validate
python3 /tmp/t029-integration-preservation.py
./kgmaker memory capture --base cceb1109df6d88e4f46107f9f9ad12f5e563c0d3 --validation targeted-integration=passed --validation semantic-union=passed --validation full-suite=skipped
```

**PASS**: union obsahuje všech 50 konceptů / 170 vztahů / 317 přesných epizod
obou rodičů. Reanchor 7 konceptů / 19 vztahů ověřil původní hash a stejný citovaný
řádek proti správnému parentu; žádná sémantická removal ani nový spekulativní vztah.
Skutečná integrační capture přidala epizodu
`episode:5bb199a167139967707bd8d2bc96cf5e2e8fd9149f6bab0a73f0a50d8f6fd027`;
finální stav **50 / 170 / 318**. Původních 48/157/310 z baseline7bb i následná
review/merge historie zůstávají zachovány. Oba dočasné worker symlinky odstraněny.

Závěrečné `./kgmaker scan`, `./kgmaker check`, `./kgmaker semantic validate`,
`python3 /tmp/t029-integration-preservation.py` a `git diff --check cceb1109...`
— **PASS**. Workflow iteration2 je ve review se skutečnými integračními artefakty.
Primary refs před publikací potvrzují main `cceb1109...` a předchozí PR110 HEAD
`7dee1dd...`; normal push publikuje fix commit a dvourodičovou integraci společně.
Nezávislé review nové dvojice base/HEAD a GH CI nejsou vydávány za PASS; implementer
PR nemerguje. Runtime/worker scope a ostatní NOT_RUN limity se integrací nemění.

## Krok 9 — přesný T014 tuple a druhý review fix (T029-S02/S04, T028-S01/S03–S05, AC04–AC06)

Baseline `e415b7f65be780a944784d39f6bc3adb433022fb`, base `cceb1109...`.
[REQUEST_CHANGES2](https://github.com/p-rum/kgmaker/pull/110#issuecomment-6901003371)
uzavřelo první invocation P1, ale doložilo druhý: odstranění všech mapping proofs
z ProcessView a nahrazení membership ref existujícím FRAMEWORK_DERIVED endpoint
proofem stále vytvářelo retry/DLT. Nezávislých 301 PASS / 70.10 s je historický
samostatný běh; nový repro má 1 FAIL / 7.45 s. Vlastní reprodukce stejného skriptu
`/tmp/kgmaker-review110-membership.py`: **1 FAIL / 0 SKIP, 7.39 s**.

Rekognoskace dle context/architect přímo ve zdroji ověřila T014 `declaration`,
canonical candidate/edge ID, SOURCE_ONLY/UNKNOWN mapping/capture kontrakt a T028
ztrátu plného candidate tuple. Parent výslovně schválil minimální aditivní passthrough
jako nutnou provenance opravu, ne nový resolver. Membership ref samotný nestačí.
Původní runtime task vyčerpal tři iteration a odmítl další advance; nový bugfix
workflow `task:a4895442104ff5881736b69b4fd262748f7e0e94a21f5c69da804d7c2ce5567a`
navazuje na stejné T029/change130, bez nového Task ID/specification.

`business_process.py` vyjímá stávající T028 membership kontrolu do společného pure
helperu. T028 subscription aditivně zachová `membership_witness` schema1: přesné
T014 source/target/binding/edge dokumenty + rules/capture. Nepřenáší celý remote view
ani druhý proof katalog. Canonical declaration ID se ověřuje z T014 VERSION,
capture a konkrétní edge/binding identity; canonical edge ID váže celý candidate.
Mapping IDs, source/target/service/context/scope, contract/release, podpůrné refs a
subscription/link/consumer occurrence musejí souhlasit. T029 helper používá
výhradně původní raw provenance z ProcessView; chybějící declaration nelze nahradit
endpoint proofem ani obálkou. T012 owner je přesné manifest service ID, T025
přidává literal `service:` prefix; žádný suffix/name-match resolver.

Zachovány všechny původní IDs, raw proofs, context selection a partial order.
T028 rules zůstávají async-process-boundary-1, přenos je aditivní metadata. T029
rules jsou process-failures-3; v1/v2/v3 failure output se nepoužívá jako nový input.
Legacy T028 import bez tuple zůstává čitelný a má UNKNOWN retry boundary; legitimní
root Kafka entry se nemění. Bounded input/output guard platí i pro nový tuple,
cyklus nebo příliš velká kolekce neprovádí mutaci ani I/O.

Dotčeno: business_process.py, vlastní T029 test a úzká T028 fixture/regrese, README,
process-paths capability/API, progress a acceptance. T014/T012 source, resolver,
flow.py, framework, worker a sousední report/feature soubory se nemění. CLI,
registry/spec identity/revision a managed templates bez dopadu. Změna T028 není
vydávána za pouhý refaktor; schopnost uchovat podklad pro downstream replay je
výslovně nová aditivní část této opravy.

První focused replay: 11 PASS / 1 FAIL, 15.44 s — pozitivní import odhalil rozdíl
T014/T025 owner namespace. První společný checkpoint 172 PASS / 2 FAIL, 73.55 s:
stejný owner převod a stará pozitivní T028 fixture měnící candidate až po T014
projekci. Opraven přesný namespace převod. Fixture nyní mění vstup před
refresh_handoff/project_remote, aby nový candidate získal vlastní canonical IDs.
Druhý checkpoint 173 PASS / 1 FAIL, 71.87 s ukázal navíc původní neúplnou UNKNOWN
catalog topology: stávající T014 gate vyžaduje service node + declares_kafka_interface.
Doplněna výhradně producer-shaped protocol fixture; neoslabuje se guard. Její
unknown/stale/raw preservation assertions zůstávají. Původní post-capture zásah
zůstává samostatný negativ. Tyto dvě fixture regrese: **2 PASS / 58 deselected,
0.53 s** (`pytest ... test_t028... -k 'scopeless or post_capture_candidate'`).

Další checkpoint 176 PASS / 1 FAIL, 71.77 s zachytil sdílený nested witness při
negativním cycle testu. Testy nyní před mutací dělají explicitní deepcopy serializace;
API již vstupní ProcessView kopíruje, source model se nemění. Původní negativy se
opakují nad izolovanými inputy, jejich staré PASS nejsou náhradou aktuálního běhu.
Nové testy pokrývají odebrání všech declarations, dvanáct tuple/proof negativů,
převzetí skutečného witness jiného endpointu/capture a cycle/size/no-mutation.

```sh
JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 JAVA_TOOL_OPTIONS=-XX:-UsePerfData PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 KGMAKER_WORKERS_HOME=/tmp/kgmaker-pr97-reconciled/workers PYTHONPATH=src:tests PYTHONDONTWRITEBYTECODE=1 /tmp/kgmaker-test-venv/bin/python -B -m pytest -q --tb=short -p no:cacheprovider --basetemp=/tmp/kgmaker-t029-membership-clean tests/test_t029_project_process_failures.py tests/test_t028_cross_async_process_boundary.py tests/test_t014_bind_remote_interfaces.py /tmp/kgmaker-review110-membership.py '/tmp/t029-review-scheduler.py::test_scheduled_local_listener_call_does_not_enter_kafka_retry[java]' '/tmp/t029-review-callee.py::test_listener_policy_does_not_apply_to_ordinary_local_callee[java]'
```

**177 PASS / 0 SKIP, 71.60 s**, log `/tmp/t029-membership-clean.txt`; skutečný JDK21,
Java/K1 pozitivo, K2 UNKNOWN a všechny tři reviewer reprodukce. První RED používal
stejné prostředí, jen `/tmp/kgmaker-review110-membership.py` a basetemp
`/tmp/kgmaker-t029-membership-red`. Intermediate checkpoint příkazy měly stejné
moduly/env a vlastní basetemp suffix membership-fix/final/verified; plný poslední
běh je jediný current výsledek tohoto fix kroku. Full suite, runtime/broker/DB a
chybějící actual Kafka3.2.0 gate NOT_RUN. GH CI není náhradou nezávislého review.

## Krok 10 — evidence druhé opravy (T029-S05, T028-S05, AC06)

Baseline `e415b7f65be780a944784d39f6bc3adb433022fb`. Source-backed reanchor zachovává
všech 50 konceptů / 170 vztahů / 318 epizod; nový koncept nebo vztah se nevymýšlí.
Původní T027/earlier business prefix zůstává byte-identický, T028 je výslovně
aditivně rozšířen v kroku9. T014/remote_mapping/flow/framework/worker source se nemění.
Generované grafy pouze CLI; výsledky níže. Předběžně fetch potvrdil skutečný main
`83999fb2e08c6d9d67449687c95b2217eee08b09`; integrace bude až po fix commitu.

Závěrečný úzký schema guard odmítá `schema_version=True` místo integer1. Nový
negativ a actual mixed pozitivum: **2 PASS / 88 deselected, 7.47 s**, stejné env
jako krok9, `pytest ... tests/test_t029_project_process_failures.py -k
'schema_bool or imported_entry_and_ordinary'`, basetemp `/tmp/kgmaker-t029-membership-schema`.
Je oddělený od předchozí177sady; integrovaný celý rozsah se ověří v kroku11.

```sh
./kgmaker semantic update --base e415b7f65be780a944784d39f6bc3adb433022fb --note docs/changes/130_projectProcessFailures.md
./kgmaker scan --no-docs
python3 /tmp/t029-membership-semantic.py
./kgmaker semantic apply
./kgmaker semantic validate
python3 /tmp/t029-membership-preservation.py
./kgmaker memory capture --base e415b7f65be780a944784d39f6bc3adb433022fb --validation membership-targeted=passed --validation semantic-preservation=passed --validation full-suite=skipped
```

Apply/validate/preservation **PASS**: 7 konceptů/19 vztahů source-backed reanchor,
žádné removal, všech 50/170/318 z reviewed HEAD zachováno. Skutečná capture po177PASS
přidala historickou epizodu `episode:ec8774d35f983b1c71327427383c74845b2f45e12e5cfe1d1b58b80e03ce00d5`;
stav50/170/319. Následující schema_bool follow-up je ověřený zvlášť výše; epizoda
se zpětně nepřepisuje. Final reanchor/check ověřuje aktuální source po follow-up.

Final `./kgmaker scan`, `./kgmaker check`, `./kgmaker semantic validate`,
`python3 /tmp/t029-membership-preservation.py`, `git diff --check` — **PASS**;
50/170/319, worker symlinky odstraněny, změny jsou dohledatelné v samostatném fix
commitu před ordinary merge main83999fb. Full/GH CI/runtime zůstávají NOT_RUN.

## Krok 11 — integrace merged Criteria main (T029-S04/S05, T028-S04/S05, AC01–AC06)

Fix parent `475b35df5d17e3f5221dec793d327f17bb1c3b77`; actual main
`83999fb2e08c6d9d67449687c95b2217eee08b09`, parents `cceb1109` +
`c57b57f478a675a9d16af71384fd5a304d48f38f`, tree
`098cb3277e62058c032b3526f342cca752715b48` ověřeny proti primary fetch.
Normální merge --no-ff --no-commit, bez rebase/force. Konflikty pouze v obou
inventářích, semantic.json a generovaných grafech; source bez konfliktu. Zachovány
obě dokumentační části a obě semantic historie. S09 report/validation/feature_cli
pracovní soubory se nepřebírají.

Integrační skutečný JDK21 worker je read-only symlink na
`/tmp/kgmaker-criteria-queries/workers/jvm/target` (včetně lib), JAR SHA256
`651468ee0743057ead245e57c2d36cc1b20633655853079a25f33d3bc05cc3fb`.
K2 target symlink zůstává na `/tmp/kgmaker-pr97-reconciled/workers/jvm/target-k2`;
jeho source se v Criteria neměnil. KGMAKER_WORKERS_HOME ukazuje na vlastní složený
workers adresář, žádný cizí target se nepřestavuje. Symlinky se po testu odstraní.

```sh
JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 JAVA_TOOL_OPTIONS=-XX:-UsePerfData PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 KGMAKER_WORKERS_HOME=/tmp/kgmaker-t029/workers PYTHONPATH=src:tests PYTHONDONTWRITEBYTECODE=1 /tmp/kgmaker-test-venv/bin/python -B -m pytest -q --tb=short -p no:cacheprovider --basetemp=/tmp/kgmaker-t029-main111 tests/test_t029_project_process_failures.py tests/test_t028_cross_async_process_boundary.py tests/test_t014_bind_remote_interfaces.py tests/test_t025_build_local_process_path.py tests/test_t026_collapse_business_steps.py tests/test_t027_cross_http_process_boundary.py /tmp/kgmaker-review110-membership.py '/tmp/t029-review-scheduler.py::test_scheduled_local_listener_call_does_not_enter_kafka_retry[java]' '/tmp/t029-review-callee.py::test_listener_policy_does_not_apply_to_ordinary_local_callee[java]'
```

**345 PASS / 0 SKIP, 83.01 s**, log `/tmp/t029-main111.txt`. Všechny tři skutečné
reviewer reprodukce, exact tuple/capture/legacy negativy, actual T012→T014→T025→T028
mixed path, Java/K1 root pozitivum, K2 UNKNOWN a finally/HTTP scope guard regrese.
Žádná integrační funkční oprava nebyla potřeba. Source byte audit **PASS**: vlastní
business_process.py a oba T028/T029 testy proti475b35d; všech5 Criteria source/test/
worker souborů změněných v main proti83999fb. Matching worker JAR hash beze změny.
Full suite/runtime/Kafka3.2.0 actual absent gate/GH CI test evidence NOT_RUN.

Progress/acceptance označují Criteria MERGED a T029 stále PR_OPEN; nový345 běh je
oddělený od historických301/177/2 checkpointů. Capability/API a README z fix parent
zůstávají, CLI/registry/templates bez dopadu. Inventory součty sledují atomické
řádky, neprohlašují novou verification nesouvisejících dodávek.

```sh
./kgmaker semantic update --base 83999fb2e08c6d9d67449687c95b2217eee08b09 --note docs/changes/130_projectProcessFailures.md
./kgmaker scan --no-docs
python3 /tmp/t029-main111-semantic.py patch
./kgmaker semantic apply
./kgmaker semantic validate
python3 /tmp/t029-main111-preservation.py
./kgmaker memory capture --base 83999fb2e08c6d9d67449687c95b2217eee08b09 --validation membership-integration=passed --validation semantic-union=passed --validation full-suite=skipped
```

Apply/validate/preservation **PASS**: všech 51 konceptů / 173 vztahů / 323 přesných
epizod obou rodičů zachováno. Source-backed reanchor ověřuje správný parent hash
+ identický citovaný řádek, žádná removal. Skutečná integrační capture
`episode:c212fdb8cd99b8ac1581478e04d88596a0bc0517671b1748c5b1defdfe6af8d7`
přidává jedinou novou epizodu; finální **51/173/324**. Oba worker symlinky odstraněny.
Primary refs před publikací potvrzují main83999fb a dosavadní PR110 head e415b7f.
Otevřené PR112, PR110 a historický draft4; change130 bez kolize, žádné nové Task ID.
Nezávislé review nové pair zůstává nutné; implementer nemerguje.

Finální `./kgmaker scan`, `./kgmaker check`, `./kgmaker semantic validate`,
`python3 /tmp/t029-main111-preservation.py`, `git diff --check 83999fb...` — **PASS**.
Runtime workflow má skutečné integration implementation/test artifacts ve review.
Normal push předá samostatný fix475b35d a dvourodičový integrační commit; PR110
body aktualizuje aktuální pair, aditivní T028 kontrakt a všechny historické FAIL
odděleně. GH CI nového HEAD a nové nezávislé review nejsou předem označeny PASS.
