# T048 — Předávací plán dokončení KGMAKER a dokumentační disciplína

- Task ID: **T048**
- Revision: **1**
- Datum: **2026-11-06**
- Stav: **SPECIFICATION** — plán realizace, nikoli potvrzení dokončení funkcí.
- Baseline: `main 250e7c16250a97b9f8df5256b9894c8119dc64d9`, po merge T020 v PR #87.
- Depends on: existující T001–T047, zejména [T003](3_finishProductionAnalysis.md), [T004](4_addHighLevelProjectViews.md), [T047](47_addReliableIncrementalContext.md) a otevřený balík T046.
- Supersedes: žádné funkční zadání ani acceptance. Tento dokument určuje předání, pořadí a integrační kontroly. Původní Task ID, soubory a větve se zachovávají.
- Větev tohoto předání: `docs/t048-completion-handoff`.
- Autorita: [AGENTS](../../AGENTS.md), [registr](README.md), [stav](../production-analysis-progress.md), [acceptance](../acceptance-inventory.md).

## 1. Úkol předanému agentovi

Pokračuj po malých samostatně reviewovatelných krocích až k dokončení deklarovaného
statického/analytického rozsahu KGMAKER. Nejprve aktualizuj baseline a důkazy stavu,
potom integruj existující práci a implementuj nedodané kontrakty v níže uvedeném
pořadí. Každý krok musí mít testy svého chování, pravdivou dokumentaci a vlastní PR
podle původního zadání. Neslučuj celý program do jednoho implementačního PR.

T048 nepřidává druhý graf, druhou cache, druhý journal ani nová funkční Task ID.
Neimplementuj již dodané úkoly znovu jen proto, že soubor stále říká SPECIFICATION.
Nezmenšuj původní acceptance tak, aby odpovídala pohodlnějšímu subsetu. Subset označ
PARTIAL a přesně eviduj zbývající požadavky.

Výsledkem je doložitelná cesta od požadavku přes aktuální kód/kontrakty až k plánu
změn v Kotlin/Spring Boot, PostgreSQL/Flyway, Kafka/HTTP a TypeScript repozitářích,
s dohledáním zdrojů, konzervativní nejistotou a použitelnými reporty. Statický důkaz
není runtime dostupnost ani důkaz bezpečnosti či správnosti business pravidel.

Non-goals tohoto předání: implementovat všechny kroky v dokumentačním PR,
automaticky mergeovat, spouštět další agenty, měnit modely, nasazovat aplikace,
připojovat bankovní DB, aktivovat live Confluence či runtime sběr.

## 2. Zjištěná baseline a omezení auditu

Podklady byly čteny přes GitHub: tree, zadání, otevřené PR, pravidla, stavová matice,
acceptance a relevantní zdroje/testy. Obsah velkého `.kgmaker/GRAPH.md` konektor
nevrátil; NOTES obsahuje obecný úvod. Graf nebyl použit jako autorita a nebyl ručně
upravován. Nebyl proveden plný běh KGMAKER ani compiler acceptance tohoto programu.

| Rozsah | Dodání v této baseline | Co se nesmí vyvodit |
|---|---|---|
| T003: 60 atomických balíčků | 37 má přiřazenou sloučenou práci; 23 bez sloučené dodávky | 37 není počet plně ověřených produkčních schopností. S12-W01 dodává konfiguraci; live zůstává odložené. |
| T004: T005–T044 | Dodané T005–T020, T023–T026, T030–T033; 24 ze 40 | T021–T022, T027–T029, T034–T044 zbývají. Model/katalog není celý procesní CLI/report. |
| T045 | Profil a pravidla review agenta jsou v main | Existence profilu neprokazuje nezávislé review konkrétního SHA. |
| T046 | Šest otevřených navazujících PR | Není v main; historické testy balíku nejsou ověření dnešního main. |
| T047 | Zadání s 13 kroky v main | Nebyla dodána implementace těchto 13 kroků jako balíku; část práce vlastní T003/T037/T038/T046. |

Součet původních T003/T004 nyní činí **61 úkolů se sloučenou prací a 39 bez
sloučené dodávky**. Navíc zůstává live Confluence a omezení již dodaných subsetů.
Nejde o procento pracnosti, úplnou acceptance ani počet zbývajících pracovních dní.
T001/T002 se nepřičítají znovu: T003 jejich dokončení koordinuje.

Staré statusy v README a historických částech matice jsou místy rozporné.
Například architecture CLI již existuje v `src/kgmaker/architecture_cli.py`,
T020 přidává interfaces-only Markdown přes `architecture_render.py`.
Topology/explain zůstávají JSON-only. Existující `graph view` a `flow render`
nejsou automaticky dokončením T021/T035.

## 3. První krok: T048-S01 — sjednotit stav a vytvořit pracovní seznam

- Větev: `docs/t048-reconcile-delivery-status`; samostatný PR.
- Před kódem přečti AGENTS, copilot instructions, aktuální zadání a existující
  architektonické instrukce. Proveď read-only rekognoskaci; bez dostupného grafu
  použij zdroje a testy. Nespouštěj worker jen pro získání statusu.
- Zaznamenej nové main SHA, head/base každého otevřeného PR a změny od této baseline.
  Zkontroluj i větve bez PR. Předpokládané chybějící části porovnej se symboly/testy,
  nikoli jen s názvem PR.
- Pro každý z 60 T003 balíčků, 40 T004 úkolů, 6 T046 etap a 13 T047 kroků udržuj
  v existující stavové matici řádek s delivery status, verification status,
  evidence SHA, zdroji/testy, PR, omezením a dalším krokem.
  T047 řádky mají explicitní upstream owner, aby se práce nepočítala dvakrát.
- Stav dokumentu SPECIFICATION ponech odděleně. Staré běhy zachovej jako historii,
  aktuální souhrn umísti před ně. Výsledky nesčítej přes různé baseline jako nový full.
- Oprav rozpory v README, capability dokumentech, CLI příkladech a aktuálním
  acceptance souhrnu. Při změně pořadí dependencies neměň požadavky bez explicitní
  revize původního zadání.
- U PR #4 porovnej patch s main. Zapiš konkrétní zbytkový rozdíl nebo úplné pokrytí
  novějšími změnami. Historický draft nemerguj naslepo; případné uzavření odůvodni
  samostatně a postupuj podle oprávnění.

