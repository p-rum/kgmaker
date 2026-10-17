# Implementační pokračování: analýza nových funkcí a datových požadavků

**Task ID:** `T001`. **Revision:** 1 (normalizace 2026-10-15). **Stav:** SPECIFICATION.
**Baseline:** původní požadavky zachovány; stav implementace se hodnotí vůči `6b5aea1`. Normativní požadavky; nejde o popis hotové implementace.
**Číslování:** [registr a převod historických označení](README.md). Historická ID testů v tomto dokumentu cituj s prefixem `T001-` (např. `T001-FA-01` podle existujícího scénáře); čísla kapitol nejsou ID etap.
**Aktuální stav:** [inventura](../production-analysis-progress.md).
**Pořadí dokončení:** [T003](3_finishProductionAnalysis.md); všechny zdejší požadavky zůstávají zachovány.

Datum: 2026-10-09
Poslední doplnění: 2026-10-12 (Flyway a multirepo, kapitoly 22–26)
Stav: závazné zadání rozšíření, nikoliv popis již implementovaných schopností
Cílový projekt: `p-rum/kgmaker`
Navazuje na: [README](../../README.md), [project-scope](../project-scope.md), [architecture](../architecture.md)

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
- Frontend a automatické testy mohou mít vlastní repozitáře. Jejich explicitně dodané checkouty propojuj s backendem podle kapitol 24–26; nedodané repozitáře označ jako nepokryté.
- PostgreSQL schéma rekonstruuj z Flyway migrací podle kapitoly 23, včetně ALTER, rename, drop a vybraného targetu.
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

Nevytvářej matematický důkazní engine, finanční validátor, runtime instrumentaci ani povinnou distribuovanou grafovou službu. Lokální propojení explicitně dodaných backend/frontend/test repozitářů je povinné rozšíření podle kapitol 24–26. Sleduj původ a použití hodnot a přiznávej hranice statické analýzy.

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

Python testy běží offline přes pytest (spouští i existující unittest test cases); závislosti se instalují explicitně před během. Nevyžadují Copilot, model API ani živý Confluence. Použij připravené agent candidate artefakty; testy nesmějí měřit doslovné znění LLM odpovědi.

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

### T001-S01 (historicky A) — analytické jádro

Model, provenance, coverage, isolation, packet lifecycle, CLI, validator a report. Připravené candidate fixtures umožňují celý proces bez LLM. FA-02/04/07/10–13/18–19/25–27/31/33–34 procházejí.

### T001-S02 (historicky B) — datové toky a matching

Field nodes, podporované mappingy, směrovaný impact, datová použitelnost, external boundaries a důkazy. FA-01/03/05–06/08–09/17/35 procházejí. Report umí skutečně vypsat „co dodat“.

### T001-S03 (historicky C) — artefakty a dokumentace

XLSX, šablony, Confluence kontext a autorita požadavků. FA-20–23/26 procházejí. Omezení parserů jsou zdokumentovaná a viditelná v coverage.

### T001-S04 (historicky D) — incremental a host agent

Inkrementální extrakce, reverse indexes včetně negativních lookupů, revise, Copilot analyst agent a JetBrains routing. FA-14–16/24/32 procházejí.

### T001-S05 (historicky E) — synchronizační boundary

Adapter interface, fake adapter, publikační diff/approval/concurrency a testy FA-28–30. Reálné připojení je samostatně reportovaný integration deliverable s doloženým hostem a API; fake adapter není živá synchronizace.

Analytické jádro je dokončeno až po milnících A–D a nově F–G podle kapitoly 26. Kompletní rozsah tohoto zadání zahrnuje také E, s explicitně uvedeným stavem reálné Confluence integrace.

Před předáním:

