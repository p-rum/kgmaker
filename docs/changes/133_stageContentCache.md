# 133 — Obsahová cache explicitních inspekčních stupňů

Task `T003-S10-W01`, kroky 1–5, acceptance `T003-S10-W01-AC01–04`, nadřazené
`T003-AC10`. Datum 2026-11-15. Výchozí SHA
`9c86d29fc267014e2bee4b197c7692f17a1cda93`. Dodání `IN_PROGRESS`, ověření
`PARTIAL`; tento dokument netvrdí dokončení celého S10 ani T003.

## Krok 1 — source audit a nahrazení nevyhovujícího prototypu (Step 1, AC01–04)

Přečteny AGENTS, copilot, registry, specifikace, profil, kgmaker-context a skutečný
`inspection.context/inspect_jvm/inspect_frontend`, `graph_provider`, `store`,
`model`, `view_cache` a relevantní testy. `status` hlásil zastaralý lokální index
po předchozím necommitnutém prototypu; query/recall byly pouze navigace, všechny
závěry ověřeny ve zdroji. Tento starý index se nevydává za pre-change baseline.

Všech sedm závislostí prošlo `git merge-base --is-ancestor <SHA> 9c86d29...`:

| Závislost | Ověřený ancestor |
|---|---|
| S03-W04 | `3686eac6dea34441bfcff4df382753dd34d1ced7` |
| S04-W01 | `eff0d3d5d7620b017fe42a65a54f672af8068667` |
| S05-W03 | `8b1eeceb28b71c122c2d48bf179e08cefa79c43c` |
| S06-W04 | `9f6605db0258d1b27bf233e25c7737bf0b675f5b` |
| S07-W07 | `5ffe09952930a5a3e7a5d7b88a08560b7775ee9d` |
| S08-W02 | `5430388a282f19f6c9637319c12a1731ae6d0674` |
| S09-W05 | `9c86d29fc267014e2bee4b197c7692f17a1cda93` |

Realm selection, explicit remote mapping a TS input closure/replay byly ověřeny
ve zdroji a jejich konkrétních testech; ancestry nepovyšuje historický PARTIAL.
Původní nepublikovaný prototyp samostatné cache a workspace key nesplňoval W01:
nesnižoval skutečné worker/extraction volání a nahrazoval worker identity hashem
indexu. Byl archivován mimo checkout a pouze jeho vlastní změny obnoveny z HEAD.
Workspace a jeho existující cache se tímto PR nemění.

Orchestrátor schválil konkrétní návrh před novým kódem: tři stupně explicitní
inspekce, embedded metadata ve stávajícím grafu a jedna autoritativní graph commit
hranice. Workflow list/check PASS, runtime task
`497feaa5c06110d5d3f3b82095b03a18c5a9b47f2cd5ccc27cdbec4b7bdfec13`
má skutečný analysis/plan artifact; nejde o přepis staré historie.

## Krok 2 — cache skutečných stupňů a kompatibilita (Steps 2–3, AC01–03)

Baseline `9c86d29...`. Soubory `extraction_cache.py`, `inspection.py`, `model.py`,
`graph_provider.py`, `tests/test_stage_content_cache.py`.
JVM má worker-analysis → compiler-graph → framework-graph; TS má první dva,
protože jeho UI/flow projekce je součást compiler graph. Explicitní handshake
běží dál, TS project preflight také. Warm hit přeskočí skutečné analyze i graph/
framework funkce. Parser SOURCE_ONLY, offline hook a workspace nic nespouštějí.

Klíč váže skutečný root, celý captured context (repo/module/source-set/variant,
scope, sources/JPA XML/TS closure, config/build/options/manifest, worker metadata
+ distribution, classpath/bytecode, rule versions), launcher/JDK platform bytes,
extractor source bytes, stage a konkrétní upstream payload/base graph hash.
Z normalizovaného graph vstupu se vynechává jen cache a generation timestamp.
Unknown launch/legacy closure zůstává BYPASS. Stage payload není autorita:
validuje se exact selected worker/context, upstream project/coverage/status/
diagnostics a absence cizího scope/runtime factů. Poškozená cache není důkaz.