**T048-AC01:** každý uvedený atomický úkol má právě jeden současný stav a explicitní
důkaz či NOT_RUN; součty odpovídají řádkům, duplicity T047 jsou označené, známé
aktuální dokumentační rozpory jsou odstraněné. Ověř odkazy, skutečné CLI argumenty
a zachování historických záznamů; pro čistou úpravu dokumentace nevytvářej textové
unit testy.

## 4. T048-S02 — integrovat již napsané T046

Pořadí je pevné: [#41 S01](https://github.com/p-rum/kgmaker/pull/41) →
[#42 S02](https://github.com/p-rum/kgmaker/pull/42) →
[#43 S03](https://github.com/p-rum/kgmaker/pull/43) →
[#44 S04](https://github.com/p-rum/kgmaker/pull/44) →
[#45 S05](https://github.com/p-rum/kgmaker/pull/45) →
[#40 S06](https://github.com/p-rum/kgmaker/pull/40).

1. Přečti T046 revision 2 z první větve a konkrétní diff každého inkrementu.
   Zachovej existující větve; nevytvářej šest duplicitních implementací.
2. Ověř mergeability proti aktuálnímu parentu. První PR bylo v předchozím auditu
   neslučitelné; stav je nutné znovu načíst. Vyřeš konflikty podle současných
   workflow/provider kontraktů, ne hromadným ours/theirs.
3. Zachovej v1/v2 reference, content bindings, lokální journal a runtime IDs.
   Default-off schvalování nesmí být automaticky aktivováno. Lokální deklarace
   identity není autentizace, vygenerovaný test zůstává NOT_RUN, data SYNTHETIC.
4. Po přijetí předchůdce retargetuj následníka, ověř base/head a zopakuj relevantní
   integrační kontroly. Přidání schválení či jeho odvolání nesmí obejít save_task.
5. Po S06 projdi skutečný scénář template → testgen prepare/validate/apply/report/
   export → explicitní běh exportovaného testu → trace. Test musí selhat po cílené
   změně ověřovaného chování. Ověř stale obsah, dirty sources, invalid refs,
   konflikt journalu, path traversal a nulovou mutaci při odmítnutí.
6. Aktualizuj registr T046 a příslušné návody současně s dodávkou. Zachovej T047/T048
   při konfliktech registru.

**T048-AC02:** šest etap má oddělené výsledky nad skutečnými integračními SHA,
kompatibilní historii a žádnou ztrátu novějších funkcí main. Nezávislé review a
merge provádí jen oprávněný workflow; jinak předej ready PR a pokračuj nezávislou
prací. Nepředstírej, že historických 198 testů ověřilo současný repozitář.

## 5. T048-S03 — dokončit důkazní a datové základy

Každý níže uvedený původní work package má vlastní zadání, větev, acceptance a PR
(odkazy a moduly jsou v příloze). Pořadí respektuje jejich dependency kontrakty:

1. T003-S05-W04: Spring proxy/async semantika v podporované matici; self-invocation
   nesmí vytvořit falešný proxy execution, runtime scheduling zůstává oddělené.
2. T003-S06-W05 → W06 → W07: JPQL/HQL gramatika, kontejnery named queries,
   Criteria/Specification/QueryDSL. Symbolové vlastníky a datasource realms
   nepřepisuj shodou názvů. Dynamic či neznámé konstrukce mají explicitní boundary.
3. T003-S07-W03: field/mapping flow nad již dodanými argument/return bindings.
   Ověř přepis hodnoty, aliasing, větev a nejednoznačný mapping; žádná domnělá hrana.
4. T003-S07-W08 → W09: evidence ranking a sjednocené pohledy. Ranking nesmí
   povýšit syntax na compiler/runtime důkaz. Přidání mnoha testů/dokumentů či
   enum referencí nesmí změnit produkční execution význam.
5. T003-S08-W05: BE–FE value flow přes explicitní verzi kontraktu/release a
   existující HTTP binding. Stejné DTO/field jméno není důkaz mapování.
6. T003-S09-W05: úplný analytický report po W09, BE–FE a již dodaných artifact
   adaptérech. Odděl chybějící business data od nedostatečného pokrytí nástroje;
   průchod musí mít ověřitelné zdroje a nejslabší evidenci.

**T048-AC03:** každá původní AC je namapována na skutečný test a konkrétní běh,
positive/negative/ambiguous varianty zůstávají rozlišené. Integrační fixture ukáže
cestu přes deklarované BE/FE rozhraní a přeruší ji při změně contract hash.
Zdokumentuj limity K2, ORM a framework variant místo tvrzení obecné úplnosti.

## 6. T048-S04 — jedna společná inkrementální infrastruktura

Důležité pořadí: T003-S10-W01 explicitně závisí také na T003-S09-W05.
Proto nelze celý incremental balík označit READY před dokončením jeho předchůdců.
T047-S01 mutation oracle a návrh identity lze připravit dříve, bez tvrzení parity.

| Dodávka | Jediný vlastník implementace | Navazující acceptance T047 |
|---|---|---|
| Reprodukční BE/FE fixture a logical symbol keys | T047-S01/S02 v existujícím scanner/model/workspace | AC01/AC02; posun řádku zachová logickou identitu, overload/realm se neslijí |
| Stage content cache | T003-S10-W01 | Rozšiř současný store/provider; žádný druhý cache engine |
| Reverse dependencies a support revocation | T003-S10-W02 | T047-S03; AND/OR podpory, sdílené entity a odvolané důkazy |
| Negative lookup a incoming-edge invalidace | T003-S10-W03 | T047-S04; nový/zmizelý symbol aktualizuje i nezměněného volajícího |
| Corruption/concurrency a generace | T003-S10-W06 | T047-S05; baseline CAS a poslední validní generace při chybě |
| Full/incremental mutation equivalence | T003-S10-W04 | T047-S06; ruční oracle a kanonické srovnání |
| Selektivní feature revise | T003-S10-W05 | Společné fingerprints a dopad; bez kompletní dependency evidence konzervativně STALE |
| Invalidace high-level pohledů | T037 | T047 kontrakty reuse, žádná paralelní cache |
| Publikace exportů | T038, až po T022/T036/T037 | Reuse generation mechanismu; publikace souborů není nezávislá implementace store |

Implementuj W01 → W02 → W03 → W04 → W05; W06 po W01 a před tvrzením bezpečného
souběžného provozu/parity. T047 specifická rozšíření zahrň do příslušného upstream
PR s odkazy na obě sady AC; jejich řádky ukazují na tentýž commit.

**T048-AC04:** mutation fixture pokrývá add/edit/delete/rename/move, komentář nad
deklarací, overload, nový dříve nenalezený symbol, změnu kontraktu/konfigurace a
cross-repo caller. Canonical full versus incremental má nula rozdílů v deklarované
matici. Neplatný vstup, výpadek uprostřed publikace, poškozená cache a souběžný writer
nezničí poslední platný snapshot. Měř počet znovu extrahovaných jednotek, ale
neobětuj správnost požadavku na minimální invalidaci.

## 7. T048-S05 — dokončit high-level pohledy jako uživatelský celek

- T020 je již v main: zachovej interfaces Markdown a jeho escaping/privacy testy.
- Po T003-S07-W09 implementuj T021 → T022 nad existujícím
  `architecture_render.py`, nikoli novým konkurenčním rendererem.
  Testuj parserem Mermaid, determinismus, dangling edges, malicious labels a
  zachování UNKNOWN/PARTIAL; nepovažuj přítomnost fenced textu za rendering PASS.
- T027 a T028 navazují na dodané T014/T025 (T028 také T012). Dodej HTTP a Kafka
  procesní přechody pouze přes explicitní binding. Zabraň nekonečným cyklům,
  shodě názvů mezi službami a falešnému synchronnímu pořadí u Kafka.
- T029 po T028/T025 a již dodaném S07-W05 zachytí doložené chybové/retry/DLT
  větve. Deklarovaná retry policy není prokázané runtime doručení.
- T034 po T027–T029/T030–T033 zpřístupní lifecycle přes CLI.
  T035 po T034 a všech path podkladech přidá Mermaid; T036 po T035/T033 report.
- T037 lze připravit po jeho existujících T018/T032/T033 předchůdcích; integruj
  s jedinou incremental infrastrukturou dle §6.
- T038 až po T022/T036/T037; potom T039 snapshot diff.
- T040 po T034/T036 sladí host instrukce i generující templates.
- T043 po T017/T025/T037 změří výkon a ořezání se zachováním coverage.
- T041 po T020/T021/T022/T038 a T042 po T035/T036/T038/T040 ověří celý workflow.
- T044 uzavři až po T039/T040/T041/T042/T043. Dokumentaci však průběžně upravuj
  u každého z uvedených PR; T044 není odklad dokumentační povinnosti.

**T048-AC05:** jeden doložený multi-repo scénář projde katalog → topologie →
procesní path → report → změna zdroje → invalidace → diff, s přesnými odkazy na
původní důkazy. Strict incomplete má dokumentovaný exit/status, nepodporované
hranice zůstávají viditelné. Read-only příkazy nespouštějí workery, build ani síť.

## 8. T048-S06 — dokončit zbývající kontext a ověření T047

1. S07 → S08 → S09: omezený model serverových ochran, řízený traversal pod
   rozpočtem a vysvětlitelná hranice dopadu. Rozšiř model/context/availability,
   nezaváděj univerzální security scanner. Client validace není serverová ochrana;
   samotné jméno tenantId nic nedokazuje.
2. Po integraci T046 dodej S10 → S11: VerificationRecord v jeho provenance/journal
   a freshness gate v existujícím workflow/memory. Dirty worktree musí zneplatnit
   doklad, i když HEAD zůstává stejné. AGENT_DECLARED nesplní runner evidence.
3. S12 → S13: CLI/docs/migrace a benchmark. Reuse §6; nepiš další mutation harness.

**T048-AC06:** malé token budgety nepřekryjí vynechanou povinnou ochranu; stale PASS
a pouhé tvrzení agenta nedokončí task. Ověř start bez completion, FAIL/SKIP/NOT_RUN,
změnu testů/config/lockfile a neplatný import. Přesné závislosti a všech 13 AC
zůstávají podle T047, tato stručná orchestrace je nenahrazuje.

## 9. T048-S07 — produkční acceptance a release

Po dokončení předchůdců T003-S03–S10: S11-W05 benchmark corpus → W06 regression
budgets → W07 full E2E → W08 release dokumentace. Corpus lze připravovat dříve,
ale finální acceptance vyžaduje skutečné implementace a předepsané toolchainy.

- Použij ručně anotované očekávané výsledky, nezískávej oracle testovaným extraktorem.
- Měř cold/warm čas, paměť, počet souborů/symbolů a invalidací; publikuj prostředí,
  vstupy a přesné revize. Výkonový threshold odvoď z měření, nevymýšlej procenta úspor.
- Reálně ověř čistou instalaci mimo checkout a podporovanou Windows konfiguraci.
  Dosud neověřené K2 Windows či nepodporované BUILD_EXECUTE nepřejmenuj na PASS.
- Pro Kotlin/JVM/TS změny jsou nutné skutečné worker testy. Mock protokol neprokazuje
  compiler resolution. Uveď jednotlivé skip důvody a dopad na deklarovanou podporu.
- Zachovej graph/store kompatibilitu a uživatelské semantic/review/history artefakty.
  Cache je odvoditelná; user evidence se při migraci automaticky nemaže.
- Po T044/S11-W08 a T047-S13 musí README, capability matrix, CLI help/příklady
  a acceptance popisovat stejnou podporovanou verzi a stejné limity.

**T048-AC07:** existuje reprodukovatelný acceptance/report balík nad přesným
release candidate SHA; žádný povinný SKIP není prezentován jako plný PASS.
GH CI je dle uživatelské politiky doplňující; konkrétní chyba testu/kódu blokuje,
billing-only ne nahrazuje lokální evidence. Tento plán sám žádnou CI chybu neřeší.

## 10. T048-S08 — oddělené odložené možnosti

T003-S12-W01 live Confluence zůstává DEFERRED, dokud není konkrétní host/API/auth
kontrakt a oprávnění pro sandbox. Existující offline export i fake boundary zachovej.
`enabled: true` ani dostupná env proměnná není důkaz funkčního spojení.

T003-S13-W01 → W02 → W03/W04 je volitelná runtime větev (s jejich dalšími závislostmi).
Trace musí být svázaná s build/config/source a oddělená od statických hran.
Nespouštěj sběr proti reálným systémům v rámci implicitního scan/hook.

**T048-AC08:** odložené položky mají důvod, konkrétní vstup pro odblokování a stav
NOT_RUN; jejich odklad nebrání pravdivému dokončení deklarovaného statického scope
a není vydáván za plné splnění live/runtime funkcí.

## 11. Společný postup pro každý atomický krok

1. Aktualizuj main/parent a přečti původní specifikaci. U závislého PR zaznamenej
   konkrétní SHA; existence souboru nebo agenta není splnění dependency.
2. Vyber jediný připravený úkol. Pokud blokuje závislost, zapiš BLOCKED s odkazem
   a pokračuj jiným nezávislým úkolem, nevymýšlej dočasné veřejné API.
3. Použij existující task/memory workflow, pokud je v checkoutu funkční; nenič
   jeho historii. Připrav malou podporovanou fixture a ověř, že acceptance
   před implementací skutečně zachytí chybějící či nesprávné chování.
4. Implementuj v existujících modulech. Zachovej immutable evidence, explicitní
   contexts a nulovou mutaci při chybě; nepovýšuj heuristiky na fakt.
5. Spusť nejmenší relevantní testy a projektovou sadu podle původního zadání.
   Standardní příkazy jsou `PYTHONPATH=src python3 -m pytest -q` a
   `git diff --check`; nejprve ověř prostředí a skutečnou konfiguraci CI.
   Přidej skutečný worker/parser/build test podle změněného kontraktu.
6. Ve stejném PR zdokumentuj každý krok podle AGENTS. Aktualizuj zdrojové
   templates a spravované kopie instrukcí, pokud se mění jejich chování.
7. Generovaný graf aktualizuj projektovým příkazem při strukturální změně;
   sémantický patch pouze s ověřenými vztahy pro aktuální packet. Graph freshness
   není důvod k obejití semantic mismatch. Bez nutnosti nevytvářej LLM vazby.
8. Před ready znovu ověř branch/base, naming kolize a dependencies. PR obsahuje
   mapování Task/AC → změna → test → skutečný výsledek → SHA. Historický důkaz
   přenosu výsledků označ výslovně; nikdy ho nenazývej novým test runem.
9. Předej nezávislému review. Implementační agent nemerguje; T045 oprávnění platí
   pouze v jeho explicitním review workflow. T048 není nové oprávnění k merge.

### Šablona záznamu každého kroku

```markdown
### <Task/Step ID> — <konkrétní změna>
- Specifikace a revize:
- Parent/base SHA a ověřované source SHA:
- Delivery: PLANNED | IN_PROGRESS | PR_OPEN | MERGED | BLOCKED | DEFERRED
- Verification: VERIFIED_IN_SCOPE | PARTIAL | NOT_RUN | FAIL
- Problém a skutečné chování před/po:
- Změněné moduly/kontrakty:
- AC → test → příkaz → výsledek → důkaz běhu:
- Nepřipravené toolchainy / SKIP / NOT_RUN a důsledky:
- Dokumentace: README; capability/API/CLI + příklady; stav; acceptance;
  registr při změně — odkaz na úpravu nebo konkrétní bez dopadu:
- Kompatibilita/migrace/rollback:
- Omezení, další krok a dependency:
- PR / review evidence:
```

**T048-R01 / AC09:** každý dokončený krok má uvedený záznam, aktuální dokumentaci
a vysvětlené dokumentační plochy bez dopadu. Review odmítne chybějící záznam nebo
rozpor kód/návod. Jeden change note může mít více jasně oddělených kroků.

**T048-R02 / AC10:** jediný vlastník každého překrývajícího se kontraktu T003/T047/
T037/T038/T046 je uvedený; existující Task ID a historická evidence jsou zachované.

## 12. Migrace, rollback a Definition of Done

Toto předání mění pravidla a text templates; nemění graph schema ani runtime ID.
Implementační migrace musí být aditivní nebo explicitně verzované, se zachováním
poslední validní generace a odmítnutím nepodporovaného readeru. Rollback nesmí
destruktivně převádět novější důkazy nebo zahazovat uživatelské review.

Dokumentační předání T048 je dodané, když je plán registrovaný, pravidlo je v AGENTS
a host instrukcích/templates, odkazy jsou validní a změna má český change note.
To **není** splnění programu S01–S08. Program je hotový až po AC01–AC10 a původních
AC povinného scope; volitelné/odložené položky zůstávají explicitně oddělené.

## Příloha A — přesné samostatné úkoly, které zůstávají dodat

Každý odkaz je normativní detail se samostatnou větví a acceptance.
Níže uvedený stručný přehled jeho požadavky nezmenšuje. Primární místa mohou ve
starém zadání říkat „nový modul“; pokud již existuje, rozšiř jej.


### [T021 — Mermaid schéma služeb](T-021_render-topology-mermaid.md)

- Depends on: [T017](T-017_filter-topology-scope.md); [T019](T-019_add-architecture-json-cli.md); `T003-S07-W09` (upstream; ověř konkrétní podporovaný kontrakt a acceptance, samotná existence zadání nestačí).
- Primární moduly: `nový architecture_render.py`, `flow.py`. Názvy nových modulů jsou návrh; při existujícím ekvivalentu jej rozšiř a odůvodni umístění v PR.
- Cíl: Mermaid schéma služeb. Výstupem tohoto úkolu je jediný otestovatelný kontrakt popsaný níže. Lze jej sloučit samostatně po splnění deklarovaných závislostí; není nutné dokončit celý T004. Závislosti neimplementuj skrytě v tomto PR. Při chybějícím upstream kontraktu zapiš BLOCKED a odkaz na konkrétní chybějící AC; fallback je povolen pouze jako přiznaný PARTIAL/UNKNOWN, pokud splní všechna zdejší kritéria.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T022 — Markdown report topologie a detailů](T-022_render-topology-markdown.md)

- Depends on: [T018](T-018_explain-view-elements.md); [T021](T-021_render-topology-mermaid.md).
- Primární moduly: `nový architecture_render.py`. Názvy nových modulů jsou návrh; při existujícím ekvivalentu jej rozšiř a odůvodni umístění v PR.
- Cíl: Markdown report topologie a detailů. Výstupem tohoto úkolu je jediný otestovatelný kontrakt popsaný níže. Lze jej sloučit samostatně po splnění deklarovaných závislostí; není nutné dokončit celý T004. Závislosti neimplementuj skrytě v tomto PR. Při chybějícím upstream kontraktu zapiš BLOCKED a odkaz na konkrétní chybějící AC; fallback je povolen pouze jako přiznaný PARTIAL/UNKNOWN, pokud splní všechna zdejší kritéria.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T027 — Průchod procesu přes HTTP rozhraní](T-027_cross-http-process-boundary.md)

- Depends on: [T014](T-014_bind-remote-interfaces.md); [T025](T-025_build-local-process-path.md).
- Primární moduly: `nový business_process.py`, `workspace.py`. Názvy nových modulů jsou návrh; při existujícím ekvivalentu jej rozšiř a odůvodni umístění v PR.
- Cíl: Průchod procesu přes HTTP rozhraní. Výstupem tohoto úkolu je jediný otestovatelný kontrakt popsaný níže. Lze jej sloučit samostatně po splnění deklarovaných závislostí; není nutné dokončit celý T004. Závislosti neimplementuj skrytě v tomto PR. Při chybějícím upstream kontraktu zapiš BLOCKED a odkaz na konkrétní chybějící AC; fallback je povolen pouze jako přiznaný PARTIAL/UNKNOWN, pokud splní všechna zdejší kritéria.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T028 — Asynchronní návaznosti procesu](T-028_cross-async-process-boundary.md)

- Depends on: [T012](T-012_catalog-kafka-interfaces.md); [T014](T-014_bind-remote-interfaces.md); [T025](T-025_build-local-process-path.md).
- Primární moduly: `nový business_process.py`. Názvy nových modulů jsou návrh; při existujícím ekvivalentu jej rozšiř a odůvodni umístění v PR.
- Cíl: Asynchronní návaznosti procesu. Výstupem tohoto úkolu je jediný otestovatelný kontrakt popsaný níže. Lze jej sloučit samostatně po splnění deklarovaných závislostí; není nutné dokončit celý T004. Závislosti neimplementuj skrytě v tomto PR. Při chybějícím upstream kontraktu zapiš BLOCKED a odkaz na konkrétní chybějící AC; fallback je povolen pouze jako přiznaný PARTIAL/UNKNOWN, pokud splní všechna zdejší kritéria.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T029 — Chybové větve, retry a kompenzace](T-029_project-process-failures.md)

- Depends on: [T025](T-025_build-local-process-path.md); [T028](T-028_cross-async-process-boundary.md); `T003-S07-W05` (upstream; ověř konkrétní podporovaný kontrakt a acceptance, samotná existence zadání nestačí).
- Primární moduly: `nový business_process.py`, `flow.py`. Názvy nových modulů jsou návrh; při existujícím ekvivalentu jej rozšiř a odůvodni umístění v PR.
- Cíl: Chybové větve, retry a kompenzace. Výstupem tohoto úkolu je jediný otestovatelný kontrakt popsaný níže. Lze jej sloučit samostatně po splnění deklarovaných závislostí; není nutné dokončit celý T004. Závislosti neimplementuj skrytě v tomto PR. Při chybějícím upstream kontraktu zapiš BLOCKED a odkaz na konkrétní chybějící AC; fallback je povolen pouze jako přiznaný PARTIAL/UNKNOWN, pokud splní všechna zdejší kritéria.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T034 — CLI životního cyklu procesů](T-034_add-process-cli.md)

- Depends on: [T027](T-027_cross-http-process-boundary.md); [T028](T-028_cross-async-process-boundary.md); [T029](T-029_project-process-failures.md); [T030](T-030_prepare-process-label-packet.md); [T031](T-031_validate-process-annotations.md); [T032](T-032_persist-process-review.md); [T033](T-033_catalog-business-processes.md).
- Primární moduly: `cli.py`, `nový process_cli.py`. Názvy nových modulů jsou návrh; při existujícím ekvivalentu jej rozšiř a odůvodni umístění v PR.
- Cíl: CLI životního cyklu procesů. Výstupem tohoto úkolu je jediný otestovatelný kontrakt popsaný níže. Lze jej sloučit samostatně po splnění deklarovaných závislostí; není nutné dokončit celý T004. Závislosti neimplementuj skrytě v tomto PR. Při chybějícím upstream kontraktu zapiš BLOCKED a odkaz na konkrétní chybějící AC; fallback je povolen pouze jako přiznaný PARTIAL/UNKNOWN, pokud splní všechna zdejší kritéria.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T035 — Mermaid business průběhu](T-035_render-business-process-mermaid.md)