```bash
python -m pip install -e . pytest==8.3.4
python -m pytest -q
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

## 22. Doplnění scope: Flyway a workspace více repozitářů

Doplněno: 2026-10-12. Kapitoly 22–26 jsou závazným rozšířením předchozích kapitol. V případě konfliktu mají přednost v otázkách Flyway a multirepo. Nemění zákaz automatických aplikačních změn analytickým agentem.

Primární backend může zůstat v jednom repository, ale KGMAKER musí umět společný analytický workspace:

- backend repository včetně Flyway migrací;
- samostatný frontend repository;
- samostatný repository automatických integračních, kontraktních a end-to-end testů.

Nejde o povinnou vzdálenou službu nebo neomezený distribuovaný graf. Jde o lokální sjednocený pohled nad explicitně nakonfigurovanými checkouty. Jednorepozitářový režim musí fungovat beze změny a bez workspace konfigurace.

## 23. Rekonstrukce databázového schématu z Flyway migrací

### 23.1 Cíl a hranice tvrzení

KGMAKER nesmí pouze vyhledat CREATE TABLE ve všech SQL souborech a sloučit nalezené sloupce. Musí rekonstruovat výsledné schéma pro konkrétní migration stream, profil a target version pomocí pořadí a účinků migrací.

Rozlišuj:

- MIGRATION_DERIVED: deklarované výsledné schéma odvozené z dodaných migračních souborů;
- DEPLOYMENT_VERIFIED: stav doložený explicitně dodaným deployment/history snapshotem, pouze v rozsahu této evidence;
- PARTIAL/UNKNOWN: neúplná historie, unresolved placeholders, nepodporované SQL či programové migrace.

Soubor v repository není důkaz, že migrace běžela v produkci. Ani úplné rekonstruované schéma nedokazuje přítomnost konkrétních dat, oprávnění aplikace nebo naplňování sloupce. Dostupnost vstupů dál podléhá kapitole 5.

Výchozí režim je offline a read-only. Nespouštěj Flyway, SQL, Java migrace, build skripty ani DB připojení. Volitelný import již existujícího schema/history snapshotu musí mít vlastní provenance; není součástí povinného živého napojení.

### 23.2 Discovery a konfigurace

Podporuj běžný kořen `src/main/resources/db/migration`, explicitní lokální locations a konzervativní čtení doložené konfigurace v Spring properties/YAML, Flyway properties/TOML a jednoduchých Gradle/Maven nastaveních. Nevyhodnocuj build skripty.

CLI/workspace konfigurace má přednost před konkrétním vybraným profilem projektu a standardním defaultem. Rozporné nebo dynamické nastavení je otázka/diagnostic, nikoliv hádání.

Eviduj:

- repo ID, database logical ID a migration-stream ID;
- dialect PostgreSQL, locations, vybraný profil a zdroj konfigurace;
- prefixy, separator, suffixes, schemas/defaultSchema;
- target version, deklarovaný počáteční schema snapshot/baseline;
- explicitně poskytnuté placeholders a jejich provenance;
- verzi parseru a podporovanou Flyway konvenci.

Neskenuj tajné hodnoty a nezapisuj connection passwords do grafu/packetů. Nepoužívej automaticky environment proměnné k dohledávání credentials. Classpath locations mapuj jen na doložené lokální resources; nepřístupný JAR nebo remote location musí zůstat nepokrytý.

Každý migration stream má vlastní konfiguraci a version ordering. Shodné verze v různých streamech nejsou kolize. Kombinování streamů do jedné databáze vyžaduje explicitní pořadí/kontrakt; jinak nevytvářej falešně jednoznačný výsledný stav.

### 23.3 Plán migrací

Zpracuj versioned SQL migrations podle Flyway version ordering, nikoliv lexikografického názvu souboru: fixture musí otestovat pořadí V2 před V10 a normalizované varianty verzí. Duplicate/equivalent version v jednom streamu je chyba plánu.

Repeatable migrace eviduj odděleně. Pro model čisté instalace aplikuj podporovaný aktuální repeatable obsah po vybraných versioned migracích, v pořadí popisu. Takový model není rekonstrukcí historických opakovaných běhů. Pro historický target bez historických repeatable souborů označ tuto část UNKNOWN.

Rozpoznej baseline migrations, undo migrations a callbacks jako odlišné typy. Undo neaplikuj do forward reconstruction. Baseline migration script není totéž jako baseline marker v historii. Podporuj jednoznačně nakonfigurovaný režim čistého bootstrapu z baseline scriptu nebo dodaného počátečního snapshotu; nejasná volba musí bránit tvrzení COMPLETE.

Historie, ve které nejsou číselně sousední verze, není automaticky neúplná. Neúplnost stanov podle deklarované počáteční báze, inventory, chybějících referencí nebo dodané historie, nikoliv pouhé mezery v číslech.

Out-of-order execution, cherry-pick, callbacks měnící schéma, Java/Kotlin migrations a podmíněné deployment kroky vyžadují doložený execution plan. Bez něj vytvoř inventory a partial model; nepředstírej simulaci skutečného nasazení. Načtený history snapshot uchovej s verzemi/checksums; SHA-256 zdrojů KGMAKERu nesmí být zaměněn za checksum algoritmus Flyway.

Konkrétní pravidla pro podporovanou Flyway verzi musí implementující agent ověřit podle oficiální dokumentace a otestovat. Referenční zdroje:

- [Versioned migrations](https://documentation.red-gate.com/flyway/flyway-concepts/migrations/versioned-migrations)
- [Repeatable migrations](https://documentation.red-gate.com/flyway/flyway-concepts/migrations/repeatable-migrations)
- [Migrations](https://documentation.red-gate.com/flyway/flyway-concepts/migrations)

### 23.4 SQL parsing a výsledný schema model

Implementuj lexer/statement splitter respektující comments, quoted identifiers, string literals a PostgreSQL dollar-quoted bodies. Nestav replay pouze na regexu rozdělujícím SQL podle středníku.

Minimální podporované strukturální operace:

- CREATE/ALTER/DROP SCHEMA a TABLE;
- ADD/DROP/RENAME COLUMN a RENAME TABLE;
- změna column type, nullability a default;
- PRIMARY KEY, FOREIGN KEY, UNIQUE, CHECK, jejich přidání/odstranění;
- CREATE/DROP INDEX a jednoduchý ALTER/rename indexu;
- CREATE/REPLACE/DROP VIEW pro podporované SELECT projekce;
- sekvence a explicitní vazby/defaulty, pokud je parser umí doložit.

DDL aplikuj v pořadí statements. Respektuj schemas a quoted identifiers; neztotožni různě kvalifikované názvy. Search path nebo default schema musí mít evidence, jinak je resolution ambiguous. IF EXISTS/IF NOT EXISTS nesmí inventovat neexistující objekty.

Udržuj entity Database, Schema, Table, Column, Constraint, Index, View, Sequence, Migration a MigrationOperation. Ke každému objektu eviduj lifecycle, origin migration, poslední změnu, účinný typ/constraints a statement/line evidence. Odstraněné objekty patří do historického pohledu, ne do současné nabídky vstupů. Rename uchová prokazatelnou vazbu identity a historii starých názvů.

Vazby například: `migration_changes` Migration → Operation, `operation_targets` Operation → DB object, `foreign_key_to` Constraint → referenced columns, `view_derived_from` View field → source column, `persisted_in` backend field → DB column. Rozlišuj aktuální schema view a historické migration operations, aby impact nezahrnul každý historický sloupec.

DML eviduj jako data transformation/backfill, nikoliv jako potvrzení aktuálních klientských dat. Funkce, triggers, dynamický SQL a DO blocks jsou minimálně explicitní artefakty s unresolved účinky, pokud nejsou podporované. Nepodporovaný statement, který může měnit schéma, musí zneplatnit důvěru v dotčené objekty; nelze-li rozsah určit, označ celý stream PARTIAL. Další známé operace lze zpracovat, ale jejich předpoklady musí být viditelné.

### 23.5 Feature analysis a inkrementální replay

Analytický report musí ukázat:

- zda potřebné pole existuje ve vybraném rekonstruovaném schématu;
- odkud pochází, zda bylo přejmenováno/odstraněno a v jaké verzi;
- zda backend mapping, nullability, precision/scale a typ souhlasí;
- návrh nové migrace jako TO_BE včetně backfill a compatibility otázek;
- dopady na views, constraints, backend DTO/API, frontend a externí testy.

Změna staré migrace invaliduje její replay checkpoint a všechny následné relevantní operace. Nový target/config/baseline/placeholder rovněž mění fingerprint. Inkrementální replay z posledního platného checkpointu musí být ekvivalentní full replay. Změnu již sdílené/aplikované migrace označ k review; agent má navrhovat novou dopřednou migraci, ne automaticky přepisovat historii.

## 24. Multirepo workspace: backend, frontend a automatické testy

### 24.1 Explicitní lokální konfigurace

Přidej versionovaný workspace manifest, např. `kgmaker.workspace.json`. JSON zachovává dependency-free runtime.

```json
{
  "schema_version": 1,
  "workspace_id": "client-financial-health",
  "repositories": [
    {
      "id": "backend",
      "role": "backend",
      "path": "../client-backend",
      "flyway": {
        "database_id": "client-db",
        "stream_id": "main",
        "locations": ["src/main/resources/db/migration"],
        "dialect": "postgresql",
        "target": "latest"
      }
    },
    {
      "id": "frontend",
      "role": "frontend",
      "path": "../client-frontend"
    },
    {
      "id": "acceptance-tests",
      "role": "automated-tests",
      "path": "../client-acceptance-tests"
    }
  ],
  "services": [
    {
      "id": "financial-health-api",
      "backend_repo": "backend",
      "frontend_repos": ["frontend"],
      "test_repos": ["acceptance-tests"],
      "contract": {
        "repo_id": "backend",
        "path": "contracts/exposure-api.json"
      },
      "consumer_path_prefix": "/api",
      "provider_path_prefix": ""
    }
  ]
}
```

Cesty jsou relativní k manifestu, explicitně schválené source roots. Prefix mapping je deklarovaná transformace consumer path → provider path, ne obecné odstranění libovolného prefixu. Ověř jednoznačnost.

Nesmí se automaticky prohledávat všechny sousední složky, klonovat nebo pullovat repozitáře, měnit branches ani spouštět jejich testy. Uživatel dodá checkouty/artefakty. Nedostupné repo se uvede v coverage; ostatní analýza pokračuje. Duplicitní repo ID, překrývající se kořeny nebo nesoulad deklarované identity vyžadují diagnostiku.

Příkazy mají přijmout `--workspace PATH` pro scan/build/update/status/query/impact/docs a feature prepare/validate/apply/report/revise/compare. `--root` s workspace určuje výstupní/koordinační kořen, nikoliv implicitní další repository. Pravidla musí být stejné ve všech commands a zdokumentovaná.

### 24.2 Globální identita a baseline

Federuj lokální grafy do workspace graphu bez destruktivního přepisování source repo artefaktů.

- Globální ID obsahuje repo ID a lokální graph ID; escaping musí být jednoznačný.
- Stejné `src/model.ts`, symbol `Client` či endpoint path ve dvou repozitářích nesmí kolidovat.
- Shared service/contract IDs jsou explicitní workspace entity, nikoliv automatické sloučení podle názvu.
- Evidence obsahuje repo ID + relativní path + hash + location.
- Baseline je mapa repo ID → commit/dirty fingerprint/inventory + manifest hash, nikoliv jeden commit.
- Ověř před i po přípravě packetu, že se zdroje nezměnily během čtení. Smíšený snapshot odmítni nebo obnov.
- Commit kombinace mohou být odlišné release verze; report nesmí tvrdit deployment compatibility bez doloženého release mappingu.
- Pokud chybí repo, nikdy neoznač celou workspace coverage COMPLETE.
- Zachovej staré single-repo IDs v původním režimu; federace použije wrapper/mapování a versionovaný kontrakt.

Cache a reverse index jsou kvalifikované repo ID. Změna jednoho repa může invalidovat cross-repo vazby i závěry v jiném, ale nezměněné soubory se znovu neparsují. Přidání dříve chybějícího repa revaliduje negativní hledání.

### 24.3 Backend ↔ frontend

Podporuj dohledání backend endpoint → API response/request fields → frontend client/type → state/selector → component/display v rozsahu podporovaných vzorů.

Matching vyžaduje service identity, HTTP method, normalizovanou path, případně operation ID a contract field pointer. Path parameter names lze normalizovat jen v dokumentovaném tvaru, nikoliv slučovat různé endpoints podle podobnosti. GraphQL/custom protocols zůstávají unresolved, pokud nejsou implementované.

Generated API clients eviduj přes původní kontrakt a generation metadata. Nepovažuj generovaný TypeScript typ za nezávislou potvrzující evidence téhož kontraktu. Závislost kontrakt → generated artifact → consumer je platný impact vztah i při vyloučení velké generated directory.

Ověř field-level rozdíly: missing/renamed field, type/nullability změna, consumer očekává jinou contract version. Runtime URL a proxy konfigurace musí mít evidence nebo explicitní manifest mapping.

U UI selectorů a data-testid propojuj jen jednoznačné odkazy; dynamické CSS/text selectors jsou kandidáti. Výstup musí ukazovat, které frontendové soubory a obrazovky vyžadují změnu, nebo kde cesta končí.

### 24.4 Repository automatických testů

Zahrň samostatné test repository do inventáře a impactu. Minimální podporované fixtures:

- TypeScript Playwright test: request/client call, locator/data-testid a explicitní assertions;
- JVM JUnit + REST Assured nebo jednoznačný HTTP test client;
- sdílené fixtures, test data builders, helpers a explicitní kontraktní soubory.

Dále rozpoznej ostatní test/config soubory jako inventory; nepodporovaný framework nesmí vést k závěru „testy neexistují“.

Modeluj TestCase, TestSuite, TestFixture, TestHelper a TestAssertion s lokalizací a hranami:

| Vztah | Směr a použití |
|---|---|
| `tests_endpoint` | Test → backend endpoint, doložený request |
| `asserts_field` | Assertion → contract/output field |
| `targets_ui` | Test locator → jednoznačný UI element |
| `uses_fixture` | Test/helper → fixture |
| `depends_on_contract` | Test/client → konkrétní contract version |
| `validates_requirement` | Test → requirement, pouze doložené mapování |

Samotný HTTP call dokazuje volání endpointu, nikoliv ověření všech jeho polí. Neztotožňuj přítomnost testu s tím, že projde nebo dostatečně pokrývá pravidlo. Přítomnost assertions je statická evidence; skutečný PASS/FAIL vyžaduje explicitně dodaný aktuální test-run report s commit/config/environment provenance.

Impact musí dohledat přes helpers/fixtures testy dotčené změnou DTO, kontraktu, scénáře, schématu nebo UI. Test data/setup SQL posuzuj proti rekonstruovanému Flyway schématu; chybějící sloupec ve fixture je rozdíl v dané baseline, nikoliv automatický důkaz produkční chyby.

Report rozliší existující relevantní testy, kandidátní vazby, návrhy nových testů a nepokrytá pravidla. Uváděj přesný repo/path/test ID a navržený command odvozený z doloženého build/test configu; bez configu označ command jako návrh. Analytický workflow testy nespouští. Zejména E2E může zapisovat do externích systémů.

### 24.5 Cross-repo návrh změn a report

Pro novou feature uveď tabulku po repozitářích: změny backendu a migrací, API kontraktu, frontendu, automatických testů, shared fixtures a dokumentace.

Příklad podporované cesty:

`Flyway Column → backend field → calculation → API response → frontend display → E2E assertion`

Každý krok musí mít vlastní evidence a repo ID. Report musí ukázat compatibility/deployment otázky: provider před consumerem, přechodná nullability, verze kontraktu, backfill a úpravy test dat. Tyto kroky jsou návrh rollout plánu, nikoliv automatické nasazení.

Návrh TO_BE je jeden analysis scope s cross-repo change items; apply jej nesmí zapisovat jako implementovaný stav do žádného source repository. Jeden globální budget prioritizuje relevantní data napříč repy a vykazuje vynechané oblasti zvlášť za každé repo.

## 25. Nové CLI, fixtures a akceptační testy

Cílové příkazy navazující na kapitolu 10:

```bash
kgmaker scan --workspace kgmaker.workspace.json
kgmaker update --workspace kgmaker.workspace.json
kgmaker schema inspect --workspace kgmaker.workspace.json --repo backend --stream main --target latest --format json
kgmaker schema diff --workspace kgmaker.workspace.json --repo backend --stream main --from 2 --to 10 --format json
kgmaker feature prepare --workspace kgmaker.workspace.json --requirement requirements/new-hedge.md --id additional-hedge
kgmaker impact --workspace kgmaker.workspace.json --entity '<workspace-graph-id>' --include-data-flow --format json
kgmaker feature report --workspace kgmaker.workspace.json --analysis additional-hedge --output docs/generated/features/additional-hedge.md
```

`schema inspect` vypíše reconstruction mode, konfiguraci, účinné objekty, migration evidence a nevyřešené operace. `schema diff` porovná dva deklarované schema targets, ne živé databáze. Unknown repeatable/historical stav nesmí být prezentován jako přesný diff.

Přidej syntetický `fixtures/multirepo-analysis/` se třemi samostatnými lokálními Git checkouty vytvořenými testem (bez síťových clone), workspace manifestem a backend migracemi V1/V2/V10 + repeatable view. Repo fixtures musí obsahovat shodné relative paths/symbol names pro test kolizí.

Migrace vytvoří tabulku, přidají/změní/přejmenují/odstraní sloupce a view. Frontend používá explicitní API field a data-testid. Test repository obsahuje Playwright assertion, HTTP assertion a shared fixture/helper. Expected výsledné schéma a vazby stanov ručně, nikoliv týmž parserem.

Rozšiř kapitolu 19 o následující závazné testy:

| ID | Situace | Požadovaný výsledek |
|---|---|---|
| FA-36 | Flyway V1, V2, V10 s ALTER | Správné version ordering a výsledné schéma, ne union CREATE TABLE |
| FA-37 | Rename/drop column/table | Nový aktuální název, historická evidence; dropped objekt nenabízen jako dostupný |
| FA-38 | Repeatable view a historický target | Čistý bootstrap podle deklarovaného plánu; historické omezení explicitní |
| FA-39 | Duplicate/equivalent version v jednom streamu | Chyba plánu; žádné COMPLETE schema |
| FA-40 | Placeholders, search_path a profil | Správná explicitní konfigurace; unresolved hodnoty označí partial |
| FA-41 | Java migration/DO block/unknown callback | Inventory a neznámé schema účinky, žádné spouštění |
| FA-42 | Citované schema pole existuje jen v unapplied migration | MIGRATION_DERIVED, nikoliv DEPLOYMENT_VERIFIED nebo potvrzení naplnění dat |
| FA-43 | Změna staré migrace nebo baseline | Invalidation následujících checkpoints, incremental = full replay |
| FA-44 | Numerická mezera mezi validními verzemi | Žádná automatická diagnóza chybějící historie |
| FA-45 | Sloupce/types/constraints/views proti backend mappingu | Konkrétní mismatch s oběma evidence a target version |
| FA-46 | Backend/frontend/tests mají stejný path/symbol | Nekolidující ID a repo-qualified citace |
| FA-47 | Backend field → FE display → E2E assertion | Vysvětlená cross-repo impact cesta |
| FA-48 | HTTP path shodný u dvou služeb | Bez service identity žádná potvrzená vazba |
| FA-49 | Manifest proxy prefix/generated client | Prokazatelné mapování a původ kontraktu, ne falešné nezávislé potvrzení |
| FA-50 | Test volá endpoint, ale neassertuje změněné pole | Relevantní test candidate, nikoliv potvrzené pokrytí pole |
| FA-51 | Shared helper/fixture ovlivní několik testů | Tranzitivní test dopad s evidence |
| FA-52 | Chybí FE/test checkout či nesedí release baseline | Analýza pokračuje, explicitní coverage/compatibility unknown |
| FA-53 | Změní se jen FE nebo test repo | Cílená invalidace cross-repo závěrů bez reparsu backendu |
| FA-54 | Candidate cituje správný path/hash, ale špatné repo ID | Validace odmítne; žádná mutace |
| FA-55 | TO_BE obsahuje migraci, FE i test změny | Žádný source repo/AS_IS artefakt se při feature apply nezmění |
| FA-56 | Test-run report chybí nebo je stale | Žádné tvrzení PASS nebo ověřeného runtime pokrytí |
| FA-57 | Workspace scan a report | Nulové síťové clone/pull, DB queries, execution migrací a E2E |
| FA-58 | Sources se mění během packet preparation | Smíšená baseline odmítnuta nebo bezpečně obnovena |
| FA-59 | Odstranění repo nebo nový dříve chybějící checkout | Žádné dangling potvrzené vazby; revalidace negativních lookupů |
| FA-60 | Single-repo bez workspace manifestu | Zachování dosavadních commands a identity |
| FA-61 | Quoting, comments, dollar-quoted středníky v SQL | Správné statements, žádné falešné DDL z literálů |
| FA-62 | Baseline script, marker a undo | Rozlišené režimy; žádný undo v forward replay |
| FA-63 | Target schema obsahuje column, ale test fixture má starý název | Konkrétní dopad na test data a žádný automatický rewrite |
| FA-64 | Two independent migration streams share version V1 | Žádná kolize mezi streamy; merge pouze podle explicitního plánu |

## 26. Doplnění modulů a definition of done

Přidej nebo rozšiř:

- `flyway.py`: discovery, konfigurace, migration inventory a plán;
- `schema_replay.py`: SQL operations, versioned schema state, checkpoints a diff;
- `workspace.py`: manifest, repo-qualified identita, multi-baseline a federace;
- `test_analysis.py`: test cases/assertions/helpers/fixtures a linkage;
- existující dataflow, coverage, validators, reporty, cache a agentové templates.

### T001-S06 (historicky F) — Flyway schema intelligence

Kapitola 23, schema CLI a FA-36–45/61–62/64. Zpracování musí poskytovat výsledné schéma s lifecycle a evidence. Pouhé indexování migračních souborů není dokončení.

### T001-S07 (historicky G) — lokální multirepo analytický workspace

Kapitola 24, workspace CLI a FA-46–60/63. Změna backend výstupu musí ve fixture dohledat konkrétní FE použití a relevantní test assertions/helpers v oddělených repozitářích.

F je závislost spolehlivého schema matching v G; workspace identity lze zavést dříve. Oba milníky jsou součástí povinného analytického rozsahu, nikoliv vzdálená volitelná integrace. Nová definition of done analytického jádra je A–D + F–G; stav Confluence milníku E zůstává odděleně reportovaný.

Aktualizuj README, project-scope, architecture a host instrukce tak, aby analytický i implementační agent před změnou ověřil baseline všech dodaných relevantních repozitářů a aktuální Flyway schema target. Ověř původní test suite, nové offline fixtures a kompatibilitu. Zadání samo nepovoluje automatické změny v připojených aplikačních repozitářích.

Finální analytický report musí umět odpovědět například:

> Přidání splatnosti externího zajištění vyžaduje novou databázovou migraci, úpravu backend mappingu a API, doplnění frontendového formuláře a změnu konkrétních E2E fixtures/assertions. Zde jsou přesné soubory ve třech repozitářích, jejich baseline, evidence, datové požadavky a otevřené rollout otázky.

Takový závěr je přípustný jen tam, kde jej dodané zdroje prokazují; jinak musí uvést konkrétní chybějící vazbu.

## 27. Specializovaný agent pro datové předpoklady nové feature

Doplněno: 2026-10-12. Agent `kgmaker-data-auditor` má zjistit, jaké vstupy jsou nutné pro implementační zadání, co je doložené, co chybí v prozkoumaném rozsahu a co musí být dodáno nebo definováno. Neřeší celý solution design.

Host artefakty: `.github/agents/kgmaker-data-auditor.agent.md` a `.junie/commands/kgmaker-check-data.md`. `kgmaker init` je instaluje idempotentně a bez přepisování uživatelských změn, pokud nebylo zadáno `--force`. Záměr `/kgmaker check-data` není záruka nativního slash příkazu v každém hostu.

### 27.1 Nejmenší možný podíl LLM

Povinné dělení práce:

| Krok | Vykonavatel |
|---|---|
| Discovery, inventář, source hashes a baseline | Existující scanner, source inventory a feature.prepare |
| Flyway plán a schema replay | Funkce z milníku F, nikdy agentové ruční skládání SQL |
| Workspace identity a cross-repo resolution | Funkce z milníku G |
| Vyhledání field/contract kandidátů | Query/index; automatické matching funkce |
| Graph traversal a impact | Existující dataflow/impact funkce |
| Rozlišení datového typu, nullability a struktury | Podporované deterministické parsers |
| Availability klasifikace z validovaných důkazů | Deterministický proof checker |
| Citace, fingerprinty, freshness, apply a report | Existující feature validator/store/renderer |
| Rozložení přirozeného jazyka a business definice | Agent |
| Nejednoznačná business ekvivalence a otázky | Agent, případně analytik/business |

Agent nesmí znovu implementovat tyto funkce v promptu, pomocných bash regexech nebo ručně sestavených hashech. Jednoduché orchestration wrappery mají volat existující Python funkce; žádný druhý scanner, validator ani nezávislý klasifikátor.

Je-li strukturované zadání již dodáno, přeskoč opakovanou LLM dekompozici. Je-li mapping schválen a jeho evidence stále platná, nevolej model k potvrzení téže vazby znovu. LLM zpracovává jen nové/změněné požadavky a ambiguity queue. Pozitivní dostupnost je výsledek kontrol důkazů, nikoliv hlasování modelu.

### 27.2 Aktuálně použitelný workflow a omezení

Agent používá `feature prepare`, `query`, `impact --entity --include-data-flow --format json`, `feature validate/apply/report` a `feature revise`. Prepare již vytváří aktuální inventory v paměti; nevyžaduj zbytečný extra scan nebo semantic extraction.

Candidate vzniká ze skutečného `candidate-template.json` se zachovanou obálkou. Soustřeď se na požadavky, input_requirements, evidence, questions a pending. Ostatní povinné kolekce mohou zůstat prázdné, pokud nejsou nutné k vysvětlení datového předpokladu.

Současný foundation validator nepodporuje důkazy AVAILABLE/PARTIAL/CONFIRMED_MISSING. Instalovaný agent nesmí tyto stavy používat, dokud implementace důkazů není dostupná. UNKNOWN a validní neúplný report jsou správný výsledek. NOT_FOUND_IN_SCOPE vyžaduje úplný ověřovaný rozsah a akceptovaný negativní lookup; neověřené pozitivní tvrzení se nesmí maskovat negativním.

Nedostupné Flyway/workspace commands označ jako capability gap, ne jako důkaz chybějících business dat. Zdrojový soubor či schema deklarace sama neprokazuje naplněnou a použitelnou hodnotu.

### 27.3 Deterministická datová kontrola k implementaci

Jako rozšíření existujícího feature workflow implementuj tenký command:

```bash
kgmaker feature data-check --root . --analysis <id> --inputs requirements/<id>-inputs.json --format json
kgmaker feature data-check --workspace kgmaker.workspace.json --analysis <id> --inputs requirements/<id>-inputs.json --format json
```

To je cílový kontrakt, nikoliv tvrzení, že command již existuje. `--workspace` závisí na milníku G. Command se nesmí potichu pokusit nahradit chybějící multi-repo podporu.

Vstup je versionovaný `DataRequirementSet`: schema_version, analysis_id, requirement_hash, requirements s ID a source quote/reference, inputs s input ID, requirement IDs, explicitními business metadata podle kapitoly 5 a volitelnými candidate entity IDs. Neznámé hodnoty jsou null. Reference musí projít stávající validací. Agent dodá pouze sémantickou specifikaci, ne výsledné hashes/availability.

Command:
1. Validuje DataRequirementSet proti aktuálnímu packetu a evidence rozsahu.
2. Použije existující inventář, graph query, schéma, field mappingy a datové cesty.
3. Vyhodnotí identity/typ/jednotku/čas/derivation dependencies, pokud mají důkazy.
4. Vytvoří pro každý vstup kandidátní zdroje, důkazy, scoped availability a důvod.
5. Vrátí ambiguity queue jen pro nevyřešený business význam, ne pro běžné hash/SQL kontroly.
6. Vykáže zvlášť data delivery gaps, business decisions a parser/access coverage gaps.
7. Připraví candidate fragments kompatibilní s aktuálním feature kontraktem; nesmí je automaticky prohlásit za schválené.
8. Renderuje datový pohled pomocí existujícího rendereru a validuje výstup běžným feature validator, bez paralelního validation path.

Pro aktuálně nepodporované proof kategorie vrátí UNKNOWN/pending. Po implementaci podporovaných důkazů se stav určí automaticky z důkazů podle kapitoly 5. Důvod rozhodnutí a pokrytí jsou součástí JSON; model nesmí změnit UNKNOWN na AVAILABLE bez nové evidence.

Proces může provést nejvýše: sémantickou dekompozici → deterministický check → cílené upřesnění ambiguities → opakovaný check po nové evidence/odpovědích. Žádné bezdůvodné LLM přezkoumání každého field po úspěšném deterministickém ověření.

### 27.4 Bash a PowerShell

Preferuj existující CLI/Python API. Shell smí sloužit pro orchestration, čtení vybraného lokálního excerptu a zpracování JSON.

- Bash fallback: `rg -n -- <literal> <approved-path>`, s korektním quotingem a omezeným rozsahem.
- PowerShell fallback: `Select-String -LiteralPath <approved-file> -Pattern <literal> -SimpleMatch`.
- JSON parsuj pomocí Python `json` nebo PowerShell `ConvertFrom-Json`, nikoliv grepem.
- Requirement prose předávej jako data/soubor, nikdy jako executable shell.
- Nepoužívej eval, Invoke-Expression, automatické build/test/DB příkazy či síťové operace.
- Větvení podle exit code musí být deterministické: invalid oprav/oznam; stale refresh; incomplete ulož jako incomplete.
- Nepřidávej povinnou závislost na Bash: core workflow běží přes Python CLI i na Windows bez admin práv.

Fallback hledání lokalizuje kandidáta; regex výskyt není parser ani důkaz neexistence dat.

### 27.5 Výstup a validace

Výstup má dvě oddělené tabulky:

1. **Co dodat/rozhodnout:** přesná pole a definice, typ/jednotka/čas, důvod potřeby, navržená odpovědná role a další krok.
2. **Co zatím nelze ověřit nástrojem:** konkrétní nepokryté repo, nepodporovaný parser, chybějící runtime evidence či budget.

Do první tabulky nezařazuj nástrojovou nejistotu jako potvrzenou absenci business dat. Doložené zdroje mají repo/entity IDs a source lokalizaci. Candidate a report jsou izolované od AS_IS a zdrojové aplikace.

Nové acceptance testy:

| ID | Situace | Výsledek |
|---|---|---|
| FA-65 | Init instaluje data auditor a JetBrains command | Templates shodné s instalací, idempotence a zachování uživatelských změn |
| FA-66 | Strukturované inputs a podporované mappingy | data-check běží bez LLM a znovu používá stávající funkce |
| FA-67 | Přirozený požadavek s nejasnou likviditou | LLM pouze dekompozice/otázka, automatická část dodá inventář a důkazy |
| FA-68 | Neexistuje pozitivní availability proof checker | UNKNOWN/pending, žádné agentové potvrzení AVAILABLE |
| FA-69 | Změní se relevantní source nebo odpověď | Check revaliduje podle existing freshness/revise, ne pouze promptovou instrukcí |
| FA-70 | Hledání nezahrnuje část repa/rozpočet nestačí | Capability/coverage gap oddělen od data delivery gap |
| FA-71 | Requirement obsahuje shell metacharacters | Předáno jako data, žádné spuštění nebo změna příkazů |
| FA-72 | Bash není dostupný | Stejný core workflow přes Python CLI/PowerShell orchestration |
| FA-73 | Validated mapping beze změny a nová nerelevantní otázka | Žádná opakovaná LLM extrakce všech vstupů |
| FA-74 | Data audit dokončí validaci a report | Žádná změna aplikačního kódu, migrací, testů ani AS_IS artefaktů |

Host agent a instalace jsou okamžitě použitelné s existující foundation. Deterministický data-check, proof checkers a ambiguity queue jsou další implementační deliverable; doplň je do milníků B/D/F/G podle závislostí. Prompt samotný není dokončením tohoto deliverable.
