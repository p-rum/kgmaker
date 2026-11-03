# JPA ORM XML overrides

Datum: 2026-10-26. Zadání: T003-S06-W03 a T003-AC06. Acceptance:
T003-S06-W03-AC01–AC04.

JVM inspection nyní pro vybraný persistence unit čte standardní
`META-INF/persistence.xml`, jeho mapping files v deklarovaném pořadí, případně
výchozí `META-INF/orm.xml`. Compiler-resolved Java/Kotlin class identity zůstává
autoritativní. Podporovaný XML subset mapuje entity/table a scalar ID, basic a
version atributy; XML mapping má přednost před annotations a
`metadata-complete` skutečně odstraní annotation-only fyzické vazby. XML
evidence nese relativní cestu, SHA-256, persistence unit, pořadí a zdrojovou
prioritu. Entity inheritance strategy z XML se zachová na výsledné tabulce a
ovlivní finální volbu tabulky pro podporované zděděné atributy.

Neznámý namespace/verze, nepodporovaný construct, chybějící nebo nejednoznačná
class/attribute reference, neúplný override, DTD/external entity a soubor mimo
repository root zůstávají diagnostikou a UNKNOWN; annotation fallback nesmí
vytvořit fyzické jméno. XML parser nepoužívá síť, entity resolver, build ani
databázi. Strict publication odmítá chybné XML bez nahrazení posledního
validního uloženého graphu. Graph/store schema zůstává v3.

Přímé actual-Javac fixture v `tests/test_orm_xml_overrides.py` pokrývá partial
table/column precedence, metadata-complete, XML-only fields, mapping-file
pořadí, vybraný persistence unit, `exclude-unlisted-classes`, mapped-superclass
projection, XML inheritance strategy, invalid-reference strict-store ochranu,
neznámý namespace, unsupported construct a DTD odmítnutí. Další regresní
matice pokrývá UTF-8/UTF-16 BOM variants, unsupported encoding, bounded reads,
namespace reset, standard nested metadata/default access, strict-store byte
preservation, XML freshness capture/replay a shared inherited columns.

Kontrola:

```bash
PATH=/workspace/tools/jdk-21.0.6+7/bin:/workspace/tools/kotlinc/bin:$PATH \
PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q tests/test_orm_xml_overrides.py
```

Focused actual-Javac XML fixture — původně 14 passed; po integraci W02 exact-owner
indexu suite prokázala 15 passed včetně dvou tříd `Order` s odděleným XML
`metadata-complete` scope. W02 exact-owner repository regression: 1 passed;
actual K2 mapped-superclass owner fixture: 1 passed. Úplný suite
`PATH=/workspace/tools/jdk-21.0.6+7/bin:/workspace/tools/kotlinc/bin:$PATH PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q`
pod sdíleným lockem — 533 passed, 28 skipped in 451.74 s (historický běh před
W02 exact-owner merge a aktuální regression test; tento refresh plný suite
neopakuje, protože se mění jen scoped XML owner lookup a metadata). Před plným během
`kgmaker-test-prerequisites.py` potvrdil existující core compiler/fixture/API
artefakty a neprovedl build ani instalaci. Semantic validace, `kgmaker scan`,
`kgmaker check` a `git diff --check` prošly. T003-S06 nadále zůstává PARTIAL;
provider-specific XML constructs, širší relationship/query grammar a schema/
deployment availability nejsou tímto omezeným XML subsetem prokázány.

## W02 canonical-owner/current-main integration refresh `283987a` (2026-10-27)

Čtyři XML overlay přístupy k `entity_attributes` nyní používají přesný owner
vyřešený compilerem, včetně registrace XML-only scalar atributu. Skutečný Javac
regression se dvěma třídami `Order` ověřuje, že `metadata-complete` pro
`demo.Order` ponechá annotation column `other.Order` a potlačí pouze
`demo.Order.extra`. W02 framework/compiler-source changes zůstávají společně s
W03 XML overlay; W01/W02 parent refresh nepřepsal jejich testy.

Finální actual-Javac XML sada: **15 passed**. Cílený W02 repository-owner
regression a actual K2 mapped-superclass owner fixture: po jednom passed.
Po posledním W01→W02→W03 refreshi proběhl nový plný běh:

```bash
flock /workspace/kgmaker-heavy-tests.lock env \
  JAVA_HOME=/workspace/tools/jdk-21.0.6+7 \
  PATH=/workspace/tools/jdk-21.0.6+7/bin:/workspace/tools/kotlinc/bin:$PATH \
  PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q
```

