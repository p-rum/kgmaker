# T003-S04-W03 — bounded coroutine source boundaries

Revision 1, base `33dc239a6d2eca2f42364a7b314aeb377e4b441a`.

Původní suspend call site zůstává source compiler důkazem s hash/range/context.
K1 descriptor `isSuspend` a K2 `KaNamedFunctionSymbol.isSuspend` poskytují
suspension boundary; konkrétní coroutines `launch`/`async` vyžadují přesnou
compiler callable identitu. Jména uživatelských metod nejsou důkazem scheduleru.
K1 source IR předává boundary existujícímu CFG, včetně resume a failure/cancel
hranic. K2 nadále neposkytuje SOURCE CFG; nevyřešený dependency JVM target
zůstává UNRESOLVED, i když compiler prokáže suspend charakter původního callu.

ContinuationImpl invokeSuspend může mapovat pouze deklaraci: Kotlin Metadata,
DebugMetadata v1, jedinečný outer method + descriptor a skutečný delegate,
přesné repo/module/source_set/scope a existující suspend source deklarace se
shodným souborem a platnými line bounds. DebugMetadata suspension lines nejsou
source call-expression locators ani bytecode offsets. Generated call sites mají
stále BYTECODE_ONLY, path/range null. Suspend lambda state machines bez takového
named declaration důkazu nemají odhadované mapování.

AC01–04: `tests/test_coroutine_mapping.py` používá skutečný Kotlin2.1.10 compiler
s pinned bundled kotlinx-coroutines JAR SHA256
`c24c8bb27bb320c4a93871501a7e5e0c61607638907b197aef675513d4c820be`.
Aplikace, coroutine scheduler ani Spring context se nespouštějí. Fixture obsahuje
suspend/delay dvakrát, launch, async a await. Testy ověřují chybějící zdroj,
neshodné metadata a každý ze čtyř realm fields; source/class/store bytes se při
inspekci nemění.

Graph/store v1/v2/v3 zůstávají čitelné; worker protocol v1 se nemění a nová
pole jsou aditivní. Source CFG producer označuje boundary-aware výstup
`source-cfg-2`; starší uložené CFG zůstávají čitelné.
Worker content identity změní compiler context/cache selector; stará evidence
se nepovyšuje na novou. Neimplementováno: runtime pořadí, globální async schedule,
obecné lambda/coroutine state-machine CFG, odhad source expression z line table.
Plný S04 ani T003 tím není prohlášen za dokončený.

## Kontroly

První skutečná acceptance před opravou: **2 FAIL /15.59 s** (chybějící K1 marker,
K2 odmítnutý suspend declaration ABI). Finální focused matice: **59 PASS /187.54 s**, z toho 50 actual coroutine případů
a 9 control-flow testů. Finální full výsledek je uveden níže;
vzdálené CI dosud NOT_RUN. Chybějící required toolchain je FAIL, nikoli PASS.

První full attempt měl 14 setup ERROR ještě před compiler cases: vlastní
worktree neměl připravené TS node_modules ani Maven fixture target. Po zjištění
neplatného prostředí byl pouze tento běh přerušen (exit130), není to full PASS.
Před opraveným během byly porovnány všechny relevantní zdroje/lockfiles proti
ověřenému default-body worktree a převzaty totožné připravené TS dependencies,
frontend dependencies a skutečný Maven fixture target. Vlastní zmrazené K1/K2
JARy se neměnily. Připravené validační běhy používají shared heavy-test flock.

Commands (explicit own worker home):
```bash
PYTHONPATH=src KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 python -m pytest -q tests/test_coroutine_mapping.py tests/test_control_flow.py
# Full: same flags, pinned JDK21/Kotlin2.1.10 PATH, explicit KGMAKER_WORKERS_HOME,
# KGMAKER_TEST_MAVEN_REPOSITORY and KGMAKER_REQUIRE_SPRING_IMPORTS=1 under flock.
python -m pytest -q
```
GitHub Actions mandatory gates zůstávají externě BLOCKED kvůli billing/spending
limitu; lokální PASS není náhradou vzdálených sedmi gates ani Windows execution.

