# Klasifikace cyklických odkazů na ORM XML

[T003-S06-W03](../tasks/T003-S06-03-ormXmlOverrides.md), kroky 1–5 a
nadřazená T003-AC06. Výchozí `main` je
`4011825b15e4b65e1f57576a0986ca05b3cf810e`.

## Krok 1 — rozdíl mezi interpretery, AC01 a AC03

Python 3.13 při `Path.resolve(strict=False)` potlačí chybu smyčky symbolických
odkazů. Capture proto zapsal `missing`, zatímco reader XML rozpoznal neplatný
vstup. Původní regrese selhala v obou bězích Pythonu 3.13 u
[#137](https://github.com/p-rum/kgmaker/pull/137).

## Krok 2 — kompatibilita, AC02

Snapshot používá dosavadní `jpa-xml-input-capture-1` a graph/store zůstává
na v3. Uložený záznam si ponechá rozlišenou cestu chybějícího cíle uvnitř
projektu. Kontext s dříve chybně uloženým stavem se po porovnání označí
jako `STALE` a obnoví explicitní inspekcí.

## Krok 3 — oddělení nepřítomnosti od chyby rozlišení, AC01 a AC03

`src/kgmaker/inspection.py` nejprve rozlišuje descriptor a mapping paths
striktně. Při `FileNotFoundError` použije dosavadní nestriktní rozlišení,
aby uchoval umístění chybějícího nebo dangling cíle. Kontrola, že cíl leží
uvnitř projektu, předchází čtení. Smyčka a další chyby rozlišení se zachytí jako
`invalid`. Přítomný soubor drží dosavadní hashový důkaz. Změna se týká
snapshotu vstupů a jeho porovnání při kontrole čerstvosti.

Příklad `kgmaker inspect code --root ./service --scope production --format json`
uvádí u smyčky `invalid` v `context.jpa_xml_inputs.inputs`.

## Krok 4 — regrese a ověření, AC01–AC03

`tests/test_orm_xml_overrides.py` kontroluje chybějící výchozí soubory,
přesměrování platného odkazu, dangling cíl uvnitř projektu, odkaz mimo root
a smyčku. U smyčky legacy compiler kontext při offline kontrole vyžaduje
obnovení. Stávající skutečné JVM fixture ověřují XML mapping a zachování
poslední platné generace při striktním odmítnutí.

- Baseline, Python 3.13.5 — 1 FAIL / 2 PASS, smyčka hlásila `missing`.
- Baseline, Python 3.12.14 — stejné tři případy PASS.

```bash
python -m pytest -p no:cacheprovider -q --tb=short tests/test_orm_xml_overrides.py \
  -k 'looped_persistence_descriptor or external_persistence_descriptor or xml_input_capture_detects_default'
```

- Opravený zdroj, Python 3.12.14 — **46 PASS / 0 SKIP**, 114,03 s. JUnit SHA-256
  `12eebbee3a4adb4453ce4e075e9e39ae44f171c6111a90cb04ed7f6519aa2e60`.
- Opravený zdroj, Python 3.13.5 — **46 PASS / 0 SKIP**, 114,61 s. JUnit SHA-256
  `4c3669670280edf2ad11c6453ee50c6c1e25769d678001990ca120853998c6bc`.
- Obě sady použily skutečný Javac/JDK 21.0.6 a workery K1/K2, s
  `PYTHONPATH=src`, `KGMAKER_REQUIRE_WORKERS=1`, `KGMAKER_REQUIRE_K2=1`
  a `JAVA_TOOL_OPTIONS=-XX:-UsePerfData`.

```bash
python -m pytest -p no:cacheprovider -q --tb=short -ra \
  tests/test_orm_xml_overrides.py tests/test_graph_provider.py \
  --junitxml=orm-xml-junit.xml
```

Lokální doklady mají názvy `orm-xml-py312.xml` a `orm-xml-py313.xml`.
`git diff --check` a kontrola parametrů z ukázky prošly. Sémantickou vrstvu
a graf ověřují `semantic validate`, `scan`, `status` a `check`.
Úplná sada, nezávislé review a GitHub Actions opraveného kandidáta jsou
při předání `NOT_RUN`.

## Krok 5 — návod a inventář, AC04

[README](../../README.md), [compiler příklad a kontrakt](../compiler-inspection.md#klasifikace-vstupů-orm-xml),
[acceptance](../acceptance-inventory.md#t003-s06-w03--orm-xml-overrides) a
[stavová matice](../production-analysis-progress.md) zaznamenávají shodnou
klasifikaci. Registry zadání a instalované instrukce používají stejné příkazy
a identitu zadání. Celá produkční matice T003-AC06 má další samostatné kroky.
