# Compiler-proven argument → parameter flow

T003-S07-W01, AC01–AC04; nadřazené T003/S07 zůstávají PARTIAL.
Stack baseline `89e50cf4cf8edbebc4f9d08879656698c75ebd50`, závislost Draft PR35,
cílová větev `feat/t003-s04-04-dependency-dispatch-hierarchy`.
GitHub Actions billing je externě pozastavené; není tvrzen remote CI PASS ani merge.

## Problém a skutečné změny

SOURCE_ONLY dataflow obsahoval jen lokální expressions. Javac/K1 zachovávaly
resolved call sites a method parameter metadata, ale žádný doklad argument→formal
binding. První actual JDK21/K1 acceptance běh selhal **2 FAIL, 13.06 s**.
TypeScript už měl starší argument facts, ale bez call-site a transformation kontextu.

Javac používá skutečný ExecutableElement a attributed executable formal types;
K1 používá resolved argument map včetně named order, default omission a vararg.
TypeScript rozšiřuje existující signature proof o source argument value occurrences
a stejné canonical parameter IDs. Původní přímá symbolová závislost se zachová
přes compiler-proven derived_from, nikoli přes name-only heuristiku.

Source argument má identitu z původního call site a source argument indexu.
Formal používá existující `METHOD_ID:parameter:INDEX` konvenci. Proof nese context,
původní call site, oba indexy, declared-contract binding kind a transformation
DIRECT/VARARG_ELEMENT/VARARG_ARRAY/VARARG_SPREAD. DIRECT váže **výsledek** source
expression na formal; netvrdí identitu výrazu ani absenci implicitních konverzí.
Vararg spread je aggregate dependency, ne vymyšlený seznam hodnot či pořadí běhu.

Call-site mapping status PROVEN/UNKNOWN/NOT_EXECUTION a konkrétní důvod jsou
aditivní version1 metadata. Omitted defaults nesou DEFAULT_VALUE_NOT_EVALUATED
bez vymyšleného value edge. Reference creation nemá execution arguments.
K2 Kotlin zůstává explicitně K2_ARGUMENT_BINDINGS_UNAVAILABLE; Java v K2 distribuci
používá Javac proof. ASM operand stack ani implicitní accessor/operator binding
mimo ordinary call expressions se neodhadují.

Compiler-error recovery TypeScript signature není argument mapping proof. Nový
actual negative na rozpracovaném workeru selhal **1 FAIL, 20 deselected, 4.15 s**;
oprava vyřadí binding při překrývající se compiler error a zachová konkrétní UNKNOWN
boundary. Spread před fixed formals bez tuple proof zůstává také UNKNOWN.
Java generic method vararg používá instantiated formal type; generic constructor
bez takového type proof neodhaduje array packing a dává lokalizovanou boundary.

## Stávající model, bezpečnost a kompatibilita

Nevzniká nový katalog ani store schema. Worker protocol zůstává v1, graph/store
v1/v2/v3 jsou čitelné. Nové proof nese argument_mapping_version=1; legacy
unversioned facts zůstávají čitelné, ale nezískávají nové silné impact paths.
Candidate dispatch se nemapuje na pozorovanou implementation; formal je pouze
compiler-declared contract. Availability zůstává UNKNOWN, execution NOT_OBSERVED.

Python ověřuje kontexty, call-site/formal vazbu, indexy, transformation a duplicity
před publikací. Malformed/ambiguous mapping nevybere libovolnou variantu a nemění
poslední validní generaci. Test skutečného graph store ověřuje byte-identický stav
před/po odmítnutém protocol response bez implicitních procesů.

Evidence zachová typed binding provenance; process JSON připojí vazby i status
původního call site a stále odmítne nejisté dispatch body expansion. Directed
impact zachová dosavadní v1 path shape a přidá samostatné contextual binding
records; candidate či legacy edge nepovýší. Workspace kvalifikuje argument,
formal, call-site i context references. Scan/hook/projection nespouštějí aplikaci,
worker, instalaci ani build implicitně.

## Příklad

Po explicitním content-bound importu a compiler inspection:

```bash
kgmaker inspect code --root project --kotlin-backend k1 --kotlin-version 2.1.10
kgmaker flow render --root project --entry METHOD_ID --view process --format json
kgmaker impact --root project --entity ARGUMENT_ID --include-data-flow --format json
```

Při více variantách je nutný odpovídající existující --context/--scope výběr.
Named Kotlin `pair(second="x",first=n)` zachová source argument0→formal1 a
argument1→formal0. `pair(first=n)` nedoplní vymyšlené vyhodnocení defaultu.

## Provedené kontroly

Všechny actual compiler testy mají explicitní vlastní worker home
`/workspace/argument-flow/workers`, PYTHONPATH=/workspace/argument-flow/src,
Temurin21.0.6+7, Kotlin2.1.10 a pinned K2 Analysis API. Žádný worker test se
nevydává za PASS při chybějícím toolchainu.

