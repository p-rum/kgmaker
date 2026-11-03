# T003-S04-W05 — ručně anotovaný JVM acceptance corpus

Revision1, T003-S04-W05-AC01–04 / T002-CG-01–05 / T003-AC04.

## Explicitní prerequisite stack

Feature base je lokální `fe36c554f88b8509457cd9eb8ea439325cd03dc3`, větev
`stack/t003-s04-w05-prerequisites`. Obsahuje pouze schválené upstream implementace:
PR35 `89e50cf4cf8edbebc4f9d08879656698c75ebd50` (W04) a PR37
`c8867f3367e2ada0348d5cd44584162ec4558530` (W03), obě nad main `33dc239`.
Nejde o tvrzení, že jsou již v main. Při merge se zachovaly oba dispatch guard a
async marker bloky; přegenerovaly se source anchors a graf, žádná skrytá nová
worker implementace. Vlastní corpus větev proti tomuto base nemění production
worker/Python runtime. Publikaci base a Draft feature po lokálním review řídí parent.

## Změna a meze

`tests/fixtures/jvm-golden/expected.json` ručně anotuje přesné source call-site
počty a identity pro 5 scénářů × K1/K2. Původní five-call golden a skutečný ordered
JAR fixture producer se znovu používají. Dosavadní Advanced/Work/Helper inline
fixtures jsou sdílené soubory se stejnými bytes; nevzniká paralelní katalog.
Java doplněk rozlišuje stejné názvy/overloads/owners, protilehlé CFG větve,
rekurzi, lambda caller a neexecuting reference a dynamickou reflexi. Kotlin doplněk
ověřuje extension/default/inline/suspend metadata a Java caller.

Expected RESOLVED/UNRESOLVED jsou skutečné existující evidence stavy. Unsupported
model/CFG diagnostiky mají samostatnou přesnou identitu a počty; nepřeznačují se
na vymyšlený call-site status. K2 nemá SOURCE CFG a nepodložený builtin JVM target
zůstává UNRESOLVED. Reflexní API může být resolved, runtime cíl nikoli. Nevytváří
se runtime precision/availability důkaz ani tvrzení dokončení celého S04/T003.

Matcher odmítá extra/chybějící/retargeted i silnější výsledky; explicitní mutation
checks ověřují, že ani stejný počet s chybným owner/descriptor neprojde. Inspection
hlídá source/class/last-valid-store byte snapshot. Reuse flow/callgraph/store modelů,
žádná změna versioned protokolu ani schema; původní v1/v2/v3 loader tests zůstávají.

## Validace

- Prerequisite composition: oba skutečné worker rebuildy PASS; actual mapping,
  coroutine, dispatch, foreign/scope guards + protocol/mandatory CI **38 PASS /75.87 s**.
- Nová inventory acceptance před dodáním corpus: **1 FAIL /0.11 s**, chybějící
  ručně anotovaný inventory; schema po dodání PASS. Nejde o runtime bug tvrzení.
- Actual corpus focus, původní shared fixture regresní testy a celý pytest mají
  výsledky zaznamenané níže. Missing required toolchain je FAIL/BLOCKED, ne PASS.
- Finální semantic update/capture/scan/check/diff jsou zaznamenány níže.
- Vzdálené Actions gates zůstávají billing BLOCKED; lokální testy nenahrazují
  sedm mandatory CI gates ani skutečný Windows gate. Bez self-review/merge.

## Opravy anotací během actual ověření

První actual corpus měl **13 PASS, 8 FAIL /44.87 s**: inventory záměrně
nepřijala chybějící známé unsupported boundary anotace ani nesprávně zvolený
owner pro K1 inline extension. Po ověření ve zdroji se explicitně doplnily
SHA-bound multi-release stdlib diagnostiky a collapsed Java expression-order /
K1 default-argument CFG boundaries. Nešlo o změny worker runtime.

K1 `substring` source binding nese compiler facade identitu a `inline=true`;
externí callee source path je null. Je to source-level inline deklarace, nikoli
tvrzení veřejného fyzického JVM memberu či runtime invocation. K2 zachovává
UNRESOLVED. Obě podpory jsou výslovně odlišeny v JSON a matici.

Další corpus: **20 PASS, 1 FAIL /55.66 s**; jediná zbývající chyba byla ruční
CFG anotace prázdného implicitního Worker constructoru. Zdroj workeru emituje
constructor CFG pouze s initializer statements, proto má mixed K1 tři Kotlin
CFG, ne čtyři. Opravený mixed corpus + původní shared Advanced/K2 regrese:
**4 PASS /51.68 s**. Matcher pořád vyžaduje přesné identities/counts; nejsou
vymazány negativní případy ani vymyšlen source CFG/line.

Před celou sadou prošel read-only session prerequisite preflight pro vlastní
worktree; vlastní source i worker production bytes jsou shodné s fe36c554.
Celý current pytest používá společný heavy-test lock; finální výsledky jsou níže.

## Finální ověření stejného source