- Depends on: [T026](T-026_collapse-business-steps.md); [T027](T-027_cross-http-process-boundary.md); [T028](T-028_cross-async-process-boundary.md); [T029](T-029_project-process-failures.md); [T034](T-034_add-process-cli.md).
- Primární moduly: `nový process_render.py`. Názvy nových modulů jsou návrh; při existujícím ekvivalentu jej rozšiř a odůvodni umístění v PR.
- Cíl: Mermaid business průběhu. Výstupem tohoto úkolu je jediný otestovatelný kontrakt popsaný níže. Lze jej sloučit samostatně po splnění deklarovaných závislostí; není nutné dokončit celý T004. Závislosti neimplementuj skrytě v tomto PR. Při chybějícím upstream kontraktu zapiš BLOCKED a odkaz na konkrétní chybějící AC; fallback je povolen pouze jako přiznaný PARTIAL/UNKNOWN, pokud splní všechna zdejší kritéria.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T036 — Markdown business report](T-036_render-business-process-report.md)

- Depends on: [T033](T-033_catalog-business-processes.md); [T035](T-035_render-business-process-mermaid.md).
- Primární moduly: `nový process_render.py`. Názvy nových modulů jsou návrh; při existujícím ekvivalentu jej rozšiř a odůvodni umístění v PR.
- Cíl: Markdown business report. Výstupem tohoto úkolu je jediný otestovatelný kontrakt popsaný níže. Lze jej sloučit samostatně po splnění deklarovaných závislostí; není nutné dokončit celý T004. Závislosti neimplementuj skrytě v tomto PR. Při chybějícím upstream kontraktu zapiš BLOCKED a odkaz na konkrétní chybějící AC; fallback je povolen pouze jako přiznaný PARTIAL/UNKNOWN, pokud splní všechna zdejší kritéria.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T037 — Invalidace odvozených pohledů](T-037_invalidate-derived-views.md)

