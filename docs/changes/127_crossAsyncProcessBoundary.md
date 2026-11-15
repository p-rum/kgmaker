# T028 — Asynchronní návaznosti procesu

Zadání: [T028](../tasks/T-028_cross-async-process-boundary.md), parent [T004](../tasks/4_addHighLevelProjectViews.md).
Výchozí skutečný main: `93c52d338ea273175b9c0ed5a7a5477ae6bf2de0` (PR105 MERGED,
parents `ec05a329fe2e51dbfe0eb47888bed037a251b8bf` a `64be66ddde69ec662476daa23a65755bed13ebb3`,
tree `811ff17d7978eba88aa808e578528a1abc67e66b`). Izolace `/tmp/kgmaker-t028`;
větev `feat/t028-cross-async-process-boundary`. Dodání **PR_OPEN**, ověření **VERIFIED_IN_SCOPE** (cílený kontrakt, nikoli celé T004).

## Krok 1 — rekognoskace a RED kontrakt (T028-S01–S04, AC01–AC05)

Baseline tohoto kroku je výše uvedený main. T012 již poskytuje přesné původní identity
producer call-site a listener symbolu i subscription; T014 poskytuje jednotlivá
explicitní release/contract memberships, ale sanitizace zahazuje pojmenovaná Kafka
identity metadata. T025 poskytuje původní call-site přímo na CFG uzlu. Návrh proto
nepotřebuje nový resolver, worker ani store. Existující T027 HTTP request/response
chování zůstává oddělené; async nemá návrat do publisheru.

Přímá rekognoskace: `interfaces.py`, `remote_interfaces.py`, `remote_mapping.py`,
`process_triggers.py`, `process_paths.py`, `process_model.py`, `business_process.py`
a veřejné testy T012/T014/T025/T027. `./kgmaker status`, `query` a `memory recall`
nenašly čitelný pre-task index; architektura byla ověřena ve zdroji. Není to compiler
ani retrospektivní memory důkaz. Workflow `existing-feature`, task
`task:4c330804f0e7c2ef59dda2118bd9f737e198ffafd12049c39f06e420d784718c`, obsahuje
architect analysis a plan; žádný review APPROVE tím nevzniká.

Veřejný kontrakt: `project_async_process_boundary(local_process, remote_interfaces,
target_processes=(), max_depth=4, max_expansions=32)` vrací existující `ProcessView`.
Join vyžaduje konkrétní původní call-site/listener identitu a odpovídající service,
context, scope a jednotlivý doložený T014 candidate. Topic match nikdy není identity
ani korelace instance. Podporované vstupy neobsahují instance-mapping kontrakt;
`instance_correlation=UNKNOWN`, `correlation_evidence_refs=[]` jsou explicitní limity.

První veřejné RED testy pro fan-out, publish, missing consumer a nulovou mutaci:

```sh
PYTHONPATH=src:tests PYTHONDONTWRITEBYTECODE=1 /tmp/kgmaker-test-venv/bin/python -B -m pytest -q -p no:cacheprovider tests/test_t028_cross_async_process_boundary.py
```

**FAIL očekávaný: 4 failed, 0.50 s**, chybělo veřejné API. Testy kontrolují dosažitelnost
cest a zachování posledního artefaktu, nejen existenci kindů. Plná sada **NOT_RUN**
podle explicitního omezení uživatele. Zbývalo dodat API, negativní matici, actual
compiler pipeline, dokumentaci a semantic maintenance.

## Krok 2 — čistá projekce a guardy (T028-S01–S04, AC01–AC05)

Baseline stále `93c52d338ea273175b9c0ed5a7a5477ae6bf2de0`; jde o navazující změny
ve stejné větvi před prvním commitem. `business_process.py` přidává potenciální
publish → channel → subscription → consumer cesty. Větve se nepropojují navzájem ani
zpět do publisheru; jeho původní normální/chybové pokračování zůstává zachováno.
Smyčka, depth/expansion limit, neznámý consumer a neověřená membership zůstávají
viditelnými boundaries. Evidence se nepovyšuje; výsledek zůstává PARTIAL.

