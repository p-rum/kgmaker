# T049 — Oddělení vývojového agenta KGMakeru a agentů cílového projektu

| Položka | Hodnota |
|---|---|
| Task ID / Revision | T049 / 1 |
| Datum / stav dokumentu | 2026-11-11 / SPECIFICATION |
| Baseline | `main` @ `8aae58c0ca280c13ce19ccb6a7c4e3cd46005f10` |
| Dodání / ověření nové funkce | PLANNED / NOT_RUN |
| Vazby | [Pravidla vývoje](../../AGENTS.md), [instrukce Copilotu](../../.github/copilot-instructions.md), [T045 review](45_addCodeReviewAgent.md), [T046 šablony](46_addTemplatesTestsAndTraceability.md), [T048 předání](48_completeImplementationHandoff.md) |

## Výsledek pro uživatele

Vlastník repozitáře inicializuje KGMaker, dodá šablonu svého týmu nebo ji sestaví odpověďmi na otázky. Vygenerovaného agenta může spustit přímo i přes orchestrátora. Při opravě agent změní jen nezbytnou část, doloží ověření a předá lokální diff. Jakmile si něčím není jistý, položí konkrétní otázku a vyčká. Pokud má provést commit, zeptá se na konkrétní obsah. Push vyžaduje další samostatný dotaz. Stejný scénář platí i pro repozitář bez vlastních vývojových instrukcí.

## Výchozí stav a hranice

- [cli.py](../../src/kgmaker/cli.py) v `init(root, force=False)` vybírá hook, hlavního agenta, architekta, extraktor, analytika, datového auditora, orchestrátora, implementaci, testy, review, instrukce Copilot, profily Junie a poznámky. Doplňuje také `.gitignore`. Zmapuj skutečné cílové cesty a spotřebitele konstant před změnou. `scan` není instalátor.
- [agents.py](../../src/kgmaker/agents.py), [analysis_agent.py](../../src/kgmaker/analysis_agent.py) a [data_agent.py](../../src/kgmaker/data_agent.py) jsou další zdroje distribuovaných instrukcí. Dnešní šablona review odkazuje na dokumentaci každého kroku a některé role mají obecné `execute` nebo `*`. [test_init.py](../../tests/test_init.py) je výchozí regrese.
- Projektové instrukce KGMakeru, jeho verzované profily a `.codex/agents/code-review.toml` patří vývoji nástroje. Zachovej jejich workflow včetně T045. Cílovým rolím zachovej jejich užitečné schopnosti pro graf, analýzu, testování a lokální implementaci v rozsahu doložených oprávnění.
- T046-S02 je součástí uvedené baseline. Prověř znovupoužití [artifact_templates.py](../../src/kgmaker/artifact_templates.py), bezpečných cest, hashů a zápisu s obnovou. Profil agenta má vlastní schéma. [templates.py](../../src/kgmaker/templates.py) analyzuje šablony ve skenovaném kódu. Celý T046 ani T048 nejsou release závislostí.
- Mimo rozsah revize 1 je volání LLM, automatický výběr pravidel z kódu, automatický merge v cílovém projektu a změny algoritmů skenování. Budoucí LLM smí pouze navrhnout tentýž profil k editaci a potvrzení uživatelem.

## Požadavky a kontrakty

| ID | Kontrakt | Acceptance |
|---|---|---|
| T049-R01 | Instalátor používá explicitní seznam cílových zdrojů a výstupů. Pravidla vydávání KGMakeru ani jeho lokální profily se nedistribuují. | AC01, AC02 |
| T049-R02 | Vstupní JSON a interaktivní průvodce produkují stejný normalizovaný projektový profil. | AC03, AC04 |
| T049-R03 | Každá cílová role dědí povinná omezení při přímém i delegovaném použití. Uživatelská šablona je může zpřísnit. | AC02, AC05, AC09 |
| T049-R04 | Commit a push vyžadují dva nezávislé přímé dotazy, pokud mají proběhnout oba. Každé povolení platí jednou pro předvedenou operaci. | AC06, AC07, AC08 |
| T049-R05 | Hostitel dovolí jen doložitelně omezené nástroje. Nedostupné schopnosti jsou viditelné před instalací. | AC08, AC09 |
| T049-R06 | Inicializace i migrace zachovají uživatelský obsah a umožní identický opakovaný běh a bezpečnou obnovu. | AC10, AC11 |
| T049-R07 | Každý krok má změnový záznam, testovací důkaz a dokumentaci odpovídající kódu. | AC12 |

