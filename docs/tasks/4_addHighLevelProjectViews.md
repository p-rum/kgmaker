# T004 — High-level zobrazení projektu

- Task ID: T004
- Revision: 1
- Datum: 2026-10-20
- Stav: SPECIFICATION; celý dokument a T005–T044 jsou plán, nikoli implementované capabilities.
- Baseline: main `c39f8adf2e3004d201960a18575bc7659808ae94`.
- Parent plan: T004; implementace je výhradně v samostatných T005–T044, ne v jednom obřím PR.
- Depends on: existující provider/model/store/workspace T003-S02; další konkrétní upstream kontrakty jsou uvedeny u tasků.
- Supersedes: žádné zadání; T001–T003 a jejich acceptance zůstávají platné.
- Zadavatelský cíl: integrační rozhraní, schematické propojení služeb a průběh identifikovaných business procesů.

## 1. Výsledek a rozsah

Uživatel získá tři provázané pohledy: katalog poskytovaných/používaných rozhraní, topologii služeb a zdrojů, a katalog/průběh business procesů. V každém může přejít ze souhrnu na původní symbol, call-site, kontrakt a důkaz. Diagram je odvozená projekce existujícího grafu. Nesmí změnit technickou pravdivost kvůli čitelnosti.

První podporovaný rozsah: Kotlin/Java a dostupný Spring/Ktor HTTP subset, HTTP klienti a Kafka přes doložené T003 adaptéry, PostgreSQL/JPA/Flyway jako datové závislosti, explicitní lokální multi-repo workspace. Typy z TypeScript/OpenAPI se přebírají jako existující contract evidence; nový TS compiler ani všeobecný frontend business discovery nejsou součástí tohoto plánu.

Výstupy: verzované JSON modely, Markdown reporty a Mermaid flowcharts, explicitní CLI pro čtení, přípravu anotací, validaci, aplikaci/review a export. Business popisy mohou vznikat v host agentovi bez API key/MCP; technické hrany vznikají deterministicky.

Non-goals: samostatná webová aplikace, live infrastructure discovery, připojení na DB/broker, automatické spouštění aplikace nebo buildů, úplné BPMN 2.0, runtime trace producer, důkaz dostupnosti dat, zaručené doručení zpráv, dokonalá obnova libovolného procesu z kódu. Existující validní runtime evidence se může zobrazit; její producer je nadále T003-S13.

## 2. Ověřená baseline a architektonická rekognoskace

Analýza zdrojů v baseline, nikoli nový test run:
- `src/kgmaker/views.py`: scope/context projekce a integrations edge filter; dosud nejde o agregaci deployable services.
- `src/kgmaker/flow.py`: `control_flow`, `process`, Mermaid/Markdown; proces je bounded statické rozvinutí CFG, nikoli business katalog.
- `src/kgmaker/control_flow.py`: strukturovaný CFG a konzervativní boundaries; zachovat větvení/finally.
- `src/kgmaker/inspection_cli.py`: integrations/data-flow render je zatím pouze JSON.
- `src/kgmaker/domain.py`, `framework.py`: zdrojové a framework integration/persistence podklady.
- `src/kgmaker/workspace.py`: repo-qualified identity, service/contract mapping a konzistentní snapshot.
- `src/kgmaker/model.py`: schema v1/v2/v3 a oddělení evidence/LLM annotation.
- `tests/test_control_flow.py`: mimo jiné výlučné větve, finally, nested calls, async boundary, escaping.
- `tests/test_workspace.py`: identity, ambiguity, missing checkout, stale contract a nulové source mutace.
- `.kgmaker/GRAPH.md` je navigační SOURCE_ONLY snapshot; jeho freshness není důkaz aktuálnosti compiler vrstvy. NOTES neobsahuje další business model.

V této dokumentační změně se compiler, pytest ani semantic scan nespouštěl. Před implementací ověř aktuální zdroje, nikoli historické PASS v progress dokumentu. Source reconciliation je provedená přímo, bez delegace; žádný nový runtime fakt se tím nezískává.

## 3. Architektura a kontrakty

