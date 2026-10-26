# T003-S04-W02 — Doložené mapování defaultních těl a bridge deklarací

## Problém

Bytecode vrstva měla pouze owner/name/descriptor spojení se source symbolem.
Kotlin DefaultImpls a Java generic bridge s odlišným descriptor neměly doloženou
vazbu; chyběla lokalizovaná bytecode-only diagnostika. Zadání:
`docs/tasks/T003-S04-02-defaultBodySourceMapping.md`, AC01–AC04, nadřazené T003-AC04.

## Změny a kontrakt

`SourceMapping` odděluje mapování deklarací od ASM dispatch/CHA. Přesná Java/Kotlin
source deklarace zůstává owner/name/descriptor. Kotlin DefaultImpls navíc vyžaduje
Kotlin Metadata kind3/kind1, unikátní InnerClasses outer interface, static receiver
téhož interface, shodný repo/module/source-set/scope realm helperu i interface a skutečně deklarovanou interface signaturu. Java bridge vyžaduje
ACC_BRIDGE+ACC_SYNTHETIC, jednoduché load/cast/single same-owner invoke/return tělo
bez handlers a nesyntetickou cílovou deklaraci; podporuje value i void return.
Samotný název/suffix, SourceFile nebo debug line nic nedokazuje. Při existující
DUPLICATE_BYTECODE_CLASS diagnostice se mapping dotčeného owneru odmítne;
první physical class se neprohlásí za jednoznačnou source vazbu.

Bytecode IDs zůstávají oddělené. Generated metody mají skutečný artifact realm
scope a přímé path/range prázdné; source locator je pouze v mapping metadata.
Přesná source candidate kontrola porovnává celé repo/module/source_set/scope
s vybraným request contextem, nejen identity prefix. `maps_to_source` nese source hash/range a bytecode
artifact hashes z vybraného contextu. Metadata a call sites obsahují mapping IDs,
reason a declaration locator; generated instrukce nemají přidělený source call
path/range. Chybějící/neshodná source signatura nebo nepodporovaný generated tvar
má `BYTECODE_ONLY_SOURCE_MAPPING` s method ID/context/reason, nikoli domyšlený LOC.
Každý generated call site má také explicitní `BYTECODE_ONLY_CALL_SITE` diagnostiku
s ID a důvodem: declaration mapping nedokazuje source call-expression LOC.
Call evidence zůstává BYTECODE a přenáší content-bound artifact hashes.
Source-only/scan nespouští worker/build. Žádný nový store ani CLI není přidán.

## Kompatibilita

Aditivní worker-v1 metadata/facts, původní graph v1/v2/v3 a identity se nemění.
Existující source deklarace nejsou přepsány. Instalace workeru zůstává explicitní;
změněná distribuce má nový content hash. Migrace uloženého formátu není potřeba.

## Příklad

```bash
kgmaker inspect code --root project --build-id BUILD_ID --context CONTEXT_ID
# Bytecode roots vyberte až s explicitním execution-bound build-import manifestem.
```

V graphu sledujte `maps_to_source` a evidence `DECLARATION_MAPPING`. Tato hrana
není call/dispatch ani runtime observation. `source_mapping_range` ukazuje na
source deklaraci, ne na konkrétní vygenerovanou instrukci.

## Ověření

- Počáteční skutečná K1 fixture selhala očekávaně: generic bridge měl
  `NO_SOURCE_MAPPING` místo `VERIFIED_BRIDGE_DELEGATE`.
- První skutečná K1/K2 debug/no-debug/missing/mismatched-source matice:
  **12 PASS / 169.69 s**. Následně rozšířena o void bridge, Kotlin JVM-default=all,
  graph evidence roundtrip a kompletní porovnání vstupních/store bytes.
- Rozšířená matice (void/JVM-default=all/graph/no-mutation): **12 PASS / 267.65 s**.
- Netriviální bridge body se druhým invoke: **4 PASS / 161.79 s**.
- Před realm guardem plná sada **390 PASS, 9 SKIP / 828.49 s**. Následný
  skutečný mixed-realm test selhal: foreign DefaultImpls si nárokoval local source;
  doplněna kontrola shodné realm identity. Tato starší plná sada se nevydává za
  finální ověření guardu.
- Realm guard: **4 PASS / 113.07 s**.
- Samostatná ochrana helper scope: **8 PASS / 91.03 s**. Následný whole-artifact
  test-scope případ ještě selhal (**39.02 s**), protože source identity neobsahuje
  scope. Finální mapper porovnává čtyřici identity i u přímých/bridge candidates;
  generated symbol nezdědí source path/range/scope z jiné evidence.