Celý pytest proběhl: **640 PASS, 10 SKIP, 6 setup ERROR /789.28 s**. Všech
21 corpus checks včetně všech actual K1/K2 scénářů a mutation checks prošlo.
Šest chyb bylo výhradně společné InstalledWorkerTests setup: setuptools sdist
selhal na `[Errno 28] No space left on device` v 4.9GB `/tmp` mountu. Nešlo o
source/test failure; původní full log se zachovává jako `/tmp/golden-full.log`.

Bez změny production či test bytes byl přesunut pouze validační temporary root
na volný `/workspace` volume a znovu proběhl celý installed-worker modul:
**9 PASS /30.94 s**. Tím jsou provedeny i původní šestice zablokovaných tests.
Není vydáván vymyšlený jeden green full běh ani sčítány duplicitní testy.
Deset SKIP jsou 9 volitelných Maven/Gradle/exporter konfigurací a skutečný
non-admin Windows remote-only gate; required K1/K2/Spring/corpus cases běžely.

Příkazy používaly explicitní vlastní workers a připravené vstupy:
```bash
flock /workspace/kgmaker-heavy-tests.lock env \
  PATH=/workspace/tools/jdk-21.0.6+7/bin:/workspace/tools/kotlinc/bin:$PATH \
  JAVA_HOME=/workspace/tools/jdk-21.0.6+7 PYTHONPATH=src \
  KGMAKER_WORKERS_HOME=/workspace/jvm-golden/workers \
  KGMAKER_TEST_MAVEN_REPOSITORY=/workspace/tools/m2 \
  KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 KGMAKER_REQUIRE_SPRING_IMPORTS=1 \
  /workspace/kgmaker-venv/bin/python -m pytest -q
# Stejné env/lock; pouze temporary location pro opravený installed setup:
TMPDIR=/workspace/jvm-golden-validation-tmp python -m pytest -q \
  tests/test_worker_install.py \
  --basetemp=/workspace/jvm-golden-validation-tmp/pytest-installed
```

Scoped semantic artifact přidává jeden doložený corpus koncept a tři vztahy;
všech 7 konceptů/20 vztahů prerequisite stacku zůstává přesně zachováno.
110 upstream epizod tvoří immutable prefix; finální capture/scan/check/diff jsou
součástí lokálního review kandidáta. Žádná samostatná produkční implementace
upstream balíků se zde neduplikuje a remote billing/egress gates zůstávají BLOCKED.


## Nový sjednocený připravený full run (2026-10-27)

Na nezměněném production/test source HEAD `ed5ed7ce114886ce448e810665cd3e486be6e04e`
proběhl samostatný strict full: **646 PASS, 10 SKIP /991.96 s**, bez failures
a setup errors. JUnit potvrzuje všech656 cases včetně21 corpus checks. Předchozí
640/10/6 environment setup errors a následný9 PASS repair zůstávají historické
výsledky výše; nový výsledek je jediný skutečně sjednocený green run.

Read-only prerequisite preflight ověřil vlastní K1/K2/TS workers, skutečný Maven
fixture, React a SHA-bound Spring API. Příkaz používá stejné explicitní JDK21,
Kotlin, vlastní workers a required Workers/K2/Spring env výše; navíc
`TMPDIR=/workspace/golden-final-tmp`,
`--basetemp=/workspace/golden-final-tmp/pytest` a
`--junitxml=/workspace/golden-final-full.xml`, stále pod shared heavy lockem.
Log `/workspace/golden-final-full.log` a XML jsou zachovány. Deset optional/
platform SKIP není mandatory compiler PASS. Žádný CI retry ani merge neproběhl.

Nepublikovaný change note57 byl přejmenován na62 kvůli nově zjištěné kolizi
s publikovaným T046; historické immutable memory episodes se nepřepisují.

## Obnovení explicitního prerequisite stacku 2026-11-03

Nový stack parent je přesný provisional Draft PR37 HEAD
`5d582025ff90a855fa1cd04143e4d98b8fa19c24`, větev
`feat/t003-s04-03-coroutine-source-mapping`. Obsahuje current mainc76 s JPA,
HTTP a factory pravidly a samostatně ověřovaný coroutine/member-extension fix.
PR52 zůstává explicitně závislé na merge PR37. Původní fe36/c886 stack a646/10
full jsou historický audit, nikoli nová validace této parent kombinace.

Všech deset vlastních corpus souborů (ručně anotované expected, osm fixture/doc
souborů a test module) je byte-identických7bdb5cbc. Veškerý Python runtime a
JVM source/build/lock soubory přesně odpovídají novému PR37 parentu; nevzniká
nová implementace workeru. Společné acceptance/CI seznamy se zachovávají unionem.
Generované views vznikají CLI a semantic historie zachovává parent prefix.

Nové actual21 corpus/shared regression testy jsou PENDING. Neproběhl nový build,
copy JAR ani implicitní bootstrap. Případný donor smí být použit až po dokončení
skutečného current-parent vlastního buildu s receipt, source/lock a JAR hash
porovnáním; samotná shoda checkout source nestačí. GH CI je volitelné podle
uživatelské revize T045, ostatní acceptance, závislosti a nezávislé review zůstávají
povinné. Nový full se kvůli této source-identické parent kompozici neplánuje.
