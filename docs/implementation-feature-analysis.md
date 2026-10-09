# Implementační pokračování: analýza nových funkcí a datových požadavků

Datum: 2026-10-09  
Stav: závazné zadání rozšíření, nikoliv popis již implementovaných schopností  
Cílový projekt: `p-rum/kgmaker`  
Navazuje na: [README](../README.md), [project-scope](project-scope.md), [architecture](architecture.md)

## 1. Cíl a instrukce pro implementujícího agenta

Rozšiř KGMAKER tak, aby pomáhal vývojářům i analytikům odpovědět:

> Co všechno musíme změnit pro novou feature, jaké vstupy potřebujeme, která data již máme, která lze odvodit a co musí dodat či rozhodnout analytik, business nebo jiný systém?

Výstup nesmí být pouze seznam podobných tříd. Musí obsahovat ověřitelné existující schopnosti, datové požadavky, návrh změn napříč vrstvami, dopady, konkrétní otázky a akceptační kritéria.

Implementuj skutečné CLI, serializovatelný model, validaci agentových výstupů, deterministické reporty, integrační instrukce a testy. Samotný prompt nebo ukázkový report nejsou dokončením tohoto zadání.

Nejdříve přečti současný kód a testy. Znovu používej stabilní identifikátory a evidence ze stávajícího grafu; nevytvářej vedle něj nezávislý katalog se stejnými entitami. Názvy nových modulů uvedené níže jsou doporučené, chování a kontrakty jsou závazné.

### Kontext cílového použití

- Primární backend je jeden Java/Kotlin repository.
- Projekt má mnoho relativně jednoduchých finančních výpočtů, FX i úvěrové produkty.
- Scénáře zahrnují optimistický, pesimistický, mid-optimistický, mid-pesimistický, konstantní a klientský vývoj.
- Například mid-pesimistický může používat polovinu konstantního poklesu pesimistického scénáře; jde o příklad požadavku, nikoliv automaticky platný fakt o každém projektu.
- Vstupy zahrnují klientská data a zajištění včetně pozic v jiných bankách.
- Technologie a artefakty: PostgreSQL, Kafka, Bloomberg, TypeScript frontend, Excel, HTML šablony a externí HTML → PDF služba.
- Frontend nebo kontrakty mohou být v jiném adresáři či repository. Nejsou-li dodány, označ tuto část jako nepokrytou.
- Confluence dodává obchodní a architektonický kontext.

KGMAKER musí zůstat obecně použitelný. Finanční názvy patří do fixtures a agentových konceptů, nikoliv do natvrdo zabudované ontologie.

## 2. Skutečný výchozí stav a změna scope

Při vytvoření zadání současný repository obsahuje:

| Součást | Stav | Požadované navázání |
|---|---|---|
| `scanner.py`, `domain.py` | Konzervativní extrakce deklarací, importů, SQL, Kafka a HTTP vztahů | Doplnit datová pole, transformace a evidence |
| `model.py` | `Node`, `Edge`, `KnowledgeGraph` | Zachovat kompatibilitu, přidat versionované analytické modely |
| `semantic.py` | Manifesty, samostatný extract, změnové pakety, validace patchů | Znovu využít evidence; analytické pakety mít oddělené |
| `impact` | Reverzní importy a heuristické volání podle názvu | Rozšířit o typované, směrované datové závislosti |
| `confluence.py` | Lokální read-only HTML export a report rozporů | Použít business kontext bez zaměňování za implementaci |
| `build`, `update` | Oba dělají full scan | Implementovat inkrementální extrakci, ne jen přejmenovat full scan |
| Agent a hooky | Copilot CLI + existující JetBrains instrukce | Přidat analytický workflow při zachování stávajících workflow |

Současné `docs/project-scope.md` vylučuje online Confluence synchronizaci. Toto pokračování mění scope pouze pro volitelnou, oddělenou synchronizační vrstvu podle kapitoly 16. Offline import, běžný scan i analýza musí fungovat bez ní.

Nezaváděj povinnou grafovou databázi, MCP server, model API klienta ani model API klíč. Zachovej Python 3.11+, lokální JSON a standardní knihovnu v základní instalaci. Sémantické uvažování provádí hostitelský Copilot/IDE agent. Podpora složitějších parserů může být později volitelná, nesmí být předpokladem acceptance fixtures.

Nevytvářej matematický důkazní engine, finanční validátor, runtime instrumentaci ani distribuovaný graf mnoha služeb. Sleduj původ a použití hodnot a přiznávej hranice statické analýzy.

## 3. Dva režimy a oddělení stavů

### 3.1 Existing impact analysis

Vstupem je existující soubor, symbol nebo datové pole. Výstupem jsou přímé i tranzitivní dopady na backend, kontrakty, databázi, zprávy, UI, reporty, testy a dokumentaci.

### 3.2 Feature feasibility analysis

Vstupem je nový business požadavek. Agent jej rozloží na cíle, výstupy, vstupy, pravidla, omezení a rozhodnutí. KGMAKER propojí návrh s existujícími schopnostmi a validuje vytvořenou analýzu.

### 3.3 Stav tvrzení versus stav návrhu

Rozlišuj tři logické pohledy:

