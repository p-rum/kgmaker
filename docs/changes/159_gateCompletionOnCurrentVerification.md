# Volitelná brána dokončení s aktuálním dokladem

## T047-S11 / T047-R11 / T047-AC11

Výchozí `main` je `34591e2f45814838dd8b21390cdc43c84530f648`. Dosavadní doklad
v1 rozpoznal zastarání vstupů, ale neobsahoval pozorovanou fázi ani iteraci.
Například editace `.test-config` při stejném Git HEAD změnila aktuálnost
skutečného PASS na `STALE` a dosavadní přechod tasku přesto zapsal `done`.
Při retry se stejným HEAD a stejnými vstupy zůstal historický doklad `CURRENT`.

`verification.py` ukládá do dokladu v2 fázi a iteraci z tasku, který
`build_runner.py` načetl před spuštěním procesu. Existující `verifies` váže
doklad k přesné lokální referenci revize tasku. Brána přijímá pouze `PASS` a
`CURRENT` nejpozději zahájeného v2 dokladu fáze `test` nebo `review` v aktuální
iteraci. Posuzuje skutečný výsledek runneru, aktuální Git HEAD, digest úplného
inventáře a XML doklady. Novější FAIL či neověřitelný běh má přednost před
starším PASS. Shodný začátek různých dokladů vyžaduje nový jednoznačný běh.

`workflow.py` používá stejný journal a zámek pro kanonický přechod i přímý
`save_task`. Přechod nesmí změnit revizi plánu. Souhrn kontroluje i soulad
uložené revize s počtem neměnných architektonických artefaktů plánu.
`provenance.py` zobrazuje v registrované lineage status a odvozené ověření
odděleně. `context.py` přidává stejný souhrn při zapnutém pravidle.
`delivery_cli.py` přidává volbu `--verification-before-done on|off` ke
stávajícímu `trace policy` a vyžaduje přesnou revizi journalu.

## Kompatibilita a příklad

Chybějící policy v existujícím journalu znamená vypnuto. Nový reader čte
v1 doklady bez přepisu a bez oprávnění rozhodnout o `done`. Agentní deklarace
a import zůstávají samostatné druhy evidence. Již dokončený task si ponechá
`done`, i když projekt po další editaci zobrazí `STALE`. T046 schválení a
kontroly workflow v3 se vyhodnocují samostatně.

```bash
kgmaker trace show --format json
kgmaker trace policy --verification-before-done on --expected-revision REVISION
kgmaker project build-run --plan /tmp/plan.json --record-verification TASK_ID
kgmaker trace show TASK_ID --format json
```