Tok dat: validovaný provider/workspace snapshot → service ownership → interface catalogue → remote bindings/topology → process projection → společné renderery. Všechny úrovně mají drill-down do původního grafu.

### 3.1 Společná identita a view model

`ViewDocument.schema_version = 1`, `kind = interfaces|topology|process`. Povinná pole:
- `view_id`, `baseline_fingerprint`, `rules_version`, `scope`, `context_selection`;
- `nodes[]`, `edges[]`, `diagnostics[]`, `coverage`, `limits`;
- původní identity a hash-bound evidence refs; generation timestamp je metadata mimo canonical content hash.

Node: `id, kind, label, original_ids, owner_id, evidence_refs`; owner může být null s diagnostikou. Edge: `id, source, target, relation, original_ids, evidence_refs, resolution_status`. Service identity vychází z explicitního manifest ID; zobrazovaný název není identita. Interface logical ID obsahuje service realm, protokol a operation/channel klíč. Verze kontraktu je revision fingerprint/variant, ne náhrada identity. Kafka broker realm a namespace jsou součástí channel klíče. Anonymní/unknown target ID je vázán na caller a výraz, aby se neslučovaly nesouvisející unknowns.

Nezakládat paralelní autoritativní graph store. Nové process review/export artefakty jsou odvozené a mohou mít vlastní verzované dokumenty. Pro starý graph formát použít existující loader s původními omezeními.

### 3.2 Služby a kontexty

Service je explicitně popsaná aplikační/deployment hranice, nikoli každý repo/modul/@Service. Workspace rozšiřovat aditivně a kompatibilně; přesnou serializaci doplní T007 s migračními testy.

Výběr kontextů je mapa pro služby/repo/moduly. Dvě služby mohou mít různé compiler context IDs. Podporovaná kombinace vyžaduje explicitní kompatibilní release/environment mapping, když se tvrdí cross-service vazba. Neznámý deployment nesmí být prezentován jako živý systém. Unknown ownership zůstává viditelný a nesmí automaticky přejít do production.

### 3.3 Rozhraní a topologie

InterfaceView obsahuje direction, protocol, owner, method/route nebo broker/topic/group, contract refs, handler/call-site refs a unresolved reasons. U HTTP odlišit definici requestu od execution boundary. U Kafka odlišit topic deklaraci, publish a consume. Schema equality, podobný název ani shodná URL samotné nepovolují cross-service vazbu.

Topologie agreguje po service/resource/channel. Agregace zachová původní interface IDs a dílčí kvalitu důkazů. DB dependencies mají vlastní resource typ, read/write pouze z podporovaných faktů. Flyway není doklad deployed schématu ani naplněných dat. Type-reference centralita DTO/enumů do topology importance nevstupuje.

### 3.4 Business proces

ProcessDefinition: stable process_id, revision, triggers, selected contexts, semantic review a definice rozsahu. ProcessView: steps, transitions, outcomes, entry/exit boundaries, origin refs, technical coverage. Step není nutně metoda; seskupení smí proběhnout jen bez ztráty control-flow.

Pořadí vychází z CFG, nikoli pořadí souborů, abecedy, centrality nebo call graphu. Zachovat branch guards, exception/finally, loops, service boundaries, known transaction boundaries, truncation a unknown dispatch. Nejistá proveditelnost podmínky zůstává nejistá. Zjednodušování nesmí vytvořit cestu mezi výlučnými větvemi.

HTTP remote expansion vyžaduje binding a target context. Async transition znamená potenciální návaznost; žádný globální total order, delivery nebo exactly-once. Korelace jedné instance vyžaduje konkrétní důkaz. Manuální business krok z dokumentace lze uchovat jako sémantický návrh mimo potvrzený technický průběh, nikoli vložit jako technickou hranu.

### 3.5 Stav a evidence

Nezavádět jediné confidence skóre:
- `evidence_kind`: zachovat existující druhy (syntax, symbol, framework, runtime atd.).
- `resolution_status`: RESOLVED / AMBIGUOUS / UNRESOLVED.
- `freshness`: CURRENT / STALE / UNKNOWN.
- `coverage.status`: COMPLETE_WITHIN_SELECTED_SCOPE / PARTIAL / UNKNOWN; úplnost platí jen vůči explicitnímu rozsahu, nikdy vůči celé organizaci.
- `semantic_review_status`: PROPOSED / APPROVED / REJECTED / NEEDS_REVALIDATION.

