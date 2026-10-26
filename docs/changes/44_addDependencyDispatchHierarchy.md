# Ordered dependency hierarchy pro konzervativní dispatch

T003-S04-W04, T003-S04-W04-AC01–AC04; nadřazené T003-AC04 zůstává PARTIAL.
Baseline `eff0d3d5d7620b017fe42a65a54f672af8068667` obsahuje dependency realms
S03-W05 a skutečný K2 backend S04-W01. Závislosti byly ověřeny před implementací.

## Problém a změny

Původní skutečný JDK21 regression sestavil API/base a dva implementation JARy v
odlišných realms. Javac správně určil declared API target, ale kandidáti byli
prázdní: ASM CHA procházela pouze explicitní application bytecode roots.

Nový metadata-only index čte ordered selected classpath JARů/adresářů, respektuje
first-match shadow a zachovává explicitní nebo stávající artifact-hash realms.
Stejná candidate enrichment cesta zpracuje ASM virtual/interface instructions a
compiler-proven Javac/K1/K2 call expressions. Candidate proof nese algoritmus,
ordered artifact vstupy a důvod neúplnosti; declared target zůstává oddělen.
Compiler source declaration má přednost před stejnojmenným compiled výstupem.
K2 source owner bez type-hierarchy proof nepřebírá starou compiled subtype vazbu.
Fyzický static classfile lookup tím není potlačen; skutečný Kotlin file-facade
regression ověřuje source+compiled target v K1 i K2.

Reference a invokedynamic creation nejsou provedení; static/private/final/super
calls nedostávají virtuální enrichment. Index nic nedefinuje ani neinicializuje,
nespouští build/aplikaci a nezvyšuje availability. Partial hierarchy nezakládá
closed-world závěr. Missing parent, corrupt class/archive, duplicate/shadow,
truncation a unsupported multi-release JAR mají konkrétní diagnostiku. MR
version-only owner rezervuje shadow pořadí. Nečitelný archive/truncated universe
potlačí domnělé kandidáty. Limity: 10000 classes, 100000 entries (včetně ne-class
filesystem entries), 16 MiB/class, souhrnně 128 MiB class bytes a 256 visited types
na hierarchy lookup.

## Kompatibilita a příklad

Worker protocol zůstává v1; dispatch provenance pole i nový capability marker jsou aditivní, původní application CHA marker zůstává. Graph/store
v1/v2/v3 a staré classpath vstupy zůstávají čitelné. Existující callgraph odděluje
DECLARED_TARGET a DISPATCH_CANDIDATE a vyřazuje reference creation z execution
adjacency. Např. `Api.run` z API JAR zůstává declared target, `A.run` a `B.run`
v odlišných repo realms jsou pouze možné implementace.

Po explicitním content-bound build/importu:
`kgmaker inspect code --root project --kotlin-backend k2 --kotlin-version 2.1.10`.
Navigace kandidátů je explicitní přes
`kgmaker callgraph callees --symbol SYMBOL --include-dispatch-candidates`.

## Ověření

- Baseline actual regression: 1 FAIL, očekávaní dva kandidáti proti prázdnému listu.
- Finální skutečné rebuildy K1/K2 PASS: `workers/jvm/build.py --kotlin-home /workspace/tools/kotlinc --maven-repository /workspace/tools/m2 --java-home /workspace/tools/jdk-21.0.6+7`; K2 navíc `--backend k2 --analysis-api-home /workspace/tools/k2-verified`. Časy 22.10 s / 19.81 s.
- Finální focused: `python -m pytest -q tests/test_dependency_dispatch.py -k 'static_facade or invalid_input_timeout or package_private_declaration or k2_source_owner or qualified_interface_super'` — 6 PASS, 17 deselected, 40.49 s.
- Předchozí full: 398 PASS / 9 SKIP / 1 nefinální test-assertion FAIL (`TIMEOUT` místo existujícího `TIMED_OUT`); assertion opraven. Samostatný skutečný Kotlin facade probe doložil fyzický static lookup regression a vedl ke konkrétní opravě a dvěma novým actual testům.
- Finální full `python -m pytest -q -rs` pod sdíleným `flock /workspace/kgmaker-heavy-tests.lock`: **401 PASS / 9 SKIP, 327.54 s**. Všech 23 W04 actual testů proběhlo. Skips jsou nepřipravené volitelné Maven/Gradle/exporter brány mimo W04; nejde o worker/K2 SKIP.
- `KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1`, `PYTHONPATH=src`, vlastní workers home a explicitní JDK21/Kotlin2.1.10 PATH byly nastaveny pro focused i full. Source/test bytes se mezi finálními rebuildy a těmito běhy neměnily.
- Scoped `semantic update --base eff0d3d5d7620b017fe42a65a54f672af8068667`, apply a validate PASS: zachovány všechny 4 manuální concepts a 8 relationships, bez nových domnělých vazeb. Citace README134/136, architecture15/19/22/140/143 a semantic.py442/102 byly přečteny proti skutečnému obsahu.
- `kgmaker scan`, `kgmaker check`, `python -m compileall -q src tests/test_dependency_dispatch.py` a `git diff --check` PASS.
- Implementační paměť používá `kgmaker memory capture --base eff0d3d5d7620b017fe42a65a54f672af8068667 --validation focused=passed --validation full-pytest=passed --validation jvm-k1=passed --validation jvm-k2=passed --validation semantic=passed`; stávající immutable episodes se zachovávají. Po capture následuje finální CLI scan/check.

Příkazy používají `PYTHONPATH=src`, vlastní
`KGMAKER_WORKERS_HOME=/workspace/dependency-dispatch/workers`, Temurin21.0.6+7,
Kotlin2.1.10, Jackson2.18.2 a explicitně připravenou pinned K2 Analysis API distribuci.
Mandatory compiler CI zahrnuje `tests/test_dependency_dispatch.py` a explicitní pinned Kotlin `bin` na PATH pro skutečný facade compilation test.
Finální runtime SHA-256: K1 `46f818faa5ce8282d5b77a238e26f128bc0f88de718095e1a05b933d85910624`, K2 `9d70e45d3d40f39ed852e1ddab56a14beab6c041c3d425a55361582635a8c0ab`.

## Zbývající hranice

Open-world runtime instantiations/reflection zůstávají neznámé a
`dispatch_complete=false`. Package-private override access a multi-release
hierarchy jsou konzervativní explicitní hranice. K2 širší source/type/CFG,
property/operator/local/lambda semantics a generated-body source mapping nejsou
tímto work package dokončeny. Neproběhl externí push ani PR; publikaci řídí parent.
