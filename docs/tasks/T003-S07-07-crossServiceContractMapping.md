# T003-S07-W07 — Cross-service contract/release mapping

- Work package ID: `T003-S07-W07`
- Milník: `T003-S07`
- Revision: 2
- Datum: 2026-11-05
- Stav: SPECIFICATION; tento soubor popisuje cílové chování, nikoli hotovou implementaci.
- Baseline: pracovní větev nad `8ac80ca30f6f680539deb7fb3590519d3a5c1460`; před zahájením ověř aktuální cílovou větev a otevřené PR.
- Baseline revize2: main `deb3691c23de19064a9e9c0484cf6a62ab295592`; explicitní draft stack T013 `f43c9e08096887ca216df4a4d1ebceee1ca0e98e`, obsahující T012 `8f76e5e` a common context roles `a65c195`. Tyto drafty nejsou potvrzením full/merge readiness. T014 je downstream spotřebitel W07, nikoli jeho závislost.
- Závislosti: T003-S03-W05, T003-S07-W04 a T003-S07-W06; průřezové požadavky `T003-R01–R10`.
- Nadřazená acceptance: `T003-AC07`.

## Cíl

Propojit HTTP/Kafka služby pouze přes explicitní service, contract a release mapping.

## Rozsah a konkrétní kontrakty

- Primární místa změny: `src/kgmaker/workspace.py, src/kgmaker/domain.py, src/kgmaker/dataflow.py`.
- Reuse existující model/store/provider/workspace/evidence vrstvy; nevytvářej paralelní katalog ani odlišnou identitu entity.
- Zachovej SOURCE_ONLY, nulové implicitní spouštění buildů, instalací, migrací a aplikace a atomickou publikaci poslední validní generace.
- Výsledek s neúplnou evidencí musí být PARTIAL/UNKNOWN s konkrétním důvodem; confidence nesmí nahrazovat chybějící důkaz.
- Veřejnou změnu současně promítni do README, capability dokumentace, CLI příkladů a stavové/acceptance matice.

## Implementační kroky

1. Před kódem ověř současný kontrakt ve zdroji, testech a knowledge graphu; zapiš přesnou podporovanou matici a failing acceptance.
2. Rozšiř stávající datový model a versioned protocol pouze o pole nutná pro tento work package; popiš migraci a kompatibilitu v1/v2/v3.
3. Implementuj pozitivní cestu, lokalizovanou diagnostiku a nulovou mutaci při invalidním vstupu, timeoutu nebo zrušení.
4. Přidej produkčně věrnou fixture a negativní/ambiguous variantu: více verzí kontraktu a shodné URL v různých service realms.
5. Aktualizuj acceptance inventář, `docs/production-analysis-progress.md` a nový český `docs/changes/<N>_<shortName>.md` skutečnými výsledky.

## Požadavky na testování

- Test musí ověřit: více verzí kontraktu a shodné URL v různých service realms.
- Spusť nejmenší relevantní testy, potom celý `python3 -m pytest -q`; worker/build task navíc spustí příslušný skutečný toolchain test.
- Ověř `git diff --check`, nulové implicitní procesy v offline cestách a nulovou mutaci store při chybě.
- Chybějící povinný toolchain je FAIL/BLOCKED/SKIP dle matice, nikdy PASS. Do change note napiš přesné příkazy, výsledky a neprovedené kontroly.

## Akceptační kritéria

- **T003-S07-W07-AC01:** Vzdálený přechod není JVM call a vznikne jen při kompatibilním explicitním mappingu.
- **T003-S07-W07-AC02:** Staré podporované vstupy a graph/store schema zůstávají čitelné nebo mají výslovně otestovanou migraci.
- **T003-S07-W07-AC03:** Negativní a nejednoznačný případ nevytvoří silnější evidence ani dostupnost, než dovolují vstupy.
- **T003-S07-W07-AC04:** Stavová matice odkazuje na konkrétní test/fixture/verzi a nepovýší celý milník nad skutečně ověřený scope.

## Větev, PR a Definition of Done

