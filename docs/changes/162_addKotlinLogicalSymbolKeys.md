# Logické klíče doložených funkcí Kotlinu

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
