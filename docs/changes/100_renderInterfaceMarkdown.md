# T020 — bounded Markdown katalog rozhraní (source candidate)

Problém: T019 poskytoval přesný JSON katalog bez Markdown formátu.
Záměr T020-S01–05/AC01–06: čistý deterministický renderer nad stejným snapshotem,
zachování IDs/status/evidence/contextu, kontraktů a generated/unclassified řádků,
bezpečné cells/internal evidence anchors a konkrétní GFM AST testy.

Explicitní draft base T019 abad2e30; upstream ready/merge zůstává samostatný gate.
Revize2 a plán byly Root APPROVED před implementací. Poznámka100 rezervována po
main/worktree/open-PR kontrole; jiné tasky ani frozen W03/staging se nemění.

Dev parser nebyl dostupný v shared interpreteru. Explicitně připraven pouze do
/workspace/t020-dev/site-packages, nikoli shared venv/cache: markdown-it-py3.0.0,
mdurl0.1.2, published wheel SHA256 ověřeny přes enforced session proxy/TLS.
Lock je tests/requirements-markdown.txt; renderer nemá runtime dependency/install.

Public pre-implementation RED:4FAIL1.08s (missing renderer/unsupported format);
původní JSON cesta na stejném bundle prošla před markdown assertion. Implementace
přidává architecture_render.py a interfaces-only formát bez změny JSON defaultu.
Čistá funkce má bounded shape/privacy guard před normalizací, deterministic known
fields a samostatné generated/unclassified/contract/evidence/diagnostics sekce.
Hash anchors rozlišují také item/proof namespace, aniž mění origin ID; validní
node/proof shodné ID nevytváří duplicitní HTML target. CI unittest explicitně
instaluje hash-locked dev parser a vyžaduje jeho dostupnost.

Po RED:4GREEN, expanded43PASS0.94s a renderer+T01977PASS4.37s. Rozšířená closure
176PASS6.59s zahrnuje model/T010/T013 regressions a public CLI JSON/Markdown,
fixed errors, AST hostile labels/decoded IDs, empty scope, realm/group/pattern,
contract revisions/polarity, malformed/secret/cycle/shared/output budgets a
actual explicit OpenAPI/generated-declaration capture. Nejde o compiler/native
nebo generator run. Jednotlivé source-specific logy/XML jsou mimo repo v t020-validation.
Finální source checkpoint a semantic/memory workflow následují; jejich pending
stav se nesmí zaměnit za final/full nebo připravenost závislostí. Native/heavy/full ani živé CI se neprohlašují za PASS; nebyly spuštěny.
Žádný implicitní scan/build/model/network/store/app ani celé T004 dokončení.


| AC | Konkrétní kontrola |
|---|---|
| AC01 | test_public_golden_keeps_original_ids_statuses_contexts_and_evidence_links; test_actual_explicit_contract_and_generated_file_capture_renders_without_recapture |
| AC02 | test_public_hostile_label_keeps_table_and_block_structure; test_escaped_ids_remain_exact_decoded_text_and_have_generated_anchor |
| AC03 | test_public_empty_scope_retains_unknown_coverage_and_diagnostics |
| AC04 | test_pure_renderer_never_uses_provider_io_store_network_or_process; test_markdown_is_interfaces_only_and_invalid_path_preserves_last_artifact |
| AC05 | test_contradictory_evidence_contract_revisions_and_runtime_are_separate; test_kafka_same_topic_distinct_realms_groups_and_regex_are_never_merged; malformed/privacy/budget parametrizations |
| AC06 | Rev2/spec, lock, capability/CLI/README/progress a tato note; final exact review a upstream/current-parent/full closure samostatně |


Finální renderer-only kontrola po úzkém generated-origin ref guardu:47PASS1.25s;
176-case výsledek výše patří předchozímu source checkpointu, nikoli předstíranému
novému whole runu. Public module obsahuje nyní47 případů. Native/heavy/full zůstává
NOT_RUN podle schváleného source-only rozsahu tohoto checkpointu.