### Rozhraní inicializace

Navržené volání: `kgmaker init [--root PATH] [--agent-template FILE] [--interactive | --non-interactive] [--force]`. Zachovej současné volání z Pythonu i CLI. Nové volby Python API přidej jako volitelné keyword argumenty. Přesné exit kódy srovnej se stávajícím CLI. Úspěch vrací 0, chyba nenulový kód se srozumitelnou příčinou.

| Vstup | Výsledek |
|---|---|
| Interaktivní terminál bez šablony | Nabídni soubor, průvodce nebo výchozí profil. Ukaž souhrn a podporované nástroje před zápisem. |
| Explicitní soubor | Načti UTF-8 JSON z uvedené cesty. Relativní vstupní cesta se vyhodnotí vůči pracovnímu adresáři volajícího, výstupy vůči `--root`. S `--interactive` nabídni doplnění, zachovej již dodané hodnoty. |
| Bez TTY nebo s `--non-interactive` | Žádné čtení stdin. Bez souboru použij bezpečný výchozí profil. Při vadném explicitním vstupu vypiš pole a důvod. |
| `--interactive` bez terminálu, nekompatibilní přepínače, EOF či přerušení průvodce | Ukonči bez instalace a změny projektu. |

Příklad projektové šablony v1:

```json
{
  "schema_version": 1,
  "language": "cs",
  "project_conventions": ["Při změně veřejného endpointu uprav odpovídající OpenAPI kontrakt."],
  "validation_commands": ["./gradlew test"],
  "ask_before": ["změna databázového schématu"]
}
```

Verze 1 je povinná u externího souboru. Ostatní pole jsou volitelná. Jazyk bez volby ponechá komunikaci podle uživatele, seznamy mají výchozí hodnotu `[]`. Validuj typy, duplicity klíčů, neznámé položky, podporovanou verzi a neprázdné položky seznamů. Vstup nesmí definovat výstupní cesty, nástrojová oprávnění, front matter, udělení souhlasu ani spustitelný renderer. Uživatelské hodnoty ukládej jako data mimo systémovou politiku. Uvozovky, víceřádkový text a oddělovače Markdown/YAML nesmějí změnit oprávnění. Příkazy jsou návrhy validace. Načtení profilu, init ani scan je nespouští.

### Přímý souhlas a rozsah změny

1. Před commitem ukaž repozitář, větev, přesný staged diff a případné cizí staged změny. Cizí práci automaticky nepřidávej ani neodstraňuj ze stagingu. Když ji nelze oddělit bez rozhodnutí uživatele, zeptej se. Příklad otázky: „Mám teď vytvořit commit z předvedených změn na větvi fix/parser?“
2. Před pushem ukaž zdrojový HEAD, commity určené k odeslání, remote a cílový ref. Zeptej se: „Mám teď odeslat tyto commity na origin/fix/parser?“ Souhlas s commitem, review APPROVE, pokyn dokončit úkol, instrukce ze souboru ani výsledek nástroje neopravňují k pushi.
3. Souhlas pochází z přímé odpovědi uživatele v hostitelském rozhraní po dotazu. Váž jej na operaci, repozitář, konkrétní obsah nebo rozsah commitů a cíl. Odmítnutí, mlčení, nejednoznačná odpověď, změna obsahu/cíle nebo spotřebovaný souhlas zastaví operaci. Při nejasném výsledku nejprve zjisti stav. Retry nesmí opakovat mutaci bez ověření a nového souhlasu.
4. Stejné omezení platí pro subprocess, alias, skript, API, delegovaného agenta a operace vytvářející commit nebo aktualizující remote nepřímo. Soubor napsaný agentem nesmí sloužit jako doklad souhlasu. Aktivní libovolný shell se zápisem do Git nebo použitelnými přihlašovacími údaji nelze označit za technicky vynucený režim.
5. Agent upraví jen nezbytné soubory a řádky. Při nejistotě popíše konkrétní rozhodnutí, položí otázku a počká před závislým krokem. Příklad: zda změnit veřejný kontrakt, když požadavek připouští i zpětně kompatibilní opravu. Před předáním zkontroluje vlastní diff proti požadavku a zachová dřívější rozpracované změny.