`REVISION` je aktuální číslo z prvního příkazu. U již spuštěného plánu vytvořte
nový testovací plán pro opakování.
[Příručka](../delivery-workflow.md#aktuální-ověření-před-dokončením-t047-s11) · [Acceptance](../acceptance-inventory.md#t047-s11--aktuální-lokální-ověření-před-dokončením)

## Provedené kontroly

Python 3.12.14, Temurin JDK 21.0.6+7, Maven 3.9.9, lokální Maven repository a
skutečný Surefire 3.5.2. `KGMAKER_REQUIRE_EXPORTERS=1` vyžadoval dostupné
exportery. Výběr dopadl 174 PASS, 0 SKIP, 0 FAIL a 0 ERROR.

```bash
PYTHONPATH=src python -m pytest -p no:cacheprovider -q --tb=short -ra \
  tests/test_verification_records.py tests/test_workflow.py \
  tests/test_delivery.py tests/test_provenance.py tests/test_workflow_profiles.py \
  tests/test_completion_handoff.py tests/test_context_roles.py tests/test_memory.py
```

Skutečný Maven/Surefire ověřil PASS, editaci při stejném HEAD, odmítnutí
`advance_task` i `save_task` se zachováním souborů, skutečný FAIL, nový PASS,
dokončení přímým uložením a pozdější `STALE` při historickém `done`. Další testy
pokrývají retry, dřívější fázi při současném posunu statusu, podvrženou revizi,
v1, import, deklaraci, novější FAIL či UNKNOWN, shodný čas startu, kompatibilitu
default-off, odvolané review a CAS. SHA-256 JUnit je
`4ddb415ce78f706ec821d3a095372933551c9096d7277cdcef5ffcfda22ce488`. Vstupní i
výstupní manifest změněných zdrojů a testů má SHA-256
`b7382abfc645629d5d21cba6bb7b1bf38796841bd4be94e1329927da80a9d9e4`.
`kgmaker completion plan --jobs 3` eviduje S11 jako `IN_PROGRESS / PARTIAL`.

## Rozsah další práce

T047-AC11 zůstává `PARTIAL`. Tato dílčí implementace pokrývá jeden explicitní
lokální běh v jednom checkoutu. Mapování různých požadovaných testů na jejich
doklady, selektivní dopad, širší produkční matice a samostatná projekce v paměti
zůstávají otevřené. Samostatný e2e Gradle scénář pro novou bránu, úplná sada a
GitHub Actions jsou pro tento dílčí pokus `NOT_RUN`.

## Oprava po nezávislém review kandidáta `29c82fe`

Dva nezávislé posudky předaly do T052 dvě závady. Zdrojová editace během čtení
XML mohla mezi předběžnou kontrolou a zápisem připustit `done` s dokladem,
který byl již zastaralý. Trace mohl pozorovat stejný doklad dvakrát a ukázat
pro něj rozdílnou aktuálnost v řádku a souhrnu. Na výchozím commitu
`29c82feead52435dd62cd5af9c7660ae56505aa8` byly tři regrese RED. Obě vstupní
cesty přijaly přechod a `trace` pro doklad provedl dvě pozorování.

`verification.py` po validaci XML, hashů a počtů znovu přečte HEAD a celý
inventář vstupů. Včas zjištěné příčiny `STALE` či `UNKNOWN` si ponechávají
dosavadní pořadí. Společný zámek chrání task a journal. Soubory projektu
se mohou měnit i mimo tento zámek, jde proto o další pozorování těsně před
zápisem. `provenance.py` počítá aktuálnost každého viditelného dokladu jednou
pro daný trace a obě zobrazení ji sdílejí. Brána používá vlastní nové
pozorování. Zkoušky `test_done_rechecks_inputs_after_bound_report_validation`
pro `advance` i `save` a `test_trace_shares_its_single_receipt_observation_with_task_summary`
jsou po opravě GREEN (3 PASS). SHA-256 JUnit výchozího RED je
`c13abe2d3765f7d769597a5c320b290c6d119c30216fbdb5445394613b9a3d7b`.
SHA-256 cíleného GREEN JUnit je
`57bb645dd90c45ea3a67cae5aaf0af16da80f56152ead3dda4074b8b3b21fd03`.
Stejný osmisouborový výběr s reálným Maven/Surefire na JDK 21 má po opravě
177 PASS, 0 SKIP, 0 FAIL a 0 ERROR. SHA-256 JUnit je
`63cac57a5f90b9b37db43895a13544d2133a45982734d427035f4b4455faef76`.
Předchozí a následný manifest změněných zdrojů a testů má stejný SHA-256
`50c8eef7243829c317618c7d9cb02d9ab3bf83c239f823f7c0e5417deb6fafff`.

Samostatný doplňkový smoke na stále neměnném `29c82fe` použil skutečný
Gradle 8.13 `--offline`, Temurin JDK 21.0.6+7, JUnit 4.13.2 a existující
instalovaný Gradle exporter. Doklad z XML jednotlivé třídy zaznamenal
PASS, po editaci konfigurace při stejném HEAD brána odmítla dokončení,
skutečný FAIL doprovodilo stejné odmítnutí, po obnovení konfigurace nový
skutečný PASS umožnil `done` a další editace odvodila `STALE`. Všechny
odmítnuté přechody zachovaly bajty tasku a journalu. První pokus se zastavil
na omezení lokálních socketů Gradle. Druhý pokus zpřístupnil sockety a Gradle
zůstal v offline režimu. SHA-256 souhrnu je
`a6428039a87190078883cb367a84a6c9b1edc3a9743117077dcb1b41799b2a2f`.

## Oprava po nezávislém review kandidáta `2b4b558`

Prázdný Git commit během závěrečného výpočtu otisku mohl změnit HEAD při
stejných souborech a stejném Git tree. Předchozí kontrola porovnala HEAD před
výpočtem a přijala dřívější hodnotu. Opakované čtení po úspěšném otisku v
`verification.py` ověřuje, že obě pozorování HEAD souhlasí. Rozdílný HEAD
vrací `STALE`. Chybějící nebo nečitelný HEAD vrací `UNKNOWN`.

Regrese `test_done_rechecks_head_after_final_input_snapshot` provede skutečný
`git commit --allow-empty` během druhého snapshotu. Ověřuje odlišné SHA HEAD,
shodné Git tree, obsah i POSIX režimy úplného inventáře, odmítnutí v
`advance_task` a `save_task` a shodný obsah úlohy i journalu. Na přesném
`2b4b5583a5b37d0493e9151b0bce3fc66f7cfccc` oba vstupy chybně dokončily úlohu.
Zůstávají pokryty také editace při čtení XML a společné pozorování v trace.
Kontrola sleduje Git a soubory projektu při zápisu. Ostatní zapisovače do
checkoutu mohou běžet mimo zámek workflow.

Výběr `tests/test_verification_records.py -k 'rechecks_head_after_final'`
na výchozím commitu zaznamenal dvě očekávaná selhání. SHA-256 jeho JUnit je
`f301f3cb56c8e04cd4c7f540c181e3817cc694edd3c13a8aa8e8d34f94e88dbc`.
Po opravě pět cílených scénářů (`rechecks_head_after_final`,
`rechecks_inputs_after` a `shares_its_single`) prošlo s JUnit SHA-256
`372b65773fff3be72a191aacc1447c695665002890bb5d10478551dc2927da2e`.
Stejný osmisouborový výběr se skutečným Surefire a Maven 3.9.9 na JDK 21 má
179 PASS, 0 SKIP, 0 FAIL a 0 ERROR. SHA-256 JUnit je
`f203861e67b0c308e85c4dee92e6cddb97e065a1ce68ed6bbab22da67c996f6d`.
Vstupní i výstupní manifest změněných zdrojů a testů má shodný SHA-256
`e7a15dfe2b0ecc4b85bbd9650a2d68e05da0b42bb339303d0a22e798a2597689`.