`remote_interfaces.py` aditivně zachovává již existující T012 `origin_id`,
`subscription_id`, `subscription_logical_id`; první dvě identity musí být obsaženy
v původních `original_ids`. Nemění původní ID ani provenance. Nový persistent formát
ani migrace nevzniká. T014 aggregate AMBIGUOUS není autorita fan-out: každý candidate
se porovná s konkrétním bindingem, mappingem, endpointem, release, scope, context a
provenance; duplicitní či konfliktní release selectors neexpandují consumer.

Průběžná úzká regrese:

```sh
PYTHONPATH=src:tests PYTHONDONTWRITEBYTECODE=1 /tmp/kgmaker-test-venv/bin/python -B -m pytest -q -p no:cacheprovider tests/test_t028_cross_async_process_boundary.py tests/test_t027_cross_http_process_boundary.py tests/test_t014_bind_remote_interfaces.py
```

**PASS: 80 passed, 1.47 s** na pracovní revizi před doplněním actual fixture.
Tento výsledek je protokolová evidence, nikoli actual worker důkaz. Další výsledky,
AC mapování, uživatelská dokumentace a semantic maintenance jsou dosud nedokončené.

## Krok 3 — actual pipeline a uzavření testové matice (T028-S04, AC01–AC05)

Baseline `93c52d338ea273175b9c0ed5a7a5477ae6bf2de0`; předchozí krok v témže
pracovním diffu. Přidány skutečné Java `@Scheduled` publish a dva `@KafkaListener`
consumer procesy přes veřejné capture/projectors. První actual běh byl **FAIL: 2
failed, 27 deselected, 19.44 s**: fixture omylem zvolila druhý release stejného
endpointu. Membership guard správně odmítl dvojznačnost. Oprava fixture vybírá jiný
canonical interface ID; guard nebyl oslaben. Opakování `-k actual_t012` dalo **PASS:
2 passed, 27 deselected, 20.72 s**. Podrobná negativní matice navíc dokládá duplicitní
membership, společnou group, backwards-compatible join přes original_ids, stejné
výsledky při permutaci vstupů, nulovou mutaci a zachování coverage i při limitu.

Finální příkaz (pouze cílené moduly):

```sh
JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 KGMAKER_WORKERS_HOME=/tmp/kgmaker-pr97-reconciled/workers PYTHONPATH=src:tests PYTHONDONTWRITEBYTECODE=1 /tmp/kgmaker-test-venv/bin/python -B -m pytest -q -p no:cacheprovider tests/test_t028_cross_async_process_boundary.py tests/test_t012_catalog_kafka_interfaces.py tests/test_t014_bind_remote_interfaces.py tests/test_t025_build_local_process_path.py tests/test_t027_cross_http_process_boundary.py
```

**PASS: 242 passed / 0 SKIP, 136.07 s**. T028 vlastní 41 případů včetně dvou actual
pipeline backend konfigurací. Existující T012 skutečně zachovává K1/K2 annotation
limity a T025 ověřuje graph v1/v2/v3; T028 nepřidává jazykový resolver. JDK21 a
připravené workery byly zpřístupněny dočasnými symlinky `workers/jvm/target` a
`workers/jvm/target-k2` do `/tmp/kgmaker-pr97-reconciled/workers/jvm/`; nejde o nový
build ani instalaci. Symlinky byly po bězích odstraněny. Actual fixture běží
explicitně pouze v test setup, čisté API má zákaz I/O/subprocess/network ověřený testem.

