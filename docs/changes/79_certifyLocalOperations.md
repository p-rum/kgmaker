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

Nezávislé source review checkpointu cea9b5d požádalo o dvě konkrétní opravy před
fresh worker buildem: workspace wrapper přidal repo_id do původního proof hashe;
validator dále neodmítal int←String, integer overflow a prázdný literal span.
Opraveno přesným odebráním/ověřením repository wrapperu, explicitními Java
primitive/String literal assignment conversions a mezemi, neprázdným ordered
source spanem a calls-shape guardem. Rozšířená pure protocol sada nyní **32 PASS
v0.25s**; raw worker/pipeline gate tím stále není nahrazen.

## Oprava po skutečném worker běhu a integrace W04

Oba vlastní fresh K1/K2 buildy na477b5f9 prošly (13.851/12.449s), ale následná
sada skončila36PASS1setupERROR: standardní declaration location má optional
origin=handwritten/generated, které Python consumer příliš striktně odmítal.
Doplněn přesný whitelist tohoto existujícího pole v obou místech validace;
source/SHA/range/binding/mirror kontroly zůstaly. Protocol regression zahrnuje
oba origin i odmítnutí dependency origin. Nejde o nový worker build.

Následný bounded actual repro odhalil ztrátu nových per-block evidence refs
v graph_provider.preserve_contexts a views.project. Obě existující projekce teď
přenášejí explicitní local_operation_evidence_ids z vybraných verzovaných CFG
bloků; samotné uchování není povýšení důkazu. Consumer stále vyžaduje přesnou
source/context/CFG/IR identity, source checksum a content hash. Stejný skutečný
K1 workspace/process průchod po opravě prošel1PASS4.69s. Další skutečné testy a
full zůstávají pending, původní neúspěšný log/XML zachovány.

Parent9f6605d (PR62/W04) integrován bez konfliktu runtime; ručně sloučen pouze
CI seznam testů a sémantická metadata, graf bude znovu CLI-generated. Vlastní
Java změny jsou stále byte-exact fresh build checkpoint477b5f9. Zachována
historie210 main epizod a dvě vlastní candidate epizody. Žádný ready/full PASS.
