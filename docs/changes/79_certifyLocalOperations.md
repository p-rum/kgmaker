# Compiler důkazy lokálních operací pro T025

T025 revize2 je samostatná upstream dodávka před T026. Původní T025 PR60 je
sloučené; tento PR neimplementuje seskupování business kroků. Současné CFG důkazy
jsou SYNTAX_CANDIDATE a technické kroky UNRESOLVED, proto je nelze přeznačit jen
podle labelu nebo absence emitovaných calls.

Plán: skutečný bounded Javac důkaz literal evaluation a přiřazení literálu do
compiler LOCAL_VARIABLE s primitive nebo canonical java.lang.String typem.
Původní CFG se staví pouze jednou. Nový důkaz se váže na konkrétní IR cestu/digest,
source/context/caller a strukturální CFG block včetně finally klonů. Jen ověřený
operation node může být RESOLVED s vlastním SYMBOL_RESOLVED proof; původní CFG
provenance a unresolved přechody zůstávají zachované odděleně.

Nepodporované Kotlin/legacy/bytecode/initializer/lambda či compiler-error bodies,
field/parameter/boxed/array/call/cast/arithmetic výrazy zůstávají UNKNOWN. Nic se
nevykonává, neodvozuje se business význam ani dostupnost dat. Nový store či druhý
CFG/resolver nevzniká. Optional worker/body verze zachovává čtení starých vstupů.

Baseline implementace: main `ef3ab4050289aafd557caa5414c594698da006ea`, který
zahrnuje původní T025, Arg, HTTP a Kafka kontrakty. Note79 ověřena vůči main,
worktrees a otevřeným PR;77/78 jsou rezervované jiným dodávkám.

Architekturu ověřil policy_review a nezávisle resume_return. Cílené skutečné RED,
nové buildy, focus a full výsledky budou doplněny po skutečném běhu; nyní žádný
z těchto gate není PASS. Původní T025 full1104/10 není důkazem tohoto rozšíření.


Skutečný RED: pinned již postavený Arg worker úspěšně analyzoval Java fixture;
`local_operation_version` v named body chybělo. **1 FAIL v0.73s**, žádný setup
error. XML/log/receipt jsou v `/workspace/local-operation-validation/red.*`.
Test vznikl před novým producerem; běžel ve FIFO s explicitním unchanged Arg
worker home. Během čekání vznikal pouze nový nezávislý consumer/materializer kód,
nikoli donor worker. Tento RED není výsledek nového workeru a není PASS.

Dílčí provedené kontroly: explicit protocol specimens **11 PASS v0.19s** (po
canonical identity guardu opakovaně11PASS0.13s), bez tvrzení skutečného compiler
běhu; existing T025/T023/worker-protocol **120 PASS,2actualDESELECTED v4.44s**.
Samostatná kompilace nového JavaFrontend proti neměnnému Arg State/JAR/lib API
pomocí JDK21 javac prošla, ale není to nový kompletní K1/K2 worker ani runtime
acceptance. Celé vlastní workery a actual pipeline/full jsou stále UNKNOWN.
