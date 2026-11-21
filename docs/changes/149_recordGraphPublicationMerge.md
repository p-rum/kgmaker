# Doložený merge souběžné publikace grafu

## T003-S10-W06, kroky 1–5, AC01–AC04 a T003-AC10

Výchozí SHA `fad4fc63c76f0f9ef5a1a292e279d1269bd84540`. Souběžné publikace mohly před opravou
přepsat novější generaci grafu nebo ponechat report po neúspěšném zápisu.
[#129](https://github.com/p-rum/kgmaker/pull/129) je MERGED jako `c067f9c3c7b3266842fc4f2230b4eaf65182e4df` do `main`.
GitHub vrátil rodiče `fad4fc63c76f0f9ef5a1a292e279d1269bd84540` a `32e933d61d0dfe0dfbe11fef754fa2016207402f` a výsledný tree
`570a6590eda49cdb2b8b8c1168f0c78655af7aca` je totožný s ověřeným kandidátem.

- **Krok 1, AC01.** [Change144](144_serializeGraphPublication.md) eviduje
  reprodukce staršího zápisu během práce s novější generací a proloženou
  publikaci s vedlejšími výstupy. Výchozí testy měly doložené RED výsledky.
- **Krok 2, AC02.** `store.py` koordinuje očekávanou generaci v existující
  zapisovací vrstvě. `build_runner.py` obsazuje adresář plánu atomicky.
  Původní schémata v1/v2/v3 zůstávají čitelná a nepotřebují migraci.
- **Krok 3, AC01 a AC03.** Scan, runtime import a workspace používají
  kontrolu generace. Confluence související výstupy se po výjimce vracejí.
  Reportované compiler důkazy a dostupnost drží původní hranici.
- **Krok 4, AC01–AC03.** [Regrese souběhu](../../tests/test_graph_publication_concurrency.py),
  [dva skutečné workery](../../tests/test_stage_content_cache_actual.py) a
  [atomický claim build plánu](../../tests/test_build_runner.py) prošly v
  ověřené Linux sadě. Například druhý `kgmaker scan` se starou generací
  vrátí kód 3 a novější publikovaný graf zůstane dostupný.
- **Krok 5, AC04.** Tento záznam aktualizuje [acceptance](../acceptance-inventory.md)
  a [stavovou matici](../production-analysis-progress.md). Příklady a rozhraní
  zůstávají podle [README](../../README.md), [cache CLI](../stage-content-cache.md)
  a [compiler inspection](../compiler-inspection.md). Samotný krok evidence
  mění dokumentaci a generovaný graf.

### Ověření a limity

- PASS — `python -m pytest --basetemp <oddělený dočasný adresář> -o tmp_path_retention_policy=failed -p no:cacheprovider -q --tb=short -ra --maxfail=1 --junitxml=.kgmaker/workflow/w06-full.xml`, 3692 PASS / 1 SKIP.
  Přeskočeno `test_actual_windows_smoke_uses_restricted_token_and_paths_with_spaces` (real non-admin Windows CI smoke is an explicit gate). Běh používal `KGMAKER_REQUIRE_WORKERS=1`,
  `KGMAKER_REQUIRE_K2=1`, `KGMAKER_REQUIRE_EXPORTERS=1` a
  `KGMAKER_REQUIRE_MARKDOWN_PARSER=1`, JDK 21/22, Kotlin K1/K2, TypeScript,
  Gradle 8.13 a Maven 3.9.9. Vstupní a výstupní manifest byly shodné.
- PASS — JUnit SHA-256 `c28752846d133b3be8cd6719a4c5007de209fb6fcc453a138be6848ff89e44d0`. SHA-256 manifestu
  `718b313635aa501af322ff87732cc987e2918f6209822af1c713dacdeed8cc82` a logu `c863a8c3ddead1b172f6aac47fcce1de6a1699d1899a3978d0f5336418ca3e1f`.
  Cílené current W06 a Mermaid testy 46 PASS / 0 SKIP. Obě nezávislá
  lokální review i projektový T045 souhlas doložené nad aktuálním headem.
  Lokální graph/status a diff PASS. Záznam finálních kontrol i serverového
  merge je také v [PR #129](https://github.com/p-rum/kgmaker/pull/129).
- GitHub Actions NEOVĚŘENO. Tři běhy neměly zaznamenané kroky ani runner,
  tři vzorkované logy vrátily 404. Samostatný Windows běh NOT_RUN.
  Obnova procesního pádu mezi výměnami zůstává T047-S05 a warm replay #116.

### Kontroly kroku evidence

Base tohoto dokumentačního kroku je `c067f9c3c7b3266842fc4f2230b4eaf65182e4df`.
`python -m pytest -p no:cacheprovider -q tests/test_completion.py` má
7 PASS. `kgmaker completion plan --jobs 3` vrací pro W06
`MERGED / VERIFIED_IN_SCOPE`, akci `none` a prázdné blokery. `kgmaker scan`,
`kgmaker status`, `kgmaker check`, `kgmaker semantic validate`,
`git diff --check` a `git diff --cached --check` prošly. Úplná sada pro
samostatný dokumentační krok je NOT_RUN, zdroj kódu a testů odpovídá #129.