Versioned `extraction_cache` je interní aditivní metadata existujícího graph
indexu. Staré v1/v2/v3 zůstávají čitelné. Veřejné `to_dict()` a scoped graph views
cache nevypisují; store používá výslovné `include_cache=True`. Nevzniká druhý
katalog/journal. Payload nemá rekurzivní cache, IDs/context/evidence se nemění.
Limit 24 entries /16 MiB vede k BYPASS nebo odložení starších cache entries,
nikoli ztrátě validních facts. Ostatní eligible contexts se zachovávají providerem.

První běh před kódem:
`PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_stage_content_cache.py`
**6 FAIL /9 PASS**. RED doložil chybějící warm reuse, cache-model kompatibilitu
a publication error; jeden case ukázal existující odmítnutí stale jiného rule
selectoru. Rule invalidace se proto ověřuje také přes public `publish=False`,
bez oslabení existujícího provider merge guardu.

## Krok 3 — poslední validní graph/cache generace (Step 3, AC01/03)

Baseline `9c86d29...`; `store.py`, inspection final guards a cílené failure testy.
Původní store zapisoval index před renderem obou generated souborů. Nově se nejdřív
validují/serializují všechny tři payloady a připraví temp soubory. JSON obsahující
facts+cache je poslední atomický replace. Každá fáze kontroluje pinned inputy,
launcher/worker inventory a bezpečné cíle. Obvyklá výjimka obnoví jen vlastní dosud
nezměněné generated soubory a uklidí vlastní prázdné adresáře. Souběžně změněný
obsah se nepřepisuje. `publish=False`, strict PARTIAL, invalid/stale/cancel/timeout
nepublikují nové cache ani graph metadata.

Toto je single-writer exception safety, nikoli crash recovery, distribuovaná
transakce či souběžný cache writer kontrakt W06. Zdrojová změna uživatele se
nevrací, pouze nepřepíše poslední store generaci. Příklad: pozdní změna Java
zdroje během renderu vrací STALE a všechny předchozí `.kgmaker` bytes zůstanou.

## Krok 4 — průběžné cílené ověření a skutečné workery (Step 4, AC01–04)

Baseline `9c86d29...`, vlastní pracovní diff. Po prvním guard zapojení bylo
**11 FAIL /4 PASS** kvůli příliš přísnému porovnání vstupního coverage s odvozeným
worker coverage; opravena konkrétní upstream vazba. Pak **14 PASS /1 FAIL**
(existující stale rule selector výše), následně **44 PASS**, **50 PASS** a
**54 PASS** v oddělených unit/provider checkpointech. Nejde o jednu sadu nad
posledním HEAD. Root audit reprodukoval malformed cache context s přepočteným
hashem; strict bounded key shape a public provider negativy mezeru uzavřely.
Dále byly přidány validátory vazby cached graph contextu na response a public
scope-output ochrana. Tyto opravy nejsou vydávány za novou runtime evidenci.

Actual fixture používá prepared JDK21/Javac+K1/K2 a TS5.7.3, bez worker buildu
nebo package installation. JVM JAR SHA-256
`651468ee0743057ead245e57c2d36cc1b20633655853079a25f33d3bc05cc3fb` je pouze čten.
První actual checkpoint **3 PASS /0 SKIP, 25.57 s**: Java+Kotlin, warm callcounts,
reálně změněné `.class` dependency a TS compiler config. Pozdější společný běh:

```bash
JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH JAVA_TOOL_OPTIONS=-XX:-UsePerfData KGMAKER_REQUIRE_WORKERS=1 PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_stage_content_cache.py tests/test_stage_content_cache_actual.py tests/test_graph_provider.py tests/test_inspection_contract.py tests/test_build_aware.py --tb=short
```

**62 PASS /0 SKIP, 35.22 s**; log `/tmp/kgmaker-w01-current-tests.log`.
JAVA_TOOL_OPTIONS je test-only potlačení host perfdata warningu, nikoli uvolnění
JSON protocolu. Další actual worker-byte/rule a late-closure negativy se ověřují
v samostatném aktuálním checkpointu níže. Full suite/GH CI/runtime application/
live DB jsou NOT_RUN. Pozitivní data availability se netvrdí.

## Dokumentační plochy a zbývající práce (Step 5, AC04)

