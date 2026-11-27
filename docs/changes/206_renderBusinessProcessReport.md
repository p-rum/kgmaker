# Čtecí Markdown výkaz dodaného procesu

27. listopadu 2026. [T036](../tasks/T-036_render-business-process-report.md)
navazuje na sloučené T033 a T035. Výchozí `main`
`f7015b61473a0700d979157eeba271c480c21cb8` už dodával `ProcessView` a
technický Mermaid diagram. Pro dodaný model chyběl veřejný technický výkaz.

## T036-S01 a T036-AC01/03 — výkaz a diagram z jediného pohledu

`src/kgmaker/process_render.py` přidává `render_process_markdown(view)`. Z jedné
normalizace dodaného `ProcessView` schema 1 sestaví tabulky a stávající
technický diagram T035. Výkaz nese identitu, revizi, fingerprint pohledu a
baseline, scope, vybrané kontexty, triggery, vstupy, výstupy a výsledky. Každý
krok a orientovaný přechod má vlastní řádek. Paralelní přechody mají samostatná
ID a tabulky se řadí podle ID. Původní veřejné Mermaid funkce zachovávají
stávající chování i bajty diagramů.

## T036-S02 a T036-AC05 — technické hranice

Výkaz zachovává technické stavy, coverage, důvod nevyřešené hranice, lokální
truncation, doložená vynechání, diagnostiku a omezení. Nedoložený účel a
dostupnost dat mají `UNKNOWN`. Kontrola aktuálních zdrojů a runtime zůstává
`NOT_CHECKED`. Vložený diagram používá čistou technickou cestu T035. Schválené
business popisky a skutečné konfliktní či zastaralé schválení patří k T036-AC02.

## T036-S03 a T036-AC04/05 — původ a meze čtení

U citovaného důkazu výkaz zobrazuje zachycený druh, polaritu, freshness a kontext.
Zachycený locator vyžaduje výslovnou cestu v repozitáři kvalifikovaného zdroje,
vybraný kontext a hash obsahu. Když záznam nese platný rozsah nebo řádek, zobrazí
ho jako text. Bez této vazby zobrazí `SOURCE_LOCATOR_UNAVAILABLE`.

Vstup, stávající artefakty i zdrojový checkout zůstávají shodné. Python funkce
nevykonává čtení souborů, práci s katalogem, čtení review ani extrakci. Při
chybě vstupu, nebezpečném výstupu nebo překročení rozpočtu vyvolá
`ProcessMarkdownError` a nevydá neúplný výkaz. Rozpočet 4 000 000 bajtů UTF-8
platí pro výkaz včetně diagramu se stávajícími limity Mermaid. Migrace není potřeba.

## T036-S04 a T036-AC01/03/04/05 — cílené ověření

- `test_checkout_report_uses_one_snapshot_and_fixed_mermaid` porovnává parserem
  skutečné hodnoty tabulek, počet normalizací a revizi. Jediný blok Mermaid má
  golden SHA-256 `55881e998d92ad88d42a03e3f28f259256827b9429ed1ce1c8be4f3833de57fa`.
- `test_partial_report_preserves_every_occurrence_and_manual_handoff` ověřuje
  sedm uzlů, devět orientovaných hran, paralelní výskyt, nevyřešený ruční přechod
  bez důkazu, `STALE`, omezený locator, `PARTIAL` a vynechání.
- `test_report_escapes_cells_and_delimits_the_exact_mermaid` ověřuje zachycené
  backticky, rouru, text HTML a podobu odkazu při zachování struktury Markdownu.
- `test_invalid_or_over_budget_report_preserves_last_valid_artifact` ověřuje
  neplatný typ, scope, kontext a reference důkazu, nebezpečný obsah a rozpočet
  Mermaid i celého výkazu, včetně shody vstupu a posledního uloženého artefaktu.