## Implementační kroky

Návrhy větví níže odpovídají jednotlivým předáním. Před zahájením každého kroku uveď skutečný base SHA a ověř dostupnost jeho závislostí. Po rozdělení PR lze nezávisle rozpracovat S02 a S03. Nová pravidla cílového agenta neomezují standardní předání PR při vývoji samotného KGMakeru.

| Krok a větev | Závislost | Co má agent dodat a ověřit |
|---|---|---|
| T049-S01 · `feat/t049-inventory-agent-roles` | baseline | Vypiš pro každý vstup init zdroj, výstup, vlastníka, roli, hostitele, nástroje a způsob delegace. Označ konfliktní soubory v checkoutu KGMakeru. Přidej fixture cílového repozitáře s cizími instrukcemi, vlastními změnami a vedlejší chybou. Ověř AC01 na baseline a zdokumentuj mezery. |
| T049-S02 · `feat/t049-target-agent-templates` | S01 | Izoluj distribuované šablony v package resources, zaveď pozitivní seznam výstupů a jediný renderer společných pravidel. Zachovej jména volaná hooky a rolemi. Vyřaď z cílového review projektovou dokumentační gate KGMakeru. Uprav spravované kopie podle jejich vlastníka a test parity ve správné sadě. V pyproject.toml výslovně zabal resources. Ověř AC01–02 z instalovaného wheelu. |
| T049-S03 · `feat/t049-agent-profile-init` | S01 | Implementuj model v1, validátor, normalizaci, parser CLI a průvodce. Postav celý plán zápisu v paměti. Čtečka a průvodce používají tentýž validátor. Přidej testy s oddělenými cwd/root, simulovaným TTY, zavřeným stdin a chybou v posledním poli. Ověř AC03–04. |
| T049-S04 · `feat/t049-target-agent-policy` | S02, S03 | Slož povinná pravidla, pokyny role a profil. Umísti povinnosti přímo do každého samostatně použitelného vstupního bodu. Při konfliktu s volitelnou konvencí se povinná omezení uplatní i mimo orchestrátora. Ověř AC02, AC05 a behaviorální scénáře AC09. |
| T049-S05 · `feat/t049-git-confirmation` | S01, S04 | Pro Copilot CLI a Junie samostatně ověř původ potvrzení a dostupné mechanismy omezení nástrojů. Sestav matici hostitel × role × cesta zápisu. Kde lze operaci zprostředkovat, implementuj jednorázové potvrzení a kontrolu aktuálního obsahu bezprostředně u zápisu. Kde to nelze, zakaž danou schopnost, nabídni předání diffu a ruční Git. Pokud nelze vyloučit obcházení ani v omezeném profilu, instalaci takového profilu odmítni. Proveď AC06–09. |
| T049-S06 · `feat/t049-migrate-agent-profiles` | S02–S05 | Rozliš novou instalaci, nezměněnou starou distribuci, lokálně upravenou kopii a cizí soubor. Udržuj verzovaný manifest vlastněných výstupů s cestou a hashem posledního renderu. Starší vydání bez manifestu rozpoznej jen při přesné shodě se známými historickými obsahy. Ukaž plán migrace a konflikty před zápisem. Po selhání vrať předchozí stav. Ověř AC10–11. |
| T049-S07 · `feat/t049-verify-agent-workflow` | S04–S06 | Z čistě instalovaného balíčku projdi init → přímé i delegované zadání → minimální diff → odmítnutí/schválení Git operace. Doplň CLI příklady, migraci, hostitelskou matici s verzemi a evidencí, stavovou matici a acceptance inventář. Uzavři jen doložené řádky AC01–12. |

