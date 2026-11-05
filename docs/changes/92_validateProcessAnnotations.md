# T031 — čistá validace návrhů procesních anotací

## Problém a výsledná změna

T030 připravuje packet, ale caller by mohl předložit stale či self-rehashed
allowlist a navrhnout technické změny. T031 připojuje na konec stejného
process_semantics.py čisté `validate_process_annotations`: z explicitně aktuálního
ProcessView/docs/conflicts znovu odvodí celý T030packet pomocí ověřených budgets.
Vyžaduje exact canonical equality, nikoli důvěru ve supplied self-hash.

Strict candidate povolí pouze schema1, skutečné target/source/group IDs a
semantic PROPOSED label/description/grouping; běžné invalidní vstupy vracejí
nonsecret REJECTED report s prázdnými annotations. Platná struktura zůstává
PENDING/CONFLICT, nikdy approval/apply. Text/group members nejsou technická
truth, grouping neprovádí T026 a výsledek nepřidává outcomes/edges/conditions/
availability. Různé overlapping field hodnoty stejného targetu se zachovají
všechny s review CONFLICT, komplementární/identické proposals zůstávají pending.
Captured documentary CONFLICT/UNKNOWN jsou review items, NLP NOT_EVALUATED.

Root předem přijal /workspace/t031-architecture-brief.md; specRev2 před publicRED
stanovila přesný invalidreport/exception, text/ref limits a konfliktní kontrakt.
Explicitní stack je T030070e709 nad main deb3691, nikoli skrytě dokončená dependency.
T030má schválený source, ale requiredfull zatím PENDING. Žádná T030function/import/
constant se nemění: complete original byte prefix a všech32ASTnodes zůstávají,
stejně jako všech47T030testů a27workerinputů. Změna je append-only124řádků, žádný
buildnative/store/provider/feature validator, Git či I/O. T032/T034 zůstávají mimo.

## Acceptance a skutečné důkazy

- T031-AC01: `test_self_rehashed_poisoned_packet_cannot_define_its_own_authority`,
  current-content/doc/scope/context mutations a generation-only positive.
- T031-AC02: hand-labelled Czech group + existing outcome; technical subtree,
  fingerprint a všechny inputy zůstanou byte/deep-equal.
- T031-AC03: explicit doc conflict a two same-target conflicting labels zůstávají
  všechny k review, comparison=NOT_EVALUATED, žádný arbitrary winner.
- T031-AC04: noI/O trap, malformed/secret/error/depth/cycle/shared cases,
  invalid later annotation vrací nulové partial proposals; saved artefakt se nemění.
- T031-AC05: forgedrefs/extra technical fields/status/group/outcome/opaqueproofrefs
  rejected, tiny-budget omissions neberou autoritu, unsupported/truncated input
  zůstává PARTIAL/PENDING. Label slovo 'approved' není human approval.
- T031-AC06: specRev2, README/API/capability/AC/progress + note92; source review,
  required full a root publication ještě PENDING.

Public RED **6FAIL,56deselected,0.40s** zachytil absenci veřejné validate API.
První targeted62PASS0.86s; final společná pure sada **229PASS,0SKIP za6.22s**
zahrnuje76T031 a všech153původních T030/T023/T026pure/feature/sanitizer/protocol
případů. Source prefix/AST proof a XML jsou v
/workspace/process-annotation-validation-proof/. Nejde o compiler ani full PASS.
Root může schválit jeden budoucí strictsuperset full pro T030+T031 po exact
prefix/47collectedIDs/native proof; žádný full se zatím nezařadil.

## Kompatibilita, příklad a nedodané části

Stejný ProcessView/store/graph reader, žádná persistent migrace ani změna
technických fingerprintů. Report má oddělenou version1/rule identity a není
aplikovaný ProcessView. Dodané CURRENT inputs jsou content consistency, nikoli
autentizace fyzického checkoutu či útočníka schopného nahradit všechny vstupy.
Opaque ID a arbitrary unlabeled secret nelze univerzálně rozpoznat; známé auth/
URI/control formáty se odmítají bez echo. Žádná raw docs/proof/code prose není
zkopírována jako nová authority; vrací se jen explicitně validovaný proposal text.

```python
from kgmaker.process_semantics import validate_process_annotations
report = validate_process_annotations(current_process_view, packet, candidate)
# report['valid'] nenahrazuje report['review_status'] ani lidské review/apply.
```

Note92 rezervoval root po91W07/90T030 a otevřených PR; všechny worktrees znovu
zkontrolovány (max91,92absent) před editací. Required full/GH CI NOT_RUN; GH CI
volitelné dle uživatele, ostatní gates zůstávají. T030worktree070 se neměnilo.
Publikace/merge pouze po root finalreview; nedokončuje se celé T004.