T019 base měl zděděnou stale semantic evidenci. První omezený apply byl atomicky
odmítnut (duplicate canonical relationship); validate/memory/check správně blokovaly.
Po Root autorizaci vznikl nový packet vůči3bef611 zahrnující zděděné změny, source
rekognoskace18affected concepts/74relationships a3přesné endpoint relocations.
Dvě přesné (source,target,kind) duplicity po alias bindingu deduplikovány; oba
původní recordy zůstávají v externím audit JSON. Žádná unsupported relationship
nebyla zahozena ani žádná nová freshness vymyšlena. Přidán pouze1T020concept se3
source-backed implements/uses/validates vazbami. Semantic apply/validate PASS;
immutable230episode prefix je zachován. Memory capture a final scan/check se
provádí před clean metadata handoffem; nejsou to full/ready ani upstream approval.

Poslední output closure escapuje také protocol/domain/email punctuation jako entity,
aby cizí plain text nebyl GFM autolink source. Dekódované ID/text se nemění.
Původní raw-substring pořadová assertion byla opravena na skutečný decoded AST,
jak požaduje Rev2. Aktuální renderer48PASS1.22s; starší176/47 výsledky jsou výše
přiřazené svým source checkpointům. Žádný další native/heavy/full nebyl spuštěn.


Root source review P2 doplnil chybějící Content fingerprint v snapshot headeru.
Hodnota je z validovaného ViewDocument.content_fingerprint, nikoli renderer hash
nebo nový snapshot. Samostatný test počítá SHA256 z dodaného canonical JSON,
ověřuje dataclass i mapping, generation metadata exclusion a změnu při změně
deklarace. Řádky/evidence ani runtime/format/capture význam se nemění.
P2 current-source parser/API/CLI matice49PASS1.24s; diff check PASS. Starší48/176
výsledky zůstávají historické, nikoli přejmenované na nový whole/full run.


Root nezávisle SOURCE_APPROVED exact446ddbe/abad2e3 po úplném renderer/CLI/test
review, včetně P2 fingerprint correction. Finální potomek mění pouze metadata,
runtime/tests se kontrolují byte-exact vůči446. Source approval nenahrazuje
upstream/current-main/full/merge readiness a nezasahuje aktivní staging full.


## T020 current-main publication transfer (2026-11-06)

Current parentfbb includes merged PR79–85; older checkpoint/review-pending entries
above are historical. T020 adds only interface Markdown: topology/explain stay
JSON-only, original286-line renderer and original49test source are preserved.
The source-corrected006 aggregate is2737PASS/10typedoptionalSKIP across2747IDs,
not a fresh single full. The T020 stage2647-ID subset is2637PASS/10typedSKIP.
Its49feature cases use48 assertion-equivalent aggregate cases and the original
unsupported topology-Markdown negative PASS on source446ddbe/metadataaa539.
The aggregate's same-ID topology-Markdown positive is T022 evidence, never the
T020 negative. Parser rejection route/entrypoint/helpers and original test body
are source-verified against that original execution; no new test was run here.
Current-main cold fix and all other APIs/CI jobs stay intact. Original249parent
capsules +three exactT020capsules=252; historical validation fields are unchanged.
Fresh scoped semantic CLI, source/global/ID proof and two-stage attribution are
recorded in /workspace/t020-publication-proof. Current T020 exact-pair independent
review/publication are pending; no T021/T022 code/capsules or wholeW09 claim.


### Current blocker — first-call renderer purity

Root's fresh ordinary CPython public-module invocation confirmed file-open I/O
inside `architecture_render._render`'s lazy `_safe_output` import (original
renderer SHAed93abfb9e4052ceef9a2aaf0b7ff2ecbed6be96db48a0948343aff97a00c8b7).
The original49 test result and2647 per-ID ledger remain source-attributed case
results, not closure of this newly uncovered first-call contract. Root RED receipt:
`/workspace/t020-cold-purity-proof/receipt.json`. The initial payload-preparation
missing parser path is separate from the corrected confirmed importlib-open RED.
This checkpoint is HOLD/REQUEST_CHANGES pending separately reviewed corrective
source/regression/affected-result transfer. No corrective code or new execution
was performed here; no final readiness or pure first-call support is claimed.


