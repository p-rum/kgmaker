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

## Druhá integrace main — T049-S08 / AC13–AC14, T050-R04

Výchozí head `3e22595a7ca59b960ef8ca3f46eca73f84ee858b`, integrovaný main
`5809e84932b1910bfc3f17c72e2a2005283389b1`. Main přijal
[#136](https://github.com/p-rum/kgmaker/pull/136) a současně změnil tři
historické vlastní grafy. Konflikty modify/delete u `.kgmaker/GRAPH.md`,
`.kgmaker/GRAPH.mmd` a `.kgmaker/semantic.json` řeší jejich odstranění;
runtime zdroje, testy a návody z #136 zůstávají. Stavová matice zaznamenává
merge #136; acceptance a README zachovávají automaticky sloučený obsah.
Bez dalších změn veřejného API a příkladů. Nezařazené lokální Gradle soubory
zůstávají mimo commit.

- **PASS:** po druhé integraci 171 testů / 0 SKIP:
  `PYTHONDONTWRITEBYTECODE=1 /tmp/kgmaker-merge-validation/bin/python -m pytest -q -p no:cacheprovider --tb=short -ra --basetemp /tmp/kgmaker-merge-tests/self-use-final tests/test_init.py tests/test_skills.py tests/test_workflow_profiles.py tests/test_completion.py tests/test_completion_handoff.py tests/test_scanner.py tests/test_installation.py tests/test_installation_distribution.py`.
- **FAIL, opraveno nastavení prostředí:** runtime příkaz nejprve použil JDK 17
  a skončil 73 PASS / 1 SKIP / 12 ERROR při `javac --release 21`. S `JAVA_HOME`
  na JDK 21, avšak starým `PATH`, následovalo 73 PASS / 13 SKIP kvůli detekci
  staršího Java. S JDK 21 i v `PATH`:

  ```bash
  JAVA_HOME=/usr/lib/jvm/temurin-21-jdk-amd64 PATH=/usr/lib/jvm/temurin-21-jdk-amd64/bin:$PATH PYTHONDONTWRITEBYTECODE=1 /tmp/kgmaker-merge-validation/bin/python -m pytest -q -p no:cacheprovider --tb=short -ra --basetemp /tmp/kgmaker-merge-tests/runtime-jdk21-path tests/test_runtime_trace_producer.py
  ```

  **PASS/SKIP:** 73 PASS / 13 SKIP; chybí sestavený JVM worker a Maven exporter.
  Aktuální integrace nedokládá jejich reálný běh, Windows ani úplnou sadu.
- **PARTIAL:** CodeQL po první integraci nenašel Python nálezy; Actions upozornil
  na chybějící omezení `GITHUB_TOKEN` u Excel jobu zděděného z main. Tento job
  PR nemění; nález zůstává neopraven. Analýza dalších jazyků vypršela.
- **NOT_RUN:** nové nezávislé review a CI nad integrovaným headem. Původní
  APPROVE se na tento merge nepřenáší.

## Třetí integrace main — T049-S08 / AC13–AC14, T050-R04

Výchozí head `d52b32aeca91840c778a3af0931f8dd10b0d6305`, společná base
`5809e84932b1910bfc3f17c72e2a2005283389b1`, integrovaný main
`5d067f152522442fa4cff22c2e69e1b9b6fcef86`. Main přinesl mimo jiné T055,
ověřené completion závislosti a změny compiler evidence.

Konflikty v `README.md`, `docs/acceptance-inventory.md`,
`docs/agent-skills.md`, `docs/production-analysis-progress.md` a
`tests/test_skills.py` zachovávají zákaz self-use i nové T055 a jeho test
instalace v odděleném projektu. Tři konfliktní vlastní grafy `.kgmaker/GRAPH.md`,
`.kgmaker/GRAPH.mmd` a `.kgmaker/semantic.json` zůstávají odstraněné.
Ostatní změny main se slučují bez úprav; produktové templates a nové
completion chování zůstávají dostupné cílovým projektům. Veřejné API ani
CLI tato integrace nemění; příslušné návody, registr a příklady přicházejí
z main. Příklad: test upgrade Excel skillu používá `tmp_path`, nikoli checkout.

Kontroly na sloučeném stromu, Python 3.12 a pytest 8.3.4 v `/tmp`:

- **PASS:** `PYTHONDONTWRITEBYTECODE=1 /tmp/kgmaker-merge-153-venv/bin/python -m pytest -q -p no:cacheprovider --tb=short -ra --basetemp /tmp/kgmaker-merge-153-self tests/test_init.py tests/test_skills.py tests/test_workflow_profiles.py tests/test_completion.py tests/test_completion_handoff.py tests/test_scanner.py tests/test_installation.py` — 177 PASS.
- **PARTIAL:** `PYTHONDONTWRITEBYTECODE=1 /tmp/kgmaker-merge-153-venv/bin/python -m pytest -q -p no:cacheprovider --tb=short -ra --basetemp /tmp/kgmaker-merge-153-incoming tests/test_excel_migration.py tests/test_reverse_dependency_index.py tests/test_symbol_identity.py tests/test_t012_catalog_kafka_interfaces.py tests/test_workflow.py tests/test_workspace.py` — 62 PASS / 142 SKIP; chybí Excel worker, JDK 21, některé Spring fixture a explicitní wheel smoke.
- **PASS:** `git diff --check`, `git diff --cached --check`, načtení 101 profilů
  pomocí `tomllib`, kontrola odstraněných self-use cest a absence `kgmaker check`
  v test workflow.
- **NOT_RUN:** úplná sada, skutečný Excel/compiler worker, Windows, živí hostitelé
  a nezávislé review nového merge. Historické CI logy opět vracejí HTTP 404;
  nové běhy pro předchozí head při kontrole probíhaly. Jejich výsledek není PASS.
  Aktuální merge vyžaduje nové review a ověření CI; starší APPROVE se nepřenáší.

## Čtvrtá integrace main — T049-S08 / AC13–AC14, T050-R04

Výchozí head `51aa32c3053405ef5b1dc618ff98d355609a885a`, společná base
`5d067f152522442fa4cff22c2e69e1b9b6fcef86`, integrovaný main
`5ff2c0846056353605ccb9ab271bd86847c6e661`. Cílem je vyřešit konflikty
bez návratu self-use a zachovat nově sloučené změny Excelu, cache a evidence.

Konflikty v `docs/acceptance-inventory.md` a
`docs/production-analysis-progress.md` zachovávají sekce T049-S08 i T056
a zpřesněné doklady T053 a T003-S13-W02 z main. Tři vlastní grafy
`.kgmaker/GRAPH.md`, `.kgmaker/GRAPH.mmd` a `.kgmaker/semantic.json` zůstaly
odstraněné. Ostatní soubory včetně `README.md`, registru, produktových
templates, workeru, testů a návodů jsou sloučené z obou větví bez další
úpravy. Integrace nemění veřejné API ani příklady; např. test instalace
skillů nadále vytváří oddělený cílový projekt.

- **PASS:** `PYTHONDONTWRITEBYTECODE=1 /tmp/kgmaker-merge-20261126/bin/python -m pytest -q -p no:cacheprovider --tb=short -ra --basetemp /tmp/kgmaker-merge-20261126-self tests/test_init.py tests/test_skills.py tests/test_workflow_profiles.py tests/test_completion.py tests/test_completion_handoff.py tests/test_scanner.py tests/test_installation.py` — 177 PASS.
- **PARTIAL:** `JAVA_HOME=/usr/lib/jvm/temurin-21-jdk-amd64 PATH=/usr/lib/jvm/temurin-21-jdk-amd64/bin:$PATH PYTHONDONTWRITEBYTECODE=1 /tmp/kgmaker-merge-20261126/bin/python -m pytest -q -p no:cacheprovider --tb=short -ra --basetemp /tmp/kgmaker-merge-20261126-main tests/test_excel_migration.py tests/test_stage_content_cache.py tests/test_stage_content_cache_actual.py tests/test_t012_catalog_kafka_interfaces.py` — 82 PASS / 132 SKIP; chybí workery, Spring fixture a explicitní wheel smoke.
- **FAIL / blocked:** `mvn -o -B -ntp -C -f workers/excel/pom.xml package`
  nemohl offline načíst Maven resources plugin 3.5.0, který není v cache;
  Excel worker nebyl ověřen.
- **PASS:** `git diff --cached --check`, načtení 101 profilů pomocí `tomllib`,
  inventář sledovaných self-use cest a kontrola absence `kgmaker check` v CI.
- **CI:** historický [push běh](https://github.com/p-rum/kgmaker/actions/runs/45616987337)
  na `d52b32a` selhal při stahování Maven pluginu kvůli HTTP 429; pozdější
  [PR běh](https://github.com/p-rum/kgmaker/actions/runs/45616997950) pro
  tento starší head skončil success. Běh pro `51aa32c` byl action_required
  bez jobů; nový merge není tímto výsledkem ověřen.
- **NOT_RUN:** úplná sada, Windows, živí hostitelé a nezávislé review nového
  merge. Předchozí review se na nový head nepřenáší.

## Pátá integrace main — T049-S08 / AC13–AC14, T050-R04

Výchozí head `cde1428eb008fcc055b9286cc5089384afc41d18`, společná base
`5ff2c0846056353605ccb9ab271bd86847c6e661`, integrovaný main
`49bab32c50436782a2009455a36ada41c06be42f`. Main se během předchozí
integrace posunul o #164. Konflikty tří vlastních grafů `.kgmaker/GRAPH.md`,
`.kgmaker/GRAPH.mmd` a `.kgmaker/semantic.json` řeší jejich odstranění.
Příchozí změna cache Linux JDK a její testy i návody se slučují bez úprav.
Veřejné API, registr a příklady se tímto řešením nemění; kompatibilita a
omezení příchozí změny jsou popsány v [change180](180_bindLinuxJdkNativeInputs.md).

- **PARTIAL:** `JAVA_HOME=/usr/lib/jvm/temurin-21-jdk-amd64 PATH=/usr/lib/jvm/temurin-21-jdk-amd64/bin:$PATH PYTHONDONTWRITEBYTECODE=1 /tmp/kgmaker-merge-20261126/bin/python -m pytest -q -p no:cacheprovider --tb=short -ra --basetemp /tmp/kgmaker-merge-20261126-cache tests/test_stage_content_cache.py tests/test_stage_content_cache_actual.py` — 69 PASS / 9 SKIP; JVM a TypeScript workery chybí.
- **PASS:** `git diff --cached --check`; inventář sledovaných self-use cest
  je prázdný.
- **NOT_RUN:** úplná sada, skutečné workery, Windows, CI a nezávislé review
  nového merge. Předchozí testy a review nejsou důkazem celého nového headu.
