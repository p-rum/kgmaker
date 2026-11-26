# Doložené zdroje a VBA podmínky ve výpisu Excelu

Datum 2026-11-26. Integrační základ `main` `80db9cb63b07ca653c53801406823eb5fb61e339`.
Původní reprodukce `5ff2c0846056353605ccb9ab271bd86847c6e661`.
[Zadání T056](../tasks/56_extractExcelBehavior.md) · [Stav](../production-analysis-progress.md#t056--funkce-a-toky-dat-v-excelu-2026-11-25) · [Akceptace](../acceptance-inventory.md#t056--funkce-a-toky-dat-v-excelu-2026-11-25)

## T056-S01 a T056-S02 / T056-AC01 a T056-AC02

Pouhá existence definovaného jména skrývala platný výstup. `behavior.py` nyní
započítává odkaz přes jméno mezi použití buňky, když na jméno skutečně odkazuje
vzorec nebo jiné pravidlo. Průchod pokrývá řetězce aliasů a ukončí se i u cyklu.

Výpis listu vynechával podmínku řídící doložený VBA zápis. `extraction.py` zapisuje
vazbu `guarded-by` k řídicímu příkazu bloku a výpis zachová jeho citaci i případné
lokální definice. Například u `If permitted Then` a následného zápisu do `C1`
výpis uvádí identifikátor a řádek podmínky. Citace dokládá statický kontext
zápisu. Zvolená větev a výsledná hodnota vyžadují nezávislé ověření.

## T056-S03 / T056-AC03

Výpis se selektorem dříve zobrazoval deklarace z nesouvisejících sešitů.
`behavior.py` používá zvolený rozsah, vazbu připojení na query tabulku
a doložené cesty k upstream zdrojům. Příklad pro list Výsledky

```sh
kgmaker excel behavior --inventory migrace/inventory.json --book main --sheet Výsledky
```

`--include-source` přidá přesné formulace a identity pouze v doloženém rozsahu.
`tests/test_excel_migration.py` ověřuje samostatné i kombinované selektory,
připojení query tabulek, skutečnou vazbu přes jiný sešit a obě úrovně zobrazení
zdrojového obsahu.

`schema_version=1`, argumenty CLI i formát exportů zůstávají kompatibilní.
Dřívější inventář lze přímo použít. Vazby k podmínkám vzniknou po nové
statické extrakci původních sešitů. [README](../../README.md#excel-migration) ·
[Návod a CLI příklad](../excel-migration.md#funkce-a-tok-dat-v-sešitu)

## Kontroly a omezení

První běhy v Cloud Environment použily Python z `/workspace/kgmaker-venv`.
Kontroly první opravy jsou vázané na strom `9a3f0776c60cc8c8b82380de25e0b3b7720cacfa`.
Identifikátory JUnit XML jsou SHA-256.

- **FAIL na základu a PASS po opravě** — `python -m pytest -q -p no:cacheprovider tests/test_excel_migration.py -k 'behavior_distinguishes_unused_aliases or behavior_sheet_scope_includes_the_guard or behavior_only_declares_selected'`.
  Všechny tři testy nejprve selhaly proti archivovanému `5ff2c08` a všechny
  prošly v obou následujících sadách. JUnit základu
  `1c88508abb6adbd849594393fb222d897b6c0c6825f458644bb4e38c58286885`.
- **84 PASS a 16 SKIP** — `python -m pytest -q -p no:cacheprovider tests/test_excel_migration.py tests/test_workbooks.py tests/test_xlsx_references.py tests/test_binary_xls.py`.
  V této sadě se přeskočilo 15 testů vyžadujících worker a jeden smoke
  test instalovaného wheelu. JUnit
  `bd2ae78c8110856132146425af0ed704bee059d90f1b2a6cb71f8f9103ee545f`.
- **10 PASS a 0 SKIP** — se skutečným workerem a `KGMAKER_REQUIRE_EXCEL_WORKER=1`
  proběhly tři nové regrese a sedm existujících případů vybraných
  `-k 'xlsm_vml_control_line_breaks or currency_behavior or vba_behavior_tracks_http_response or query_destination or vba_function_lineage or vba_non_mutating_intrinsic or behavior_distinguishes_unused_aliases or behavior_sheet_scope_includes_the_guard or behavior_only_declares_selected'`
  v `tests/test_excel_migration.py`. Sestavení použilo Temurin 21.0.6,
  `javac --release 17` a 16 JAR se shodou SHA-256 se zámkem. Zdroj workeru
  `59f57cbbecccd87855306c1b274da0e865263a9b08875703bcd9533bbc6ce4c6`
  a zámek `0c82b22cc0e242bb6ed7d22edb1d515ea263fcd439b5d2d9489907138fd01c06`
  odpovídají výchozímu `main`. JUnit
  `896263e5a0db14d7dd7e78dd07e876b6d8f0bdbac726b40bc6c114abd87748be`.
- **PASS** — `git diff --cached --check` a obnova strojového indexu
  příkazem `kgmaker scan --no-docs`. `kgmaker semantic update --base 5ff2c08`
  našel citace mimo rozsah opravy Excelu. `kgmaker semantic validate` hlásí
  **FAIL** kvůli dříve zastaralé citaci README. Hash README ve výchozím
  `main` se už lišil od hashe uloženého v sémantickém artefaktu.
- **NOT_RUN** — produkční sešit, živý Copilot, instalovaný wheel, Maven,
  běh na Java 17 a hostované CI. Počty výše dokládají pouze uvedené lokální
  běhy. Statický výpis neprovádí přepočty, VBA ani volání deklarovaných služeb.

## T056-S02 / T056-AC02 — opravy po prvním review

`extraction.py` sjednocuje mezery a tabulátory v uzavíracích příkazech jako
`End If` a `End Select`. `Next j, i` uzavře oba odpovídající vnořené bloky.
Pozdější zápis zachovává pouze řídicí kontext stále otevřeného bloku.

`behavior.py` při čtení inventáře ověřuje vazby `guarded-by` a lokální
`depends-on`. Obě operace musejí mít doloženou a jednoznačnou společnou
proceduru, odpovídající lokátory a dřívější řádek či pořadí kroku. Citace
podmínek a přiřazení se používají v průchodu i ve výpisu. Seznam alternativ
používá ověřené vazby.

- **11 očekávaných FAIL** — `python -m pytest -q -p no:cacheprovider tests/test_excel_migration.py -k 'behavior_closes_nested_vba_blocks or behavior_rejects_unbound_vba_context'`
  na původním implementačním stromu `9a3f0776`. JUnit
  `ad1a0ba92dd0c7c31ead9e298fa8819c7e2623c420e6af0300b15b39be5b757c`.
- **95 PASS a 16 SKIP** — po opravě `python -m pytest -q -p no:cacheprovider tests/test_excel_migration.py tests/test_workbooks.py tests/test_xlsx_references.py tests/test_binary_xls.py`.
  Sada zahrnuje všech 11 regresí review. Důvody přeskočení jsou stejné jako v
  prvním čistě pythonovém běhu. JUnit
  `b59995c59618202f122e82f4e00e5ef64f69afeb27abc6855105c5cb2f0a821c`.

## Ověření na integračním základu po #167

Základ tohoto běhu byl `d9379b210d6d4e245c958024484bc864ddb1105a`.
Kanonické řádky zachovávají stav PARTIAL pro T056-S01 až S03 a T056-AC01 až
AC03. Při přenosu se zachovaly původní důkazy, historická reprodukce a rozsah
sloučených změn. [Evidence #167](183_reconcileExcelCompletionInventory.md)

- **95 PASS a 16 SKIP** — `python -m pytest -q -p no:cacheprovider tests/test_excel_migration.py tests/test_workbooks.py tests/test_xlsx_references.py tests/test_binary_xls.py`.
  Stejných 15 worker testů a jeden test instalovaného wheelu bylo v tomto běhu
  přeskočeno. JUnit `e1552197096cdd7fe9470fa0b991312e53a36780f7b0de00a6d43b8d06370701`.
- **22 PASS a 0 SKIP** — cílené případy v `tests/test_excel_migration.py`
  zahrnují čtení obou zápisů VML, 15listou fixture, skutečný vícesešitový
  inventář i nové regrese VBA. Použitý worker byl sestaven stejným
  `javac --release 17` a se stejnými 16 zamčenými JAR jako výše.
  JUnit `940d31d8b3a8b01fde23916b65014a7af7536cb6c7e3b40373ac6d7dd46f1b37`.
- **PASS** — doplňková sonda vytvořila kopii XLSM se syntetickým
  `Worksheet_Change`. Skutečný worker načetl podmínku, přiřazení a ukončení
  bloků s tabulátorem i mezerami. CLI `excel behavior --book invoice --sheet Sheet1`
  zachovalo citace k podmíněnému zápisu, správně ponechalo následující
  zápis bez podmínky a redigovalo text v implicitním režimu. SHA-256
  dočasného XLSM byl stejný před analýzou i po ní. Záznam sondy
  `ce993e758d30f64611be550f43969841b3a413c12e3a887cd733c631dc8e6cff`.
- **NOT_RUN** — produkční sešit, živý Copilot, instalovaný wheel, Maven,
  běh na Java 17, úplná sada a hostovaná CI.

Pro ověření grafu se používají `kgmaker semantic update --base d9379b2`,
`kgmaker semantic apply`, `kgmaker semantic validate`, `kgmaker scan`,
`kgmaker status` a `kgmaker check`. Aktuální odkazy README se vážou na
stávající citace sémantického modelu.

## T056-S03 / T056-AC03 — stejná kontrola vazeb v packetu

Při lokálním ověření stromu `752e27342199407b641f99895a4bf4cfb5bcc2f3`
výpis `excel packet --entity` zahrnul nedoloženou podmínku nebo přiřazení
z nesouvisejícího sešitu přes surovou vazbu inventáře. `relations.py` poskytuje
stejnou kontrolu pro `behavior.py` a `plan.py`. Packet odfiltruje chybné vazby
před výběrem sousedů a zobrazí pouze přijaté místní vazby a alternativy.
Od vybraného zápisu projde řetězec podmínek a jejich doložených definic.
Přímé vazby vzorců do dalšího sešitu zachová. Výchozí výstup rediguje zdrojový
text a `--include-source` ho přidá u zahrnutých důkazů. Formát verze 1 a CLI
jsou kompatibilní.

- **7 očekávaných FAIL a 1 PASS** — na `752e273` spuštění
  `python -m pytest -q -p no:cacheprovider tests/test_excel_migration.py -k 'behavior_rejects_unbound_vba_context or behavior_only_declares_selected'`.
  Chybné vazby se reprodukovaly a přímý odkaz do dalšího sešitu prošel.
  JUnit `9acd101b0df567fe91916969203d60e32ff26cd8ad9edad54e3ed9211dfe5ce3`.
- **95 PASS a 16 SKIP** — opravené CLI, vnořené podmínky a čtyři excelové
  moduly `tests/test_excel_migration.py tests/test_workbooks.py tests/test_xlsx_references.py tests/test_binary_xls.py`
  přes `python -m pytest -q -p no:cacheprovider`. Přeskočily se worker
  případy a jeden test instalovaného wheelu.
  JUnit `011d940e79fe4404d49eaabd74493398f93e59f7536c20efd358a24566a93aa5`.
- **13 PASS a 0 SKIP** — skutečný worker, Temurin 21.0.6, `--release 17`,
  stejných 16 zamčených JAR a cílený výběr v `tests/test_excel_migration.py`
  `-k 'real_multi_workbook or xlsm_vml_control_line_breaks or currency_behavior or behavior_sheet_scope_includes_the_guard or behavior_rejects_unbound_vba_context or behavior_only_declares_selected'`.
  JUnit `166bef036d426ef5c99dc51d0f29bde5936d2163a4b4954ac2df4e8a5ea9d48f`.
  Živý Copilot, produkční sešit, plná sada a hostovaná CI mají stav NOT_RUN.

## Ověření po sloučení #166

Na sloučené revizi `80db9cb63b07ca653c53801406823eb5fb61e339` má stejný
cílený výběr se skutečným workerem **13 PASS a 0 SKIP**. Pokrývá obě
varianty VML, skutečný vícesešitový packet, patnáctilistý výpis, vnořené
podmínky a odmítnutí nedoložených vazeb v reportu i packetu. JUnit
`6dab6cf601c0350315f001d576eb708ec1fed9410f4112f5b998b566fc7b89c4`.

Stav T056-S01 až S03 a T056-AC01 až AC03 zůstává PARTIAL. Úplná sada,
hostovaná CI, živý Copilot a produkční sešit mají stav NOT_RUN.