Vlastní audit doplnil guard proti lokální source funkci se stejným FQ názvem
`kotlinx.coroutines.launch`: API scheduler marker vyžaduje, aby compiler binding
nebyl vybranou checkout source deklarací. Suspend marker vychází nezávisle ze
skutečného compiler isSuspend. Actual negative overload i skutečné knihovní
launch/delay positives: **4 PASS /44.20 s**, K1 i K2. Předchozí prepared full byl
přerušen pouze kvůli této změně před drahou maticí: **42 PASS, 2 SKIP /32.87 s**;
není označen jako dokončený full. Finální worker rebuildy po guardu PASS.

První neplatný setup full zanechal pravdivý částečný výsledek: **117 PASS,
2 SKIP, 14 setup ERROR /254.27 s**, poté KeyboardInterrupt/exit130. Připravený
finální full používá shodné ověřené fixture sources/dependencies a vlastní
zmrazené worker JARy; nedělá fallback na cizí implementaci.

Read-only session prerequisite preflight prošel po přípravě všech vstupů:
`/workspace/kgmaker-test-prerequisites.py /workspace/coroutine-mapping`.
Local docs checker: 0 HTML pages, 0 contradictions (žádné live Confluence proof).
Prázdný vygenerovaný report není součástí změny.

## Finální validace

Zmrazený production source po API-provenance guardu: **584 PASS, 10 SKIP
/804.87 s**. Všech 50 actual coroutine případů a 36 W02 mapping případů běželo;
žádný required K1/K2/Spring případ nebyl přeskočen. SKIP: 9 volitelných
Maven/Gradle/exporter konfigurací a skutečný non-admin Windows remote-only gate.
Po tomto baseline full byly pouze zesíleny existující positive assertions pro
`async` a `await` (žádná production změna ani nový testcase): actual K1/K2
**2 PASS /22.40 s**. Plná sada se kvůli těmto dvěma assertions neopakovala.

Finální rebuild SHA256: K1
`4d0d843153b8a4b87dae1a86159ae635f72fdce54becde6ebcd564131c9de5d4`, K2
`13ef27479bb215af50f6cb578746425837d1a5ce11a9d66c26b8f63d9306e903`.
Testované production bytes se po full nemění. Semantic update zachovává 105
main epizod jako přesný immutable prefix; existující source mapping kotvy jsou
pouze posunuty na skutečné řádky, nový coroutine koncept má pět doložených vazeb.
Remote sedm mandatory CI gates je nadále billing BLOCKED, nikoli PASS.

Přesný finální full příkaz (log `/tmp/coroutine-full-final.log`):
```bash
flock /workspace/kgmaker-heavy-tests.lock env \
  PATH=/workspace/tools/jdk-21.0.6+7/bin:/workspace/tools/kotlinc/bin:$PATH \
  JAVA_HOME=/workspace/tools/jdk-21.0.6+7 PYTHONPATH=src \
  KGMAKER_WORKERS_HOME=/workspace/coroutine-mapping/workers \
  KGMAKER_TEST_MAVEN_REPOSITORY=/workspace/tools/m2 \
  KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 KGMAKER_REQUIRE_SPRING_IMPORTS=1 \
  /workspace/kgmaker-venv/bin/python -m pytest -q
```
Rebuild používal `python workers/jvm/build.py --kotlin-home
/workspace/tools/kotlinc --maven-repository /workspace/tools/m2 --java-home
/workspace/tools/jdk-21.0.6+7`; K2 navíc `--backend k2 --analysis-api-home
/workspace/tools/k2-verified`. Všechny build/test subprocessy byly explicitní
validační akce; offline source/query cesty žádný build ani aplikaci nespustily.


## Kompozice s aktuálním dependency-dispatch parentem

Integrační base je ověřený main
`ec333966e657896382f310ef018835e3d696513e`. Původní frozen feature c8867f3
a její584/10 full jsou historický důkaz, nikoli validace nové kombinované JVM.
Před editací proběhla přímá architektonická rekognoskace task/spec, původních
DebugMetadata/realm/ABI guards a current physical/source hierarchy views; memory
recall je zaznamenán v externím validačním adresáři.

