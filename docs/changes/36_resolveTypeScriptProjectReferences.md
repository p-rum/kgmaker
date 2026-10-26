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
- Finální integrovaná celá sada s vlastním upraveným workerem:
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

## Hranice a zbývající práce

W02 (paths/exclude), W03 (callback/generics), UI events a BE–FE value flow jsou
samostatná zadání. Cross-repo source reference, runtime execution a persistent
incremental compilation cache nejsou touto změnou dodány. Celá solution analysis
zůstává jedním uloženým compiler kontextem; fingerprints umožní dohledat dotčené
projekty, zatímco současný provider konzervativně invaliduje celý tento kontext.