- `AS_IS`: reprezentace současného stavu; každý fakt má vlastní kvalitu a platnost evidence.
- `TO_BE`: návrh budoucího stavu izolovaný v konkrétní analýze.
- `UNKNOWN`: nevyřešená otázka či neověřený předpoklad.

`AS_IS` samo o sobě není potvrzení správnosti. Heuristický vztah v AS_IS nesmí být vydáván za prokázané chování. Odděleně eviduj `EXTRACTED / INFERRED / AMBIGUOUS` a `VALID / STALE / UNRESOLVED`.

Návrh nikdy automaticky nepřepisuje `.kgmaker/graph.json`, `.kgmaker/semantic.json` ani zdrojový kód. Následný scan může zjistit implementaci navržené změny, ale nepovýší návrhový uzel na existující entitu bez nové evidence.

## 4. Model analýzy a provenance

Přidej versionovaný kontrakt `FeatureAnalysis`. Minimální povinná pole:

| Pole | Význam |
|---|---|
| `schema_version` | Verze analytického formátu |
| `analysis_id`, `revision` | Stabilní ID analýzy a monotónní revize |
| `requirement_hash` | Hash přesného zadání a odpovědí |
| `baseline` | Git commit, fingerprint grafu a analyzovaného working tree |
| `coverage` | Skenované kořeny, artefakty, vyloučení, parser capabilities a omezení |
| `requirements` | Cíle, pravidla, vstupy, výstupy a omezení s vazbou na text zadání |
| `input_requirements` | Požadované vstupy a vyhodnocení jejich dostupnosti |
| `capability_matches` | Kandidáti existujících funkcí a zdůvodnění využitelnosti |
| `proposal` | Izolované uzly a vztahy budoucího stavu |
| `changes` | Navrhované změny komponent a kontraktů |
| `impact_paths` | Vysvětlené cesty dopadu s evidence |
| `questions`, `assumptions`, `alternatives` | Nevyřešené otázky a varianty |
| `acceptance_criteria`, `test_plan` | Očekávané chování a relevantní testy |
| `completion` | Úplnost zpracování a pending práce |

Používej ID se jmenným prostorem, např. `analysis:<id>:input:available-liquidity` a `proposal:<id>:recommended-hedge`. Odkazy na existující entity musí použít jejich skutečná graph ID.

Evidence musí obsahovat:

- identifikátor zdroje a druh: CODE, CONTRACT, SCHEMA, CONFIG, DOCUMENTATION, WORKBOOK, REQUIREMENT nebo HUMAN_DECISION;
- cestu relativní ke schválenému kořeni, SHA-256 a lokalizaci: řádky/symbol, JSON pointer, HTML anchor/sekce nebo workbook/sheet/cell;
- konkrétní stručné zdůvodnění, co evidence prokazuje;
- způsob získání, confidence a stav platnosti;
- pro rozhodnutí osobou ID rozhodnutí, explicitní odpověď, revizi a deklarovaný approval status.

U souborových zdrojů validátor ověřuje hash i existenci citované lokalizace. Vytvoření předstírané citace agentem musí selhat. Potvrzená evidence podporuje jen to, co z ní lze odvodit; existence stejně pojmenovaného pole není důkaz shodné business definice.

`baseline` musí zahrnout relevantní necommitnuté změny. Nepoužívej samotný Git HEAD jako doklad aktuálnosti.

## 5. Datové požadavky a dostupnost

### 5.1 Neslučuj význam, dostupnost a zdroj

Každý `InputRequirement` musí mít alespoň:

- business název, definici a ID požadavků, které jej potřebují;
- datový typ, jednotku, měnu, granularitu, identifikační klíče;
- časový význam: as-of, interval platnosti, horizont, požadovanou čerstvost;
- povinnost/nullability, požadavky na kvalitu a povolené fallbacky;
- kandidátní zdroje, mapping, potřebné transformace a evidence;
- dostupnost, rozsah ověření a konkrétní další krok;
- návrh odpovědné role, nikoliv vymyšlené jméno vlastníka.

Neznámá metadata musí být explicitně neznámá a případně vytvořit otázku.

Použij nezávislé dimenze:

| Dimenze | Hodnoty |
|---|---|
| `availability` | AVAILABLE, PARTIAL, NOT_FOUND_IN_SCOPE, CONFIRMED_MISSING, UNKNOWN |
| `acquisition` | EXISTING, DERIVED, EXTERNAL, USER_SUPPLIED, PROPOSED, UNRESOLVED |
| `usability` | FIT, TRANSFORMATION_REQUIRED, INCOMPATIBLE, UNASSESSED |

Přehled pro analytika může mít záložky Required / Existing / Missing / Derived / External / Unresolved, ale jejich implementace musí vycházet z těchto dimenzí. Externí data mohou být již AVAILABLE; odvozená data nejsou automaticky dostupná.

### 5.2 Pravidla rozhodování