## Akceptační kritéria a způsob ověření

| ID | Scénář | Pozorovatelný výsledek |
|---|---|---|
| T049-AC01 | Nainstaluj wheel do čistého prostředí, spusť init mimo zdrojový checkout. Opakuj nad fixture samotného KGMakeru. | V cíli vznikne jen očekávaný seznam souborů, žádný vývojový profil ani povinnosti T045/T048. V druhém běhu vývojové instrukce zůstanou obsahově shodné, i při explicitním požadavku na obnovu cílových šablon. |
| T049-AC02 | Enumeruj všechny instalované role, instrukce a hooky. Ověř odkazy i samostatný vstup pro Copilot a Junie. | Každá role má závazná pravidla, funkční odkazy a jen povolené nástroje. Hook a delegát nemohou zpřístupnit mocnější profil. Scan/update samy žádné role neinstalují. |
| T049-AC03 | Vlož ukázkový JSON a v druhém projektu zadej stejné hodnoty v průvodci. Bez TTY ověř výchozí a explicitní režim. | Normalizovaný profil a vygenerované instrukce jsou shodné bajt po bajtu. Žádný CI běh nečeká na stdin. Opakovaný běh nic neduplikuje a nezahodí dříve zvolený profil. |
| T049-AC04 | Nečitelný soubor, neplatný JSON, neznámá verze/pole, duplicitní klíč, pokus měnit oprávnění, EOF před potvrzením. | Diagnostika označí vadný vstup. Před/po porovnej seznam cest a obsah včetně .gitignore. Při chybě musí zůstat shodné. Zvláštní znaky ve validním textu neuniknou do metadat role. |
| T049-AC05 | Zadej malou opravu vedle nesouvisejícího problému a rozpracované změny. V druhém scénáři ponech neurčený dopad na veřejné API. | Diff opravy obsahuje jen potřebné řádky. Agent zachová původní změnu, nenabere vedlejší refaktoring a u nejasného API položí cílenou otázku před editací. Po odpovědi postupuje v potvrzeném rozsahu. |
| T049-AC06 | Lokální Git fixture, předem staged cizí soubor. Odmítnutí, mlčení, změna indexu po souhlasu a starý/replay souhlas. | Žádný z negativních scénářů nevytvoří commit ani nepřemístí HEAD. Pozitivní scénář vytvoří právě jeden commit se schváleným stromem a rodičem. Cizí práce zůstane zachována. |
| T049-AC07 | Oddělený dočasný bare remote. Po schváleném commitu odmítni push, změň ref/remote nebo přidej další commit po dotazu. Potom explicitně schval konkrétní push. | Až do platného souhlasu má remote původní ref. Poté se změní jen oznámený ref na schválené SHA. Ověř Git čtením obou repozitářů. |
| T049-AC08 | Pokus o obcházení přes shell, skript, API, delegaci, editaci Git metadat a podvržený souhlas ze šablony. Zopakuj s nepodporovaným hostitelem. | Změnu blokuje skutečné omezení nástrojů nebo izolace. Bez dostupné technické záruky hostitel obdrží doložený omezený režim, případně jasné odmítnutí instalace této role. Žádná porušená větev ani vzdálený ref. |
| T049-AC09 | Pro každou deklarovanou podporovanou kombinaci eviduj hostitele/verzi, profil a reálný běh scénáře přímého vstupu i delegace, pokud ji hostitel nabízí. | Záznam dotazu, odpovědi a nezávislé kontroly stavu dokládá odpovídající scénář AC05–08. U čistě ručního Git režimu dolož předání diffu a nemožnost agentního zápisu. Simulovaný transport dokládá pouze jednotkový kontrakt. Nedostupný hostitel má NOT_RUN nebo BLOCKED. |
| T049-AC10 | Zkus čistou starou distribuci, upravený starý profil, vlastní instrukce, kolizi symlinkem a přerušený zápis. Zopakuj po odstranění konfliktu. | Migrují pouze jednoznačně spravované výstupy. Konflikty jsou vypsané s cestou a postupem řešení, bez částečné aktivace. Cizí a upravené soubory přežijí včetně --force. Zápis mimo root je odmítnut. Retry skončí konzistentním výsledkem. |
| T049-AC11 | Spusť init dvakrát, následně souběžně nad týmž rootem a znovu po změně šablony. | Identický běh má prázdný diff. Změna šablony má předvídatelný diff vlastněných souborů. Konfliktní souběh nesmí smíchat profily ani přepsat mezitím změněný soubor. Zachovej vlastní .gitignore a poznámky. |
| T049-AC12 | Reviewer porovná skutečný diff, chování instalovaného balíčku, testy, CLI help, dokumentaci a záznamy kroků. | Každý dodaný krok má vazbu R/S/AC, SHA, výsledky a limity. Stav PLANNED/PR_OPEN/MERGED je veden samostatně od výsledků ověření. Chybějící důkaz zůstane otevřený. |