- Před ABI guardem: focused scope/duplicate guards **16 PASS / 66.33 s**.
- Před ABI guardem plná sada se všemi **32** mapping případy: **410 PASS, 9 SKIP / 258.72 s**.
  Přesný běh z tohoto checkoutu:

  ```bash
  flock /workspace/kgmaker-heavy-tests.lock env \
    PATH=/workspace/tools/jdk-21.0.6+7/bin:/workspace/tools/kotlinc/bin:$PATH \
    JAVA_HOME=/workspace/tools/jdk-21.0.6+7 PYTHONPATH=src \
    KGMAKER_WORKERS_HOME=/workspace/default-body/workers \
    KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 \
    /workspace/kgmaker-venv/bin/python -m pytest -q -rs
  ```

  Focused používá stejný explicitní worker home/JDK/Kotlin a
  `pytest -q tests/test_default_body_mapping.py -k 'foreign or test_scope_bytecode or duplicate'`.
  SKIP: trusted Maven exporter/Maven a druhý JDK nebyly pro tento běh nakonfigurovány;
  skutečné Maven/Gradle wheel exporty, Gradle8.13 variants/included builds a Kotlin2.2.20
  Gradle cache proto zůstávají mimo tento důkaz. Nejsou vykazovány jako PASS.
- K1 i K2 worker byl zkopírován z připravených pinned dependencies a znovu sestaven
  explicitním `workers/jvm/build.py` nad tímto zdrojem. Golden fixture Java/Kotlin
  kompilace se provedly skutečně; existující mixed/TS fixture assets byly připravené.
  Žádný nový Maven/Gradle projektový build se tímto záznamem neprohlašuje za provedený.
- `semantic update --base eff0d3d5d7620b017fe42a65a54f672af8068667 --note docs/changes/46_mapDefaultBodySources.md`,
  scoped `semantic apply`, `semantic validate`, generovaný `scan`, `check` a
  `git diff --check` — **PASS**. Přidán 1 koncept/3 doložené vztahy; původní
  4 koncepty/8 vztahů z main zachovány, 70 původních epizod tvoří přesný prefix.
- `memory recall` před implementací — **PASS**. `memory capture --base eff0d3d5`
  ukládá ověřené labely focused16/full410/actualK1K2/semantic a 9 optional
  toolchain skips jako oddělený výsledek; epizoda se připojuje před finálním scan.
- Vzdálené CI a publikace tohoto W02 nebyly provedeny: tato dodávka končí
  lokálním commitem pro nezávislé review, bez self-review/merge.

Matice AC01: `test_real_default_and_bridge_mapping`; AC02: graph roundtrip a
`test_k2_backend.py::test_existing_graph_loader_is_unchanged`; AC03: `test_absent_sources_remain_bytecode_only`
a `test_wrong_source_signature_never_maps_generated_body`, navíc
`test_nontrivial_bridge_body_stays_bytecode_only` odmítá původní compiler bridge
s vloženým druhým invoke; `test_foreign_default_impls_realm_cannot_claim_local_source`
kontroluje cizí realm/scope; `test_test_scope_bytecode_never_claims_production_source`
ověřuje celý test artifact proti production source a
`test_duplicate_class_bodies_do_not_prove_source_mapping` má dvě skutečně
kompilované odlišné class bodies stejného owneru; včetně byte porovnání
celého fixture checkoutu a poslední validní store generace. AC04: tato poznámka,
capability docs a acceptance/progress inventář. Povinné compiler CI nyní obsahuje
nový test; toolchain musí být explicitní JDK21/Kotlin2.1.10 a oba workery.

## Omezení a zbývající práce

S04 zůstává PARTIAL. Nepokrýváme arbitrary/dependency bridges, default-argument
mask dispatch, coroutine state machines ani statement-level source mapping.
Golden no-debug varianta používá javac -g:none a odstranění debug atributů z
reálného Kotlin compiler output přes pinned ASM; kód a metadata zůstávají zachovány.
Není to důkaz runtime execution, dependency dispatch completeness ani podpory
libovolného produkčního projektu. Live projekt/runtime se nespouštěl.


## Static/instance ABI a integrace aktuálního main

Main `a83dbab6263eb2fe225f0da51f2f2549c0ab162e` přináší schválený Windows
portable transport, přímé Java compiler builders a všech sedm CI gates. Tyto
změny se zachovávají; compiler gate nadále obsahuje skutečné W02 testy.