Bytecode.java je převzat přesně z main: physical application mapping view se
nezaměňuje se source hierarchy view pro dispatch. SourceMapping.java a
control_flow.py zůstávají přesněc8867f3; původních50 actual coroutine případů je
zachováno, pozdější P1 doplňuje čtyři regresní varianty níže. SMAP,
DebugMetadata, čtyři realm fields, source hash/range a statické ABI guards se
neodstraňují. K1/K2 call-site bloky zachovávají zvlášť suspend/async markers a
main dispatch metadata. K2 light-declaration výběr používá stejný continuation
a extension-receiver ABI count/filter jako původní coroutine method guard.
Nevzniká nový scheduler, async runtime ani odhad source-expression mapping.

CI zachovává všechny main testy a explicitní API-only bootstrap; coroutine suite
se přidává do mandatory compiler jobu. Main134 immutable episodes tvoří přesný
prefix, všechny unikátní původní captures zůstávají beze změny. Zastaralé
vygenerované views se obnovují CLI.

Nové vlastní clean-classes K1/K2 buildy a actual coroutine/dispatch/default-body
focus jsou queued pod shared heavy lockem. Receipt zaznamenává přesné source
hashes, příkazy, exit codes a nové JAR SHA; původní c886 JARy jsou archivovány
jen jako historical. Žádný stale artifact nebyl použit jako nový proof.
Zdrojové/source review a jeden fresh frozen strict full následují až po green
focus; zatím nejsou PASS. Logy a receipts: `/workspace/coroutine-main-integration/`.
Současné remote CI je externě billing BLOCKED, bez retry/bypass; lokální autorizovaná
integrace pokračuje a implementační agent nepushuje ani neself-schvaluje source.


Nezávislé review před prvním novým buildem našlo P1 v převzatém dispatch bloku:
member-extension `value.ext()` nesmí použít typ dot value jako dispatch receiver.
Skutečný parent K1 donor e44e3dac pro Base.use(Derived) tvrdil jen Derived.ext,
ačkoli compiler dispatch receiver je this:Base. Nově povolený K2 suspend ABI
mohl otevřít tentýž chybný průchod. Původní vlastní build/focus queue byl před
editací zastaven; neměl child a žádný build/test nezačal (status JSON zachován).

K1 nyní pro member-extension bere compiler resolved dispatchReceiver.type; K2
partiallyApplied dispatchReceiver.type, bez dot fallbacku při neprokázaném typu.
Ordinary call dot narrowing se nemění. Čtyři actual regresní varianty K1/K2 ×
ordinary/suspend kontrolují Base dispatch proti Derived extension receiveru,
zachované ordinary Derived narrowing a nepovýšenou K2 neznámou source hierarchy.
Guardy coroutine mappingu se nemění. Nové fresh buildy/focus jsou stále PENDING.

## Obnovení validační evidence 2026-11-03

Přetrvávající receipt a XML potvrzují dokončené vlastní clean buildy: K1
`684394f8c1017805316918a4daefb8b09a3db0a61c86709f9ee7f8e774087656`, K2
`f3f09bcf1171a5d9bce5ec87a026a62891328b01a9255f2bbd273efdcc617e7a`.
Oba buildy mají exit0 a všech14 build source/lock hashů stále odpovídá.
Combined focus z příkazu v `build-receipt.json` skutečně dokončil
**166 PASS, 0 SKIP v803.20s** (XML166/0failures/0errors), zahrnuje všech54
coroutine případů, dispatch/default-body, control-flow, protocol a CI guards.
Všech200 frozen runtime/test/fixture/JAR hashů stále přesně odpovídá manifestu.
Neopakuje se dokončený build ani focus. Původně final Derived bylo v regresní
fixture před tímto během změněno na open, aby positive ordinary narrowing opravdu
ověřovalo dynamický dispatch. Production se po validovaném buildu nezměnila.