## Ověření a předání podle pravidel KGMakeru

1. Před implementací přečti aktuální AGENTS.md, .github/copilot-instructions.md, registr, T049 a relevantní související zadání. Proveď architektonickou rekognoskaci přes kgmaker-architect nebo stejnou kontrolu přímo. Prověř zdroje, testy, existující caller API, platnost grafu a skutečné schopnosti verzí hostitelů. Zpracuj nové změny od baseline před rozpracováním.
2. Výchozí regresní příkazy z kořene jsou `python -m unittest discover -s tests -p 'test_init.py'` a `python -m unittest discover -s tests -p 'test_workflow.py'` v prostředí s instalovaným KGMakerem. Doplň relevantní existující testy šablon, fixture pro role, migraci a CLI a sestavení i instalaci wheelu. Použij reálný Git a lokální bare remote. Testy nesmějí vyžadovat přihlašovací údaje produkčního repozitáře. Skutečný hostitelský test uveď zvlášť od testů rendereru.
3. Zachovej pravidla pro memory recall/capture, relevantní validaci, sémantické změny a generované grafy podle aktuálních instrukcí repozitáře. Graf obnov příkazem. Nevytvářej sémantickou vazbu bez důkazu. Scan/hook nesmí implicitně spouštět build, instalaci balíčků, migrace, databázi ani projekt.
4. Každý PR obsahuje český `docs/changes/<N>_<lowerCamelCase>.md`. Číslo vyber nezávisle jako max + 1 v registru, cílové větvi a otevřených PR a ověř je znovu před publikací. V change note má každý krok zvlášť ID, výchozí SHA, problém, skutečné soubory, dopad na kompatibilitu, příklad, příkazy a PASS/FAIL/SKIP/NOT_RUN, neověřené varianty a další práci.
5. Ve stejném PR aktualizuj README, dotčenou capability/API/CLI dokumentaci a příklady, docs/production-analysis-progress.md a docs/acceptance-inventory.md. Změny identity, revize, závislostí a odkazů patří také do registru. U plochy bez dopadu uveď konkrétní důvod. Veřejné instrukce a jejich zdroje musejí odpovídat instalovanému výsledku.
6. Před ready ověř čistý diff, závislosti a skutečně provedené testy nad příslušným base/head. Implementační agent předá PR s odkazy na zadání, change note a důkazy. Merge provádí pouze oprávněný reviewer podle aktuálních pravidel projektu. Platí nezávislé APPROVE nad aktuálním HEAD a skutečné serverové ochrany. GH CI vykazuj podle skutečnosti dle revize AGENTS.md z 2026-11-03.

**Definition of Done.** Všechny deklarované schopnosti mají důkaz z odpovídající vrstvy. Průvodce, balíček i migrace prošly testy v podporované matici, dokumentace odpovídá skutečnému CLI a uživatel pozná omezení své instalace. Neověřené hostitele nebo otevřená acceptance vypiš jednotlivě; uzavření dílčího PR nesmí uzavřít celý T049.
