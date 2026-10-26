# TypeScript project references s obsahově svázaným project graph

Datum: 2026-10-26. Zadání: [T003-S08-W01](../tasks/T003-S08-01-typescriptProjectReferences.md),
AC01–AC04 a nadřazené T003-AC08. Výchozí main `07ad86592d0b57d071fbc120de462f3400b51213`;
závislost T003-S03-W05 je sloučena jako PR #17. Integrovaný main je
`aa9e64bbec0bfea4bf143824dcc3d8ddf5cd6533` (včetně PR #8).
Celý T003-S08 zůstává PARTIAL.

## Problém a skutečné změny

Původní jediný `createProgram` nad solution-style configem s `files: []` vrátil
nula source calls a COMPLETE, přestože odkazované projekty obsahovaly volání.
Failing acceptance reprodukovala 0 místo dvou přesných targetů.

Worker v2 načítá kanonický reference DAG uvnitř zvoleného rootu (nejvýše 128
projektů), vytváří per-project Program/TypeChecker a používá skutečné compiler
source redirects bez výstupních `.d.ts`, `emit`, solution builderu či instalace.
Repo/config-qualified project identity odděluje stejnojmenné deklarace.
Captured `project_graph` v1 obsahuje configy, root files, options, reference a
obsahové fingerprints, které se propagují po reference hranách. Existující
provider ověřuje zachycené input hashes a při transitive změně konzervativně
zneplatní uložený compiler kontext bez spuštění procesu.

Missing, cyklický, outside-root reference či dvojí vlastnictví source souboru
selže s konkrétní config cestou před publikací store. Preflight a analysis
musí mít stejný project graph; opakovaná četba změněného vstupu je odmítnuta.
Nevzniká paralelní store ani pozitivní runtime/data availability důkaz.
Stávající compiler-workers CI job nyní výslovně spouští také novou referenční
sadu po přípravě skutečného TS toolchainu; source-only CI její chybění dál
poctivě vykazuje jako SKIP.

## Kompatibilita a použití

`kgmaker inspect frontend --root /repo --tsconfig tsconfig.json` funguje i pro
solution config s odkazy na composite projekty. Jednoprojektové vstupy
zachovávají původní symbol-ID layout. Graph/store v1/v2/v3 a worker protocol v1
zůstávají čitelné; project provenance je aditivní. Změna worker distribuce
standardně zneplatní starou compiler vrstvu přes její SHA-256.

## Ověření

- Skutečný TS 5.7.3 / Node 24.19.0 fixture: dva projekty se stejnojmenným
  exportem, consumer a solution root; targety odpovídají konkrétním source
  projektům a nevznikají build/emit artefakty.
- `test_source_redirect_does_not_resolve_against_stale_emitted_declaration`
  odmítá přebrat stale declaration signature místo aktuálního source targetu.
- `test_incremental_project_fingerprints_propagate_only_through_reference_edges`
  ověřuje změnu leaf → consumer → solution při nezměněném sibling fingerprintu.
- Missing/cycle/outside a overlap negativní případy ověřují konkrétní chybu,
  nulovou mutaci posledního store a žádné podvržené resolved facts.
- Offline source/config změna v transitive projektu vyřadí compiler facts
  bez child procesů a bez zápisu store. Legacy loader v1/v2/v3 je ověřen.
- První focused matice před rozšířením fingerprint testu: 9 PASS / 85.75 s.
- První strict celá sada nad pracovními vstupy: 272 PASS / 7 SKIP / 227.00 s;
  skutečné JVM/TS workers a Maven fixture artefakty, bez dostupného Maven
  executable, Gradle a druhého JDK.
- Nový skutečný fingerprint test a integrovaná methodology sada: 12 PASS / 12.65 s.
- Integrovaná celá sada před nezávislým review s vlastním upraveným workerem:
  `KGMAKER_REQUIRE_WORKERS=1 KGMAKER_WORKERS_HOME=/workspace/ts-project-refs/workers JAVA_HOME=/workspace/tools/jdk-21.0.6+7 PATH=/workspace/tools/jdk-21.0.6+7/bin:/workspace/kgmaker-venv/bin:$PATH PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q`:
  **284 PASS / 7 SKIP / 199.57 s**. Obsahuje všech deset W01 scénářů,
  skutečné compiler workers, React/overload regresi a instalační sdist/wheel
  testy. Explicitní worker home zaručuje vlastní worker v2, nikoli resource
  package z jiného editable checkoutu. Linux, Python 3.12.14, pytest 8.3.4,
  Temurin 21.0.6+7, Kotlin 2.1.10, TypeScript 5.7.3 a Node 24.19.0.
- SKIP: dva skutečné Maven scénáře (Maven executable není na PATH), druhý JDK
  a čtyři Gradle scénáře. Nejde o tvrzení jejich úspěchu nebo nově spuštěného
  Maven/Gradle buildu. Připravené genuine fixture/worker artefakty byly výslovně
  převzaty z již sestavené kontrolované distribuce v pracovním prostředí.
- `node --check workers/typescript/worker.cjs`, `git diff --check`, scoped
  semantic apply/validate, memory capture a command-generated scan/check:
  **PASS**. Stávající ověřené semantic vztahy i historie z main jsou zachovány;
  nepřidává se žádný smyšlený semantic vztah.

### Opravy po nezávislém review

Review reprodukovalo dva P1 případy mimo původní matici. Při rozdílném
`strictNullChecks` vznikaly dvě identity téže deklarace podle consumer checkeru;
call target pak neměl owner CFG, ačkoli výstup tvrdil COMPLETE. Deklarace se nyní
kanonizuje na AST a TypeChecker vlastnícího projektu podle přesné source polohy.
Consumer call-site signature zůstává oddělená; target identity, argument parameter
identity a owner CFG ukazují na stejnou vlastněnou deklaraci.

`disableSourceOfProjectReferenceRedirect: true` dovoloval převzít stale emitted
`.d.ts` jako current resolved target. Takový referencující config nyní v tomto
source inspection režimu selže s lokalizovanou diagnostikou před zápisem store.
Neobchází se explicitní compiler option a neimplementuje se nový build workflow.

Obě skutečné acceptance před opravou FAIL, po první opravě 2 PASS / 7.84 s.
Větev je znovu integrována s main `35033096e8a2ea5d74ae8d2195a7b27d22c7590a`;
XLSX dokumentace, zdroj i všechny sémantické epizody main jsou zachovány.

Finální strict běh po opravách s výše uvedeným explicitním vlastním worker home,
Temurin 21.0.6+7 a TS 5.7.3: **302 PASS / 7 SKIP / 182.40 s**. Obsahuje všech
12 W01 scénářů, skutečné původní compiler/React/worker-install testy a nové XLSX
regrese z main. SKIP zůstávají stejné nedostupné Maven/Gradle/second-JDK scénáře.
Poslední cílené dvě review reprodukce po doplnění owner parameter a consumer
signature assertion: **2 PASS / 29.39 s**. Finální scoped semantic update/apply/
validate, memory capture, scan/check a diff check prošly; žádná historie main
nebyla přepsána starým branch snapshotem.

### Integrace distribuovaných exporterů z main

Po sloučení PR #22 je větev integrována s main
`e656b8ef4c174d3d60600037d7c0d78fc514e39d`. TS worker, `inspection.py`, worker
protocol i opravené TS acceptance testy jsou byte-identické s nezávisle
schváleným `74baab337d1cbb3e1afcdaff8bb40d3b40a0f230`; `build_runner.py`
odpovídá přesně novému main. Obě prepended stavové/acceptance sekce i celá
sémantická historie exporterů jsou zachovány.

`KGMAKER_REQUIRE_WORKERS=1 KGMAKER_WORKERS_HOME=/workspace/ts-project-refs/workers PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q tests/test_typescript_project_references.py::test_consumer_options_do_not_fork_owner_declaration_or_lose_its_cfg tests/test_typescript_project_references.py::test_disabled_source_redirect_rejects_stale_declaration_without_store_mutation tests/test_exporter_distribution.py -k 'not installed_exporters'`:
**10 PASS / 2 DESELECTED / 12.14 s** — dva skutečné TS repros a osm exporter
negative/legacy kontraktů. Dvě installed real-build varianty jsou zde výslovně
vynechány; nejsou nově tvrzeny jako PASS. Celá 302-testová strict sada výše
zůstává důkazem předchozího main `3503309`, neopakovala se pouze kvůli nezávislé
exporter integraci bez změny TS runtime.

README sémantická provenance je znovu ověřena proti skutečným command bullets:
`semantic prepare` na řádku 99 pro concept evidence, `semantic update --base REF`
na řádku 101 pro README relationship evidence. Nejde pouze o kontrolu rozsahu
řádků; cílové texty odpovídají evidenci. Scoped update/apply/validate,
memory capture, command-generated scan/check, syntax a diff check: PASS.

## Hranice a zbývající práce

W02 (paths/exclude), W03 (callback/generics), UI events a BE–FE value flow jsou
samostatná zadání. Cross-repo source reference, runtime execution a persistent
incremental compilation cache nejsou touto změnou dodány. Celá solution analysis
zůstává jedním uloženým compiler kontextem; fingerprints umožní dohledat dotčené
projekty, zatímco současný provider konzervativně invaliduje celý tento kontext.

### Integrace context selection a service ownership z main

Větev je znovu integrována s main
`3a393e451b0d7b8f83de93f05f07d2307ba66ec3` po sloučení T006 a T007.
Schválený TS worker/inspection/protocol i opravené TS testy zůstávají
byte-identické s `74baab3`. `views.py`, `workspace.py` a nové context/ownership
testy odpovídají přesně main; žádná další namespace politika se nepřidává.

`KGMAKER_REQUIRE_WORKERS=1 KGMAKER_WORKERS_HOME=/workspace/ts-project-refs/workers PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q tests/test_t006_select_service_contexts.py tests/test_t007_define_service_ownership.py tests/test_workspace.py tests/test_cross_repo_artifacts.py tests/test_typescript_project_references.py::test_consumer_options_do_not_fork_owner_declaration_or_lose_its_cfg tests/test_typescript_project_references.py::test_disabled_source_redirect_rejects_stale_declaration_without_store_mutation`:
**52 PASS / 16.20 s**. Jde o relevantní integration gate včetně dvou skutečných
TS reprodukcí; celá strict sada se pouze kvůli nezávislým views změnám neopakuje.

README concept evidence je ověřena proti skutečnému `semantic prepare` bullet
na řádku 130; `uses` evidence proti `semantic update --base REF` na řádku 132.
Architecture source-authority evidence odpovídá skutečné větě na řádku 22;
service-ownership concept/implementation evidence odpovídá odstavci a funkci
na řádcích 140/143. Zachovány jsou všechny související main vztahy i historie;
scoped semantic apply/validate, memory capture, command-generated scan/check,
byte identity, syntax a diff check: PASS.

### Úplný input closure a kompatibilita selektorů po integraci K2

Větev je integrována s main `eff0d3d5d7620b017fe42a65a54f672af8068667`
(K2 Analysis API, PR #26). CI zachovává skutečné K2 i TS acceptance. Genuine
K1/K2 worker distribuce jsou převzaty z již sestaveného kontrolovaného worktree
a jejich JVM zdroje, builder i pinned dependency locks byly před převzetím
porovnány byte-for-byte s integrovaným main.

Další skutečná reprodukce odhalila P1: paths alias dependency soubor chyběl při
preflight, vznikl těsně před analyze a vstoupil do nově resolved call. Root source
scan tento soubor mimo vybraný root neviděl a původní kontrola rehashovala pouze
staré vstupy, takže nahradila store jako COMPLETE. Nová kontrola vyžaduje shodnou
úplnou mapu path/SHA-256, validuje její tvar a při změně členství vrátí STALE před
konstrukcí či publikací grafu. Projektový/config graph se nadále porovnává;
žádná pravidla pro outside-root project references se neoslabují.

`test_new_alias_dependency_after_preflight_cannot_replace_last_graph` používá
skutečné oba worker requesty a řízenou změnu mezi nimi; kontroluje byte-identický
poslední graph i source/config. Před opravou FAIL, po opravě **1 PASS / 2.05 s**;
celá dosavadní skutečná TS matice **13 PASS / 55.42 s**. Strict celá sada po této
opravě a integraci K2: **391 PASS / 9 SKIP / 330.87 s**.

Integrace K2 také přidala frontend selectoru dvě irrelevantní Kotlin None pole.
Reinspection původního TS snapshotu z kontraktu `7b9a9ea` pak zachovala dva čerstvé
kontexty stejného projektu. Konstrukce nyní sdílí `_selection_key` s providerem;
Kotlin backend/version vstupují pouze do JVM selectorů. Přesně známý dočasný TS
digest se normalizuje na původní slot; opaque varianty a K1/K2 selector keys se
zachovají. Nejde o obecnou JVM migraci nebo W02 selektivní cache.

Skutečné legacy worker fixture pokrývají původní uložený klíč, absenci klíče a
dočasný K2-era digest; při reinspection zbude jeden čerstvý context a jedna sada
call sites. Původní klíč před opravou FAIL (dva contexts). Fokus legacy/provider/
K2: **41 PASS / 2 DESELECTED / 304.11 s**. Přesné syntetické K1/K2 klíče byly
před/po opravě porovnány a zůstaly shodné.

### Integrace konfigurovatelného Confluence připojení

Integrace s main `7b9a9eaecaf41c9c5bc5a6d1233cd82e2cf4f1e9`
zachovává schválené TS runtime a testy byte-identické s `e39661d`.
Relevantní sada context/ownership/workspace/cross-repo a všechny skutečné TS
project-reference testy: **62 PASS / 57.59 s**. Plná sada se kvůli této integraci
neopakovala. README semantic prepare/update evidence odpovídá řádkům 134/136;
zachovány jsou 4 koncepty, všech 8 původních vztahů a sjednocená neměnná historie.
Scoped semantic apply/validate, generovaný scan/check a diff check: PASS.

### Finální strict validace po obou P1 opravách

```sh
KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 KGMAKER_WORKERS_HOME=/workspace/ts-project-refs/workers JAVA_HOME=/workspace/tools/jdk-21.0.6+7 PATH=/workspace/tools/jdk-21.0.6+7/bin:/workspace/kgmaker-venv/bin:$PATH PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q -rs
```

Výsledek: **394 PASS / 9 SKIP / 734.61 s**; zahrnuje všech 16 TS
project-reference případů a skutečné K1/K2 compiler testy. Devět SKIP se týká
Maven/trusted exporteru, druhého JDK s Maven, dvou installed exporterů
(Maven/Gradle), Gradle included build, dvou Gradle variants a dvou Kotlin
Maven/Gradle build-options fixture. Žádný skutečný TS/K2 test není SKIP.
Scoped semantic apply/validate, scan/check, `node --check` a diff check: PASS.
README evidence byla ověřena proti skutečným semantic prepare/update odrážkám
na řádcích 134/136; architecture authority i ownership evidence odpovídají textu.
Zachovány jsou 4 koncepty, 8 vztahů a všechny předchozí epizody obou větví.
