# Propojení projektových workflows

Datum 2026-11-15; [T051 revize 1](../tasks/51_connectProjectWorkflows.md).
Výchozí SHA všech kroků: `6790b0e0a930089924c61c3f8a6b3aef1d44121c`.
Dodání **PR_OPEN** ([draft PR #99](https://github.com/p-rum/kgmaker/pull/99)); ověření
**VERIFIED_IN_SCOPE** pro níže uvedené lokální kontrakty, živí hostitelé NOT_RUN.
Vstupní změna verze v pyproject.toml a staged smazání starého skillu patří uživateli.

## T051-S01 — konfigurovatelné profily

T051-R01 / T051-AC01. Problém: pevné role neměly verzovatelný projektový výběr
postupu a instrukcí. `src/kgmaker/workflow_profiles.py` dodává greenfield,
existing-feature a bugfix, striktní JSON konfiguraci `.kgmaker/workflows.json`,
validaci limitů/duplicit/symlink cest a read-only CLI list/show/check zapojené v
`cli.py`. Vlastní profil dědí pouze builtin; role instrukce a validace jsou data,
nikdy shell ani povolení. `examples/workflows/python-project.json` je použitelná
ukázka s výběrem výchozího profilu.

Kompatibilita: žádná nová závislost, runner ani katalog. Konfigurace je mimo
ignorovaný runtime adresář. Init ji nevytváří ani nepřepisuje. Ověření validních,
chybných a duplicitních vstupů, příkladu, odděleného root/cwd a nulové mutace při
chybě: **PASS** v sadě níže. Limity: pevná posloupnost fází, bez libovolného DAG.

## T051-S02 — snapshot, context a předání

T051-R02/R03 / T051-AC02/AC03. Problém: role neměly stabilní projektové instrukce,
legacy task mohl pokračovat bez doložených handoffů. `workflow.py` zavádí opt-in
v3 snapshot; `task_id` zahrnuje profil jen u v3. `context.py` předává instrukce
role, validace a hash do JSON/Markdown; při nedostatečném budgetu selže před zápisem.
`cli.py` přijímá `task add --workflow`, profile/default priority, limit a budget.

Kontroly v persistence vyžadují dokončené artefakty příslušných rolí; povinné
validace musí mít passed pro přesný label/command. V3 váže i test na HEAD a
source_inventory; před review/done odmítá staré výsledky. Review musí schvalovat
bez otevřeného major/blocker. Retry a stop fungují i po neúspěchu; dosavadní
volitelná lidská approval policy zůstává další samostatnou kontrolou.

Kompatibilita: v1/v2 identity i legacy chování zachované, starší nástroj v3 nepřečte.
Obsah artefaktů je LOCAL_DECLARED, nikoli automaticky ověřený záznam runneru.
Source inventory vynechává skryté adresáře (i .github), generované/senzitivní,
symlink a nadlimitní vstupy; jejich změny a prostředí vyžadují zvláštní review.
Konfigurace nezmění existující task; změna profilu vyžaduje nový task.

`tests/test_workflow_profiles.py` ověřuje v1/v3 identity, snapshot po smazání
konfigurace, gate přes save_task, skip/unknown/fail, jiný příkaz, stale test/review,
retry, open major, budget a plný CLI průchod s artefakty v runtime adresáři.
**PASS**. Nezávislé read-only review odhalilo TypeError pro nehashovatelnou verzi
schema_version; opraveno přesunutím typové kontroly a pěti negativními regresemi.

## T051-S03 — instrukce, příručka a distribuce

T051-R04/R05 / T051-AC04/AC05. Problém: jednotlivé schopnosti byly oddělené a
nebylo zřejmé, kdy použít feature, testgen nebo implementační task.
`delivery_instructions.py`, `skills.py` a odpovídajících pět Copilot rolí (včetně analytika),
Junie analyze-feature command, Copilot instructions a kgmaker-context SKILL.md nyní vedou přes workflow snapshot
a role context. Původní pětice skillů zůstává; init zachovává uživatelské úpravy.
`docs/project-workflows.md` obsahuje mapu záměrů, schéma, kompletní handoff příkazy,
artefakty, traceability a výslovné limity. Běžný runner se spouští odděleně.

Kompatibilita: stávající init API, hostitelé a nástrojová oprávnění beze změny.
T049 izolace rolí, interaktivní průvodce, technické vynucení oprávnění a atomická
migrace nejsou dodané tímto krokem. Živá discovery a chování modelu NOT_RUN.

### Provedené kontroly

| Příkaz / kontrola | Výsledek |
|---|---|
| `PYTHONPATH=src python -m pytest -q tests/test_workflow_profiles.py tests/test_workflow.py tests/test_init.py tests/test_skills.py tests/test_delivery.py tests/test_provenance.py tests/test_artifact_templates.py` | PASS: 103 testů |
| `python /tmp/kgmaker-workflow-wheel-smoke.py` | PASS: wheel bez nových dependencies, čistý venv, init mimo checkout, 8 resources parity, opakovaný init bytes/mtime, workflow list/show/check, v3 task a context; artefakty `/tmp/kgmaker-t051-wheel-iuvpsnkh` |
| `python -m compileall -q src/kgmaker/workflow_profiles.py src/kgmaker/workflow.py src/kgmaker/context.py src/kgmaker/cli.py src/kgmaker/delivery_instructions.py src/kgmaker/skills.py tests/test_workflow_profiles.py` | PASS |
| `git diff --check` | PASS po odstranění přidaných prázdných koncových řádků |
| Architektonická rekognoskace, query a memory recall | PASS se zdrojovým ověřením; existující graf byl stale, neobnoven při čtení |

První meziběhy odhalily chybějící synchronizaci read-only kopie skillu, špatné
volání main(argv) v novém testu a rozdíl whitespace spravovaných instrukcí.
Opraveno; konečná sada výše je nové ověření po opravách, nikoli přepsání historie.

### Dokumentační plochy

| Plocha | Dopad |
|---|---|
| README | Profily, příklady, nové odkazy; odstraněn neplatný odkaz na dřívější monolitický skill |
| Capability/API/CLI | project-workflows.md, architecture.md, delivery-workflow.md, agent-skills.md, CLI help |
| Příklady | examples/workflows/python-project.json a handoff příkazy ve workflow příručce |
| Stavová matice / acceptance | T051 řádky; oddělené dodání a ověření |
| Registr | T051 revize 1; žádná změna historických/runtime ID |
| Templates / instalované kopie | Společné delivery instructions a context skill, parity a init preservation test |
| Feature/data-check/testgen schémata, graph/store/Flyway | Bez dopadu: žádná změna modelu ani jejich parserů, pouze odkazy na existující postupy |

### Neprovedené kontroly a zbývající práce

Plná produkční/compiler/toolchain/Windows sada a živí hostitelé **NOT_RUN**;
změna je čistě Python orchestrace a instrukce. Historické environmentální chyby
celé sady z change117 se tímto neoznačují za opravené. GH CI: poslední pozorované běhy skončily FAIL před spuštěním kroků; viz audit níže.
Nejde o runtime data proof, automatický runner ani automatické vytváření trace vazeb.

`memory capture` **NOT_RUN**: pracovní strom zahrnuje cizí změny, které nelze
vydávat za součást této implementační epizody. Sémantický patch nevznikl, protože
pro aktuální semantic packet nebyly doloženy nové vazby. Generované pohledy nejsou
ručně upravované. Publikace PR a review aktuálního commitu zůstávají samostatným
krokem; lokální diff se nemerguje automaticky.

Příklad: `kgmaker task add "Opravit prázdný vstup" --workflow bugfix`, context
architekta, doložená analýza/plán, implementace, skutečný regresní výsledek a review.
Chybějící testovací nástroj blokuje povinný test; text instrukcí nevytváří PASS.

Nezávislé review v S03 našlo dvě chybějící distribuované kopie společného bloku
(analytik a Junie analyze-feature) a legacy formulaci source observations v delivery
příručce. Opraveno v témže kroku; parity test nyní kontroluje všech sedm spotřebitelů.
Během práce přibyl souběžný dokumentační commit T050 `5a6f09ba6a39a158ff573abec5d84c66ee3569b3`
a draft PR #98; jeho změny zůstaly zachované. Výchozí implementační baseline výše
je historicky správná, finální diff je nad tímto novým dokumentačním HEAD.

Finální údržba indexu: `PYTHONPATH=src python -m kgmaker scan --no-docs` **PASS**,
556 souborů, 5691 deklarací/sekcí, 42702 vztahů. Přeskočeno 20 stale semantic
vztahů v README/architecture/cli; není to plná semantic validace. Textové generované
pohledy zůstaly beze změny. Číslování T051/change118 před publikací znovu ověřené
v main a otevřených PR #4/#97/#98; bez kolize. Remote T050 tree je shodný s lokální
baseline `5a6f09b` (`cbe737d266a4b33e9c67521319cd548cd872c68e`), případný PR bude
navazovat na větev T050 a vyžaduje dokončení závislosti #98.

Nezávislé read-only review finálního lokálního diffu: **APPROVE**,
103 testů a diff check nezávisle zopakovány PASS. Není to GitHub review
publikovaného HEAD ani oprávnění k merge.

## Publikované předání

Draft PR [#99](https://github.com/p-rum/kgmaker/pull/99), větev
`feat/t051-project-workflows`, base `feat/t050-target-project-skills` (závislost #98).
Implementační commit `504ad625a01ba9571759a40b870382cf8bc12568`, ověřený tree
`5c6cd9fec7238bd4289a6a0626a947bd91851bde`. Následující čistě dokumentační záznam
mění delivery stav z lokálního IN_PROGRESS na PR_OPEN; nemění funkční kód.
Před zveřejněním byl strom porovnán s dočasným lokálním Git indexem, který
nezměnil uživatelův staging. Změny pyproject.toml a smazání starého skillu nejsou
součástí PR. Merge neproveden; po dodání #98 aktualizovat base a provést nezávislé
review aktuálního HEAD. GH CI není ověřené; viz audit níže.

### Audit GitHub Actions po publikaci

Pro dokumentační HEAD `ecd5a587a45801cd4bf87d54931788a5b9b6ce91` mají běhy
[43703382892](https://github.com/p-rum/kgmaker/actions/runs/43703382892) a
[43703378838](https://github.com/p-rum/kgmaker/actions/runs/43703378838) conclusion
**failure**. Joby skončily failure/cancelled a všechny mají prázdné `steps`.
Log unittest jobu 132779162086 není dostupný (BlobNotFound); konektor neposkytuje
check-run annotations. Příčina není ověřená a nelze ji vydávat za konkrétní chybu
kódu ani za prokázaný billing problém. Vzdálené testy jsou **NOT_RUN / neověřené**,
nikoli PASS. Cílená lokální sada po publikaci znovu **103 PASS** a diff check PASS.
Tato poznámka je dokumentační audit, nikoli oprava CI nebo nezávislé review HEAD.
