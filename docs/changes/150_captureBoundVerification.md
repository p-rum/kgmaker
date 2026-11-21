# Doklad skutečného testu v lokálním checkoutu

T047-S10 / T047-R10 / T047-AC10 (§5.6). Výchozí `main`
`c2885a6f8daf0281967e3bc5386a69f1647718e0`. T046-S01 z #41 je sloučen
a poskytuje společný journal. Dodání IN_PROGRESS, ověření PARTIAL.

## Zachycení a ověření výsledku

Dosavadní testovací artefakt ukládá deklarovaný výsledek a pozoruje zdroj při
odeslání. Nedokládá, jaké soubory a Git HEAD měl skutečný běh před a po testu.

`src/kgmaker/project_cli.py` přijímá výslovný
`project build-run --plan /tmp/plan.json --record-verification TASK_ID`.
`src/kgmaker/build_runner.py` používá svůj dosavadní runner a jeho kopii
deklarovaných vstupů. Opt-in vyžaduje existující úlohu v kořeni Git
repozitáře a plán pro fázi `test`. `src/kgmaker/verification.py` zachytí
návratový kód a omezené reporty surefire nebo Gradle JUnit z výstupních
adresářů nového běhu. Porovná i úplný deklarovaný inventář kopie. Zmocnění
k explicitnímu buildu se řídí stávající hostitelskou policy.

`src/kgmaker/provenance.py` ukládá typovaný `test_run`, odkazuje na
existující task a při čtení znovu ověří HEAD, úplný inventář a reporty.
Výsledek se nepřepisuje po změně. Textový import zůstává `IMPORTED` a
běžný artefakt role `AGENT_DECLARED`. Evidenční model stále používá
BuildPlan v1, BuildManifest v1, journal v1 a dosavadní workflow. Přidává se
verzovaný payload, výstupní pole v opt-in běhu a nová značka v `trace show`.
Historické artefakty jsou čitelné. Migrace není potřeba.

