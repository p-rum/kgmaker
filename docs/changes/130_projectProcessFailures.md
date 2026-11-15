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