1. AVAILABLE vyžaduje důkaz dostupné datové cesty a doloženou použitelnost pro požadavek. Samotná deklarace DTO nestačí jako důkaz, že služba pole skutečně naplňuje.
2. PARTIAL použij například pro externí zajištění, kde máme objem a měnu, ale ne splatnost potřebnou pro nový výpočet.
3. DERIVED vyžaduje existující nebo navrženou transformaci, všechny závislosti a jejich dostupnost. Cyklus bez vstupní kotvy nesmí potvrdit odvoditelnost.
4. NOT_FOUND_IN_SCOPE znamená pouze, že nebyl nalezen použitelný zdroj v popsaném rozsahu. V reportu musí být uvedeno, kde se hledalo a co se nezpracovalo.
5. CONFIRMED_MISSING vyžaduje explicitní relevantní rozhodnutí vlastníka nebo doložený úplný kontrakt s jasně omezeným tvrzením, např. „toto pole chybí v této verzi API“. To není důkaz neexistence dat v celé bance.
6. UNKNOWN použij při neurčité definici, chybějícím přístupu, nepodporovaném parseru, dynamické konfiguraci či vyčerpaném kontextu.
7. Shoda názvů, fuzzy search ani vysoké LLM confidence nesmějí samy povýšit UNKNOWN na AVAILABLE nebo CONFIRMED_MISSING.
8. Vygeneruj konkrétní zadání pro získání dat: pole, definice, klíče, jednotky, časová platnost, požadovaná čerstvost, zamýšlený kontrakt a důvod potřeby.

Příklady otázek: „Co přesně zahrnují disponibilní prostředky?“, „Potřebujeme splatnost každé externí pozice?“, „Je limit pevný, nebo klientský parametr?“. Odpověď na jednu otázku musí změnit jen závěry, které na ní závisejí.

## 6. Cross-layer data flow

### 6.1 Rozšíření strukturální extrakce

Přidej explicitní uzly pro DTO/model fields, message fields, API contract fields, template variables, workbook cells/ranges a external systems.

Doplň vztahy s přesně popsaným směrem:

| Vztah | Směr |
|---|---|
| `reads_value` | Konzument → čtené pole |
| `writes_value` | Producent → naplňované pole |
| `derived_from` | Výsledná hodnota → vstupní hodnota |
| `maps_to` | Zdrojové pole → cílové pole |
| `serialized_as` | Interní pole → pole kontraktu |
| `displayed_in` | Hodnota → UI prvek |
| `rendered_in` | Hodnota → template variable/sekce |
| `sent_to` | Kontrakt → externí integrační bod |
| `tested_by` | Chování/entita → test |
| `documented_by` | Entita → dokumentační tvrzení |

Impact traversal musí respektovat význam vztahu: změna vstupu ovlivňuje hodnoty, které jsou z něj odvozené, tedy jde reverzně přes `derived_from`. Nedělej univerzální neorientovanou procházku všech hran.

Každá cesta dopadu musí označit nejslabší článek a nevyřešenou hranici. Heuristické call edge zůstává kandidátem. Nepředstírej kompletní interprocedurální analýzu pouze pomocí regexů.

### 6.2 Minimální podporované vzory

- Kotlin primary constructor properties, Java fields/records a TypeScript interfaces/types.
- Jednoznačné přímé property assignmenty a konstruktorové mappingy v rámci podporovaných vzorů.
- Explicitní použití parametrů a návratových hodnot jednoduchých metod; příslušný rozsah metody a evidence.
- Jednoduché SQL SELECT projekce/agregace a návaznost na schéma; u komplexního dynamického SQL unresolved.
- OpenAPI JSON properties a jednoduché YAML struktury; nepodporované konstrukce reportovat.
- Kafka payload DTO a explicitní producer/consumer mapping s vyřešeným topicem.
- Frontend HTTP response mapping a explicitní použití hodnot.
- HTML template placeholders a jejich backendové naplnění; template dialect musí být uveden. Začni podporou jednoho fixture dialektu, např. Thymeleaf.
- Externí Bloomberg a PDF služba jako obecné external-system uzly s nalezenými kontrakty, bez domýšlení vnitřního chování.

Pokrytí každého parseru popiš ve capability manifestu a otestuj i negativní případ. Sémantický agent může propojení navrhnout, avšak pouze jako INFERRED s citací.

### 6.3 Scénáře a jednoduché výpočty

Agent může extrahovat koncepty Scenario, Assumption a Calculation pomocí existující sémantické vrstvy. Deterministicky zachyť deklarované konstanty, explicitní parametry, jednoduché výrazy a datové závislosti.

Nevyhodnocuj obchodní správnost vzorce. Pokud zdroj skutečně obsahuje `midDecline = pessimisticDecline / 2`, lze doložit vztah a ukázat následné použití. Bez takové evidence nelze předpokládat poloviční pokles jen podle názvu scénáře.

Zaznamenej explicitně nalezené konverze, precision a rounding jako evidence; nerozšiřuj je automaticky na celý systém.

## 7. Excel jako zdroj znalostí

Přidej offline čtení `.xlsx` přes `zipfile` a XML ze standardní knihovny:

- workbook, sheets, named ranges a vazby buněk;
- vzorce a odkazy mezi sheety pro dokumentované podporované konstrukce;
- explicitní vstupní/výstupní buňky a parametry scénářů;
- cached values oddělené od vzorců a s upozorněním na neznámou aktuálnost;
- lokální mapování workbook cell/range → graph entity s evidence a stavem schválení.

