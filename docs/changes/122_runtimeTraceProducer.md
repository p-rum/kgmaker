# T003-S13-W01 — synchronní opt-in runtime capture a oprava review

Datum: 2026-11-15. Zadání: [T003-S13-W01](../tasks/T003-S13-01-runtimeTraceProducer.md),
parent `T003-S13 / T003-AC13`. Výchozí SHA implementace:
`14d7f7cefab2fa5c9cf8c6d939d3b92e838faea8`; výchozí SHA těchto oprav po
REQUEST_CHANGES: `45dae061ee8e61fca8e2c48dfae3ddb6f6258dae`.
Dodání `IN_PROGRESS` do lokálního předání koordinátorovi; ověření celého milníku
`PARTIAL`. Dále uvedené PASS platí pro konkrétní bounded testy, ne pro celý T003.

## Krok T003-S13-W01-S01 — rekognoskace / AC01, AC04

Výchozí SHA opravy: `45dae061ee8e61fca8e2c48dfae3ddb6f6258dae`.
Původní wrapper pouze přijímal JSON, pozdě validoval context a označoval jakékoli
facts jako COMPLETE. Provedena přímá rekognoskace dle `kgmaker-architect`:
AGENTS, copilot instructions, registr/celé zadání, historické GRAPH.md/NOTES.md,
`runtime_evidence.py`, `inspection_cli.py`, `worker_protocol.py`,
`graph_provider.validate_context_snapshot`, `inspection.context` a stávající v1 test.

Kontroly (prefix `PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m kgmaker`):

- PASS — `workflow list`, `task add ... --workflow bugfix` a context/analysis/plan
  pro lokální task `task:62e703b7bce541fbb18ef6ee6ab3b7747dbe8258f3d8d0890254d7c447a7faa9`.
- NOT_RUN (chybějící index při zahájení) — `status`,
  `query 'runtime observations build context'`, `memory recall 'runtime producer'`
  odpověděly „No readable graph“. Executable je se správným PYTHONPATH funkční.
- NOT_RUN — `memory capture --base 45dae061ee8e61fca8e2c48dfae3ddb6f6258dae --validation focused-tests=unknown`
  nezapsal episode: chyběl skutečný pre-task graph. Nevytváří se zpětně falešný baseline.

Kompatibilita: rekognoskace nemění aplikaci ani graph schema. Dotčené dokumentační
plochy shrnuje S05. Omezení: historický GRAPH.md byl pouze navigační vodítko;
aktuální zdroje byly ověřeny přímo. Další architektonická práce mimo W01 neprovedena.

## Krok T003-S13-W01-S02 — uzavřený v2 kontrakt / AC02, AC03

Výchozí SHA opravy: `45dae061ee8e61fca8e2c48dfae3ddb6f6258dae`.
Nálezy 1, 2 a 6: `{kind:call}` bylo dostatečné pro COMPLETE, volné diagnostics,
text a URL mohly obsahovat secrets; v2 postrádal povinné service/version a přesnou
source identity. `src/kgmaker/runtime_evidence.py` nyní kontroluje přesná pole
jednotlivých facts, typ výsledku, existující symboly i jejich compiler context.
Neznámé pole nebo diagnostický text odmítne bez echo citlivé hodnoty. Status
PARTIAL/UNKNOWN zachovává; neodvozuje jej z počtu facts. UNKNOWN nemůže vytvořit
observation evidence. V2 vyžaduje celý envelope a neprázdné identifikátory,
`source_identity` porovná s digestem celého uloženého kontextu a source manifestu.
To funguje i pro skutečný compiler context, který pole `content_hash` nemá.

`tests/test_runtime_trace_producer.py` pokrývá chybějící/empty identity, forged
source fingerprints, cizí symboly, nevalidní typy, unsupported v3, volné credentials,
status i nulovou mutaci store a posledního artefaktu. PASS — testy v běhu V1 níže.
Příklad: incomplete call bez caller/target skončí AnalysisError, validní PARTIAL
call zůstane PARTIAL i po importu.

Kompatibilita: původní sanitizované v1 observation manifesty zůstávají čitelné
(stávající `BuildAwareContractsTest.test_runtime_import_is_bound_to_context_and_rejects_stale_source`).
V2 má explicitně přísnější kontrakt; dřívější nevalidované exporty této větve
je nutné vytvořit znovu. Graph/store schema beze změny. W01 facts se neimportují
jako RTA/value-flow a neudělují availability. Obecná bezpečnost libovolného textu
se neslibuje. Neprovedeno: migrace nevalidních v2, runtime manifest v3 a W02–04.

