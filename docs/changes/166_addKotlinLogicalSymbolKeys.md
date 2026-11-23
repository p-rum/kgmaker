# 166 — Logické klíče doložených funkcí Kotlinu

[T047](../tasks/47_addReliableIncrementalContext.md), krok T047-S02,
požadavek T047-R02 a acceptance T047-AC02. Výchozí `main`
`b3bbba43304f499f96950ea4ecc2a2467919e616` obsahuje sloučenou fixture S01.
[Sloučený #121](https://github.com/p-rum/kgmaker/pull/121).

Posun deklarace komentářem v reprodukční fixture mění source range i compiler
context. Dosavadní `id` identifikovalo konkrétní výskyt, takže z něj nešel
odvodit stabilní klíč deklarace. Použití samotného JVM deskriptoru by sloučilo
deklarované typy, které mají stejnou JVM erasure.

K1 a K2 u jednoznačných veřejných pojmenovaných funkcí na úrovni souboru předávají
verzovaný doklad o package, jménu a compilerem ověřených kanonických Kotlin
typech. [Mapování](../../src/kgmaker/symbol_identity.py) porovnává tento doklad
s JVM tvarem, modulem, source setem, scope a kontrolním součtem zdrojového
souboru ve vybraném compiler kontextu. Při kolizi deklarací logický klíč
nevzniká. Graph schema v3 přidává volitelný `graph.symbols[].logical_key`.
Čtení ověřuje shodu klíče s výskytem a kontextem; starší grafy v1–v3 fungují
i bez logického klíče. ID výskytu používají call sites a evidence dál ve
stejných compiler kontextech. Workspace přebírá klíče s doloženým repo
selektorem a při jiném přiřazení repo ponechá kvalifikovaný výskyt.
[Návod](../compiler-inspection.md#logické-klíče-deklarací-kotlinu),
[stav](../production-analysis-progress.md), [acceptance](../acceptance-inventory.md).

Verze 1 ověřuje `Int`, `String` a `Boolean` bez nullability ve výslovném
produkčním nebo testovacím source setu. Vyžaduje ručně psaný zdroj, explicitní
návratový typ a lokálně doloženou variantu bez profilů. Typové aliasy a
generika, soukromé, syntetické, členské, lokální a anonymní funkce klíč
nedostávají. Převod starých identit a
packetů, další Kotlin signatury, TypeScript, Windows a inkrementální parita
zůstávají otevřené. Striktní SOURCE_ONLY XFAIL pro stará ID s číslem řádku
eviduje vlastní mezeru. T047-AC02 je PARTIAL.

### Skutečné ověření

- RED — v přesném `b3bbba4` s doplněným testem skutečné K1 i K2 našly
  `(I)I`, ale vracely `None` místo očekávaného logického klíče. 2 FAIL, 0 SKIP.
  JUnit `t047-s02-red.xml`, SHA-256
  `143d56fc5ad1c56eea6068f741017d0d49a43b3e1efa67dbdc673ab54cd15be9`.
- PASS — připnuté offline sestavení `workers/jvm/build.py` pro obě distribuce
  Kotlin 2.1.10 s Temurin/Javac 21.0.6. SHA-256 K1 JAR
  `1652d8fd970834bbf2625378b9dcde3ffa040d6385fa753898664a1fc3b6a1ed`, K2 JAR
  `b2ec81153319c97a1f1fbfd98dda96f400397a1e1881c417145d1cd5ba4e93b9`.
- PASS — závěrečný výběr 7 PASS, 0 SKIP za 85,48 s. Oba workery
  ověřují přesné byty zdroje, oba overloady po posunu řádků a nový klíč po
  náhradě `Int` za `Boolean`. Klíč nevzniká pro nejednoznačné a soukromé
  deklarace, překryv členství modulů a nepodložené repo, scope či profil.
  JUnit `t047-s02-stage-native.xml`, SHA-256
  `fd968fc52136d3a822ccdfdc47b0afab6da6c076a881b4266d84c4b302727499`.
  Shodné manifesty testovaných vstupů a skutečných JARů mají SHA-256
  `9bcbc937a96c860a75d52c50e96ed51509e1a64e94a9ee3882ea619ceb049e21`.
- PASS — 127 integračních a regresních testů pro cache, provider, workspace,
  T052 a T032, 0 SKIP. JUnit `t047-s02-final-fast.xml`, SHA-256
  `41c977701bbcbae4ee96f83d46a18ab8fbe77f2261251c098f34164adb8be680`.
- PASS — S01 cold delty a skutečná stage cache, 13 PASS, 0 SKIP,
  1 očekávaný strict XFAIL a 10 DESELECTED. JUnit
  `t047-s02-final-legacy-and-cache.xml`, SHA-256
  `bfac57e469dfc5ec85adaceebb4307b255b36c804df339ffaeba973d3239ee9e`.
- K2 a JVM golden corpus — 50 PASS a 4 setup ERROR při chybějící mixed Maven
  fixture. JUnit `t047-s02-final-toolchain.xml`, SHA-256
  `c126a05300c3dda57e2bf846272a898cace2145b285e60799bed1258193830fa`.
  Po offline buildu fixture prošly všechny 4 původně neprovedené případy.
  JUnit `t047-s02-final-mixed.xml`, SHA-256
  `4f039899c6a8dc40640bb139355833301658186cf9775c8ac6bfe5e675fcc624`.

```bash
kg_tools=/workspace/kgmaker-tools
export JAVA_HOME="$kg_tools/jdk-21.0.6+7"
export PATH="$JAVA_HOME/bin:$kg_tools/kotlinc/bin:$PATH"
JAVA_TOOL_OPTIONS="-XX:-UsePerfData -XX:ActiveProcessorCount=2" \
  python workers/jvm/build.py --backend k1 --java-home "$JAVA_HOME" \
  --kotlin-home "$kg_tools/kotlinc" --maven-repository "$kg_tools/maven-repository"
JAVA_TOOL_OPTIONS="-XX:-UsePerfData -XX:ActiveProcessorCount=2" \
  python workers/jvm/build.py --backend k2 --java-home "$JAVA_HOME" \
  --kotlin-home "$kg_tools/kotlinc" --maven-repository "$kg_tools/maven-repository" \
  --analysis-api-home "$kg_tools/k2"
export PYTHONPATH=src JAVA_TOOL_OPTIONS=-XX:-UsePerfData
KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 \
  python -m pytest -p no:cacheprovider -q -x --tb=short -ra tests/test_symbol_identity.py
python -m pytest -p no:cacheprovider -q --tb=short tests/test_stage_content_cache.py \
  tests/test_graph_provider.py tests/test_workspace.py tests/test_completion.py \
  tests/test_t032_persist_process_review.py
KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 \
  python -m pytest -p no:cacheprovider -q --tb=short -ra \
  tests/test_incremental_equivalence.py tests/test_stage_content_cache_actual.py \
  -k 'changed_kotlin or deleted_kotlin_target or added_kotlin or comment_does_not_change_logical_identity or stage_content_cache_actual'
KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 \
  python -m pytest -p no:cacheprovider -q --tb=short -ra \
  tests/test_k2_backend.py tests/test_jvm_golden_corpus.py
"$kg_tools/apache-maven-3.9.9/bin/mvn" -o -B \
  -f fixtures/build-inspection/maven/pom.xml \
  -Dmaven.repo.local="$kg_tools/maven-repository" -DskipTests compile
KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 \
  python -m pytest -p no:cacheprovider -q --tb=short -ra tests/test_jvm_golden_corpus.py -k mixed
```

Graf a diff ověřují `kgmaker semantic update --base b3bbba4`, `kgmaker semantic apply`,
`kgmaker semantic validate`, `kgmaker memory capture --base b3bbba4`,
`kgmaker scan`, `kgmaker status`, `kgmaker check` a `git diff --cached --check`.

Úplná projektová sada, GitHub Actions, Windows a nezávislé review NOT_RUN.

## T047-S02 / T047-AC02 — úplný Kotlin výběr a přesné členství

Oprava navazuje na `a48914a4ef88984acced036a69550feadab15e56`. Skutečné K1 a K2
při dvou oddělených inspekcích souborů s kolidující deklarací vydaly stejný
logický klíč pro různé výskyty. Při společné inspekci oba klíče správně
potlačily. Dále získala deklarace z modulu `left` se source setem `right:main`
klíč modulu `left:right` se source setem `main`. Dvojice měly shodné textové
označení `left:right:main`.

`symbol_identity.py` ověří úplnou množinu zachycených Kotlin vstupů výslovně
zvoleného source setu a jeho zachycené generované varianty. Současně použije
stejné pravidlo členství v souboru a kořenu jako `classification.py`, se
samostatnými hodnotami modulu, source setu a scope. Při neúplném výběru
zůstane dostupný výskyt s compiler dokladem. Kolizní kandidáti ze stejné
zachycené množiny se započítají i tehdy, kdy sami klíč získat nemohou.
Stávající ID výskytů, textové označení v existujících výstupech a starší
grafy bez klíčů zůstávají kompatibilní.

Test načítání grafu ověřuje relativní seznam vstupů ve stávajícím workspace
a kvalifikovaný seznam pro serializovanou verzi `selected-source-set-raw-1`.
Případný cizí repo prefix klíč zneplatní. Skutečné vydávání této verze při
spojené inspekci po #145 vyžaduje samostatnou integrační zkoušku.
[Návod](../compiler-inspection.md#logické-klíče-deklarací-kotlinu),
[stav](../production-analysis-progress.md), [acceptance](../acceptance-inventory.md).

- RED — oba případy s původním produktem selhaly se skutečnými K1 a K2.
  4 FAIL, 0 SKIP. JUnit `t047-s02-retry1-red.xml`, SHA-256
  `d9091f8da7124871034480ccd5c54d1297862ce9df4edf5320a0d6e8ddf62fd8`.
- PASS — 138 testů, 0 SKIP za 272,19 s. Výběr zahrnuje 11 testů
  logických klíčů, obě nové regrese na skutečných K1 i K2, kvalifikaci
  workspace, čtení starších grafů, cache, provider, T052 a T032. Testy obou
  oprav ověřují i pozitivní případy úplného výběru a přesného členství.
  Dvě varování Pythonu doprovázela test souběžných procesů.
  JUnit `t047-s02-retry1-green.xml`, SHA-256
  `ea154d8ce08789daf0694bfc8fbc8a7866a47fcc30e307ef9349e652816a2bc9`.
  Shodné manifesty vstupů a JARů před a po běhu mají SHA-256
  `6cbaf7b48f836c58139cc6f76df10ce6ef5ba91e2a658efbad935236c3514930`.
- PASS — S01 cold delty a skutečná stage cache, 13 PASS, 0 SKIP za 224,76 s.
  Původní strict XFAIL pro SOURCE_ONLY ID zůstává. Dalších 10 případů výběr
  nezahrnuje. JUnit `t047-s02-retry1-occurrences-and-cache.xml`, SHA-256
  `95b4cdcd39df1b00327327ec9e69c923ada76b1faa2d59269eb6aefd10e65af5`.

```bash
kg_tools=/workspace/kgmaker-tools
export JAVA_HOME="$kg_tools/jdk-21.0.6+7"
export PATH="$JAVA_HOME/bin:$kg_tools/kotlinc/bin:$PATH"
export PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 JAVA_TOOL_OPTIONS=-XX:-UsePerfData
export KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1
python -m pytest -n 3 -p no:cacheprovider -q --tb=short -ra \
  tests/test_symbol_identity.py tests/test_stage_content_cache.py \
  tests/test_graph_provider.py tests/test_workspace.py tests/test_completion.py \
  tests/test_t032_persist_process_review.py
python -m pytest -n 2 -p no:cacheprovider -q --tb=short -ra \
  tests/test_incremental_equivalence.py tests/test_stage_content_cache_actual.py \
  -k 'changed_kotlin or deleted_kotlin_target or added_kotlin or comment_does_not_change_logical_identity or stage_content_cache_actual'
```

Graf opravy ověřují `kgmaker semantic update --base a48914a`, `kgmaker semantic apply`,
`kgmaker semantic validate`, `kgmaker memory capture --base a48914a`, `kgmaker scan`,
`kgmaker status`, `kgmaker check` a `git diff --cached --check`.
Worker zdroje ani připnuté JARy oprava nemění.
Pro spojený stav po #145 ověřit skutečnou raw inspekci a workspace projekci
na K1/K2, včetně úplného i neúplného výběru a opakovaného načtení po zahřátí cache.
V tomto původním checkpointu měly společný běh s #145, nezávislé review,
úplná projektová sada, GitHub Actions a Windows stav NOT_RUN.
T047-AC02 zůstává PARTIAL.

## T047-S02 / T047-AC02 — fixture workspace vůči kandidátu #145

Výchozí S02 je `1cc422b7473d12f6e8d14d454c8bf8b7859310e6`. Předběžný
izolovaný strom kombinuje jeho soubory s raw kandidátem #145
`ee0c69db36524b31c16f5d6611753dcc6d4816b7`, tree `773300512fe01b120b7e98d9c495110438633032`.
Workspace producer v tomto kandidátu vydává `compiler_inputs` s repo prefixem.
Původní fixture přidala prefix podruhé, takže její vlastní přepsaný graf
odmítl logický klíč i v platném případě.

`tests/test_symbol_identity.py` dál převádí relativní seznam staré inspekce na
tvar raw workspace pro zkoušku čtení. Vstupy, které už zachytil raw producer,
čte v jejich původním tvaru. Zkouška následně záměrně nasadí cizí repo prefix
a ověří jeho odmítnutí. Ověřuje také rozdílné klíče mezi repozitáři a source sety.
Čtení starších grafů v1–v3 dál ověřují dosavadní případy.

- Předběžná kombinace s původní fixture měla 12 PASS a 2 FAIL bez přeskočení.
  Oba případy K1/K2 selhaly při čtení grafu s dvakrát přidaným prefixem.
  JUnit `native.xml`, SHA-256
  `e55a5cd054123d576878ebccd9ebff599ddc796a40e80e04a5e6bce87536a65f`.
- Samostatná předběžná adaptace fixture měla 2 PASS, 0 SKIP. JUnit
  `adapted.xml`, SHA-256
  `d2159c0972ca08694a5608489f33942f3f55dd267b04bea66aa4c06c868acd0b`.
- Skutečný přechod z `selected-source-set-2` na `selected-source-set-raw-1`
  zachoval klíč Kotlin deklarace a vytvořil nová ID výskytu a kontextu.
  K1 i K2 ověřily raw SHA-256 souvisejícího Java vstupu s CRLF, jeho
  normalizovaný hash a odmítnutí cizího repo prefixu. JUnit `transition.xml`
  má 2 PASS, 0 SKIP, SHA-256
  `4ba70dc2018a169c282875eebb7046065a06eff007bd52924eea052603e17982`.
- Opravená fixture se skutečnými K1 i K2 na původním S02 měla 5 PASS, 0 SKIP
  za 165,20 s. JUnit `legacy.xml` má SHA-256
  `cd4409333edad260ac0519923146c11e43079a1859398de2d817e2fd8d1b6d57`.
  Shodné manifesty před a po běhu mají SHA-256
  `21b2e0c86d0807b23cb18abc55c2e87b15d7bebd6c605a5cdd008f5630ee19ab`.
- Opravená fixture v izolované kombinaci s raw kandidátem měla se stejnými
  K1/K2 workery 5 PASS, 0 SKIP za 158,33 s. JUnit `composite.xml` má SHA-256
  `2f34e8dc17da4330ea2f6d2037d5c2f6f4cb7a3a4ed07018c47b7296f2a01f47`.
  Shodné manifesty před a po běhu mají SHA-256
  `67c46a272b2ea2e9b6c0c2de7902715009ab13f6e2a4a8dbad5c741e517aee54`.
  Oba běhy použily shodný soubor testu se SHA-256
  `1e95450e38494bd084796a1a0aaceac7f17c141496341be7365000a40d2ddd51`.

Opravená fixture používá v obou stromech stejný výběr. Běhy mají nastavené
`PYTHONPATH=src`, `KGMAKER_REQUIRE_WORKERS=1`, `KGMAKER_REQUIRE_K2=1`,
`JAVA_TOOL_OPTIONS=-XX:-UsePerfData` a JDK 21.0.6+7.

```bash
python -m pytest -n 2 -p no:cacheprovider -q --tb=short -ra \
  tests/test_symbol_identity.py -k 'isolate_realms_and_unsupported_declarations or legacy_graphs'
```

Před sloučením #145 se čekalo na ověření přesného společného stromu, včetně
průchodu zahřátou cache. Nezávislé review tohoto checkpointu, úplná projektová
sada, GitHub Actions a Windows měly stav NOT_RUN. T047-AC02 zůstalo PARTIAL.

Graf ověřují `kgmaker semantic update --base 1cc422b`, `kgmaker semantic apply`,
`kgmaker semantic validate`, `kgmaker memory capture --base 1cc422b`,
`kgmaker scan`, `kgmaker status`, `kgmaker check` a `git diff --cached --check`.

## T047-S02 / T047-AC02 — přenos po sloučení #145

Prvním rodičem je `0fb789f1eccc9a943a0df149402f4afc3baed42e`, druhým
`1569d5d1f3133360bb0c29d9cedf9b7cd1778ae4` se sloučeným #145. Společný
strom používá raw zdrojové hashe compileru v jejich existujícím schématu.
Identitu Kotlin deklarace určuje původní S02 doklad a úplný zachycený výběr.
Kód a testy odpovídají zdrojovým změnám obou rodičů. Tři sdílené soubory
`inspection.py`, `model.py` a `workspace.py` mají čisté třícestné spojení.
[Kontrakt raw hashů](160_bindJvmSourceBytes.md) · [Stav T047](../production-analysis-progress.md).

Cílený výběr používá připnuté K1 a K2 z převzatých, již přeložených zdrojů S02
a JDK 21.0.6+7. Samostatná fixture nejprve uloží skutečný legacy kontext z
archivu prvního rodiče. Poté změní Java vstup na CRLF, provede raw inspekci a
znovu načte workspace. Opakovaná inspekce stejného raw stavu ověřuje klíč a ID
výskytu i kontextu ze zahřátého uloženého grafu. Běžný mechanismus etap nadále
hlásí `BYPASS`.

Na společných zdrojích prošlo 13 testů za 244,35 s (13 PASS, 0 SKIP).
Sada obsahuje všech 11 případů logické identity a dvě skutečné migrace z
`selected-source-set-2` na `selected-source-set-raw-1`. K1 i K2 zachovaly
logický klíč při změně ID kontextu a výskytu, ověřily raw a normalizovaný hash
CRLF vstupu, zachovaly výsledky po opakovaném načtení a odmítly cizí repo
prefix. Případy pro neúplný výběr, kolizi dvou strukturovaných source setů
a čtení starších grafů zůstaly zelené.

- JUnit `native.xml`, SHA-256
  `2df756813be9da8bdbff0114f1f549b46927f7655f8caf5aa108acd45d3ffec2`.
- Shodné manifesty vstupů před a po běhu, SHA-256
  `c9364a9f55961c04359db66d7e2abee5ef1485baffc4110736eb5f3b23c2a13a`.
- Pomocná fixture `test_real_qualified_transition.py`, SHA-256
  `ba0ffe6a707632b00f0c7906d5c8e32ca170ee1bf2791eff89dbd764dc17f619`.
- Porovnání rodičovských změn `parent-deltas-before.json`, SHA-256
  `b1b2e3b6d8e54288932fd980d0dac4815f1d8de34f85a2e6d5fa43e102eb1c94`.

Běh použil CPython 3.12, hodnoty prostředí z předchozích K1/K2 zkoušek
a `KGMAKER_WORKERS_HOME` nastavené na adresář `workers` společného stromu.
Proměnná `evidence` v příkazu označuje adresář s pomocnou fixture a archivem
`legacy-s02/src` z prvního rodiče.

```bash
python -m pytest -c pyproject.toml -n 2 -p no:cacheprovider -q --tb=short -ra \
  --junitxml "$evidence/native.xml" --basetemp "$evidence/native-pytest" \
  tests/test_symbol_identity.py "$evidence/test_real_qualified_transition.py"
```

Nezávislé review, úplná projektová sada, GitHub Actions a Windows mají pro
tento společný stav zatím status NOT_RUN. T047-AC02 zůstává PARTIAL.
