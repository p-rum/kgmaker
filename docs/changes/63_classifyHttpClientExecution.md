# Oddělení HTTP request definition od execution intent

T003-S07-W06, AC01–AC04; implementovaný omezený kontrakt. Celý S07/T003 zůstává
PARTIAL. Samostatná větev `feat/t003-s07-06-http-client-execution` je nad
`c7beaec95951267796c0c21baa6079fafe5fe124`, target
`stack/t003-s07-w06-prerequisites`: explicitní merge PR35
`89e50cf4cf8edbebc4f9d08879656698c75ebd50` a PR34
`78d7968ea7408adea3ec9ce783769bb799522470`. Žádná skrytá závislost na W01.
Aktuální reviewovatelný source checkpoint je `0484a8d0a5d5c0f341c8c43a375f963ea8cc8ba0`;
finální commit mění jen validation/memory/generated documentation.

## Problém a skutečná změna

Dřívější SOURCE_ONLY HTTP reference nerozlišovala cold publisher od execution.
Před feature kódem actual Spring6.2.2/Reactor3.7.2 API RED ukázal5 attributed
calls a0 definitions; první acceptance **2 FAIL13.60s**, bez Javac errors.

JavaFrontend nyní dodává aditivní compiler literal/local-binding/capture facts
(`typed-java-literals-bindings-v1`) ve stávajícím IR. Pure `http_execution`
projection používá skutečné compiler target/receiver/origin identities, nikoli
source labels, method spelling samotné nebo confidence. Reuse Node/Edge/evidence,
store/context/workspace, bez nového paralelního katalogu či runtime flow engine.

WebClient retrieve/bodyToMono/bodyToFlux/exchangeToMono/Flux jsou cold definitions.
Closed unused local publisher je UNSUBSCRIBED_WITHIN_SCOPE; doložený same-origin
Mono block/blockOptional/subscribe/toFuture nebo Flux blockFirst/blockLast/subscribe
je jen STATIC_TRIGGER/CONDITIONAL_STATIC_TRIGGER. Každý publisher má vlastní
origin i při sdíleném request spec. RestClient retrieve sám nestačí; body/toEntity/
toBodilessEntity/exchange je imperativní terminal. Feign pouze annotated abstract
nonstatic contract + attributed call znamená FEIGN_INVOCATION_INTENT, proxy
registration UNKNOWN. Default/static/custom methods se nepovyšují na HTTP proof.

Return/store/pass/capture/reference, anonymous capture, unsupported switch,
unknown helper/operator či merged origin zůstávají UNKNOWN bez invented terminal.
Neznámá reconfiguration nezachová původní konkrétní URI. Kotlin K1/K2 bez potřebného
binding IR má explicitní HTTP_TYPED_IR_UNAVAILABLE/UNKNOWN. Integrations/data-flow
JSON a process JSON/Markdown čtou typed inventory. Consumer process zahrnuje Feign
intent přes terminal call-site caller; samotná unused deklarace execution není.

URI method/base/path jsou oddělené, bez guessed concatenation. Simple @Value/
PropertyResolver/Feign placeholder se mapuje jen při matching explicit property,
selected application.properties/profile file a SHA provenance. Plain string
placeholder, nested/default/SpEL/YAML a ambiguous/missing source jsou UNKNOWN.
Fresh scans/captures redaktují URI userinfo/query/fragment před persistencí,
včetně explicit context, SOURCE_ONLY signatures/doc summaries/heading IDs a
legacy HTTP references. Privacy pokrývá i unsupported URI schemes (FTP/PostgreSQL/
JDBC nested) a scheme-relative authority; HTTP recognition se tím nerozšiřuje. Opaque input hashes drží freshness bez plaintext secrets.
Workspace kvalifikuje identities a source locators, nikoli URI paths; service
binding ani cross-service path match se nevymýšlí. Runtime execution vždy
NOT_OBSERVED a availability UNKNOWN. Žádné HTTP, klient či application neběžely.

## Kompatibilita a fixture

Graph/store1/2/3 zůstává čitelný; bez HTTP version je coverage UNKNOWN. Protocol1
má jen optional typed fields; malformed nové facts se odmítnou před publikací.
Fresh capture binduje HTTP rule/config fingerprint a replay je validuje offline.
Pure/source-only/config-failure testy zakazují subprocess a ověřují zachování
posledního grafu. Historické store není implicitně přepisováno.

