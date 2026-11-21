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
