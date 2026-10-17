---
sessionId: session-261006-120611-2vym
---

# Findings

### Overview

The 16 Graphify `INFERRED` edges into `KnowledgeGraph` (`src/kgmaker/model.py:34`) are **all correct**. They are AST type-annotation `uses` links (`origin=ast`, score `0.95`) from `graphify-out/graph.json`, not kgmaker semantic edges and not speculative LLM guesses. Graphify’s report phrasing (“model-reasoned connections”) overstates that.

This request is a question. **No source, graph, or semantic-patch files should be modified.**

### The 16 edges (all verified)

| Source | Graphify context | Source | Verdict |
|---|---|---|---|
| `_code_nodes()` | parameter_type | `confluence.py:350` `graph: KnowledgeGraph` | correct |
| `validate_documents()` | parameter_type | `confluence.py:369` | correct |
| `recall()` | parameter_type | `memory.py:174` | correct |
| `build_capture_episode()` | parameter_type | `memory.py:348-349` two params collapsed | correct |
| `graph_fingerprint()` | parameter_type | `semantic.py:44` | correct |
| `build_semantic_input()` | parameter_type | `semantic.py:55` | correct |
| `validate_semantic_data()` | parameter_type | `semantic.py:99` | correct |
| `build_semantic_update()` | parameter_type | `semantic.py:241` (`previous_graph: KnowledgeGraph \| None` at 245 not a second edge) | correct |
| `apply_semantic_patch()` | parameter_type | `semantic.py:431` | correct |
| `apply_semantic_layer()` | generic_arg | `semantic.py:551` return `tuple[KnowledgeGraph, ...]` plus param `graph: KnowledgeGraph` | correct, incomplete context |
| `save_graph()` | parameter_type | `store.py:16` | correct |
| `load_graph()` | return_type | `store.py:29` `-> KnowledgeGraph \| None` | correct |
| `render_markdown()` | parameter_type | `store.py:37` | correct |
| `render_mermaid()` | parameter_type | `store.py:132` | correct |
| `render_context()` | parameter_type | `store.py:185` | correct |
| `render_bootstrap()` | parameter_type | `store.py:227` | correct |

### Coverage gaps (not false positives)

EXTRACTED constructor `calls` already exist, so Graphify omitted INFERRED `uses` for:

- `merge_into_graph()` — param and return `KnowledgeGraph`; constructor at `confluence.py:455`
- `documentation_check()` — `graph: KnowledgeGraph | None`; constructor at `confluence.py:541`
- `scan_repository()` — `-> KnowledgeGraph`; constructor at `scanner.py:309`

### kgmaker graph vs Graphify

`.kgmaker/graph.json` has only 3 INFERRED name-match `calls` to the class (confluence 455/541, scanner 309). Those three *are* constructors. `.kgmaker/semantic.json` has no KnowledgeGraph inferred edges. `kgmaker status` is stale mainly due to `graphify-out/` files; that does not change these 16 facts.

# Scope

### In scope

- Read-only verification of the 16 Graphify INFERRED `uses` edges involving `KnowledgeGraph`.
- Cross-check against current source in `src/kgmaker/{model,confluence,memory,semantic,store,scanner}.py`.

### Out of scope

- Any source, test, documentation, or `.kgmaker/semantic-patch.json` edits.
- Hand-editing generated graph views (`graphify-out/`, `.kgmaker/GRAPH.md`, `.kgmaker/graph.json`).
- `kgmaker scan` / semantic update / apply (question-only; do not rewrite generated artifacts).
- Verifying the separate Graphify questions about `Node` (12 INFERRED) or `Edge` (3 INFERRED).

# Delivery Steps

### * Step 1: Keep the 16 Graphify uses as verified type annotations
The 16 INFERRED KnowledgeGraph edges remain documented as correct AST type uses; no graph or source rewrite.

- Treat every listed `uses` edge in `graphify-out/graph.json` as verified against the function signatures in confluence, memory, semantic, and store.
- Do not invent extra semantic relationships or edit Graphify/kgmaker generated views.
- Keep `uses` (type mention) distinct from EXTRACTED constructor `calls`.

###   Step 2: Leave constructor-classified type uses as coverage gaps only
merge_into_graph, documentation_check, and scan_repository stay classified as EXTRACTED calls; no inferred-edge backfill.

- Do not add hand-written INFERRED `uses` for those three functions.
- Do not run semantic update/apply/scan for this question.
- If a later task asks to improve Graphify labeling, handle it separately from this verification.

### * Step 3: Update / Follow-up
improve kgmaker to include implementation agent, review agent, test-expert agent, and orchestrator agent, create whole RAG including better data preparation for agents. The goal is to be able to add task to agent, and he will analyze the task, create implementation plan,. implement the plan, test the implementation, do code review, and iterate if necessary.