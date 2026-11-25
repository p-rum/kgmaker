# Ověření Excel skillu bez vlastního grafu repozitáře

Datum 2026-11-25. Výchozí `main` `3a6b97fc9c44941e68bb390772a5eb13906bf1ff`.
[T055-S03 / T055-AC03](../tasks/55_automateExcelMigration.md) · [Instalace skillu](../agent-skills.md) · [Související odstranění vlastní integrace](https://github.com/p-rum/kgmaker/pull/153).

V [Python 3.13 jobu](https://github.com/p-rum/kgmaker/actions/runs/45617722148/job/139217362565) prošel `pytest` s 2 567 PASS, 1 334 SKIP a 1 XFAIL. Následný `kgmaker check` selhal kvůli zastaralé sémantické evidenci README. [Linux Excel job](https://github.com/p-rum/kgmaker/actions/runs/45617722148/job/139217362508) a [Windows Excel job](https://github.com/p-rum/kgmaker/actions/runs/45617722148/job/139217362452) měly po 26 PASS včetně instalace wheelu.

`.github/workflows/test.yml` odstraňuje krok `kgmaker check` nad checkoutem KGMakeru. Všechny příkazy pro testy a build v CI zůstávají. `tests/test_skills.py` ověřuje instalaci, upgrade a shodu výstupu s distribuovanou šablonou v dočasných projektech. Excel skill dodává `src/kgmaker/skills.py`; vývojová kopie skillu se odstraňuje. Dosavadní `kgmaker init` pro nový cílový projekt a `kgmaker upgrade` pro existující instalaci v něm doručí stejný skill.

`python workers/excel/verify_distribution.py` ověřil worker a 16 runtime závislostí. Cílený `pytest` nad `test_excel_migration.py`, `test_skills.py`, `test_installation.py`, `test_workbooks.py`, `test_xlsx_references.py`, `test_binary_xls.py` a `test_workflow.py` s Java 17, `KGMAKER_REQUIRE_EXCEL_WORKER=1` a `KGMAKER_REQUIRE_EXCEL_WHEEL=1` má 183 PASS. `KGMAKER_REQUIRE_MARKDOWN_PARSER=1 python -m pytest -q` má 2 579 PASS, 1 323 SKIP a 1 XFAIL. `git diff --check` prošel.

Živá relace Copilotu a import do Jira Cloud zůstávají NOT_RUN.
