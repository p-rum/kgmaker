# Výhradní publikace grafu a build snapshotu

T003-S10-W06 kroky 1–5, AC01–AC04, výchozí `main`
`17e9e7368e6cc2d6550983c3039eb39debd65424`.
Souběžné ukládání mohlo vstoupit mezi kontrolu a výměnu odvoditelných souborů.
Odděleně mohl `scan` přepsat generation, kterou druhý zapisovač commitnul
až po prvním načtení starého grafu.

- **Kroky 1–3.** `store.py` koordinuje zapisovače pod existující
  `.kgmaker/workflow/` a validuje očekávanou generation před zápisem.
  `inspection.py`, `cli.py`, `project_cli.py`, `runtime_evidence.py` a
  `workspace_cli.py` zachycují generaci před čtením nebo odvozením grafu.
  `confluence.py` připraví snapshot exportu v paměti. Report a index jsou součástí společného zápisu s rollbackem.
  Report nesmí ukazovat na soubory
  spravovaného stavu grafu. `build_runner.py` atomicky obsadí adresář plánu před
  inicializací snapshotu. Schéma a offline chování scan/hook jsou zachované.
- **Krok 4.** `test_graph_publication_concurrency.py` samostatně reprodukuje
  proloženou publikaci, zastaralý scan, runtime import, migraci, workspace
  scan, Confluence výstupy a odmítnutí kolidujícího reportu. Doplňkové testy ověřují proloženou publikaci
  dvou kandidátů ze skutečných workerů a opakovaný claim stejného build plánu.
  Existující cache kontroly pokrývají poškozené payloady, v1/v2/v3,
  zachování poslední generace, strict PARTIAL, výjimku a zrušení.
- **Krok 5.** [README](../../README.md), [cache CLI a limity](../stage-content-cache.md),
  [compiler inspection](../compiler-inspection.md), [acceptance](../acceptance-inventory.md)
  a [stavová matice](../production-analysis-progress.md) popisují přesný rozsah.
  Instalované instrukce a init už ignorují `.kgmaker/workflow/`. Projektová
  API a čitelnost dřívějších schémat jsou zachované.

Příklad při proloženém `kgmaker scan` vrátí druhý neúspěšný pokus kód 3.
Po dokončení druhé publikace lze původní `kgmaker scan` opakovat.

- RED: nad výchozím checkoutem `PYTHONPATH="$PWD/src" python -m pytest -c
  /dev/null -p no:cacheprovider -q /tmp/kgmaker-w06-six-red.py`, kam se
  zkopíroval `tests/test_graph_publication_concurrency.py`, 7 FAIL.
- GREEN: `python -m pytest -p no:cacheprovider -q
  tests/test_graph_publication_concurrency.py tests/test_build_aware.py
  tests/test_workspace.py tests/test_stage_content_cache.py
  tests/test_graph_provider.py tests/test_confluence_configuration.py
  tests/test_confluence_sync.py tests/test_scanner.py
  tests/test_methodology_conflicts.py`, 149 PASS / 0 SKIP.
- `python -m pytest -p no:cacheprovider -q -rs tests/test_build_runner.py
  tests/test_stage_content_cache_actual.py`, 19 PASS / 0 SKIP se skutečnými
  workery K1/K2 a TypeScript, Maven 3.9.9 a JDK 21/22.
- Úplná sada, nezávislé T045 a Windows souběh v této revizi zatím NOT_RUN.
  Pád procesu se zámkem fail closed. Obnova lidských pohledů po pádu
  mezi dvěma výměnami má samostatný rozsah T047-S05 a nelze ji odvodit ze
  souběžných zápisů. Workspace může před odmítnutím grafu uložit platné
  samostatné cache záznamy klíčované obsahem. Obnovení výkonového cache
  replay řeší #116.

## Kroky 1–5 / AC01–AC04 — dvojí oprava nesouladu po review

Výchozí kandidát má tree `19446b42442e44b03a796cd276e74fef671f7af5` nad
`main` `17e9e7368e6cc2d6550983c3039eb39debd65424`.

1. Reálný Confluence scan při injektované chybě posledního `os.replace`
   zachoval starý graf a přesto zanechal novější report i index. Při skutečném
   importu runtime manifestu schema 1 do grafu schema 3 mohl jinak platný
   explicitní starý graf přepsat nově uložený compiler kontext.
