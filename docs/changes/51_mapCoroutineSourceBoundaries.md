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
nezaměňuje se source hierarchy view pro dispatch. SourceMapping.java,
control_flow.py a celý coroutine test modul zůstávají přesněc8867f3; SMAP,
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