- Initial source rebuild K1/K2 PASS31.23/19.16 s; tehdejší focused **19 PASS, 20.98 s**.
- Finální sequential preflight podle výslovné parent výjimky mimo globální FULL lock:
  K1 `python workers/jvm/build.py --kotlin-home /workspace/tools/kotlinc --maven-repository /workspace/tools/m2 --java-home /workspace/tools/jdk-21.0.6+7` PASS45.32 s;
  K2 stejný příkaz + `--backend k2 --analysis-api-home /workspace/tools/k2-verified` PASS34.86 s.
- Finální `python -m pytest -q tests/test_argument_parameter_flow.py`:
  **25 PASS, 62.62 s**; 11 skutečných compiler případů a 14 model/protocol negatives,
  `KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1`, žádný SKIP.
- TypeScript project-reference a related selection během implementace:
  **17 PASS, 21 deselected, 153.82 s**. Samostatná TS positive/error check po opravě
  **2 PASS, 21 deselected, 7.67 s**; finální source je znovu pokryt focused25.
- Stávající pure dataflow/workspace/control-flow **33 PASS, 3.52 s**; finální
  dataflow/workspace/control-flow/protocol/mandatoryCI **59 PASS, 6.59 s**.
- Dodatečné pure negative gates ověřují samostatně REQUIRE_WORKERS i REQUIRE_K2:
  **3 PASS, 25 deselected, 0.09 s**. Pouze skutečně chybějící optional toolchain může
  být SKIP; runtime/protocol chyba se neskrývá. Compiler source a runtime zůstaly
  beze změny, tehdejší suite obsahovala28 feature cases.
- Před spuštěním queued full odhalil actual mixed Java/Kotlin Integer.parseInt
  regression příliš přísnou rovnost display parameter names (**1 FAIL, 10.48 s**).
  Javac/K1 mají stejný canonical formal/index, ale různé zobrazované názvy.
  Odstraněna pouze rovnost názvů; method/index/call-site/context a ostatní proof
  checks zůstaly. Ověření mixed case + malformed/duplicate/candidate negatives:
  **12 PASS, 17 deselected, 5.39 s**. Suite má29 feature cases (12 actual,17 pure).
  Finální Python correction mtime20:05:51.291 UTC předchází actual full pytest
  process start20:05:57 UTC; tento jediný whole-suite běh tedy načetl opravený zdroj.
- První current-source full odhalil14 setup errors existující compiler integration:
  framework annotation fallback volal None.get pro nový formal s path a range=None.
  Známý failed běh byl bezpečně přerušen: **165 PASS, 2 SKIP, 14 ERROR, 150.89 s**,
  KeyboardInterrupt; původní `/tmp/s07-final-full.log` a XML zůstaly zachované.
  Není to PASS ani problém prostředí.
- Minimální Python null-safe guard neodvozuje vymyšlený parameter locator. Actual
  inspect_jvm regression **1 PASS, 43 deselected, 9.21 s**; potom celý existující
  CompilerWorkerTests s --maxfail=1 **14 PASS, 103.07 s** pod vlastními pinned workers.
  Source/runtime JVM se nezměnily. Finální feature suite má30 případů (13 actual,17 pure).
- Teprve po opraveném fixture byl frontován finální corrected full pod
  `flock /workspace/kgmaker-heavy-tests.lock`, výstup `/tmp/s07-final-retry-full.log`,
  JUnit `/tmp/s07-final-retry-full.xml`: **605 PASS, 10 SKIP, 608.68 s**.
  Všech30 feature cases běželo; devět SKIP jsou optional Maven/Gradle/exporter/two-JDK
  prerequisites, desátý skutečný non-admin Windows CI-only gate. Source/test
  manifest12 files i oba runtime SHA zůstaly byte-identické po celý corrected full.
- Scoped semantic update/apply/validate PASS, zachováno6 manual concepts/15 edges
  a všech109 inherited episodes. Refaktor workspace posunul scanner ID stávající
  resolve_service_ownership259→273; změněn jen cíl této doložené relation, nikoli
  její význam ani architecture citation143. CLI scan/check a git diff --check PASS.
  Finální immutable implementační memory zachovává109 inherited episodes a přidává
  episode110 s actual focused/full validations; následný CLI scan/check PASS.

Finální runtime SHA-256 K1 `dd0f91d1d71c374ca251f486e254a0c25fba609a5eb0f66cde496c0e583f04bb`,
K2 `56b00cf030c6eb05de8cce4f843b37548048fee9a13548970a12045e4bbf7d82`.
JVM source/runtime jsou od finálního preflight frozen; jediná následná produkční
Python změna odstraňuje chybnou rovnost display názvů před actual full startem.
První failed full byl zastaven před null-safe framework opravou; všechen
produkční kód a feature testy jsou od spuštění corrected retry frozen.
Povinné compiler CI explicitně zahrnuje nový tests/test_argument_parameter_flow.py.

## Zbývající hranice

Širší intraprocedural value equivalence, generated operand-stack values,
implicitní receiver binding, K2 Kotlin argument API a úplná produkční matice nejsou
tvrzené. Skutečné runtime values, dostupnost dat, globální pořadí ani async/HTTP/Kafka
tok nejsou tímto work package dodané. CI billing blocker se nesmí obejít lokálním
PASS ani mergem Draft PR.

