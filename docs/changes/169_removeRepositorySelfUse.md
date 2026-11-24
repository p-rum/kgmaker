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
- **NOT_RUN:** úplná testovací sada, skutečné compiler/build/Windows joby,
  hostované GitHub Actions a živý restart hostitelů. Změna jejich implementace
  nebyla součástí kroku. Self-use příkazy nebyly použity k ověření ani předání.

### Zbývající omezení

Již spuštěná session může mít staré instrukce v paměti; aktuální pokyn uživatele
je nahrazuje a nová session načte upravené profily. Ostatní staré worktree
ani globální nastavení hostitelů se automaticky nepřepisují. Při integraci
otevřených PR je nutné zachovat odstranění vlastních grafů a integrace.
CLI obecně neblokuje manuální init libovolné cesty; toto je změna vývojové
konfigurace repozitáře, nikoli nový runtime zákaz v produktu.
