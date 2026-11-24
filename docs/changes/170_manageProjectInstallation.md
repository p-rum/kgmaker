# Upgrade a odstranění projektové instalace

Datum: 2026-11-24. Zadání: [T053](../tasks/53_manageProjectInstallation.md), revize 1.
Výchozí SHA všech kroků: `edb65e57ca4de1743c810689c78e069cd86b2b41`.
Dodání: PR_OPEN; ověření: VERIFIED_IN_SCOPE níže uvedených scénářů.
Číslování ověřeno proti lokálnímu registru, main a souborům otevřených PR
#153, #151, #150, #136, #130, #118 a #4; lokální change169 ponechán cizí práci.

## T053-S01 / T053-AC01 — společný inventář a vlastnictví

Původní init vytvářel soubory bez evidence vlastnictví, takže nebylo možné
odlišit původní instalovaný obsah od lokálních úprav. `cli.bundled_init_files`
a `installation.bundled_files` skládají existující Python templates včetně
artifact defaults. `init` zapisuje schéma 1 instalačního manifestu, otisky,
verzi distribuce, zachované soubory a přesně přidaný ignore blok.
Dotčeno: `src/kgmaker/cli.py`, `installation.py`, `installation_history.py`.
Opakovaný init zachovává obsah/mtime a původní ochranu editable template párů;
rozpoznané legacy soubory může převzít podle otisku. Root musí existovat.
PASS: manifest vlastnictví, idempotence, cizí instrukce a částečný template pár
v `tests/test_installation.py`; původní init/skills/artifact regrese níže.

## T053-S02 / T053-AC02 — upgrade

`kgmaker upgrade [--root PATH] [--dry-run] [--force]` používá instalovaný balíček.
Obnoví nezměněné agenty, hooky, commands, skilly/reference, templates i ignore
pravidla, přidá nové/chybějící a odstraní známé retired soubory. Zachová graf,
historii a uživatelské NOTES. Lokální změna blokuje celý plán; force je explicitní.
Pre-existing soubory označené v manifestu zůstávají cizí i s upgrade force.
Dotčeno: `cli.py`, `installation.py`, `installation_history.py`, nové testy.
PASS: změna obsahu ve všech kategoriích, přidání/vyřazení/cílová chybějící cesta,
legacy otisky, opakování, poznámky a nové ignore pravidlo. Neznámé starší distribuce
bez manifestu potřebují ruční sloučení nebo explicitní force; historie otisků
není úplnou databází všech vydání. T049 hostitelské profily se tím nedodávají.

## T053-S03 / T053-AC03 — uninstall

`kgmaker uninstall` se stejnými volbami odstraní vlastněnou integraci a celý
`.kgmaker/` s konfigurací, poznámkami a historií. Projektové zdroje, cizí
agenty/skilly/instrukce a cizí ignore bajty zachová. Upravené integrační soubory
mimo datový adresář blokují odstranění bez force. Dotčeno: `cli.py`,
`installation.py`, lifecycle testy. PASS: úplný roundtrip, custom soubory,
CRLF/bez koncového newline, předem existující ignore pravidlo, pozdější uživatelské
pravidlo, idempotence a symlink uvnitř runtime dat bez zásahu do externího cíle.
Exporty mimo datový adresář, globální balíček a neznámé ruční integrace se nemažou.

## T053-S04 / T053-AC04 — validace, rollback a distribuce

Preflight pokrývá celý inventář před zápisem; manifest nepovoluje libovolné
cesty ani mazání cizích ignore pravidel. Zápisy se připraví do dočasného adresáře,
původní soubory se zálohují přejmenováním. Zachytitelná chyba publikace vrací
původní obsah, mtime i mód. Zálohy při chybě obnovy zůstanou s diagnostikou.
Dotčeno: `installation.py`, `tests/test_installation.py`,
`tests/test_installation_distribution.py`. PASS: konflikty a dry-run bez změn,
neplatné/duplicitní JSON, schéma, cesty a otisky, symlinky, injektované chyby
publikace i přejmenování datového adresáře, CLI v jiném cwd, skutečný offline
wheel v novém venv bez zdrojového checkoutu.
Souběžné editace, výpadek procesu/napájení a Windows nejsou garantované.

## Přesné kontroly

- PASS: `python -m pytest -q tests/test_installation.py tests/test_init.py tests/test_skills.py tests/test_artifact_templates.py tests/test_workflow.py tests/test_workflow_profiles.py tests/test_completion.py --junitxml=/tmp/kgmaker-lifecycle-tests.xml` — **134 PASS / 0 SKIP**.
- PASS: `TMPDIR=/home/petra/wrk/tepsivo/kgmaker/.pytest_cache /tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_installation_distribution.py --basetemp=.pytest_cache/lifecycle-wheel --junitxml=.pytest_cache/lifecycle-wheel.xml` — **1 PASS / 0 SKIP**; Python 3.12.0, setuptools 84.2.1, wheel 0.48.0; offline build a instalace.
- PASS na samostatné PR větvi: `TMPDIR=/home/petra/wrk/tepsivo/kgmaker/.pytest_cache /tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_installation.py tests/test_installation_distribution.py tests/test_init.py tests/test_skills.py tests/test_artifact_templates.py tests/test_workflow.py tests/test_workflow_profiles.py --basetemp=/home/petra/wrk/tepsivo/kgmaker/.pytest_cache/lifecycle-branch-tests --junitxml=/home/petra/wrk/tepsivo/kgmaker/.pytest_cache/lifecycle-branch-tests.xml` — **129 PASS / 0 SKIP** včetně wheelu. Starý completion test nad samotným checkoutem se na PR větvi nespouštěl; lokální sada výše používá již oddělenou fixture z rozpracované změny T049-S08.
- PASS: `git diff --check`.
- První širší pokus FAIL kvůli `Disk quota exceeded` v `/tmp` včetně zápisu JUnit;
  po odstranění pouze dočasných fixture tohoto běhu opakován s výše uvedeným PASS.
- První wheel pokus FAIL kvůli chybějícímu setuptools v základním Python prostředí;
  opakován v již připraveném testovacím venv s výše uvedeným PASS.
- NOT_RUN: celá projektová sada, GH CI, skutečné compiler workery (změna je
  nespouští), Windows a živý reload Copilot/Junie/Codex. Žádný self-use runtime.

## Dokumentace, kompatibilita a příklad

README má nové CLI příkazy; `docs/project-installation.md` obsahuje chování,
API, ochranu dat a migraci; `docs/agent-skills.md` odkazuje na nový postup.
Registr T053, stavová matice i acceptance inventář obsahují oddělený stav dodání
od ověření. Capability compiler/framework/API grafu: bez dopadu, nemění se.
Distribuované texty agentů a skillů a jejich spravované kopie: bez obsahové změny;
nový lifecycle používá stejné Python templates a neinstaluje je do checkoutu.
Stávající `update` dál aktualizuje graf; aktualizace integrace je `upgrade`.

```bash
kgmaker upgrade --root /cesta/k/projektu
kgmaker uninstall --root /cesta/k/projektu --dry-run
kgmaker uninstall --root /cesta/k/projektu
```

Zbývá nezávislé review a případný merge. Uživatelské rozpracované odstranění
self-use integrace (change169) není součástí tohoto PR a nebylo přepsáno.
