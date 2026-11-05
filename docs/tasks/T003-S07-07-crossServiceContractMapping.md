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

- `capture_remote_mapping_inputs(workspace, graph, *, scope="production",
  selected_contexts=None, source_coverage=None)` je explicitní bounded I/O fáze.
  ZDE běží existující HTTP provider/consumer a Kafka canonical projekce, jejich
  saved-source/private-index replay a T013 capture/contract attachment. Tyto funkce
  mohou číst filesystem a čistý resolver je NEVOLÁ. Žádný worker/build/model ani
  nová graph context/store/cache; source_coverage nesmí nahradit canonical proof.
- `resolve_remote_mappings(workspace, graph, interfaces, *, captured, scope,
  selected_contexts=None)` je pure funkce nad explicitně dodanými transportově
  rozlišenými ViewDocuments. Porovnává je s canonical captured projekcemi a ověřuje
  pouze in-memory tuple/content consistency. Nesmí volat upstream projectors,
  contract attachment/capture, saved-source validators ani filesystem. Full graph
  je pro integritu; selected inventory pro eligibility. Freshness je evidence
  capture-time, nikoli nové ověření fyzického checkoutu v pure resolveru.
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

Capture v1 má přesně `{schema_version,rule_version,workspace_id,
workspace_manifest_sha256,workspace_fingerprint,graph_fingerprint,selection,
remote_declarations,contract_capture,canonical_interfaces,diagnostics,capture_id}`.
Selection má `{scope,selected_contexts,source_coverage_fingerprint}` s přesně
normalizovaným explicitním výběrem. Workspace fingerprint váže deklarativní
workspace bez privátních/absolutních repo roots, graph fingerprint celý dodaný graf
bez nezávislých generation timestamps. Canonical_interfaces jsou serialized
upstream ViewDocuments v pořadí HTTP provider, HTTP consumer, Kafka s contract
attachments. Contract_capture je ref-only summary původní T013 capture: source_capture_id,
file repo/path/raw/source hashes/status/indexed, bounded pointer inventory a
declarations; raw JSON examples/descriptions se po attachment neexportují. Není to
další store ani druhý contract parser.
Capture_id je digest celého envelope bez sebe sama. Výstup neobsahuje private index,
raw secret properties ani source bodies; graph/workspace fingerprints pouze vážou
externě dodané inputs. Cesty/timestamps nejsou autentizace. Očekávaný canonical
ViewDocument musí přesně odpovídat dodanému interfaces včetně provenance/selection.
Reordered semantically unordered collections se canonicalizují existujícím modelem;
ordered occurrences/candidate varianty se nezahazují.

Tato capture je explicitní handoff mezi důvěryhodnou lokální capture fází a pure
consumerem, NENÍ kryptografické potvrzení původu libovolného neověřeného JSON. Při
neexistenci takové capture authority není positive remote claim dovolený; self-hash
nesmí být vydáván za autentizaci. Tamper testy mění graph/workspace/selection/
interfaces samostatně při původní capture a musí selhat. Koherentní útočník schopný
přepsat všechny vstupy včetně capture není touto lokální datovou smlouvou ověřen.

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


Implementační upřesnění prvního source checkpointu: běžný HTTP client bez T013
generated-client vazby získává pouze explicitní manifest contract EXPECTATION.
Známý HTTP method/path musí odpovídat vybrané operation pointer; target nadále
vyžaduje skutečný current T013 binding. K1/K2 Kotlin HTTP typed-body je upstream
UNKNOWN, nikoli pozitivní W07 execution proof. Původní T013/common source se nemění.

### Actual-matrix freshness clarification — rule v2

Actual5b Kafka catalog nodes mají resolution RESOLVED a canonical VERIFIED_STATIC
code/current selected context/BOUND contract, ale jejich agregovaná interface
freshness zůstává UNKNOWN. Freshness summary není totéž co statický declared
mapping resolution. Rule `remote-contract-mapping-2` smí přijmout UNKNOWN summary
POUZE pro Kafka, pokud existující trusted capture canonical replay a všechny
původní context/code/contract/broker/topic/group guards uspějí. Explicitní STALE
je vždy odmítnuto, stejně jako unproven source či contract. HTTP nadále vyžaduje
CURRENT summary; žádný zdejší nový actual důkaz jeho změnu nepovoluje.

Output uchová source_interface_freshness a target_interface_freshness přesně,
UNKNOWN se nezmění na CURRENT ani runtime proof. Manifest/capture schema v1 je
aditivní; rule_version v2 vyžaduje novou explicitní capture, starý v1 self-hash
se neopravuje ani nepovýší. T014/T016 downstream musí tuto nejistotu zachovat.

Stejný Kafka-only exception se vztahuje také na canonical
`declares_kafka_interface` aggregate edge: musí mířit ze skutečného katalogového
`service:<release.service_id>` na přesný interface variant, mít UNKNOWN freshness,
bez AMBIGUOUS/STALE/contradicting stavu a projít všemi ostatními code/context/
contract/realm/topic/group guardy. Původní UNRESOLVED edge summary se nepovýší ani
nepřepíše. Chybějící či jiná declaration edge tuto výjimku nezíská.

Jedna release reference označuje jeden konkrétní interface variant a smí být
použita pouze s jediným transportem. Reuse stejného release ID zároveň pro HTTP
 a KAFKA je logicky neplatná deklarace: REMOTE_TRANSPORT_CONFLICT před capture či
materializací, bez smíchání protokolových rows/candidates.
