# T048-S01 — Sjednocení současného delivery inventáře

- Task/Step: **T048 / T048-S01**; acceptance **T048-AC01**.
- Datum: 2026-11-07.
- Výchozí SHA: `f115aa4a1c37683f3be9e4607111d51d9c1301c1` (main po PR88).
- Větev: `docs/t048-reconcile-delivery-status`.
- Dodání tohoto kroku: **PR_OPEN** po publikaci samostatného PR;
  ověření inventáře **VERIFIED_IN_SCOPE**, funkční acceptance programu **NOT_RUN**.

## Problém a skutečné změny

Stavové dokumenty obsahovaly aktuálně formulované draft/review-pending věty i pro
již sloučené PR. T048-S01 vyžaduje jeden současný stav každé atomické položky.

- `docs/production-analysis-progress.md`: přidán aktuální inventář 60 T003
  balíčků, 40 T004 úkolů, šesti T046 etap a 13 T047 kroků. Každý řádek má
  delivery/verification, evidence SHA, zdroje/testy, PR, omezení a další krok.
  T047 řádky uvádějí upstream vlastníka, sdílená práce se nesčítá jako nová funkce.
  Součty 37+24 MERGED jsou delivery, nikoli počet úplně ověřených schopností.
- Zaznamenány přesné base/head páry sedmi otevřených PR. Šest T046 PR má nyní
  `mergeable=true`, `draft=false`, `mergeable_state=unstable`; starší T048 údaj
  o konfliktu PR41 je historický. GH CI ani nezávislé review nejsou tímto PASS.
- Zkontrolováno 92 remote refs včetně origin/HEAD. Mimo šest T046 větví mají
  pouze PR4 a `feat/compiler-workers` nesloučené topologické merge commity;
  oba zbytkové patche proti společnému předkovi jsou prázdné. PR4 nebyl uzavřen.
- README, capability dokumentace, registr a acceptance odkazují na současný
  inventář; T020 je MERGED, topology/explain zůstávají JSON-only. T031/T032
  jsou dodané knihovní kontrakty, T034 CLI zůstává plánované.
- Starý obsah stavové a acceptance matice je zachován jako explicitně historický.
  Historické výsledky v capability dokumentech zůstávají označeny podle checkpointu.

## Rekognoskace a kompatibilita

Přečteny AGENTS, copilot instructions, registr, T048, T047 a instrukce
kgmaker-architect. Rekognoskace proběhla přímo, bez spouštění dalších agentů.
Původně chyběl strojový graf; `status` a `memory recall` to přiznaly. Následný
explicitní `scan --no-docs` vytvořil lokální source-only index bez workerů.
Grafové query a zdroje potvrdily existující architecture CLI/renderery/projekce.
Omezení stale semantic evidence v README bylo výslovně reportováno scanem.
První memory capture a semantic validate odmítly zastaralé dokumentační hashe.
Následný obsahově vázaný update znovu ověřil 17 dotčených konceptů a 42 vazeb:
zachoval identity/druhy/confidence, upravil citované řádky a historické pending
souhrny. Nevznikly nové technické vazby; staré immutable epizody zůstaly přesné.
Poté byla přidána jedna epizoda tohoto dokumentačního auditu.

Žádná změna veřejného API, parser arguments, graph/store schema, workerů nebo
runtime IDs. Vytvořen pouze lokální task intake pro audit; není to nezávislé review.
Původní zadání a jejich acceptance nebyly zmenšeny.

## Dokumentační dopad

| Plocha | Změna / konkrétní bez dopadu |
|---|---|
| README | Opraven současný merge stav T013/T014/T016–T020/T025/T026/T030–T033/W05/W07/W08 a odkaz na inventář. |
| Capability/API návody | Aktualizován delivery status v architecture-json-cli, interface-contracts, interface-markdown, kafka-retry-dlt, process-annotations, process-catalog, process-label-packets, process-paths, process-review-store, remote-contract-mapping, remote-interfaces, schema-compatibility, service-topology, topology-filter a view-explanation. Historické výsledky zachovány. |
| CLI příklady | Bez změny syntaxe; skutečné architecture help výstupy potvrzují interfaces JSON/Markdown a topology/explain JSON. Příklady zůstávají platné. |
| Stav / acceptance | Aktuální souhrn + 119 řádků; historické checkpointy odděleny. |
| Registr | T020 delivery opraven; T046 odkaz vede na skutečné existující zadání ve větvi PR41. |
| Templates / spravované instrukce | Bez dopadu: žádná změna instalovaného chování či pravidel init. |
| Graf / semantic | Lokální index obnoven explicitním scanem; scoped patch revaliduje 17 konceptů/42 vazeb bez změny jejich identit. Memory capture přidává jednu epizodu, staré epizody zachovány. Generované sdílené grafy nejsou ručně upraveny. |