Nepouštěj makra, nevyhodnocuj Excel vzorce a nenačítej externí odkazy. Shared formulas, dynamické odkazy typu INDIRECT, externí workbooky a nepodporované struktury označ unresolved, pokud nejsou implementovány. Binární `.xls` a jiné nepodporované formáty musí mít explicitní diagnostic, nikoliv tiché ignorování.

Parser omezí počet ZIP entries, celkovou rozbalenou velikost a velikost XML. Lokální linky nesmějí uniknout mimo povolené kořeny.

Vzorec v Excelu může být referenční model či schválená metodika. Nesoulad s kódem označ jako k přezkoumání. Číselnou ekvivalenci netvrď bez nezávislého testu. Fixture očekávané hodnoty mají být ručně stanovené, ne odvozené týmž analyzátorem, který se testuje.

## 8. Requirement, availability a proposal graph

Implementuj tři logické pohledy, nikoliv tři povinné databáze:

1. Requirement graph: Feature, Goal, OutputRequirement, InputRequirement, BusinessRule, Constraint, Question.
2. Availability graph: vazby požadavků na skutečné pole, kontrakt, zdroj a transformaci.
3. Proposed change graph: nové a změněné komponenty v rámci analysis ID.

Povinné návrhové vztahy: `requires_input`, `satisfies_requirement`, `reuses_entity`, `proposes_change_to`, `blocked_by`, `depends_on_decision`.

Všechny cíle hran se musí resolvovat do návrhu nebo baseline grafu. Neexistující target není nová implementace; jde o chybný odkaz, který validátor odmítne.

Žádná obecná query, hook ani render AS_IS nesmí implicitně zahrnout návrhy. Pro smíšený pohled vyžaduj konkrétní `--analysis <id>` a viditelně rozlišuj stav.

Alternativy sdílejí baseline, ale mají vlastní návrhové ID, omezení a otázky. Například varianta „bez nového externího API“ musí vyhodnotit, co lze splnit stávajícími nebo klientem dodanými daty; nemá vymyslet dostupné API.

## 9. Workflow analytického agenta

Vytvoř `.github/agents/kgmaker-analyst.agent.md` a jeho instalační template. Agent:

1. Přijme požadavek v češtině nebo angličtině a zachová přesný text.
2. Rozloží jej na strukturované požadavky a označí otázky.
3. Připraví evidence packet a zkontroluje aktuálnost grafu.
4. Vyhledá relevantní existující koncepty, datové toky, kontrakty a testy.
5. Ověří vybrané závěry přímo v citovaných zdrojích.
6. Namapuje požadované vstupy a určí dostupnost i využitelnost.
7. Navrhne minimální změny, varianty a datové dodávky.
8. Zapíše strukturovaný candidate výstup.
9. Spustí deterministickou validaci; při chybě opraví candidate.
10. Vygeneruje report a předá konkrétní otevřené otázky.

Nezastavuj celou analýzu kvůli jedné otázce. Zpracuj nezávislé části a závislé závěry označ UNKNOWN nebo podmíněný návrh.

Přidej analytický routing do existujících Copilot a JetBrains instrukcí. Uživatelský záměr je `/kgmaker analyze-feature`; nejde automaticky o garantovaný nativní CLI command Copilota. Dodej custom agent i JetBrains command file `.junie/commands/kgmaker-analyze-feature.md` a zdokumentuj skutečný způsob invocation pro hosta. Nenaruš stávající `/kgmaker` ani samostatné `semantic extract`.

Analytický agent nemění aplikační kód, migrace ani Confluence. Návrhy mají být předatelné implementačnímu agentovi jako plán s evidence.

## 10. Konkrétní CLI a lifecycle

Přidej následující veřejné kontrakty. Příkazy jsou cílový stav k implementaci:

```bash
kgmaker feature prepare --root . --requirement requirements/new-hedge.md --id additional-hedge --token-budget 8000
kgmaker feature validate --root . --analysis additional-hedge --candidate .kgmaker/analyses/additional-hedge/candidate.json
kgmaker feature apply --root . --analysis additional-hedge --candidate .kgmaker/analyses/additional-hedge/candidate.json
kgmaker feature report --root . --analysis additional-hedge --output docs/generated/features/additional-hedge.md
kgmaker feature status --root . --analysis additional-hedge
kgmaker feature revise --root . --analysis additional-hedge --answers requirements/additional-hedge-answers.json
kgmaker feature compare --root . --analysis additional-hedge --variant no-new-api
kgmaker impact --root . --entity '<existing-graph-id>' --include-data-flow --format json
kgmaker query --root . --analysis additional-hedge 'available liquidity'
```

- `prepare` založí nebo idempotentně připraví revizi a její packet; nevolá model. Bez aktuálního indexu provede potřebný scan nebo oznámí neověřitelný baseline.
- `validate` je read-only a vrací diagnostiky.
- `apply` znovu validuje candidate a atomicky uloží pouze konkrétní analytickou revizi.
- `report` používá validovaný výstup; stale report označí a neprezentuje jako aktuální.
- `status` vypíše stav zdrojů, rozhodnutí, pokrytí a pending práce.
- `revise` přijme strukturované odpovědi s question ID a připraví nový packet. Zachová historii a nezávislé závěry.
- `compare` generuje porovnání doložených variant; variantu nevymýšlí deterministický CLI.
- Zachovej původní `impact FILE [FILE ...]` a `query WORD...`.

