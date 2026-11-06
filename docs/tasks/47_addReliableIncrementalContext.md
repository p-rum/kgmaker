# T047 — Spolehlivý inkrementální graf a doložený kontext implementačního agenta

- Task ID: **T047**
- Revision: **1**
- Datum: **2026-11-06**
- Stav: **SPECIFICATION** — zadání cílového chování; tento dokument neimplementuje ani necertifikuje popsané funkce.
- Baseline: [main fbb0957be895e1e8967339bba6cd7e4b4e7b769f](https://github.com/p-rum/kgmaker/tree/fbb0957be895e1e8967339bba6cd7e4b4e7b769f).
- Dokumentační větev: `docs/t047-reliable-incremental-context`.
- Zadání navazuje na technický přehled z 6. 11. 2026; z předchozího přehledu přebírá jako doplňující experiment řízený průchod grafem a práci s pamětí.
- Supersedes: **nic**. T003, T037 ani T046 se neruší, nepřečíslují a neprohlašují za hotové.
- Závislosti: existující model/store/provider/workspace; pro inkrementální infrastrukturu T003-S10-W01–W06; pro projekce T037/T038; pro execution evidence T046-S01/S05/S06.
- První samostatný výstup: reprodukovatelná mutation fixture s ručním oracle, poté stabilní symbolové klíče a kontrola příchozích hran.

## 1. Výsledek pro uživatele

Když analytik změní požadavek nebo implementační agent upraví Kotlin endpoint, TS klienta či integrační kontrakt, KGMAKER:

1. odvolá zastaralé důkazy, zachová stále doložené vztahy a nevytvoří duplicity jen posunem řádků;
2. vysvětlí dopad cestou přes konkrétní vztahy, revize a zdroje, včetně nezměněných volajících a dalších repozitářů;
3. připojí relevantní serverovou autorizaci, validaci a tenant/data-access omezení do kontextu agenta;
4. odliší platný výsledek testu nad aktuálními vstupy od starého výsledku, pouhého návrhu a tvrzení agenta;
5. přizná neúplné rozlišení, neznámé ochrany, zastaralý compiler kontext a vyčerpaný rozpočet.

Úplnost znamená pouze úplnost v deklarované podporované fixture a vybraném kontextu. Statický graf není důkaz runtime dostupnosti, bezpečnosti aplikace ani správnosti celého projektu.

## 2. Ověřená výchozí situace a implementační místa

Rekognoskace proběhla čtením souborů a testů nad uvedeným SHA přes GitHub. V této práci nebyl spuštěn checkout, CLI ani testy aplikace. Obsah `.kgmaker/GRAPH.md` v odpovědi konektoru nebyl dostupný; `.kgmaker/NOTES.md` obsahuje jen obecný úvod. Následující závěry proto stojí na zdrojích, nikoli na předpokládané platnosti uloženého grafu.

| Doložené místo | Současné chování / pozorování | Důsledek pro zadání |
|---|---|---|
| `scanner.py:_stable_id` a `_extract_symbols` | Syntaktické ID zahrnuje druh, cestu, jméno a volitelné číslo řádku; extraktor řádek používá. | Stabilní deklaraci a konkrétní výskyt je třeba oddělit. Nejde automaticky o stejný problém v compiler workeru. |
| `model.py:KnowledgeGraph.from_dict` | Čte graph v1/v2/v3, kontroluje dangling references, evidence kinds a kontexty; v3 nese symbols/call_sites/CFG. | Rozšiř stávající kontrakt. Žádný druhý graf s jinými autoritativními ID. |
| `graph_provider.py:validate_context_snapshot`, `retain_compiler_layer`, `_merge_contexts` | Ověřuje obsah, uchovává platné compiler kontexty, stale kontext ponechá diagnosticky a jeho fakta neprojektuje jako platná. Kolize compiler ID odmítá. | Zachovej bezpečný fallback; neobnovuj staré compiler hrany jen proto, že existuje stejný název. |
| `store.py:save_graph` | Validuje graf a atomicky zapisuje jednotlivé soubory. | Samotný atomický zápis souboru nezaručuje konzistenci celé více-souborové generace. |
| `workspace.py:qualified/source_key/snapshot_workspace` | Repo-qualified identity, snapshoty, cache a kontrola změn zdrojů během snímání. | Reuse kvalifikaci, manifest a baseline; absolutní checkout cesta není identita repozitáře. |
| `semantic.py:apply_semantic_patch` | Kontroluje update_id, integritu packetu a file hashes; patch má omezený dopad. | Zachovej ochranu packetů, nepovoluj obejití mismatch a nevymýšlej LLM vazby. |
| `context.py:_neighbors`, `_truncate`, `prepare_packet` | Omezený seznam sousedů; ořezávání po kategoriích; kontext a historické epizody. | Přidej typované cesty a zachování povinných diagnostik/ochran pod rozpočtem. |
| `memory.py:episode_freshness`, `build_capture_episode` | Epizody již mají obsahovou vazbu a freshness. | Rozšiř evidenci skutečných běhů; nebuduj druhou paměť. |
| `workflow.py:record_artifact/save_task/advance_task` | Existující role, stavy, packet bindings a ukládání artefaktů. | Integruj dokončení přes společný validátor, včetně přímého knihovního save. |
| `docs/production-analysis-progress.md` | T003-S10 je PARTIAL; zbývají selektivní compiler/feature invalidace a negative lookups. | Není přípustné vydávat plánované cache kontrakty za dostupné API. |

Relevantní existující testy: `tests/test_graph_provider.py`, `test_compiler_workers.py`, `test_worker_protocol.py`, `test_scanner.py`, `test_feature.py`, `test_memory.py`, `test_workflow.py`. Zejména zachovej testy `test_stale_module_is_projected_out_while_other_context_remains_usable`, `test_invalid_second_module_does_not_publish_over_first` a `test_scan_hook_and_feature_retain_compiler_layer_without_processes`.

### Rozpracované změny

T046 není v baseline main. Je dodáváno přes otevřené PR [#41](https://github.com/p-rum/kgmaker/pull/41), [#42](https://github.com/p-rum/kgmaker/pull/42), [#43](https://github.com/p-rum/kgmaker/pull/43), [#44](https://github.com/p-rum/kgmaker/pull/44), [#45](https://github.com/p-rum/kgmaker/pull/45), [#40](https://github.com/p-rum/kgmaker/pull/40).

Při přípravě byl přečten T046 revize 2 z PR #41 HEAD `a9cdcab41ef0c10bbe3bc0acdfabecd070f2419b`. Zavádí obsahové reference, journal, templates/testgen a volitelné schvalovací brány. Execution evidence v tomto zadání se musí připojit k jeho `provenance.py` a workflow, nikoli je znovu implementovat. Otevřené PR nejsou důkaz dokončení ani test PASS na současném main.

| Oblast | Vlastník existujícího rozsahu | Přínos T047 a hranice |
|---|---|---|
| Stage cache / reverse index / negative lookup | [T003-S10-W01](T003-S10-01-stageContentCache.md), [W02](T003-S10-02-reverseDependencyIndexes.md), [W03](T003-S10-03-negativeLookupInvalidation.md) | Konkrétní pravidla identity, podpůrných důkazů, příchozích hran a nové acceptance scénáře. |
| Full/incremental equivalence a concurrency | [W04](T003-S10-04-filesystemMutationEquivalence.md), [W06](T003-S10-06-cacheCorruptionConcurrency.md) | Kotlin/TS oracle, failure injection a baseline parity. |
| Feature revise | [W05](T003-S10-05-selectiveFeatureRevise.md) | Obsahově vázaná hranice dopadu a bezpečnostní kontext. |
| High-level invalidace/publikace | [T037](T-037_invalidate-derived-views.md), [T038](T-038_publish-view-artifacts-atomically.md) | Sdílený fingerprint a generační mechanismus, žádná paralelní cache. |
| Integrační kontrakty | [T013](T-013_attach-interface-contracts.md), [T014](T-014_bind-remote-interfaces.md), [T003-S07-W07](T003-S07-07-crossServiceContractMapping.md) | Reuse přesných contract/release bindings; nezavádět name-only FE–BE matching. |
| Testy a traceability | T046, výše uvedené PR | Doklady skutečného běhu, freshness a odvozený stav ověření; žádný nový test runner ani journal. |

Agent před každým krokem znovu ověří upstream SHA a implementované API. Chybí-li upstream, dodá změnu v jeho existujícím zadání/PR s odkazem na T047, nebo označí navazující krok BLOCKED. Stejný kód se nesmí implementovat současně pod dvěma Task ID.

## 3. Zdroje a míra jejich ověření

| Zdroj | Co přebíráme | Stav ověření v této práci |
|---|---|---|
| [Knot](https://www.knot.kz/), [knot-server 0.9.8](https://docs.rs/crate/knot-server/0.9.8) | Motivaci pro regresní test normalizace cest, odstraňování starých entit a příchozích hran. | Primární dokumentace crate potvrzuje historickou změnu uložených cest na repo-relative a reindex. Přesný incident 0.9.8 a počty z přehledu se z přístupného textu znovu ověřit nepodařilo; nepoužíváme je jako důkaz chyby KGMAKERu. |
| [A.S.E 2.0](https://arxiv.org/abs/2611.06294) | Funkční kontext může vynechat ochranný mechanismus; testovat funkčnost i negativní bezpečnostní scénáře. | Ověřen abstrakt primárního preprintu. Experimentální výsledky nejsou měřením KGMAKERu. |
| [From Ripple to Boundary](https://arxiv.org/abs/2610.36549) | Obsahové fingerprinty a vysvětlitelná propagace dopadu. | Primární stránku ani HTML se při této práci nepodařilo načíst. Bereme jako inspiraci z předchozího přehledu, ne jako znovu ověřenou záruku bezpečnosti. |
| [Soei](https://arxiv.org/abs/2610.39468) | Oddělení tvrzení hotovo od dokladu ověření po změně. | Ověřen abstrakt primárního preprintu; omezený korpus neumožňuje předpověď přínosu pro KGMAKER. |

Následující datové kontrakty, kroky a prahy jsou návrh pro KGMAKER odvozený z jeho kódu. Nejsou převzatým benchmarkem ani slibem procentuální úspory.

## 4. Rozsah a neřešené oblasti

Priorita: Kotlin/Spring Boot backend, TypeScript frontend, existující PostgreSQL/Flyway model a HTTP/Kafka kontrakty. Implementace KGMAKERu zůstává v Pythonu; jazyková fakta dodávají existující JVM/TS workers.

Non-goals: nová graph/vector databáze, náhrada compileru LLM, univerzální security scanner, automatická oprava zranitelností, live discovery infrastruktury, deployment, implicitní spuštění aplikace/buildů/testů/migrací, nový LLM API klient, automatický merge, přepis všech historických ID a implementace clusteringu architektury z ASNER.

Konfigurace se neodfiltruje plošně: zůstává oddělená svým scope/role/origin a může být důkazem podmínky ochrany. Testy a číselníky se nestávají produkčním execution tokem pouze četností použití.

## 5. Společné datové kontrakty a invariants

Názvy nových polí níže jsou návrh. Agent musí sladit serializaci se skutečným upstream schématem a přidat jeho validátor; libovolné dictionary pole bez verze není implementace kontraktu.

### 5.1 Identita, výskyt a revize

- **LogicalSymbolKey** = verzovaný kanonický tuple `repo_id, language, module/source-set/scope realm, qualified_owner, kind, declared_name, normalized_signature`.
- Neobsahuje absolutní checkout root, číslo řádku, čas generování, hash celého souboru ani momentální content hash compiler kontextu.
- Signatura je jazykově definovaná: Kotlin receiver, deklarované typy parametrů a arita/type parameters; TS module/export a rozlišená signatura deklarace. Nepoužívej pouhý display text compileru bez normalizace/verze.
- Existující context-qualified compiler ID a source-only node ID nejsou bez migrace přepsány. Logical key je vazba mezi snapshoty; konkrétní fakt si zachovává svůj context/evidence ID.
- **Occurrence** nese cestu a source range; **revision** nese obsah/signaturu/kontext/verzi pravidel. Posun komentářem mění occurrence a source snapshot, nikoli logical key pojmenované deklarace.
- Rename symbolu nebo změna signatury vytvoří nový key. Starý se odvolá; alias pouze jako doložený rename mapping s původem, nikdy automatické přesměrování starého volání.
- Přesun souboru zachová key jen pokud se nezmění jazyková identita (např. Kotlin package/owner). Změna TS module/export path může legitimně vytvořit nový key.
- Lokální anonymní funkce a nerozlišené overloady: identita omezená na snapshot, `identity_quality=UNRESOLVED` či dokumentovaný ekvivalent. Žádná falešná stabilita.
- Repo/source-set/profile varianty se nesmějí slít. Logical key může mapovat více kontextových výskytů, výběr konkrétního kontextu zůstává povinný.

**SourceKey** používá existující workspace kvalifikaci. Cesta uvnitř repo je POSIX relative. Normalizace vstupních Windows separatorů probíhá na boundary; cesty se globálně nepřevádějí na lowercase. Odmítni escape mimo root, nejednoznačný case alias a nepovolené symlinky. Obsah se hashuje z přesných bytů; CRLF/LF se nesmí bez explicitního kontraktu považovat za stejný snapshot.

### 5.2 Podpora tvrzení

Reuse `evidence_ids/context_ids`; přidej reverzní vazby v existujícím stage cache/store:

- `source_key + content_hash + producer/rule_version -> evidence_id`;
- `evidence_id -> supported assertions`;
- `target logical key/contract -> incoming assertions + resolver lookup keys`;
- `assertion/contract/context -> dependent conclusions/views/packets`.

Jedna nezávislá podpora může stačit; složený důkaz může vyžadovat více podmínek současně. Model musí explicitně rozlišit alternativy (OR) a členy společné support group (AND). Při odstranění jedné nutné podmínky skupina neplatí; pouhý zbývající počet evidence IDs nestačí.

Hrany se slučují podle typované identity, scope a kontextu; ne přes řádky citace a ne napříč různou silou evidence. Sdílená entita přežije, dokud má platný deklarativní zdroj nebo platnou podporu. Historické důkazy smějí zůstat v historii, nikoli v current projection.

### 5.3 Plán změny a publikace

Návrh interního `ChangePlan`:

```json
{
  "schema_version": 1,
  "base_generation": "generation:old",
  "source_snapshot_hash": "sha256:...",
  "changed_sources": [],
  "revoked_evidence_ids": [],
  "dirty_assertions": [],
  "dirty_lookup_keys": [],
  "recheck_incoming": [],
  "invalidated_artifacts": [],
  "coverage": "PARTIAL",
  "diagnostics": []
}
```

Čistá příprava plánu nezapisuje. Apply ověří baseline znovu, připraví kandidátní generaci, validuje reference a atomicky publikuje manifest přes compare-and-swap. Konkurenční změna nebo chyba ponechá poslední validní generaci beze změny. Report uvede důvody invalidace a cache reuse; výkonové statistiky nejsou součástí sémantické identity.

Read-only snapshot/impact/context/report nespouští worker. Stale compiler kontext se přizná a doloží příkazem pro explicitní refresh; jeho fakta se nevracejí jako current. Větší bezpečná invalidace je pro první verzi přípustná, musí být měřena a reportována.

### 5.4 Ochranné mechanismy

Nový odvozený záznam `Safeguard` ve společné modelové/evidence vrstvě:

- id, chráněný target, druh `AUTHORIZATION | INPUT_VALIDATION | TENANT_ISOLATION | DATA_ACCESS`;
- místo vynucení `SERVER | CLIENT | UNKNOWN`;
- evidence/context/source refs, fingerprint, applicability conditions;
- stav applicability `PROVEN_STATIC | CONDITIONAL | UNKNOWN` a coverage gaps.

Tyto stavy popisují statické přiřazení, nikoli zaručenou bezpečnost. Samotná anotace `@PreAuthorize` bez doloženého zapnutí method security zůstává podmíněná. TS validace nenahrazuje serverovou. Název `tenantId` není důkaz izolace dat. Chybějící nalezená ochrana znamená UNKNOWN, nikoli automaticky zranitelnost.

### 5.5 Kontext a hranice dopadu

Rozšiř existující packet o logické sekce `impact_paths`, `safeguards`, `coverage_gaps`, `omitted_required_context` a `verification_summary`. Vše je svázané se snapshotem a pravidly.

Každá cesta nese seed, směr, typy hran, původ/evidence, kontext a důvod zařazení cíle. Přechod FE → HTTP → BE nebo přes Kafka je pouze přes existující doložený binding. Name-match patří do candidates, nikdy do proven path.

Hashování: obsahové hashe listů kontraktů, závislostních manifestů a kontextu; reverzní dependency index propaguje dirty stav fixpointem. Graf kódu může mít cykly. Pokud se použije Merkle DAG, nejprve kondenzuj silně souvislé komponenty; jinak použij visited/fixpoint bez předstírání DAG. Hash je důkaz změny vstupu, nikoli úplnosti resolveru.

### 5.6 Doklad ověření

Reuse T046 obsahové reference a journal. Navržený `VerificationRecord` má:

- run_id, task/step/requirement reference, runner a jeho verzi, command digest;
- přesné repo HEADs a worktree/input manifest hash, včetně testů, konfigurace, lockfiles a relevantních untracked zdrojů;
- started/completed event, exit code, výsledek `PASS | FAIL | SKIP | NOT_RUN | ERROR`;
- evidence origin `RUNNER_CAPTURED | IMPORTED | AGENT_DECLARED`;
- rozsah ověření, artifact digest a redigované diagnostiky.

Freshness `CURRENT | STALE | UNKNOWN` je oddělená od výsledku. Historické PASS po změně zůstane historické PASS, ale je STALE. Importovaný záznam bez ověřitelné obsahové vazby ani text agenta nemůže splnit completion gate. Ani lokální hash/journal neprokazuje identitu nezávislého člověka.

Výchozí verze vynucuje shodu celé deklarované vstupní množiny. Selektivní přenos PASS po nesouvisející změně je možný až s doloženou úplnou závislostní množinou; jinak konzervativní STALE. Samotné shodné HEAD nestačí při dirty worktree.

## 6. Implementační kroky

Každý krok má samostatnou větev a PR. Uvedené nové názvy modulů/testů jsou návrh; existující ekvivalent se rozšiřuje. Jeden PR může implementovat odpovídající existující upstream work package a uvést obě sady acceptance, ale nesmí vytvořit duplicitní implementaci.

### T047-S01 — Reprodukční fixture a ruční oracle

- Větev: `test/t047-s01-mutation-oracle`.
- Depends on: pouze baseline; upstream cache není nutná pro přípravu corpus.
- Moduly: navržené `fixtures/incremental-integrity/`, `tests/test_incremental_equivalence.py`; reuse compiler/workspace fixtures.
- Připrav dva repo (Kotlin/Spring BE a TS FE), dva BE moduly, samostatný caller a nezávislý modul. Zahrň overload, endpoint/DTO, TS klienta, explicitní API kontrakt/release mapping, Kafka binding a izolovaný Flyway stream.
- Přidej ručně zapsanou ground-truth tabulku logical symbolů, očekávaných hran a úmyslně unresolved míst. Oracle se negeneruje stejnou funkcí jako testovaný graf.
- Mutation scripts provádějí operace z §7 v deterministickém pořadí; vracejí checksum vstupů a očekávaný rozdíl. Žádné bankovní kódy ani data.
- **T047-R01 / T047-AC01:** Fixture jde resetovat a dvě spuštění mutation scripts dají stejné vstupy. Čistý scan se porovná s ručním oracle; známá mezera je explicitně XFAIL/BLOCKED s konkrétní chybou, nikoli vynechaná assertion.
- Ověření: golden fixture loader, malformed oracle rejection, reset/replay, ruční review BE–FE bindingu. PR ještě nesmí tvrdit incremental parity.

### T047-S02 — Stabilní logical key a kanonické cesty

- Větev: `feat/t047-s02-logical-symbol-keys`.
- Depends on: S01.
- Moduly: `scanner.py`, `model.py`, `inspection.py`, `worker_protocol.py`, `workspace.py`; workers pouze tam, kde doložená signatura chybí. Návrh sdílené funkce v `symbol_identity.py`.
- Implementuj kontrakt §5.1. Přidej explicitní identity version a mapper occurrence → logical key. Nenech regex vrstvu předstírat compiler resolution; pro nejednoznačné deklarace vrať UNKNOWN.
- Vypracuj mapu staré ID → nový logical key; nejednoznačné mapování vyžádá explicitní reindex a nový semantic packet. Staré packet IDs nepřepisuj.
- **T047-R02 / T047-AC02:** Komentář nad pojmenovanou metodou zachová logical key, různé overloady/shody jmen mezi repozitáři a test/prod zůstanou odlišné. Rename/signature change má explicitní zánik/vznik. Snapshot-bound lokální symbol se nesmí chybně sloučit.
- Ověření: `tests/test_symbol_identity.py`, skutečné Kotlin/TS worker fixtures, migrace legacy v1/v2/v3, Windows separátory/case/escape/collision. Při invalidní identitě nulová mutace.

### T047-S03 — Odvolání podpory a zachování sdílených entit

- Větev: `feat/t047-s03-evidence-support`.
- Depends on: S02; reuse T003-S10-W01/W02, nebo dodání těchto kontraktů ve stejném deklarovaném upstream PR.
- Moduly: `model.py`, `store.py`, `graph_provider.py`, `semantic.py`.
- Eviduj vlastníka extrakce a support groups dle §5.2. Re-extrakce souboru nahradí jeho příspěvek; nesmaže bez rozlišení všechny incidentní hrany.
- V kandidátním snapshotu odvolej jen neplatné důkazy. Hranu zachovej jen pokud zbývá kompletní platná alternativa. Pruning uzlů proveď až po vyhodnocení podpory.
- Semantic fakta z LLM zachovají vlastní původ; logický key nepovýší jejich evidence kind.
- **T047-R03 / T047-AC03:** Dvě nezávislé podpory → odstranění jedné zachová vztah; odstranění poslední jej odvolá. AND skupina po ztrátě jednoho členu neplatí. Sdílený kontrakt s druhým zdrojem přežije. Opakované apply nevytvoří duplicity.
- Ověření: `tests/test_evidence_support.py`, vadné evidence refs, support cycle/unknown producer, duplicate receipt a semantic packet mismatch.

### T047-S04 — Příchozí hrany, negative lookups a dirty closure

- Větev: `feat/t047-s04-incoming-edge-invalidation`.
- Depends on: S03 a T003-S10-W02/W03.
- Moduly: `graph_provider.py`, `inspection.py`, `workspace.py`, `feature.py`, existující reverse index.
- Z předchozí generace zachyť nezměněné callers do změněných cílů před odebráním faktů. Indexuj i neúspěšné lookupy podle resolver realm, symbol/contract klíče a podmínek.
- Body-only změna: logická deklarace může přežít; evidence závislá na těle musí projít revalidation. Signature/delete: stará příchozí hrana se nesmí slepě připojit; caller/kontext označ dirty.
- Pozitivní aktualizace symbolu musí invalidovat i dřívější unresolved lookup, nejen existující edges. Cross-repo revalidation vychází z release/contract map, nikoli podobnosti názvů.
- Offline cesta uchová platné nedotčené kontexty; dotčené compiler vazby se vrátí až po explicitním inspect. Neznámou dependency boundary označ PARTIAL a invaliduj bezpečně širší oblast.
- **T047-R04 / T047-AC04:** Po podporovaném explicitním refreshi je nezměněný caller zachován pro platný cíl, odstraněn/označen unresolved pro zaniklý cíl a nově vyřešen po přidání dříve chybějícího cíle; stejně přes dvě repo. Nezávislý modul zůstává použitelný.
- Ověření: `tests/test_incoming_invalidation.py`, negativa rename/overload/profile/classpath/nový provider; test nulového subprocess během scan/context.

### T047-S05 — Atomická generace a souběh

- Větev: `feat/t047-s05-atomic-generations`.
- Depends on: S04 a T003-S10-W06; integrace odvozených view až po T038.
- Moduly: `store.py`, `graph_provider.py`, `workspace.py`, existující atomic/CAS helper; nevytvářej konkurenční view publisher.
- Zaveď ChangePlan prepare/validate/apply podle §5.3. Evidence indexy a graf musí odkazovat na jednu commitnutou generaci.
- Ověř zdroje při přípravě i před publication; starý manifest uchovej, staging cleanup nesmí mazat current ani generaci právě čtenou readerem.
- Specifikuj podporu lock/CAS na Windows a POSIX. Pokud platforma nemá implementovaný bezpečný kontrakt, zápis odmítni s jasnou diagnostikou; netvrď univerzální atomickou podporu.
- **T047-R05 / T047-AC05:** Výpadek mezi zápisy, dvě souběžná apply a změna zdroje během výpočtu nedají smíšenou generaci; při chybě zůstane původní graph/index/manifest čitelný a obsahově stejný.
- Ověření: fault injection před a po publish, stale expected-generation, corrupt cache fallback, čtenář souběžně se zápisem a restart recovery; žádné timestamp-only CAS.

### T047-S06 — Ekvivalence úplného a inkrementálního přepočtu

- Větev: `test/t047-s06-full-incremental-parity`.
- Depends on: S01–S05 a T003-S10-W04.
- Moduly: test harness z S01; `scanner.py`, `semantic.py`, `store.py` jen při prokázané chybě.
- Pro každou mutaci spusť full výpočet z prázdné cache a incremental ze staré generace nad identickými finálními vstupy, stejným toolchainem a stejnými uloženými sémantickými extrakcemi.
- Porovnávej logické uzly, typované edges, support, contexts, coverage a diagnostics. Lze vynechat čas, absolutní scratch root a execution/cache counters. Nesmí se normalizací zahodit evidence kind, scope, source hash, unresolved či stale stav.
- Source-only srovnávej se source-only; compiler parity až po ekvivalentním explicitním worker refreshi na obou stranách. Offline stale varianta má samostatný oracle.
- **T047-R06 / T047-AC06:** Celá matice §7 bez duplicit, dangling edges či ztráty platného calleru; idempotence a shoda s ručním oracle. Full i incremental mohou sdílet chybu, proto jejich vzájemná shoda sama nestačí.
- Ověření: metamorfní test přidání nerelevantních testů/enumů, dva různé checkout roots, cache off/on, permutace pořadí souborů. Nekoriguj oracle jen aby test prošel.

### T047-S07 — Model a omezená extrakce serverových ochran

- Větev: `feat/t047-s07-safeguard-evidence`.
- Depends on: S02/S03, platné Spring kontexty; nezávislé na dokončení celého incremental pipeline.
- Moduly: `framework.py`, `spring_beans.py`, `spring_conditions.py`, `inspection.py`, `model.py`; případný `safeguards.py` jako projekce existujících důkazů.
- Implementuj §5.4; první podporovaný subset: compiler-resolved method authorization annotation se zapnutím method security, controller `@Valid` s přiřazenými DTO constraints, explicitní evidence-backed custom guard mapping.
- SecurityFilterChain/matcher pořadí, proxy/self-invocation, dynamický SpEL a tenant predikáty mimo prokázaný subset vracejí CONDITIONAL/UNKNOWN s důvodem. Rozšíření matcherů se nesmí tvářit jako plná Spring Security podpora.
- Custom guard mapping obsahuje target, podmínky a konkrétní zdroje; je deklarací uživatele, ne automaticky compiler proof. TS guard je CLIENT.
- **T047-R07 / T047-AC07:** Podporovaný endpoint má dohledatelnou ochranu; vypnuté method security nebo změna profilu ji zneplatní/podmíní. Stejnojmenná vlastní anotace, pouhý tenantId a TS-only validace neprojdou jako prokázaná serverová ochrana.
- Ověření: `tests/test_safeguards.py`, skutečné compiler fixtures a explicitní negativní runtime fixture tests v samostatně povoleném test běhu.

### T047-S08 — Řízený průchod a bezpečnostní kontext pod rozpočtem

- Větev: `feat/t047-s08-bounded-agent-context`.
- Depends on: S04/S07; existující feature/context API.
- Moduly: `context.py:_neighbors/_truncate/prepare_packet`, `feature.py`, `analysis_agent.py`.
- Přidej deterministický typovaný traversal s max_depth/max_nodes/max_edges a visited. Pořadí: explicitní target → platné impact paths → relevantní safeguards → testy → doplňující historické epizody.
- Balíček musí chránit základní target, snapshot, coverage a důvody vynechání. Při malém budgetu nevytěsni safeguards tiše; vrať `omitted_required_context`, počet a IDs vynechaných položek. Nepředávej instrukci k implementaci jako úplný podklad.
- Rozliš token estimate od skutečného tokenizer count; u hard limitu definuj tokenizer nebo konzervativní budget. Pokud se nevejde ani minimální envelope, vrať explicitní chybu bez zápisu.
- Historická epizoda jen jako hint, s freshness; nepřidává proven edge ani neodstraňuje coverage gap.
- **T047-R08 / T047-AC08:** FE → client → endpoint → service → persistence cesta je vysvětlitelná ve fixture; cyklus skončí; výsledek je deterministický; různé profily se nepromíchají. Povinná ochrana je obsažena nebo je její vynechání explicitní.
- Ověření: `tests/test_context_paths.py`, rozpočty 2k/4k/8k (nad skutečným minimem API), hranice hloubky 1/2/4/6, citlivé cesty a stale kontext. Dokumentuj co je omezený statický průchod.

### T047-S09 — Fingerprint kontraktů a vysvětlitelná hranice dopadu

- Větev: `feat/t047-s09-contract-impact-boundaries`.
- Depends on: S04/S08; T013/T014 a příslušné T003-S07-W07 bindingy; T037 pro uložené views.
- Moduly: `contract_inputs.py`, `interfaces.py`, `remote_interfaces.py`, `remote_mapping.py`, `feature.py`, existující dataflow/impact rozhraní.
- Hashuj normalizovaný kontrakt, jeho verzi/rules a provenance. Změna povinnosti DTO pole, Kafka schématu či Flyway targetu invaliduje doložené dependents a jejich závěry.
- Definuj result entries: target, reason, evidence path, change kind, old/new fingerprint, uncertainty. Reference-only edge se nesmí vydávat za vykonání.
- Zpracuj cykly podle §5.5; limit průchodu je PARTIAL s frontier, ne COMPLETE. Kromě known boundary zobraz unresolved frontier.
- **T047-R09 / T047-AC09:** Required-field mutace vrátí správný BE+TS dopad a konkrétní cestu; nesouvisející modul není vybrán bez důvodu. Cyklus se nezacyklí. Neznámé FE–BE mapování zůstane unresolved.
- Ověření: `tests/test_impact_boundaries.py`, ruční golden affected set, recall/precision, negative lookup na nového providera, profil/contract release změna, stale cache a stejné názvy v různých repo.

### T047-S10 — Záznam skutečného ověření

- Větev: `feat/t047-s10-verification-records`.
- Depends on: T046-S01 a jeho skutečné merged API; S02 pro symbol references, nebo explicitně file-bound první verze.
- Moduly: `workflow.py`, `memory.py`, upstream `provenance.py`, existující `build_runner.py` pouze jako zdroj schváleného běhu. Návrh `verification.py` pro validaci/import a freshness.
- Implementuj §5.6; zachycení manifestu před/po běhu. Změna vstupů během testu znamená nejvýše historický/neověřitelný výsledek, nikoli CURRENT PASS.
- Testy se spouštějí existujícím explicitním runnerem/host procesem, nikdy voláním prepare/status/scan. Timeout/interrupt/missing toolchain nevytváří PASS.
- Ukládej digests a redigované shrnutí; neukládej environment dump, tokeny, produkční payloady ani celé citlivé logy.
- **T047-R10 / T047-AC10:** Skutečný fixture test vytvoří content-bound PASS; úmyslná mutace fixture vytvoří FAIL; test script/config/lockfile edit při stejném HEAD zneplatní předchozí current výsledek. Agentem deklarované PASS je odlišeno a nestačí.
- Ověření: `tests/test_verification_records.py`, malformed/imported/tampered record, chybějící artefakt, changed-during-run, multi-repo vector, unknown untracked dependency a redaction.

### T047-S11 — Freshness v dokončení, reportu a paměti

- Větev: `feat/t047-s11-verification-freshness`.
- Depends on: S10 + T046-S05/S06; S09 pro selektivní odvození dopadu (jinak konzervativní invalidace).
- Moduly: `workflow.py:save_task/advance_task/record_artifact`, `context.py`, `memory.py`, upstream delivery/trace CLI a instrukce.
- Odvoď `verification_summary` z aktuálních požadovaných testů a evidence. Po nové editaci příslušný PASS nesplňuje gate, historie se nepřepisuje.
- Respektuj default-off lokální approvals z T046. Zaveď oddělenou explicitní verification policy; existující v1 `done` nemigruj na VERIFIED. Report vždy odlišuje workflow status od ověřenosti.
- V zapnuté policy kontroluj done v knihovním save i advance; nelze obejít CLI. Po již dokončeném tasku další editace odvodí STALE ověření, nesmaže historickou událost done.
- Testy a review jsou různé doklady. Nezávislé review nevznikne přejmenováním vlastní role či podpisem v JSON.
- **T047-R11 / T047-AC11:** PASS → edit → done je při zapnuté policy odmítnuto; rerun + požadované current review jej umožní. Policy off zachová kompatibilní postup, ale report zůstane UNVERIFIED/STALE. Přímý save neobejde gate.
- Ověření: rozšíření `tests/test_workflow.py`, `test_memory.py` a T046 delivery testů; revoke/stale decision, retry iterace, source-only nebo SKIP nesplní povinný compiler/runtime test.

### T047-S12 — CLI, migrační kontrakt a dokumentace

- Větev: `feat/t047-s12-incremental-context-cli`.
- Depends on: S06/S08/S09/S11.
- Moduly: `cli.py`, existující `feature_cli.py`, `project_cli.py`, `inspection_cli.py`, upstream delivery CLI; agent templates i instalované instrukce.
- Rozšiř stávající status/check/feature/task-context/trace výstupy o diagnostiky a doporučené explicitní refresh příkazy. Nevytvářej paralelní příkazový strom pro totéž.
- Před implementací zapiš konkrétní parser arguments do návrhu PR; příklady níže jsou scénáře, nikoli tvrzení o existujících nových flags.
- Dodej verzi schématu/reader matrix, explicitní migrate/reindex workflow, backup a rollback. Staré context/evidence zůstávají UNKNOWN/STALE, dokud je podporovaný postup nepotvrdí.
- Aktualizuj README, capability docs, `docs/production-analysis-progress.md`, `docs/acceptance-inventory.md`, obě sady agent templates. Init zachová ruční editace.
- **T047-R12 / T047-AC12:** Všechny dokumentované příklady projdou CLI smoke testem; v1/v2/v3 read nebo řízená migrace zachová data; nekompatibilní downgrade a legacy packet se odmítnou bez destrukce.
- Ověření: `tests/test_incremental_context_cli.py`, help/parser roundtrip, old-reader fixture, init-no-force, čistý report bez network/subprocess/build a bez zápisu při read-only operaci.

### T047-S13 — Benchmark, acceptance a předání

- Větev: `test/t047-s13-repository-agent-acceptance`.
- Depends on: S12; reuse T003-S11 benchmark/budget metodiku.
- Připrav alespoň 10 endpoint-change úloh se samostatným expected affected set, safeguards a negativními testy. Úlohy neodvozuj pouze z právě generovaného plánu.
- Porovnej keyword/grep baseline, současný packet a nový typovaný packet při stejném token budgetu, modelu a výchozím snapshotu. Offline retrieval metriky musí jít spustit bez LLM; agentové experimenty jsou samostatné a explicitní.
- Pro každý režim loguj nalezené soubory/safeguards, false positives/negatives, cestu a hloubku, token estimate/actual, skutečné tool calls, čas a cache práce. U experimentů s LLM zopakuj každou úlohu alespoň 3×, zaznamenej model/version/settings; neposkytuj z malého vzorku obecný ekonomický slib.
- **T047-R13 / T047-AC13:** Všechny deterministické AC projdou na deklarované podporované matici. Nový packet nezhorší recall povinných ochran proti baseline; všech 10 ručně označených podporovaných úloh má ochrany zahrnuté nebo explicitní blocking gap. Úspory se hodnotí až po správnosti.
- Ověření: benchmark report s raw results a manifesty, opakovaný warm/cold run; žádný odhad času nevydávej za měření. Nesplněný přínos popiš a ponech feature opt-in, dokud se opraví příčina.

## 7. Povinná mutation a negativní matice

| Operace / scénář | Očekávaný výsledek | AC |
|---|---|---|
| Přidání komentáře nad Kotlin metodou | Stejný logical key, nové source ranges, bez duplicit; compiler freshness podle snapshotu. | AC02, AC06 |
| Odstranění nesouvisející metody před cílem | Cíl nezíská novou logickou identitu jen posunem řádků. | AC02 |
| Body-only změna cíle, caller beze změny | Přehodnocení body-dependent důkazů; platný caller po explicitním refreshi zachován. | AC04, AC06 |
| Rename / změna signatury / overload | Žádné tiché přesměrování; nové rozlišení nebo unresolved. | AC02, AC04 |
| Delete cíle | Žádná dangling current edge; staré tvrzení pouze v historii. | AC03, AC06 |
| Přidání dříve chybějícího symbolu/provideru | Negative lookup invaliduje dependent a umožní nové rozlišení. | AC04, AC09 |
| Přesun souboru; root přesunut na jiný disk | Jazyková identita respektována; root není key; source locators zůstávají platné. | AC02, AC06 |
| Windows separator, case-only rename, symlink/escape | Jednoznačná normalizace nebo fail-closed bez zápisu. | AC02, AC05 |
| Dvě repo se stejným FQN | Oddělené identity; cross-repo pouze přes doložený mapping. | AC02, AC04 |
| Odebrání jedné OR podpory / členu AND skupiny | OR přežije platnou alternativou; neúplná AND skupina nepodporuje hranu. | AC03 |
| Změna DTO required/nullability / Kafka kontraktu | Doložená hranice dopadu a invalidace přes přesný contract/release binding. | AC09 |
| Nový Flyway skript / změna targetu | Aktualizace migration-derived schema a dependentů; žádná implicitní DB migrace. | AC09 |
| Změna Spring profilu, security activation, tsconfig, classpath | Žádné znovupoužití neplatného kontextu/ochrany. | AC04, AC07 |
| Cizí uživatel / cizí tenant / neplatný vstup | Explicitní negativní testy s ručně stanoveným očekáváním; statický guard není runtime PASS. | AC07, AC13 |
| TS-only validace, stejná vlastní anotace, custom dynamický guard | SERVER protection není vymyšlena; coverage gap. | AC07 |
| Přidání 500 testů a 500 sdílených enum referencí | Nesmí vytěsnit povinný produkční target/safeguards; scope oddělený. | AC06, AC08 |
| Cyklus, max depth/edges, token budget | Ukončení, determinismus, frontier a přiznané truncation. | AC08, AC09 |
| Test PASS → změna kódu nebo testu při stejném HEAD | Historický PASS, current verification STALE. | AC10, AC11 |
| PASS → nesouvisející změna | Konzervativní STALE, dokud není dokázána úplná relevance hranice. | AC10 |
| SKIP/toolchain missing/agent text „testy prošly“ | Nesplní povinné ověření. | AC10, AC11 |
| Cache corruption / crash / concurrent writer | Poslední validní generace zachována; explicitní miss/conflict. | AC05 |
| Opakované stejné apply | Stejný current graph a support, bez dalších věcných změn. | AC03, AC06 |

## 8. Doporučené pořadí a kontrolní body

1. **Nejdřív správnost:** S01 → S02 → S03 → S04 → S05 → S06. Milník: fixture prokáže parity a zachování příchozích hran; teprve pak optimalizovat počet extrakcí.
2. **Kontext:** S07 → S08 → S09, s uvedenými společnými závislostmi. Milník: ručně ověřitelné cesty a žádné tiché vynechání ochrany.
3. **Doklady dokončení:** po T046 S10 → S11. Milník: staré PASS nemůže splnit current gate.
4. **Integrace:** S12 → S13. Celé T003/T004 nejsou plošným blockerem; vyžadují se konkrétní upstream kontrakty popsané u kroků.

Pokud je T046 stále rozpracované, lze dokončit první dvě větve práce a připravit adapter kontrakt pro S10; nevytvářet druhý journal. Stacked PR je možný pouze s přesným base/dependency SHA a následným retarget/retest.

## 9. Ověření a metriky

Implementační PR spustí nejmenší relevantní testy a potom projektovou sadu podle platných pravidel:

```bash
PYTHONPATH=src python3 -m pytest -q
git diff --check
```

Před spuštěním ověř skutečný test layout a toolchain. Pro compiler změnu musí být skutečný Kotlin/JVM/TS worker test, ne pouze mock JSON. Není-li toolchain dostupný, zaznamenej SKIP/BLOCKED, žádné PASS. Runtime negativní Spring testy a TS typecheck vyžadují explicitní spuštění; read-only commands je nesmějí spouštět.

| Metrika | Způsob výpočtu / release pravidlo |
|---|---|
| Parity | Počet rozdílů canonical full vs incremental; pro podporovanou matici 0. |
| Integrity | Duplicate logical declarations v témže realm, dangling refs, neplatné support groups; 0. |
| Golden recall | Očekávané doložené vztahy/cíle nalezené proti ručnímu oracle; 100 % pro vymezenou fixture. |
| Over-invalidation | Počet znovu zpracovaných neovlivněných jednotek; vykázat, první verze smí bezpečný širší scope. |
| Selectivity | Počet parser/worker/LLM jednotek a cache hits; nezaměňovat parse souboru za compiler module rebuild. |
| Context | Recall/precision dotčených míst a safeguards podle hloubky, explicitní omissions, token budget. |
| Verification | Kolik stale/declared výsledků bylo správně odmítnuto; všechny negativní acceptance případy. |
| Čas/náklady | Warm/cold wall time, peak memory, skutečné tokeny; API cost jen se známou cenou a počtem, jinak NOT_MEASURED. |

GH Actions není samostatná povinná podmínka merge dle uživatelské revize AGENTS z 2026-11-03. Neprovedené CI se uvede NOT_RUN; konkrétní test failure se musí vyřešit. Ostatní povinné acceptance, lokální toolchain, review a mergeability se nevynechávají. Tento implementační agent PR sám nemerguje.

## 10. Migrace, rollout a rollback

1. Nejprve aditivní logical keys/readery. Zachovej původní runtime IDs; legacy logical mapping může být UNKNOWN.
2. Nový cache/index formát má verzi. Nekompatibilní cache se zahodí jako odvoditelná cache; user semantic data, review historie a journal se automaticky nemažou.
3. Migrace vytváří novou generaci vedle staré; validace před publish. Při ambiguity vrací report a explicitní reindex požadavek, ne domnělý alias.
4. Výchozí rollout incremental: shadow comparison na fixtures, potom opt-in na větším corpus. Při mismatch publikaci kandidáta odmítni; nabídni explicitní full rebuild. Compiler/build se ani při fallbacku nespouští implicitně.
5. Safeguards/traversal: nejprve report/packet feature flag. Dokud subset není ověřen, nevydávej UNKNOWN za „bezpečné“ a nepřepisuj uživatelské procesy.
6. Verification gate je oddělená policy; v1 workflow zůstává čitelné a neověřené. Lokální approvals z T046 se nezapínají automaticky.
7. Rollback přepne na kompatibilní validní generaci a reader. Novější evidence formát se destruktivně nepřevádí na starší. Release notes uvedou minimální reader verzi.

## 11. Definition of Done a instrukce pro implementačního agenta

Před kódem čti AGENTS, copilot instructions, registr, konkrétní upstream zadání; proveď read-only architektonickou rekognoskaci. Použij existující task/memory workflow v checkoutu. Ověř aktuální main i otevřené PR, zapiš dependency SHA. Žádné spuštění subagentů ani volba modelu nejsou tímto dokumentačním předáním automaticky provedeny.

Každý krok je hotový pouze když:

- má konkrétní implementaci, podporovaný subset a testy vlastního AC, včetně alespoň jednoho neplatného/ambiguous případu;
- změna veřejného chování současně upraví relevantní README/capability/CLI a acceptance stav;
- zůstává nulová mutace při vadném vstupu, žádné implicitní build/test/model/DB volání a žádné povýšení důkazu;
- PR body uvádí `Task/Step/AC → test → příkaz → skutečný výsledek → baseline`, blokery a zbývající limity;
- přidá český `docs/changes/<max+1>_<lowerCamelCase>.md` po nové kontrole čísel main/open PRs; číslo change note není Task ID;
- semantic patch přidá jen při doložené změně pro aktuální packet; generovaný graf obnoví příkazem po strukturální implementaci. Pokud není co doložit, nic nevymýšlí;
- větev je pushnutá a existuje samostatný reviewovatelný PR. PR se bez oprávněného merge workflow nemerguje.

Celé T047 je dodáno teprve po splnění AC01–AC13, publikaci benchmark výsledků a explicitním seznamu nepodporovaných jazykových/framework variant. Návrh v tomto souboru není důkaz jejich splnění.