- Implementuj výhradně v samostatné větvi, doporučeně `feat/t003-s07-07-cross-service-contract-mapping`; do stejné větve nepřidávej jiný work package.
- Na konci vytvoř samostatný pull request do aktuálně určené cílové větve. PR musí odkázat na tento soubor, `T003-S07`, nadřazenou acceptance a nový change note; bez explicitního pokynu jej nemerguj.
- Hotovo znamená implementovaný omezený kontrakt, zelené požadované kontroly, aktualizované docs, validní sémantický patch/scan podle projektových instrukcí a zdokumentované zbývající hranice.

## Revize2 — konkrétní plán před runtime implementací

Následující API/formát je SPECIFICATION. Zachovává AC01–04 a reuse skutečných
S03-W05/S07-W04/S07-W06 producerů plus explicitní T012/T013 draft stack. T014,
payload type resolver a runtime discovery se zde neimplementují.

### Explicitní manifest authority

Původní `release_mapping` v1 znamená nadále obsahové mapování build output →
classpath, nikoli API/deployment kompatibilitu. Nové volitelné pole workspace je
`remote_mapping` s přesnými top-level poli `{schema_version:1,releases:[],
compatibilities:[],mappings:[]}`. Všechna pole/container/enum/ID se strict validují,
unknown keys a duplicate IDs jsou controlled error. Seznamy mají konečné limity.

Release record má přesně `{id,service_id,interface_id,context_id,scope,release,
contract:{repo_id,path,sha256,pointer}}`. Reference míří na existující service,
interface variant a selected qualified context. Scope je konkrétní podporovaný
workspace/view scope, nikoli `all`. Contract je explicitně deklarovaný repo/path,
raw lowercase SHA256 a existující operation/schema JSON pointer. HTTP pointer
odpovídá T013 operation_pointer; Kafka má kořen `""` nebo již zachycenou schema
reference. Žádné nové external `$ref` řešení. Release je netajná deklarace, nikoli
runtime/deployment zjištění. Manifest není autentizace libovolných public faktů.

Compatibility record má přesně `{id,source_release_id,target_release_id,
assertion}`. Podporovaná assertion v1 je `DECLARED_OPERATION_COMPATIBILITY`.
Směrová reference váže konkrétní obě service/interface/context/scope/hash/pointer/
release records, bez wildcards, semver ranges nebo obecné payload ekvivalence.

Mapping record má přesně `{id,transport,source_release_id,target_release_id,
compatibility_id}`. Transport je HTTP nebo KAFKA, compatibility_id null nebo exact
record ID. Default null vyžaduje shodu raw contract SHA, pointer a release selectoru.
Rozdílné hashes/pointers/releases jsou možné jen přes konkrétní explicitní paired
compatibility record pro přesně tuto dvojici. Shoda URL/hostname/DTO/short-type,
GAV, názvu souboru či pořadí kandidátů není authority.

HTTP source je existující CONSUMER, target PROVIDED/PROVIDER; Kafka source PRODUCER,
target CONSUMER. Strany patří odlišným explicitním service realms. Více mappings
pro stejnou source je dovolený candidate set, nikoli arbitrary winner.

### Dvě fáze / navržená veřejná API

- `capture_remote_mapping_inputs(workspace, graph)` je výslovná bounded I/O capture
  fáze, reuse T013 `capture_interface_contracts` a confined raw file hashes. Váže
  workspace manifest hash, normalized remote declarations a přesně deklarované
  inputs. Žádný glob/live discovery, nové context/store/cache, worker/build/model.
  Změna během capture nebo escaped/oversized input je controlled error.
- `resolve_remote_mappings(workspace, graph, interfaces, *, captured, scope,
  selected_contexts=None)` je pure funkce. Interfaces jsou existující transportově
  rozlišené ViewDocuments. Reuse upstream canonical projection/proof validation a
  T013 contract attachment, bez druhého resolveru nebo skrytého I/O. Full graph je
  zachován pro integritu; selected inventory určuje eligibility.