## Krok T003-S13-W01-S03 — preflight a životní cyklus procesu / AC01, AC03

Výchozí SHA opravy: `45dae061ee8e61fca8e2c48dfae3ddb6f6258dae`.
Nálezy 4 a 5: stale source dříve spustil proces a timeout nechával potomky běžet.
`runtime_evidence.py` nyní před Popen kontroluje argv, konečný timeout `(0,900]`,
identity, snapshot zdrojů/configu/workeru/classpath, cancellation a výstupní cestu.
Sdílí `graph_provider.validate_context_snapshot` a bounded `_exchange/_terminate`
z `worker_protocol.py`; samotné sdílené moduly se nemění. Proces dostává vlastní
POSIX skupinu, která se uklidí při timeout/cancel/KeyboardInterrupt i po konci
leaderu. Stderr a argv se nepřepisují do výsledku.

Po capture znovu kontroluje neměnnost uloženého grafu, snapshot i cestu před
atomickou publikací. `inspection_cli.py` přidává `--cancel-file`; argv za `--`
je pokryto CLI testem. Output smí být jen oddělený `.json` v `.kgmaker/runtime/`,
bez symlinků a překryvu s inputs. Původní umístění do rootu vytvářelo config input
a zneplatňovalo skutečný compiler snapshot; tento případ opravuje oddělený output.

PASS — preflight/postflight, path/NaN/Infinity, invalid JSON/exit/oversized output,
timeout/cancel/leader-exit/KeyboardInterrupt a CLI testy v běhu V1. Negativní
preflight má Popen nahrazený selháním: žádná aplikace se nespustí. Test potomka
ověřuje, že po návratu nevytvoří odložený marker a není běžícím procesem.
Příklad: změna App.java od inspection vyvolá STALE před startem aplikace.

Kompatibilita: explicitní producer je POSIX-only, v1 import zůstává offline.
Uložení mimo `.kgmaker/runtime` je nyní odmítnuto. Omezení: běžní potomci ve stejné
skupině; odpojené daemony, Windows a rollback vlastních side effects aplikace
nejsou podporovány. Neprovedeno: Windows runner / obecná izolace aplikace.

## Krok T003-S13-W01-S04 — skutečný JDK21 producer / AC01, AC03

Výchozí SHA opravy: `45dae061ee8e61fca8e2c48dfae3ddb6f6258dae`.
Nález 3: původní test pouze vytiskl ručně napsaný JSON. Nový zdrojový SDK
`tooling/runtime/java/org/kgmaker/runtime/RuntimeTrace.java` s opt-in env provádí
synchronní callback, factory, boolean predikát a skutečnou registraci map routeru.
`tests/fixtures/runtime-trace/TraceApplication.java` vytvoří service, dispatchne
handler a ověří návratovou hodnotu i počet volání. Bez opt-in nic neexportuje.
SDK drží pouze uzavřená data; neukládá argumenty, return values, exception text ani
credentials. URL authority/query/fragment odstraní ještě před SHA-256 cesty.

PASS — V1 skutečně spouští `javac --release 21`, JVM compiler worker a výslednou
aplikaci přes `java`. Symbol IDs pocházejí z workeru, build/bytecode/source
snapshoty jsou obsahově svázány. `test_actual_jdk21_application_observes_all_four_kinds_and_no_values`
ověří všechny čtyři kinds, sanitizer hranici v argumentu i URL a hash `/orders`.
`test_actual_jdk21_capture_is_opt_in_and_records_only_executed_branch` ověří bez
opt-in prázdný stdout a disabled větev bez call/mapping.
`test_real_compiler_source_change_fails_before_application_start` má zákaz Popen.

Kompatibilita: SDK je volitelný source v checkoutu, ne agent ani dependency
Python wheelu. Jde o explicitní synchronní instrumentaci, ne Spring registr,
bytecode auto-instrumentaci či plné pokrytí aplikace. `CREATED` znamená nenulový
výsledek factory, ne důkaz nové alokace. Výsledek SDK je vždy
PARTIAL/INSTRUMENTED_SCOPE_ONLY. Neprovedeno: Spring application toolchain,
Kotlin, Windows, async/reflection, RTA/value-flow a produkční deployment/data proof.

## Krok T003-S13-W01-S05 — dokumentace a evidence / AC04

