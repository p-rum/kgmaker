# T026 — Bezztrátové seskupení doložených lokálních operací

T026-S01–S05 / AC01–AC06. Explicitní draft stack nad PR65,
`feat/t025-certify-local-operations`, exact `a6170c18c53333946dc6bb694e797170227a90fc`.
Prerequisite má samostatný review/full/merge gate; readiness T026 čeká na jeho
schválení a merge. Celé T003/T004 se tímto dokumentem neprohlašuje za dokončené.

## Změna a hranice důkazu

Čisté `business_process.collapse_business_steps` / `expand_business_steps`
využívá ProcessView/ViewDocument a již vložené T025 certifikáty. Kontroluje jejich
existující content identity a method/context/scope/source/CFG tuple; nevytváří
nový compiler certifikát, CFG, resolver, store ani fyzické ověření checkoutu.
Slučuje maximální acyklické single-entry/single-exit sousední řetězce min2
certifikovaných lokálních operací stejného method/owner/scope/context.

Ordered origin nodes/internal edges, původní endpointy a všechny paralelní
vnější hrany, evidence/provenance, entry/exit/outcome i nevyužitý exceptional_exit
se zachovávají přesně. Rozbalení znovu ověřuje deterministickou podporovanou
projekci, nikoli jen supplied hash; digest-consistent změna pořadí je odmítnuta.
Finally klony se rozlišují expanded topologií/IR path, nikoli samotným rozsahem.
Decisions, calls, side effects/field writes, loops, service/transaction/async a
UNKNOWN hranice zůstávají viditelné. Stejné DTO, label ani semantic approval
nedodávají execution/purity proof.

Action zůstává UNRESOLVED s operation i SYNTAX_CANDIDATE vnitřními přechody;
process zůstává PARTIAL. CURRENT/polarita jsou převzaté vstupní podklady, nikoli
runtime execution nebo business ekvivalence. Public API má explicitní pravidla
`business-steps-1`, rozpočty struktury/velikosti a fail-closed chybu s diagnostic.
Staré ProcessView bez group metadata expanduje identicky; graph v1/v2/v3,
existující graph view a flow render se nemění. Nová CLI/migrace není potřebná.

## Skutečné kontroly

- Před implementací actual Javac workspace→T024→T025 vytvořil šest skutečných
  certified operací a skončil RED1FAIL4.78s na chybějícím modulu T026.
- Preliminary actual K1/K2 GREEN2PASS10.20s; první širší matice82PASS9.76s.
- Historická širší matice T026+T023+T025+local operation proofs:265PASS43.62s.
  Běžela **bez sdíleného FIFO locku a bez zaznamenaného pre/post hash receipt**.
  Tento scheduling nedostatek byl přiznán; nejde o zamčený final gate a pouze
  kvůli bookkeeping se stejná matice neopakovala.
- Nezávislý architect source APPROVE exact base a6170c18 / head cff803c43ca3b8d0;
  vlastní pure negativní případ1PASS a1400 SCC porovnání PASS, bez compiler/full.
- Finální **ONE strict full FIFO: 1566PASS/10SKIP v 1532.43s**, XML bez failure/error,
  všech95 T026 případů bez SKIP, obě JVM backend fixture skutečné. Příkaz:
  `flock /workspace/kgmaker-heavy-tests.lock /workspace/kgmaker-venv/bin/python /workspace/business-collapse-proof/run_final.py`.
  Pytest uvnitř: `python -m pytest -q --basetemp=/workspace/business-collapse-proof/full-tmp --junitxml=/workspace/business-collapse-proof/full.xml`.
  Explicitní vlastní PYTHONPATH/worker home, REQUIRE_WORKERS=1 a REQUIRE_K2=1;
  připravený JDK21/Kotlin2.1.10/TypeScript a Maven API/POM cache, Maven není na PATH.
- Preflight ověřil oba `target*/licenses/kotlin/LICENSE.txt`, Worker.class a
  TS/React podklady. Pre/post receipt zachoval HEAD a všech2091
  tracked/compiler/runtime/JAR/lib/LICENSE/fixture/API/POM souborů. Log/XML,
  final-results a manifest jsou v `/workspace/business-collapse-proof`.
- První session-only receipt pokus skončil před pytestem na chybně pevné
  `/usr/bin/node`; Node je v runtime PATH. Runner byl opraven na skutečné
  `shutil.which` a vrácen do FIFO. Nešlo o product RED ani provedený full.
  První samotný RED pokus bez cache selector byl TOOLCHAIN_UNAVAILABLE setup
  ERROR a rovněž není vykazován jako product RED/PASS.

## Acceptance mapování

Všechny názvy níže jsou v `tests/test_t026_collapse_business_steps.py`:

| AC | Konkrétní test |
|---|---|
| AC01 | `test_actual_javac_literal_local_chain_collapses_and_expands_exactly`, `test_ordered_origins_are_topology_not_id_sort_and_no_mutation`, `test_parallel_external_edges_are_distinct_and_exactly_restored`, `test_same_proof_finally_clones_and_unused_exit_are_preserved` |
| AC02 | `test_disconnected_equal_dto_or_label_does_not_create_adjacency`, `test_diamond_and_two_field_writes_are_not_inferred_pure` |
| AC03 | `test_actual_field_call_and_finally_boundaries_remain_visible`, `test_boundaries_never_disappear_or_merge_across_them`, `test_cycle_cannot_be_hidden_inside_a_business_group` |
| AC04 | `test_invalid_stale_foreign_and_opaque_inputs_do_not_borrow_operation_proof`, `test_tampered_expansion_is_rejected_without_mutation`, `test_public_input_budgets_and_malformed_shapes_fail_without_projection_io` |
| AC05 | skutečný unresolved aggregate, scope/context/method/hash/CFG guard, `test_digest_consistent_but_wrong_origin_order_is_not_a_valid_group` |
| AC06 | README, process-paths capability, status, acceptance a tento note; semantic/memory dle CLI |

Příklady API jsou v `docs/process-paths.md`. Čisté funkce neprovádějí I/O,
subprocess/network/DB/model ani aplikaci; nemění vstup nebo poslední artefakt.
Runtime observations, business approval a GH CI NOT_RUN. Explicitní prerequisite
PR65, finální exact-pair review a publikace patří root/code-review workflow;
implementační agent nemerguje. Full SKIP jsou přiznané scoped/optional případy
z XML, nikoli potvrzení chybějícího povinného toolchainu.
