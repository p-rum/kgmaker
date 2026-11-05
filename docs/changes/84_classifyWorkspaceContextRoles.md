# T006/T008 revize 2 — role workspace-derived kontextů

Baseline `8afabe7c5056b9ec45e04f1f8fcf3470d18f4c98`, izolovaný stack
`fix/t006-t008-derived-context-roles`. Note84 rechecked local worktrees,
origin/main a changed paths otevřených PR před zápisem; dosud bez kolize.

Problém: veřejný mixed Kafka snapshot má kanonické SOURCE_ONLY/
WORKSPACE_DECLARATION kontexty s cross-repo contract inputy. T008 dosud všechny
context.source_files předává T007 jako repository source a dostává správnou
foreign-path chybu. Prefix/mode fallback by oslabil ownership a legacy coverage.

Root i nezávislá architektura schválili bounded brief. T006-S06–S08/AC07–08 a
T008-S06–S08/AC07–09 jsou před implementací explicitně rozšířeny. Plán reuse
producer identity helperu a společné klasifikace role, celého původního graphu,
T006 selection/freshness a T007 striktních scope/repo/hash kontrol. Role validity
není source freshness; historické nevybrané derived inputy nevyžadují private
compiler replay. Unknown/malformed claim nemá source fallback.

Zatím žádná implementace, nový PASS, full nebo ready evidence. Actual uložený
T012 mixed snapshot reprodukuje AnalysisError foreign ownership path čistě nad
existujícími capture; config-only a portable public regression budou ověřeny
samostatně. No worker build, app/broker/network/runtime pozorování se netvrdí.

## První bounded draft po skutečném RED

Portable public RED: inventory nad snapshot_workspace vrací původní
foreign-qualified-path AnalysisError (**1FAIL/0.26s**). Samostatný actual uložený
T012 capture reprodukuje stejnou chybu se3 derived contexts; workspace/fullgraph/
coverage i původní stores jsou beze změny a projection path zakazuje proces/network.

První draft přesouvá přesnou producer context identity konstrukci do pure helperu,
klasifikuje known/unknown derived claims před ownership a compiler selection a
ponechává legacy source context bez nových markerů. Role a freshness jsou oddělené;
T008 rules_version2 je aditivní, staré ViewDocument zůstávají čitelné. První krátký
check měl3PASS/1FAIL: trigger view záměrně neobsahuje service nodes a test nejprve
nesprávně předpokládal opak; fixture assertion je opravena na jeho context_selection.
Žádný coalesced/final focus ani full zatím neprošel. Current-main/T011 integrace
zůstává před frozen final source review/full povinná; T016 ještě není dodán.

## Current-parent scoped evidence before source review

Parent `19b0594795ac1f9167916178907b77bb0f070f51` includes verified main944 and
T011 consumers; it is merged into this isolated stack. T016 remains undelivered.
One coalesced pure matrix over T005–T010/T015, existing Kafka/trigger contracts and
new role cases: **294PASS/0SKIP/9actual DESELECTED v15.04s**, all606 frozen inputs
unchanged. Model-invalid identity mutation initially correctly produced structured
INVALID_SNAPSHOT; the regression now keeps reference integrity to exercise the
actual canonical identity guard. The earlier10PASS/1fixtureFAIL is retained.

Pure actual replay `/workspace/kafka-code-validation/main944/focus-pytest/` schema2
capture: T008/T010/T011/T015/T024 all5projections pass, both real compiler contexts
remain CURRENT and2derived contexts are excluded only from ownership/selection.
Full graph/workspace/coverage/private stores remain byte/equality unchanged;
Popen/network are forbidden during projections. No new compiler execution/build.
Separate older T012 capture with3derived contexts also projects without error,
but its legacy freshness gives0CURRENT contexts; it is not the current-positive
proof. Source review and one final frozen full remain pending. Root owns publication.

Dodatečný bounded canonical-hash negative (valid64hex změna input SHA bez změny
context ID) prošel **1PASS/0.19s**. Doplnil výslovnou hash/identity coverage po
coalesced294; produktový runtime po něm zůstává byte-exact jako při294 a actual
replay. Změnil se pouze seznam parametrů testu. Finální full stále pending.