AC01–06 mají jednotlivé testy a omezení v [acceptance inventory](../acceptance-inventory.md#t028--potential-asynchronous-process-paths).
Zbývá semantic údržba, kontrola diffu, publikace a nezávislé review. Full suite,
GH CI, Kafka delivery/runtime a data availability **NOT_RUN**. Tento cílený PASS
neprokazuje celé T004 ani libovolný produkční projekt.

## Krok 4 — dokumentace a kompatibilita (T028-S05, AC06)

Baseline stále `93c52d338ea273175b9c0ed5a7a5477ae6bf2de0`. README odkazuje skutečné
async API; `docs/process-paths.md` obsahuje přesné parametry, příklad, evidence a
limity; `docs/remote-interfaces.md` popisuje aditivní identity handoff a upravuje
historickou větu o budoucích T027/T028. Progress/acceptance oddělují delivery od
ověření; T027 metadata jsou nyní pravdivě MERGED na `93c52d33`, jeho historické testy
zůstávají zachované. Task registry/spec beze změny identity/revize/závislostí — bez
dopadu. CLI commands/installed templates beze změny — bez dopadu; Python příklad
výslovně uvádí, že T034/T038 lifecycle/export CLI není dodán. ProcessView schema a
staré graph loadery se nemění; migrace není potřeba. Instance correlation zůstává
UNKNOWN, protože podporovaný upstream vstup nenese příslušný mapping kontrakt.


## Krok 5 — souhrnný input budget a čistě Kafka metadata (T028-S03–S04, AC04–AC05)

Baseline `93c52d338ea273175b9c0ed5a7a5477ae6bf2de0` + předchozí pracovní kroky.
Závěrečná kontrola odhalila, že samostatně bounded target dokumenty potřebují také
společný limit před kopírováním. API nyní přijímá nejvýše 128 target procesů a
kontroluje jejich souhrnný structure/text budget. Příliš velká opakovaná struktura
končí řízenou chybou bez mutace. Sanitizační adice je navíc výhradně pro
`kafka_interface`; dříve ignorované stejně pojmenované HTTP extra attributes zůstávají
ignorované. Nejde o změnu HTTP kontraktu ani resolveru.

- Příkaz z kroku 3 omezený na `tests/test_t028_cross_async_process_boundary.py`:
  **PASS: 42 passed / 0 SKIP, 20.18 s**, včetně obou actual pipeline konfigurací.
- `PYTHONPATH=src:tests PYTHONDONTWRITEBYTECODE=1 /tmp/kgmaker-test-venv/bin/python -B -m pytest -q -p no:cacheprovider tests/test_t028_cross_async_process_boundary.py tests/test_t014_bind_remote_interfaces.py -k 'not actual_t012'`:
  **PASS: 66 passed, 2 deselected, 1.21 s** po Kafka-only guardu. Dva actual případy
  byly záměrně deselected, nikoli SKIP; Kafka větev guardu zůstala stejná.
- T028 má po těchto opravách 43 veřejných případů. Předchozí širší 242 PASS zůstává
  historickým výsledkem kroku 3, nejde o znovu spuštěnou širší sadu nad tímto krokem.
- `git diff --check`: PASS. Byte identity celého původního T026/T027 prefixu
  `business_process.py` vůči main: PASS. Ostatní source moduly se nemění.

Oba malé opravné kroky mají vlastní negativní testy. Full suite zůstává NOT_RUN;
bez další funkční změny se neopakuje nesouvisející celá sada.


## Krok 6 — sémantická údržba a předání (T028-S05, AC06)

Baseline `93c52d338ea273175b9c0ed5a7a5477ae6bf2de0`. Použit skill
`.agents/skills/kgmaker-semantic/SKILL.md`. `semantic update` připravil skutečný
packet; žádný token budget nebyl zadán. Patch má nulová remove pole a zachovává
všech 45 původních konceptů / 144 vztahů / 299 epizod. Reanchor 6 dotčených konceptů
a 15 vztahů byl doložen přesnými base source hashes a nezměněnými citovanými řádky;
nový T028 koncept a 3 EXTRACTED vztahy citují API, capability a actual pipeline test.
Po závěrečných guardech vznikl nový aktuální packet a reanchor se ověřil znovu.
Žádné unrelated/historické semantic údaje nebyly odstraněny.

```sh
./kgmaker semantic update --base 93c52d338ea273175b9c0ed5a7a5477ae6bf2de0 --note docs/changes/127_crossAsyncProcessBoundary.md
./kgmaker scan --no-docs
./kgmaker semantic apply
./kgmaker semantic validate
./kgmaker memory capture --base 93c52d338ea273175b9c0ed5a7a5477ae6bf2de0 --validation targeted=passed --validation semantic-preservation=passed --validation full-suite=skipped
./kgmaker memory capture --base 93c52d338ea273175b9c0ed5a7a5477ae6bf2de0 --validation targeted=passed --validation final-bounds=passed --validation full-suite=skipped
```

Apply/validate **PASS**, preservation audit **PASS**: všechna baseline concept IDs,
summary, edge kind/confidence/evidence a celé historické epizody zachovány (povoleny
jen ověřené source-line/symbol-line reanchory). Výsledek **46 konceptů / 147 vztahů /
301 epizod**. Pre-task index při začátku chyběl; oba uvedené skutečné memory capture
příkazy později uspěly nad explicitní Git baseline a reálnými postupnými diffy. Nejde
o smyšlenou pre-task recall nebo review evidence. První episode odpovídá stavu před
závěrečným bounded-input krokem; druhá zachycuje jeho skutečnou změnu. Průběžné scan
warnings před opravou stale source citations jsou historické, ne aktuální validační
PASS. Finální grafy se generují příkazem `./kgmaker scan`, nikoli ruční editací.

Před publikací byl primary main opakovaně ověřen jako `93c52d33`; otevřené PR106
ranking a historický draft4 nekolidují s rezervovaným change127 (125 BEFE, 126
ranking). Implementační agent nemerguje. Zbývá nezávislé review přesné publikované
revize; full suite a GH CI nejsou vykázány jako PASS.


Finální `./kgmaker scan`, `./kgmaker check`, `./kgmaker semantic validate` a
`git diff --check`: **PASS**. Generováno 587 souborů, 6 726 uzlů a 46 513 vztahů
včetně historických epizod; samotná semantic vrstva má výše uvedených 46/147/301.
Workflow je ve fázi `review` s uloženými architect/implementation/test artefakty;
nezávislé review APPROVE nebylo nahrazeno vlastním hodnocením. README/capability/
API příklady/progress/acceptance odpovídají aktuálnímu kontraktu. Veřejná dodávka
zůstává PR_OPEN do samostatného review/merge; implementer nemerguje.

## Krok 7 — review fix: skutečná authority endpoint/binding proofs (T028-S01–S04, AC04–AC05)

Výchozí HEAD `1732a3d7b924a7dfd60c67436622ae05db43dfff`, base
`93c52d338ea273175b9c0ed5a7a5477ae6bf2de0`. Nezávislé
[REQUEST_CHANGES](https://github.com/p-rum/kgmaker/pull/108#issuecomment-6899165580)
našlo stale endpoint proof skrytý pod UNKNOWN endpoint summary a stale binding
proof, které přesto dovolily expanzi. Původní cílená sada reviewerovi prošla
244 PASS / 0 SKIP, 134.94 s; tím nejsou nálezy vyřešeny. Vlastní opakování všech
čtyř reviewer reprodukcí na přesném výchozím HEAD: **FAIL očekávaný, 4 failed,
0.61 s**. Tři reprodukce patří tomuto kroku; čtvrtá je řešena v kroku 8.

`business_process.py` nyní kontroluje přímo referenced endpoint proofs (stale,
contradicting, foreign scope a nedostatečné evidence kinds), nikoli jen node flag.
Candidate a `original_evidence_refs` musí přesně odpovídat endpoint refs. Binding
a edge musí nést původní T014 SOURCE_ONLY/UNKNOWN deklarace se správnými scope,
contexts, mapping IDs a společným capture ID. Vyšší freshness/kind se nedovozuje
ze změny summary flagu. Neplatná authority zachová subscription boundary a blokuje
consumer expansion. Původní lokální success/exception cesty se nemění.

Rejected i přijaté raw proofs se neztrácejí. Pokud původní scope/contexts již
vyhovují ProcessView, zůstane record beze změny. Jinak nový odvozený provenance
odkaz nese `projection_role=REMOTE_PROOF_ENVELOPE`,
`authority=PROVENANCE_REFERENCE_ONLY`, `original_id` a celý nezměněný
`original_provenance`. Top-level process scope/context popisuje pouze umístění
odkazu, ne původní authority. Obálka má evidence_kind/polarity UNKNOWN a freshness
STALE u stale originálu, jinak UNKNOWN; nikdy nepředstírá nový CURRENT compiler
proof. Guard čte výhradně raw upstream record. Diagnostic
`ASYNC_REMOTE_PROOF_REFERENCE_ONLY` zachovává původní scope/context/freshness gap.
Boundary polarity buckets i druh evidence nyní zachovávají konkrétní odkazované
records; stale boundary se neskrývá pod silnějším summary.

Kompatibilita: canonical T012 framework proofs mohou mít UNKNOWN freshness,
chybějící scope a virtuální Kafka contexts. Zůstávají použitelné jako původní
omezená T014 evidence, nikoli přepsané na CURRENT; původní obsah je dohledatelný.
Není nový resolver, ProcessView schema ani worker protokol. Dotčené soubory:
`business_process.py`, veřejné `test_t028_cross_async_process_boundary.py` a níže
uvedené dokumentační plochy. Veřejné negativy v platných ViewDocuments pokrývají
stale/contradicting/foreign endpoint i binding proof, wrong mapping/capture/kind,
missing declaration, exact raw preservation a nulovou mutaci. První vlastní RED
příkaz s `-k 'referenced_endpoint or binding_declaration_authority'`:
**13 failed, 43 deselected, 0.97 s**. Doplněná positive/negative dvojice potvrzuje,
že reference-only obálka nezavře PARTIAL gap a neobejde stale raw authority.

## Krok 8 — review fix: aliasy release selectorů napříč bindingy (T028-S01–S04, AC01/AC03/AC05)

Výchozí HEAD `1732a3d7b924a7dfd60c67436622ae05db43dfff` plus krok 7 v témže
pracovním diffu. Dvě source release IDs téhož producer endpointu a dvě target
release IDs téhož consumer endpointu vytvořily dva samostatné RESOLVED T014
bindingy. Původní guard kontroloval pouze jeden candidate array, proto importoval
stejný consumer dvakrát. Nový index kontroluje membership napříč celým dodaným
remote view podle canonical endpoint/service/context/group a channel identity.
Release ID je selector, ne další consumer. Konfliktní selectors zůstávají všechny
viditelné v `conflicting_selectors`, s boundary/diagnostic
`ASYNC_MEMBERSHIP_SELECTOR_CONFLICT`, bez importované consumer cesty.

Odlišné canonical endpoints, contexts a groups nejsou sloučeny; positive test
používá dva bindingy a explicitně kompatibilní v2 endpoint, zachová oba consumers
a dokládá absenci A-before-B. Nejde o odhad verze podle jména; používá původní
content-bound interface identity a T014 declaration contract. Původní test duplicity
v jednom bindingu nyní očekává stejný explicitní conflict důvod. Nový RED:
`-k 'release_aliases or distinct_versioned or unknown_scopeless'` → **1 failed,
2 passed, 56 deselected, 0.64 s**.

Po opravách obou nálezů:

```sh
PYTHONPATH=src:tests PYTHONDONTWRITEBYTECODE=1 /tmp/kgmaker-test-venv/bin/python -B -m pytest -q -p no:cacheprovider tests/test_t028_cross_async_process_boundary.py tests/test_t014_bind_remote_interfaces.py tests/test_t027_cross_http_process_boundary.py /tmp/kgmaker-review108-repros.py -k 'not actual_t012'
```

**PASS: 115 passed, 2 deselected, 1.95 s**, včetně všech 4 původních reviewer
reprodukcí. Jde o průběžný protokolový důkaz před závěrečnou actual regresí a
semantic maintenance; full suite NOT_RUN. README, process-paths API/capability
včetně ukázky `remote_evidence_refs`, remote-interfaces, progress a acceptance
jsou aktualizovány ve stejném review fixu. Registry/spec/installed CLI templates
bez dopadu: identity, schema a CLI parametry se nemění. Zbývající práce tohoto
kroku je finální cílený běh, source-backed semantic reanchor, commit/push a nové
nezávislé review přesného HEAD; žádný původní APPROVE se nepředpokládá.


Závěrečná cílená regrese kroků 7–8 (funkční kód se po tomto běhu neměnil):

```sh
JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 KGMAKER_WORKERS_HOME=/tmp/kgmaker-pr97-reconciled/workers PYTHONPATH=src:tests PYTHONDONTWRITEBYTECODE=1 /tmp/kgmaker-test-venv/bin/python -B -m pytest -q -p no:cacheprovider tests/test_t028_cross_async_process_boundary.py tests/test_t012_catalog_kafka_interfaces.py tests/test_t014_bind_remote_interfaces.py tests/test_t025_build_local_process_path.py tests/test_t027_cross_http_process_boundary.py /tmp/kgmaker-review108-repros.py
```

**PASS: 264 passed / 0 SKIP, 138.32 s**: 260 veřejných případů (T028 nyní 59)
a všechny 4 nezávislé reviewer reprodukce. Skutečný JDK21/Javac/K1/K2; actual
T012→T014→T025→T028 pipeline obsahuje původní UNKNOWN/scopeless/virtuální Kafka
proofs a prochází bez jejich přepisování na compiler authority. Dočasné symlinky
`workers/jvm/target` a `target-k2` do připraveného toolchainu byly opět odstraněny.
V protokolové fixture byly pro contradictory proof upraveny i jeho odpovídající
polarity buckets, aby vstup zůstal platným ViewDocument; produkční validátor nebyl
oslaben. `git diff --check` a byte identity původního T026/T027 prefixu vůči
`1732a3d`: PASS. Plná suite a nový aplikační/Kafka runtime **NOT_RUN**.

Předchozí CI run `43745930952` nad HEAD `1732a3d` skončil failure se sedmi
ověřenými prázdnými step seznamy (5 failure, 2 cancelled); žádné CI testy neběžely.
To je historický NOT_RUN testový důkaz, nikoli code/test PASS nebo náhrada lokálního
běhu. Nová CI metadata se uvádějí v PR body po publikaci nového HEAD. Merge ani
APPROVE nejsou součástí tohoto implementačního kroku.

## Krok 9 — review-fix semantic maintenance a předání (T028-S05, AC06)

Výchozí SHA `1732a3d7b924a7dfd60c67436622ae05db43dfff`, nikoli původní main.
Aktuální pre-fix index existoval; recon prošel přes `status`, query a přímý zdroj.
Semantic update/apply zachovává všech **46 konceptů / 147 vztahů / 301 epizod**
reviewované baseline. Patch pouze obnovuje aktuální zdrojové citations 7 dotčených
konceptů a 18 vazeb; remove seznamy jsou prázdné a nový koncept/vztah se nevymýšlí.
Reanchor porovnává přesné baseline SHA-256 zdrojů a nezměněné citované řádky.
Po pozdější dokumentační úpravě apply správně odmítl zastaralý packet beze zápisu
(`analysis context changed`); nový `semantic update` a nový patch tento packet
nahradily. Nešlo o přepsání update_id bez nového vyhodnocení.

```sh
./kgmaker semantic update --base 1732a3d7b924a7dfd60c67436622ae05db43dfff --note docs/changes/127_crossAsyncProcessBoundary.md
./kgmaker scan --no-docs
./kgmaker semantic apply
./kgmaker semantic validate
./kgmaker memory capture --base 1732a3d7b924a7dfd60c67436622ae05db43dfff --validation targeted=passed --validation review-repros=passed --validation full-suite=skipped
```

Apply/validate a preservation audit **PASS**. Nová skutečně zachycená review-fix
epizoda dává **46 konceptů / 147 vztahů / 302 epizod**; všechna původní IDs,
summary, kind/confidence/evidence a celé historické epizody zachovány. Grafy se
znovu generují příkazem, ne ručním přepisem. README/API/capability/CLI příklady,
status a acceptance odpovídají opravě; staré testové výsledky jsou výslovně
historické a current row obsahuje 264 PASS. Workflow zaznamenává opravnou iteraci,
nezávislé REQUEST_CHANGES se nepřepisuje vlastní deklarací APPROVE. Před push
ověřen main `93c52d33` a remote branch stále `1732a3d`; není potřeba přebírat
nesloučené sousední PR106/107. Následuje normální commit/push a review nového HEAD.

Finální `./kgmaker scan`, `./kgmaker check`, `./kgmaker semantic validate`,
review-baseline preservation audit a `git diff --check`: **PASS**. Aktuální
vygenerovaný graf má 587 souborů, 6 742 uzlů a 46 843 vztahů (včetně epizod).
Task workflow je v opravné iteraci 1 ve fázi review; uloženy skutečné implementační
a testové artefakty, žádné vlastní APPROVE. Cílené testy se po dokumentační údržbě
zbytečně neopakovaly; funkční source/test obsah zůstal od finálního běhu shodný.