Úspěšné cílené běhy použily z kořene izolované kopie tento výběr pytestu.
Pro commity `27619782` a `bd9bf03` se kopie vytvořila pomocí `git archive`
ze zkoušené revize. U zdrojových stromů `38623fb` a `4808276` se přenesly
`src`, `tests`, `fixtures/process-model`, `workers/jvm/dependencies.lock.json`,
`fixtures/process-triggers/dependencies.lock.json` a
`fixtures/kafka-code-bindings/dependencies.lock.json` z pracovní kopie.
`PYTHON` je cesta k CPythonu 3.13.18 s pytestem a markdown-it-py 3.0.0.
`NODE_BIN`, `RUNTIME_LAUNCHER_BIN`, `NATIVE_LAUNCHER_BIN`, `JAVA_HOME`,
`WORKERS`, `MAVEN_REPO` a `RENDER_NODE_MODULES` jsou místní cesty k dodanému
Node 24.22.3, launcherům, Temurinu 21.0.6+7, workerům a jejich závislostem.
`SCRATCH` a `PROOF` jsou zapisovatelné adresáře mimo kopii. Nativní ověření
použilo Mermaid 11.4.1 a jsdom 26.0.0 z připnutého `package-lock.json`.

```bash
mkdir -p "$SCRATCH/java-tmp" "$PROOF"
ln -s "$WORKERS/jvm/target" workers/jvm/target
ln -s "$RENDER_NODE_MODULES" tests/rendering/node_modules
export JAVA_HOME
export PATH="$NODE_BIN:$RUNTIME_LAUNCHER_BIN:$NATIVE_LAUNCHER_BIN:$JAVA_HOME/bin:$PATH"
export KGMAKER_WORKERS_HOME="$WORKERS" KGMAKER_TEST_MAVEN_REPOSITORY="$MAVEN_REPO"
export KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_MARKDOWN_PARSER=1
export JAVA_TOOL_OPTIONS=-XX:-UsePerfData PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD/src" TMPDIR="$SCRATCH/java-tmp"
printf '%s  %s\n' \
  65dd49c35e012e67c3f425d8f0667039c765a5f1dc1d77979563605d8b47c2f8 tests/rendering/package-lock.json \
  021584a2c6b14626d8af4a6907aed1837dc7c8ee51da1d9ad56c3326b87e0e3b workers/jvm/target/kgmaker-jvm-worker.jar \
  | sha256sum -c
env -u _JAVA_OPTIONS -u JDK_JAVA_OPTIONS -u NODE_OPTIONS -u CLASSPATH \
  "$PYTHON" -m pytest -q --assert=plain -p no:cacheprovider \
  --basetemp "$SCRATCH/pytest" --junitxml="$PROOF/native.xml" \
  tests/test_t020_render_interface_markdown.py \
  tests/test_t032_persist_process_review.py \
  tests/test_t035_render_business_process_mermaid.py \
  tests/test_t036_render_business_process_report.py
```

Podmínkou PASS je raw exit 0, nula SKIP a očekávaný počet případů v JUnit.
Fixture parseru a SVG může bez připnutého runtime Mermaid vrátit SKIP.
U běhů z archivu se porovnal manifest všech verzovaných souborů a obou
odkazů na JVM a Node závislosti před a po běhu, včetně kontrolních součtů
toolchainu.

Na původním zdroji selhalo všech deset nových případů kvůli chybějícímu API.
Raw exit 1, JUnit SHA-256 `2ba509568fddc979da8f1a24cf80a0dfc1bbd4fe74d96c47c3aee25b311f5f70`.
Historický log dokládá deset případů v `tests/test_t036_render_business_process_report.py`.
Přesný původní příkaz včetně přepínačů a prostředí se pro tento RED nedochoval.
První připravený zdrojový strom `38623fb80cd6860d66cc6bd32b7cb876e3372d87`
měl 120 PASS, 0 SKIP, 0 FAIL, raw exit 0. JUnit SHA-256
`3b6e0af06b9136de98d8fe673b0c10408795a33bb0073a3f22b4ad668b620420`.

## T036-S01, T036-S02 a T036-S04 · AC01/05 — přesná ID a lokální truncation

