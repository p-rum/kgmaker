# Bounded Spring registrar a FactoryBean deklarace

Datum: 2026-10-26. Task [T003-S05-W02](../tasks/T003-S05-02-springRegistrarsFactories.md),
AC01–AC04; nadřazené S05/AC05 zůstává PARTIAL. Číslo47 bylo rezervováno parentem.
Závislost W01 je skutečně merged v `4113a7975451a8313321fd521252485c959908e3`.
Před finální validací integrován skutečný main
`33dc239a6d2eca2f42364a7b314aeb377e4b441a`, včetně inventory, mandatory CI a
source/bytecode mapping. Nejde o dokončení obecného Spring runtime.

## Problém a skutečné změny

Actual Javac/Spring6.2.2 probe nad oběma distribucemi ukázal chybějící literal
registrace a záměnu FactoryBean objektu s produktem. `FactoryBean<Product>` měl
v běžných bean types dokonce `Product>`, bez produktové provenance/boundary.
Regresní suite před implementací: **6 FAIL, 4 PASS v32.10 s**, oba backendy.

`RegistrationFacts.java` přidává pouze compiler declaration facts:

- Přesná/transitivní `ImportBeanDefinitionRegistrar` identita, effective owner
  veřejné dvouparametrové metody a informace o custom tříparametrovém overloadu.
- Nejvýše128 přímých expression statements skutečného
  `BeanDefinitionRegistry.registerBeanDefinition` na přesném registry parametru,
  literal bean name do512 znaků a přesný `RootBeanDefinition(Type.class)`.
  Conditional/control flow, alias/helper, jiný receiver/constructor či překročený
  limit je explicitně UNSUPPORTED. Fake registry stejného method name neprojde.
- Přesná `FactoryBean` hierarchie včetně generic substitution, effective source
  metody getObject/getObjectType a jediný literal zero-argument constructor/class
  return. Generický typ a oba return typy se musí přesně shodovat; source target
  musí být indexovaný. Těla, konstruktory ani class initializers se neprovádějí.

`spring_beans.py` validuje schema1 facts, jejich shape a selected context.
Framework reuse stávající `spring_bean`, condition/reachability, evidence a
injection/store vrstvy; přidává `spring_registrar`, `uses_bean_registrar`,
`registers_bean` a `produces_bean`. Configuration view tyto vazby zachovává.
Registrar bean condition dědí od importující konfigurace; RootBeanDefinition
zde samo nevyhodnocuje target @Profile. Unknown custom condition či overload
nevyrobí ACTIVE product. Factory objekt `&name` a produkt `name` jsou odlišné
deklarace. Abstract factory objekt/produkt zůstává UNKNOWN. Kompilátorově
rozlišený Spring FactoryBean injection nesmí vybrat stejnojmenný fake interface.

## Kontrakty, bezpečné hranice a kompatibilita

Worker protocol zůstává1; aditivní fields `bean_registrar`, `bean_registrations`,
`factory_bean`, `factory_bean_return`, `factory_return` mají vlastní schema1.
Legacy fakta a graph/store v1/v2/v3 zůstávají čitelné; bez nového důkazu se literal
registrace/produkt nepromuje. Invalidní facts, strict error a timeout ponechávají
poslední validní generaci. Cross-context symbol odmítne už společný model validator.

Nový Spring rule version je `annotation-source-v5` pouze pro JVM. TypeScript a
React metadata/key zůstávají současnému main byte-identické; pre-existing React
metadata overwrite se tímto taskem nemění. Evidence je FRAMEWORK_DERIVED,
obsahově/source-symbol/context-bound; nevzniká execution ani runtime/data proof.
Audit statického registered beanu zůstává UNKNOWN, žádný CONFIRMED_MISSING.

Reálná fixture používá stávajících šest SHA/license-bound Spring6.2.2 API JARů
z `fixtures/spring-imports/pom.xml` a locku. Žádná nová dependency ani implicitní
instalace/fetch nevzniká. Mandatory CI bootstrap z W01 zůstává a compiler job
navíc spouští `tests/test_spring_registrations.py`; missing API/worker je FAIL
pod mandatory flags. Spring JARy nejsou redistribuované v worker wheelu.

Nepodporováno: obecné BeanDefinition builders/properties/suppliers, runtime
post-processors, custom registrars/factory evaluace, Kotlin registration facts,
XML a Spring/Boot factories metadata discovery. `spring.factories` a Boot
`.imports` se nepovyšují na beans; jejich budoucí čtení musí nejprve zavést
source-set-bound freshness. Nejde o aktuální podporu těchto formátů.

## Provedené kontroly a průběh

- Projektový kgmaker skill, status/scan/query, přijatý read-only architecture
  brief, ověření normativních dependencies a memory recall: provedeny. Durable
  analyze/plan/implementation packet je zapsaný.
- První skutečné integrované JVM/TS-context případy: **12 PASS v18.90 s**.
- Rozšířená actual sada: **40 PASS, 2 FAIL v88.08 s**. Dvě chyby byly očekáváním
  AnalysisError v testu cross-context symbolu; společný model správně odmítl symbol
  dříve přes ValueError. Test nyní ověřuje tento existující kontrakt i nulový zápis.
- K1/K2 byly explicitně rebuildnuté s vlastními source facts, JDK21.0.6+7,
  Kotlin2.1.10/AnalysisAPI2.1.10 a Jackson2.18.2, pinned/offline vstupy.
  Po integraci main33dc se znovu sestavují i s jeho mapping additions.

Finální relevantní/full výsledky, semantic update/apply/validate, memory capture,
scan/check a diff check jsou součástí předání. Žádný skutečný runtime PASS se
neodvozuje z fixture nebo přítomnosti compileru. GitHub Actions billing/quota
je externí překážka nového CI; lokální validace ji nenahrazuje. Publikace má být
Draft a merge/CI retry zůstává pozastaven dle výslovného uživatelského pokynu.

## Použití

```bash
kgmaker inspect code --root project --manifest /approved/build-manifest.json \
  --context BUILD_CONTEXT_ID --kotlin-backend k2 --worker-home /approved/workers
kgmaker query --root project --context ANALYSIS_CONTEXT_ID registeredProduct
```

Nutný je explicitní Spring/API classpath a profile/scan scope; bez důkazu jsou
conditions UNKNOWN. Scan/hook/query/feature/data-check nic implicitně nesestaví,
neinstaluje ani nespustí. Bean ACTIVE zde označuje statickou condition deklarace,
nikoli instanci, úspěšný custom constructor nebo dostupná produkční data.