Artefakty:

```text
.kgmaker/analyses/<analysis-id>/
  requirement.md
  packet.json
  agent-task.md
  candidate.json
  revisions/<revision>/analysis.json
  current.json
  source-index.json
docs/generated/features/<analysis-id>.md
```

`current.json` odkazuje na platnou revizi; zápis historie je append-only. Machine artefakty jsou defaultně ignorované Gitem, report lze commitovat. Všechny výstupy analýz vyluč ze source scanu, aby nevznikala sebeodkazující evidence.

Analysis ID musí být bezpečný path segment. Nepovoluj traversal, absolutní ID ani přepsání zdrojů pomocí output path. Externí artefakty použij jen z explicitně přidaných kořenů.

Exit codes pro nové příkazy: 0 úspěšné zpracování (i validní neúplná analýza), 1 provozní chyba, 2 nevalidní candidate nebo CLI vstup, 3 stale baseline/packet vyžadující refresh. Stav úplnosti je vždy také ve strojovém výstupu. Přidej `--require-complete`, který vrací 4 pro validní, ale neúplný výstup. Zachovej existující chování starých příkazů.

## 11. Analytický packet a validace

Analytický packet musí být oddělen od semantic change packetů. Analýza nové feature musí fungovat i bez Git diffu a bez předchozího implementation requestu.

Packet obsahuje analysis ID, revision, requirement hash, baseline fingerprint, source manifest, povolené graph ID, evidence inventory, rozpočet a coverage. `packet_id` počítej deterministicky z kanonických vstupů; timestamp nesmí měnit jeho identitu.

Candidate musí uvést stejné packet ID a revizi. Validátor kontroluje:

- verzi, typy, povinná pole, unikátní ID a referenční integritu;
- shodu zadání, packetu, baseline a relevantních source hashes;
- platnost citací a podporu závěrů daným evidence druhem;
- oddělení AS_IS a TO_BE;
- pravidla dostupnosti z kapitoly 5;
- že proposal neprovádí mutaci baseline;
- že každý requirement má řešení, otevřenou otázku nebo explicitní unresolved položku;
- že nepodporované či neprozkoumané oblasti nejsou označeny jako kompletní;
- že tvrzení o implementaci neopírá pouze o business dokument;
- že číselná finanční správnost není deklarována pouhou shodou vzorce.

Při mismatch vypiš konkrétní příčinu a další postup. Opakování prepare nad nezměněným stavem nesmí invalidovat odpovídající candidate. Pokud candidate patří starému packetu, nabídni příkaz k přípravě nové revize; nikdy jej potichu nepřeznač aktuálním packet ID.

Nevalidní apply nesmí změnit ani analýzu, ani AS_IS artefakty. Testuj hashovou shodu před/po.

## 12. Report pro analytika

Report je v jazyce požadavku, obsahuje technické odkazy, ale hlavní text je srozumitelný i bez znalosti tříd.

Povinné části:

1. Business cíl a rozsah.
2. Stav analýzy, baseline a pokrytí.
3. Existující schopnosti a omezení jejich reuse.
4. Tabulka požadovaných dat.
5. Co musí být dodáno a kdo má rozhodnout.
6. Navržené změny podle vrstev.
7. Cesty dopadu a nejistoty.
8. Varianty a jejich předpoklady.
9. Akceptační kritéria a plán testů.
10. Otevřené otázky.
11. Evidence index a pending práce.

Tabulka dat musí obsahovat: vstup, business definici, typ/jednotku, granularitu/čas, dostupnost, zdroj, transformaci, evidence a další krok. Žádná buňka „chybí“ bez rozsahu a zdůvodnění.

Každý návrh změny má requirement ID, vrstvu, existující entity nebo označený nový návrh, důvod, vstupy/výstupy, závislosti a testovací dopad.

Uváděj konkrétní odkazy `path:line` a hash baseline, případně HTML anchor nebo workbook cell. Nedoplňuj vymyšlené řádky ani automaticky vymyšlené veřejné URL.

Doplň tabulku „Co dodat“ s jednotlivými datovými poli a rozhodnutími, nikoliv jen seznamem obecných témat.

Report nesmí říkat „data neexistují“, pokud pouze nebyla nalezena. Report bez semantic candidate je přípustný, ale musí jasně uvést, že obsahuje pouze inventář a neúplnou analýzu.

## 13. Inkrementální aktualizace a změny baseline

Implementuj cache podle source hashes, parser version a relevantní konfigurace.

- Nezměněné soubory znovu neparsuj.
- Změny, nové soubory, odstranění a přejmenování aktualizují uzly, hrany i evidence.
- Změna parseru/config invaliduje dotčené výsledky.
- Rozlišení symbolů musí přepočítat i soubory, jejichž resolution se může změnit novou kolizí názvů.
- Identita závisí na jednoznačně definované relativní cestě a kvalifikovaném symbolu; rename může vytvořit nové ID. Nepřipojuj staré evidence na nové ID bez ověření.

Udržuj reverse index `source/entity → assertions/input matches/impact paths/documentation`.

