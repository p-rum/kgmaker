# Oprava Pythonu a coverage v automatickém PR review

## T045-S03 / T045-R01 a T045-AC04

Výchozí `main` má SHA `4011825b15e4b65e1f57576a0986ca05b3cf810e`.
Na [#137](https://github.com/p-rum/kgmaker/pull/137) měl krok Requirements
Analysis chybu odsazení uvnitř `with`. Testovací krok instaloval `coverage`
bez adaptéru pro příznaky `pytest --cov`. Výchozí shell navíc předával
výsledek `tee`, takže chyba pytestu mohla skončit s prázdným coverage a
úspěšným stavem kroku.

První kandidát `b6ff24f2ee23133e65561b8ae602896078e291b3` přidal do
[workflow PR Review](../../.github/workflows/pr-review.yml) `pytest-cov` a
opravil odsazení vloženého Pythonu. Testovací krok používá
explicitní Bash s `pipefail`. Uloží výpis a hodnotu coverage a poté vrátí
stav pipeline. Při chybě pytestu s úspěšným zápisem výpisu je to stav
pytestu. `continue-on-error` zachovává pokračování workflow a revizní
souhrn vidí skutečný `steps.tests.outcome`.

[README](../../README.md#development) popisuje doplňující workflow.
[Inventář acceptance](../acceptance-inventory.md#t045--doplňující-automatická-kontrola-pr)
a [stavová matice](../production-analysis-progress.md) zaznamenávají
lokální ověření. Rozsah opravy je krok workflow v GitHub Actions.
Projektové schvalování dál používá [T045](../tasks/45_addCodeReviewAgent.md).

### Kontroly prvního kandidáta v Cloud Environment

- RED — původní vložený Python končí `IndentationError` při kompilaci
  přesného bloku `run`. Původní testovací krok s `coverage` bez
  `pytest-cov` hlásí neznámý argument `--cov`, končí stavem 0 a vrací
  prázdný výstup coverage.
- PASS — `/workspace/kgmaker-tools/pr-review-venv311/bin/python /workspace/kgmaker-evidence/pr-review-ci-smoke.py`.
  Harness načte skutečný YAML a kompiluje přesný nový blok v CPythonu
  3.11.18. Lokálně spouští pouze vyňatý testovací krok v dočasné fixture.
  Používá `bash --noprofile --norc -e -o pipefail` jako explicitní Bash
  v Actions.
  - Zelená fixture vrací stav 0, `coverage=100`, XML coverage a výpis
    v souhrnu.
  - Fixture s úmyslně chybným očekáváním vrací stav 1 a zachová
    `coverage=100`, XML i výpis.
  - Varianta bez pluginu vrací stav 4, diagnostiku a fallback `coverage=0`.
    Fallback označuje chybějící měření.
  - SHA-256 harnessu `90d75b39b0e3c7a13fe279488963dfba5809f3b43d3524a7a3b92cd491877864`,
    logu `776524b11d96860a84b339033a5a14875676ca99bdc6852d976a64deb656c31f`.
- PASS — 64 cílených testů a 0 SKIP v CPythonu 3.11.18 s pytest 9.2.0
  a pytest-cov 7.1.0. Coverage XML se vytvořilo. SHA-256 JUnit
  `8c9bde48a33d5b508ae12c445c1e8e179e41b7eb0f8abe2bdea7f972ea2631c8`.

  ```bash
  export COVERAGE_FILE=/workspace/kgmaker-evidence/pr-review-ci-repo.coverage
  PYTHONPATH=src /workspace/kgmaker-tools/pr-review-venv311/bin/python -m pytest -p no:cacheprovider -q \
    --cov=src --cov-report=xml:/workspace/kgmaker-evidence/pr-review-ci-repo-coverage.xml \
    --cov-report=term --basetemp /workspace/kgmaker-evidence/pr-review-ci-pytest \
    --junitxml=/workspace/kgmaker-evidence/pr-review-ci-repo.xml \
    tests/test_completion.py tests/test_completion_handoff.py tests/test_workflow.py \
    tests/test_mandatory_worker_ci.py
  ```

- PASS — `kgmaker semantic update --base HEAD`, `kgmaker semantic apply`,
  `kgmaker semantic validate`, `kgmaker memory capture --base HEAD`,
  `kgmaker scan`, `kgmaker status`, `kgmaker check` a `git diff --check`.
- NOT_RUN — úplná projektová sada, nový hostovaný běh PR Review, publikace
  komentáře a nezávislé GitHub review tohoto kandidáta.

## T045-S03 / T045-R01 a T045-AC04 — oprava po nezávislém review

Review prvního kandidáta `b6ff24f2ee23133e65561b8ae602896078e291b3`
našla přímé vkládání hodnot události do shellu, Pythonu a skriptu
komentáře. U dalšího návrhu upozornila na čtení pracovních souborů po
testech a na neúplné reportování coverage.

Checkout používá head SHA události. Fetch načte validované base SHA.
Vložený Python validuje oba identifikátory, porovná konkrétní commity
přes Git argv a přečte obsah přímo z Git objektu headu. Smazané soubory
vyřadí ze seznamu změn. Hodnoty z události, coverage a stav testů se
přenášejí jako hodnoty prostředí. Výstup coverage má jediný číselný řádek,
pokud je dostupné měření. Komentář zobrazuje `Unavailable` při chybějícím
měření a zachovává naměřených `0%`. Souhrn pojmenovává stav testovacího
kroku. Výpis lint kroků je dostupný v jejich logu.

- PASS — `/workspace/kgmaker-tools/pr-review-venv311/bin/python /workspace/kgmaker-evidence/pr-review-ci-retry.py`.
  Harness kompiluje přesný Python a provádí syntaktickou kontrolu
  JavaScriptu. Spouští pouze vyňaté čisté formátování a shell kroky v
  dočasném lokálním repozitáři. Po změně HEAD, změně pracovního souboru a
  odstranění dalšího souboru se analyzuje obsah z head commitu. Smazaný
  soubor z PR se přeskočí. Neplatný a nedostupný SHA vede k chybě.
  Výstup rozlišuje úspěšný, selhaný i přeskočený testovací krok,
  skutečných `0%` a nedostupné coverage. Testy používají i cesty s mezerami.
  SHA-256 harnessu `b658ef1c4d627d8b79bac1565896f98d8e53732348cc12881a5e542c163150ad`,
  logu `0f2ef53650048f2d7b1583b4cb62cef2b586dfe4e3fc4d835f8a15cf4170c556`.
- PASS — 64 cílených testů a 0 SKIP s CPythonem 3.11.18, pytest 9.2.0
  a pytest-cov 7.1.0. SHA-256 JUnit `43489f50e071fdf7c656616f6e975e653ebb9349f40b8925805826509d693fa7`.

  ```bash
  export COVERAGE_FILE=/workspace/kgmaker-evidence/pr-review-ci-frozen.coverage
  PYTHONPATH=src /workspace/kgmaker-tools/pr-review-venv311/bin/python -m pytest -p no:cacheprovider -q \
    --cov=src --cov-report=xml:/workspace/kgmaker-evidence/pr-review-ci-frozen-coverage.xml \
    --cov-report=term --basetemp /workspace/kgmaker-evidence/pr-review-ci-frozen-pytest \
    --junitxml=/workspace/kgmaker-evidence/pr-review-ci-frozen.xml \
    tests/test_completion.py tests/test_completion_handoff.py tests/test_workflow.py \
    tests/test_mandatory_worker_ci.py
  ```

- PASS — `kgmaker semantic update --base HEAD`, `semantic apply`,
  `semantic validate`, `memory capture --base HEAD`, `scan`, `status`,
  `check`, `git diff --check HEAD` a `git diff --cached --check`.
- NOT_RUN — skutečný běh workflow na GitHubu, publikace komentáře,
  úplná projektová sada a schválení konečné revize.
