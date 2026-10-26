# Ordered dependency hierarchy pro konzervativní dispatch

T003-S04-W04, T003-S04-W04-AC01–AC04; nadřazené T003-AC04 a S04 zůstávají PARTIAL.
Baseline `eff0d3d5d7620b017fe42a65a54f672af8068667` obsahuje ověřené dependency
realms S03-W05 a skutečný K2 backend S04-W01.

## Problém a skutečné změny

Původní actual JDK21 regression sestavil API/base a dva implementation JARy v
odlišných realms. Javac určil declared API target, ale kandidáti byli prázdní:
ASM CHA procházela pouze explicitní application bytecode roots.

Metadata-only index nyní čte ordered selected classpath JARů/adresářů, respektuje
first-match shadow a explicitní i stávající artifact-hash realms. Stejný dispatch
výpočet obsluhuje ASM virtual/interface instructions a compiler-proven Javac/K1/K2
call expressions. Candidate proof nese algoritmus, ordered artifact vstupy a důvod
neúplnosti; declared target zůstává oddělen.

Candidate **class** musí být subtype erased receiveru i owneru skutečného declared
targetu. Source type-variable/intersection receiver nemá úplné upper-bound proof,
proto nedostává kandidáty a zachovává declared target s konkrétní compiler
diagnostikou. Inherited body může
zůstat na Parent, který sám tyto dva vztahy nesplňuje. Cache klíč je tuple
receiver/declared-contract/name/descriptor. Unresolved bytecode target vrací
stávající lokalizovanou diagnostiku a PARTIAL, nikoli chybu null lookupu.

Compiler source declaration má přednost v source hierarchy view; physical classfile
lookup má samostatný view i cache a nesmí přebindovat foreign artifact na lokální
stejnojmenný source. Skutečné JDK platform resources mají parent-first přednost
před dependency metadata a zachovávají toolchain realm. `module-info.class` není
candidate class. Compiler-proven `jvm_static` konflikt stejného canonical symbolu
vrací `SOURCE_BINARY_ABI_CONFLICT`, unresolved/PARTIAL a generated body bez
nekompatibilního source locator/mapping. Nevzniká alternativní ID katalog.
K2 source owner bez type-hierarchy proof nepřebírá starou compiled subtype vazbu;
fyzický static classfile lookup zůstává zachovaný. Reference/invokedynamic creation
nejsou execution; static/private/final/super calls nedostávají virtuální enrichment.
Index nedefinuje ani neinicializuje classes, nespouští build/aplikaci a nezvyšuje
availability. Missing parent, corrupt class/archive, duplicate/shadow, truncation
a unsupported multi-release candidate enumeration mají konkrétní diagnostiku.
Physical lookup čte bounded runtime-effective JarFile metadata včetně version-only
owners, pinned kotlin-stdlib ABI se zachová; pozdější plain JAR nesmí nahradit
první selected MR class. Nečitelný archive/truncated universe potlačí domnělé kandidáty.

Limity: 10000 classes, 100000 entries včetně ne-class filesystem entries,
16 MiB/class, souhrnně 128 MiB class bytes a 256 visited types na hierarchy lookup.

## Kompatibilita a příklad

Worker protocol zůstává v1; provenance pole a nový capability marker jsou aditivní,
původní application CHA marker zůstává. Graph/store v1/v2/v3 a staré classpath
vstupy zůstávají čitelné. Callgraph odděluje DECLARED_TARGET a DISPATCH_CANDIDATE
a vyřazuje reference creation z execution adjacency. Např. Api.run zůstává
declared target, A.run a B.run v odlišných repo realms jsou možné implementace.

Po explicitním content-bound build/importu:
`kgmaker inspect code --root project --kotlin-backend k2 --kotlin-version 2.1.10`.
Navigace kandidátů je explicitní přes
`kgmaker callgraph callees --symbol SYMBOL --include-dispatch-candidates`.

## Ověření finálního zdroje