- Depends on: [T018](T-018_explain-view-elements.md); [T032](T-032_persist-process-review.md); [T033](T-033_catalog-business-processes.md).
- Primární moduly: `graph_provider.py`, `nový view_cache.py`. Názvy nových modulů jsou návrh; při existujícím ekvivalentu jej rozšiř a odůvodni umístění v PR.
- Cíl: Invalidace odvozených pohledů. Výstupem tohoto úkolu je jediný otestovatelný kontrakt popsaný níže. Lze jej sloučit samostatně po splnění deklarovaných závislostí; není nutné dokončit celý T004. Závislosti neimplementuj skrytě v tomto PR. Při chybějícím upstream kontraktu zapiš BLOCKED a odkaz na konkrétní chybějící AC; fallback je povolen pouze jako přiznaný PARTIAL/UNKNOWN, pokud splní všechna zdejší kritéria.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T038 — Atomická publikace exportů](T-038_publish-view-artifacts-atomically.md)

- Depends on: [T022](T-022_render-topology-markdown.md); [T036](T-036_render-business-process-report.md); [T037](T-037_invalidate-derived-views.md).
- Primární moduly: `nový view_store.py`, `architecture_cli.py`, `process_cli.py`. Názvy nových modulů jsou návrh; při existujícím ekvivalentu jej rozšiř a odůvodni umístění v PR.
- Cíl: Atomická publikace exportů. Výstupem tohoto úkolu je jediný otestovatelný kontrakt popsaný níže. Lze jej sloučit samostatně po splnění deklarovaných závislostí; není nutné dokončit celý T004. Závislosti neimplementuj skrytě v tomto PR. Při chybějícím upstream kontraktu zapiš BLOCKED a odkaz na konkrétní chybějící AC; fallback je povolen pouze jako přiznaný PARTIAL/UNKNOWN, pokud splní všechna zdejší kritéria.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T039 — Sémantický diff dvou snapshotů](T-039_diff-architecture-and-processes.md)