Nový combined full zatím nebyl spuštěn; čeká na nezávislou source closure.
Historický584/10 full jej nenahrazuje. Uživatelská revize T045 v merged PR57
činí GH CI volitelným při splnění všech ostatních kontrol; neprovedené nebo
billing-only CI zůstává neověřené a konkrétní chyba správnosti je stále blokující.

Po nezávislém root source closure nad K1/K2 member-extension fixem byl spuštěn
jeden strict frozen combined full nad634576a: **755 PASS, 10 SKIP v1001.00s**,
exit0. XML765/0failures/0errors; všech200 před/po source/test/fixture/JAR hashů
zůstalo přesně shodných. Povinné workers/K2/Spring flags byly zapnuté; deset
volitelných Maven/Gradle/exporter a non-admin Windows konfigurací je v logu
pravdivě SKIP. Persistent evidence: `full.log`, `full.xml`, `full-status.json`
a `full-inputs.json` v `/workspace/coroutine-main-integration/`. Tento výsledek
nahrazuje výše uvedený PENDING combined full, nikoli omezení podporované matice.

## Ověření kombinovaného K2 s aktuální JPA podporou

Integrace mainb78 zachovala všechny vlastní K1/SourceMapping/control-flow a
coroutine test bytes z full755/10; K2 spojila nové parent JPA annotation fakty
s původním coroutine ABI a member-extension dispatch guardem. Nový vlastní
clean K2 build **exit0/21.684s**, SHA
`ff65f40034a9b21ff7f87535b1ab059d250147ba2c0922f47fb9f8c91e40d46d`.
Coalesced actual K1/K2 member-extension, suspend, continuation, missing-source,
ordinary-name, K1 CFG, K2 JPA a celý dependency-dispatch subset:
**64 PASS, 0 SKIP v299.45s**, XML64/0errors/0failures. Receipt potvrzuje všech14
source/lock hashů nezměněných. Evidence je `integrated-build-receipt.json`,
`integrated-focus.log/xml` v persistent validačním adresáři; nový full se
kvůli parent integraci neopakoval.

## Finální kombinace s main Factory/HTTP/JPA

Po mainc76 integraci vlastní coroutine runtime/test source zůstává byte-identický
full755/10. Nové parent Java registration hooks vyžadovaly skutečné vlastní fresh
K1 i K2 buildy; oba mají exit0, receipt všech15 JVM source/build/lock hashů je
nezměněný. Coalesced actual coroutine/member-extension/JPA/Javac a celý registrar/
FactoryBean subset: **48 PASS, 0 SKIP v205.22s**, XML48/0failures/0errors.
Před tímto během current HTTP/T023/T008/T009/CFG/workspace/dataflow pure integration
ověřila **174 PASS v4.93s**. Evidence je `factory-build-receipt.json`,
`factory-focus.log/xml` a `current-main-pure.log/xml`; nový full se neopakoval.

Dřívější provisional Draft PR37 byl publikován s pravdivým PENDING stavem.
Lokální validační blokace je nyní uzavřena; nezávislé review přesného finálního
base/head páru, ready stav, ověření závislostí a root guarded merge stále zbývají.
Tato poznámka sama nepředstavuje review APPROVE ani merge.

Poslední finální base je main
`8b1eeceb28b71c122c2d48bf179e08cefa79c43c` s typed Spring conditions v6.
Všech15 JVM source/build/lock hashů přesně odpovídá skutečnému Factory build
receiptu výše; vlastní coroutine/source mapping/control-flow a regresní testy
se nezměnily. Pure conditions/provider/CFG/HTTP integrace: **82 PASS,
5 actual/real/fixture deselected v3.49s**, bez skips (`conditions-pure.log/xml`).
Nejde o nový actual compiler nebo full run; platí předchozí obsahově shodné
755/10 full a fresh current-JVM48actual výsledky. Sémantické K2 function anchors
se při spojení nových parent facts přivázaly na aktuální deklarace; epizody
main zůstávají nezměněným prefixem. Finální independent review zůstává rootovi.
