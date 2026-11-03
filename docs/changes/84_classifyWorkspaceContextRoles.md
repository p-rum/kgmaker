# T006/T008 revize2 — role workspace-derived kontextů (rozpracováno)

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
