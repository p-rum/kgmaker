# Field a explicitní mapper flow

T003-S07-W03 přidává `field-mapping-1`: omezenou projekci existujícího Javac
source IR do stejného grafu. `reads_value` a `writes_value` mají vlastní source
occurrence; `maps_to` spojuje compiler identity field deklarací při doloženém
přímém přiřazení. Nejde o identitu konkrétních objektů ani hodnot za běhu.
[Změna a ověření](changes/124_fieldAndMappingFlow.md).

| Varianta | Podpora | Hranice |
|---|---|---|
| Java field read/write | Přímý compiler binding, source SHA/range, owner identity z Javac | Pole bez zachycené source deklarace, array/compound assignment a reflexe UNKNOWN |
| Ruční DTO/entity mapper | Přímé field assignment; lokální alias; getter → identity helper → setter | Jen statické/private/final metody s přímým source tělem a compiler `DIRECT` argument bindingem; vararg packing UNKNOWN; otevřený dispatch UNKNOWN |
| Generated mapper | Skutečně zachycený Java source používá stejná pravidla; fixture generuje MapStruct 1.6.3 | Anotace, jméno property ani generated filename samy mapping nedokládají; procesor se při inspekci nespouští |
| Větvení mapperu | Přímé přiřazení v rameni nese source branch guard; rozdílné lokální definice se neslučují na jistou hodnotu | Helper summary obsahuje jen straight-line tělo; smyčky, try/catch, rekurze a obchodní transformace UNKNOWN |
| Kotlin/K2/TypeScript/ASM | Dosavadní SOURCE_ONLY, argument a return evidence zůstává čitelná | W03 pro tyto backendy nedodává nové field mapping proofs |

Getter a setter se identifikují podle compiler identity a skutečného těla, nikoli
prefixů `get`/`set`. Source helpers mají nejvýše 16 vnoření; projekce má limit
50 000 expression kroků, 64 vnoření struktury a 256 provenance lokátorů. Překročení vrací lokalizovanou
`FIELD_MAPPING_LIMIT` a neúplnou evidence. Neznámé transformace mají
`FIELD_MAPPING_CALL_BODY_UNKNOWN`, `FIELD_MAPPING_EXPRESSION_UNKNOWN` nebo
`FIELD_MAPPING_VALUE_UNKNOWN`; nepodporované řízení toku
`FIELD_MAPPING_CONTROL_FLOW_UNKNOWN`. Diagnostika je omezena na metody
s field přístupy a jejich source callers.

Příklady po explicitní inspekci:

```bash
kgmaker inspect code --root app --classpath /absolute/path/dependency.jar
kgmaker query 'publicName' --root app
kgmaker impact --root app --entity '<compiler-field-id-from-query>' --include-data-flow --format json
```

Impact JSON obsahuje `field_mapping_bindings` pro dotčené endpoints. Evidence
nese `field_mapping_version: 1`, zdrojové lokátory v `provenance`, source guards,
`owner_method`, `transformation: DIRECT_ASSIGNMENT` u mapování a
`identity_scope: FIELD_DECLARATION`. `business_equivalence` a `availability`
zůstávají **UNKNOWN**, `runtime_execution` **NOT_OBSERVED**. Řetězec může být
statickou závislostí napříč metodami; nedokládá pořadí jejich spuštění, aliasy
objektů, bezpečnost konverzí ani business ekvivalenci.

Scan, hook a impact worker ani annotation processor nespouštějí. Explicitní
inspekce validuje existující return IR před projekcí; source/classpath/worker
freshness a atomická publikace zůstávají stejné. `field_flow_rule_version` je
aditivní capture metadata v context ID; rozdílná zaznamenaná verze je STALE.
Graph/store v1/v2/v3 a worker protocol v1 se nemění. Starší grafy bez markeru
zůstávají čitelné a nevytvářejí novou W03 evidence. Workspace kvalifikuje i
vnořené metody, call sites a source lokátory. `domain.py` zůstává beze změny:
SOURCE_ONLY JPA názvy se neslučují s compiler field identitou podle podobnosti.

Reprodukovatelný skutečný fixture build a inspekci provede cílený test:

```bash
PATH="$JAVA_HOME/bin:$PATH" KGMAKER_REQUIRE_WORKERS=1 python -m pytest -q tests/test_field_mapping_flow.py
```

Vyžaduje JDK21, připravený JVM worker (`KGMAKER_WORKERS_HOME`) a existující
MapStruct API/processor 1.6.3 v lokálním Maven repository. Alternativní repository
určí `KGMAKER_MAPSTRUCT_REPOSITORY`. Test explicitně spustí `javac` s procesorem
v dočasném adresáři a potom veřejné `inspect_jvm`; žádnou závislost nestahuje.
Chybějící toolchain je při required režimu FAIL, jinak SKIP. Nespouští aplikaci.