[Příkaz, pole a omezení](../delivery-workflow.md#dokumentace-skutečného-testovacího-běhu),
[README](../../README.md#doklad-skutečného-testovacího-běhu-t047-s10),
[build dokumentace](../compiler-inspection.md#explicitní-lokální-build),
[stav](../production-analysis-progress.md) a
[acceptance](../acceptance-inventory.md#t047-s10--záznam-ověření-z-jednoho-checkoutu)
popisují stejný rozsah. Identita a závislosti zadání, schema grafu a
instrukce instalované pomocí init nemají dopad.

## Ověření

- RED — Kandidátní `tests/test_verification_records.py` s `src` archivovaným
  z výchozí revize. `python -m pytest -c /dev/null -p no:cacheprovider -q --tb=short tests/test_verification_records.py -k 'existing_cli and suite.py'`
  skončil 1 FAIL, 16 DESELECTED. Původní CLI odmítl nový argument s exitem 2.
- PASS — v Pythonu 3.12.14, pytest 8.3.4, s `KGMAKER_REQUIRE_EXPORTERS=1`,
  Mavenem 3.9.9, JDK 21.0.6 a připraveným lokálním Maven repozitářem:

  ```bash
  PYTHONPATH=src python -m pytest -p no:cacheprovider -q --tb=short -ra \
    tests/test_verification_records.py tests/test_build_runner.py \
    tests/test_provenance.py tests/test_delivery.py tests/test_workflow_profiles.py \
    tests/test_completion_handoff.py
  ```

  123 PASS / 2 SKIP za 23,74 s. Obě přeskočení jsou ze starších
  `tests/test_build_runner.py` scénářů. Jeden očekává exporter pod checkoutem,
  druhý javac v jedné pevné systémové cestě. Nový test
  `test_actual_maven_surefire_pass_and_fail` skutečně spustil Maven/Surefire
  3.5.2 offline. Uložil 1 vykonaný PASS s CURRENT, změna testu při stejném
  HEAD zanechala historický PASS se STALE a opakovaný běh měl 1 skutečný FAIL.
- PASS — cílené scénáře ověřily testovací skript, skrytou konfiguraci, lockfile
  a nový neversionovaný soubor při stejném HEAD, změny v originálním checkoutu
  i v pracovní kopii během procesu, chybějící/upravené XML, symlink, FIFO,
  nesoulad počtů a neměnnost journalu po odmítnutém dokladu.
- NOT_RUN — úplná sada, skutečný Gradle běh pro tento kontrakt, GitHub Actions
  a nezávislé review. Více checkoutů, nezávislé ověření libovolných importovaných
  reportů a brána T047-S11 zůstávají otevřené. Rozsah dokladu je explicitní
  BUILD inventář a reporty. Lokální měření před a po běhu nezjišťuje mezilehlou
  změnu obnovenou do původního stavu.

## T047-S10 / T047-AC10 — druhá iterace po nezávislém review

Výchozí kandidát měl tree `eb62db338eb4edb81255d2816347ccdf199a350f`.
Obě review vrátila nálezy do implementace v T052. Nový source fingerprint
zohledňuje v deklarované množině i POSIX příznaky spustitelnosti. Inventář
kopie se porovnává před i po spuštění. Oprávnění uvnitř těchto tří bitů jsou
součástí dokladu, ostatní informace o filesystemu smlouva nevystavuje.
`verifies` vyžaduje přesný klíč zaznamenané task reference včetně její
revize. `argv[0]` odpovídá executable, jehož hash runner ověřuje.
Příjem XML omezuje důkaz na jednotlivý `testsuite` s úplnými případovými
záznamy a odmítá agregované a vnořené reporty. Neplatný typ položky dokladu
vrátí řízenou chybu bez zápisu. Nové úpravy jsou v
`build_runner.py`, `verification.py`, `provenance.py` a
`tests/test_verification_records.py`.

- RED — `PYTHONPATH=src python -m pytest -p no:cacheprovider -q --tb=short tests/test_verification_records.py -k 'chmod_alone or cannot_attach or malformed_receipt or different_executable or wrapper-report'`
  proti zdrojům prvního kandidátu vykázal 7 FAIL / 17 DESELECTED.
- PASS — stejný soubor s `-k 'not actual_maven'` po opravě vykázal 23 PASS
  a 1 DESELECTED za 10,56 s.
- PASS — stejná rozšířená sada a toolchain jako v prvním kroku vykázala
  130 PASS / 2 SKIP za 35,70 s. Obě přeskočení mají stejnou příčinu jako
  v prvním kroku. Skutečný offline Surefire PASS, STALE a následný FAIL
  prošly znovu nad touto iterací.
- Úplná sada, CI, nezávislé schválení této iterace a zbývající části T047-AC10
  čekají. Nedokončená matice zůstává PARTIAL.

[README](../../README.md#doklad-skutečného-testovacího-běhu-t047-s10),
[příručka](../delivery-workflow.md#dokumentace-skutečného-testovacího-běhu),
[stav](../production-analysis-progress.md) a [acceptance](../acceptance-inventory.md)
zaznamenávají omezení. Build model, nastavení brány, task registry, graph schema
ani instalované instrukce neměníme.

## T047-S10 / T047-AC10 — třetí iterace po nezávislém review

Výchozí kandidát měl tree `a87c28818981e74329c6294214ea3a6d7dcdbbf1`.
Druhé předání review v T052 našlo dva případy, kdy doklad mohl zůstat
CURRENT. POSIX změna režimu `0600` na `0400` při shodných bajtech
ovlivnila test. Změněné počty v jinak konzistentním dokladu se také mohly
rozcházet s přesným uloženým XML.

`src/kgmaker/verification.py` používá všechny režimové bity vrácené
`stat.S_IMODE` pro původní checkout i pracovní kopii. Při čtení dokladu
přepočte výsledek omezeným parserem a porovná přesnou sadu digestů,
pokrytí a souhrnné počty. Lišící se sada reportů znamená STALE.
Neúplné nebo rozporné údaje znamenají UNKNOWN. Dochovaný výsledek se
v historii nepřepisuje. Model dokladu má stejný formát jako v předchozí
místní iteraci. Vlastnictví souboru, ACL, vnější stav a autenticita reportu
zůstávají mimo ověřený rozsah.

- RED — `PYTHONPATH=src python -m pytest -p no:cacheprovider -q --tb=short tests/test_verification_records.py -k 'read_write_mode or coherent_pass_summary'`
  proti zdrojům druhého kandidáta vykázal 2 FAIL / 24 DESELECTED.
- PASS — stejná rozšířená sada a toolchain jako v prvním kroku vykázaly
  132 PASS / 2 SKIP za 25,62 s. Obě přeskočení mají stejnou příčinu jako
  v prvním kroku. Ověření zahrnovalo oba nové scénáře i skutečný offline
  Maven/Surefire s PASS, změnou freshness a následným FAIL.
- Úplná sada, CI a nezávislé schválení této iterace čekají. Nedokončená
  matice T047-AC10 zůstává PARTIAL.

[README](../../README.md#doklad-skutečného-testovacího-běhu-t047-s10),
[příručka](../delivery-workflow.md#dokumentace-skutečného-testovacího-běhu),
[stav](../production-analysis-progress.md) a [acceptance](../acceptance-inventory.md)
uvádějí aktuální rozsah. Build model, task registry, graph schema a
instalované instrukce nemají dopad z této iterace.