Změna relevantního zdroje invaliduje navázané závěry. Změna nové entity nebo kontraktu může ovlivnit i dřívější NOT_FOUND_IN_SCOPE: negativní hledání musí mít coverage/query fingerprint a při rozšíření daného inventáře se revalidovat.

Nezměněné závěry zůstávají, změněné se stanou STALE a připraví se omezený analytický packet. Starý report nesmí tvrdit aktuální AVAILABLE z neplatné evidence.

Canonical graf po incremental update musí být ekvivalentní full scanu při stejné konfiguraci; porovnej uzly, hrany, hashes a coverage po vynechání timestampů. To platí pro deterministickou vrstvu. U LLM části ověř stejné invalidace a invariants, nikoliv byte-identický přirozený text.

Scan může přepočítat deterministické dopady; nemá automaticky vyvolávat drahou sémantickou analýzu při každém save. Zachovej možnost spustit samostatnou semantic extraction.

## 14. Token budget a neúplné výsledky

Budget se vztahuje na připravený kontext, ne na skutečné účtování tokenů hostitelského modelu. Uveď použitý odhad a počty zahrnutých/vynechaných zdrojů.

Priorita: deterministická extrakce → field resolution → matching → ověření evidence → sémantický návrh.

- Kontext omezuj podle relevantních entities, výstupů a požadovaných vstupů.
- Nevkládej celý repository nebo HTML export do packetu.
- Zachovej souhrnný manifest pokrytí i při zkrácení textů.
- Při vyčerpání dokonči deterministickou část, ulož pending položky a označ SEMANTIC_PENDING/PARTIAL.
- Zkrácení nesmí být interpretováno jako nepřítomnost dat.
- Validátor nesmí přijmout COMPLETE, pokud existuje nezpracovaný požadavek, unresolved blocker či pending práce potřebná k závěru.
- Opakované spuštění s vyšším budgetem obnoví pending práci bez duplikování návrhů.

Kompletní analýza znamená kompletní zpracování požadavků v deklarovaném rozsahu; může obsahovat otevřené business rozhodnutí. Odděl proto `processing_status` od `decision_readiness` (READY/BLOCKED). Nezaměňuj nalezenou otázku za parserový výpadek.

## 15. Autorita kódu, požadavků a dokumentace

Odděl dvě osy:

1. „Jak je to nyní implementováno?“ — primárně současný kód a deterministicky odvozené artefakty.
2. „Jak to má fungovat?“ — schválené požadavky a metodiky s explicitní verzí a stavem schválení.

Dokumentační business informace neověřitelná z kódu zůstává NOT_VERIFIABLE_FROM_CODE. Rozpor současného chování s výslovně schválenou metodikou je IMPLEMENTATION_VS_APPROVED_REQUIREMENT a vyžaduje review; nesmí být automaticky prohlášen za chybu dokumentace.

Bez doloženého schválení používej stav UNAPPROVED/UNKNOWN. Ani kód, ani Excel, ani název Confluence stránky nemohou sami dokazovat finanční správnost.

Ponech stávající report `docs/generated/confluence-inconsistencies.md`. Feature report odkáže na související rozpory, ale neodstraní je ani neopraví zdrojové HTML, diagramy či workbooky.

## 16. Volitelná Confluence synchronizace

Online synchronizace je samostatný adapter a pozdější implementační milník; nesmí blokovat analytické jádro. Samotný offline export neumožňuje tvrdit, že byla implementována synchronizace.

Definuj adapter rozhraní:

- `pull`: načtení explicitně vybraných pages a attachments s page ID a verzí do lokálního read-only snapshotu;
- `propose`: vytvoření publikačního balíčku, diffu a mapování report sections na spravované části stránky;
- `publish`: odeslání konkrétního schváleného balíčku s kontrolou aktuální page version.

První implementační krok adapteru je interface + fake adapter pro acceptance tests. Reálný adapter se implementuje jen proti doloženému dostupnému Confluence hostu/verzi a ověřenému API. Agent nesmí vymyslet univerzální Cloud/Server endpoint nebo způsob autentizace. Pokud přístup chybí, dokonči offline část a reportuj přesný blocker synchronizačního milníku.

Publikační workflow: lokální návrh → diff → explicitní schválení konkrétního payload hash/base version → publikování. Schválení jednoho payloadu neplatí pro jeho pozdější změnu. Optimistic concurrency při změně stránky vrací konflikt a vyžaduje nový diff.

Piš jen do explicitně spravované stránky nebo sekce; zachovej ostatní obsah. Nepřepisuj business metodiky a zdrojové dokumenty automaticky podle grafu. Uchovávej audit výsledku, page ID, původní/novou verzi a payload hash bez tajných údajů.

Publikované TO_BE musí zůstat návrhem, nesmí se po následném pull stát potvrzeným AS_IS. Importovaný snapshot neposkytuje důkaz, že feature byla implementována.

## 17. Moduly a kompatibilita

Doporučená struktura:

| Modul | Odpovědnost |
|---|---|
| `analysis_model.py` | Kontrakty požadavků, dostupnosti, proposal, evidence a coverage |
| `dataflow.py` | Konzervativní extrakce polí a toků hodnot |
| `workbooks.py` | Bezpečná offline XLSX extrakce |
| `feature.py` | Prepare, revise, status, matching a packet lifecycle |
| `analysis_validation.py` | Deterministická validace candidate |
| `analysis_report.py` | Deterministický Markdown/JSON výstup |
| `incremental.py` | Cache a invalidace |
| `confluence_sync.py` | Volitelný adapter boundary, fake a publikační balíčky |