První strom v Markdown tabulce sléval některá rozdílná ID a lokální truncation
zůstával pouze v metadatech diagramu. `test_report_keeps_whitespace_and_literal_escape_occurrence_ids_distinct`
prověřuje řízené páry s ASCII mezerou, řídicími znaky, NBSP, oddělovačem Unicode
a doslovným escapem. ID a jejich reference se zobrazují reverzibilním zápisem
JSON, diagram dál obsahuje původní ID. `test_report_exposes_captured_occurrence_truncation_independently_of_coverage`
prověřuje booleovské `true` u kroku i hrany při celkovém `false`. Chybějící či
neplatná lokální hodnota má `UNKNOWN`.

Oba nové případy na prvním stromu selhaly na příslušných asercích, raw exit 1.
JUnit SHA-256 `ab9f18e350433722ee664def4b6384a45d2e6566581b3f39740672159c5b43d1`.
Historický log dokládá dva výše uvedené případy v
`tests/test_t036_render_business_process_report.py`. Přesný původní příkaz
včetně přepínačů a prostředí se pro tento RED nedochoval.
Opravený zdrojový strom `4808276cf5d936809641cb2c3695a6bd53684d26` nad výchozím
`f7015b6` má v cíleném běhu T020, T032, T035 a T036 **122 PASS, 0 SKIP, 0 FAIL**,
raw exit 0. JUnit SHA-256 `96e76123d3581a485b8a33bd9149172b918492d00c97097d44891fdd8e00a491`.
Běh použil CPython 3.13.18, markdown-it-py 3.0.0, Mermaid 11.4.1, jsdom 26.0.0
a skutečný Javac 21.0.6 ve stávající fixture retry a DLT. Výstup parseru a SVG,
regrese obou Mermaid funkcí i kontrola shody vstupů jsou součástí tohoto běhu.

## T036-S05 a T036-AC06 — rozsah předání