Finální source je připravený pro nezávislé review a stacked Draft do explicitní
PR35 větve. GitHub billing stále blokuje remote povinné gates; lokální full tento
blocker ani zákaz merge bez zeleného CI nenahrazuje.


## Protocol guard opravy a kombinace s aktuálním parentem

Nezávislé source review našlo kontradikce nového protocol proof: list/object
enum měl raw TypeError, argument mohl tvrdit cizí owner nebo jiný occurrence
index a list/object call_site obešel structured rejection. Opravy f92c83e a
ee14ea8 kontrolují primitive enum type, source owner proti caller, canonical
site:argument:index a případný explicitní source index před publikací.
Actual captured Javac/TS response table: RED2 FAIL v13.59s, corrected focus
51 PASS v99.49s a call_site followup11 PASS v9.69s; žádný SKIP. Původní605/10
full je historický před těmito guards, ne finální validace změněného source.

Parent integrace používá ověřený PR35 `10ad31912fb6d7c099a0b0a53c8e07bcca91f2ff`,
obsahující main49c46b0/T015 a TS freshness/callbacks. JVM i argument test modul
jsou byte-identickéee14ea8. TS worker5 označuje odlišný kombinovaný kontrakt:
využívá jednou zachycené diagnostics a input_discovery; selected signatures a
callback candidates zůstávají. Version1 value occurrence→declared formal proof
je oddělený od původních unversioned callable→implementation-parameter candidates.
Ordinary symbol arguments používají versioned occurrence a compiler derived_from,
ne duplicitní neversioned formal claim. Candidate runtime dispatch zůstává otevřený.

Tři material callback assertions na kombinovaném source byly skutečně RED:
3 FAIL v44.59s (lowercase formal kind a nová oddělená occurrence edge). Minimální
fixture adaptace dále vyžaduje exact canonical formal/owner/program identity, oba
původní DISPATCH_CANDIDATE proofs a zvlášť version1 declared-contract proof.
Potom GREEN3 PASS,4 deselected v93.89s. JVM/args testy se nezměnily; production
guards se neoslabily. Oba bounded direct repro běhy měl root výslovně povolené
mimo heavy lock, bez buildu/instalace/full. Původní queued matrix ani queued RED
nezačaly (žádný pytest child); nahrazené vlastní queues byly zrušeny před startem.

Jedna platná společná focused matrix pod heavy lockem je GREEN: **106 PASS
v233.38s**, bez skips (arguments, callbacks, freshness, protocol a mandatory CI).
Následující jediný fresh combined strict full je GREEN: **733 PASS,10 SKIP
v1162.26s**, exit0; XML743 tests/0errors/0failures/10skips. Všech200 zmrazených
source/test/fixture/JAR SHA256 zůstalo beze změny. Source checkpoint b5ac0f
má přesně stejný tree100835a9583fd4feb2c68bf59556fc78946cb7e5 jako417e2aa;
navíc obsahuje ancestry-only merge ověřeného main
ec333966e657896382f310ef018835e3d696513e. Rozdíl417→b5 je prázdný.
Parent134 immutable episodes jsou exact prefix, unikátní původní child captures
zůstávají nezměněné. Billing pause již byla odblokována; root vlastní nezávislé
exact-head review a publikaci/CI, implementační agent nepushuje ani nemerguje main.


Finální persistent evidence: `/workspace/argument-main-integration/focus.log`,
`focus.xml`, `full.log`, `full.xml`, `full-status.json` a `frozen-source.json`.
Deset skips jsou pouze optional Maven/trusted exporter, Gradle8.13/Kotlin2.2.20
cache, druhý JDK21+ a skutečný non-admin Windows smoke; žádný mandatory actual
argument/callback/freshness případ nebyl přeskočen. Historické RED2/51/11 a
původní605/10 zůstávají zachovány ve svém původním rozsahu. Finální metadata
po běhu nemění žádný source/test/runtime byte. Semantický merge zachovává všechny
podporované manual facts; obsolete resolve_service_ownership259 duplicate byl
nahrazen skutečným current273 s ověřenou architecture citation156.

## Integrace main po změně CI politiky a Kotlin JPA

Main `b78d2e62148f225be7ba8c53c839f8b052ee269d` obsahuje T045 revizi2,
Kotlin JPA W01 a T023. Integrace zachovává jejich runtime i vlastní argument
proof guards; konflikty byly pouze v generovaných grafech a stavovém přehledu.
Main149 immutable episodes tvoří přesný prefix a původní child captures zůstávají.
Sémantické duplicitní ownership odkazy byly sjednoceny na doložený workspace modul.

Dřívější full733PASS10SKIP platí pro vlastní nezměněný argument source; nová
K2 kombinace vyžaduje čerstvý explicitní build a integrační actual kontroly.
Jejich výsledek zatím není PASS. GH CI je podle výslovného pokynu uživatele
volitelné, všechny ostatní acceptance a nezávislé review nad aktuálním párem
zůstávají povinné. Celý T003-S07 ani T003/T004 nejsou dokončené.