- Depends on: [T037](T-037_invalidate-derived-views.md); [T038](T-038_publish-view-artifacts-atomically.md).
- Primární moduly: `nový view_diff.py`. Názvy nových modulů jsou návrh; při existujícím ekvivalentu jej rozšiř a odůvodni umístění v PR.
- Cíl: Sémantický diff dvou snapshotů. Výstupem tohoto úkolu je jediný otestovatelný kontrakt popsaný níže. Lze jej sloučit samostatně po splnění deklarovaných závislostí; není nutné dokončit celý T004. Závislosti neimplementuj skrytě v tomto PR. Při chybějícím upstream kontraktu zapiš BLOCKED a odkaz na konkrétní chybějící AC; fallback je povolen pouze jako přiznaný PARTIAL/UNKNOWN, pokud splní všechna zdejší kritéria.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T040 — Instrukce host agenta pro pohledy](T-040_add-agent-process-instructions.md)

- Depends on: [T034](T-034_add-process-cli.md); [T036](T-036_render-business-process-report.md).
- Primární moduly: `agents.py`, `agent_rules.py`, `dodávané agent templates`. Názvy nových modulů jsou návrh; při existujícím ekvivalentu jej rozšiř a odůvodni umístění v PR.
- Cíl: Instrukce host agenta pro pohledy. Výstupem tohoto úkolu je jediný otestovatelný kontrakt popsaný níže. Lze jej sloučit samostatně po splnění deklarovaných závislostí; není nutné dokončit celý T004. Závislosti neimplementuj skrytě v tomto PR. Při chybějícím upstream kontraktu zapiš BLOCKED a odkaz na konkrétní chybějící AC; fallback je povolen pouze jako přiznaný PARTIAL/UNKNOWN, pokud splní všechna zdejší kritéria.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T041 — End-to-end acceptance architektury](T-041_verify-architecture-acceptance.md)

