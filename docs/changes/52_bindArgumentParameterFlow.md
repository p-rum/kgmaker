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
- Jediný finální whole-suite běh je frontovaný pod
  `flock /workspace/kgmaker-heavy-tests.lock`, výstup `/tmp/s07-final-full.log`,
  JUnit `/tmp/s07-final-full.xml`; výsledek bude doplněn po doběhu.
- Scoped semantic update/apply/validate PASS, zachováno6 manual concepts/15 edges
  a všech109 inherited episodes. Refaktor workspace posunul scanner ID stávající
  resolve_service_ownership259→273; změněn jen cíl této doložené relation, nikoli
  její význam ani architecture citation143. CLI scan/check a git diff --check PASS.
  Nová immutable implementační memory bude zachycena až s finálním full výsledkem.

Finální runtime SHA-256 K1 `dd0f91d1d71c374ca251f486e254a0c25fba609a5eb0f66cde496c0e583f04bb`,
K2 `56b00cf030c6eb05de8cce4f843b37548048fee9a13548970a12045e4bbf7d82`.
Kód a runtime jsou od finálního preflight frozen; další práce je dokumentace/evidence.
Povinné compiler CI explicitně zahrnuje nový tests/test_argument_parameter_flow.py.

## Zbývající hranice

Širší intraprocedural value equivalence, generated operand-stack values,
implicitní receiver binding, K2 Kotlin argument API a úplná produkční matice nejsou
tvrzené. Skutečné runtime values, dostupnost dat, globální pořadí ani async/HTTP/Kafka
tok nejsou tímto work package dodané. CI billing blocker se nesmí obejít lokálním
PASS ani mergem Draft PR.
