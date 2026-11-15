# Skilly pro použití KGMakeru v cílovém projektu

Datum: 2026-11-15. Zadání [T050 revize 1](../tasks/50_addTargetProjectSkills.md).
Výchozí SHA obou kroků: `193c89b4d461047fd3330fd74892c5830ba8ac81`.
Dodání: **PR_OPEN**; ověření: **PARTIAL** — lokální kontrakty ověřené,
živé chování hostitelů NOT_RUN. Toto není dodání T049.

## T050-S01 — templates a instalace

- Požadavky T050-R01 až R04; acceptance T050-AC01 až AC03.
- Problém: init distribuoval Copilot/Junie role, ale ne sadu samostatných skillů
  použitelných v cílovém projektu; některé role navíc odkazují na vývojové dokumenty
  nástroje. Dřívější ruční skill `kgmaker` nebyl distribuovaným kontraktem init.
- Skutečná změna: `src/kgmaker/skills.py` obsahuje pět samostatných skillů a tři
  references v explicitní mapě Python templates. `src/kgmaker/cli.py` zapojuje
  výstupy do init a doplňuje help. Před zápisem init kontroluje nové skill cesty
  existujícím `safe_path`; odmítá symlinky a kolize file/directory.
  Spravované kopie jsou v `.agents/skills/kgmaker-context`, `kgmaker-semantic`,
  `kgmaker-feature-analysis`, `kgmaker-data-audit` a `kgmaker-testgen`.
- Skills přímo popisují současné query/impact, semantic, feature/data-check a
  testgen kontrakty. References jsou dodané spolu s nimi, bez závislosti na
  checkoutových docs. Nepřebírají PROJECT_RULES ani vývojové review/release profily.
- Kompatibilita: Python init API, datová schémata a existující role beze změny.
  Běžný init zachovává obsah i mtime; explicitní force obnovuje deklarované
  templates jako dosud. Žádné přidání závislosti ani změna package-data: texty jsou
  součástí Python modulu. Cizí skill a uživatelsky smazaný původní skill se neobnovují.
- Kontroly: parita osmi spravovaných souborů, init CLI s oddělenými cwd/root,
  zachování uživatelských úprav/cizích skillů, opakování, explicitní force, šest
  symlinkových pozic s/bez force, čtyři file/directory kolize a scan bez instalace:
  **PASS**, součást níže uvedené pytest sady. Formátový validator: **5 PASS**.
- Omezení: preflight není transaction/rollback celého starého init ani ochrana
  proti souběžnému zápisu. Neřeší původní distribuované role ani technické omezení
  shellu (T049). Discovery a syntaxe vyvolání závisejí na hostiteli.

## T050-S02 — ověření příkladů, distribuce a dokumentace

- Požadavky T050-R01 až R04; acceptance T050-AC01 až AC05.
- Problém: samotná existence SKILL.md ani zelená fixture nedokládá použitelný
  kontrakt nebo dostupnost resources mimo checkout.
- Skutečné změny: `tests/test_skills.py` testuje instalaci, paritu, odkazy,
  ochranu souborů a nulovou mutaci při vadné cestě. JSON příklady z nových
  references skutečně procházejí data-check/feature validate/apply a testgen
  validate/apply/report. Data audit vrací UNKNOWN; testgen execution je NOT_RUN
  a nevznikají testové soubory bez exportu. Testy nekopírují text instrukcí.
- CLI testy používají skutečný vstup přes `main()`/SystemExit; ukázka datových
  vstupů ověřuje analysis-scoped IDs proti feature validátoru.
- Kompatibilita: nové testy a dokumentace, bez změny analytických schémat.
  README a příručka vysvětlují manuální otevření skillu a oddělené evidence.

### Přesné kontroly a výsledky

Z kořene checkoutu, pokud není uvedeno jinak:

| Kontrola | Výsledek |
|---|---|
| `PYTHONPATH=src python -m pytest -q tests/test_skills.py tests/test_init.py tests/test_scanner.py tests/test_artifact_templates.py tests/test_data_check.py tests/test_delivery.py` | **PASS: 83 passed** (z toho 24 nových skills testů) |
| `/usr/bin/python3 /home/petra/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/<name>` pro pět nových skillů | **PASS: 5× Skill is valid**; běžný Python 3.12 nemá PyYAML, použit dostupný systémový Python |
| `python /tmp/kgmaker-skill-wheel-smoke.py` | **PASS**: build kopie aktuálních zdrojů přes `/usr/bin/python3 -m pip wheel --no-deps --no-build-isolation`, instalace wheelu do čistého venv, init mimo checkout bez PYTHONPATH, shoda 8 resources, druhý init shodné bytes/mtime; `/tmp/kgmaker-t050-wheel-ah9605vx/summary.json` |
| `PYTHONPATH=src python -m pytest -q` | **FAIL při collection**: existující `referencing/typing.py` volá nepodporované `TypeVar(default=...)` v místním Pythonu 3.12; žádné tvrzení plného PASS |
| `PYTHONPATH=src /usr/bin/python3 -m pytest -q -x` | **FAIL**: 58 passed, 12 skipped, 16 subtests passed, 1 failed; první pád existující `test_mv02_real_reactor_output_precedes_stale_repository_jar`: `Exporter distribution hash mismatch` |
| `PYTHONPATH=src /usr/bin/python3 -m pytest -q` | **FAIL: 6 failed, 1878 passed, 807 skipped, 36 errors, 76 subtests passed**, 299.53 s; Kotlin snap nelze spustit (36 setup errors), Maven exporter hash mismatch, Gradle home není zapisovatelný; dva další pády confluence nesting a ORM symlink na Pythonu 3.14 se stejně reprodukují na čisté baseline |
| Baseline `git archive HEAD src tests/test_confluence_configuration.py tests/test_orm_xml_overrides.py`, dva dotčené testy pod `/usr/bin/python3 -m pytest -q` | **FAIL: stejné 2 pády** na nezměněné baseline; `/tmp/kgmaker-t050-baseline-glc5i71v/pytest.log` |
| `git diff --check` | **PASS** |
| `python -m compileall -q src/kgmaker/skills.py src/kgmaker/cli.py tests/test_skills.py` | **PASS** |
| `build_parser().parse_args(...)` pro 24 CLI tvarů ze skillů | **PASS**: query/impact/memory/scan/semantic/feature/data-check/testgen/template/trace/init |
| Kontrola relativních odkazů v nových docs a instalovaných references | **PASS** |
| `PYTHONPATH=src python -m kgmaker.cli scan --no-docs` | **PASS**: 550 files, 5639 declarations/sections, 43052 relationships; obnoven pouze ignored machine index, textové pohledy beze změny. Ohlášeny vynechané stale semantic entries v README/architecture/cli; nejde o plnou semantic validaci |

Wheel smoke kopie nezahrnovala worker build výstupy ani
node_modules: ověřuje distribuci skillů, nikoli funkčnost compiler workerů.
Vstupní pracovní strom obsahuje uživatelské `pyproject.toml` 0.2.0 a staged smazání
starého skillu; tyto změny nejsou součástí dodávky ani jejího commitu.

### Dokumentační plochy

| Plocha | Změna nebo konkrétní bez dopadu |
|---|---|
| README | Nové instalované skilly, příklady, force a hostitelské limity; odkaz sem |
| Capability / API / CLI | `docs/agent-skills.md`, `docs/architecture.md`, init help; Python signatura init beze změny |
| Feature/data/testgen capability docs | Bez dopadu na jejich příkazy a datové kontrakty; nový návod odkazuje na samostatné instalované postupy a nenahrazuje dosavadní dokumentaci |
| Příklady | Tabulka požadavků v agent-skills.md, příkazy v SKILL.md a tři přímo dodávané references |
| Stavová matice / acceptance | T050 řádky v production-analysis-progress a acceptance-inventory; historické výsledky jiných úkolů zachované |
| Registr zadání | T050 revize 1 přidána; žádné přečíslování T049 ani runtime analysis ID |
| Instalované instrukce | Nové kopie shodné s `skills.py`; staré Copilot/Junie instrukce mají bez dopadu, jejich izolaci řeší T049 |

### Příklad a zbývající práce

Po `kgmaker init --root /cesta/k/projektu` agent může otevřít
`.agents/skills/kgmaker-data-audit/SKILL.md`, připravit izolovaný feature packet,
zpracovat `candidate` z data-check a vrátit oddělené business/data a coverage gaps.
Bez pozitivního důkazu dostupnosti zůstane UNKNOWN.

Živé Copilot/Codex/Junie scénáře a automatická discovery **NOT_RUN**. GH CI a
nezávislé review aktuálního HEAD **NOT_RUN**; merge není součástí práce. Celá
produkční/compiler/Windows acceptance **NOT_RUN**, existující toolchain selhání
se touto změnou neřeší. T049 migrace/profily a vynucování souhlasů zůstávají otevřené.

Semantic patch nevznikl: nebyly doloženy nové sémantické vazby pro aktuální packet.
Údržba starých stale semantic entries zůstává otevřená. `memory capture` NOT_RUN:
pracovní strom obsahuje i cizí rozpracované změny; jejich epizoda se k tomuto
předání nepřiřazuje. Žádný zdrojový HTML/Confluence ani ruční generovaný graf
nebyl změněn. T050/change117 znovu prověřeny před publikací: main SHA a oba
otevřené PR heady zůstaly stejné, kolize čísel nenalezena.

## Stav publikace

Lokální implementační commit: `224a1285ba0843b9f16200aa89b367e20b2169a4`.
Původní push na `origin/feat/t050-target-project-skills` automatická kontrola zamítla,
protože vytvoření skillů nepovažuje za výslovné oprávnění exportovat commit
se zdrojovým kódem a dokumentací na externí GitHub remote. V této fázi PR nevznikl.
Uživatel následně výslovně požádal „vytvoř pr“. Nově povolený git push skončil
na chybějícím HTTPS přihlášení. Publikace používá připojený GitHub konektor:
větev `feat/t050-target-project-skills`, base `main`, draft PR. Obsah publikovaného
stromu se porovnává s lokálním committed tree; commit SHA může kvůli metadatům
GitHub API lišit. Žádná dřívější uživatelská změna se nepublikuje.
Navazující dokumentační záznamy T050-S02 opravují delivery status podle publikace,
bez změny implementace; kontrola `git diff --check` PASS.