README, `docs/compiler-inspection.md`, `docs/stage-content-cache.md`, progress a
acceptance odkazují na tuto změnu. CLI zachovává argumenty, aditivně vrací `cache`
se stage HIT/MISS/BYPASS a důvodem. Registry bez dopadu: identity/revision/deps
beze změny. Installed instructions/templates bez dopadu: jejich chování se nemění.
Zbývá aktuální targeted regression, integrace nového main, sémantický preservation/
scan a samostatný PR s nezávislým review. W02–W06, selective per-file extraction,
reverse dependency invalidace a crash/concurrent writer garance jsou mimo W01.

## Krok 5 — rozšířená current acceptance před integrací (Steps 3–5, AC01–04)

Baseline `9c86d29...`, vlastní pracovní diff. Doplněny actual worker-byte/rule
mutace výhradně v lokální kopii JAR, count cap (facts všech variant zůstávají),
late source/worker inventory abort a bounded metadata traversal před kopírováním.
Veřejné malformed cache key/provenance negativy a scoped output ochrana jsou
součástí stejné cílené matice. Aktuální rozšířený příkaz:

```bash
JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH JAVA_TOOL_OPTIONS=-XX:-UsePerfData KGMAKER_REQUIRE_WORKERS=1 PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_stage_content_cache.py tests/test_stage_content_cache_actual.py tests/test_graph_provider.py tests/test_inspection_contract.py tests/test_build_aware.py tests/test_tsconfig_freshness.py --tb=short
```

**101 PASS /0 SKIP, 122.69 s**, log `/tmp/kgmaker-w01-expanded-tests.log`.
Následná malá bounded-traversal kontrola (počty/velikost před rozšířením fronty)
se ověří ještě v integračním běhu; předchozí101 se nevydává za tento pozdější SHA.
`git diff --check` PASS. Žádný build sdíleného workeru, instalace dependencies,
full suite nebo aplikace; tyto kontroly NOT_RUN. Připravený actual JAR je stále
`651468ee...`. V1/v2/v3 a veřejné model contracts zachovány; payloadmetadata se
zobrazí pouze výslovnému store serializeru, nikoli public graph/flow/feature.

## Krok 6 — žádné fallible čtení po authoritative replace (Step 3, AC01/03)

Baseline `9c86d29fc267014e2bee4b197c7692f17a1cda93`, vlastní diff.
Závěrečný audit `store.py` našel čtení `_file_state` až po `os.replace` hlavního
indexu. Při chybě čtení by hotový commit oznámil chybu. Ownership se nyní čte
z připraveného temp souboru před replace; po commitu zbývá pouze zápis do paměti.
Regression `test_authoritative_commit_needs_no_post_replace_read` nejdřív
**1 FAIL (0.09 s)** na původní implementaci, po opravě spolu s cache/provider
soubory **57 PASS (5.68 s), 0 SKIP**:

```bash
PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_stage_content_cache.py tests/test_graph_provider.py --tb=short
```

Předchozí bounded-traversal oprava byla samostatně **56 PASS (5.66 s)** stejným
příkazem před přidáním této regrese. Kompatibilita a single-writer limit beze změny;
žádná crash/concurrency garance. Uživatelské kontrakty zůstávají dle guide výše.
Runtime implementation artifact `artifact:c0f4f8af8fcd83f23dd371fedd0dd8980dc5899ce074a681ad13dd91bf240eda`
obsahuje skutečné změny i dosud nedokončenou integraci/semantic/final gate.


## Krok 7 — ordinary integrace main (Steps 2–5, AC01–04)

Vlastní checkpoint `c60893b` integruje main
`84f94d4462437fe1228f07d0ba8f51071224952e` ordinary merge bez přepisování historie.
Fetch ze skutečného remote potvrdil toto SHA. Konflikt pouze v sousedních řádcích
progress: ponechán main MERGED stav S09-W05 a vlastní skutečný W01 checkpoint.
Zdrojové změny main T028/T029 v `business_process.py` zůstaly bez zásahu; W01
nezavádí žádné procesní změny. Sémantická vrstva obou rodičů obsahuje union
52 concepts /176 relations /328 immutable episodes; další vlastní capture
a ověření preservation budou zaznamenány samostatně. Generated views z main
se znovu vytvoří CLI po scoped update. Integrační actual gate zatím NOT_RUN.