Po sloučení [#189](https://github.com/p-rum/kgmaker/pull/189) je základem tohoto
výřezu commit `c8b77a35c4e4255d2606f6bb8317435d69c6c885` z větve `main`.
Přenesený zdrojový strom `936bab8e441f45d720e3d0a7a30d9924da3073a8` obsahuje
shodný renderer a test. Příklad a meze rozhraní uvádí
[README](../../README.md#local-technical-process-paths-t025) a
[návod k výkazu](../process-paths.md#markdown-report-for-a-supplied-processview-t036).
[Acceptance](../acceptance-inventory.md#t036--markdown-výkaz-dodaného-procesu)
a [stavová matice](../production-analysis-progress.md) zaznamenávají místní
ověření `IN_PROGRESS / PARTIAL`. Příkaz `process render` nadále vydává JSON.

AC02, ověření aktuálního source locatoru a širší CLI mají samostatný rozsah.
Úplná sada, nezávislá recenze integrovaného výřezu a hostované CI měly při
uvedeném přípravném ověření stav `NOT_RUN`.

## Integrace po #165 — T036-S05 a T036-AC06

Po sloučení [#165](https://github.com/p-rum/kgmaker/pull/165) je základem
integrace `0e0c49120281e73ae131777e6f342f39407644e6` z větve `main`.
Větev výkazu navazuje na `27619782d2856d9aa16c9ae3c9379cb73f56edaa` z
[#190](https://github.com/p-rum/kgmaker/pull/190). Lokální sloučení zachovalo
úpravy obou větví v README, inventáři akceptace a stavové matici. Zdroj
rendereru a jeho test mají shodný obsah jako v předchozím commitu #190.

Na přesném commitu `0e0c491` skončil příkaz `kgmaker semantic validate`
s raw exit 2. Pět řádků přidaných do README posunulo důkaz existujícího
konceptu volitelné sémantické vrstvy a jedné vazby z řádku 232 na 237.
Důkaz druhé vazby se posunul z řádku 234 na 239. Omezená aktualizace
obnovila tyto tři kotvy při zachování obsahu konceptu a vztahů. Srovnávací
graf vychází z izolovaného stromu `0e0c491` a zachovává 511 přijatých epizod.
Zápis nové epizody pokrývá pouze sedm souborů T036.

### Plánovač, sémantika a graf pro T036-S05 a T036-AC06

`PYTHON` a `KGMAKER` jsou binárky stejného místního prostředí. `PREVIOUS_BASE`
je `c8b77a35c4e4255d2606f6bb8317435d69c6c885` a `BASE` je
`0e0c49120281e73ae131777e6f342f39407644e6`. Plán se spustil v samostatném
checkoutu `BASE` a v připravené větvi. Na větvi následovaly testy a kontrola
změn v indexu Git. Obě spuštění plánu, testy i kontrola indexu měly raw exit 0.

```bash
export PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1
"$KGMAKER" completion plan --jobs 32 --root "$PWD" > "$PROOF/plan.json"
"$PYTHON" -m pytest -q tests/test_completion.py \
  --junitxml="$PROOF/planner.xml" --basetemp="$PROOF/planner-tmp"
git diff --cached --check "$BASE"
```

Plánovač měl 13 PASS, 0 SKIP a JUnit SHA-256
`b49ab94a499b823c8c2dd78b59f77c169da657986c945cbef1acef4ca356bc4c`.
Porovnání obou plánů změnilo T036 a odvozené blokující podmínky T038, T040
a T042. Podmínka `VERIFIED_IN_SCOPE` pro W03 zůstala zachována.

V izolovaném checkoutu `BASE` vyšla prvotní `semantic validate --root "$PWD"`
s raw exit 2 kvůli README. Pro srovnání se načetl strojový graf
`PREVIOUS_BASE` se SHA-256 `e85945cee6c2feb0f5933f6c8cd5e818475264279cc7a3cc059d041fd7a1fd5e`.
Omezenou aktualizaci připravil příkaz
`"$KGMAKER" semantic update --base "$PREVIOUS_BASE" --root "$PWD"`.
Omezená záplata pro tento packet posunula uvedené tři kotvy. Následné příkazy
`semantic apply`, `semantic validate`, `scan`, `status` a `check` s
`--root "$PWD"` měly raw exit 0. Strojový graf základu měl SHA-256
`de8edef2bc2a702dfa1925be582705ce54e5e1f07ab20d2fcba8dd68a706ab3e`.

Připravená větev použila tento strojový graf jako vstup
`.kgmaker/graph.json`. Po `semantic update` se pro jeho `update_id` vytvořila
`.kgmaker/semantic-patch.json` ze stávajících 9 dotčených konceptů a 23
vztahů. Posunuté kotvy se mapovaly na shodné řádky zdroje a na rozšířený
import z `architecture_render` v `src/kgmaker/process_render.py`.
V původní integraci `bd9bf03` proběhly tyto příkazy s raw exit 0.

```bash
"$KGMAKER" semantic update --base "$BASE" --root "$PWD"
# Připravit omezenou záplatu pro právě vytvořený packet.
"$KGMAKER" semantic apply --root "$PWD"
"$KGMAKER" semantic validate --root "$PWD"
capture=(memory capture --base "$BASE" --validation exact-head-native=unknown
  --validation standard=unknown --validation planner=passed
  --validation source-diff=passed --validation semantic-before-capture=passed)
"$KGMAKER" "${capture[@]}" --root "$PWD"
"$KGMAKER" "${capture[@]}" --root "$PWD"
"$KGMAKER" semantic validate --root "$PWD"
"$KGMAKER" scan --root "$PWD"
"$KGMAKER" status --root "$PWD"
"$KGMAKER" check --root "$PWD"
git diff --cached --check "$BASE"
```

Druhý `memory capture` nalezl stejnou epizodu a zachoval bajty obou vstupů.
Výsledný strojový graf měl SHA-256
`2e46c059ae90fb3b4239a01633067ac821bc7933587e7ee360de86882eaeff13`.
Hodnota `unknown` zachycuje tehdejší stav nativní a úplné sady před jejich
spuštěním na commitu `bd9bf03`.

### Úplná standardní sada a výsledky pro T036-S04 a T036-AC06

Pro každý běh se použil nový archiv zkoušeného commitu `REV`. `PROOF` je
nový zapisovatelný adresář s absolutní cestou. Výstupy testů se ukládaly
mimo kořen zdrojů. Kromě `PYTHON` a `JAVA_HOME` níže označuje
`RUNTIME_LAUNCHER_BIN` místní launchery, `GRADLE_BIN` Gradle 8.13 a
`GRADLE_USER_HOME` jeho místní cache. Gradle používal lokální loopback.

```bash
mkdir -p "$PROOF/source" "$PROOF/java-tmp"
git archive "$REV" | tar -x -C "$PROOF/source"
git ls-tree -rz --name-only "$REV" > "$PROOF/tracked.z"
cd "$PROOF/source"
xargs -0 sha256sum < "$PROOF/tracked.z" > "$PROOF/before.sha256"
export JAVA_HOME GRADLE_USER_HOME
export PATH="$RUNTIME_LAUNCHER_BIN:$GRADLE_BIN:$JAVA_HOME/bin:$PATH"
export JAVA_TOOL_OPTIONS=-XX:-UsePerfData TMPDIR="$PROOF/java-tmp" PYTHONPATH="$PWD/src"
unset KGMAKER_REQUIRE_WORKERS KGMAKER_REQUIRE_K2 KGMAKER_WORKERS_HOME
raw=0
"$PYTHON" -m pytest -q -p no:cacheprovider -o tmp_path_retention_policy=failed \
  --basetemp "$PROOF/pytest" --junitxml "$PROOF/standard.xml" || raw=$?
printf '%s\n' "$raw" > "$PROOF/standard.exit"
xargs -0 sha256sum < "$PROOF/tracked.z" > "$PROOF/after.sha256"
cmp "$PROOF/before.sha256" "$PROOF/after.sha256"
```

Na předchozí dvojici `27619782` a `c8b77a35` prošel cílený nativní běh
se 122 PASS, 0 SKIP a raw exit 0. JUnit SHA-256
`afb09496a97d500b88cdf54dcecf861bcda6c7c0ebb5efac92356b31eb56094b`.
První pokus o úplnou standardní sadu
měl 2692 PASS, 1414 SKIP, 1 očekávaný XFAIL a 6 chyb při přípravě fixture.
Vnořené `ensurepip` selhalo kvůli `No space left on device` a běh měl raw exit 1.
JUnit SHA-256 `6b4deec3e82a33b5ffab5b2d248fd6d226d06c38da78074a471dda5dbb400fd3`.
Po uvolnění místa opakování na stejné dvojici a se shodným manifestem
vstupů skončilo s 2694 PASS, 1418 SKIP, 1 očekávaným XFAIL a raw exit 0.
JUnit SHA-256 `68b9a670031f02bba9edd785a05b454c01ddea568acb51df5b5ed9c5809fef5a`.

Na dvojici `bd9bf038651f7fd4be7f36229ed263815b1d6502` a `0e0c491`
prošel cílený nativní běh se 122 PASS, 0 SKIP a raw exit 0. JUnit SHA-256
`1896265e9f0ea3530ed12018ffbec27805e17553753866c307bfe816e61052fe`.
Úplná standardní sada měla 2694 PASS, 1418 SKIP, 1 očekávaný XFAIL a raw
exit 0. JUnit SHA-256 `5b04c4c112b1faae0f648a8cb10c8efd54b5bab0c8d87cb1d4a99a5bb110ee7a`.
Manifest souborů před a po běhu se shodoval pro cílený i standardní běh.

Uvedené výsledky dokládají výhradně zapsané revize. Pro revizi s tímto
doplněním návodu mají cílená sada, standardní sada, nezávislá recenze a
hostované CI při přípravě záznamu stav `NOT_RUN`.