Approval popisu není approval technické pravdy. Statická cesta, build PASS ani diagram nejsou pozitivním důkazem datové dostupnosti. Smíšené evidence zůstanou rozlišitelné; unresolved kus nelze schovat do silnější agregované hrany.

### 3.6 Semantic workflow

prepare → bounded packet + template → host agent candidate → validate → apply immutable proposal revision → explicit review. Packet hash váže snapshot, pravidla, evidence a target IDs. Povolené návrhy: label, description, citovaný business význam a grouping proposal. Zakázané: nové technické hrany, conditions, execution facts, availability, falešné evidence.

Schválení zaznamená explicitní rozhodnutí, payload/base hash a lokální actor label, ale nepředstírá autentizovaný podpis. Stale candidate se odmítá; změna podkladů vyžaduje revalidation a zachování historie. Chybějící business rozhodnutí není možné „dopočítat“ modelem.

## 4. Cílový kontrakt CLI (SPECIFICATION)

Společné čtení: `--root` nebo `--workspace`, `--scope production`, `--context-selection FILE`, `--strict`. Výběr workspace musí využít existující provider, ne přepnout potichu na jeden repo. `--context` lze přijmout jako kompatibilní zkratku jen pro jednoznačný single-root případ.

```text
kgmaker architecture interfaces --workspace workspace.json --context-selection contexts.json --format json
kgmaker architecture topology --workspace workspace.json --focus order-service --max-hops 2 --max-nodes 100 --format mermaid
kgmaker architecture explain --snapshot view.json --element ELEMENT_ID --format json
kgmaker process list --workspace workspace.json --format json
kgmaker process render --entry ENTRY_ID --workspace workspace.json --context-selection contexts.json --format json
kgmaker process render --process PROCESS_ID --process-view process.json --workspace workspace.json --context-selection contexts.json --format json
kgmaker process prepare --process PROCESS_ID --root . --token-budget 4000 --output packet-dir
kgmaker process validate --packet packet.json --candidate candidate.json --root .
kgmaker process apply --packet packet.json --candidate candidate.json --expected-revision REV --root .
kgmaker process review --process PROCESS_ID --revision REV --decision approve --payload-hash HASH --root .
kgmaker architecture export --snapshot view.json --output reports/architecture
kgmaker process export --snapshot process.json --output reports/process
kgmaker architecture diff --before old.json --after new.json --format json
```

Render formáty: JSON všude; interfaces Markdown (diagram není povinný); topology/process JSON, Markdown, Mermaid. Přepínače se přidají až s odpovídajícím renderer taskem. Export patří T038, diff T039, nikoli základnímu CLI tasku. `--entry` a `--process` jsou vzájemně výlučné. `--root` slouží pro store/coordinator podle stávajícího workspace kontraktu.

