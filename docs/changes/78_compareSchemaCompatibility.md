# T003-S06-W08 — offline schema compatibility (rozpracováno)

Datum: 2026-11-03. Task T003-S06-W08, AC01–04.
Výslovný draft stack nad W04 checkpoint7dc10168f7d2d0a7a65d62f5885130efa958a4db;
W04 není tímto schválen ani merged. Note78 ověřeno proti local worktrees/main a
changed paths všech otevřených PR;77 ponecháno Kafka rev2. Před publikací recheck.

Plán: reuse stejného Replay a compiler-owned ORM/realm/XML graph/proofs; report
COMPATIBLE/CONFLICT/UNKNOWN po dimenzích type/nullability/precision/scale/PK/FK/UK.
Explicitní chybějící column po rename/drop zůstane reportovaná: CONFLICT jen při
ověřené explicitní ORM column+selected physical table a COMPLETE replay stejného
realm/target, jinak UNKNOWN. Inferred naming není absence proof. XML effective
nullable/precision/keys bez typed evidence zůstávají UNKNOWN, bez regex fallback.
Povinný skutečný pozitivní supported type/null/decimal/key subset; všechnyUNKNOWN
nejsou pozitivní acceptance. Žádná availability/deployment/population promotion.

Zatím pouze durable task/architektura a acceptance RED; implementace/full/PR nejsou
hotovy. Stav bude doplněn konkrétními skutečně provedenými výsledky.

## Průběžná skutečná evidence

- RED3FAIL/0.04s: chyběl referenced_columns, FK target column se neověřoval,
  chyběla veřejná compatibility API; rozšířený RED5FAIL/0.05s obsahoval actual
  positive test před dostupností API (worker se tehdy nespustil).
- Stejný Replay rozšířen o ordered referenced_columns, arity/existence guard,
  rename aktualizaci a fail-closed drop referenced target; parser version3.
- První validní actual běh3PASS/1FAIL/4.30s,239 frozen inputs unchanged: chyba
  fixture předávala augment_framework_graph contextID místo contextdict. XML/log
  `/workspace/validation/schema-compatibility/first-actual.*` zůstávají zachovány.
- Root early review odhalilo analyzer-status/freshness záměnu, qualified workspace
  metadata context a neznámý SQL family conflict. Skutečný capture potvrdil
  statusPARTIAL/freshnessCONTENT_VERIFIED; opraveno bez reinterpretace evidence.
- Grouped actual6PASS/0SKIP/9.22s,239 frozen inputs unchanged: skutečné Javac FIELD
  type/null/decimal12/2/PK/UK ve K1/K2 distribucích, customdemo.BigDecimal UNKNOWN,
  actual workspace positive, nullable/type/key snapshot tamper UNKNOWN a foreign
  target UNKNOWN. Nejde o pozitivní Kotlin/JPA annotation proof.
- Report/provider/cache/CLI integrace:54PASS/30actual deselected/3.41s; samostatný
  Flyway regression13PASS/0.29s. Current expanded actual focus pending, ne PASS.

Worker donor `/workspace/http-execution`:15 git-tracked JVM source/build/lock
files přesně odpovídají W04 stacku i skutečnému source-before manifestu, obě
SUCCESS build receipts K150cf8376/K22eb240a5 a všechny JAR/library hashes ověřeny
před kopií. `/workspace/validation/schema-compatibility/worker-provenance.json`.
Žádný nový worker build. Není zatím full/ready/merge evidence.

## Lifecycle a konkrétní poslední actual výsledky

Focus96629 se skutečně provedl před obnovou prostředí:3PASS/1FAIL/11.78s,
runnerexit1/12.242s, všech269 source/test/fixture/JAR inputs beze změny. Selhal až
CLI assertion: fixture vytvořila money-config.json po inspect a provider správně
označil source/config snapshot STALE. Config nyní vzniká před capture; žádný
freshness guard nebyl oslaben. Dřívější assertion v témže testu se nepovýšily
na tvrzení dokončeného actual PASS.

Root požadovalo skutečný úzký FK kontrakt: canonical FIELD ManyToOne, explicitní
JoinColumn(name,referencedColumnName), stejné ověřené fyzické owner/target tabulky,
compiler→association witness, target FQN shodné s field descriptorem, structured
Replay FK + PK/UK. Captured skutečný Javac replay měl RED UNKNOWN a po změně
COMPATIBLE; fresh expanded actual pozitivní/negativní matice je zatím pending.
PROPERTY/inherited physical column links doplněny v témže framework produceru
přes existující selected-realm matcher. XML není odhadováno ani retargetováno.

Doložený rename bug: Replay zachovalo původní ID, ale starý realm validator
vyžadoval ID z aktuálního jména. Opraveno výhradně ve W08, bez zásahu do frozen
W04 full: parser4/cache version2, immutable creation identity metadata a validace
stable ID/incarnation. Mapování používá pouze CURRENT schema_object komponenty;
previous_names není lookup fallback. Audit aktualizuje PK/UK/FK lokální/referenční
tuples i last_change a opravuje dvojí rename dětí při schema rename. Ověření
zdrojů zahrnuje celý migration inventory prefix a snapshot provenance.

Pure integrace66PASS/32actual deselected/2.73s, včetně strukturálního creation
identity/rename/incarnation a legacy/availability immutability scope. Fresh grouped
actual po těchto změnách běží/čeká; full/source closure/ready/merge stále pending.