Příkazy používají `PYTHONPATH=src`, vlastní
`KGMAKER_WORKERS_HOME=/workspace/dependency-dispatch/workers`, Temurin21.0.6+7,
Kotlin2.1.10, Jackson2.18.2 a připravenou pinned K2 Analysis API distribuci.
Pro focused/full byly nastaveny `KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1`
a PATH obsahoval vlastní JDK21 i Kotlin2.1.10 bin. Finální cyklus běží pod
`flock /workspace/kgmaker-heavy-tests.lock`; source/test/runtime bytes se od finálních
rebuildů během focused/full nemění.

- Rebuild K1 PASS, 19.52 s: `python workers/jvm/build.py --kotlin-home /workspace/tools/kotlinc --maven-repository /workspace/tools/m2 --java-home /workspace/tools/jdk-21.0.6+7`.
- Rebuild K2 PASS, 15.48 s: stejný příkaz navíc `--backend k2 --analysis-api-home /workspace/tools/k2-verified`.
- Focused `python -m pytest -q tests/test_dependency_dispatch.py`: **40 PASS, 236.45 s**, všechny skutečné JDK/K1/K2 worker cases běžely.
- Full `python -m pytest -q -rs`: **418 PASS, 9 SKIP, 366.33 s**. Skips jsou volitelné Maven/Gradle/exporter testy bez jejich explicitního runner nastavení; žádný actual W04/K1/K2 test se nepřeskočil.

Runtime SHA-256: K1 `6cb8c8e2bd4f4f748ca31b6ae7df3d26dc67246c0150b8918bf64150dd1459a2`,
K2 `edeb7a67e73e0be90875e16de88ef4aedadca68524c761e62f26010371750a41`.
- Scoped `semantic update --base eff0d3d5d7620b017fe42a65a54f672af8068667 --note docs/changes/44_addDependencyDispatchHierarchy.md`, matching-packet apply/validate PASS; zachováno 4 manual concepts/8 edges s ověřenými citations.
- CLI `scan`/`check`, `git diff --check` PASS. Immutable memory capture nad korekcí base6cac zachovává všech 71 předchozích episodes a přidává novou implementační epizodu.

Mandatory compiler CI zahrnuje `tests/test_dependency_dispatch.py` a pinned Kotlin
bin na PATH pro skutečnou facade compilation.

## Nezávislé review a regression evidence

První feature acceptance selhala očekávaně prázdnými kandidáty. Samostatný skutečný
Kotlin file-facade probe odhalil potlačený physical static lookup; jeho opravu
ověřují K1/K2 actual compilation testy. Nezávislý review nad původním headem
`6cac8e99708d398bf58497e11b23c35cc79ab13e` našel intersection false candidate:
OnlyMarker.run neimplementuje Api. Dva actual regression testy selhaly na původním
binary (2 FAIL, 13.56 s); zároveň ověřují inherited body z ne-implementujícího
parenta a dva odlišné interface contracts se stejnou erasure/signaturou.
Parent nezávisle ověřil také obrácené pořadí obou contracts.

Další actual negative s chybějícím declared API doložil NullPointerException při
TreeMap.get(null) (1 FAIL, 3.11 s); minimální guard zachovává existující unresolved
site a BYTECODE_UNRESOLVED_TARGET/PARTIAL. Finální focused tyto případy pokrývá.
Předchozí full 401/403/404 PASS s 9 SKIP patří předchozím runtime verzím.
Další actual probes doložily ztracený třetí/druhý generic bound, foreign realm
source/static alias a dependency shadow skutečného JDK Object. Jejich opravy
ověřil focused 33 PASS. Tehdejší full byl po potvrzení static-ABI/MR kompatibility
problému bezpečně přerušen (165 PASS, 2 SKIP, KeyboardInterrupt), nikoli vydáván
za PASS. Sedm nových actual ABI/MR regressions na předchozím binary selhalo
(7 FAIL, 33 deselected, 50.45 s); finální evidence je uvedena výše.

## Zbývající hranice

Open-world runtime instantiations/reflection zůstávají neznámé,
`dispatch_complete=false`. Package-private override access a multi-release
hierarchy jsou explicitní konzervativní hranice. K2 širší source/type/CFG,
property/operator/local/lambda semantics a generated-body source mapping nejsou
tímto work package dokončeny. Neproběhl externí push ani PR; publikaci řídí parent.
