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

## Integrace aktuální main33dc

Lokální merge zachovává historii main `33dc239a6d2eca2f42364a7b314aeb377e4b441a`
a core guard commit `cb86e66b3024d59f440fe017f332af2e02c10998`.
Portable Windows builders/transport, TypeScript, XLSX, T008 a povinné CI gates
včetně `test_mandatory_worker_ci.py` zůstávají zachované. JavaFrontend skládá
Spring selector hooks s dispatch hierarchy metadata; stejné compiler `jvm_static`
flags z W02 jsou sjednocené bez duplicitních imports.

Bytecode skládá W04 physical/source lookup s W02 `SourceMapping`, ambiguous-owner
hook a bytecode-only call-site locator evidence. Raw incompatible target má
`SOURCE_BINARY_ABI_CONFLICT`; samostatná declaration mapping boundary zachovává
W02 `SOURCE_METHOD_ABI_MISMATCH`. Jedna W04 assertion byla upravena na tento
přesnější mapping kontrakt; nevzniká falešný target ani locator. DependencyHierarchy,
State a K2 source zůstávají byte-identické s core guard commitem.

Oba merged-source rebuildy K1/K2 PASS (19.19 s / 17.57 s). První composition běh
byl po 26 PASS bezpečně přerušen pro doplnění explicitního
`KGMAKER_TEST_MAVEN_REPOSITORY=/workspace/tools/m2`; nebyl vydáván za kompletní PASS.
Finální composition `python -m pytest -q tests/test_worker_protocol.py tests/test_mandatory_worker_ci.py tests/test_default_body_mapping.py tests/test_spring_imports.py tests/test_spring_imports_context.py`: **86 PASS, 297.50 s**, žádné SKIP.
Selected W04 `python -m pytest -q tests/test_dependency_dispatch.py -k 'source_interface_call or intersection or missing_declared_api or generic_receiver or foreign_bytecode or shadow_actual_toolchain or staticness_conflict or pinned_stdlib or effective_class_lookup'`: **18 PASS, 22 deselected, 102.48 s**.
Přesný pinned env a příkazy jsou v `/tmp/dispatch-integrated-check-validate.py`; vlastní worker home a `KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1` zůstávají explicitní.
Scoped semantic update/apply/validate, CLI scan/check a diff check PASS. Nová integrační paměť zachovává immutable union107 episodes a přidává episode108.
Full418/9 se neopakuje pouze kvůli integraci; vztahuje se výslovně na core zdroj.
Main semantic facts6/15 a všech105 immutable episodes jsou zachované; sjednocená
historie obsahuje107 episodes před novou integrační epizodou.

Merged runtime SHA-256: K1 `59b63284454ad062679e3564a5d7378fc0ca238957ff8803eff8f218512622af`,
K2 `7da400af535820a5d4271a3509deb7f1e171ea556910d3aa500901d0ace69ca8`.

### Finální scope-only canonical collision guard

Nezávislé actual review merged runtime nalezlo ještě scope-only collision:
physical dependency realm test a lokální source production mají shodný
repo/module/source_set prefix i ABI; scope není součástí canonical ID. Nový actual
regression na předchozím runtime selhal (1 FAIL / 4 valid-realm PASS / 36 deselected,
46.98 s). Raw physical target nyní před canonical bindingem ověřuje všechna čtyři
realm pole repo_id/module/source_set/scope proti source contextu. Mismatch vrací
`SOURCE_BINARY_REALM_CONFLICT`, declared_target=None, UNRESOLVED/PARTIAL; source
declaration ani identity se nepřepisují. W02 mapping nadále používá vlastní exact
realm proof. Platný shodný realm a ABI zůstává pozitivní.

Protože tento guard mění runtime, předchozí core418/9 a integrační86+18 jsou
historická evidence před guardem. Finální oba rebuildy, scope/ABI focus,
protocol/CI a **nový celý pytest** běží pouze jednou pod stejným heavy-test lockem
přes `/tmp/dispatch-realm-final-validate.py`. Oba rebuildy PASS (K1 30.10 s / K2 12.95 s);
actual scope/ABI/foreign focus **6 PASS, 35 deselected, 39.63 s**, protocol/mandatoryCI
**26 PASS, 2.62 s**. Finální current-source full **575 PASS, 10 SKIP, 664.80 s**. Devět
SKIP je volitelné Maven/Gradle/exporter nastavení uvedené výše; desátý je skutečný
non-admin Windows CI-only gate. Žádný actual W04/K1/K2/mapping/Spring case se
nepřeskočil. Zdroj a oba runtimes se během finálního cyklu neměnily.
Nezávislý architect zopakoval původní scope-only probe na stejném finálním K1
runtime: VIRTUAL target=None, UNRESOLVED; source canonical se nepřepsal.

Finální realm-guard runtime SHA-256: K1 `e44e3dac04ba28cd8899fed0ae183f5739c4311911b1ae656e6d1db26b64e15e`,
K2 `5dc33b9d5a635b04bccebb024f8473571fc59cbc3383af8dbb9034e2a9440c66`.

Závěrečné semantic update/apply/validate zachovává všech6 manual concepts/15 edges
a ověřené citations. Immutable historie main105 + core72 =107 episodes, předchozí
integrační episode108 zůstává historická; finální guard capture přidává episode109.
CLI scan/check a git diff --check PASS. Externí mandatory CI je blokováno GitHub
Actions billing/spending limitem; tento lokální výsledek nenahrazuje sedm povinných
remote gates ani skutečný Windows běh. Publikace může být Draft, bez merge.

## Integrace aktuálního main po obnovení Actions

Main `5430388a282f19f6c9637319c12a1731ae6d0674` obsahuje T009 a merged
T003-S08-W02. JVM worker sources a celý dispatch test modul zůstávají byte-identické
s předchozím reviewovaným `89e50cf`; Python bridge doplňuje pouze původní tři
metadata dispatch pole do aktuálního inspection. CI zachovává aktuální dependency
pins/Windows opravu a společně spouští dispatch i selected-tsconfig freshness.

Cílená integrační validace: **120 PASS, žádný SKIP, 330.63 s** nad
`tests/test_dependency_dispatch.py`, T005, T008, T009 a mandatory CI guards.
Log/XML: `/workspace/dispatch-main543-validation/focus.log` a `focus.xml`.
Původní full **575 PASS / 10 SKIP** stále dokládá nezměněné feature source;
pro čistou integraci se další lokální full neopakoval. Před merge je nutný review
přesného nového head/base a všech sedm aktuálních remote CI kontrol.

Sémantika zachovává přesný main prefix 118 immutable episodes a všechny čtyři
unikátní původní child captures. Žádný původní capture objekt se neupravuje.
Generované grafy se obnovují výhradně CLI; žádný runtime/classpath důkaz není
povýšen na pozorované spuštění aplikace.
