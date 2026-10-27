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
neznámý namespace, unsupported construct a DTD odmítnutí.

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
