# W04 revize2: explicitní plán Kafka code/group proof

T003-S07-W04 revize2, S06–S09 a AC05–AC09. Tato úvodní změna je specifikace,
nikoli dokončená implementace. Samostatná větev je explicitní draft stack nad
PR51/head0797d4c; po jeho verified merge byl parent aktualizován na main ef3ab405.
Frozen PR51 acceptance a jeho uzavřený scope se nemění.

Revize1 umí deklarovanou cluster/topic/contract/release identitu a správně uvádí
code_binding UNPROVEN. T012 potřebuje skutečné consumer group/subscription a
listener/send origin proofs. Veřejná revize2 proto rozšiřuje stejné zadání, nikoli
resolver uvnitř T012: exact canonical annotations, explicit config groups, schema2
code refs, current context/SHA/scope/ownership a typed Javac literal send. Regex je
pouze candidate bez expanze, Kotlin producer bodies/wrappers/default groups UNKNOWN. Javac Java send musí fungovat
v obou k1/k2 worker backendech; nerozhoduje blanket backend flag.

Před implementací se provádí durable analyze/plan a skutečný RED nad existujícími
API/worker fixture. Zatím nebyl deklarován nový PASS, full, runtime ani merge.
Zůstává Graph/store/protocol kompatibilita a nulový implicitní broker/app/build.
Allocation: main, všechny worktrees a otevřená PR ověřeny; max76, note77 volné;
note78 je rezervováno pro W08. Před publikací se kontrola zopakuje.

## Průběžná implementace a skutečné omezené kontroly

Nový Python adapter `kafka-code-1` používá pouze stávající compiler graph/body,
canonical contains/argument proof a bounded původní zdroje. Kafka-only původní
realm/annotation witness brání povýšení vzájemně pozměněných symbol/Node mirrors.
Provider kontroluje version stamp a původní raw source hashes; non-Kafka IDs se
nemění. Schema2 code refs vyžadují přesný current source/context/scope/ownership,
canonical replay, topic agreement a pro consumer exact `.group`. Subscription
odděluje logical identity a capture revision. Graph/store schema se nemění.

Aktuální bounded matrix: `tests/test_kafka_code_bindings.py`, oba skutečné JVM
backendy s povinnými toolchains a pinned Maven API, **9 PASS / 47.15 s**,
`/workspace/kafka-code-validation/current-nine-corrected.xml`. Zahrnuje Java
listener/group/regex a send oba backendy, SOURCE_ONLY/forged metadata negatives,
canonical replay corruption, explicit schema2 join/private redaction a foreign
ID/context/SHA negatives. Kotlin K1 listener je pozitivní; Kotlin K2 actual test
ověřuje explicitní PARTIAL/absenci annotations a žádné listener promotion. Nejde
o tvrzení podpory Kotlin K2 listenerů. Java producer constants/escaped literals,
wrappers/ProducerRecord/NewTopic/method references neposkytují pozitivní proof.

Předchozí logy zůstávají oddělené: chybně nastavený PATH způsobil required JDK
FAIL; mutation payload byl původně model-invalid; foreign context správně vyvolal
AnalysisError místo očekávaného UNPROVEN; první Kotlin K2 positive expectation
odhalilo chybějící worker metadata. Opravená explicitní matice je uvedena výše.
Finální full, dependency bootstrap, semantic/memory/scan a nezávislé review jsou
stále neprovedené/pending; T012 ani tato revize nejsou DONE.

## Uzavření canonical proof guardů před full

Nezávislé review našlo P1: vzájemně přepsaný method owner v raw symbolu a Node
metadata původně prošel. Oprava váže id/owner/name/descriptor/kind/context/scope
na původní compiler contains tuple. Producer má analogický původní call-site a
canonical dependency-target tuple v declares_call proof. Vlastní actual negative
navíc prokázal source annotation shadow se stejným oficiálním FQCN; adapter jej
nyní odmítá podle skutečných compiler source symbols, bez source parseru.
Podezření na code_ref ownership bylo nezávisle staženo: existující validace již
vyžaduje unique explicit source ownership shodné s binding.service_id.

Aktuální opravená matrix je **10 PASS / 54.287 s / 0 SKIP, FAIL, ERROR**, XML
`/workspace/kafka-code-validation/final-guard-ten.xml`. Všech91 bounded input
hashů je pre/post beze změny; nejde o celý full input manifest. Nezávislá source
closure APPROVE je nad ef3ab405/f2f3dc4. Předchozí9 PASS zůstává pouze důkazem
předchozího draft source. Semantic apply/validate a draft memory/scan/check byly
provedeny; posunuté původní reference se obnovují před finálním full freeze.