## Aktuální oddělený T020 checkpoint — 2026-11-06

Base je ověřený cold main `fbb0957`; pouze interface Markdown, nikoli Mermaid
ani topology Markdown. Původní 49 test bodies z aa539 zůstává beze změn; přidána
jedna přijatá first-call cold regrese. Schválená korekce109 extrahuje pouze původní
helpery do architecture_render_common a přesouvá existující importy do module scope
v rendereru/CLI/inspection; algoritmy, limity, veřejná exception a JSON zůstávají.
Historický HOLD výše je uzavřen korekcí, nikoli zpětným přepsáním starých důkazů.

Přijatý pokračovací běh007v2 na `41b9a454`: 152 PASS / 0 SKIP a 19 actual SVG.
Celková SOURCE_CORRECTED evidence je 2740 PASS + 10 typed optional SKIP / 2750;
nejde o nový jediný full běh. Oddělený T020 ledger má přesně 2648 IDs =
2638 PASS + 10 typed optional SKIP: 2598 parent + 50 T020. Původní unsupported
[topology] negative čerpá výhradně skutečný původní446/aa 49PASS receipt;
pozdější combined same-ID positive jej nedokládá. Ostatní47 původních případů
a specialized [explain]/path-error odpovídají přijatým cestám; nový cold případ
má exact41b9 AST. Source/global/per-ID proof je externě v
`/workspace/t020-corrected-publication-proof`. Native630 artefakty ani tools se
nemění; žádný nový test, collection, parser/SVG, preflight, build či full nebyl
pro tento isolated head spuštěn. Nezávislé finální review a publication PENDING.
T021 následně přidá Mermaid; T022 topology Markdown až ve vlastním odděleném PR.


## Aktuální stage ověření — 2026-11-06

Testovaný runtime/source checkpoint `fc6f58f997281e9dee871ae9ab61a90ddaea4578`:
jediná current-stage collect-only kontrola přesně 2648 unique IDs, bez module
skip/missing/extra; následný autorizovaný narrow běh **85 PASS / 0 SKIP, 14.05s**
(50 T020, 34 T019, jedna T014 first-call cold public regrese). Původní unsupported
topology-Markdown negative i explain/path-error nyní skutečně prošly na current
stage; původní446/aa receipt i pozdější combined positive historie zůstávají.
Před/po všech306 source/build/test inputs a čistý HEAD přesné; read-only parser
162member kind/hash/membership přesný proti accepted007v2. Cacheoff/PND1, mandatory
Markdown parser, maxfail1, vlastní tmp; žádný nový native/browser/SVG/build/full.

Aktuální per-ID SOURCE_CORRECTED union **2638 PASS + 10 typed optional SKIP /2648**
obsahuje85 skutečných current-stage řádků a2563 dříve přijatých source-qualified
řádků. Není to fresh2648 full. Raw XML, commands, collect a před/po guards i přesné
source-attribution řádky jsou v `/workspace/t020-corrected-stage-validation`;
receipt SHA256 `4256910e7b59ac67c396fa20751ed88235b4b2d7c779c1503bb95e41a1f72696`.
Finální metadata head je následník téhož testovaného runtime; nezávislé FINAL
review Root+resume10 před publikací čeká. GH CI neověřené/doplňující; žádný push,
PR ani merge nebyl proveden. Závislosti T013/T019 a cold main PR85 jsou sloučené;
T021/T022 nejsou součástí tohoto stage. AC01–05 dokládá původních49+novýcold
current-stage případ, CLI JSON/Markdown/fixed-error kontrakty dalších34T019;
AC06 čeká na finální review a samostatnou publikaci.
