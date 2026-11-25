# Vývoj KGMAKERu bez vlastní integrace

## T049-S08 · T049-R08 · T049-AC13 a AC14

Výchozí SHA: `edb65e57ca4de1743c810689c78e069cd86b2b41` (`main`, 2026-11-24).
Uživatel výslovně požaduje odstranit používání KGMAKERu při jeho vlastním vývoji.
Dosavadní session hook, instrukce, profily i CI odkazovaly zpět na opravovaný
nástroj a jeho zastaralý graf. Vývoj musí fungovat přímo nad zdrojem a testy.

### Skutečné změny a soubory

- `AGENTS.md` a `.github/copilot-instructions.md` zavádějí přímé čtení zdrojů,
  testů a Gitu. Starší self-use požadavky v historických zadáních a již
  načtených profilech jsou výslovně nahrazené.
- Odstraněn session hook `.github/hooks/kgmaker.json`, devět instalovaných
  cílových agentů `.github/agents/kgmaker*.agent.md`, čtyři Junie commands
  a sedm aktivních skillů v `.agents/skills/` včetně completion a jejich
  tří referencí. Distribuované Python templates zůstávají beze změny.
- Sto implementačních profilů a jeden review profil v `.codex/agents/`
  zachovávají zadání, modely, worktree a PR pravidla; místo vlastního
  grafu/semantic/memory workflow používají přímé zdrojové a testové důkazy.
  T045 merge oprávnění se nemění. Registr agentů již neodkazuje na smazaný profil.
- `.github/workflows/test.yml` přestává spouštět `kgmaker check` nad checkoutem.
  Testovací, worker, instalační a renderer joby zůstávají zachované.
- Odstraněné verzované `.kgmaker/GRAPH.md`, `GRAPH.mmd`, `NOTES.md` a
  `semantic.json` se již neobnovují. `.gitignore` ignoruje celý kořenový
  `.kgmaker/`; ostatní lokální historická data nebyla mazána. Git historie
  nadále obsahuje původní verzované artefakty.
- `tests/test_skills.py` odstraňuje jen redundantní kontrolu aktivních kopií
  v checkoutu. Existující test nad dočasným cílem nadále porovnává každý
  instalovaný soubor s templates a ověřuje relativní reference.
  `tests/test_workflow_profiles.py` zachovává kontrolu cílových instrukcí
  a ochrany uživatelských úprav, vypouští jen závislost na kopiích v checkoutu.
  `tests/test_completion.py` používá kopii skutečného inventáře a zadání
  v dočasném cíli namísto plánování nad vývojovým checkoutem.

### Dokumentace, kompatibilita a příklad

README odděluje instalaci balíčku od `cd /path/to/target-project` před init.
Sekce Development popisuje práci bez vlastního indexu. Návody
`docs/agent-skills.md`, `docs/architecture.md` a
`docs/completion-orchestrator.md` popisují izolovanou paritu a vypnutí vlastního
completion workflow. T049 revize 2 přidává S08 a AC13–14; T050 revize 2 mění
umístění parity. T052 zachovává historický kontrakt s aktuální informací
o vypnutí. Registry, stavová matice a acceptance odkazují na tento záznam.

Veřejné CLI/API, runtime schémata a templates v `src/kgmaker/` jsou **bez dopadu**:
funkce se nadále testují a instalují do cílových projektů. Ostatní capability
a CLI příklady jsou **bez dopadu**, protože popisují produkt v cíli, nikoli
vývojovou integraci tohoto checkoutu. T049-S01–S07 tím nejsou dokončené.
Rozpracovaná změna verze v `pyproject.toml` a soubor
`.kgmaker-semantic-patch.json` nejsou součástí této změny.

Příklad vývojového ověření:

```bash
python3 -m pytest -q tests/test_init.py tests/test_skills.py tests/test_workflow_profiles.py
git diff --check
```

### Provedené kontroly

- **PASS:** 111 testů / 0 SKIP / 0 FAIL, 5,19 s, CPython 3.12.0.
  Kvůli dřívější kvótě `/tmp` používá test runner oddělený `TMPDIR` mimo checkout.

  ```bash
  PYTHONDONTWRITEBYTECODE=1 TMPDIR="$validation_dir" python3 -m pytest -q \
    -p no:cacheprovider --tb=short -ra --basetemp "$validation_dir/tmp" \
    --junitxml "$validation_dir/result.xml" \
    tests/test_init.py tests/test_skills.py tests/test_workflow_profiles.py \
    tests/test_completion.py tests/test_completion_handoff.py tests/test_scanner.py
  ```

- **PASS:** Python `tomllib.loads` načetl všech 101 upravených profilů.
- **PASS:** přímý inventář ověřil absenci aktivního hooku, všech cílových
  agentů/skills/commands a verzovaných grafových výstupů; CI už nemá vlastní
  `kgmaker check`. Git hooks obsahují pouze neaktivní sample soubory.
- **PASS:** `git diff -- src/kgmaker workers` je prázdný; templates a worker
  implementace zůstaly nedotčené. `git diff --check` prošel.
- **PASS:** kontrola čísla změny proti lokálnímu registru, `origin/main`,
  vzdálenému main a souborům otevřených PR: maximum 168, přiděleno 169.
- **NOT_RUN:** úplná testovací sada, skutečné compiler/build/Windows ověření
  a živý restart hostitelů. Změna jejich implementace nebyla součástí kroku.
  Self-use příkazy nebyly použity k ověření ani předání.