Pro full se explicitně připravují skutečné JDK21/Kotlin K1+K2/TypeScript5.7.3 a
React18.3.1 fixture, byte-exact27 worker inputs a30JAR/lib closure z dříve
ověřeného argument donor buildu. Source-only preflight nespouští build/install.
Nový API-only Maven fixture má samostatný explicitní offline bootstrap ve FIFO
frontě. Povinný strict full se teprve zařazuje; žádný full PASS ani DONE se netvrdí.

## Integrace current main před finálními kontrolami

Main `9442114d169b84e6c9f98dd097faafd80eff0d48` (T011, PR65 local operations,
T026) je integrován před novým current-parent full. Kafka Python adapter/binding
runtime a `tests/test_kafka_code_bindings.py` zůstávají byte-exact8af/f2f3.
Main215 implementation episode prefix i oba původní Kafka capture objekty jsou
zachovány beze změny. Workspace qualification a compiler CI drží obě vrstvy;
připravený Kafka API-only Maven krok zůstává explicitní.

Historické full pokusy nejsou PASS: první **1151PASS/9SKIP/1ERROR** skončil na
ENOSPC při UI fixture copy, všech1364 input hashů beze změny. Následující full
**1235PASS/10SKIP/1FAIL v1529.28s** doběhl k packaging license assertion; vlastní
JVM analyze/store již prošel, chyběl `target/licenses/kotlin/LICENSE.txt`.
Obě původní XML/log/receipt jsou zachovány. Env recovery matrix191PASS/0SKIP
v251.61s a celý packaging/exporter/Windows/Kafka/CI focus45PASS/3SKIP v79.21s
ověřily předchozí exact-source distribuci; skips jsou explicitní Maven/Gradle
PATH a skutečný non-admin Windows gate, nikoli PASS těchto prostředí.

Complete102 Kotlin license files byly ověřeny proti původnímu exact27 native /
30JAR donor buildu a official Kotlin license tree. Následný license-full nebyl
spuštěn: capacity gate2.70GB <5GiB jej zastavil před pytest. Requeued FIFO runner
byl na pokyn root zastaven ještě childless/unstarted před current-main merge;
nejde o další full výsledek. Temporary fixture copies dokončených vlastních běhů
byly před cleanup SHA-manifestovány; receipts/log/XML se nemažou.

Current-parent worker distribuce je převzata z ověřeného PR65 donor
`/workspace/local-operation-proofs` teprve po shodě všech27 tracked worker
source/build/lock/config inputs a132 distribution JAR/license hashů z jeho
původního build receipt. No nový build: K1 `5dd96f7c6cd6a5d7317b98cd81953a37d2bf4f914dbeee73b3d8983106ab170d`.
Current-parent coalesced actual focus, full, finální exact-pair review a ready
zůstávají pending; předchozí bounded PASS se za ně nevydává.

## Finální current-parent lokální evidence

Výše uvedené pending/FAIL odstavce jsou historické checkpointy. Frozen source
`19b0594795ac1f9167916178907b77bb0f070f51` nad main944 má current-parent focus
**102PASS/0SKIP v99.74s**, včetně Kafka code guards, celého T011 consumer katalogu,
installed-worker checks, mandatory CI a actual K1/K2 local-operation producer /
workspace kontraktu. Všech1477 source/distribution/fixture/tool input hashů bylo
před/po beze změny. Root nezávisle potvrdilo source composition APPROVE nad19b;
implementační agent si source approval neuděluje.

Jediný skutečně spuštěný current-parent strict full poté prošel
**1576PASS/10SKIP v1536.69s** (XML1586cases,0FAIL,0ERROR). Required worker/K2/
Spring imports/conditions/HTTP-provider flags byly1, prerequisite preflight PASS,
HEAD19b i všech1477 hashů zůstaly beze změny. Receipt/XML/log:
`/workspace/kafka-code-validation/main944/`. Skip10 přesně odděluje explicitní
Maven/trusted-exporter PATH případy, Gradle8.13/Kotlin-cache gate, druhý JDK a
skutečný non-admin Windows smoke; tyto prostředí nejsou PASS. GitHub CI nebylo
znovu spuštěno a není tímto tvrzeno zelené.

Full dokládá integrovaný statický kontrakt, nikoli broker/app/data availability.
Kotlin K2 listener metadata zůstávají výslovně PARTIAL bez promotion, regex není
exact-topic join a producer wrappers/unsupported Kotlin arguments zůstávají UNKNOWN.
Finální follow-up mění jen tuto evidenci, acceptance, implementation memory a
CLI-generated graph; runtime/tests/native bytes zůstávají stejné jako při19b full.
Root provede finální exact-head review a publication/merge; tato větev nemerguje sama.
