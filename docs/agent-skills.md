# Skilly KGMakeru v cílovém projektu

`kgmaker init --root /cesta/k/projektu` instaluje pět samostatných skillů do
`.agents/skills/`. Každý obsahuje `SKILL.md` s name/description; podrobné kontrakty
pro semantic, data audit a testgen jsou v jeho `references/`. Tyto soubory jsou
součástí distribuce, nepotřebují checkout ani vývojovou dokumentaci KGMakeru.
Dodávka: [T050](tasks/50_addTargetProjectSkills.md), [change117](changes/117_addTargetProjectSkills.md).

| Skill | Kdy jej použít | Příklad požadavku agentovi |
|---|---|---|
| `kgmaker-context` | Orientace ve zdrojích, architektura, dopad změny a rekognoskace před implementací | „Použij $kgmaker-context a najdi volající této služby; dolož zdroje.“ |
| `kgmaker-semantic` | Prvotní nebo inkrementální údržba doložených sémantických vazeb | „Použij $kgmaker-semantic pro změny oproti merge-base s origin/main.“ |
| `kgmaker-feature-analysis` | Posouzení požadavku, návrh změn a otevřených otázek bez implementace | „Použij $kgmaker-feature-analysis pro requirements/exposure.md.“ |
| `kgmaker-data-audit` | Audit požadovaných vstupů a business nejasností ze schválených lokálních zdrojů | „Použij $kgmaker-data-audit a ověř podklady k tomuto požadavku.“ |
| `kgmaker-testgen` | Návrhy testů existující funkcionality, syntetických dat a volitelný export | „Použij $kgmaker-testgen pro src/calculator.py; zatím jen návrh.“ |

## Instalace a použití

Po instalaci Python balíčku spusť v cílovém projektu:

```bash
kgmaker init
# Samostatná explicitní příprava/obnova strukturálního grafu:
kgmaker scan
kgmaker status
kgmaker query "calculator"
```

`init` vrací vytvořené cesty; samotná instalace nevytváří graf ani nespouští
aplikaci, instalaci závislostí, compiler worker, migraci nebo testy. `scan` skilly
neinstaluje. Při práci s existujícím compiler indexem nejprve ověř status a zdroje;
neobnovuj index jen kvůli přečtení compiler dat. Zastaralý graf lze při čistě
informační otázce použít jako vodítko a závěry ověřit přímo ve zdroji.

Automatické objevení `.agents/skills/`, reload i syntaxe `$skill` závisejí na
hostiteli. Pokud je nenabízí, zadej například:
„Otevři `.agents/skills/kgmaker-data-audit/SKILL.md` a postupuj podle něj pro tento
požadavek.“ Skills nevyžadují custom-agent delegaci, registraci služby ani modelové
API. Konkrétní Copilot/Codex/Junie discovery a odpovědi modelů zatím nemají živé
ověření; lokální testy dokazují soubory a nástrojové kontrakty, nikoli hostitele.

## Údržba a ochrana existujících souborů

Opakovaný běžný `init` zachovává existující obsah i mtime. Po aktualizaci Python
balíčku spusť `kgmaker upgrade`: obnoví nezměněné skilly, reference, agenty i další
inicializační soubory na instalovanou verzi. Místní změny blokují celý plán;
`--dry-run` ho vypíše bez zápisu a explicitní `--force` zahodí změny spravovaných
souborů. Cizí soubory zachované při init upgrade nepřebírá.

`kgmaker uninstall` odstraní projektovou integraci a celý `.kgmaker/` s daty.
Oba příkazy podporují `--root`. Manifest vlastnictví, migraci starších instalací,
rollback i limity popisuje [návod](project-installation.md).
[Záznam T053](changes/170_manageProjectInstallation.md). Úplné hostitelské profily
T049 zůstávají samostatným rozsahem.

## Hranice jednotlivých workflow

Instrukce respektují pravidla cílového projektu a neobsahují povinnosti vytvářet
české KGMaker change notes, používat jeho Task ID či jeho release agenta. Stávající
Copilot/Junie templates mají vlastní historická omezení; T050 je neopravuje.
Skills samy neudělují oprávnění ke commitu, pushi, publikaci či přístupu ke službám
a nepředstavují technický sandbox hostitelského shellu.

Semantic patch je vázán na aktuální `update_id`; feature kandidát na packet,
revision a requirement hash; testgen návrh na svůj packet. Zastaralé závěry je
nutné znovu posoudit, nestačí změnit ID. Feature/data audit nesmí měnit AS_IS
graf přes semantic apply. `data-check` vrací obálku: kandidátem pro validate/apply
je její `candidate`, nikoli celá odpověď. Exit 4 znamená validní neúplný výsledek,
nikoli runtime úspěch. Statická vazba ani Flyway replay nejsou důkaz naplněných dat.

Testgen návrh, export a spuštění testů jsou tři různé operace. Exportuj až na
požadavek zápisu testů, potom použij existující projektový runner v povoleném
rozsahu. Výsledek bez skutečného běhu zůstává NOT_RUN; chybějící toolchain je
SKIP/blocked. Přehled CLI je přímo v instalovaných skillech a v `kgmaker --help`.

## Zdroj templates a ověření

Zdroj je `src/kgmaker/skills.py`. Checkout KGMakeru nemá aktivní cílové skilly.
`python -m pytest -q tests/test_skills.py` ověřuje vygenerovaný obsah a relativní
reference v dočasném cílovém projektu. Parita nevyžaduje vlastní instalaci.
Nespouštěj init nad checkoutem KGMakeru. [Změna T049-S08](changes/169_removeRepositorySelfUse.md).
Konkrétní příkazy, výsledky a neprovedené kontroly jsou v [change117](changes/117_addTargetProjectSkills.md).

## Návaznost analýzy, implementace a testů

Skill kgmaker-context a distribuované workflow role odkazují na
[konfigurovatelné projektové workflows](project-workflows.md). `task add --workflow`
volí greenfield/existing-feature/bugfix nebo projektový profil; task context předává
konkrétní instrukce role a povinné validace. Samostatné audity používají dosavadní
feature/data-check a testy existujícího kódu testgen, bez umělých implementačních
fází. Aktualizované templates i spravované kopie: [change118](changes/118_connectProjectWorkflows.md).
