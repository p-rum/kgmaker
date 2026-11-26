# 193 — Čtecí render lokálního technického procesu

Lokální provider T024/T025 uměl doložit spouštěč a vytvořit kanonický `ProcessView`.
Veřejné CLI dříve nabízelo jen legacy CFG report. Dílčí dodávka T034 vychází
z `main` `7e9fa691417706562c875a01a40606350ae058ea` a zachovává kontrakty T019 a T025.

## T034-S01/S02/S03 — lokální render a výběr (AC01, AC04, AC05)

`cli.py` registruje `process render`. `process_cli.py` čte existující explicitní
workspace, originální indexy a volitelný konfigurační soubor pinů stejnou cestou
jako architecture. Lokální T025 řez vezme přesný trigger, jeho vybraný kontext
a původní provenance. Výstup pro `--entry` používá revizi 1 a stejný digest
jako identita triggeru. Výstup `--process` vyžaduje explicitní `--process-view`
se stejným ID a jedním triggerem. Přepočet používá dodané ID, revizi, scope a
aktuální provider. Ověřuje celý kanonický obsah. Chyba při stejném baseline
končí exit 3. Obě cesty vydávají `ProcessView` schema 1 na stdout. Provider
nepublikuje index ani cache. Migrace uložených formátů není potřeba.

## T034-S04 — veřejný kontrakt a zachování vstupů (AC01, AC03–AC05)

`tests/test_t034_add_process_cli.py` využívá dvě skutečná Javac zachycení z
fixture sdílené s T025. Veřejný vstup na baseline po dvou úspěšných zachyceních
skončil exit 2 na chybějícím příkazu `process`. Regrese po implementaci prošla.
Ověřuje přesná původní ID, dvě CFG větve, evidence a omezení na jeden kontext.
Render oběma selektory a se strict vrací shodné bajty. Cizí scope, chybný
selektor, revize, piny, očekávaný otisk a chybějící index vydají přesnou chybu
bez výsledku a změny vstupních bajtů. Historický široký výběr má shodný
baseline, platné schéma a jiný obsah. Zůstává nepoužitelný jako aktuální view.
`flow render --view process` v téže Javac fixture vydává vlastní CFG schema 1.

Cílený Cloud běh s JDK 21.0.6, Javac a připravenými workery K1/K2, `--assert=plain`
a `-p no:cacheprovider`, skončil **237 PASS / 0 SKIP / 0 FAIL** za 83,16 s.
Moduly `tests/test_t019_add_architecture_json_cli.py`,
`tests/test_t023_define_business_process_model.py`,
`tests/test_t024_discover_process_triggers.py`,
`tests/test_t025_build_local_process_path.py`,
`tests/test_t030_prepare_process_label_packet.py` a `tests/test_t034_add_process_cli.py`.

Přímé příkazy `python -m kgmaker process render` nad zachovanou Javac fixture
vrátily exit 0 pro oba selektory se shodnými bajty. Dříve vytvořený aktuální
`process:orders-checkout` prošel i s očekávaným otiskem. Historická širší verze
se shodným baseline skončila `PROCESS_VIEW_STALE`, exit 3 a prázdný stdout.
Devět souborů workspace a tři explicitní pin/view dokumenty zůstaly shodné.

Nezávislá kontrola ve stejné dvouslužbové Javac fixture zkopírovala platné ID
kontextu `orders` do pinu `payments`. Zmrazený kód `b4de6912840204f32c80cc2dae087fa0ee351cc6`
propustil `--entry` s exit 0 a odmítl `--process` jako zastaralý s exit 3.
Nový regresní test na stejném kódu selhal. Oprava ověřuje čtveřici
služba/repozitář/modul/kontext vůči řádkům `CURRENT` z T024 dříve, než T025
zúží projekci. Oba selektory vracejí `INVALID_SELECTOR`, exit 2 a prázdný
stdout. Přímé CLI ověření stejné fixture zachovalo 12 souborů. Správné piny
vrátily původní JSON. Běh T034, T019 a T025 s aktuálním připnutým workerem a
JDK 21.0.6 skončil **80 PASS / 0 SKIP / 0 FAIL** za 48,48 s. Test pokrývá i
výběr bez pinů a legacy flow. Kontrakty T008 a architecture se nemění.

## T034-S05 — dokumentace a zbývající ověření (AC06)

Aktuální příklady a limity uvádějí [README](../../README.md#local-technical-process-paths-t025),
[capability návod](../process-paths.md#read-only-process-render-t034) a
[příklad v T004](../tasks/4_addHighLevelProjectViews.md#4-cílový-kontrakt-cli-specification).
[Revize T034](../tasks/T-034_add-process-cli.md) vymezuje výřez. Přehledy
[acceptance](../acceptance-inventory.md#t034--lokální-technický-json-render) a
[dodání](../production-analysis-progress.md) ponechávají T034 jako PARTIAL.
Instalované instrukce a CLI syntaxe legacy flow se nemění.
Lokální validace sémantické vrstvy, scan, status, check a kontrola odkazů prošly.

```bash
kgmaker process render --entry "$ENTRY_ID" --workspace workspace.json --format json > process.json
kgmaker process render --process "$PROCESS_ID" --process-view process.json --workspace workspace.json
```

Interní dohledání podle ID, `list`, `prepare`, `validate`, `apply`, `review`,
další formáty a distribuovaná kompozice jsou mimo dodaný rozsah. Přesné
nezávislé review, úplná sada a GitHub Actions zůstávají v okamžiku lokálního
předání NOT_RUN.