- Pure resolver kontroluje manifest/capture binding, skutečný canonical Node/raw
  symbol/site/edge+proof tuple, context/scope/path/SHA/range, source freshness,
  contract authority/pointer/revision a explicitní release pair. Public self-hash
  či version marker bez původních upstream důkazů nesmí přinést pozitivní claim.
  Nepoužít private LATEST nebo nevybraný context k povýšení selected public faktu.
- Výstup je bounded versioned report `{schema_version,rule_version,input_hash,
  bindings,diagnostics,coverage}`. Binding zachovává source interface a celé target
  candidates, původní mapping/release/contract/evidence refs, scope/context a reasons.
  Reuse resolution statuses RESOLVED (jediný oprávněný deklarovaný kandidát),
  AMBIGUOUS (více), UNRESOLVED (žádný). Žádná nová `calls`/JVM dispatch hrana ani
  automatické pokračování process CFG. T014 je samostatná následná view projekce.

RESOLVED znamená pouze statický declared remote mapping. HTTP request/response a
Kafka async publish/subscribe zůstávají oddělené významy. HTTP request definition,
execution intent a runtime jsou nezávislé: unsubscribed request může mít mapping
operace, ale nikoli vykonaný remote transition. Payload request/response/message
reference/kompatibilita zůstávají UNKNOWN bez skutečného versioned typed produceru.
Kafka vyžaduje explicit broker realm a exact topic, contract/release + origin proof;
groups jsou oddělené candidates. Regex/dynamic/config-only nepovyšuje code/delivery
proof. Runtime/delivery/deployment/availability zůstává UNKNOWN/NOT_OBSERVED.

### Chyby, budget, kompatibilita

Malformed schema/container/reference je controlled error před publikací. Validní,
ale absent/stale/unsupported důkaz znamená localized UNRESOLVED/UNKNOWN; nezneplatnit
nezávislý validní source. Multiple targets ani partial coverage nesmí dokazovat
endpoint absence. Bounds na depth/cycles/shared occurrences/fanout před deepcopy;
truncation uchová candidate neúplnost a omitted IDs/counts, nesmí tvrdit unikátnost.
Žádný raw payload/property/credential/URL secret do output/errors. Pure vstup/store
se nemění. Absence remote_mapping ve starém workspace/Graph1/2/3 je čitelná bez
auto-binding. Rule/capture identity patří do existující případné cache, ne nového
store. Žádná fyzická freshness kontrola se nesmí předstírat čistým self-hashem.

### Předimplementační RED a acceptance matice

Nejprve public pure RED: chybějící capture/resolver API nad konkrétní hand-labelled
service/operation/release fixture, nikoli porovnání se stejným helperem. Potom jeden
FIFO actual RED/capture reuse W04/W06 fixtures pro Java/K1 HTTP client/provider a
Kafka producer/consumer. Pokud typed kontrakty postačí, žádný native producer/build.

| AC | Povinný skutečný nebo public negative důkaz |
|---|---|
| AC01 | HTTP i Kafka explicitní service+contract+release positive, původní refs; žádná JVM calls hrana; HTTP request/response a execution intent proti async publish/subscribe |
| AC02 | Legacy Graph1/2/3 a absent field; artifact release_mapping beze změny; version/container validation, roundtrip/qualification/cache identity |
| AC03 | Stejná URL ve dvou services; více contract verzí; wrong release/hash/pointer; paired compatibility positive a wrong-pair negative; dva candidates bez winneru |
| AC03 | Foreign Node/symbol/site/edge/proof/context/scope/path/SHA/range; unselected/private newer fact; config-only/regex/dynamic/unsupported; HTTP unsubscribed; Kafka rozdílné realms/groups |
| AC03 | Capture symlink/oversize/race/ref; secrets; no IO/process/network/model; deep/shared/cyclic/bounded fanout a omitted IDs; input/store unchanged na chybě |
| AC04 | Přesná backend/rule/API/fixture matice v docs; honest RED/focus/full, semantic/memory/scan; T014 a payload/runtime nepředstírat hotové |

Final full až po nezávislé source closure a green actual focus nad frozen vstupy,
FIFO lock a připraveným toolchain. GH CI doplňující dle AGENTS/T045 user revize,
ne náhrada chybějícího jiného povinného důkazu.