Dodatečný skutečný same-realm probe doložil, že shodné owner/name/descriptor
nestačí: compiled INSTANCE `A.run()I` se mapoval na aktuální STATIC source metodu.
Taková vazba nesmí být doloženým source mappingem. Nyní source metadata obsahuje
`jvm_static`: Javac čte skutečný Modifier.STATIC, K1 používá compiler
DescriptorAsmUtil.isStaticMethod s OwnerKind z descriptor containeru (Java
method descriptor má vlastní dispatch receiver proof), K2 čte vybraný light
method STATIC flag. Neznámý/synthesized/inline-value-class ABI není odhadnut z
názvu a zůstává neprokázaný.

Direct mapping vyžaduje shodu static/instance. Bridge musí doložit non-static
physical delegate i non-static source target. DefaultImpls je zvláštní doložená
transformace static helperu s interface receiverem na instance source deklaraci;
nejde o obecné obejití ABI guardu. Chybějící nebo neshodný ABI flag má konkrétní
SOURCE_METHOD_ABI_UNAVAILABLE / SOURCE_METHOD_ABI_MISMATCH bytecode-only důvod.
Generated method také nese vlastní ASM jvm_static flag; source canonical
metadata a původní IDs se nepřepisují.

`test_same_realm_static_instance_abi_changes_never_map` ověřuje oba směry změny
na Java/Kotlin source pod K1/K2 s debug/no-debug class files. Positive matice
obsahuje top-level static a @JvmStatic object a zachovaný DefaultImpls transform;
file initializer bez source method ABI proof nepřevezme odhadovaný flag.
Focused static/instance + positives: **8 PASS / 45.94 s**. Finální plná sada
na integrovaném main se všemi **36** skutečnými W02 případy: **425 PASS,
10 SKIP / 299.89 s**. Běžela pod společným flock se stejným explicitním
worker home/JDK/Kotlin a REQUIRE_WORKERS=1/REQUIRE_K2=1 jako příkaz výše.
SKIP jsou 9 dříve uvedených optional exporter konfigurací a skutečný Windows
non-admin smoke, který je samostatným povinným vzdáleným gate.
Starší výše uvedené 410/9 výsledky nejsou finálním ověřením tohoto ABI guardu.


Integrační semantic update používá base `a83dbab`; hlavní 4 koncepty/8 vztahů
zůstávají zachované s aktuálními README citacemi 140/142. Vlastní koncept a
mapovací vztahy se doplňují o tři doložené compiler ABI provider vazby.
80 epizod aktuálního main tvoří přesný prefix; stará W02 epizoda zůstává beze
změny a nový capture zaznamenává ABI/full425 ověření. Vzdálené CI pro nový HEAD
nebylo lokálně spouštěno; publikaci a nezávislé review provádí parent.


## Integrace TS/XLSX main 1091330

Po lokálním ABI commitu `ac3248b` byl integrován
`1091330b67a7ff67db329ffbbb2eaba162313b3f`. Všech šest testovaných mapper/
frontend/test souborů z 425-PASS běhu zůstalo byte-identických. Aktuální main
Windows transport/builders, TS shared selector/input closure, ESRCH regression
oprava a všech sedm gates jsou zachovány; compiler job obsahuje TS i W02 testy.
Relevantní actual mapping positive, same-realm ABI a scope + provider/protocol/
JDK prerequisites: **28 PASS, 1 explicit Windows smoke SKIP /54.83 s**.
Plná425 sada se pouze kvůli této kompozici neopakovala. Semantic union zachovává
93 main epizod jako přesný prefix a oba původní W02 záznamy beze změny.


## Finální integrace Spring a source-only views

Main `4113a797` zachovává Spring SelectorFacts spolu s compiler `jvm_static`
metadata. Po rebuild vlastních K1/K2 workers prošly skutečné mapping positive,
ABI/scope negative, Spring K1/K2 a provider/protocol testy: **34 PASS,
1 explicit Windows SKIP /91.80 s**. `abiFailure` se resetuje při každém mapMethod,
aby předchozí ABI odmítnutí neoznačilo nesouvisející nenamapovanou deklaraci.
Následný views-only main `ff26a6d` nepřináší změnu JVM workerů. Zachováno je
100 main epizod jako přesný prefix a oba dosavadní W02 záznamy. Plná ABI sada
425/10 zůstává předchozím ověřením; kvůli samotné integraci se neopakovala.

Po ff26 refresh core provider/protocol: **21 PASS /2.02 s**. Semantic validate,
scan, check a diff whitespace prošly; všech 5 main konceptů/9 vztahů je přesně
zachováno, 100 main epizod je přesný prefix celkových 103 epizod (dva původní
W02 a nový integrační capture). Výsledný graph: 317 files, 3008 nodes,
20104 relationships. Nový vzdálený CI běh je před publikací NOT_RUN.