Výsledek: **614 passed, 28 skipped in 1009.11 s**. Před během
`kgmaker-test-prerequisites.py /workspace/s06-w03` potvrdil existující core
compiler/fixture/API vstupy; nic nestavěl ani neinstaloval. `kgmaker scan`,
semantic validation, `kgmaker check` a `git diff --check` doplňují final refresh.
T003-S06 zůstává PARTIAL; provider-specific XML constructs, širší
relationship/query grammar a schema/deployment availability nejsou tímto subsetem
prokázány.

## Audit-boundary repair (2026-10-27)

Parser rejection now uses an encoding-aware Expat declaration guard before
ElementTree, reads at most 2 MiB plus one byte, diagnoses unknown encodings and
requires every XML element to remain in the document's JPA namespace. The
standard nested `persistence-unit-metadata/xml-mapping-metadata-complete` and
`persistence-unit-defaults/access` are honored; unknown nested constructs set
the selected mapping scope UNKNOWN and suppress annotation physical bindings.
JVM context selection now captures root persistence/default mapping candidates,
the selected unit's referenced mapping paths, content hashes and resolved
targets, including absent candidates. Offline replay detects same-length edits,
selection/reference changes, appearance/removal, and symlink retargeting; old
JVM contexts without this capture remain readable only while no JPA XML input is
present. Unknown/malformed JVM snapshot versions and JVM snapshot markers on
other languages fail stale before replay; external and looped descriptor
symlinks are captured as invalid without uncaught resolution errors. The JPA
rule version is now `annotation-source-v5-orm-xml-v2`. Shared mapped-superclass
column nodes are retained while a sibling effective entity still references
them.

Focused validation before the final bounded guard additions: XML override suite
**29 passed**; graph provider, Gradle variant and TypeScript freshness suites
**56 passed, 2 skipped**. The added snapshot-version, outside/looped-symlink,
and owner-isolated shared-column cases passed their targeted checks. One strict
full-suite attempt was interrupted after pytest reported **352 passed, 9
skipped, 1 failed**: two old assertions expected JPA rule v1. The actual-Javac
compatibility test passed after updating those expected literals to v2; no
runtime behavior changed for that correction.

Final strict repository-wide command:

```bash
exec flock /workspace/kgmaker-heavy-tests.lock env \
  JAVA_HOME=/workspace/tools/jdk-21.0.6+7 \
  PATH=/workspace/tools/jdk-21.0.6+7/bin:/workspace/tools/kotlinc/bin:$PATH \
  KGMAKER_WORKERS_HOME=/workspace/s06-w03/workers \
  KGMAKER_TEST_MAVEN_REPOSITORY=/workspace/tools/m2 \
  KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 \
  KGMAKER_REQUIRE_SPRING_IMPORTS=1 PYTHONPATH=src \
  /workspace/kgmaker-venv/bin/python -m pytest -q -rs --tb=short --maxfail=1 \
  --basetemp=/workspace/s06-w03-corrected-full-pytest \
  --junitxml=/workspace/s06-w03-corrected-full.xml
```

Result: **652 passed, 10 skipped in 761.46 s**. The required worker, K2 and
Spring-import checks ran with mandatory flags. Nine skips are explicit Maven or
Gradle execution prerequisites (trusted exporter, multiple JDKs, or pinned
Gradle/Kotlin caches); the tenth is the Windows non-admin smoke gate. Persistent
output is `/workspace/s06-w03-corrected-full.log`; JUnit XML is
`/workspace/s06-w03-corrected-full.xml`. The prerequisite checker, run with the
same JDK/Kotlin PATH, confirmed core compiler/fixture/API artifacts without
building or installing anything. Earlier **614/28** and **533/28** counts are
historical and superseded by this final run. Semantic/memory refresh results are
recorded below after their final validation. T003-S06 remains PARTIAL.


## Obnovení kontroly 2026-11-03

Po restartu prostředí byl přečten dokončený corrected-full log a JUnit: 662
testů, 0 failures, 0 errors, 10 skips, tedy **652 PASS / 10 SKIP**. Všech pět
auditem zmrazených runtime/test SHA zůstalo přesně shodných; žádný nový full
se neopakoval. Starší přerušený full ani neřízený historický běh nejsou finálním
důkazem. Durable finalizační task je
`task:c14ea9675845fe1744a3a61cc48a313a03123975bd49501e18aaee5d34d27589`.
Sémantický patch zachovává dotčené vazby a aktualizuje pouze posunutou citaci
TypeScript filesystem replay. GH CI je podle nového výslovného pokynu uživatele
volitelné; ostatní acceptance, nezávislé review a dependency merge zůstávají
povinné. Tento checkpoint sám nemerguje W03 ani neprohlašuje celý S06 za hotový.