`fixtures/http-client-execution` explicitně připravuje Spring6.2.2, Reactor3.7.2,
OpenFeign4.2.0 API. Lock obsahuje skutečné JAR/POM SHA a published POM license
names (Apache2; reactive-streams MIT-0); JARy se nevendorizují. Actual tests ověřují
bytes/license a vlastní worker home. Mandatory Linux compiler CI explicitně
kompiluje fixture a zahrnuje HTTP module. [Capability matrix](../compiler-inspection.md#http-client-intent),
README, architecture, acceptance inventory a progress mají stejný omezený scope.

## Přesné finální kontroly

Env: `PYTHONPATH=/workspace/http-execution/src`,
`KGMAKER_WORKERS_HOME=/workspace/http-execution/workers`,
`KGMAKER_TEST_MAVEN_REPOSITORY=/workspace/tools/m2`,
`KGMAKER_REQUIRE_WORKERS=1`, `KGMAKER_REQUIRE_K2=1`; JDK21.0.6/Kotlin2.1.10,
Python `/workspace/kgmaker-venv/bin/python`. Heavy runs pod týmovým flock.

- Sequential actual `python workers/jvm/build.py --kotlin-home /workspace/tools/kotlinc --maven-repository /workspace/tools/m2 --java-home /workspace/tools/jdk-21.0.6+7`: **PASS14.07s**; také `--backend k2 --analysis-api-home /workspace/tools/k2-verified`: **PASS12.36s**. Pozdější opravy jsou pure Python; JVM source/bytes se nezměnily.
- K1 SHA256 `14eddbf8f31011c22a144e67552706268daa3138ca71993fd638d70a556f026b`; K2 `3c84080730333731611f42dbacd91a1bf3f75b863f045de715be73fc3828a0b3`.
- Read-only prerequisite preflight **PASS0.07s**. Final focused scanner/inspection-contract/HTTP/protocol/control-flow/dataflow/workspace/mandatory-CI **121 PASS63.39s**, všech40 HTTP případů včetně skutečných Java K1/K2 a Kotlin UNKNOWN.
- `python -m pytest -q --basetemp=/workspace/http-review-fix/full-tmp --junitxml=/workspace/http-review-fix/full.xml`: **654 passed, 10 skipped in 869.89s (0:14:29)**. Runner 870.22s. XML: 654 PASS/10 SKIP,0 errors/0 failures. Optional tool/platform skips nejsou vydávány za mandatory worker PASS.
- `TMPDIR=/workspace/http-review-fix/tmp`, persistent runner/log/XML/results/source-manifest v `/workspace/http-review-fix/`. Frozen112-file source manifest souhlasí před/po full; obě runtime SHA stejné.
- `compileall`, `git diff --check`, bounded semantic update/apply/validate/CLI scan/check **PASS**. Zachováno původních7 concepts/25 relations, přidán1 HTTP concept/4 doložené relations. Scanner target258, HTTP prepare87/augment605, ownership275 a Javac citation112 jsou revalidované. Všech119 inherited episodes i historický feature episode85d60f (source0258bba) jsou immutable. Finální workflow zachycuje ještě jeden feature episode (`memory capture --base c7beaec95951267796c0c21baa6079fafe5fe124`) a obnovuje graf CLI.

## Uchovaná historie neúspěšných a přerušených kontrol

První full: **1 FAIL330 PASS7 SKIP449.35s**, zastaven po legacy redaction assertion
požadujícím ponechat public `safe=1` query. Expectation opraven na celý redacted URI;
contract+relevant focus **86 PASS41.96s**. Produkt source/binary se tím neměnil.
`/tmp/http-interrupted-full.log/.xml` jsou zachované. Jeden runner typo před retry
neodstartoval žádné testy a byl opraven.

Další retry exit1/392.15s zaplnil `/tmp` tmpfs4.9GiB; sessionfinish/JUnit write
Errno28, XML0 bytes. Není to validní whole PASS ani spolehlivý per-test count.
Jen vlastní ukončené pytest545/547 temporary artifacts byly zachovány přesunem do
`/workspace/http-interrupted-pytest-545` a `http-enospc-pytest-547`; cizí data se
neměnila. Další log/temp/XML používají spacious workspace.

Při privacy auditu actual SOURCE_ONLY scan odhalil raw default-URL signature leak;
regression scan/save/load/docs s Popen zákazem po fixu **2 PASS0.07s**. Před změnou
byl full ukončen **159 PASS2 SKIP196.37s**. Následný actual Feign consumer-process
assertion měl **RED1 FAIL3.10s**, po pure read filter fixu **GREEN1 PASS2.16s**;
před touto změnou full ukončen **184 PASS2 SKIP311.54s**. Tyto runy nejsou konečný
PASS; konečný neporušený výsledek je výše. Artifacty zůstávají v
`/workspace/http-validation-final` a `/workspace/http-privacy-final`.

Source0258bba měl také kompletní **641 PASS10 SKIP624.24s** a capture
`episode:85d60f164567d3a0d585b89166c6cd16fe712c84aeb59ba5ea7d81313c86784b`.
Následná iteration1 pure negative však reprodukovala plaintext unsupported FTP
credential v contextu. Generic URI privacy parsing to opravilo bez rozšíření HTTP
mapping; pět nových unsupported-scheme cases plus SOURCE_ONLY/contract
**7 PASS0.09s**, zakázaný Popen. Starý641/10 je historický proof, nikoli náhrada
nového aktuálního whole výsledku výše. Historical episode se nepřepisoval.

## Neprovedené kontroly a hranice

Remote mandatory Actions gates jsou BLOCKED potvrzeným billing/spending limit;
žádný remote PASS ani merge se netvrdí. Independent review a Draft publication
provádí parent nad finálním exact HEAD. Nepodporovány jsou obecné custom clients,
operator/interprocedural/generic publisher flow, dynamic URLs, libovolná proxy
registration a skutečná HTTP/data availability. Specifikace S07/S13 runtime a
celý T003 zůstávají samostatné, nedokončené kontrakty.

## Nezávislé review PR49 — ověřený rule2 follow-up

Root dodal a zachovány jsou jeho uncommitted embedded scheme-relative URI privacy
fix a SOURCE_ONLY Python doc-comment regression. Nezávislý reviewer doložil
actual P1 false UNSUBSCRIBED přes throw operand, ternary condition a for update;
nový combined actual test přidává resource a break/unreachable update negativy.
Výrazy se navštíví, ale loop/try order se nevymýšlí: tato hranice je UNKNOWN,
nikoli execution či uzavřený unused proof. Ternary branch aliases se mergují.

Další actual repro URI(String,Function) měnilo efektivní path z /old na /new,
ale původně se ukládalo /old. Unsupported multiargument URI nyní odstraní exact
base/path, s HTTP_URI_OVERLOAD_UNSUPPORTED. Feign path prefix se ukládá zvlášť
(client_path/method_path), composed path je UNKNOWN bez guessed concatenation.
Escaped/whitespace properties overriding line už nesmí vytvořit MATCHED první
hodnoty: unsupported meaningful syntax či nečitelný/oversized selected file
invalidačně označí property provenance. Žádný nový properties evaluator.

Před opravou nových7 parametrizovaných případů **7 FAIL27.39s** (skutečné
Javac API v K1/K2, Feign a pure property negatives). Po fixu původních39 cases
**39 PASS111.07s**, před version-only bump. Rule je nyní http-client-execution-2;
předchozí v1 HTTP index je STALE při read bez procesu nebo store mutace.
Pure privacy/property/v1-staleness subset **4 PASS0.72s**.

Worker Java/Kotlin source i K1/K2 JAR SHA se neměnily. Aktuální striktní
focused/full proběhl serializovaně po golden pod týmovým flock, s vlastním worker
home a log/temp/XML na /workspace, nikoli malém /tmp tmpfs. Prerequisite preflight
PASS0.07s, focused121 PASS63.39s, celý současný source654 PASS10 SKIP869.89s.
Všech40 HTTP cases běželo bez skip/error/failure;112-file manifest a oba JAR
hashes souhlasí před/po full. Historický sourcee55 měl646/10; nenahrazuje tento
aktuální rule2 whole proof. Žádný JVM/IR rebuild nebyl nutný ani tvrzený.

Scoped semantic update/apply/validate revalidoval8 manual concepts/29 relations,
prepare_context87/augment_http_graph605 a všechny související citations.
Všech121 předchozích episodes zůstává immutable; po kontrolách se přidává jediný
review-fix episode nad přesným basec5c45f3. Závěrečný commit mění pouze metadata.
Root provádí exact-source review a publikaci; autor nepushuje, nemerguje a
nespouští billing-blocked remote CI. Return-flow zůstalo po dobu oprav zmrazené.