2. [Confluence editor](../../src/kgmaker/confluence.py) vrací připravený text
   reportu a indexu do [CLI](../../src/kgmaker/cli.py). CLI je předává jako
   obyčejné výstupy do stávající [publikace](../../src/kgmaker/store.py).
   Store připraví a hlídá všechny výstupy i jejich rollback kopie. Každý
   dočasný soubor leží vedle svého cíle. `graph.json` se vymění poslední.
   Nové výstupy a prázdné adresáře vytvořené tímto zápisem se při výjimce
   uklidí. Rezervované soubory a kolidující adresáře se odmítnou. Samostatné
   `kgmaker docs check` používá tytéž formáty a vlastní zápis.
3. [Runtime import](../../src/kgmaker/runtime_evidence.py) přečte generaci
   před načtením uloženého grafu. Při existujícím store porovná obsah dodaného
   grafu s jeho autoritativní deserializovanou kopií a používá tuto kopii.
   Nesoulad vrací `STALE` s kódem 3. Shodný explicitní vstup i explicitní seed
   bez store zůstávají podporované. Závěrečný compare-and-swap platí i při
   souběhu po validaci manifestu. Schémata, flags a offline režim se nemění.
4. [Regrese](../../tests/test_graph_publication_concurrency.py) obsahují
   skutečný ingest s dříve existujícími i dosud chybějícími výstupy, relativní
   a absolutní cesty a alias přes symlink. Injekce `EXDEV`, pokud staging
   soubor neleží v adresáři cíle, ověřuje umístění a pořadí výměn. Schema 3
   fixture odmítá explicitní starý graf a přijímá shodný. Stávající
   [test seedu](../../tests/test_build_aware.py) pokrývá první import.
5. Aktualizovány [README](../../README.md), [cache CLI](../stage-content-cache.md),
   [compiler inspection](../compiler-inspection.md), [acceptance](../acceptance-inventory.md)
   a [stavová matice](../production-analysis-progress.md). Úplná sada, nový
   Windows běh, obnova po pádu mezi výměnami a samostatný nezávislý re-review
   tohoto stromu jsou NOT_RUN. Sdílenou transakci používá Confluence výstup
   vyvolaný `scan`. Cizí zapisovač nemusí respektovat lock a provozní
   zotavení po pádu zůstává mimo tento krok.

- RED — `PYTHONPATH=src python -m pytest -p no:cacheprovider -q --tb=short tests/test_graph_publication_concurrency.py -k 'commit_failure or stale_supplied'`
  na předchozím zdroji, 3 očekávané FAIL. Obě Confluence varianty změnily
  související soubory a schema 3 runtime import nevyvolal požadovaný konflikt.
- GREEN — 250 PASS / 0 SKIP za 83,67 s. Běh použil JDK 21.0.13.1 a 22.0.1,
  skutečné workery Kotlin 2.1.10 K1/K2 a TypeScript 5.7.3, Maven 3.9.9 a
  existující lokální Maven cache. Parametry `KGMAKER_REQUIRE_WORKERS=1`,
  `KGMAKER_REQUIRE_K2=1`, `JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64`,
  `JAVA_TOOL_OPTIONS=-XX:-UsePerfData`, `KGMAKER_TEST_OTHER_JAVA_HOME=/home/petra/.jdks/openjdk-22.0.1`
  a `PYTHONPATH=src`. Přesný výběr testů:

  ```bash
  python -m pytest -p no:cacheprovider -q --tb=short -ra \
    --basetemp .kgmaker/workflow/pytest-w06-review2 \
    tests/test_graph_publication_concurrency.py tests/test_build_aware.py \
    tests/test_workspace.py tests/test_stage_content_cache.py tests/test_graph_provider.py \
    tests/test_confluence_configuration.py tests/test_confluence_sync.py tests/test_scanner.py \
    tests/test_methodology_conflicts.py tests/test_build_runner.py \
    tests/test_stage_content_cache_actual.py tests/test_runtime_trace_producer.py
  ```

- PASS — `kgmaker semantic update --base HEAD`, reanchor z čisté baseline,
  `kgmaker semantic apply`, `kgmaker memory capture --base HEAD`,
  `kgmaker semantic validate`, `kgmaker scan`, `kgmaker status`,
  `kgmaker check`, `git diff --check` a `git diff --cached --check`.
