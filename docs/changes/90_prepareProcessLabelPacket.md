# T030 — bezpečný packet pro návrhy business popisů

## Problém a změna

T024/T026 poskytují technický ProcessView, nikoli bounded vstup pro návrhy
business popisů. T030 přidává čistou Python API `prepare_process_label_packet`:
content-bound packet a prázdný PROPOSED template pouze pro existující targets.
Nevykonává discovery, model/compiler/build, feature.prepare, I/O ani semantic
apply. T031 validace/apply a T034 CLI zůstávají samostatně pending.

Zachovává process/revision, původní baseline i skutečné definition/technical/
content hashes, scope a typed context selection, úplné target/source/proof refs,
owner/original IDs, entry/exit/outcomes, evidence/status a unresolved/truncated
hranice. Ordered collapse content je hash-bound, neexpanduje se. Žádné raw
labels/doc/config/condition/proof prose se neexportují; omission má pevný důvod
+hash. Unicode IDs a paths s mezerami zůstávají; rozpoznatelně unsafe credential/
URI/control ID se odmítne bez echo. Opaque ID není autentizováno ani univerzálně
klasifikováno jako secret; privacy slib nespočívá na libovolné password regex.

Explicit document capture má ověřený či výslovně supplied content hash, vybraný
scope/context a malý ref-only provenance schema. Unknown note/config pole není
reference. Captured structured CONFLICT/UNKNOWN jsou review items; žádný NLP
conflict detector ani nová technical authority. Existing selection diagnostics/
coverage payload jsou hash-bound místo raw textu. Selection shape mimo konkrétní
existující service-list/row/inventory kontrakty je řízená chyba.

Účtování finálního canonical `{packet,candidate_template}` zahrnuje schema,
omissions, hashes i cost fields. Token estimate je ceil(UTF8_bytes/4), char count
Unicode. Započítané status_padding drží stejnou šířku false/null a true/reason,
aby přesná hranice neoscilovala. Mandatory overflow neodstraní ID; hard input/
packet limit selže bez artefaktu. Per-occurrence iterativní bounds předcházejí
model copy/JSON a chrání cykly, shared aliases, depth a velikost.

## Acceptance a skutečné kontroly

- T030-AC01: `test_identity_template_and_original_proofs_are_complete_without_new_targets`,
  `test_hash_ignores_order_and_generation_but_binds_actual_content_and_documents`,
  `test_collapsed_step_order_is_bound_but_expansion_and_existing_approval_never_export`.
- T030-AC02: tiny budget, UTF8, hard-envelope, invalid-budget a parametrizované
  `test_adjacent_exact_budget_has_consistent_final_cost_and_flag` (char/token).
- T030-AC03: no-I/O secret sentinel + malformed secret validation key, Unicode
  ID/path, ref-only doc provenance a inventory-diagnostic privacy.
- T030-AC04: deep input equality při success/chybě, stored sentinel soubor se
  nemění, preflight cycle/deep/shared/nonjson před ProcessView.from_dict.
- T030-AC05: explicit structured conflicts, scope/context/content/reference
  mismatch, unsupported/unresolved/truncated proces bez evidence promotion.
- T030-AC06: spec revize2, README/Python příklad, capability/acceptance/progress,
  tento note; independent source review + required full zatím PENDING.

Public RED: **4 FAIL,25 deselected,0.21s** — veřejná API dosud neexistovala.
První targeted po implementaci35PASS0.70s; následné privacy/budget/identity
hardening přidalo explicitní testy. Finální společná pure sada **149 PASS,0 SKIP
za4.18s**: T030, celý T023, pure T026 diamond/field-write boundary, feature,
inspection sanitizer a worker protocol. Testy se nespouštěly jako compiler
acceptance. Žádný nový native build není potřeba, workery se nemění.

Receipts: /workspace/process-label-packet-validation/public-red.{log,xml},
pure-focus.{log,xml}. Required full, nový actual worker/toolchain běh a GH CI
jsou NOT_RUN. Local full čeká na source review/preflight; GH CI je volitelné dle
uživatelské revize pravidel, nikoli nahrazené tvrzením PASS.

## Kompatibilita a příklad

Nevzniká nový store, přepis ProcessView ani persistent migrace. Existing process/
view model, opaque original IDs a absence runtime důkazu zůstávají. Candidate
není aplikovaný ProcessView ani approval a nevytváří outcomes/edges/conditions.

```python
from kgmaker.process_semantics import prepare_process_label_packet
result = prepare_process_label_packet(existing_process_view, token_budget=8000, char_budget=32000)
# result['candidate_template']['annotations'] == []; caller navrhuje význam zvlášť.
```

Note90 ověřen přes main/registr a všechny worktrees (max89), otevřené PR současně
ověřil root2026-11-05. Baseline deb3691; upstream T024/T026 jsou přítomné. Root
před implementací přijal architecture brief /workspace/t030-architecture-brief.md.
Zbývá full, finální nezávislé review a root-authorized publikace; tento note
netvrdí dokončení celého T004 ani T031/T034. Nevolaly se aplikace či model API.
