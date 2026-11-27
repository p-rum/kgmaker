# Ověření doprovodného volání THREW v S13-W03

[T003-S13-W03](../tasks/T003-S13-03-runtimeValueFlow.md), kroky 4–5 a AC01–AC04.
Výchozí `main` pro první cílené běhy `7ad9fce7526add0986bee29f56ced33aa5da79e3`, strom
`56048188996fe4ca296e12916b0f25c2b27db5b4`. Nový scénář ověřuje již
[dokumentovaný kontrakt v4](../runtime-trace.md#přítomnost-hodnoty-po-přímém-přiřazení-v-javě).
Rozsah celého work package zůstává `IN_PROGRESS / PARTIAL`.

Přenos vychází ze skutečného sloučení [#200](https://github.com/p-rum/kgmaker/pull/200)
`eaf6dce8f0914fb0da8ac4d727c1e67672fe8ac5`, strom
`39430e0aa583b3445b2435512e2e00e075e61b53`. Oba dříve testované
soubory mají stejné Git bloby. Nové ověření obou režimů hooku na
složeném kandidátovi má zatím stav NOT_RUN.

## Krok 4 a AC01–AC03 — skutečná výjimka a hodnotový důkaz

V existující
[Java fixture](../../tests/fixtures/runtime-trace/ValuePresenceApplication.java)
volání `throwingCompanion` skutečně vyhodí výjimku. Obal ji zachytí po
zápisu doprovodného `THREW`. Následuje původní přímočaré přiřazení
statických `String` polí a jeho hook. [Regrese](../../tests/test_runtime_value_presence.py)
ověřuje pořadí `call:THREW → value_presence:PRESENT → call:RETURNED`,
přesné vybrané symboly a export v4 s `PARTIAL / INSTRUMENTED_SCOPE_ONLY`.
Hodnota ani její hash se neobjeví v exportu.

Offline import uloží jeden `runtime_value_presence` doklad a zachová všechny
ostatní grafové hrany. Doprovodná volání zůstávají v exportu. Živý `data-check`
pro přesné čerstvé schválené mapování vrátí `PARTIAL / UNASSESSED` pro jeden
běh. Stav dostupnosti zůstane `UNKNOWN` pro kontrolní obyčejný call, `ABSENT`,
prošlý nebo nesouhlasný doklad. Kontroly neplatných doprovodných faktů
zachovaly poslední validní výstupy a regresní v2 import zachoval své identity.

Zdroj `copy()` je bajtově shodný s výchozí verzí. `javap` porovnal
tutéž metodu v novém zachyceném buildu a přímé Javac fixture z #191.
Po odstranění pouze čísel indexů constant poolu jsou instrukce a symbolické
operandy stejné. SHA-256 srovnávacího dokladu je
`5cf21d468b2c86b8edbc1652576c7fed1a7af75c1eaba08ebb8ea2dd57b61e97`.
Produktový kód, SDK, manifesty a schémata mají původní bajty a kontrakt.
Změna se týká jen fixture a testu. Jejich patch má SHA-256
`3e5ece0f7fbba17c7c215de01c92a3ad9f994950a7758ea4e18bcf8eeef14396`.

## Krok 4 — skutečné kontroly

Temurin Java/Javac 21.0.6+7 a 15 připnutých položek workeru/JDK
odpovídají přímé kontrole #191. Otisk kontrolního seznamu je
`ad54d197e4ebadb93ea6065eee090f4f37d9f3666600fabce0fcf6292268dc6d`.
CPython 3.13.18 spustil dva oddělené běhy. V obou jsou otisky všech
963 verzovaných cest před běhy a po nich shodné. Jejich manifest má SHA-256
`2b25bdccdd1761237fe09f5f2b9287f882dd8bb22887cf682b4ea244e3c35a67`.

| Běh | Skutečný výsledek |
|---|---|
| Nativní `test_actual_java_value_presence_affects_only_matching_live_data_check[same-line]` | 1 PASS, 0 SKIP, raw pytest 0. JUnit SHA-256 `f611d4a39e990a0b27d68d536822862dd04c07ae5ff643f0681c65c58356523f`. |
| Nativní `test_actual_java_value_capture_rejects_invalid_companions` a kompatibilitní `test_runtime_import_retains_same_edge_observations_and_v2_variant_identity` | 2 PASS, 0 SKIP, raw pytest 0. JUnit SHA-256 `4cceaa04bffb15e7247d73ea974828d508b034be6541696710e5a04e4786274f`. |
| Přímé spuštění již přeložené fixture ve scénáři `combined-threw` | Raw exit 0, prázdný stderr a tři sanitizované záznamy v doloženém pořadí. Čtyři kontrolované vstupy mají stejné bajty a časy změn. SHA-256 stdout `fb2b1a6af9a4fac00e6eeb774eb040d3eb6ad7cb858eadfa2806d07bca88170f`. |
| `git diff --check` a zpětná kontrola dvousouborového patche | Raw exit 0. |

První společný pokus přerušila místní disková ochrana při vytváření
dočasných kopií grafu. Pytest měl raw exit 143 a nevydal JUnit verdikt
žádného případu. Doklady úspěchu výše patří až dvěma odděleným,
dokončeným běhům. Jde o nové ověření již podporovaného chování.

Nový scénář `THREW` pro hook na následujícím řádku má v tomto výřezu
stav NOT_RUN. Dřívější ověření následujícího řádku platí pro původní
výřez hodnotového hooku. Instanční pole a vícekrokový hodnotový tok
zůstávají mimo ověřený kontrakt. Úplná sada a formální review finálního
složeného stromu zatím mají stav NOT_RUN.

### Zopakování cílených běhů

Příkazy spusťte z kořene testovaného checkoutu s příslušným
testovacím patchem. `PROOF` označuje existující zapisovatelný adresář
mimo checkout, `S13_PYTHON` Python s pytestem a `JAVA_HOME` a
`KGMAKER_WORKERS_HOME` uvedenou lokální distribuci JDK a workeru.
Běhy používaly samostatnou dočasnou složku, protože publikace grafu
během testu vytváří dočasné kopie.

```bash
export PATH="$JAVA_HOME/bin:$PATH"
export JAVA_HOME KGMAKER_WORKERS_HOME KGMAKER_REQUIRE_WORKERS=1
export JAVA_TOOL_OPTIONS=-XX:-UsePerfData PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
export PYTHONPATH="$PWD/src" PYTHONDONTWRITEBYTECODE=1
mkdir -p "$PROOF/same-line/java" "$PROOF/controls/java"
(
  TMPDIR="$PROOF/same-line/java" env -u _JAVA_OPTIONS -u JDK_JAVA_OPTIONS -u NODE_OPTIONS -u CLASSPATH \
    "$S13_PYTHON" -B -m pytest -q --assert=plain -p no:cacheprovider \
    --basetemp "$PROOF/same-line/pytest" --junitxml "$PROOF/same-line/native.xml" \
    'tests/test_runtime_value_presence.py::test_actual_java_value_presence_affects_only_matching_live_data_check[same-line]'
)
(
  TMPDIR="$PROOF/controls/java" env -u _JAVA_OPTIONS -u JDK_JAVA_OPTIONS -u NODE_OPTIONS -u CLASSPATH \
    "$S13_PYTHON" -B -m pytest -q --assert=plain -p no:cacheprovider \
    --basetemp "$PROOF/controls/pytest" --junitxml "$PROOF/controls/native.xml" \
    tests/test_runtime_value_presence.py::test_actual_java_value_capture_rejects_invalid_companions \
    tests/test_runtime_trace_producer.py::test_runtime_import_retains_same_edge_observations_and_v2_variant_identity
)
```

## Krok 5 a AC04 — sloučený výřez a stav inventáře

[#191](https://github.com/p-rum/kgmaker/pull/191) je od 27. listopadu 2026
součástí `main` jako `3dc249ec66855671f6b78fd6fc86e02603521553`,
tree `20ddb36177a390f0b8e315edaba0e2f66f1e69fb`.
Přímý běh této revize měl 3 PASS, 0 SKIP a raw exit 0. Běžel původní
Javac případ hooku na následujícím řádku, odmítnutí neplatných
doprovodných záznamů a v2 import. JUnit SHA-256
`d5eeef2d6b153e55df5c826e629cab081e8efc0b03581b77e7bc9f7504fa2ef0`.
Doklad původního scénáře `RETURNED` je v
[Change207](207_allowRuntimeValueCallCompanions.md).

[Stavová matice](../production-analysis-progress.md) a
[acceptance](../acceptance-inventory.md#t003-s13-w03--přítomnost-hodnoty-po-přímém-přiřazení)
oddělují tento sloučený doklad od nového ověření `THREW`. W03 i
nadřazená AC13 zachovávají dosavadní stupeň ověření.

Při složení na výchozím stromu po #200 prošlo 13 testů plánovače bez
přeskočení, raw exit 0. Plán zachoval 135 položek, všech 32 pozic
výběru a přísnou závislost S10-W03 na ověřeném S10-W02. U S13-W03
přibyl odkaz na skutečně sloučené #191. Kontroly sémantiky, opakovaného
zachycení a kontroly grafu vrátily raw exit 0. Graf zachoval 522
doslovných epizod a přidal jednu epizodu tohoto kroku. Všech 60
kurátorovaných konceptů a 222 vztahů má původní obsah. Zachovalo se
674 importních vztahů i 3 uzly a 275 vztahů sešitu Rates. Nativní
kontrola přesného kandidáta a úplná sada mají v této fázi stav NOT_RUN.