- Depends on: [T020](T-020_render-interface-markdown.md); [T021](T-021_render-topology-mermaid.md); [T022](T-022_render-topology-markdown.md); [T038](T-038_publish-view-artifacts-atomically.md).
- Primární moduly: `tests/fixtures`, `tests`, `CI rendering job`. Názvy nových modulů jsou návrh; při existujícím ekvivalentu jej rozšiř a odůvodni umístění v PR.
- Cíl: End-to-end acceptance architektury. Výstupem tohoto úkolu je jediný otestovatelný kontrakt popsaný níže. Lze jej sloučit samostatně po splnění deklarovaných závislostí; není nutné dokončit celý T004. Závislosti neimplementuj skrytě v tomto PR. Při chybějícím upstream kontraktu zapiš BLOCKED a odkaz na konkrétní chybějící AC; fallback je povolen pouze jako přiznaný PARTIAL/UNKNOWN, pokud splní všechna zdejší kritéria.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T042 — End-to-end acceptance business procesů](T-042_verify-process-acceptance.md)

- Depends on: [T035](T-035_render-business-process-mermaid.md); [T036](T-036_render-business-process-report.md); [T038](T-038_publish-view-artifacts-atomically.md); [T040](T-040_add-agent-process-instructions.md).
- Primární moduly: `tests/fixtures`, `tests`, `CI`. Názvy nových modulů jsou návrh; při existujícím ekvivalentu jej rozšiř a odůvodni umístění v PR.
- Cíl: End-to-end acceptance business procesů. Výstupem tohoto úkolu je jediný otestovatelný kontrakt popsaný níže. Lze jej sloučit samostatně po splnění deklarovaných závislostí; není nutné dokončit celý T004. Závislosti neimplementuj skrytě v tomto PR. Při chybějícím upstream kontraktu zapiš BLOCKED a odkaz na konkrétní chybějící AC; fallback je povolen pouze jako přiznaný PARTIAL/UNKNOWN, pokud splní všechna zdejší kritéria.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T043 — Limity výkonu a velikosti](T-043_bound-view-performance.md)