Integruj do stávajícího `cli.py`, `store.py`, `domain.py` a modelu bez zbytečného přepisu.

Přidej schema version migration pro staré grafy a sémantické artefakty. Nová metadata mají bezpečné defaulty; starší evidence bez potřebné informace zůstává neověřená. Novější neznámou verzi odmítni s konkrétní diagnostikou. Otestuj načtení existujícího formátu a zachování starých commands.

Aktualizuj README, architecture, project-scope, generované agent templates a `init`. Přidání nových agent souborů musí být idempotentní a respektovat současné zachování uživatelských souborů bez `--force`.

Pokud změna implementace změní graph snapshots sledované v Gitu, přegeneruj je standardním CLI a ověř `kgmaker check`.

## 18. Fixture pro celý analytický scénář

Přidej `fixtures/feature-analysis/` se syntetickými daty:

```text
backend/
  ScenarioCalculator.kt
  ExposureService.kt
  HedgeRecommendationService.kt
  ExternalHedgeDto.kt
  ReportDto.kt
  MarketDataClient.kt
  PdfClient.kt
  PositionConsumer.kt
db/
  V001__positions.sql
contracts/
  exposure-api.json
  positions-event.json
frontend/
  ExposureView.tsx
templates/
  client-report.html
workbooks/
  scenarios.xlsx
confluence-export/
  index.html
  Hedge-Methodology.html
requirements/
  additional-hedge.md
  additional-hedge-answers.json
expected/
  coverage.json
  analysis-invariants.json
  candidate-valid.json
  candidate-invalid.json
```

Fixture backend obsahuje explicitní datový tok a jednoduché scénáře. Externí pozice mají objem a měnu, avšak chybí požadovaná splatnost v dodaném kontraktu. Pole `accountBalance` nesmí být automaticky považováno za `availableLiquidity`. PDF klient je externí hranice s dostupným kontraktem, nikoliv interním zdrojovým kódem.

Požadavek:

> Doporuč klientovi dodatečné FX zajištění tak, aby očekávaná expozice v pesimistickém scénáři nepřesáhla 20 % disponibilních prostředků. Zohledni externí bankovní pozice a zobraz doporučení v UI i PDF.

Připrav druhou variantu „bez nového externího API“ a odpovědi definující disponibilní prostředky. Tento text je syntetický test požadavku, nikoliv finanční doporučení nebo schválená bankovní metodika.

## 19. Závazné akceptační testy

Testy běží offline pomocí existujícího unittest workflow. Nevyžadují Copilot, model API ani živý Confluence. Použij připravené agent candidate artefakty; testy nesmějí měřit doslovné znění LLM odpovědi.

| ID | Situace | Požadovaný výsledek |
|---|---|---|
| FA-01 | Existing input má doložený source → DTO → calculation tok | AVAILABLE s evidence a použitelností |
| FA-02 | Pole nebylo nalezeno a část systému není dodána | NOT_FOUND_IN_SCOPE/UNKNOWN s coverage, nikdy globální neexistence |
| FA-03 | Externí pozice mají objem a měnu, chybí splatnost kontraktu | PARTIAL, přesný požadavek na nové pole a dopad na kontrakt |
| FA-04 | Account balance má podobný název jako dostupná likvidita | Žádné automatické ztotožnění; business otázka |
| FA-05 | Odvoditelná hodnota má chybějící dependency | Není AVAILABLE; blocker a conditional derivation |
| FA-06 | Dvě derivace tvoří cyklus bez vstupu | Cyklus hlášen, dostupnost neprokázána |
| FA-07 | Nová feature přidává metriku a pole | Vše je TO_BE; hash AS_IS grafu i semantic artefaktu stejný před/po apply |
| FA-08 | Výpočet se používá v DTO, UI a šabloně | Impact paths pokryjí podporovanou cestu a označí PDF external boundary |
| FA-09 | Dvě třídy sdílejí název | Ambiguous edge nesmí potvrdit reuse ani datovou cestu |
| FA-10 | Candidate cituje neexistující řádek/field nebo špatný hash | Validace selže; žádná mutace |
| FA-11 | Candidate má jiný packet ID/revision | Diagnostika mismatch a zachování aktuální analýzy |
| FA-12 | Prepare se opakuje nad identickými vstupy | Stejné packet ID, stále použitelný candidate |
| FA-13 | Requirement nebo relevantní working-tree file se změní | Starý candidate nelze aplikovat; cílená invalidace |
| FA-14 | Změní se nesouvisející zdroj | Relevantní evidence zůstává použitelná; baseline update se vysvětlí bez hromadné invalidace |
| FA-15 | Přidá se nový zdroj dříve nenalezeného vstupu | Negativní lookup se revaliduje a lze jej změnit na AVAILABLE |
| FA-16 | Odpověď na otázku upřesní likviditu | Nová revize, zachovaná historie, aktualizované závislé závěry |
| FA-17 | Varianta zakáže nové API | Report popíše alternativu i omezení; nevymyslí zdroj |
| FA-18 | Dojde budget | Deterministický report vznikne; pending práce je explicitní |
| FA-19 | Malý budget vynechá source, kde data existují | Výsledek UNKNOWN, nikoliv CONFIRMED_MISSING |
| FA-20 | Pravdivé / zastaralé / business Confluence tvrzení | Zachování VERIFIED, CONTRADICTED a NOT_VERIFIABLE odlišení |
| FA-21 | Implementace odporuje doložené schválené metodice | IMPLEMENTATION_VS_APPROVED_REQUIREMENT, bez automatické opravy |
| FA-22 | XLSX obsahuje vzorce mezi sheety a named range | Dependency evidence se sheet/cell lokalizací |
| FA-23 | XLSX obsahuje INDIRECT/externí link/makro či nepodporovaný XLS | Explicitní unresolved/diagnostic; žádná síť ani spuštění |
| FA-24 | Update zahrnuje add/change/delete/rename/kolizi | Canonical deterministic graph shodný s full scanem |
| FA-25 | Analýza běží bez diffu a bez semantic change packetu | Prepare → candidate → apply → report funguje |
| FA-26 | Není Confluence ani Excel ani frontend | Backendová analýza funguje s popsanou coverage |
| FA-27 | Output má traversal nebo návrh dangling reference | Odmítnutí bez změny souborů |
| FA-28 | Fake Confluence page version se změní po approval | Publish konflikt, žádný overwrite |
| FA-29 | Publikační payload se změní po approval | Původní approval neplatí |
| FA-30 | Pull stáhne publikovaný návrh | TO_BE není povýšeno na AS_IS |
| FA-31 | Staré grafy/semantic artefakty a staré příkazy | Kompatibilní načtení a dosavadní chování |
| FA-32 | Init podruhé při upravených uživatelských agent files | Idempotence a zachování změn |
| FA-33 | Analýza vygeneruje vlastní report | Report není nascanován jako nezávislý důkaz |
| FA-34 | Question je vyřešena, parser nemá pending, ale business approval chybí | Processing COMPLETE, decision_readiness BLOCKED |
| FA-35 | Změna vstupu jde přes derived_from | Dopad jde na odvozené výsledky, ne svévolně na všechny sousedy |

