# T048 — předávací plán a povinná dokumentace kroků

Datum: 2026-11-06. Baseline: main `250e7c16250a97b9f8df5256b9894c8119dc64d9`.
Task: T048 revision 1; dokumentační předání, pravidlo T048-R01/AC09 a návaznosti R02/AC10.
Celý implementační program T048-S01–S08 tím není dokončený.

## Krok: předávací plán

Problém: existující zadání a historické statusy neukazují jednotné aktuální pořadí
dokončení; T003/T047 se překrývají a T046 je mimo main.
Přidán `docs/tasks/48_completeImplementationHandoff.md`: baseline po T020/PR87,
pořadí T046, dependencies datových toků a incremental, jediní vlastníci společných
kontraktů, 39 odkazovaných původních nedodaných úkolů, acceptance, testy, větve/PR,
migrace, rollback a předávací šablona. T047 ani starší zadání se neruší.
Registr, README a úvod stavové matice odkazují na plán a rozlišují delivery/verification.
README opravuje známé nepravdivé tvrzení o neexistenci architektonického CLI.
Všechna historická acceptance nebyla znovu certifikována; detailní sjednocení je S01.

## Krok: dokumentační gate každé implementace

AGENTS vyžaduje dohledatelný záznam každého kroku v českém change note,
současnou úpravu relevantních návodů/API/CLI/příkladů/stavové a acceptance matice,
nebo konkrétní důvod bez dopadu. Chybějící či rozporná dokumentace blokuje
dokončení. Registr se mění při změně identity/revize/dependencies/odkazů.
Pravidlo je přeneseno do společného `src/kgmaker/agent_rules.py`,
Copilot/JetBrains spravovaných kopií a implementačního/review agenta v
`src/kgmaker/agents.py` i odpovídajících souborech.
Původní zastaralá věta v AGENTS o přepisování compiler vrstvy je opravena podle
existujícího provideru. Init nadále chrání uživatelské změny.

Příklad: při dokončení T021 nestačí dodat Mermaid renderer. Tentýž PR musí mít
krok T021 s mapováním AC na skutečné testy, aktuální popis CLI/limitů, stav dodání
a ověření; pokud se API nemění, uvede konkrétní důvod bez dopadu.

## Ověření

Validace proběhla na lokálně materializovaných Python zdrojích uvedené baseline
a změněných instrukcích, nikoli plným checkoutem s worker artefakty.

- `PYTHONPATH=src python3 -m unittest discover -s tests -p test_init.py -v`: PASS,
  1 existující test; zopakován po normalizaci konců upravených souborů.
- `python3 -m compileall -q src/kgmaker/agent_rules.py src/kgmaker/agents.py`: PASS.
- Jednorázový Python smoke nad `kgmaker.cli.init`: PASS; nové pravidlo v generovaných
  instrukcích, přesná shoda implementační/review kopie s templates, zachování ručně
  upraveného souboru při druhém init.
- Kontrola relativních odkazů plánu proti GitHub tree a novým souborům: PASS;
  příloha obsahuje právě 23 T003 a 16 T004 původních úkolů.
- `git diff --no-index --check` nad přesně změněnými soubory proti původnímu obsahu:
  PASS. První kontrola odhalila novou prázdnou koncovou řádku, opraveno.
  Kontrola zahrnující i nezměněné pomocné zdroje byla nevhodně široká a nahrazena
  kontrolou skutečného diffu; staré whitespace v nezměněných zdrojích se neupravovaly.
- Plná Python/worker/build/rendering sada: NOT_RUN; změna upravuje plán a text
  instrukcí, nikoli analytické algoritmy. Výsledek init smoke není produkční acceptance.
- GitHub CI tohoto PR a nezávislé review: při přípravě NOT_RUN.
- Generovaný graf/semantic patch: beze změny; nevznikly nové strukturální vazby
  analytického kódu. Dostupný Graph.md konektor vrátil bez obsahu; zdroje byly
  ověřeny přímo, bez vymyšlených sémantických hran.

## Dokumentační dopady a kompatibilita

README: odkaz na plán a oprava CLI dostupnosti. Registr: T048.
Stavová matice: datovaný souhrn a oddělení historických checkpointů.
Capability/API/CLI schémata: bez změny chování, jejich detailní historické rozpory
řeší T048-S01; nedeklaruje se nové CLI.
Acceptance inventář: v tomto předání beze změny výsledků, protože se žádná
funkční acceptance nepřehodnocovala; nová dokumentační acceptance je v T048.
Agent instrukce a jejich templates: změněny současně.

Graph/store/runtime IDs, schémata a uživatelské history zůstávají kompatibilní.
Rollback vrátí dokumentační/template commit; nejde o datovou migraci.
Zbývá realizovat program a ověřit konkrétní source SHA jednotlivých dodávek;
samotný merge plánu není jeho splnění.