Výchozí SHA opravy: `45dae061ee8e61fca8e2c48dfae3ddb6f6258dae`.
Nález 7: předchozí change note slučoval vše do S01 a přeceňoval Python JSON fixture.
Tento záznam odděluje všech pět kroků. Aktualizovány:

- [README](../../README.md), [architecture](../architecture.md) a nový
  [runtime kontrakt/API/CLI/limity](../runtime-trace.md), včetně použitelných příkladů.
- [Acceptance inventář](../acceptance-inventory.md) a
  [stavová matice](../production-analysis-progress.md): oddělené dodání/ověření,
  JDK21/POSIX subset a ostatní runtime rozsah PARTIAL/NOT_RUN.
- `.kgmaker/semantic.json`: packet-scoped obnova 8 existujících concepts a
  20 vztahů po posunu citovaných řádků. Původní citace ověřeny proti přesným
  souborům baseline `14d7f7ce`, jejichž hashe odpovídaly uloženému semantic layer;
  zachovány stejné výroky, identity i confidence. Žádný nový runtime semantic fakt.

Bez dopadu: registr/zadání — stejná identita, revize a dependencies, implementuje
se jeho omezený kontrakt; host instructions/Python templates — žádná změna
instalovaných instrukcí; ostatní capability docs — W02–04 a další projekce se
nemění. Graph dokumenty se neupravují ručně; lokální machine index obnovuje
`scan --no-docs`. Tracked GRAPH.md/GRAPH.mmd zůstávají historickým snapshotem.

PASS — CLI help, níže V1, semantic apply/validate a diff check. Neprovedeno:
full suite dle aktuálního výslovného pokynu uživatele, GH CI a independent review
opraveného HEAD (provádí reviewer po předání). Dokumentace nic z toho neoznačuje PASS.

## Přesné kontroly

**V1 — PASS, 88 testů** (finální cílený běh; samotný runtime soubor obsahuje
kontraktové i skutečné JDK testy):

```sh
PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH \
JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 \
KGMAKER_WORKERS_HOME=/tmp/kgmaker-pr97-reconciled/workers \
KGMAKER_REQUIRE_WORKERS=1 PYTHONPATH=src \
/tmp/kgmaker-test-venv/bin/python -m pytest -q \
  tests/test_runtime_trace_producer.py tests/test_build_aware.py \
  tests/test_graph_provider.py::test_scan_hook_and_feature_retain_compiler_layer_without_processes \
  tests/test_worker_protocol.py
```

Toolchain PASS: `/usr/lib/jvm/java-21-openjdk-amd64/bin/java -version`:
OpenJDK `21.0.13.0.3`; fixture kompiluje stejným JDK s `--release 21`.
Chybějící actual worker je při `KGMAKER_REQUIRE_WORKERS=1` FAIL; bez flagu SKIP,
nikoli PASS. `PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m kgmaker runtime produce --help`
PASS, odpovídá publikovaným parametrům.

`git diff --check` a `git diff --check 14d7f7cefab2fa5c9cf8c6d939d3b92e838faea8`
PASS; odstraněn nadbytečný prázdný EOF původního testu. Po commitu koordinátor
ověří tentýž base proti přesnému HEAD.

Semantic postup (prefix `PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m kgmaker`):
`scan --no-docs`; `semantic update --base 45dae061ee8e61fca8e2c48dfae3ddb6f6258dae`;
aktuální scoped patch; `semantic apply`; `semantic validate`; `scan --no-docs`.
Výchozí stale citace nejsou vydávané za PASS před opravou.

Historie: původní commit `45dae061` uváděl `PYTHONPATH=src python3 -m pytest -q
 tests/test_runtime_trace_producer.py tests/test_build_aware.py` — 7 PASS. To
neprokazovalo skutečný producer ani současné acceptance. Hlášený
ModuleNotFoundError bez PYTHONPATH byl chybou spuštění, nikoli chybějící kgmaker.
Během opravy byly FAIL skutečné integrační pokusy (`-k actual` a V1 bez správného
JDK PATH): ukázaly nutnost vybrat plné JDK, nullable worker source paths/nested
class names, správný context digest a vyloučení exportu z source snapshotu.
Předchozí finální kandidát měl 83 PASS / 1 FAIL kvůli způsobu volání CLI main
v testu; opraven přes sys.argv. Následně 84 PASS, poté doplněny 4 negativní
observation-kind varianty a proveden výše uvedený finální V1.

Zbývá: nezávislé review aktuálního commit, publikace PR koordinátorem a samostatné
W02–04. Nic z bounded runtime evidence nedokládá dostupnost dat nebo nasazení.