První [čtecí výřez T034](../process-paths.md#read-only-process-render-t034) podporuje
uvedené dvě varianty `process render` s JSON a explicitním workspace. Obecné
dohledání jen podle ID a render Markdown/Mermaid zůstávají cílovým chováním.
Čisté [T035 Python API](../process-paths.md#mermaid-for-a-supplied-processview-t035)
vykreslí diagram z dodaného typovaného pohledu.

Exit codes: 0 validní výsledek (i přiznaný PARTIAL bez strict), 2 invalid input/unsupported schema, 3 stale baseline/revision konflikt, 4 neúplné pokrytí při strict. stdout pouze požadovaný dokument; žádný progress text v JSON. Read/list/render/explain/diff/validate jsou read-only. Prepare/apply/review/export zapisují pouze explicitní artefakty, nikdy aplikaci/graf. Cache je opt-in a její poškození je cache miss, ne evidence.

## 5. Vazby na T003 bez duplikace

| Upstream | Vlastní odpovědnost | T004 používá |
|---|---|---|
| T003-S02 | lifecycle/provider/freshness | všechny snapshoty |
| T003-S07-W04 | Kafka identity a bindings | T012, T028 |
| T003-S07-W05 | retry/DLT semantika | T029 |
| T003-S07-W06 | HTTP execution facts | T011 |
| T003-S07-W07 | cross-service contract/release mapping | T014, T027 |
| T003-S07-W08 | evidence ranking | T009 |
| T003-S07-W09 | společný low-level flow/render kontrakt | T021 adaptér, bez druhého renderer modelu |
| T003-S04/S05/S06 | CFG/Spring/persistence fakta v podporovaném scope | T015, T024–T029 |
| T003-S10 | obecná incremental infrastruktura | T037 může použít dostupnou implementaci; bezpečný full refresh je povolen |
| T003-S13 | volitelný runtime producer/import | není podmínkou statického MVP |

Závislost na milníku nevyžaduje automaticky celý jeho budoucí scope, ale vyžaduje doložený kontrakt potřebný konkrétním taskem. Při chybějícím kontraktu nepřesouvej upstream implementaci do T004 PR. Existující work packages nejsou hotové jen proto, že mají agent profil.

## 6. Požadavky a nadřazená acceptance

| Requirement | Požadavek | Implementace | Acceptance |
|---|---|---|---|
| T004-R01 | Stabilní model, identity a kompatibilita | T005–T009 | T004-AC01: validované round-trip fixtures, oddělené kontexty a neproměněná evidence |
| T004-R02 | Katalog HTTP/Kafka a kontraktů | T010–T014, T020 | T004-AC02: přesný očekávaný katalog včetně unknowns; žádné falešné propojení podle názvu |
| T004-R03 | Servisní topologie a DB dependencies | T015–T018, T021–T022 | T004-AC03: drill-down každé hrany a správná izolace realms, scope a protokolů |
| T004-R04 | Lokální business průběh | T023–T026 | T004-AC04: CFG alternativy, výjimky a omezení přežijí agregaci |
| T004-R05 | Cross-service a async průběh | T027–T029 | T004-AC05: pouze ověřené bindingy, žádný vymyšlený delivery/total order/rollback |
| T004-R06 | Host-agent význam a lidská revize | T030–T033, T040 | T004-AC06: forged/stale návrhy odmítnuty, explicitní review a historie zachovány |
| T004-R07 | CLI a konzistentní exporty | T019–T022, T034–T036, T038 | T004-AC07: tři formáty stejné baseline, bezpečný rendering, atomické publikování |
| T004-R08 | Aktualizace a rozdíly | T037, T039 | T004-AC08: plný/inkrementální výsledek ekvivalentní, negative lookup invalidace a label-only diff |
| T004-R09 | Reálné testy a výkon | T041–T043 | T004-AC09: upstream-backed E2E, negativní corpus, bounded traversal a měřený budget |
| T004-R10 | Samostatné dodání a dokumentace | všechny, T044 | T004-AC10: jeden task/soubor/větev/PR; všechny AC mají konkrétní výsledky a capability limity |

Každé podřízené AC je normativní. Nadřazené AC lze označit VERIFIED_IN_SCOPE až po doložení všech odpovídajících podřízených AC a konkrétního běhu. Příprava této specifikace neplní implementační acceptance.

## 7. Registr atomických úkolů

Každý řádek je samostatný soubor a samostatný PR. ID je globální z existující číselné řady; T-005 v názvu znamená T005, nikoli další souběžnou řadu. Číslo 150 z příkladu zadavatele nebylo rezervací.

| Task | Soubor a cíl | Závislosti | Stav |
|---|---|---|---|
| T005 | [Verzovaný společný model pohledu](T-005_add-view-model.md) | T004 kontrakt | SPECIFICATION |
| T006 | [Výběr kontextů pro více služeb](T-006_select-service-contexts.md) | T005; T003-S02 | SPECIFICATION |
| T007 | [Explicitní vlastnictví služeb](T-007_define-service-ownership.md) | T005 | SPECIFICATION |
| T008 | [Inventář služeb a externích systémů](T-008_project-service-inventory.md) | T006, T007 | SPECIFICATION |
| T009 | [Evidence a pokrytí agregovaných objektů](T-009_propagate-view-evidence.md) | T005, T006; T003-S07-W08 | SPECIFICATION |
| T010 | [Katalog poskytovaných HTTP rozhraní](T-010_catalog-http-providers.md) | T008, T009 | SPECIFICATION |
| T011 | [Katalog používaných HTTP rozhraní](T-011_catalog-http-consumers.md) | T008, T009; T003-S07-W06 | SPECIFICATION |
| T012 | [Katalog Kafka producerů a consumerů](T-012_catalog-kafka-interfaces.md) | T008, T009; T003-S07-W04 | SPECIFICATION |
| T013 | [Připojení verzovaných integračních kontraktů](T-013_attach-interface-contracts.md) | T010, T011, T012 | SPECIFICATION |
| T014 | [Projekce ověřených vzdálených bindingů](T-014_bind-remote-interfaces.md) | T013; T003-S07-W07 | SPECIFICATION |
| T015 | [Databáze a jiné datové závislosti](T-015_project-data-resources.md) | T008, T009; T003-S06 | SPECIFICATION |
| T016 | [Agregace topologie služeb](T-016_aggregate-service-topology.md) | T014, T015 | SPECIFICATION |
| T017 | [Filtrování a omezení velikosti topologie](T-017_filter-topology-scope.md) | T016 | SPECIFICATION |
| T018 | [Dohledání zdrojů high-level objektů](T-018_explain-view-elements.md) | T009, T016 | SPECIFICATION |
| T019 | [Read-only CLI pro architektonické pohledy](T-019_add-architecture-json-cli.md) | T010, T011, T012, T013, T017, T018 | SPECIFICATION |
| T020 | [Markdown katalog integračních rozhraní](T-020_render-interface-markdown.md) | T013, T019 | SPECIFICATION |
| T021 | [Mermaid schéma služeb](T-021_render-topology-mermaid.md) | T017, T019; T003-S07-W09 | SPECIFICATION |
| T022 | [Markdown report topologie a detailů](T-022_render-topology-markdown.md) | T018, T021 | SPECIFICATION |
| T023 | [Model business procesu a jeho revizí](T-023_define-business-process-model.md) | T005, T009 | SPECIFICATION |
| T024 | [Inventář doložených spouštěčů](T-024_discover-process-triggers.md) | T008, T023 | SPECIFICATION |
| T025 | [Lokální technický průběh od vstupu](T-025_build-local-process-path.md) | T023, T024; T003-S04 | SPECIFICATION |
| T026 | [Seskupení technických uzlů do business kroků](T-026_collapse-business-steps.md) | T025 | SPECIFICATION |
| T027 | [Průchod procesu přes HTTP rozhraní](T-027_cross-http-process-boundary.md) | T014, T025 | SPECIFICATION |
| T028 | [Asynchronní návaznosti procesu](T-028_cross-async-process-boundary.md) | T012, T014, T025 | SPECIFICATION |
| T029 | [Chybové větve, retry a kompenzace](T-029_project-process-failures.md) | T025, T028; T003-S07-W05 | SPECIFICATION |
| T030 | [Packet pro business pojmenování agentem](T-030_prepare-process-label-packet.md) | T024, T026 | SPECIFICATION |
| T031 | [Validace agentových návrhů](T-031_validate-process-annotations.md) | T023, T030 | SPECIFICATION |
| T032 | [Schválení a revizní historie procesů](T-032_persist-process-review.md) | T031 | SPECIFICATION |
| T033 | [Katalog identifikovaných procesů](T-033_catalog-business-processes.md) | T024, T032 | SPECIFICATION |
| T034 | [CLI životního cyklu procesů](T-034_add-process-cli.md) | T027, T028, T029, T030, T031, T032, T033. Čtecí výřez T019, T023–T025 | SPECIFICATION rev. 2 |
| T035 | [Mermaid business průběhu](T-035_render-business-process-mermaid.md) | T026, T027, T028, T029, T034 | SPECIFICATION rev. 2 |
| T036 | [Markdown business report](T-036_render-business-process-report.md) | T033, T035 | SPECIFICATION |
| T037 | [Invalidace odvozených pohledů](T-037_invalidate-derived-views.md) | T018, T032, T033 | SPECIFICATION |
| T038 | [Atomická publikace exportů](T-038_publish-view-artifacts-atomically.md) | T022, T036, T037 | SPECIFICATION |
| T039 | [Sémantický diff dvou snapshotů](T-039_diff-architecture-and-processes.md) | T037, T038 | SPECIFICATION |
| T040 | [Instrukce host agenta pro pohledy](T-040_add-agent-process-instructions.md) | T034, T036 | SPECIFICATION |
| T041 | [End-to-end acceptance architektury](T-041_verify-architecture-acceptance.md) | T020, T021, T022, T038 | SPECIFICATION |
| T042 | [End-to-end acceptance business procesů](T-042_verify-process-acceptance.md) | T035, T036, T038, T040 | SPECIFICATION |
| T043 | [Limity výkonu a velikosti](T-043_bound-view-performance.md) | T017, T025, T037 | SPECIFICATION |
| T044 | [Dokumentace a release gate](T-044_document-high-level-capabilities.md) | T039, T040, T041, T042, T043 | SPECIFICATION |

## 8. Pořadí a samostatnost

- T004-S01 základ: T005–T009.
- T004-S02 architektonické MVP: T010–T022; uvolnit po odpovídajícím E2E subsetu T041. T041 může dodat úplný corpus později, ale MVP nesmí vynechat vlastní testy.
- T004-S03 lokální proces: T023–T026, pak anotace T030–T033.
- T004-S04 distribuovaný proces: T027–T029 a CLI/render T034–T036.
- T004-S05 lifecycle a provozní kvalita: T037–T040.
- T004-S06 dokončení: T041–T044.

Číselné pořadí je navigace; dependency DAG je autoritou. Například HTTP provider a consumer katalog lze implementovat odděleně po společném základu. Samostatný task znamená mergeovatelný izolovaný kontrakt po splnění závislostí, ne nulové závislosti. Žádný agent nemá převzít celý T004 jako jeden implementační úkol.

## 9. Společné testy, migrace a DoD

Každý implementační PR musí obsahovat pozitivní, negativní a regression testy skutečného kontraktu; povinný full pytest a diff check. Compiler/framework a render změny mají skutečný worker/parser gate. Syntetický graph test doplňuje, nenahrazuje upstream-backed E2E. U každého AC eviduj test/fixture, commit a run. Chybějící povinný toolchain je BLOCKED/SKIP, nikdy PASS.

Migrační politika: zachovat graph v1/v2/v3 a stávající CLI; nové manifest fields jsou aditivní/versioned; neznámé verze se odmítají před zápisem. Exporty mají vlastní versioned schema a atomic generation manifest. Review změna je append-only revision s CAS. Identita není timestamp a label není klíč. Zdroje mimo checkout se nenahrávají na služby.

Každý task má ve svém souboru přesné branch/PR jméno a DoD. Jedna větev a jeden PR na jeden task, žádný automatický merge. Nový change note používá nezávislé max+1 číslování po kontrole main/open PRs. README, capability docs a acceptance matrix musí odpovídat skutečnému kódu. Dokumentace omezení je součást výsledku, nikoli doplněk.

## 10. Příklad a zbývající omezení

Ilustrační fixture (nejde o tvrzení o konkrétním uživatelském projektu): HTTP trigger → validace → alternativa odmítnutí nebo persistence → HTTP integrace → publish event; dva consumers jsou nezávislé možné návaznosti. Externí nedostupný consumer zůstane boundary. „Schválení objednávky“ je navržený business název, nikoli závěr z libovolného UPDATE.

I po dokončení bude rozsah limitován podporovanými parsery, compiler kontexty, konfigurací a dodanými kontrakty. Bez runtime evidence není znám skutečný průběh konkrétní instance. Bez explicitního business review nemusí být správné pojmenování procesu. Bez datového důkazu není známa dostupnost vstupů. Tyto limity musí být viditelné v reportech a release dokumentaci.
