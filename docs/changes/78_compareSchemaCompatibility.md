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
