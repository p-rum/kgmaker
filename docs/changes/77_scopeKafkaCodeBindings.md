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