Před jediným full přijat main8e81 (PR67 optional prerequisites). Produktový runtime,
workers/fixtures/workflow zůstávají byte-exact source-reviewed49d; změněny jsou jen
available-tool setup guards a nový25unit modul. Current-parent guard/classifier/
mandatory checks **43PASS/0SKIP v0.33s**; původní295pure a actual5projection evidence
zůstávají source základem. Root source closure APPROVE49d platí pro shodný runtime;
full je povolen až na tomto current-parent checkpointu, bez nového worker buildu.

## Current Return parent before the single actual full

Dřívější10d full nebyl spuštěn: capacity gate2.55GB<5GiB skončil předpytest,
bez started marker/XML/full receipt. Capacity-only audit zůstává zachován a není
FAIL/PASS testů. Po ověřeném PR70 přijat main
`deb3691c23de19064a9e9c0484cf6a62ab295592`; Return freshness/qualification a
LocalOps→Return→Kafka augmentation zůstávají přesným parent runtime. Vlastní
83line roleclassifier, views boundary a producer tuple helper zůstávají přesně
stejné jako source-approved49d. Main224episodeprefix a oba vlastní captures se
zachovávají. Native27 inputs jsou přesně source-testedReturn079; jeho30JAR a102
licencí jsou ověřeny a explicitně převzaty, žádný nový build.

Následuje current-parent bounded common/Return/Kafka projection focus, nezávislá
composition closure a jediný actual full; žádný full10d ani fullnovéhoSHA zatím
není tvrzen PASS. Předchozí295/43/pureactualreplay proof zůstává historicky přesný.


## Finální current-main a společný strict full (2026-11-05)

Finální source baseline je main `3e5ef0f0c56c406a5428e826120ca525774b373f`.
Vlastní tři runtime soubory a test jsou byte-exact se source-approved `a65c195`
a s validovaným společným potomkem `2df55ff8d15d790808f6a81072144eeb408a05b8`.
Current-Return actual focus: **217 PASS / 0 SKIP, 170.849 s**, 1490 vstupů
beze změny. Pure current-main focus: **100 PASS / 0 SKIP, 3.06 s** společně
s T012/T013; nenahrazuje skutečnou kompilátorovou evidenci.

Jediný společný strict full běžel na `2df55ff`: **2587 PASS / 10 přesně
povolených optional SKIP, 2042.93 s**, všech 2597 výsledků, 4897 hashů a pět
úplných inventářů artefaktových adresářů beze změny. Celá kolekce tohoto Common
rodiče obsahuje 1966 ID; ve společném XML mají **1956 PASS / 10 optional SKIP**.
Jde o podmnožinu jednoho běhu potomka, nikoli samostatný full této větve.
Povolené SKIP se týkají neaktivovaných Maven/Gradle exporterů, druhého JDK a
Windows smoke; žádný compiler/feature SKIP navíc nebyl přijat. Evidence:
`full-attempt-2/full.xml`, `parent-result-classification.json` a samostatné
ověření `final-green-verification.json` ve validačním workspace.

První společný full skončil **78 PASS / 2 optional SKIP / 1 FAIL**, zbytek
2516 NOT_RUN: classpath fixture postrádala `JavaBridge.class` a Kotlin module
metadata, která původní transfer manifest nepokrýval. Původní log/XML a vstupy
zůstaly zachovány. Po explicitním doplnění přesných donor artefaktů prošly oba
nezměněné původní golden/branch testy **2 PASS**; teprve potom byl autorizován
nový celý strict full. Runtime ani assertion nebyly oslabeny, nový native build
neproběhl. Native zdroje odpovídají původnímu skutečnému buildu Return079.

T006-AC07–08 a T008-AC07–09 jsou ověřeny v uvedeném rozsahu. Role nadále není
freshness ani runtime availability; unknown/malformed claims nemají source
fallback. Nezávislé finální review aktuálního base/head, ready a merge jsou
samostatné kroky; GH CI není tímto lokálním výsledkem prohlášeno za PASS.