## Publikovaný draft checkpoint

W04 dependency PR62 je nyní merged (ověřeno přes GitHub); W08 začínalo nad
checkpoint7dc1016 a current-main refresh zůstává povinný po dokončení frozen focus.
Publikovaný draft PR64 má source checkpoint8dbaf878fcb18db1788e750a3d6b8fd53a933b7e.
Aktuální actual focus43409/creation-source.json má269 frozen inputs a zatím není
PASS. Full, finální semantic/memory a nezávislé exact-pair review nejsou hotovy.

## Current-main skutečný focus a nezávislé review guardů

Main9f6605db... integrován, runtime cache-list konflikt vyřešen zachováním všech
parent Kafka i vlastních JPA/compatibility version tokens. Verified Arg donor
15source/build/locks +30JAR, oba fresh SUCCESS build receipts a108PASS actual;
K12bf6cbde/K224461c43, bez nového buildu. Current-main focus23PASS/0SKIP91.73s,
runnerexit0/92.104s, všech283 source/test/fixture/JAR inputs beze změny, XMLmain.xml.
Zahrnuje skutečnou FIELD/PROPERTY/inherited a FK/rename/incarnation matice, CLI,
namespace/canonical-member negatives i XML/W04 reprojection/resource/two-unit seams.

Nezávislé review našlo P1 v navazujícím T015 projector: hardcoded v6 stamp guard
nevyžadoval physical binding pro v7. Repro2RESOLVEDreads/writes bez physicalproof
byl skutečně potvrzen. Oprava používá přesnou množinu known historical v6/v7JPQL/
v7compat + current JPA_RULE_VERSION; neznámý nebo malformed explicit stamp je
UNKNOWN s diagnostikou, unstamped legacy kontrakt zůstává zachován. Producer
rules_version je t015-data-resources-2-realm-rule-guards, schema/IDs beze změn.
Pure65PASS/7actual deselected; actual selected-realm missing-proof negative pending.

Review P2: precision='oops' současně v symbol i canonical Node members původně
vyvolalo TypeError; scale=-1 mělo být unsupported UNKNOWN. Member-specific typed
guards nyní kontrolují precision/scale exact int0..INT_MAX (bool není int), bool/
string members podle kontraktu, před výpočtem. Nezávislý captured repro nyní
GUARDED UNKNOWN;9 malformed-member public mutation případů je v grouped actual.

Full prerequisite: po dokončeném validním focus znovu ověřeno15source+30JAR a
zkopírováno kompletních102license files z téhož donor closure. Oba
target/licenses/kotlin/LICENSE.txt mají SHA shodné s oficiálním Kotlin LICENSE.
Receiptlicense-prerequisites.json. Další ignored fixture/runtime prerequisites
se materializují až po aktuálním frozen guard focus; full zatím nefrontován.

## Guard review — dokončený grouped actual

Po dokončeném validním předchozím focus byl spuštěn pouze relevantní grouped
guard focus: **29PASS/0SKIP86.52s, runnerexit0/86.917s**,
`/workspace/validation/schema-compatibility/guards.xml`. Nezávislá kontrola XML
a všech385 frozen source/test/JAR/license hashes prošla, beze změn.
Zahrnuje P1 actual selected-realm missing-physical-proof negatives a zachované
T015/W04 current positives; P2 devět malformed-member mutací současně v symbol
a canonical Node (včetně precision='oops', negative/bool/string scale) končí
UNKNOWN bez výjimky a bez mutace. FIELD/PROPERTY/inherited, FK/rename/incarnation,
CLI a namespace scope běží na obou skutečných K1/K2 distributions s Javac facts.
Nejde o implicitní runtime/DB proof ani univerzální Kotlin annotation coverage.

Root REQUEST_CHANGES P1/P2 vyžaduje nezávislé přezkoumání tohoto checkpointu;
pouhé29PASS není review APPROVE. Full ještě nebyl spuštěn.

## Integrace aktuálního parentu 9442114

Nezávislé root review uzavřelo P1/P2 nad1568d568. Jeho queued full nebyl
spuštěn: vlastní flock136928 byl bez potomků i start markeru;1462 input hashes
byly beze změn. Na pokyn koordinátora byla ukončena pouze tato neaktivní fronta
(audit full-unstarted-cancelled-1568.json), nikoli platný běh. Žádný full PASS.

Current main9442114 přidává local-operation proofs a T026/T011. Vlastní P1/P2,
creation identity a compatibility runtime zůstávají zachované; workspace
obsahuje i parent qualification proofů. Všech27 tracked worker souborů je
byte-exact s původním built source donor receipt; všech132 původních JVM
artifact hashes včetně kompletních licenses ověřeno před kopií i po ní.
Receipt current944-workers.json; žádný nový build ani instalace. Nový focused
actual a full jsou zatím neprovedené, před full následuje composition review.

## Current-parent actual a source closure

Current944 coalesced actual dokončen: **152PASS/0SKIP127.01s**, runnerexit0
127.697s; XML current944.xml a status current944-status.json. Všech1471 broad
frozen inputs a HEAD a1fe8306 beze změn, nezávisle znovu ověřeno. Zahrnuje
compatibility guard matrix, local-operation proofs, HTTP consumer catalog a
T015/W04 selected physical-realm seams. Root nezávisle schválil composition
a1fe8306 a povolil jeden strict full; full výsledek zatím neexistuje.
