# Model business procesu a revizí (T023)

## Problém a rozsah

Společný T005 `ViewDocument(kind="process")` a T009 evidence kontrakt již existují,
ale chyběl samostatný process identity/revision model a bezpečná hranice mezi
technickým průběhem a business popisem. `flow.process` rozvíjí source CFG; není
business katalog ani authority pro agentem navržený význam.

Baseline je `49c46b0bd165cf11e7b3eb0af04bf64fb93e23ce` (aktuální main po T015).
T005 `c79c551`/`000d35a` a T009 `18b7070`/`cbf17b1`/merge `09d351d` jsou skuteční
ancestors. Nezávislá rekognoskace z předchozího main3a7 ověřila source a61 shared
model/evidence/CFG testů. Root potvrdil rezervaci čísla70 po kontrole main,
otevřených PR a rezervace69. Implementace je izolovaná ve větvi
`feat/t023-define-business-process-model`.

## Skutečné změny

- Čistý `process_model.py`: version1 `ProcessDefinition` a `ProcessView`, exact
  revision/definition fingerprint binding, scope/context, trigger/entry/exit/
  outcome reference checks. Steps/transitions reuse T005 nodes/edges; branch,
  exception, retry/loop a async se nepřevádějí na lineární pořadí.
- Evidence/polarity/freshness reuse T009. Každý technický krok má origin IDs;
  missing proof musí být explicitní UNRESOLVED/UNKNOWN boundary nebo invalidní.
  Cizí kontext/scope se odmítá i v nepoužité provenance. Candidate evidence se
  nemění na RESOLVED; incomplete/stale/contradictory proof neumožní COMPLETE.
- Oddělené semantic annotations s allowlistem label/description/citací/grouping
  proposal a sdílenými review stavy. APPROVED label nepřepíše technické bytes,
  evidence ani fingerprint. Technical injection a vymyšlené target/citation IDs
  jsou odmítnuty. Model nedělá review rozhodnutí ani jejich autentizaci.
- Structural JSONschema odkazuje na existující viewv1; Python navíc validuje
  cross-reference a content binding. Explicitní syntetická payment fixture
  ukazuje alternativy, retry, exception a async, nikoli běžící aplikaci.
- README, capability dokumentace, acceptance inventář a progress matrix uvádějí
  skutečný Python API rozsah. Žádné nové process CLI/render/apply příkazy.

## Acceptance a ověřování

| Acceptance | Konkrétní test / důkaz |
|---|---|
| T023-AC01 | `test_ac01_diamond_loop_exception_and_async_roundtrip_preserve_exact_ids`, `test_input_order_is_not_execution_order_or_identity`, veřejná JSON fixture |
| T023-AC02 | `test_ac02_approved_czech_label_never_changes_technical_truth` — porovnání technical JSON/status/fingerprint |
| T023-AC03 | `test_ac03_annotation_technical_injection_is_rejected` — evidence/edges/conditions/availability/nested attributes |
| T023-AC04 | invalidní references/revision/scope/evidence porovnávají celý input a last-valid artefakt; pure API test zakazuje file/process/network I/O |
| T023-AC05 | missing proof boundary, stale/candidate/unknown polarity, foreign scope/context i unused proof, explicitní truncation diagnostics |
| T023-AC06 | source, veřejný schema/fixture, tento note a capability/progress/acceptance dokumenty; finální příkazy a výsledky níže |

RED před modelem: `ModuleNotFoundError` při collection nového AC souboru.
První implementační focus36PASS/1FAIL chyběl nový schema soubor; tento skutečný
mezistav nebyl vydáván za PASS. Po schématu a zesílení hranic focus123PASS0.49s
(62 nových +61 shared/CFG); následně přidán test veřejné dokumentované fixture.
Finální focused a frozen full výsledky budou zaznamenány po skutečném dokončení.

## Kompatibilita, příprava a omezení

Graph v1/v2/v3 i shared viewv1 zůstávají beze změny, stejně tak `flow.py`, worker
protocol a framework. Neexistuje nový authoritative graph store nebo zápis API;
migrace jejich dat není potřeba. Model validuje explicitní JSON, ne aktuálnost
fyzického checkoutu. Fingerprint je content identity, nikoli podpis nebo nová
RUNTIME_OBSERVED evidence.

Own worker a build-fixture tracked sources byly před kopírováním trusted lokálních
artefaktů porovnány přes git tree s T015 `0701543`; jsou shodné. TypeScript package
locks jsou shodné. Explicitní session preflight i pinned10 JPA API/JAR/POM/license
hashes PASS, žádný worker build/install nebo implicitní fetch. New task nemění
compiler/framework/render source; samostatný nový toolchain/render fixture pro
nový model není zapotřebí. Required existing worker fixtures ověří frozen full.

T024+ discovery/projection, grouping simplification, agent packets, apply/review,
revision history store, katalog, CLI, Mermaid/report/export nejsou implementovány.
Async znamená typ vazby, nikoli delivery, total order nebo observed execution.
Celý T004 ani upstream milníky se tím neoznačují za hotové. Publikaci a nezávislé
review/CI provádí root, autor pouze připravuje lokální commit.

## Nezávislá kontrola malformed input před full

Root read-only review našlo dva P2 shape případy: `relation=[]` a provenance
`evidence_kind=[]` mohly po shared validation pokračovat do membership a vyhodit
raw TypeError. Oprava ihned ukončí validaci při shared strukturální chybě;
regrese pro list/dict obou polí porovnává input i last-valid bytes. Navíc
identity targetů nesmí kolidovat mezi process/step/transition, aby annotation
nikdy nemířila na dvě různé entity. Žádný full se před opravou nefrontoval.

Finální focused před frozen full: **130 PASS** (69 T023 +61 shared/CFG), exit0;
XML/log jsou v `/workspace/validation/t023/final-focused.*`. Přesný čas je
v XML. JSONschema i dokumentovaná fixture jsou zahrnuty. Frozen source manifest
a required full budou v `/workspace/validation/t023/`; queued/running stav není
PASS. Required full používá vlastní worker home/PYTHONPATH, JDK21+Kotlin prefix
a děděný PATH s managed Node; Maven/Gradle nejsou přidávány na PATH.