## Přesné kontroly

| Kontrola | Výsledek |
|---|---|
| GitHub GET `/repos/p-rum/kgmaker/pulls?state=all&per_page=100` a jednotlivé GET PR4/40–45 | PASS: skutečné metadata a všech sedm párů načteny; výsledky CI z toho neodvozovány. |
| `git for-each-ref --format='%(refname:short)' refs/remotes/origin`; `git rev-list --count main..REF` a ancestry kontroly | PASS: 92 refs, osm topologicky ahead větví, šest funkčních T046 větví s otevřenými PR. |
| `git diff main...origin/feat/evidence-production-scope`; `git diff main...origin/feat/compiler-workers` | PASS: oba prázdné; konkrétní nesloučené merge commity jsou v inventáři. |
| `git diff --name-only 250e7c1 main` + kontrola historie main | PASS: po výchozím T020 pouze T048/governance; funkční součty nezměněny. |
| `python /tmp/validate_kgmaker_audit.py`: 119 unikátních ID, součty a existence 271 nových lokálních/branch odkazů, zachování starých matic | PASS; validační postup neinstaluje nástroje ani nepouští worker. Skript je lokální jednorázový audit, nikoli nový unit test. |
| `PYTHONPATH=src python -m kgmaker scan --no-docs` | PASS source-only: 521 souborů, 5287 deklarací/sekcí, 42538 vztahů; stale semantic warnings přiznány. |
| `PYTHONPATH=src python -m kgmaker query 'architecture topology process workflow cache' --limit 5` | PASS: nalezeny existující flow/architecture symboly, ověřeny ve zdroji. |
| `PYTHONPATH=src python -m kgmaker memory recall 'T048 delivery status' --token-budget 500` | PASS po explicitním scan; historické epizody označeny HISTORICAL. |
| `PYTHONPATH=src python -m kgmaker architecture interfaces --help`, `topology --help`, `explain --help` | PASS; formáty JSON/Markdown pouze interfaces. |
| `git diff --check` | PASS. |
| `PYTHONPATH=src python -m kgmaker semantic update --base main --token-budget 2000`, následný scoped patch, `semantic apply`, `semantic validate` | PASS po výslovné revalidaci 17 konceptů/42 vazeb; první stale odmítnutí zůstává přiznáno výše. |
| `PYTHONPATH=src python -m kgmaker memory capture --base main --validation delivery-inventory=passed --validation cli-help=passed --validation diff-check=passed`; závěrečný `scan --no-docs` | PASS po semantic update; jedna nová epizoda, všechny staré přesné. |
| `python -m pytest --version` | NOT_RUN test suite: pytest není v novém prostředí instalován. Pro čistou dokumentaci nebyl instalován a nevznikly textové unit testy. |
| Plná pytest/compiler/Windows/parser/runtime/DB acceptance a GH CI | NOT_RUN; tento audit ji nepřenáší z historických výsledků. |

## Příklad a zbývající práce

T020 byl v registru „final review pending“, přestože PR87 již byl merged.
Aktuální řádek uvádí MERGED / PARTIAL, přesný integrační SHA, renderer/CLI a
původní test soubor; novou úplnou acceptance netvrdí. T021 zůstává PLANNED a
uvádí chybějící upstream W09 místo opakované implementace existujícího T019.

Další krok je T048-S02: existující T046 stack zachovat, skutečně ověřit jeho
kontrakty proti dnešním rodičům a předat nezávislému exact-pair review. Merge
implementátorovi T048 nepovoluje. Potom pokračovat závislostmi T048-S03–S08;
39 T003/T004 položek bez sloučené dodávky, live DEFERRED a T047 tímto nejsou hotové.