- Depends on: [T017](T-017_filter-topology-scope.md); [T025](T-025_build-local-process-path.md); [T037](T-037_invalidate-derived-views.md).
- Primární moduly: `tests/benchmarks`, `architecture.py`, `business_process.py`. Názvy nových modulů jsou návrh; při existujícím ekvivalentu jej rozšiř a odůvodni umístění v PR.
- Cíl: Limity výkonu a velikosti. Výstupem tohoto úkolu je jediný otestovatelný kontrakt popsaný níže. Lze jej sloučit samostatně po splnění deklarovaných závislostí; není nutné dokončit celý T004. Závislosti neimplementuj skrytě v tomto PR. Při chybějícím upstream kontraktu zapiš BLOCKED a odkaz na konkrétní chybějící AC; fallback je povolen pouze jako přiznaný PARTIAL/UNKNOWN, pokud splní všechna zdejší kritéria.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T044 — Dokumentace a release gate](T-044_document-high-level-capabilities.md)

- Depends on: [T039](T-039_diff-architecture-and-processes.md); [T040](T-040_add-agent-process-instructions.md); [T041](T-041_verify-architecture-acceptance.md); [T042](T-042_verify-process-acceptance.md); [T043](T-043_bound-view-performance.md).
- Primární moduly: `README.md`, `docs/production-analysis-progress.md`, `docs/acceptance-inventory.md`, `docs/high-level-views.md`. Názvy nových modulů jsou návrh; při existujícím ekvivalentu jej rozšiř a odůvodni umístění v PR.
- Cíl: Dokumentace a release gate. Výstupem tohoto úkolu je jediný otestovatelný kontrakt popsaný níže. Lze jej sloučit samostatně po splnění deklarovaných závislostí; není nutné dokončit celý T004. Závislosti neimplementuj skrytě v tomto PR. Při chybějícím upstream kontraktu zapiš BLOCKED a odkaz na konkrétní chybějící AC; fallback je povolen pouze jako přiznaný PARTIAL/UNKNOWN, pokud splní všechna zdejší kritéria.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T003-S05-W04 — Proxy, weaving a async semantika](T003-S05-04-springProxyAsyncSemantics.md)

- Závislosti: T003-S04-W03 a T003-S05-W01 až T003-S05-W03; průřezové požadavky `T003-R01–R10`.
- Primární místa změny: `src/kgmaker/framework.py, src/kgmaker/flow.py, src/kgmaker/views.py`.
- Cíl: Modelovat podporované proxy/weaving režimy a oddělit Async/event/reactive přechod od synchronního pokračování.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T003-S06-W05 — Rozšířená JPQL/HQL gramatika](T003-S06-05-jpqlHqlGrammar.md)

- Závislosti: T003-S06-W02 a T003-S06-W04; průřezové požadavky `T003-R01–R10`.
- Primární místa změny: `src/kgmaker/framework.py, src/kgmaker/dataflow.py`.
- Cíl: Parsovat joins, subqueries, updates/deletes, constructor projections a path expressions konzervativně.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T003-S06-W06 — NamedQueries a named native queries](T003-S06-06-namedQueryContainers.md)

- Závislosti: T003-S06-W03 a T003-S06-W05; průřezové požadavky `T003-R01–R10`.
- Primární místa změny: `src/kgmaker/framework.py, src/kgmaker/domain.py`.
- Cíl: Podpořit opakované/container anotace a XML named queries včetně parametrů/projekcí.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T003-S06-W07 — Criteria, Specification a QueryDSL](T003-S06-07-criteriaSpecificationQuerydsl.md)

- Závislosti: T003-S04-W04, T003-S06-W05 a T003-S06-W06; průřezové požadavky `T003-R01–R10`.
- Primární místa změny: `workers/jvm, src/kgmaker/framework.py, src/kgmaker/dataflow.py`.
- Cíl: Přidat bounded patterny pro statické Criteria/Specification/QueryDSL dotazy a custom repository fragments.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T003-S07-W03 — Field a explicitní mapping tok](T003-S07-03-fieldAndMappingFlow.md)

- Závislosti: T003-S06-W02, T003-S07-W01 a T003-S07-W02; průřezové požadavky `T003-R01–R10`.
- Primární místa změny: `src/kgmaker/dataflow.py, src/kgmaker/domain.py`.
- Cíl: Rozšířit field read/write a podporované DTO/entity mapper patterns přes metody.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T003-S07-W08 — Vysvětlitelný execution/impact ranking](T003-S07-08-evidenceRanking.md)

- Závislosti: T003-S07-W01 až T003-S07-W07; průřezové požadavky `T003-R01–R10`.
- Primární místa změny: `src/kgmaker/callgraph.py, src/kgmaker/analysis_report.py, src/kgmaker/views.py`.
- Cíl: Doplnit entry relevance, doloženou cestu, side effects a penalty za neúplnost.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T003-S07-W09 — Jednotné flow pohledy](T003-S07-09-unifiedFlowViews.md)

- Závislosti: T003-S07-W08; průřezové požadavky `T003-R01–R10`.
- Primární místa změny: `src/kgmaker/views.py, src/kgmaker/flow.py`.
- Cíl: Generovat Markdown/Mermaid/JSON z jednoho modelu včetně async, unresolved, provenance a truncation.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T003-S08-W05 — Backend→frontend value flow](T003-S08-05-backendFrontendValueFlow.md)

- Závislosti: T003-S07-W06, T003-S07-W07 a T003-S08-W01 až T003-S08-W04; průřezové požadavky `T003-R01–R10`.
- Primární místa změny: `src/kgmaker/workspace.py, src/kgmaker/dataflow.py, src/kgmaker/test_analysis.py`.
- Cíl: Propojit response fields přes kontrakt, mapping/destructuring/state do UI použití.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T003-S09-W05 — Úplný analytický report](T003-S09-05-completeAnalysisReport.md)

- Závislosti: T003-S07-W09, T003-S08-W05 a T003-S09-W01 až T003-S09-W04; průřezové požadavky `T003-R01–R10`.
- Primární místa změny: `src/kgmaker/analysis_report.py, src/kgmaker/analysis_validation.py`.
- Cíl: Doplnit Required/Existing/Missing/Derived/External/Unresolved z nezávislých dimenzí a delivery/test plán.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T003-S10-W01 — Content-addressed cache po stupních](T003-S10-01-stageContentCache.md)