- **FAIL / příčina neověřená:** GitHub Actions na prvním PR headu `04f75ed`
  evidují neúspěšný [Test](https://github.com/p-rum/kgmaker/actions/runs/45457427415)
  a [PR Review](https://github.com/p-rum/kgmaker/actions/runs/45457427303).
  Joby skončily bez dostupných kroků; log vracel BlobNotFound. Z tohoto stavu
  nelze vyvozovat výsledek testů ani fakturační příčinu.

### Předání a nezávislá kontrola

[PR #153](https://github.com/p-rum/kgmaker/pull/153), větev
`chore/t049-disable-repository-self-use`. První publikovaný head
`04f75edbcb260a72f9d96992cc150b941cb5b25d`, tree
`c4f171c6127cda53903aea59db3f28da3b625337`, odpovídá přesně ověřenému lokálnímu
obsahu bez cizí změny verze. JUnit SHA-256:
`29adf66a5a8aa42949165c9101efad96178edf3915b75279f67b579fac4f18f8`.
Nezávislý code_review pro tento head a uvedenou base vydal obsahové APPROVE,
ověřil všech 148 publikovaných cest, JUnit, metadata 101 profilů a izolaci
cílových instalací. V tomto checkpointu byl PR draft; merge neproběhl.
Následující dokumentační oprava aktualizuje pouze stav PR a pozorované CI.

### Zbývající omezení

Již spuštěná session může mít staré instrukce v paměti; aktuální pokyn uživatele
je nahrazuje a nová session načte upravené profily. Ostatní staré worktree
ani globální nastavení hostitelů se automaticky nepřepisují. Při integraci
otevřených PR je nutné zachovat odstranění vlastních grafů a integrace.
CLI obecně neblokuje manuální init libovolné cesty; toto je změna vývojové
konfigurace repozitáře, nikoli nový runtime zákaz v produktu.

## Integrace aktuálního main — T049-S08 / AC13–AC14, T050-R04

Výchozí head `7c49c136e991df9c8fab2b9a24bccbc612a34d23`, společná base
`edb65e57ca4de1743c810689c78e069cd86b2b41`, integrovaný main
`782ac6ac0287550084e9afadbd6182756fdd2730`. Main mezitím převzal T053
([#154](https://github.com/p-rum/kgmaker/pull/154)) a T054
([#155](https://github.com/p-rum/kgmaker/pull/155)).

Konflikty v `docs/acceptance-inventory.md` a
`docs/production-analysis-progress.md` zachovávají sekce T049, T053 i T054;
stav T053/T054 odpovídá jejich merge. Automatické sloučení zachovává nový
Excel CI job a současně odstranění self-use `kgmaker check`. Ostatní změny
main, včetně instalačního lifecycle, Excelu, jejich testů, dokumentace a
distribuovaných templates, zůstávají zachovány. Veřejné změny T053/T054 jsou
popsány v jejich návodech a change170/171; tato integrace nemění jejich API
ani příklady. README, registr zadání a `docs/agent-skills.md` zachovávají
automaticky sloučený obsah obou větví. Příklad izolovaného ověření je níže.

Provedené kontroly na sloučeném pracovním stromu (CPython 3.12.3, pytest 8.3.4):

- **FAIL, opraveno:** první dva běhy měly chybějící rodič `--basetemp`:
  self-use/instalace 22 PASS / 148 ERROR a Excel 1 SKIP / 18 ERROR.
  Po `mkdir -p /tmp/kgmaker-merge-tests` byly spuštěny znovu:

  ```bash
  PYTHONDONTWRITEBYTECODE=1 /tmp/kgmaker-merge-validation/bin/python -m pytest -q -p no:cacheprovider --tb=short -ra --basetemp /tmp/kgmaker-merge-tests/self-use tests/test_init.py tests/test_skills.py tests/test_workflow_profiles.py tests/test_completion.py tests/test_completion_handoff.py tests/test_scanner.py tests/test_installation.py
  PYTHONDONTWRITEBYTECODE=1 /tmp/kgmaker-merge-validation/bin/python -m pytest -q -p no:cacheprovider --tb=short -ra --basetemp /tmp/kgmaker-merge-tests/excel tests/test_excel_migration.py
  PYTHONDONTWRITEBYTECODE=1 /tmp/kgmaker-merge-validation/bin/python -m pytest -q -p no:cacheprovider --tb=short -ra --basetemp /tmp/kgmaker-merge-tests/distribution tests/test_installation_distribution.py
  ```

- **PASS:** první příkaz 170 PASS / 0 SKIP; třetí 1 PASS, včetně wheelu a
  instalace do odděleného projektu. Druhý: 8 PASS / 11 SKIP (worker není
  sestaven, wheel smoke nebyl vyžádán).
- **PASS:** 101 profilů načteno `tomllib`; `git ls-files` nepotvrdil návrat
  odstraněných aktivních hooků, skillů, agentů, Junie commands ani grafů.
  `git diff --check` a `git diff --cached --check` bez chyb.
- **NOT_RUN:** úplná sada, Excel worker/wheel smoke, Windows, compiler/build
  matice a živý restart hostitelů. Dosavadní review se vztahuje k původnímu
  headu, nikoli k tomuto merge; nové nezávislé review a kontrola CI zbývají.
- Historické Actions Test a PR Review vracely při novém dotazu logů HTTP 404;
  jejich příčina nadále není ověřená.
