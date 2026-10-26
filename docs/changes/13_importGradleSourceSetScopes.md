# Explicitní scope vlastních Gradle source sets

## Problém, změny a zadání

T003-S03-W02 / AC01–AC04: exporter odvozoval test scope z podřetězce názvu a
ignoroval vlastní explicitní scope. Exporter `gradle-source-sets-2` nyní čte
`SourceSetContainer`, zachovává project/source-set identitu a přijímá deklaraci
`ext.kgmakerSourceSetScopes`. Pouze přesné main/test/testFixtures mají výchozí scope.
Neznámé i nepodporované deklarace zůstávají unknown s konkrétní diagnostikou.
Volitelné `scope_origin` se validuje a přenáší do existujícího classifier modelu.
Sdílený soubor s více scopes zůstává unknown; generated sources zachovávají
stávající hash/execution binding. Build je nadále výhradně explicitní workflow.

## Kompatibilita a příklad

Staré manifesty bez nového pole zůstávají čitelné. Graph/store v1/v2/v3 a worker
protokol se nemění. Vlastní `integrationTest` dříve dostalo scope podle názvu;
nově potřebuje explicitní `[integrationTest:'test']`, jinak zůstává unknown.
`ext.kgmakerSourceSetScopes = [integration:'test']` umožňuje zvolit scope bez
přejmenování adresářů nebo variant. README a capability dokument obsahují CLI příklad.

## Evidence a kontroly

- Failing acceptance před změnou: skutečný Gradle8.13 export ignoroval integration
  mapping; assertion očekávala test a dostala unknown (1 failed in 4.20 s).
- Pozitivní skutečný Gradle8.13 acceptance po opravě: 1 passed in 4.77 s.
- Offline negativní testy: invalid scope provenance (včetně neřetězcové hodnoty)
  nepublikuje manifest; conflicting memberships zůstávají unknown bez subprocessu.
- Před rebase celý suite s povinnými workers: 201 passed in 47.81 s.
- Rebase na lokální `3155b49` obsahově shodný s remote merge `a39a24d`:
  oba mají tree `11576c09a94522a1bee24a736850c8426ac9417d`.
- Finální full-suite a semantic výsledky jsou doplněny níže.

## Omezení a neprovedené kontroly

Podpora se týká Java Gradle SourceSetContainer, nikoli libovolných Android/KMP
variant API nebo included builds. Export vlastního source setu neznamená, že byl
jeho compile task v dané build fázi spuštěn. Libovolný custom source set bez
explicitní deklarace nedostává production scope. Rebuild worker distribucí nebyl
proveden; skutečné baseline workers/fixture outputs byly zkopírovány z parent
checkoutu a použity při mandatory regresi. T003-S03 jako celek zůstává PARTIAL.

## Závěrečné výsledky

`KGMAKER_REQUIRE_WORKERS=1 KGMAKER_TEST_OTHER_JAVA_HOME=/home/petra/.jdks/openjdk-22.0.1 KGMAKER_TEST_GRADLE=/home/petra/.gradle/wrapper/dists/gradle-8.13-bin/5xuhj0ry160q40clulazy9h7d/gradle-8.13/bin/gradle PYTHONPATH=src python3 -m pytest -q` — **206 passed in 55.56 s**, bez skips. Obsahuje skutečné JVM/TS workers, Maven přes JDK21/22 a oba Gradle8.13 scénáře.

Scoped semantic update/apply/validate, memory capture a scan/status nad `3155b49` a `git diff --check`: PASS. Dotčený koncept a čtyři existující doložené vazby zachovány; žádné nové vztahy nebyly vymyšleny.

## Opravy P1 z code review (2026-10-19)

Baseline oprav: `8e13f82` (původní implementace), parent tasku `3155b49`.
Před opravou nový offline snapshot test a čtyři forged-convention testy selhaly:
**5 failed in 0.07 s**. Sibling source set stejného scope byl součástí celého
compiler snapshotu a původ GRADLE_CONVENTION neověřoval konkrétní dvojici.

Nová policy `selected-source-set-1` ve společném capture/replay helperu omezuje
JVM snapshot na module/source-set membership, jeho generated set a skutečně
sdílené root/module configuration a Gradle config/scripts. Stejný helper je použit
před publikací i v offline provideru. Selected resources a nové/změněné/odstraněné
vstupy se porovnávají obsahově. Sibling Java/resources stejného scope nestalují
vybranou variantu; offline scan/hook/current_graph zachovají compiler symbol bez
subprocessu. Staré contexty bez policy markeru zachovávají svůj konzervativní
scope-wide snapshot až do nové inspection.

Import nyní přijímá GRADLE_CONVENTION pouze pro main→production, test→test a
testFixtures→test_fixture. Custom source set potřebuje EXPLICIT_MAPPING/UNKNOWN.
Legacy manifest bez pole zůstává čitelný; žádné nové provenance se mu nevymýšlí.
Čtyři negativní importy porovnávají všechny existující store soubory byte-for-byte.
Související acceptance T003-S03-W02-AC01–AC04 a T003-AC03.

- Cílený skutečný Gradle + offline provider běh:
  `KGMAKER_REQUIRE_WORKERS=1 KGMAKER_TEST_GRADLE=<Gradle8.13> python3 -m pytest -q tests/test_gradle_variants.py tests/test_graph_provider.py --basetemp=/tmp/kgmaker-variants-cr-focused-final`
  — **25 passed in 8.65 s**.
- Finální full (lokální native services/cache pro Gradle schváleny):
  `KGMAKER_REQUIRE_WORKERS=1 KGMAKER_TEST_GRADLE=/home/petra/.gradle/wrapper/dists/gradle-8.13-bin/5xuhj0ry160q40clulazy9h7d/gradle-8.13/bin/gradle KGMAKER_TEST_OTHER_JAVA_HOME=/home/petra/.jdks/openjdk-22.0.1 python3 -m pytest -q -rs --basetemp=/tmp/kgmaker-variants-cr-full`
  — **215 passed in 62.08 s, bez SKIP**. Skutečné JVM/TS, Maven JDK21/22 a Gradle8.13 fixture testy.
- Dodatečné zpřísnění testu negative importu na skutečně čitelný uložený graf:
  `python3 -m pytest -q tests/test_gradle_variants.py -k 'forged or snapshot_ignores or conventional_pairs' --basetemp=/tmp/kgmaker-variants-cr-negative-final`
  — **9 passed in 0.29 s**; runtime zdroje od full běhu beze změny.
- `semantic update --base 8e13f82`, packet-bound patch zachovávající jeden ověřený
  existující koncept a čtyři vazby k nezměněnému semantic workflow,
  `semantic apply`, `semantic validate`, `memory capture --base 8e13f82 --validation focused25=passed --validation full215=passed --validation negative9=passed`, `scan`, `status` a `git diff --check` — PASS.
- GitHub export a PR nebyly součástí uvedených lokálních testovacích běhů.
  Následný PR do `feat/impl` vyžaduje aktuální CI a review před merge.