- Závislosti: T003-S03-W04, T003-S04-W01, T003-S05-W03, T003-S06-W04, T003-S07-W07, T003-S08-W02 a T003-S09-W05; průřezové požadavky `T003-R01–R10`.
- Primární místa změny: `src/kgmaker/graph_provider.py, src/kgmaker/store.py, src/kgmaker/inspection.py`.
- Cíl: Zavést cache per module/source-set/variant/extraction stage se všemi freshness vstupy.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T003-S10-W02 — Reverse dependency indexy](T003-S10-02-reverseDependencyIndexes.md)

- Závislosti: T003-S10-W01; průřezové požadavky `T003-R01–R10`.
- Primární místa změny: `src/kgmaker/store.py, src/kgmaker/graph_provider.py, src/kgmaker/feature.py`.
- Cíl: Indexovat callers, schema/contract evidence a feature conclusions pro selektivní invalidaci.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T003-S10-W03 — Invalidace negativních lookupů](T003-S10-03-negativeLookupInvalidation.md)

- Závislosti: T003-S10-W02; průřezové požadavky `T003-R01–R10`.
- Primární místa změny: `src/kgmaker/store.py, src/kgmaker/scanner.py, src/kgmaker/graph_provider.py`.
- Cíl: Ukládat scope dependency pro NOT_FOUND_IN_SCOPE a invalidovat ji při přidání zdroje.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T003-S10-W04 — Ekvivalence add/change/delete/rename](T003-S10-04-filesystemMutationEquivalence.md)

- Závislosti: T003-S10-W01 až T003-S10-W03; průřezové požadavky `T003-R01–R10`.
- Primární místa změny: `src/kgmaker/scanner.py, src/kgmaker/semantic.py, src/kgmaker/store.py`.
- Cíl: Sjednotit canonical výsledek incremental a full scan pro všechny filesystem mutace a ID kolize.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T003-S10-W05 — Selektivní revise a historie](T003-S10-05-selectiveFeatureRevise.md)

- Závislosti: T003-S10-W02 a T003-S10-W04; průřezové požadavky `T003-R01–R10`.
- Primární místa změny: `src/kgmaker/feature.py, src/kgmaker/analysis_validation.py, src/kgmaker/store.py`.
- Cíl: Přepočítat závislé feature závěry, zachovat nezávislé a auditní historii.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T003-S10-W06 — Corruption fallback a worker concurrency](T003-S10-06-cacheCorruptionConcurrency.md)

- Závislosti: T003-S10-W01; průřezové požadavky `T003-R01–R10`.
- Primární místa změny: `src/kgmaker/store.py, src/kgmaker/inspection.py, src/kgmaker/build_runner.py`.
- Cíl: Považovat poškozenou cache za miss a publikovat immutable worker artefakty atomicky.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T003-S11-W05 — Benchmark corpus a měření](T003-S11-05-benchmarkCorpus.md)

- Závislosti: T003-S03-W01 až T003-S10-W06; průřezové požadavky `T003-R01–R10`.
- Primární místa změny: `benchmarks, tests/fixtures, docs`.
- Cíl: Vytvořit reprezentativní anotovaný corpus a měřit cold/warm čas, paměť, index a coverage.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T003-S11-W06 — Výkonové regression budgets](T003-S11-06-regressionBudgets.md)

- Závislosti: T003-S11-W05; průřezové požadavky `T003-R01–R10`.
- Primární místa změny: `benchmarks, CI`.
- Cíl: Odvodit rozpočty z benchmark baseline a přidat stabilní regresní gate.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T003-S11-W07 — Společná end-to-end acceptance](T003-S11-07-fullEndToEndAcceptance.md)

- Závislosti: T003-S03-W01 až T003-S10-W06, T003-S11-W04 a T003-S11-W06; průřezové požadavky `T003-R01–R10`.
- Primární místa změny: `tests, fixtures, docs/acceptance-inventory.md`.
- Cíl: Automatizovat build/import→inspection→refresh→feature/data audit→report→změna→invalidace.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T003-S11-W08 — Release a capability dokumentace](T003-S11-08-releaseDocumentation.md)

- Závislosti: T003-S11-W07; průřezové požadavky `T003-R01–R10`.
- Primární místa změny: `README.md, docs, CLI help/templates`.
- Cíl: Sjednotit README, architecture, CLI help, registry, capability docs a progress s release scope.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T003-S13-W01 — Sanitizovaný runtime trace producer](T003-S13-01-runtimeTraceProducer.md)

- Závislosti: T003-S05-W04, T003-S07-W05 a T003-S07-W06; průřezové požadavky `T003-R01–R10`.
- Primární místa změny: `runtime tooling, src/kgmaker/runtime_evidence.py`.
- Cíl: Vytvořit explicitně spouštěný exportér call/bean/condition/mapping facts bez automatického startupu aplikace.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T003-S13-W02 — RTA a runtime dispatch import](T003-S13-02-runtimeRtaImport.md)

- Závislosti: T003-S04-W04 a T003-S13-W01; průřezové požadavky `T003-R01–R10`.
- Primární místa změny: `src/kgmaker/runtime_evidence.py, src/kgmaker/callgraph.py`.
- Cíl: Importovat observed receiver/type facts jako scope-bound doplnění statických dispatch kandidátů.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T003-S13-W03 — Runtime value-flow evidence](T003-S13-03-runtimeValueFlow.md)

- Závislosti: T003-S07-W03, T003-S13-W01 a T003-S13-W02; průřezové požadavky `T003-R01–R10`.
- Primární místa změny: `src/kgmaker/runtime_evidence.py, src/kgmaker/availability.py, src/kgmaker/dataflow.py`.
- Cíl: Importovat sanitizované value-path evidence odděleně od pouhé call observation.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.

### [T003-S13-W04 — Async a reflective runtime capture](T003-S13-04-runtimeAsyncReflection.md)

- Závislosti: T003-S05-W04, T003-S07-W05, T003-S13-W01 a T003-S13-W02; průřezové požadavky `T003-R01–R10`.
- Primární místa změny: `runtime tooling, src/kgmaker/runtime_evidence.py, src/kgmaker/flow.py`.
- Cíl: Zachovat async boundaries a explicitně zachytit podporované reflective targets.
- Acceptance a testy: všechny AC původního zadání; ověř pozitivní, nejednoznačný a chybový vstup, freshness a no-mutation dle jeho kontraktu. Dokumentační gate T048-AC09 platí navíc.
