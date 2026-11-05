# T014 — projekce explicitních vzdálených bindingů

Root schválil architecture brief a explicitní stack W07 5b39ec4/T013 f43c9e0.
Spec revize2 stanovuje pure ViewDocument projekci přes existující W07 resolver,
původní endpoint/proof IDs, kandidátní ambiguity/incomplete boundaries a
capture-time UNKNOWN. Žádný druhý resolver, I/O, compiler či runtime proof.

T014-S01–05/AC01–06: implementace a public RED/green zatím PENDING.
T013/W07 actual/full, nezávislé source review, current-main integration a full
T014 jsou NOT_RUN/PENDING; tento note neprohlašuje dodávku za hotovou.

Note93 přidělen po main/registr/ALL worktrees (max92), file listech všech7
otevřených PR a koordinaci resume_return: T032 nemá rezervovaný note.

## Source checkpoint a skutečné kontroly

Nový remote_interfaces.py přes existující W07 resolver vrací topology ViewDocument.
Zachovává endpoint/origin/proof IDs, oddělené HTTP/Kafka remote relations, všechny
candidates, incomplete/unmapped boundaries a capture-time UNKNOWN. Nová provenance
je SOURCE_ONLY/UNKNOWN polarity, origin compiler proofs se nepřejmenovávají.
Raw prose/payload se neexportuje. Žádný native/runtime/W07 producer se nemění.

Public RED2FAIL0.97s: API neexistovala. Po rozšíření19PASS1FAIL0.42s: test chybně
vyžadoval shodu celého recaptured packetu po změně pořadí workspace array. W07
váže původní workspace hash; opravený test vyžaduje stejné candidate edge IDs,
targets a AMBIGUOUS místo falešné rovnosti nového capture fingerprintu.
Následující coalesced pure135PASS10actualDESELECTED1.42s (T014/W07/View/T009),
bez compiler/build/runtime. Receipt /workspace/t014-validation/pure-focus3.xml.
Finální scope-hardening source:135PASS10actualDESELECTED1.08s, pure-final.xml.

Independent source review, actual capture reprojection, strict full a GH CI jsou
NOT_RUN; žádný heavy job se nequeueoval. Final readiness závisí i na upstream
T013/W07 actual/full a current-main source closure.