Kromě fixture testů dodej end-to-end CLI test prepare/validate/apply/report/revise a test nulové mutace při chybě. Mock LLM má dodávat strukturované candidate, ne zázračně potvrzovat dostupnost.

## 20. Pořadí implementace a definition of done

### Milník A — analytické jádro

Model, provenance, coverage, isolation, packet lifecycle, CLI, validator a report. Připravené candidate fixtures umožňují celý proces bez LLM. FA-02/04/07/10–13/18–19/25–27/31/33–34 procházejí.

### Milník B — datové toky a matching

Field nodes, podporované mappingy, směrovaný impact, datová použitelnost, external boundaries a důkazy. FA-01/03/05–06/08–09/17/35 procházejí. Report umí skutečně vypsat „co dodat“.

### Milník C — artefakty a dokumentace

XLSX, šablony, Confluence kontext a autorita požadavků. FA-20–23/26 procházejí. Omezení parserů jsou zdokumentovaná a viditelná v coverage.

### Milník D — incremental a host agent

Inkrementální extrakce, reverse indexes včetně negativních lookupů, revise, Copilot analyst agent a JetBrains routing. FA-14–16/24/32 procházejí.

### Milník E — synchronizační boundary

Adapter interface, fake adapter, publikační diff/approval/concurrency a testy FA-28–30. Reálné připojení je samostatně reportovaný integration deliverable s doloženým hostem a API; fake adapter není živá synchronizace.

Analytické jádro je dokončeno až po milnících A–D. Kompletní rozsah tohoto zadání zahrnuje také E, s explicitně uvedeným stavem reálné Confluence integrace.

Před předáním:

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
kgmaker check
```

Proveď fixture CLI workflow a dolož cestu k vygenerovanému analytickému reportu. Aktualizuj dokumentaci a veřejné příklady. U testovacích plánů pro cílový projekt rozliš skutečně nalezené testy od nově navržených testů.

Závěrečný implementační report musí uvést hotové milníky, validaci, podporované vzory, nepokryté oblasti a konkrétní integration blockers. Neprezentuj prompt, fake adapter, heuristickou cestu nebo neúplné coverage jako dokončenou přesnou analýzu.

## 21. Očekávaný výsledek pro analytika

Po zadání nové funkce má vzniknout konkrétní, zdrojově doložený plán:

- které současné funkce lze využít a za jakých podmínek;
- které metody, pole, kontrakty, tabulky, zprávy, UI a šablony je nutné změnit;
- jaká data dodat, v jaké podobě a s jakým časovým/jednotkovým významem;
- které vstupy jsou použitelné, částečné, odvoditelné, nenalezené nebo neověřené;
- co musí business rozhodnout před implementací;
- které existující testy a nové akceptační scénáře ověří změnu;
- které závěry jsou potvrzené, které jsou návrhem a kde analýza končí.

Základní invariant: **KGMAKER nesmí zaměnit navrženou budoucnost za současnou implementaci ani neúplné hledání za důkaz neexistence dat.**
