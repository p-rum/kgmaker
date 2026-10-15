# Repository knowledge graph

> Generated locally by kgmaker. Structural edges come from source text; name-based call edges are heuristic.
> Review semantic conclusions with the repository's Copilot knowledge-graph agent.

- Scope: production; omitted files: 92
- Mode: SOURCE_ONLY; coverage: PARTIAL; no build/test/runtime result is implied.
- Freshness below describes the captured snapshot; use `kgmaker status` to compare current inputs.
- Context: `21e36f00ac4bb19981244a363a0a3b45ed6d74a36ad713a551e9b816cf3bd7db`; content: `2e87b474e5a0330d820c5bcb10fb748c97101aeb2b26a910b3edb4fc30e3168e`; freshness: CONTENT_VERIFIED
- Files indexed: 48
- Symbols and sections: 410
- Internal imports: 145
- Heuristic cross-file calls: 1677
- PostgreSQL tables/columns: 0/0
- Kafka topics: 0
- API endpoints: 0
- TypeScript frontend routes: 0
- Semantic concepts: 0
- Implementation episodes: 0
- Inferred/ambiguous relationships: 1677/0

## Architecture diagram

The diagram groups declarations under their source files and shows detected imports and domain relationships. Heuristic call edges are omitted. An editable standalone Mermaid source is available at `.kgmaker/GRAPH.mmd`.

```mermaid
flowchart LR
  n0["src/kgmaker/__main__.py"]
  n1["src/kgmaker/agent_rules.py"]
  n2["src/kgmaker/agents.py"]
  n3["src/kgmaker/analysis_agent.py"]
  n4["src/kgmaker/analysis_model.py"]
  n5["src/kgmaker/analysis_report.py"]
  n6["src/kgmaker/analysis_validation.py"]
  n7["src/kgmaker/availability.py"]
  n8["src/kgmaker/build_maven.py"]
  n9["src/kgmaker/build_model.py"]
  n10["src/kgmaker/build_runner.py"]
  n11["src/kgmaker/callgraph.py"]
  n12["src/kgmaker/classification.py"]
  n13["src/kgmaker/cli.py"]
  n14["src/kgmaker/confluence.py"]
  n15["src/kgmaker/context.py"]
  n16["src/kgmaker/control_flow.py"]
  n17["src/kgmaker/data_agent.py"]
  n18["src/kgmaker/data_check.py"]
  n19["src/kgmaker/dataflow.py"]
  n20["src/kgmaker/domain.py"]
  n21["src/kgmaker/feature.py"]
  n22["src/kgmaker/feature_cli.py"]
  n23["src/kgmaker/flow.py"]
  n24["src/kgmaker/flyway.py"]
  n25["src/kgmaker/framework.py"]
  n26["src/kgmaker/graph_provider.py"]
  n27["src/kgmaker/inspection.py"]
  n28["src/kgmaker/inspection_cli.py"]
  n29["src/kgmaker/memory.py"]
  n30["src/kgmaker/model.py"]
  n31["src/kgmaker/project_cli.py"]
  n32["src/kgmaker/runtime_evidence.py"]
  n33["src/kgmaker/scanner.py"]
  n34["src/kgmaker/schema_replay.py"]
  n35["src/kgmaker/semantic.py"]
  n36["src/kgmaker/store.py"]
  n37["src/kgmaker/views.py"]
  n38["src/kgmaker/worker_protocol.py"]
  n39["src/kgmaker/workflow.py"]
  n40["src/kgmaker/workspace.py"]
  n41["src/kgmaker/workspace_cli.py"]
  n42{"technology: Kafka"}
  n43{"technology: PostgreSQL"}
  n0 -->|imports| n13
  n3 -->|imports| n1
  n5 -->|imports| n21
  n6 -->|imports| n4
  n6 -->|imports| n7
  n6 -->|imports| n19
  n6 -->|imports| n21
  n6 -->|imports| n33
  n6 -->|imports| n35
  n6 -->|imports| n40
  n7 -->|imports| n4
  n7 -->|imports| n19
  n7 -->|imports| n21
  n8 -->|imports| n4
  n9 -->|imports| n4
  n9 -->|imports| n10
  n9 -->|imports| n12
  n9 -->|imports| n27
  n10 -->|imports| n4
  n10 -->|imports| n27
  n11 -->|imports| n4
  n11 -->|imports| n30
  n11 -->|imports| n37
  n12 -->|imports| n4
  n13 -->|imports| n1
  n13 -->|imports| n2
  n13 -->|imports| n3
  n13 -->|imports| n14
  n13 -->|imports| n15
  n13 -->|imports| n17
  n13 -->|imports| n21
  n13 -->|imports| n28
  n13 -->|imports| n29
  n13 -->|imports| n30
  n13 -->|imports| n31
  n13 -->|imports| n33
  n13 -->|imports| n35
  n13 -->|imports| n36
  n13 -->|imports| n39
  n13 -->|imports| n41
  n14 -->|imports| n30
  n15 -->|imports| n29
  n15 -->|imports| n30
  n15 -->|imports| n33
  n15 -->|imports| n35
  n15 -->|imports| n36
  n15 -->|imports| n39
  n16 -->|imports| n4
  n17 -->|imports| n1
  n18 -->|imports| n4
  n18 -->|imports| n5
  n18 -->|imports| n7
  n18 -->|imports| n19
  n18 -->|imports| n36
  n18 -->|imports| n40
  n19 -->|imports| n30
  n20 -->|imports| n30
  n20 -->|uses_messaging| n42
  n20 -->|connects_to| n43
  n21 -->|imports| n4
  n21 -->|imports| n6
  n21 -->|imports| n7
  n21 -->|imports| n19
  n21 -->|imports| n24
  n21 -->|imports| n26
  n21 -->|imports| n30
  n21 -->|imports| n33
  n21 -->|imports| n34
  n21 -->|imports| n35
  n21 -->|imports| n40
  n22 -->|imports| n4
  n22 -->|imports| n5
  n22 -->|imports| n6
  n22 -->|imports| n7
  n22 -->|imports| n18
  n22 -->|imports| n19
  n22 -->|imports| n33
  n22 -->|imports| n35
  n23 -->|imports| n4
  n23 -->|imports| n11
  n23 -->|imports| n37
  n24 -->|imports| n4
  n25 -->|imports| n4
  n25 -->|imports| n30
  n25 -->|uses_messaging| n42
  n26 -->|imports| n4
  n26 -->|imports| n12
  n26 -->|imports| n27
  n26 -->|imports| n30
  n26 -->|imports| n33
  n26 -->|imports| n36
  n26 -->|imports| n38
  n27 -->|imports| n4
  n27 -->|imports| n12
  n27 -->|imports| n16
  n27 -->|imports| n25
  n27 -->|imports| n30
  n27 -->|imports| n33
  n27 -->|imports| n36
  n27 -->|imports| n38
  n28 -->|imports| n4
  n28 -->|imports| n9
  n28 -->|imports| n26
  n28 -->|imports| n27
  n28 -->|imports| n32
  n28 -->|imports| n36
  n28 -->|imports| n37
  n28 -->|imports| n38
  n28 -->|uses_messaging| n42
  n29 -->|imports| n30
  n30 -->|imports| n12
  n31 -->|imports| n4
  n31 -->|imports| n8
  n31 -->|imports| n9
  n31 -->|imports| n10
  n31 -->|imports| n12
  n31 -->|imports| n28
  n31 -->|imports| n33
  n31 -->|imports| n36
  n31 -->|imports| n37
  n31 -->|imports| n40
  n32 -->|imports| n4
  n32 -->|imports| n30
  n32 -->|imports| n36
  n33 -->|imports| n4
  n33 -->|imports| n12
  n33 -->|imports| n19
  n33 -->|imports| n20
  n33 -->|imports| n30
  n34 -->|imports| n4
  n34 -->|imports| n24
  n34 -->|imports| n30
  n35 -->|imports| n29
  n35 -->|imports| n30
  n36 -->|imports| n4
  n36 -->|imports| n30
  n36 -->|imports| n37
  n37 -->|imports| n30
  n38 -->|imports| n4
  n39 -->|imports| n29
  n40 -->|imports| n4
  n40 -->|imports| n12
  n40 -->|imports| n30
  n40 -->|imports| n34
  n41 -->|imports| n4
  n41 -->|imports| n19
  n41 -->|imports| n34
  n41 -->|imports| n36
  n41 -->|imports| n40
```

## Files and symbols

### `src/kgmaker/__init__.py`
- No declarations extracted.

### `src/kgmaker/__main__.py`
- No declarations extracted.

### `src/kgmaker/agent_rules.py`
- No declarations extracted.

### `src/kgmaker/agents.py`
- No declarations extracted.

### `src/kgmaker/analysis_agent.py`
- No declarations extracted.

### `src/kgmaker/analysis_model.py`
- **class** `AnalysisError` line 31 — `AnalysisError(ValueError)`
- **function** `__init__` line 34 — `__init__(self, message: str, code: int = 2)`
- **function** `canonical` line 37 — `canonical(value: Any)`
- **function** `digest` line 41 — `digest(value: Any)`
- **function** `file_hash` line 45 — `file_hash(path: Path)`
- **function** `safe_path` line 49 — `safe_path(root: Path, value: str)`
- **function** `analysis_dir` line 67 — `analysis_dir(root: Path, analysis_id: str)`
- **function** `read_json` line 73 — `read_json(path: Path)`
- **function** `reject_constant` line 76 — `reject_constant(value: str)`
- **function** `unique` line 78 — `unique(pairs: list)`
- **function** `atomic_write` line 89 — `atomic_write(path: Path, text: str)`
- **function** `write_json` line 103 — `write_json(path: Path, value: Any)`
- **class** `FeatureAnalysis` line 110 — `FeatureAnalysis` — Serializable envelope. Nested contracts are checked by analysis_validation.
- **function** `from_dict` line 115 — `from_dict(cls, data: Any)`
- **function** `to_dict` line 132 — `to_dict(self)`
- **function** `inventory_candidate` line 135 — `inventory_candidate(packet: dict)`

### `src/kgmaker/analysis_report.py`
- **function** `cell` line 16 — `cell(value)`
- **function** `render_report` line 24 — `render_report(candidate: dict, packet: dict, stale: list[str], applied: bool = True, *, data_audit: dict | None = None)`
- **function** `section` line 34 — `section(index)`
- **function** `objects` line 36 — `objects(items)`

### `src/kgmaker/analysis_validation.py`
- **class** `_Anchors` line 17 — `_Anchors(HTMLParser)`
- **function** `__init__` line 20 — `__init__(self)`
- **function** `handle_starttag` line 23 — `handle_starttag(self, tag, attrs)`
- **function** `_location` line 28 — `_location(root: Path, item: dict, packet: dict)`
- **function** `validate_candidate` line 110 — `validate_candidate(root: Path, packet: dict, data: object)`
- **function** `_validate_candidate` line 117 — `_validate_candidate(root: Path, packet: dict, data: object)`
- **function** `strings` line 195 — `strings(item, key, choices=None, nullable=False)`
- **function** `refs` line 202 — `refs(item, key, targets, required=False)`
- **function** `visit` line 293 — `visit(identity)`

### `src/kgmaker/availability.py`
- **function** `observation_staleness` line 14 — `observation_staleness(candidate: dict)`
- **function** `evaluate_proof` line 35 — `evaluate_proof(root, packet, candidate, item, graph=None)`

### `src/kgmaker/build_maven.py`
- **function** `_tag` line 19 — `_tag(name: str)`
- **function** `_text` line 23 — `_text(parent: ET.Element | None, name: str, default: str | None = None)`
- **function** `_children` line 31 — `_children(parent: ET.Element | None, name: str)`
- **function** `_interpolate` line 35 — `_interpolate(value: str | None, properties: dict[str, str])`
- **function** `_parse` line 41 — `_parse(path: Path, root: Path, properties: dict[str, str])`
- **function** `discover` line 79 — `discover(root: Path)`
- **function** `visit` line 90 — `visit(path: Path, inherited: dict[str, str])`

### `src/kgmaker/build_model.py`
- **function** `validate_manifest` line 15 — `validate_manifest(root: Path, manifest: dict)`
- **function** `import_manifest` line 81 — `import_manifest(root: Path, manifest: dict)`
- **function** `inspection_inputs` line 96 — `inspection_inputs(root: Path, manifest: dict, *, context_id: str | None, scope: str)`
- **function** `absolute` line 108 — `absolute(raw)`

### `src/kgmaker/build_runner.py`
- **function** `snapshot` line 21 — `snapshot(root: Path)`
- **function** `tests_report` line 80 — `tests_report(work: Path, phase: str)`
- **function** `run_plan` line 96 — `run_plan(plan: dict, *, cancel_file: Path | None=None)`

### `src/kgmaker/callgraph.py`
- **function** `adjacency` line 9 — `adjacency(graph: KnowledgeGraph, include_candidates=True)`
- **function** `callees` line 41 — `callees(graph, symbol, *, scope="production", include_candidates=False)`
- **function** `callers` line 50 — `callers(graph, symbol, *, scope="production")`
- **function** `path` line 61 — `path(graph, source, target, *, scope="production", max_depth=30, max_nodes=5000, include_candidates=True)`
- **function** `strongly_connected` line 89 — `strongly_connected(graph: KnowledgeGraph)`

### `src/kgmaker/classification.py`
- **class** `Classification` line 20 — `Classification`
- **class** `Classifier` line 26 — `Classifier`
- **function** `__init__` line 29 — `__init__(self, root: Path, model: dict | None = None, strict: bool = False)`
- **function** `classify` line 58 — `classify(self, path: str)`

### `src/kgmaker/cli.py`
- **function** `_write_if_missing` line 243 — `_write_if_missing(path: Path, text: str, force: bool = False)`
- **function** `init` line 251 — `init(root: Path, force: bool = False)`
- **function** `scan` line 295 — `scan(root: Path, generate_docs: bool = True, confluence_dir: str | None = None, report: str | None = None)`
- **function** `status` line 327 — `status(root: Path)`
- **function** `check` line 351 — `check(root: Path)`
- **function** `docs` line 381 — `docs(root: Path, action: str | None = None, confluence_dir: str | None = None, report: str | None = None)`
- **function** `semantic_prepare` line 405 — `semantic_prepare(root: Path)`
- **function** `semantic_extract` line 419 — `semantic_extract(root: Path, base_ref: str, note_path: str | None = None, token_budget: int | None = None)`
- **function** `semantic_update` line 470 — `semantic_update(root: Path, base_ref: str, note_path: str | None = None, token_budget: int | None = None)`
- **function** `semantic_apply` line 551 — `semantic_apply(root: Path)`
- **function** `semantic_validate` line 571 — `semantic_validate(root: Path)`
- **function** `impact` line 586 — `impact(root: Path, changed_files: list[str])`
- **function** `query` line 658 — `query(root: Path, terms: str, limit: int = 10, scope: str = "production")`
- **function** `memory_capture` line 675 — `memory_capture(root: Path, base: str, validation_values: list[str])`
- **function** `memory_recall` line 732 — `memory_recall(root: Path, terms: str, limit: int = 8, token_budget: int = 1_000)`
- **function** `task_add` line 752 — `task_add(root: Path, request: str, title: str | None, max_iterations: int)`
- **function** `task_list` line 763 — `task_list(root: Path, status_filter: str | None)`
- **function** `task_show` line 774 — `task_show(root: Path, task_id_value: str)`
- **function** `task_advance` line 784 — `task_advance(root: Path, task_id_value: str, target: str)`
- **function** `task_stop` line 794 — `task_stop(root: Path, task_id_value: str, reason: str)`
- **function** `task_record` line 804 — `task_record(root: Path, task_id_value: str, role: str, artifact_path: Path)`
- **function** `task_context` line 819 — `task_context(root: Path, task_id_value: str, role: str, token_budget: int)`
- **function** `hook_context` line 829 — `hook_context(root: Path, token_budget: int | None = None)`
- **function** `build_parser` line 849 — `build_parser`
- **function** `main` line 979 — `main`

### `src/kgmaker/confluence.py`
- **function** `_norm` line 30 — `_norm(value: str)`
- **function** `_safe_rel` line 34 — `_safe_rel(path: str)`
- **function** `_sha` line 38 — `_sha(path: Path)`
- **class** `ConfluenceDocument` line 49 — `ConfluenceDocument`
- **class** `DocumentationAssertion` line 63 — `DocumentationAssertion`
- **class** `_ExportHTMLParser` line 80 — `_ExportHTMLParser(HTMLParser)`
- **function** `__init__` line 86 — `__init__(self)`
- **function** `_attrs` line 105 — `_attrs(self, attrs: list[tuple[str, str | None]])`
- **function** `handle_starttag` line 108 — `handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]])`
- **function** `handle_endtag` line 139 — `handle_endtag(self, tag: str)`
- **function** `handle_data` line 169 — `handle_data(self, data: str)`
- **function** `text` line 183 — `text(self)`
- **function** `_resolve_local_ref` line 187 — `_resolve_local_ref(value: str, current_file: str)`
- **function** `_parse_mermaid` line 194 — `_parse_mermaid(source: str)`
- **function** `_parse_drawio` line 209 — `_parse_drawio(path: Path, source_file: str)`
- **function** `_parse_svg` line 232 — `_parse_svg(path: Path)`
- **function** `_document_from_html` line 243 — `_document_from_html(path: Path, export_root: Path, digest: str)`
- **function** `_load_cache` line 262 — `_load_cache(root: Path)`
- **function** `_write_cache` line 270 — `_write_cache(root: Path, payload: dict[str, Any])`
- **function** `discover_export` line 276 — `discover_export(export_root: Path)`
- **function** `ingest_export` line 280 — `ingest_export(export_root: Path, repository_root: Path)`
- **function** `_assertions_from_document` line 319 — `_assertions_from_document(doc: ConfluenceDocument)`
- **function** `_code_nodes` line 348 — `_code_nodes(graph: KnowledgeGraph)`
- **function** `_missing_category` line 355 — `_missing_category(assertion: DocumentationAssertion)`
- **function** `validate_documents` line 367 — `validate_documents(documents: list[ConfluenceDocument], graph: KnowledgeGraph)`
- **function** `merge_into_graph` line 415 — `merge_into_graph(graph: KnowledgeGraph, documents: list[ConfluenceDocument], attachments: list[dict[str, Any]], assertions: list[DocumentationAssertion])`
- **function** `render_report` line 456 — `render_report(assertions: list[DocumentationAssertion], report_path: Path, export_root: Path, revision: str = "working tree")`
- **function** `persist_validation_index` line 484 — `persist_validation_index(root: Path, assertions: list[DocumentationAssertion])`
- **function** `resolve_confluence_dir` line 495 — `resolve_confluence_dir(root: Path, cli_value: str | None)`
- **function** `documentation_check` line 529 — `documentation_check(root: Path, confluence_dir: str | None = None, report: str | None = None, graph: KnowledgeGraph | None = None)`

### `src/kgmaker/context.py`
- **class** `ContextError` line 28 — `ContextError(ValueError)`
- **function** `_terms` line 32 — `_terms(text: str)`
- **function** `_origin` line 36 — `_origin(kind: str)`
- **function** `_node_payload` line 44 — `_node_payload(node: Any, include_summary: bool = True)`
- **function** `_score_node` line 58 — `_score_node(node: Any, terms: list[str])`
- **function** `_rank_nodes` line 64 — `_rank_nodes(graph: KnowledgeGraph, terms: list[str], limit: int)`
- **function** `_neighbors` line 80 — `_neighbors(graph: KnowledgeGraph, seeds: list[Any], limit: int)`
- **function** `_episode_items` line 104 — `_episode_items(graph: KnowledgeGraph, terms: list[str], limit: int)`
- **function** `_semantic_hits` line 135 — `_semantic_hits(graph: KnowledgeGraph, root: Path, terms: list[str], limit: int)`
- **function** `_impact_items` line 164 — `_impact_items(graph: KnowledgeGraph, seed_paths: list[str], limit: int)`
- **function** `_compact_artifact` line 218 — `_compact_artifact(artifact: dict[str, Any])`
- **function** `_query_terms` line 237 — `_query_terms(task: dict[str, Any])`
- **function** `_token_estimate` line 249 — `_token_estimate(payload: dict[str, Any])`
- **function** `_truncate` line 254 — `_truncate(packet: dict[str, Any], token_budget: int)`
- **function** `_select_prior` line 275 — `_select_prior(task: dict[str, Any], role: str)`
- **function** `_graph_status` line 291 — `_graph_status(root: Path, graph: KnowledgeGraph | None)`
- **function** `_test_nodes` line 303 — `_test_nodes(graph: KnowledgeGraph, terms: list[str], limit: int)`
- **function** `_render_markdown` line 422 — `_render_markdown(packet: dict[str, Any], task: dict[str, Any])`

### `src/kgmaker/control_flow.py`
- **class** `Environment` line 17 — `Environment`
- **class** `Builder` line 23 — `Builder`
- **function** `__init__` line 26 — `__init__(self, method: str, context_id: str, *, max_blocks: int = 3000, max_depth: int = 150)`
- **function** `node` line 34 — `node(self, kind, label, ir, env)`
- **function** `edge` line 46 — `edge(self, source, target, kind="normal", **metadata)`
- **function** `computation` line 52 — `computation(self, ir, destination, env, kind="basic_block", label=None)`
- **function** `abrupt` line 59 — `abrupt(self, destination, env, *, keep=0, reason="return", depth=0)`
- **function** `condition` line 69 — `condition(self, ir, when_true, when_false, env, depth)`
- **function** `emit` line 91 — `emit(self, ir, destination, env, depth=0)`
- **function** `boundary` line 202 — `boundary(self, ir, reason, env)`
- **function** `build` line 206 — `build(self, body: dict)`
- **function** `from_body` line 219 — `from_body(record: dict, **limits)`

### `src/kgmaker/data_agent.py`
- No declarations extracted.

### `src/kgmaker/data_check.py`
- **function** `_object` line 19 — `_object(value, required, optional=())`
- **function** `_array` line 24 — `_array(value, label)`
- **function** `_ids` line 29 — `_ids(value, allowed, label)`
- **function** `data_check` line 35 — `data_check(root: Path, analysis_id: str, specification: dict)`
- **function** `reference_evidence` line 54 — `reference_evidence(reference, identity)`

### `src/kgmaker/dataflow.py`
- **function** `masked` line 32 — `masked(text: str)`
- **function** `closing` line 38 — `closing(text: str, start: int, opening='(', ending=')')`
- **function** `parts` line 50 — `parts(text: str)`
- **class** `Extraction` line 57 — `Extraction`
- **function** `extract_dataflow` line 61 — `extract_dataflow(sources: dict[str, str])`
- **function** `node` line 68 — `node(path, kind, qualified, offset, signature=None, summary=None)`
- **function** `issue` line 78 — `issue(path, offset, reason)`
- **function** `relation` line 81 — `relation(source, target, kind, path, offset, evidence)`
- **function** `walk` line 146 — `walk(value, pointer='')`
- **function** `resolve` line 207 — `resolve(token)`
- **function** `expression` line 218 — `expression(value, destination, statement_offset)`
- **function** `impact_paths` line 283 — `impact_paths(graph: KnowledgeGraph, entity: str, max_depth: int = 20)`

### `src/kgmaker/domain.py`
- **technology** `Kafka`
- **technology** `PostgreSQL`
- **function** `_line` line 65 — `_line(text: str, offset: int)`
- **function** `_unquote_identifier` line 69 — `_unquote_identifier(value: str)`
- **function** `_canon` line 73 — `_canon(value: str)`
- **function** `_node_id` line 77 — `_node_id(kind: str, key: str)`
- **function** `_shared_node` line 81 — `_shared_node(kind: str, key: str, display: str, path: str, line: int | None = None, summary: str | None = None)`
- **function** `_split_sql_items` line 85 — `_split_sql_items(body: str)`
- **function** `_sql_objects` line 108 — `_sql_objects(text: str, path: str, file_id: str)`
- **function** `_entity_edges` line 137 — `_entity_edges(text: str, path: str, symbols: list[Node], tables: dict[str, Node], columns: dict[str, Node])`
- **function** `_string_literals` line 191 — `_string_literals(value: str)`
- **function** `_kafka_references` line 195 — `_kafka_references(text: str, path: str, file_id: str)`
- **function** `add` line 200 — `add(topic: str, offset: int, relation: str, evidence: str)`
- **function** `normalize_api_path` line 230 — `normalize_api_path(path: str)`
- **function** `_api_node` line 241 — `_api_node(method: str, path: str, source: str, line: int | None, operation: str | None = None)`
- **function** `_mapping_path` line 254 — `_mapping_path(args: str)`
- **function** `_openapi_yaml` line 259 — `_openapi_yaml(text: str, path: str, file_id: str)`
- **function** `flush` line 271 — `flush(offset: int)`
- **function** `_openapi_json` line 302 — `_openapi_json(text: str, path: str, file_id: str)`
- **function** `_api_references` line 324 — `_api_references(text: str, path: str, language: str, file_id: str)`
- **function** `add` line 329 — `add(method: str, endpoint_path: str, offset: int, relation: str, evidence: str)`
- **function** `_typescript_routes` line 392 — `_typescript_routes(path: str, text: str, file_id: str)`
- **function** `_technology_nodes` line 426 — `_technology_nodes(text: str, path: str, file_id: str)`
- **function** `extract_domain` line 440 — `extract_domain(path: str, text: str, language: str, file_id: str, symbols: list[Node])`
- **function** `extract_openapi` line 475 — `extract_openapi(path: str, text: str, file_id: str)`
- **function** `connect_persistence` line 484 — `connect_persistence(symbols_by_file: dict[str, list[Node]], text_by_file: dict[str, str], nodes: list[Node])`
- **function** `merge_domain_nodes` line 515 — `merge_domain_nodes(nodes: list[Node])`

### `src/kgmaker/feature.py`
- **function** `source_inventory` line 22 — `source_inventory(root: Path)`
- **function** `current_graph` line 53 — `current_graph(root: Path, workspace: Path | None = None)`
- **function** `attach_schema` line 71 — `attach_schema(graph, schema, root: Path | None = None)`
- **function** `source_path` line 102 — `source_path(root: Path, key: str, packet: dict)`
- **function** `graph_for_packet` line 109 — `graph_for_packet(root: Path, packet: dict)`
- **function** `snapshot` line 114 — `snapshot(root: Path, *, workspace: Path | None = None, _details: dict | None = None, _persist_cache: bool = False)`
- **function** `packet_identity` line 157 — `packet_identity(packet: dict)`
- **function** `load_packet` line 161 — `load_packet(root: Path, analysis_id: str)`
- **function** `freshness` line 170 — `freshness(root: Path, packet: dict)`
- **function** `prepare` line 189 — `prepare(root: Path, requirement: str, analysis_id: str, token_budget: int = 8000, *, _answers: list | None = None, workspace: Path | None = None)`
- **function** `validate` line 272 — `validate(root: Path, analysis_id: str, candidate: dict)`
- **function** `apply` line 292 — `apply(root: Path, analysis_id: str, candidate: dict)`
- **function** `status` line 310 — `status(root: Path, analysis_id: str)`
- **function** `revise` line 319 — `revise(root: Path, analysis_id: str, answers: dict)`

### `src/kgmaker/feature_cli.py`
- **function** `register` line 11 — `register(subparsers)`
- **function** `run` line 39 — `run(args)`
- **function** `query_analysis` line 123 — `query_analysis(root: Path, analysis_id: str, terms: str, limit: int)`
- **function** `impact_entity` line 144 — `impact_entity(root: Path, entity: str, output_format: str)`

### `src/kgmaker/flow.py`
- **function** `_label` line 10 — `_label(value)`
- **function** `control_flow` line 14 — `control_flow(graph, entry, *, scope="production", max_nodes=500, representation="SOURCE")`
- **function** `process` line 56 — `process(graph, entry, *, scope="production", max_depth=3, max_nodes=500)`
- **function** `expand` line 76 — `expand(method, depth, ancestry, prefix)`
- **function** `mermaid` line 122 — `mermaid(report)`
- **function** `markdown` line 143 — `markdown(report)`

### `src/kgmaker/flyway.py`
- **function** `version` line 22 — `version(value: str)`
- **function** `configuration` line 31 — `configuration(root: Path, overrides: dict | None = None)`
- **function** `migration_plan` line 148 — `migration_plan(root: Path, overrides: dict | None = None)`

### `src/kgmaker/framework.py`
- **function** `_simple` line 39 — `_simple(value: str)`
- **function** `_line` line 43 — `_line(text: str, offset: int)`
- **function** `_args` line 47 — `_args(annotation: str)`
- **function** `_string_arg` line 52 — `_string_arg(args: str, names: tuple[str, ...] = ("name", "value", "path"))`
- **function** `_annotation_values` line 61 — `_annotation_values(text: str, line: int)`
- **function** `_imports` line 77 — `_imports(text: str)`
- **function** `_allowed_annotation` line 81 — `_allowed_annotation(name: str, imports: set[str], families: tuple[str, ...])`
- **function** `_annotation_map` line 92 — `_annotation_map(symbol: dict[str, Any], source: str)`
- **function** `_annotation` line 113 — `_annotation(values: list[tuple[str, str]], name: str)`
- **function** `_path_text` line 117 — `_path_text(root: Path, path: str)`
- **function** `_node_id` line 126 — `_node_id(prefix: str, payload: Any)`
- **function** `augment_framework_graph` line 130 — `augment_framework_graph(root: Path, graph: KnowledgeGraph, context: dict[str, Any])`
- **function** `evidence_for` line 152 — `evidence_for(kind: str, source: str, target: str, relation: str, path: str, line: int | None, detail: str)`
- **function** `symbol_node` line 187 — `symbol_node(item: dict[str, Any])`
- **function** `bean_selection` line 190 — `bean_selection(values: list[tuple[str, str]])`
- **function** `class_for` line 205 — `class_for(item: dict[str, Any])`

### `src/kgmaker/graph_provider.py`
- **function** `validate_compiler_snapshot` line 8 — `validate_compiler_snapshot(root: Path, graph: KnowledgeGraph)`
- **function** `retain_compiler_layer` line 39 — `retain_compiler_layer(root: Path, syntax: KnowledgeGraph)`

### `src/kgmaker/inspection.py`
- **function** `artifact_hash` line 23 — `artifact_hash(path: Path)`
- **function** `worker_home` line 36 — `worker_home(path: Path | None = None)`
- **function** `_jvm_worker_jar` line 44 — `_jvm_worker_jar(home: Path)`
- **function** `command` line 67 — `command(language: str, home: Path | None = None)`
- **function** `distribution` line 82 — `distribution(language: str, home=None)`
- **function** `sanitize` line 88 — `sanitize(value, *, key="")`
- **function** `validate_response` line 119 — `validate_response(response: dict, selected_context: dict)`
- **function** `proof` line 159 — `proof(fact: dict, kind: str, *, source: str, target: str, relation: str)`
- **function** `relation` line 172 — `relation(source, target, name, fact, kind="SYMBOL_RESOLVED")`

### `src/kgmaker/inspection_cli.py`
- **function** `common` line 11 — `common(parser)`
- **function** `register` line 18 — `register(sub)`
- **function** `indexed` line 69 — `indexed(args)`
- **function** `run` line 93 — `run(args)`

### `src/kgmaker/memory.py`
- **class** `EpisodeValidationError` line 23 — `EpisodeValidationError(ValueError)`
- **class** `CaptureError` line 27 — `CaptureError(ValueError)`
- **function** `_canonical_payload` line 31 — `_canonical_payload(record: dict[str, Any])`
- **function** `episode_id` line 35 — `episode_id(record: dict[str, Any])`
- **function** `_safe_path` line 43 — `_safe_path(value: Any, field: str)`
- **function** `_string_list` line 52 — `_string_list(value: Any, field: str, limit: int = 2_000)`
- **function** `validate_episode` line 62 — `validate_episode(record: Any, index: int | None = None)`
- **function** `episode_freshness` line 130 — `episode_freshness(record: dict[str, Any], current_files: dict[str, str])`
- **function** `project_episode` line 145 — `project_episode(record: dict[str, Any], current_nodes: set[str], current_files: dict[str, str])`
- **function** `_terms` line 158 — `_terms(text: str)`
- **function** `_text_score` line 162 — `_text_score(query: list[str], exact_query: str, fields: list[str])`
- **function** `parse_validations` line 255 — `parse_validations(values: list[str])`
- **function** `_git` line 275 — `_git(root: Path, *args: str)`
- **function** `is_sensitive_path` line 285 — `is_sensitive_path(path: str)`
- **function** `_sensitive_path` line 298 — `_sensitive_path(path: str)`
- **function** `_changed_paths` line 302 — `_changed_paths(root: Path, base_commit: str)`
- **function** `_file_hash` line 332 — `_file_hash(root: Path, path: str)`
- **function** `_node_payload` line 344 — `_node_payload(node: Node)`

### `src/kgmaker/model.py`
- **class** `Node` line 10 — `Node`
- **class** `Edge` line 27 — `Edge`
- **class** `KnowledgeGraph` line 42 — `KnowledgeGraph`
- **function** `migrate_legacy` line 56 — `migrate_legacy(self)`
- **function** `to_dict` line 71 — `to_dict(self)`
- **function** `from_dict` line 90 — `from_dict(cls, data: dict[str, Any])`

### `src/kgmaker/project_cli.py`
- **function** `common` line 13 — `common(parser)`
- **function** `register` line 21 — `register(sub)`
- **function** `run` line 69 — `run(args)`

### `src/kgmaker/runtime_evidence.py`
- **function** `_check_hashes` line 16 — `_check_hashes(root: Path, context: dict[str, Any], manifest: dict[str, Any])`
- **function** `validate_manifest` line 36 — `validate_manifest(graph: KnowledgeGraph, root: Path, manifest: dict[str, Any])`
- **function** `import_manifest` line 69 — `import_manifest(root: Path, manifest: dict[str, Any], *, graph: KnowledgeGraph | None = None)`

### `src/kgmaker/scanner.py`
- **function** `_safe_text` line 78 — `_safe_text(path: Path)`
- **function** `_file_digest` line 87 — `_file_digest(text: str)`
- **function** `_stable_id` line 91 — `_stable_id(kind: str, path: str, name: str, line: int | None = None)`
- **function** `_line_for` line 96 — `_line_for(text: str, offset: int)`
- **function** `_doc_for_line` line 100 — `_doc_for_line(lines: list[str], index: int)`
- **function** `_extract_symbols` line 108 — `_extract_symbols(text: str, path: str, language: str)`
- **function** `_imports` line 164 — `_imports(text: str, language: str)`
- **function** `_candidate_paths` line 182 — `_candidate_paths(root: Path, source: str, import_name: str, known_files: set[str])`
- **function** `_should_skip` line 211 — `_should_skip(path: Path, relative: Path)`
- **function** `_candidate_files` line 222 — `_candidate_files(root: Path, project_model: dict | None = None)`
- **function** `scan_repository` line 246 — `scan_repository(root: Path, *, project_model: dict | None = None, strict: bool = False)`

### `src/kgmaker/schema_replay.py`
- **function** `statements` line 19 — `statements(text: str)`
- **function** `identifier` line 83 — `identifier(token: str)`
- **function** `groups` line 91 — `groups(tokens: list[str])`
- **class** `Replay` line 103 — `Replay`
- **function** `__init__` line 106 — `__init__(self, config: dict)`
- **function** `name` line 111 — `name(self, tokens, offset=0)`
- **function** `key` line 121 — `key(kind, name)`
- **function** `create` line 123 — `create(self, kind, name, **attributes)`
- **function** `get` line 136 — `get(self, kind, name)`
- **function** `change` line 142 — `change(self, item)`
- **function** `drop` line 146 — `drop(self, kind, name, optional=False)`
- **function** `rename` line 156 — `rename(self, kind, name, target)`
- **function** `constraint` line 180 — `constraint(self, table, tokens, fallback)`
- **function** `column` line 206 — `column(self, table, tokens)`
- **function** `apply` line 231 — `apply(self, tokens)`
- **function** `reconstruct` line 394 — `reconstruct(root: Path, config: dict | None = None, *, use_cache: bool = True)`
- **function** `schema_diff` line 463 — `schema_diff(root: Path, config: dict, start: str, end: str)`
- **function** `graph_entities` line 472 — `graph_entities(schema: dict)`
- **function** `schema_mappings` line 510 — `schema_mappings(root: Path, schema: dict, graph)`

### `src/kgmaker/semantic.py`
- **class** `SemanticValidationError` line 32 — `SemanticValidationError(ValueError)`
- **function** `concept_id` line 36 — `concept_id(source_file: str, name: str)`
- **function** `graph_fingerprint` line 42 — `graph_fingerprint(graph: KnowledgeGraph)`
- **function** `build_semantic_input` line 54 — `build_semantic_input(graph: KnowledgeGraph)`
- **function** `_positive_line` line 76 — `_positive_line(value: Any, field: str)`
- **function** `_check_line` line 84 — `_check_line(root: Path, source_file: str, line: int | None, field: str, line_counts: dict[str, int])`
- **function** `validate_semantic_data` line 99 — `validate_semantic_data(data: Any, graph: KnowledgeGraph, root: Path)`
- **function** `_run_git` line 226 — `_run_git(root: Path, *args: str, check: bool = True)`
- **function** `_is_sensitive_path` line 241 — `_is_sensitive_path(path: str)`
- **function** `apply_semantic_patch` line 439 — `apply_semantic_patch(patch: Any, update: Any, graph: KnowledgeGraph, root: Path)`
- **function** `apply_semantic_layer` line 561 — `apply_semantic_layer(graph: KnowledgeGraph, root: Path)`

### `src/kgmaker/store.py`
- **function** `query_nodes` line 14 — `query_nodes(graph: KnowledgeGraph, terms: str, limit: int = 10, scope: str = "all")`
- **function** `save_graph` line 37 — `save_graph(graph: KnowledgeGraph, root: Path, generate_docs: bool = True)`
- **function** `load_graph` line 54 — `load_graph(root: Path)`
- **function** `render_markdown` line 62 — `render_markdown(graph: KnowledgeGraph, scope: str = "production")`
- **function** `render_mermaid` line 171 — `render_mermaid(graph: KnowledgeGraph, scope: str = "production")`
- **function** `render_context` line 224 — `render_context(graph: KnowledgeGraph, limit: int = 8_000, root: Path | None = None)`
- **function** `render_bootstrap` line 270 — `render_bootstrap(graph: KnowledgeGraph, limit: int = 8_000)`
- **function** `_edge_details` line 292 — `_edge_details(edge)`

### `src/kgmaker/views.py`
- **function** `project` line 17 — `project(graph: KnowledgeGraph, scope: str = "production", *, view: str = "architecture", context_id: str | None = None)`
- **function** `rank` line 62 — `rank(graph: KnowledgeGraph, entry: str | None = None, profile: str = "execution", scope: str = "production")`

### `src/kgmaker/worker_protocol.py`
- **class** `WorkerError` line 18 — `WorkerError(AnalysisError)`
- **function** `__init__` line 21 — `__init__(self, message: str, status: str, stderr: str = "")`
- **function** `_terminate` line 24 — `_terminate(process)`
- **function** `unique` line 102 — `unique(pairs)`
- **function** `reject_constant` line 109 — `reject_constant(value)`
- **function** `handshake` line 122 — `handshake(argv: list[str], *, cwd: Path, timeout: float = 30)`

### `src/kgmaker/workflow.py`
- **class** `WorkflowError` line 62 — `WorkflowError(ValueError)`
- **function** `_canonical` line 66 — `_canonical(record: dict[str, Any], exclude: set[str])`
- **function** `task_id` line 71 — `task_id(title: str, request: str, max_iterations: int, base_commit: str | None)`
- **function** `artifact_id` line 80 — `artifact_id(record: dict[str, Any])`
- **function** `packet_id` line 85 — `packet_id(record: dict[str, Any])`
- **function** `_safe_path` line 90 — `_safe_path(value: Any, field: str)`
- **function** `_string_list` line 101 — `_string_list(value: Any, field: str, limit: int = 200, item_limit: int = 500)`
- **function** `_bounded_text` line 111 — `_bounded_text(value: Any, field: str, limit: int, allow_empty: bool = False)`
- **function** `_git_head` line 119 — `_git_head(root: Path)`
- **function** `_non_negative_int` line 139 — `_non_negative_int(value: Any, field: str)`
- **function** `_artifact_fields` line 145 — `_artifact_fields(role: str, phase: str)`
- **function** `_validate_plan_steps` line 157 — `_validate_plan_steps(steps: Any, field: str)`
- **function** `_validate_validations` line 177 — `_validate_validations(values: Any, field: str)`
- **function** `_validate_findings` line 197 — `_validate_findings(values: Any, field: str)`
- **function** `validate_artifact` line 220 — `validate_artifact(record: Any, index: int | None = None)`
- **function** `validate_task` line 271 — `validate_task(record: Any)`
- **function** `legal_transitions` line 328 — `legal_transitions(task: dict[str, Any])`
- **function** `normalize_task_id` line 390 — `normalize_task_id(value: str)`
- **function** `task_path` line 404 — `task_path(root: Path, task_id_value: str)`
- **function** `_atomic_write` line 409 — `_atomic_write(path: Path, payload: dict[str, Any])`
- **function** `save_task` line 423 — `save_task(root: Path, task: dict[str, Any])`
- **function** `load_task` line 431 — `load_task(root: Path, task_id_value: str)`
- **function** `list_tasks` line 440 — `list_tasks(root: Path, status: str | None = None)`
- **function** `advance_task` line 473 — `advance_task(root: Path, task_id_value: str, target: str)`
- **function** `stop_task` line 494 — `stop_task(root: Path, task_id_value: str, reason: str)`
- **function** `_merge_paths` line 505 — `_merge_paths(existing: list[str], extra: list[str])`
- **function** `packet_path` line 515 — `packet_path(root: Path, task: dict[str, Any], role: str, iteration: int)`
- **function** `record_artifact` line 521 — `record_artifact(root: Path, task_id_value: str, role: str, payload: dict[str, Any])`

### `src/kgmaker/workspace.py`
- **function** `qualified` line 14 — `qualified(repo: str, identity: str)`
- **function** `split_id` line 18 — `split_id(identity: str)`
- **function** `source_key` line 28 — `source_key(repo: str, path: str)`
- **function** `load_workspace` line 32 — `load_workspace(path: Path)`
- **function** `source_path` line 91 — `source_path(packet: dict, key: str)`
- **function** `snapshot_workspace` line 101 — `snapshot_workspace(manifest: Path, *, cache_root: Path | None = None, persist_cache: bool = False)`

### `src/kgmaker/workspace_cli.py`
- **function** `register_schema` line 6 — `register_schema(subparsers)`
- **function** `schema_command` line 23 — `schema_command(args)`
- **function** `workspace_command` line 54 — `workspace_command(args)`

### `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java`
- **data_field** `Bytecode.state` line 15 — `State`
- **data_field** `Bytecode.loader` line 16 — `URLClassLoader`
- **function** `Bytecode` line 21 — `Bytecode(State state)`

### `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java`
- **data_field** `JavaFrontend.state` line 14 — `State`
- **data_field** `JavaFrontend.trees` line 15 — `Trees`
- **data_field** `JavaFrontend.elements` line 16 — `Elements`
- **data_field** `JavaFrontend.types` line 16 — `Types`
- **data_field** `JavaFrontend.unit` line 16 — `CompilationUnitTree`
- **data_field** `JavaFrontend.file` line 17 — `Path`
- **data_field** `JavaFrontend.source` line 17 — `String`
- **function** `JavaFrontend` line 20 — `JavaFrontend(State state)`
- **data_field** `Visitor.caller` line 115 — `String`
- **type** `Visitor` line 115 — `Visitor(extends TreePathScanner<Void,Void>)`

### `workers/jvm/src/main/java/org/kgmaker/worker/State.java`
- **data_field** `State.root` line 12 — `Path`
- **function** `State` line 21 — `State(Map<String,Object> request)`

### `workers/jvm/src/main/kotlin/org/kgmaker/worker/JvmWorker.kt`
- **function** `handshake` line 8 — `handshake`
- **function** `main` line 14 — `main`

### `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`
- **data_field** `KotlinFrontend.state` line 30 — `State`
- **type** `KotlinFrontend` line 30 — `KotlinFrontend((private val state: State))`
- **function** `loc` line 35 — `loc(element: PsiElement)`
- **function** `line` line 41 — `line(offset: Int)=text.take(offset)`
- **function** `column` line 42 — `column(offset: Int)=offset-(text.lastIndexOf('\n', (offset-1).coerceAtLeast(0)))`
- **function** `owner` line 46 — `owner(descriptor: DeclarationDescriptor)=mapper.mapOwner(descriptor).internalName.replace('/','.')`
- **function** `constant` line 47 — `constant(value: ConstantValue<*>): Any? = when(value)`
- **function** `annotation` line 57 — `annotation(value: org.jetbrains.kotlin.descriptors.annotations.AnnotationDescriptor)`
- **function** `annotations` line 59 — `annotations(descriptor: DeclarationDescriptor)=descriptor.annotations.map(::annotation)`
- **function** `method` line 60 — `method(descriptor: FunctionDescriptor, element: PsiElement? = null)`
- **function** `property` line 69 — `property(descriptor: PropertyDescriptor, element: PsiElement?=null)`
- **function** `analyze` line 75 — `analyze(files: List<Path>)`
- **data_field** `Visitor.caller` line 102 — `String`
- **function** `visitClassOrObject` line 103 — `visitClassOrObject(declaration: KtClassOrObject)`
- **function** `visitNamedFunction` line 112 — `visitNamedFunction(function: KtNamedFunction)`
- **function** `visitSecondaryConstructor` line 126 — `visitSecondaryConstructor(constructor: KtSecondaryConstructor)`
- **function** `visitLambdaExpression` line 135 — `visitLambdaExpression(expression: KtLambdaExpression)`
- **function** `visitProperty` line 144 — `visitProperty(declaration: KtProperty)`
- **function** `visitParameter` line 153 — `visitParameter(parameter: KtParameter)`
- **function** `visitCallExpression` line 161 — `visitCallExpression(expression: KtCallExpression)`
- **function** `visitCallableReferenceExpression` line 181 — `visitCallableReferenceExpression(expression: KtCallableReferenceExpression)`
- **function** `visitSimpleNameExpression` line 188 — `visitSimpleNameExpression(expression: KtSimpleNameExpression)`
- **function** `callsIn` line 201 — `callsIn(element: KtExpression)`
- **function** `visitLambdaExpression` line 204 — `visitLambdaExpression(expression: KtLambdaExpression)`
- **function** `visitNamedFunction` line 205 — `visitNamedFunction(function: KtNamedFunction)`
- **function** `visitCallExpression` line 206 — `visitCallExpression(expression: KtCallExpression) {calls[expression]?.let(result::add);super.visitCallExpression(expression)`
- **function** `label` line 210 — `label(element: PsiElement)=element.text.replace(Regex("\"(?:\\\\.|[^\"\\\\])*\""),"\"…\"").take(300)`
- **function** `ir` line 211 — `ir(expression: KtExpression?)`

## Implementation history

- No implementation episodes recorded.

## Internal relationships

- `src/kgmaker/__main__.py` imports `src/kgmaker/cli.py` (.cli)
- `src/kgmaker/analysis_agent.py` imports `src/kgmaker/agent_rules.py` (.agent_rules)
- `src/kgmaker/analysis_report.py` imports `src/kgmaker/feature.py` (.feature)
- `src/kgmaker/analysis_validation.py` imports `src/kgmaker/analysis_model.py` (.analysis_model)
- `src/kgmaker/analysis_validation.py` imports `src/kgmaker/availability.py` (.availability)
- `src/kgmaker/analysis_validation.py` imports `src/kgmaker/dataflow.py` (.dataflow)
- `src/kgmaker/analysis_validation.py` imports `src/kgmaker/feature.py` (.feature)
- `src/kgmaker/analysis_validation.py` imports `src/kgmaker/scanner.py` (.scanner)
- `src/kgmaker/analysis_validation.py` imports `src/kgmaker/semantic.py` (.semantic)
- `src/kgmaker/analysis_validation.py` imports `src/kgmaker/workspace.py` (.workspace)
- `src/kgmaker/availability.py` imports `src/kgmaker/analysis_model.py` (.analysis_model)
- `src/kgmaker/availability.py` imports `src/kgmaker/dataflow.py` (.dataflow)
- `src/kgmaker/availability.py` imports `src/kgmaker/feature.py` (.feature)
- `src/kgmaker/build_maven.py` imports `src/kgmaker/analysis_model.py` (.analysis_model)
- `src/kgmaker/build_model.py` imports `src/kgmaker/analysis_model.py` (.analysis_model)
- `src/kgmaker/build_model.py` imports `src/kgmaker/build_runner.py` (.build_runner)
- `src/kgmaker/build_model.py` imports `src/kgmaker/classification.py` (.classification)
- `src/kgmaker/build_model.py` imports `src/kgmaker/inspection.py` (.inspection)
- `src/kgmaker/build_runner.py` imports `src/kgmaker/analysis_model.py` (.analysis_model)
- `src/kgmaker/build_runner.py` imports `src/kgmaker/inspection.py` (.inspection)
- `src/kgmaker/callgraph.py` imports `src/kgmaker/analysis_model.py` (.analysis_model)
- `src/kgmaker/callgraph.py` imports `src/kgmaker/model.py` (.model)
- `src/kgmaker/callgraph.py` imports `src/kgmaker/views.py` (.views)
- `src/kgmaker/classification.py` imports `src/kgmaker/analysis_model.py` (.analysis_model)
- `src/kgmaker/cli.py` imports `src/kgmaker/agent_rules.py` (.agent_rules)
- `src/kgmaker/cli.py` imports `src/kgmaker/agents.py` (.agents)
- `src/kgmaker/cli.py` imports `src/kgmaker/analysis_agent.py` (.analysis_agent)
- `src/kgmaker/cli.py` imports `src/kgmaker/confluence.py` (.confluence)
- `src/kgmaker/cli.py` imports `src/kgmaker/context.py` (.context)
- `src/kgmaker/cli.py` imports `src/kgmaker/data_agent.py` (.data_agent)
- `src/kgmaker/cli.py` imports `src/kgmaker/feature.py` (.feature)
- `src/kgmaker/cli.py` imports `src/kgmaker/inspection_cli.py` (.inspection_cli)
- `src/kgmaker/cli.py` imports `src/kgmaker/memory.py` (.memory)
- `src/kgmaker/cli.py` imports `src/kgmaker/model.py` (.model)
- `src/kgmaker/cli.py` imports `src/kgmaker/project_cli.py` (.project_cli)
- `src/kgmaker/cli.py` imports `src/kgmaker/scanner.py` (.scanner)
- `src/kgmaker/cli.py` imports `src/kgmaker/semantic.py` (.semantic)
- `src/kgmaker/cli.py` imports `src/kgmaker/store.py` (.store)
- `src/kgmaker/cli.py` imports `src/kgmaker/workflow.py` (.workflow)
- `src/kgmaker/cli.py` imports `src/kgmaker/workspace_cli.py` (.workspace_cli)
- `src/kgmaker/confluence.py` imports `src/kgmaker/model.py` (.model)
- `src/kgmaker/context.py` imports `src/kgmaker/memory.py` (.memory)
- `src/kgmaker/context.py` imports `src/kgmaker/model.py` (.model)
- `src/kgmaker/context.py` imports `src/kgmaker/scanner.py` (.scanner)
- `src/kgmaker/context.py` imports `src/kgmaker/semantic.py` (.semantic)
- `src/kgmaker/context.py` imports `src/kgmaker/store.py` (.store)
- `src/kgmaker/context.py` imports `src/kgmaker/workflow.py` (.workflow)
- `src/kgmaker/control_flow.py` imports `src/kgmaker/analysis_model.py` (.analysis_model)
- `src/kgmaker/data_agent.py` imports `src/kgmaker/agent_rules.py` (.agent_rules)
- `src/kgmaker/data_check.py` imports `src/kgmaker/analysis_model.py` (.analysis_model)
- `src/kgmaker/data_check.py` imports `src/kgmaker/analysis_report.py` (.analysis_report)
- `src/kgmaker/data_check.py` imports `src/kgmaker/availability.py` (.availability)
- `src/kgmaker/data_check.py` imports `src/kgmaker/dataflow.py` (.dataflow)
- `src/kgmaker/data_check.py` imports `src/kgmaker/store.py` (.store)
- `src/kgmaker/data_check.py` imports `src/kgmaker/workspace.py` (.workspace)
- `src/kgmaker/dataflow.py` imports `src/kgmaker/model.py` (.model)
- `src/kgmaker/domain.py` imports `src/kgmaker/model.py` (.model)
- `src/kgmaker/feature.py` imports `src/kgmaker/analysis_model.py` (.analysis_model)
- `src/kgmaker/feature.py` imports `src/kgmaker/analysis_validation.py` (.analysis_validation)
- `src/kgmaker/feature.py` imports `src/kgmaker/availability.py` (.availability)
- `src/kgmaker/feature.py` imports `src/kgmaker/dataflow.py` (.dataflow)
- `src/kgmaker/feature.py` imports `src/kgmaker/flyway.py` (.flyway)
- `src/kgmaker/feature.py` imports `src/kgmaker/graph_provider.py` (.graph_provider)
- `src/kgmaker/feature.py` imports `src/kgmaker/model.py` (.model)
- `src/kgmaker/feature.py` imports `src/kgmaker/scanner.py` (.scanner)
- `src/kgmaker/feature.py` imports `src/kgmaker/schema_replay.py` (.schema_replay)
- `src/kgmaker/feature.py` imports `src/kgmaker/semantic.py` (.semantic)
- `src/kgmaker/feature.py` imports `src/kgmaker/workspace.py` (.workspace)
- `src/kgmaker/feature_cli.py` imports `src/kgmaker/analysis_model.py` (.analysis_model)
- `src/kgmaker/feature_cli.py` imports `src/kgmaker/analysis_report.py` (.analysis_report)
- `src/kgmaker/feature_cli.py` imports `src/kgmaker/analysis_validation.py` (.analysis_validation)
- `src/kgmaker/feature_cli.py` imports `src/kgmaker/availability.py` (.availability)
- `src/kgmaker/feature_cli.py` imports `src/kgmaker/data_check.py` (.data_check)
- `src/kgmaker/feature_cli.py` imports `src/kgmaker/dataflow.py` (.dataflow)
- `src/kgmaker/feature_cli.py` imports `src/kgmaker/scanner.py` (.scanner)
- `src/kgmaker/feature_cli.py` imports `src/kgmaker/semantic.py` (.semantic)
- `src/kgmaker/flow.py` imports `src/kgmaker/analysis_model.py` (.analysis_model)
- `src/kgmaker/flow.py` imports `src/kgmaker/callgraph.py` (.callgraph)
- `src/kgmaker/flow.py` imports `src/kgmaker/views.py` (.views)
- `src/kgmaker/flyway.py` imports `src/kgmaker/analysis_model.py` (.analysis_model)
- `src/kgmaker/framework.py` imports `src/kgmaker/analysis_model.py` (.analysis_model)
- `src/kgmaker/framework.py` imports `src/kgmaker/model.py` (.model)
- `src/kgmaker/graph_provider.py` imports `src/kgmaker/analysis_model.py` (.analysis_model)
- `src/kgmaker/graph_provider.py` imports `src/kgmaker/classification.py` (.classification)
- `src/kgmaker/graph_provider.py` imports `src/kgmaker/inspection.py` (.inspection)
- `src/kgmaker/graph_provider.py` imports `src/kgmaker/model.py` (.model)
- `src/kgmaker/graph_provider.py` imports `src/kgmaker/scanner.py` (.scanner)
- `src/kgmaker/graph_provider.py` imports `src/kgmaker/store.py` (.store)
- `src/kgmaker/graph_provider.py` imports `src/kgmaker/worker_protocol.py` (.worker_protocol)
- `src/kgmaker/inspection.py` imports `src/kgmaker/analysis_model.py` (.analysis_model)
- `src/kgmaker/inspection.py` imports `src/kgmaker/classification.py` (.classification)
- `src/kgmaker/inspection.py` imports `src/kgmaker/control_flow.py` (.control_flow)
- `src/kgmaker/inspection.py` imports `src/kgmaker/framework.py` (.framework)
- `src/kgmaker/inspection.py` imports `src/kgmaker/model.py` (.model)
- `src/kgmaker/inspection.py` imports `src/kgmaker/scanner.py` (.scanner)
- `src/kgmaker/inspection.py` imports `src/kgmaker/store.py` (.store)
- `src/kgmaker/inspection.py` imports `src/kgmaker/worker_protocol.py` (.worker_protocol)
- `src/kgmaker/inspection_cli.py` imports `src/kgmaker/analysis_model.py` (.analysis_model)
- `src/kgmaker/inspection_cli.py` imports `src/kgmaker/build_model.py` (.build_model)
- `src/kgmaker/inspection_cli.py` imports `src/kgmaker/graph_provider.py` (.graph_provider)
- `src/kgmaker/inspection_cli.py` imports `src/kgmaker/inspection.py` (.inspection)
- `src/kgmaker/inspection_cli.py` imports `src/kgmaker/runtime_evidence.py` (.runtime_evidence)
- `src/kgmaker/inspection_cli.py` imports `src/kgmaker/store.py` (.store)
- `src/kgmaker/inspection_cli.py` imports `src/kgmaker/views.py` (.views)
- `src/kgmaker/inspection_cli.py` imports `src/kgmaker/worker_protocol.py` (.worker_protocol)
- `src/kgmaker/memory.py` imports `src/kgmaker/model.py` (.model)
- `src/kgmaker/model.py` imports `src/kgmaker/classification.py` (.classification)
- `src/kgmaker/project_cli.py` imports `src/kgmaker/analysis_model.py` (.analysis_model)
- `src/kgmaker/project_cli.py` imports `src/kgmaker/build_maven.py` (.build_maven)
- `src/kgmaker/project_cli.py` imports `src/kgmaker/build_model.py` (.build_model)
- `src/kgmaker/project_cli.py` imports `src/kgmaker/build_runner.py` (.build_runner)
- `src/kgmaker/project_cli.py` imports `src/kgmaker/classification.py` (.classification)
- `src/kgmaker/project_cli.py` imports `src/kgmaker/inspection_cli.py` (.inspection_cli)
- `src/kgmaker/project_cli.py` imports `src/kgmaker/scanner.py` (.scanner)
- `src/kgmaker/project_cli.py` imports `src/kgmaker/store.py` (.store)
- `src/kgmaker/project_cli.py` imports `src/kgmaker/views.py` (.views)
- `src/kgmaker/project_cli.py` imports `src/kgmaker/workspace.py` (.workspace)
- `src/kgmaker/runtime_evidence.py` imports `src/kgmaker/analysis_model.py` (.analysis_model)
- `src/kgmaker/runtime_evidence.py` imports `src/kgmaker/model.py` (.model)
- `src/kgmaker/runtime_evidence.py` imports `src/kgmaker/store.py` (.store)
- `src/kgmaker/scanner.py` imports `src/kgmaker/analysis_model.py` (.analysis_model)
- `src/kgmaker/scanner.py` imports `src/kgmaker/classification.py` (.classification)
- `src/kgmaker/scanner.py` imports `src/kgmaker/dataflow.py` (.dataflow)
- `src/kgmaker/scanner.py` imports `src/kgmaker/domain.py` (.domain)
- `src/kgmaker/scanner.py` imports `src/kgmaker/model.py` (.model)
- `src/kgmaker/schema_replay.py` imports `src/kgmaker/analysis_model.py` (.analysis_model)
- `src/kgmaker/schema_replay.py` imports `src/kgmaker/flyway.py` (.flyway)
- `src/kgmaker/schema_replay.py` imports `src/kgmaker/model.py` (.model)
- `src/kgmaker/semantic.py` imports `src/kgmaker/memory.py` (.memory)
- `src/kgmaker/semantic.py` imports `src/kgmaker/model.py` (.model)
- `src/kgmaker/store.py` imports `src/kgmaker/analysis_model.py` (.analysis_model)
- `src/kgmaker/store.py` imports `src/kgmaker/model.py` (.model)
- `src/kgmaker/store.py` imports `src/kgmaker/views.py` (.views)
- `src/kgmaker/views.py` imports `src/kgmaker/model.py` (.model)
- `src/kgmaker/worker_protocol.py` imports `src/kgmaker/analysis_model.py` (.analysis_model)
- `src/kgmaker/workflow.py` imports `src/kgmaker/memory.py` (.memory)
- `src/kgmaker/workspace.py` imports `src/kgmaker/analysis_model.py` (.analysis_model)
- `src/kgmaker/workspace.py` imports `src/kgmaker/classification.py` (.classification)
- `src/kgmaker/workspace.py` imports `src/kgmaker/model.py` (.model)
- `src/kgmaker/workspace.py` imports `src/kgmaker/schema_replay.py` (.schema_replay)
- `src/kgmaker/workspace_cli.py` imports `src/kgmaker/analysis_model.py` (.analysis_model)
- `src/kgmaker/workspace_cli.py` imports `src/kgmaker/dataflow.py` (.dataflow)
- `src/kgmaker/workspace_cli.py` imports `src/kgmaker/schema_replay.py` (.schema_replay)
- `src/kgmaker/workspace_cli.py` imports `src/kgmaker/store.py` (.store)
- `src/kgmaker/workspace_cli.py` imports `src/kgmaker/workspace.py` (.workspace)
- `src/kgmaker/analysis_model.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 58; src/kgmaker/analysis_model.py:58; INFERRED 0.85)
- `src/kgmaker/analysis_model.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 63; src/kgmaker/analysis_model.py:63; INFERRED 0.85)
- `src/kgmaker/analysis_model.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 64; src/kgmaker/analysis_model.py:64; INFERRED 0.85)
- `src/kgmaker/analysis_model.py` may call `271 in `src/kgmaker/domain.py`` (name match at line 97; src/kgmaker/analysis_model.py:97; INFERRED 0.85)
- `src/kgmaker/analysis_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 118; src/kgmaker/analysis_model.py:118; INFERRED 0.85)
- `src/kgmaker/analysis_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 121; src/kgmaker/analysis_model.py:121; INFERRED 0.85)
- `src/kgmaker/analysis_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 123; src/kgmaker/analysis_model.py:123; INFERRED 0.85)
- `src/kgmaker/analysis_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 126; src/kgmaker/analysis_model.py:126; INFERRED 0.85)
- `src/kgmaker/analysis_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 129; src/kgmaker/analysis_model.py:129; INFERRED 0.85)
- `src/kgmaker/analysis_report.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 107; src/kgmaker/analysis_report.py:107; INFERRED 0.85)
- `src/kgmaker/analysis_report.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 114; src/kgmaker/analysis_report.py:114; INFERRED 0.85)
- `src/kgmaker/analysis_report.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 132; src/kgmaker/analysis_report.py:132; INFERRED 0.85)
- `src/kgmaker/analysis_report.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 133; src/kgmaker/analysis_report.py:133; INFERRED 0.85)
- `src/kgmaker/analysis_report.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 134; src/kgmaker/analysis_report.py:134; INFERRED 0.85)
- `src/kgmaker/analysis_report.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 136; src/kgmaker/analysis_report.py:136; INFERRED 0.85)
- `src/kgmaker/analysis_report.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 138; src/kgmaker/analysis_report.py:138; INFERRED 0.85)
- `src/kgmaker/analysis_report.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 140; src/kgmaker/analysis_report.py:140; INFERRED 0.85)
- `src/kgmaker/analysis_report.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 40; src/kgmaker/analysis_report.py:40; INFERRED 0.85)
- `src/kgmaker/analysis_report.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 56; src/kgmaker/analysis_report.py:56; INFERRED 0.85)
- `src/kgmaker/analysis_report.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 60; src/kgmaker/analysis_report.py:60; INFERRED 0.85)
- `src/kgmaker/analysis_report.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 62; src/kgmaker/analysis_report.py:62; INFERRED 0.85)
- `src/kgmaker/analysis_report.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 69; src/kgmaker/analysis_report.py:69; INFERRED 0.85)
- `src/kgmaker/analysis_report.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 71; src/kgmaker/analysis_report.py:71; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 100; src/kgmaker/analysis_validation.py:100; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 105; src/kgmaker/analysis_validation.py:105; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 107; src/kgmaker/analysis_validation.py:107; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 109; src/kgmaker/analysis_validation.py:109; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 35; src/kgmaker/analysis_validation.py:35; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 40; src/kgmaker/analysis_validation.py:40; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 42; src/kgmaker/analysis_validation.py:42; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 51; src/kgmaker/analysis_validation.py:51; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 56; src/kgmaker/analysis_validation.py:56; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 59; src/kgmaker/analysis_validation.py:59; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 61; src/kgmaker/analysis_validation.py:61; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 65; src/kgmaker/analysis_validation.py:65; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 67; src/kgmaker/analysis_validation.py:67; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 69; src/kgmaker/analysis_validation.py:69; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 72; src/kgmaker/analysis_validation.py:72; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 78; src/kgmaker/analysis_validation.py:78; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 81; src/kgmaker/analysis_validation.py:81; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 85; src/kgmaker/analysis_validation.py:85; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 89; src/kgmaker/analysis_validation.py:89; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 93; src/kgmaker/analysis_validation.py:93; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 98; src/kgmaker/analysis_validation.py:98; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `45 in `src/kgmaker/analysis_model.py`` (name match at line 66; src/kgmaker/analysis_validation.py:66; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `73 in `src/kgmaker/analysis_model.py`` (name match at line 86; src/kgmaker/analysis_validation.py:86; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 52; src/kgmaker/analysis_validation.py:52; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `35 in `src/kgmaker/availability.py`` (name match at line 273; src/kgmaker/analysis_validation.py:273; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `283 in `src/kgmaker/dataflow.py`` (name match at line 343; src/kgmaker/analysis_validation.py:343; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `109 in `src/kgmaker/feature.py`` (name match at line 333; src/kgmaker/analysis_validation.py:333; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 104; src/kgmaker/analysis_validation.py:104; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 156; src/kgmaker/analysis_validation.py:156; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 166; src/kgmaker/analysis_validation.py:166; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 172; src/kgmaker/analysis_validation.py:172; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 179; src/kgmaker/analysis_validation.py:179; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 182; src/kgmaker/analysis_validation.py:182; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 190; src/kgmaker/analysis_validation.py:190; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 193; src/kgmaker/analysis_validation.py:193; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 194; src/kgmaker/analysis_validation.py:194; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 197; src/kgmaker/analysis_validation.py:197; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 201; src/kgmaker/analysis_validation.py:201; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 204; src/kgmaker/analysis_validation.py:204; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 206; src/kgmaker/analysis_validation.py:206; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 209; src/kgmaker/analysis_validation.py:209; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 211; src/kgmaker/analysis_validation.py:211; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 221; src/kgmaker/analysis_validation.py:221; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 222; src/kgmaker/analysis_validation.py:222; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 226; src/kgmaker/analysis_validation.py:226; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 234; src/kgmaker/analysis_validation.py:234; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 236; src/kgmaker/analysis_validation.py:236; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 242; src/kgmaker/analysis_validation.py:242; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 244; src/kgmaker/analysis_validation.py:244; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 261; src/kgmaker/analysis_validation.py:261; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 263; src/kgmaker/analysis_validation.py:263; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 267; src/kgmaker/analysis_validation.py:267; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 268; src/kgmaker/analysis_validation.py:268; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 274; src/kgmaker/analysis_validation.py:274; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 276; src/kgmaker/analysis_validation.py:276; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 278; src/kgmaker/analysis_validation.py:278; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 281; src/kgmaker/analysis_validation.py:281; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 285; src/kgmaker/analysis_validation.py:285; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 287; src/kgmaker/analysis_validation.py:287; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 290; src/kgmaker/analysis_validation.py:290; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 291; src/kgmaker/analysis_validation.py:291; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 300; src/kgmaker/analysis_validation.py:300; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 31; src/kgmaker/analysis_validation.py:31; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 315; src/kgmaker/analysis_validation.py:315; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 317; src/kgmaker/analysis_validation.py:317; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 320; src/kgmaker/analysis_validation.py:320; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 33; src/kgmaker/analysis_validation.py:33; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 34; src/kgmaker/analysis_validation.py:34; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 344; src/kgmaker/analysis_validation.py:344; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 349; src/kgmaker/analysis_validation.py:349; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 350; src/kgmaker/analysis_validation.py:350; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 371; src/kgmaker/analysis_validation.py:371; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 372; src/kgmaker/analysis_validation.py:372; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 374; src/kgmaker/analysis_validation.py:374; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 376; src/kgmaker/analysis_validation.py:376; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 38; src/kgmaker/analysis_validation.py:38; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 381; src/kgmaker/analysis_validation.py:381; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 384; src/kgmaker/analysis_validation.py:384; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 385; src/kgmaker/analysis_validation.py:385; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 387; src/kgmaker/analysis_validation.py:387; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 389; src/kgmaker/analysis_validation.py:389; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 390; src/kgmaker/analysis_validation.py:390; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 391; src/kgmaker/analysis_validation.py:391; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 41; src/kgmaker/analysis_validation.py:41; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 44; src/kgmaker/analysis_validation.py:44; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 47; src/kgmaker/analysis_validation.py:47; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 49; src/kgmaker/analysis_validation.py:49; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 54; src/kgmaker/analysis_validation.py:54; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 57; src/kgmaker/analysis_validation.py:57; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 58; src/kgmaker/analysis_validation.py:58; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 60; src/kgmaker/analysis_validation.py:60; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 63; src/kgmaker/analysis_validation.py:63; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 66; src/kgmaker/analysis_validation.py:66; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 70; src/kgmaker/analysis_validation.py:70; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 73; src/kgmaker/analysis_validation.py:73; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 76; src/kgmaker/analysis_validation.py:76; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 79; src/kgmaker/analysis_validation.py:79; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 83; src/kgmaker/analysis_validation.py:83; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `28 in `src/kgmaker/workspace.py`` (name match at line 349; src/kgmaker/analysis_validation.py:349; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `28 in `src/kgmaker/workspace.py`` (name match at line 53; src/kgmaker/analysis_validation.py:53; INFERRED 0.85)
- `src/kgmaker/analysis_validation.py` may call `18 in `src/kgmaker/workspace.py`` (name match at line 55; src/kgmaker/analysis_validation.py:55; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 102; src/kgmaker/availability.py:102; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 105; src/kgmaker/availability.py:105; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 109; src/kgmaker/availability.py:109; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 117; src/kgmaker/availability.py:117; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 120; src/kgmaker/availability.py:120; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 124; src/kgmaker/availability.py:124; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 127; src/kgmaker/availability.py:127; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 130; src/kgmaker/availability.py:130; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 133; src/kgmaker/availability.py:133; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 143; src/kgmaker/availability.py:143; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 151; src/kgmaker/availability.py:151; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 164; src/kgmaker/availability.py:164; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 166; src/kgmaker/availability.py:166; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 168; src/kgmaker/availability.py:168; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 177; src/kgmaker/availability.py:177; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 40; src/kgmaker/availability.py:40; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 45; src/kgmaker/availability.py:45; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 48; src/kgmaker/availability.py:48; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 52; src/kgmaker/availability.py:52; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 54; src/kgmaker/availability.py:54; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 57; src/kgmaker/availability.py:57; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 61; src/kgmaker/availability.py:61; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 64; src/kgmaker/availability.py:64; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 71; src/kgmaker/availability.py:71; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 75; src/kgmaker/availability.py:75; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 78; src/kgmaker/availability.py:78; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 85; src/kgmaker/availability.py:85; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 89; src/kgmaker/availability.py:89; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 95; src/kgmaker/availability.py:95; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 97; src/kgmaker/availability.py:97; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 99; src/kgmaker/availability.py:99; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `283 in `src/kgmaker/dataflow.py`` (name match at line 82; src/kgmaker/availability.py:82; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `109 in `src/kgmaker/feature.py`` (name match at line 81; src/kgmaker/availability.py:81; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 100; src/kgmaker/availability.py:100; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 108; src/kgmaker/availability.py:108; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 128; src/kgmaker/availability.py:128; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 134; src/kgmaker/availability.py:134; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 140; src/kgmaker/availability.py:140; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 146; src/kgmaker/availability.py:146; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 155; src/kgmaker/availability.py:155; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 156; src/kgmaker/availability.py:156; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 160; src/kgmaker/availability.py:160; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 171; src/kgmaker/availability.py:171; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 175; src/kgmaker/availability.py:175; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 18; src/kgmaker/availability.py:18; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 19; src/kgmaker/availability.py:19; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 20; src/kgmaker/availability.py:20; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 22; src/kgmaker/availability.py:22; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 23; src/kgmaker/availability.py:23; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 25; src/kgmaker/availability.py:25; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 38; src/kgmaker/availability.py:38; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 42; src/kgmaker/availability.py:42; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 55; src/kgmaker/availability.py:55; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 56; src/kgmaker/availability.py:56; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 62; src/kgmaker/availability.py:62; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 65; src/kgmaker/availability.py:65; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 66; src/kgmaker/availability.py:66; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 67; src/kgmaker/availability.py:67; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 68; src/kgmaker/availability.py:68; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 69; src/kgmaker/availability.py:69; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 73; src/kgmaker/availability.py:73; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 87; src/kgmaker/availability.py:87; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 90; src/kgmaker/availability.py:90; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 91; src/kgmaker/availability.py:91; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 92; src/kgmaker/availability.py:92; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 93; src/kgmaker/availability.py:93; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 94; src/kgmaker/availability.py:94; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 96; src/kgmaker/availability.py:96; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 98; src/kgmaker/availability.py:98; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `91 in `src/kgmaker/schema_replay.py`` (name match at line 148; src/kgmaker/availability.py:148; INFERRED 0.85)
- `src/kgmaker/availability.py` may call `91 in `src/kgmaker/schema_replay.py`` (name match at line 149; src/kgmaker/availability.py:149; INFERRED 0.85)
- `src/kgmaker/build_maven.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 47; src/kgmaker/build_maven.py:47; INFERRED 0.85)
- `src/kgmaker/build_maven.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 50; src/kgmaker/build_maven.py:50; INFERRED 0.85)
- `src/kgmaker/build_maven.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 86; src/kgmaker/build_maven.py:86; INFERRED 0.85)
- `src/kgmaker/build_maven.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 99; src/kgmaker/build_maven.py:99; INFERRED 0.85)
- `src/kgmaker/build_maven.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 115; src/kgmaker/build_maven.py:115; INFERRED 0.85)
- `src/kgmaker/build_maven.py` may call `45 in `src/kgmaker/analysis_model.py`` (name match at line 70; src/kgmaker/build_maven.py:70; INFERRED 0.85)
- `src/kgmaker/build_maven.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 104; src/kgmaker/build_maven.py:104; INFERRED 0.85)
- `src/kgmaker/build_maven.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 83; src/kgmaker/build_maven.py:83; INFERRED 0.85)
- `src/kgmaker/build_maven.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 92; src/kgmaker/build_maven.py:92; INFERRED 0.85)
- `src/kgmaker/build_maven.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 40; src/kgmaker/build_maven.py:40; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 101; src/kgmaker/build_model.py:101; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 103; src/kgmaker/build_model.py:103; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 106; src/kgmaker/build_model.py:106; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 19; src/kgmaker/build_model.py:19; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 21; src/kgmaker/build_model.py:21; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 25; src/kgmaker/build_model.py:25; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 27; src/kgmaker/build_model.py:27; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 29; src/kgmaker/build_model.py:29; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 33; src/kgmaker/build_model.py:33; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 35; src/kgmaker/build_model.py:35; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 39; src/kgmaker/build_model.py:39; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 42; src/kgmaker/build_model.py:42; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 44; src/kgmaker/build_model.py:44; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 48; src/kgmaker/build_model.py:48; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 51; src/kgmaker/build_model.py:51; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 56; src/kgmaker/build_model.py:56; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 58; src/kgmaker/build_model.py:58; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 60; src/kgmaker/build_model.py:60; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 63; src/kgmaker/build_model.py:63; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 66; src/kgmaker/build_model.py:66; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 68; src/kgmaker/build_model.py:68; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 73; src/kgmaker/build_model.py:73; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 77; src/kgmaker/build_model.py:77; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 79; src/kgmaker/build_model.py:79; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 123; src/kgmaker/build_model.py:123; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 28; src/kgmaker/build_model.py:28; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `45 in `src/kgmaker/analysis_model.py`` (name match at line 32; src/kgmaker/build_model.py:32; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 110; src/kgmaker/build_model.py:110; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 31; src/kgmaker/build_model.py:31; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 46; src/kgmaker/build_model.py:46; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 54; src/kgmaker/build_model.py:54; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 71; src/kgmaker/build_model.py:71; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 90; src/kgmaker/build_model.py:90; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `103 in `src/kgmaker/analysis_model.py`` (name match at line 91; src/kgmaker/build_model.py:91; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 110; src/kgmaker/build_model.py:110; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `23 in `src/kgmaker/inspection.py`` (name match at line 55; src/kgmaker/build_model.py:55; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `23 in `src/kgmaker/inspection.py`` (name match at line 72; src/kgmaker/build_model.py:72; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 100; src/kgmaker/build_model.py:100; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 114; src/kgmaker/build_model.py:114; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 116; src/kgmaker/build_model.py:116; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 119; src/kgmaker/build_model.py:119; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 120; src/kgmaker/build_model.py:120; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 121; src/kgmaker/build_model.py:121; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 122; src/kgmaker/build_model.py:122; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 123; src/kgmaker/build_model.py:123; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 18; src/kgmaker/build_model.py:18; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 20; src/kgmaker/build_model.py:20; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 22; src/kgmaker/build_model.py:22; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 23; src/kgmaker/build_model.py:23; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 24; src/kgmaker/build_model.py:24; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 26; src/kgmaker/build_model.py:26; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 28; src/kgmaker/build_model.py:28; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 34; src/kgmaker/build_model.py:34; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 38; src/kgmaker/build_model.py:38; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 41; src/kgmaker/build_model.py:41; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 43; src/kgmaker/build_model.py:43; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 47; src/kgmaker/build_model.py:47; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 50; src/kgmaker/build_model.py:50; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 57; src/kgmaker/build_model.py:57; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 59; src/kgmaker/build_model.py:59; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 64; src/kgmaker/build_model.py:64; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 65; src/kgmaker/build_model.py:65; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 67; src/kgmaker/build_model.py:67; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 72; src/kgmaker/build_model.py:72; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 74; src/kgmaker/build_model.py:74; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 78; src/kgmaker/build_model.py:78; INFERRED 0.85)
- `src/kgmaker/build_model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 92; src/kgmaker/build_model.py:92; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 100; src/kgmaker/build_runner.py:100; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 101; src/kgmaker/build_runner.py:101; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 105; src/kgmaker/build_runner.py:105; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 106; src/kgmaker/build_runner.py:106; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 108; src/kgmaker/build_runner.py:108; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 111; src/kgmaker/build_runner.py:111; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 113; src/kgmaker/build_runner.py:113; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 117; src/kgmaker/build_runner.py:117; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 119; src/kgmaker/build_runner.py:119; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 30; src/kgmaker/build_runner.py:30; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 33; src/kgmaker/build_runner.py:33; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 34; src/kgmaker/build_runner.py:34; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 42; src/kgmaker/build_runner.py:42; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 43; src/kgmaker/build_runner.py:43; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 44; src/kgmaker/build_runner.py:44; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 48; src/kgmaker/build_runner.py:48; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 50; src/kgmaker/build_runner.py:50; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 52; src/kgmaker/build_runner.py:52; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 55; src/kgmaker/build_runner.py:55; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 58; src/kgmaker/build_runner.py:58; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 66; src/kgmaker/build_runner.py:66; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 70; src/kgmaker/build_runner.py:70; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 100; src/kgmaker/build_runner.py:100; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 111; src/kgmaker/build_runner.py:111; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 73; src/kgmaker/build_runner.py:73; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 76; src/kgmaker/build_runner.py:76; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 78; src/kgmaker/build_runner.py:78; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `45 in `src/kgmaker/analysis_model.py`` (name match at line 108; src/kgmaker/build_runner.py:108; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `45 in `src/kgmaker/analysis_model.py`` (name match at line 117; src/kgmaker/build_runner.py:117; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `45 in `src/kgmaker/analysis_model.py`` (name match at line 141; src/kgmaker/build_runner.py:141; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `45 in `src/kgmaker/analysis_model.py`` (name match at line 145; src/kgmaker/build_runner.py:145; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `45 in `src/kgmaker/analysis_model.py`` (name match at line 35; src/kgmaker/build_runner.py:35; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `45 in `src/kgmaker/analysis_model.py`` (name match at line 75; src/kgmaker/build_runner.py:75; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `73 in `src/kgmaker/analysis_model.py`` (name match at line 137; src/kgmaker/build_runner.py:137; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 104; src/kgmaker/build_runner.py:104; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 116; src/kgmaker/build_runner.py:116; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 145; src/kgmaker/build_runner.py:145; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `103 in `src/kgmaker/analysis_model.py`` (name match at line 168; src/kgmaker/build_runner.py:168; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 102; src/kgmaker/build_runner.py:102; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 148; src/kgmaker/build_runner.py:148; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 156; src/kgmaker/build_runner.py:156; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 41; src/kgmaker/build_runner.py:41; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 53; src/kgmaker/build_runner.py:53; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `146 in `src/kgmaker/dataflow.py`` (name match at line 26; src/kgmaker/build_runner.py:26; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `23 in `src/kgmaker/inspection.py`` (name match at line 155; src/kgmaker/build_runner.py:155; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `23 in `src/kgmaker/inspection.py`` (name match at line 162; src/kgmaker/build_runner.py:162; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `36 in `src/kgmaker/inspection.py`` (name match at line 53; src/kgmaker/build_runner.py:53; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 100; src/kgmaker/build_runner.py:100; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 101; src/kgmaker/build_runner.py:101; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 111; src/kgmaker/build_runner.py:111; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 140; src/kgmaker/build_runner.py:140; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 149; src/kgmaker/build_runner.py:149; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 150; src/kgmaker/build_runner.py:150; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 165; src/kgmaker/build_runner.py:165; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 166; src/kgmaker/build_runner.py:166; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 169; src/kgmaker/build_runner.py:169; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 76; src/kgmaker/build_runner.py:76; INFERRED 0.85)
- `src/kgmaker/build_runner.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 90; src/kgmaker/build_runner.py:90; INFERRED 0.85)
- `src/kgmaker/callgraph.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 46; src/kgmaker/callgraph.py:46; INFERRED 0.85)
- `src/kgmaker/callgraph.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 55; src/kgmaker/callgraph.py:55; INFERRED 0.85)
- `src/kgmaker/callgraph.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 67; src/kgmaker/callgraph.py:67; INFERRED 0.85)
- `src/kgmaker/callgraph.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 14; src/kgmaker/callgraph.py:14; INFERRED 0.85)
- `src/kgmaker/callgraph.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 16; src/kgmaker/callgraph.py:16; INFERRED 0.85)
- `src/kgmaker/callgraph.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 19; src/kgmaker/callgraph.py:19; INFERRED 0.85)
- `src/kgmaker/callgraph.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 20; src/kgmaker/callgraph.py:20; INFERRED 0.85)
- `src/kgmaker/callgraph.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 22; src/kgmaker/callgraph.py:22; INFERRED 0.85)
- `src/kgmaker/callgraph.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 25; src/kgmaker/callgraph.py:25; INFERRED 0.85)
- `src/kgmaker/callgraph.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 26; src/kgmaker/callgraph.py:26; INFERRED 0.85)
- `src/kgmaker/callgraph.py` may call `17 in `src/kgmaker/views.py`` (name match at line 44; src/kgmaker/callgraph.py:44; INFERRED 0.85)
- `src/kgmaker/callgraph.py` may call `17 in `src/kgmaker/views.py`` (name match at line 53; src/kgmaker/callgraph.py:53; INFERRED 0.85)
- `src/kgmaker/callgraph.py` may call `17 in `src/kgmaker/views.py`` (name match at line 64; src/kgmaker/callgraph.py:64; INFERRED 0.85)
- `src/kgmaker/classification.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 112; src/kgmaker/classification.py:112; INFERRED 0.85)
- `src/kgmaker/classification.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 35; src/kgmaker/classification.py:35; INFERRED 0.85)
- `src/kgmaker/classification.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 37; src/kgmaker/classification.py:37; INFERRED 0.85)
- `src/kgmaker/classification.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 40; src/kgmaker/classification.py:40; INFERRED 0.85)
- `src/kgmaker/classification.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 42; src/kgmaker/classification.py:42; INFERRED 0.85)
- `src/kgmaker/classification.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 46; src/kgmaker/classification.py:46; INFERRED 0.85)
- `src/kgmaker/classification.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 49; src/kgmaker/classification.py:49; INFERRED 0.85)
- `src/kgmaker/classification.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 52; src/kgmaker/classification.py:52; INFERRED 0.85)
- `src/kgmaker/classification.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 54; src/kgmaker/classification.py:54; INFERRED 0.85)
- `src/kgmaker/classification.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 57; src/kgmaker/classification.py:57; INFERRED 0.85)
- `src/kgmaker/classification.py` may call `73 in `src/kgmaker/analysis_model.py`` (name match at line 33; src/kgmaker/classification.py:33; INFERRED 0.85)
- `src/kgmaker/classification.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 32; src/kgmaker/classification.py:32; INFERRED 0.85)
- `src/kgmaker/classification.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 43; src/kgmaker/classification.py:43; INFERRED 0.85)
- `src/kgmaker/classification.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 56; src/kgmaker/classification.py:56; INFERRED 0.85)
- `src/kgmaker/classification.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 109; src/kgmaker/classification.py:109; INFERRED 0.85)
- `src/kgmaker/classification.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 34; src/kgmaker/classification.py:34; INFERRED 0.85)
- `src/kgmaker/classification.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 36; src/kgmaker/classification.py:36; INFERRED 0.85)
- `src/kgmaker/classification.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 41; src/kgmaker/classification.py:41; INFERRED 0.85)
- `src/kgmaker/classification.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 43; src/kgmaker/classification.py:43; INFERRED 0.85)
- `src/kgmaker/classification.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 48; src/kgmaker/classification.py:48; INFERRED 0.85)
- `src/kgmaker/classification.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 51; src/kgmaker/classification.py:51; INFERRED 0.85)
- `src/kgmaker/classification.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 53; src/kgmaker/classification.py:53; INFERRED 0.85)
- `src/kgmaker/classification.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 55; src/kgmaker/classification.py:55; INFERRED 0.85)
- `src/kgmaker/classification.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 68; src/kgmaker/classification.py:68; INFERRED 0.85)
- `src/kgmaker/classification.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 72; src/kgmaker/classification.py:72; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `27 in `src/kgmaker/memory.py`` (name match at line 682; src/kgmaker/cli.py:682; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `27 in `src/kgmaker/memory.py`` (name match at line 698; src/kgmaker/cli.py:698; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `27 in `src/kgmaker/memory.py`` (name match at line 701; src/kgmaker/cli.py:701; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `27 in `src/kgmaker/memory.py`` (name match at line 705; src/kgmaker/cli.py:705; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `62 in `src/kgmaker/workflow.py`` (name match at line 812; src/kgmaker/cli.py:812; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `529 in `src/kgmaker/confluence.py`` (name match at line 387; src/kgmaker/cli.py:387; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `280 in `src/kgmaker/confluence.py`` (name match at line 302; src/kgmaker/cli.py:302; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `415 in `src/kgmaker/confluence.py`` (name match at line 305; src/kgmaker/cli.py:305; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `484 in `src/kgmaker/confluence.py`` (name match at line 304; src/kgmaker/cli.py:304; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `495 in `src/kgmaker/confluence.py`` (name match at line 300; src/kgmaker/cli.py:300; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `367 in `src/kgmaker/confluence.py`` (name match at line 303; src/kgmaker/cli.py:303; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 595; src/kgmaker/cli.py:595; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 603; src/kgmaker/cli.py:603; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 808; src/kgmaker/cli.py:808; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 809; src/kgmaker/cli.py:809; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 984; src/kgmaker/cli.py:984; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `53 in `src/kgmaker/feature.py`` (name match at line 299; src/kgmaker/cli.py:299; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `53 in `src/kgmaker/feature.py`` (name match at line 335; src/kgmaker/cli.py:335; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `53 in `src/kgmaker/feature.py`` (name match at line 356; src/kgmaker/cli.py:356; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `53 in `src/kgmaker/feature.py`` (name match at line 837; src/kgmaker/cli.py:837; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `144 in `src/kgmaker/feature_cli.py`` (name match at line 1041; src/kgmaker/cli.py:1041; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `123 in `src/kgmaker/feature_cli.py`` (name match at line 1047; src/kgmaker/cli.py:1047; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `255 in `src/kgmaker/memory.py`` (name match at line 683; src/kgmaker/cli.py:683; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `246 in `src/kgmaker/scanner.py`` (name match at line 386; src/kgmaker/cli.py:386; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `246 in `src/kgmaker/scanner.py`` (name match at line 409; src/kgmaker/cli.py:409; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `246 in `src/kgmaker/scanner.py`` (name match at line 475; src/kgmaker/cli.py:475; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `246 in `src/kgmaker/scanner.py`` (name match at line 558; src/kgmaker/cli.py:558; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `246 in `src/kgmaker/scanner.py`` (name match at line 578; src/kgmaker/cli.py:578; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `246 in `src/kgmaker/scanner.py`` (name match at line 684; src/kgmaker/cli.py:684; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 337; src/kgmaker/cli.py:337; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 498; src/kgmaker/cli.py:498; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 504; src/kgmaker/cli.py:504; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 512; src/kgmaker/cli.py:512; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 513; src/kgmaker/cli.py:513; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 516; src/kgmaker/cli.py:516; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 518; src/kgmaker/cli.py:518; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 617; src/kgmaker/cli.py:617; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 618; src/kgmaker/cli.py:618; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 621; src/kgmaker/cli.py:621; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 622; src/kgmaker/cli.py:622; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 638; src/kgmaker/cli.py:638; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 652; src/kgmaker/cli.py:652; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 697; src/kgmaker/cli.py:697; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 703; src/kgmaker/cli.py:703; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 708; src/kgmaker/cli.py:708; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 712; src/kgmaker/cli.py:712; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 717; src/kgmaker/cli.py:717; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 718; src/kgmaker/cli.py:718; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `561 in `src/kgmaker/semantic.py`` (name match at line 699; src/kgmaker/cli.py:699; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `439 in `src/kgmaker/semantic.py`` (name match at line 559; src/kgmaker/cli.py:559; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `54 in `src/kgmaker/semantic.py`` (name match at line 410; src/kgmaker/cli.py:410; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `99 in `src/kgmaker/semantic.py`` (name match at line 579; src/kgmaker/cli.py:579; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `99 in `src/kgmaker/semantic.py`` (name match at line 688; src/kgmaker/cli.py:688; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `99 in `src/kgmaker/semantic.py`` (name match at line 721; src/kgmaker/cli.py:721; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `54 in `src/kgmaker/store.py`` (name match at line 330; src/kgmaker/cli.py:330; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `54 in `src/kgmaker/store.py`` (name match at line 386; src/kgmaker/cli.py:386; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `54 in `src/kgmaker/store.py`` (name match at line 393; src/kgmaker/cli.py:393; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `54 in `src/kgmaker/store.py`` (name match at line 474; src/kgmaker/cli.py:474; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `54 in `src/kgmaker/store.py`` (name match at line 590; src/kgmaker/cli.py:590; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `54 in `src/kgmaker/store.py`` (name match at line 661; src/kgmaker/cli.py:661; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `54 in `src/kgmaker/store.py`` (name match at line 680; src/kgmaker/cli.py:680; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `54 in `src/kgmaker/store.py`` (name match at line 737; src/kgmaker/cli.py:737; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `14 in `src/kgmaker/store.py`` (name match at line 665; src/kgmaker/cli.py:665; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `270 in `src/kgmaker/store.py`` (name match at line 842; src/kgmaker/cli.py:842; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `224 in `src/kgmaker/store.py`` (name match at line 745; src/kgmaker/cli.py:745; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `62 in `src/kgmaker/store.py`` (name match at line 361; src/kgmaker/cli.py:361; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `62 in `src/kgmaker/store.py`` (name match at line 399; src/kgmaker/cli.py:399; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `171 in `src/kgmaker/store.py`` (name match at line 363; src/kgmaker/cli.py:363; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `171 in `src/kgmaker/store.py`` (name match at line 401; src/kgmaker/cli.py:401; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `37 in `src/kgmaker/store.py`` (name match at line 312; src/kgmaker/cli.py:312; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `37 in `src/kgmaker/store.py`` (name match at line 840; src/kgmaker/cli.py:840; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `473 in `src/kgmaker/workflow.py`` (name match at line 788; src/kgmaker/cli.py:788; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `440 in `src/kgmaker/workflow.py`` (name match at line 767; src/kgmaker/cli.py:767; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `431 in `src/kgmaker/workflow.py`` (name match at line 778; src/kgmaker/cli.py:778; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `521 in `src/kgmaker/workflow.py`` (name match at line 813; src/kgmaker/cli.py:813; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `494 in `src/kgmaker/workflow.py`` (name match at line 798; src/kgmaker/cli.py:798; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `6 in `src/kgmaker/workspace_cli.py`` (name match at line 975; src/kgmaker/cli.py:975; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `23 in `src/kgmaker/workspace_cli.py`` (name match at line 993; src/kgmaker/cli.py:993; INFERRED 0.85)
- `src/kgmaker/cli.py` may call `54 in `src/kgmaker/workspace_cli.py`` (name match at line 996; src/kgmaker/cli.py:996; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `27 in `src/kgmaker/model.py`` (name match at line 429; src/kgmaker/confluence.py:429; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `27 in `src/kgmaker/model.py`` (name match at line 439; src/kgmaker/confluence.py:439; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `27 in `src/kgmaker/model.py`` (name match at line 446; src/kgmaker/confluence.py:446; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `27 in `src/kgmaker/model.py`` (name match at line 454; src/kgmaker/confluence.py:454; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `42 in `src/kgmaker/model.py`` (name match at line 541; src/kgmaker/confluence.py:541; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `10 in `src/kgmaker/model.py`` (name match at line 423; src/kgmaker/confluence.py:423; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `10 in `src/kgmaker/model.py`` (name match at line 433; src/kgmaker/confluence.py:433; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `10 in `src/kgmaker/model.py`` (name match at line 451; src/kgmaker/confluence.py:451; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 284; src/kgmaker/confluence.py:284; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 500; src/kgmaker/confluence.py:500; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 515; src/kgmaker/confluence.py:515; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 527; src/kgmaker/confluence.py:527; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 113; src/kgmaker/confluence.py:113; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 117; src/kgmaker/confluence.py:117; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 123; src/kgmaker/confluence.py:123; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 138; src/kgmaker/confluence.py:138; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 164; src/kgmaker/confluence.py:164; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 185; src/kgmaker/confluence.py:185; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 221; src/kgmaker/confluence.py:221; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 222; src/kgmaker/confluence.py:222; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 226; src/kgmaker/confluence.py:226; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 228; src/kgmaker/confluence.py:228; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 288; src/kgmaker/confluence.py:288; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 294; src/kgmaker/confluence.py:294; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 295; src/kgmaker/confluence.py:295; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 296; src/kgmaker/confluence.py:296; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 328; src/kgmaker/confluence.py:328; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 333; src/kgmaker/confluence.py:333; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 336; src/kgmaker/confluence.py:336; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 338; src/kgmaker/confluence.py:338; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 344; src/kgmaker/confluence.py:344; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 380; src/kgmaker/confluence.py:380; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 381; src/kgmaker/confluence.py:381; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 392; src/kgmaker/confluence.py:392; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 398; src/kgmaker/confluence.py:398; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 403; src/kgmaker/confluence.py:403; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 443; src/kgmaker/confluence.py:443; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 448; src/kgmaker/confluence.py:448; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 512; src/kgmaker/confluence.py:512; INFERRED 0.85)
- `src/kgmaker/confluence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 513; src/kgmaker/confluence.py:513; INFERRED 0.85)
- `src/kgmaker/context.py` may call `285 in `src/kgmaker/memory.py`` (name match at line 128; src/kgmaker/context.py:128; INFERRED 0.85)
- `src/kgmaker/context.py` may call `285 in `src/kgmaker/memory.py`` (name match at line 140; src/kgmaker/context.py:140; INFERRED 0.85)
- `src/kgmaker/context.py` may call `285 in `src/kgmaker/memory.py`` (name match at line 206; src/kgmaker/context.py:206; INFERRED 0.85)
- `src/kgmaker/context.py` may call `285 in `src/kgmaker/memory.py`` (name match at line 309; src/kgmaker/context.py:309; INFERRED 0.85)
- `src/kgmaker/context.py` may call `285 in `src/kgmaker/memory.py`` (name match at line 47; src/kgmaker/context.py:47; INFERRED 0.85)
- `src/kgmaker/context.py` may call `285 in `src/kgmaker/memory.py`` (name match at line 70; src/kgmaker/context.py:70; INFERRED 0.85)
- `src/kgmaker/context.py` may call `285 in `src/kgmaker/memory.py`` (name match at line 92; src/kgmaker/context.py:92; INFERRED 0.85)
- `src/kgmaker/context.py` may call `246 in `src/kgmaker/scanner.py`` (name match at line 297; src/kgmaker/context.py:297; INFERRED 0.85)
- `src/kgmaker/context.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 113; src/kgmaker/context.py:113; INFERRED 0.85)
- `src/kgmaker/context.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 114; src/kgmaker/context.py:114; INFERRED 0.85)
- `src/kgmaker/context.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 118; src/kgmaker/context.py:118; INFERRED 0.85)
- `src/kgmaker/context.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 122; src/kgmaker/context.py:122; INFERRED 0.85)
- `src/kgmaker/context.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 123; src/kgmaker/context.py:123; INFERRED 0.85)
- `src/kgmaker/context.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 158; src/kgmaker/context.py:158; INFERRED 0.85)
- `src/kgmaker/context.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 160; src/kgmaker/context.py:160; INFERRED 0.85)
- `src/kgmaker/context.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 176; src/kgmaker/context.py:176; INFERRED 0.85)
- `src/kgmaker/context.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 177; src/kgmaker/context.py:177; INFERRED 0.85)
- `src/kgmaker/context.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 180; src/kgmaker/context.py:180; INFERRED 0.85)
- `src/kgmaker/context.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 181; src/kgmaker/context.py:181; INFERRED 0.85)
- `src/kgmaker/context.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 196; src/kgmaker/context.py:196; INFERRED 0.85)
- `src/kgmaker/context.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 208; src/kgmaker/context.py:208; INFERRED 0.85)
- `src/kgmaker/context.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 264; src/kgmaker/context.py:264; INFERRED 0.85)
- `src/kgmaker/context.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 278; src/kgmaker/context.py:278; INFERRED 0.85)
- `src/kgmaker/context.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 367; src/kgmaker/context.py:367; INFERRED 0.85)
- `src/kgmaker/context.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 368; src/kgmaker/context.py:368; INFERRED 0.85)
- `src/kgmaker/context.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 369; src/kgmaker/context.py:369; INFERRED 0.85)
- `src/kgmaker/context.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 371; src/kgmaker/context.py:371; INFERRED 0.85)
- `src/kgmaker/context.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 443; src/kgmaker/context.py:443; INFERRED 0.85)
- `src/kgmaker/context.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 77; src/kgmaker/context.py:77; INFERRED 0.85)
- `src/kgmaker/context.py` may call `54 in `src/kgmaker/store.py`` (name match at line 329; src/kgmaker/context.py:329; INFERRED 0.85)
- `src/kgmaker/context.py` may call `328 in `src/kgmaker/workflow.py`` (name match at line 338; src/kgmaker/context.py:338; INFERRED 0.85)
- `src/kgmaker/context.py` may call `431 in `src/kgmaker/workflow.py`` (name match at line 466; src/kgmaker/context.py:466; INFERRED 0.85)
- `src/kgmaker/context.py` may call `85 in `src/kgmaker/workflow.py`` (name match at line 403; src/kgmaker/context.py:403; INFERRED 0.85)
- `src/kgmaker/context.py` may call `515 in `src/kgmaker/workflow.py`` (name match at line 406; src/kgmaker/context.py:406; INFERRED 0.85)
- `src/kgmaker/context.py` may call `271 in `src/kgmaker/workflow.py`` (name match at line 328; src/kgmaker/context.py:328; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 37; src/kgmaker/control_flow.py:37; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 49; src/kgmaker/control_flow.py:49; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 94; src/kgmaker/control_flow.py:94; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 96; src/kgmaker/control_flow.py:96; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 39; src/kgmaker/control_flow.py:39; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 40; src/kgmaker/control_flow.py:40; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 66; src/kgmaker/control_flow.py:66; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 105; src/kgmaker/control_flow.py:105; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 109; src/kgmaker/control_flow.py:109; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 110; src/kgmaker/control_flow.py:110; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 111; src/kgmaker/control_flow.py:111; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 114; src/kgmaker/control_flow.py:114; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 116; src/kgmaker/control_flow.py:116; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 117; src/kgmaker/control_flow.py:117; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 121; src/kgmaker/control_flow.py:121; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 123; src/kgmaker/control_flow.py:123; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 126; src/kgmaker/control_flow.py:126; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 139; src/kgmaker/control_flow.py:139; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 141; src/kgmaker/control_flow.py:141; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 143; src/kgmaker/control_flow.py:143; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 149; src/kgmaker/control_flow.py:149; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 151; src/kgmaker/control_flow.py:151; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 152; src/kgmaker/control_flow.py:152; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 159; src/kgmaker/control_flow.py:159; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 164; src/kgmaker/control_flow.py:164; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 170; src/kgmaker/control_flow.py:170; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 171; src/kgmaker/control_flow.py:171; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 174; src/kgmaker/control_flow.py:174; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 176; src/kgmaker/control_flow.py:176; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 177; src/kgmaker/control_flow.py:177; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 187; src/kgmaker/control_flow.py:187; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 192; src/kgmaker/control_flow.py:192; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 194; src/kgmaker/control_flow.py:194; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 196; src/kgmaker/control_flow.py:196; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 198; src/kgmaker/control_flow.py:198; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 200; src/kgmaker/control_flow.py:200; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 204; src/kgmaker/control_flow.py:204; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 215; src/kgmaker/control_flow.py:215; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 39; src/kgmaker/control_flow.py:39; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 42; src/kgmaker/control_flow.py:42; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 43; src/kgmaker/control_flow.py:43; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 44; src/kgmaker/control_flow.py:44; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 50; src/kgmaker/control_flow.py:50; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 54; src/kgmaker/control_flow.py:54; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 56; src/kgmaker/control_flow.py:56; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 71; src/kgmaker/control_flow.py:71; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 78; src/kgmaker/control_flow.py:78; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 85; src/kgmaker/control_flow.py:85; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 88; src/kgmaker/control_flow.py:88; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 97; src/kgmaker/control_flow.py:97; INFERRED 0.85)
- `src/kgmaker/control_flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 98; src/kgmaker/control_flow.py:98; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 121; src/kgmaker/data_check.py:121; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 23; src/kgmaker/data_check.py:23; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 28; src/kgmaker/data_check.py:28; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 34; src/kgmaker/data_check.py:34; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 46; src/kgmaker/data_check.py:46; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 48; src/kgmaker/data_check.py:48; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 50; src/kgmaker/data_check.py:50; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 60; src/kgmaker/data_check.py:60; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 86; src/kgmaker/data_check.py:86; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 95; src/kgmaker/data_check.py:95; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 97; src/kgmaker/data_check.py:97; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `135 in `src/kgmaker/analysis_model.py`` (name match at line 40; src/kgmaker/data_check.py:40; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `35 in `src/kgmaker/availability.py`` (name match at line 184; src/kgmaker/data_check.py:184; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `283 in `src/kgmaker/dataflow.py`` (name match at line 134; src/kgmaker/data_check.py:134; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `109 in `src/kgmaker/feature.py`` (name match at line 83; src/kgmaker/data_check.py:83; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `161 in `src/kgmaker/feature.py`` (name match at line 39; src/kgmaker/data_check.py:39; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `272 in `src/kgmaker/feature.py`` (name match at line 203; src/kgmaker/data_check.py:203; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `272 in `src/kgmaker/feature.py`` (name match at line 41; src/kgmaker/data_check.py:41; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `272 in `src/kgmaker/feature.py`` (name match at line 80; src/kgmaker/data_check.py:80; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 101; src/kgmaker/data_check.py:101; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 102; src/kgmaker/data_check.py:102; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 114; src/kgmaker/data_check.py:114; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 125; src/kgmaker/data_check.py:125; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 130; src/kgmaker/data_check.py:130; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 141; src/kgmaker/data_check.py:141; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 152; src/kgmaker/data_check.py:152; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 159; src/kgmaker/data_check.py:159; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 160; src/kgmaker/data_check.py:160; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 163; src/kgmaker/data_check.py:163; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 168; src/kgmaker/data_check.py:168; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 170; src/kgmaker/data_check.py:170; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 171; src/kgmaker/data_check.py:171; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 194; src/kgmaker/data_check.py:194; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 196; src/kgmaker/data_check.py:196; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 57; src/kgmaker/data_check.py:57; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 58; src/kgmaker/data_check.py:58; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 65; src/kgmaker/data_check.py:65; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 76; src/kgmaker/data_check.py:76; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `14 in `src/kgmaker/store.py`` (name match at line 106; src/kgmaker/data_check.py:106; INFERRED 0.85)
- `src/kgmaker/data_check.py` may call `28 in `src/kgmaker/workspace.py`` (name match at line 57; src/kgmaker/data_check.py:57; INFERRED 0.85)
- `src/kgmaker/dataflow.py` may call `27 in `src/kgmaker/model.py`` (name match at line 83; src/kgmaker/dataflow.py:83; INFERRED 0.85)
- `src/kgmaker/dataflow.py` may call `10 in `src/kgmaker/model.py`` (name match at line 71; src/kgmaker/dataflow.py:71; INFERRED 0.85)
- `src/kgmaker/dataflow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 148; src/kgmaker/dataflow.py:148; INFERRED 0.85)
- `src/kgmaker/dataflow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 152; src/kgmaker/dataflow.py:152; INFERRED 0.85)
- `src/kgmaker/dataflow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 210; src/kgmaker/dataflow.py:210; INFERRED 0.85)
- `src/kgmaker/dataflow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 212; src/kgmaker/dataflow.py:212; INFERRED 0.85)
- `src/kgmaker/dataflow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 213; src/kgmaker/dataflow.py:213; INFERRED 0.85)
- `src/kgmaker/dataflow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 217; src/kgmaker/dataflow.py:217; INFERRED 0.85)
- `src/kgmaker/dataflow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 223; src/kgmaker/dataflow.py:223; INFERRED 0.85)
- `src/kgmaker/dataflow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 236; src/kgmaker/dataflow.py:236; INFERRED 0.85)
- `src/kgmaker/dataflow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 313; src/kgmaker/dataflow.py:313; INFERRED 0.85)
- `src/kgmaker/domain.py` may call `27 in `src/kgmaker/model.py`` (name match at line 118; src/kgmaker/domain.py:118; INFERRED 0.85)
- `src/kgmaker/domain.py` may call `27 in `src/kgmaker/model.py`` (name match at line 135; src/kgmaker/domain.py:135; INFERRED 0.85)
- `src/kgmaker/domain.py` may call `27 in `src/kgmaker/model.py`` (name match at line 155; src/kgmaker/domain.py:155; INFERRED 0.85)
- `src/kgmaker/domain.py` may call `27 in `src/kgmaker/model.py`` (name match at line 179; src/kgmaker/domain.py:179; INFERRED 0.85)
- `src/kgmaker/domain.py` may call `27 in `src/kgmaker/model.py`` (name match at line 189; src/kgmaker/domain.py:189; INFERRED 0.85)
- `src/kgmaker/domain.py` may call `27 in `src/kgmaker/model.py`` (name match at line 206; src/kgmaker/domain.py:206; INFERRED 0.85)
- `src/kgmaker/domain.py` may call `27 in `src/kgmaker/model.py`` (name match at line 276; src/kgmaker/domain.py:276; INFERRED 0.85)
- `src/kgmaker/domain.py` may call `27 in `src/kgmaker/model.py`` (name match at line 322; src/kgmaker/domain.py:322; INFERRED 0.85)
- `src/kgmaker/domain.py` may call `27 in `src/kgmaker/model.py`` (name match at line 335; src/kgmaker/domain.py:335; INFERRED 0.85)
- `src/kgmaker/domain.py` may call `27 in `src/kgmaker/model.py`` (name match at line 380; src/kgmaker/domain.py:380; INFERRED 0.85)
- `src/kgmaker/domain.py` may call `27 in `src/kgmaker/model.py`` (name match at line 417; src/kgmaker/domain.py:417; INFERRED 0.85)
- `src/kgmaker/domain.py` may call `27 in `src/kgmaker/model.py`` (name match at line 424; src/kgmaker/domain.py:424; INFERRED 0.85)
- `src/kgmaker/domain.py` may call `27 in `src/kgmaker/model.py`` (name match at line 434; src/kgmaker/domain.py:434; INFERRED 0.85)
- `src/kgmaker/domain.py` may call `27 in `src/kgmaker/model.py`` (name match at line 438; src/kgmaker/domain.py:438; INFERRED 0.85)
- `src/kgmaker/domain.py` may call `27 in `src/kgmaker/model.py`` (name match at line 509; src/kgmaker/domain.py:509; INFERRED 0.85)
- `src/kgmaker/domain.py` may call `27 in `src/kgmaker/model.py`` (name match at line 513; src/kgmaker/domain.py:513; INFERRED 0.85)
- `src/kgmaker/domain.py` may call `10 in `src/kgmaker/model.py`` (name match at line 126; src/kgmaker/domain.py:126; INFERRED 0.85)
- `src/kgmaker/domain.py` may call `10 in `src/kgmaker/model.py`` (name match at line 246; src/kgmaker/domain.py:246; INFERRED 0.85)
- `src/kgmaker/domain.py` may call `10 in `src/kgmaker/model.py`` (name match at line 415; src/kgmaker/domain.py:415; INFERRED 0.85)
- `src/kgmaker/domain.py` may call `10 in `src/kgmaker/model.py`` (name match at line 84; src/kgmaker/domain.py:84; INFERRED 0.85)
- `src/kgmaker/domain.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 309; src/kgmaker/domain.py:309; INFERRED 0.85)
- `src/kgmaker/domain.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 319; src/kgmaker/domain.py:319; INFERRED 0.85)
- `src/kgmaker/domain.py` may call `91 in `src/kgmaker/schema_replay.py`` (name match at line 150; src/kgmaker/domain.py:150; INFERRED 0.85)
- `src/kgmaker/domain.py` may call `91 in `src/kgmaker/schema_replay.py`` (name match at line 176; src/kgmaker/domain.py:176; INFERRED 0.85)
- `src/kgmaker/domain.py` may call `91 in `src/kgmaker/schema_replay.py`` (name match at line 222; src/kgmaker/domain.py:222; INFERRED 0.85)
- `src/kgmaker/domain.py` may call `91 in `src/kgmaker/schema_replay.py`` (name match at line 258; src/kgmaker/domain.py:258; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 166; src/kgmaker/feature.py:166; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 168; src/kgmaker/feature.py:168; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 193; src/kgmaker/feature.py:193; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 197; src/kgmaker/feature.py:197; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 202; src/kgmaker/feature.py:202; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 209; src/kgmaker/feature.py:209; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 304; src/kgmaker/feature.py:304; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 326; src/kgmaker/feature.py:326; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 330; src/kgmaker/feature.py:330; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 336; src/kgmaker/feature.py:336; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 338; src/kgmaker/feature.py:338; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 341; src/kgmaker/feature.py:341; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 343; src/kgmaker/feature.py:343; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 346; src/kgmaker/feature.py:346; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 350; src/kgmaker/feature.py:350; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 355; src/kgmaker/feature.py:355; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `27 in `src/kgmaker/model.py`` (name match at line 95; src/kgmaker/feature.py:95; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `67 in `src/kgmaker/analysis_model.py`` (name match at line 164; src/kgmaker/feature.py:164; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `67 in `src/kgmaker/analysis_model.py`` (name match at line 194; src/kgmaker/feature.py:194; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `89 in `src/kgmaker/analysis_model.py`` (name match at line 267; src/kgmaker/feature.py:267; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `37 in `src/kgmaker/analysis_model.py`` (name match at line 231; src/kgmaker/feature.py:231; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `37 in `src/kgmaker/analysis_model.py`` (name match at line 243; src/kgmaker/feature.py:243; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 132; src/kgmaker/feature.py:132; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 133; src/kgmaker/feature.py:133; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 160; src/kgmaker/feature.py:160; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 214; src/kgmaker/feature.py:214; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 307; src/kgmaker/feature.py:307; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `45 in `src/kgmaker/analysis_model.py`` (name match at line 134; src/kgmaker/feature.py:134; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `45 in `src/kgmaker/analysis_model.py`` (name match at line 186; src/kgmaker/feature.py:186; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `45 in `src/kgmaker/analysis_model.py`` (name match at line 208; src/kgmaker/feature.py:208; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `135 in `src/kgmaker/analysis_model.py`` (name match at line 270; src/kgmaker/feature.py:270; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `135 in `src/kgmaker/analysis_model.py`` (name match at line 315; src/kgmaker/feature.py:315; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `73 in `src/kgmaker/analysis_model.py`` (name match at line 164; src/kgmaker/feature.py:164; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `73 in `src/kgmaker/analysis_model.py`` (name match at line 300; src/kgmaker/feature.py:300; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `73 in `src/kgmaker/analysis_model.py`` (name match at line 315; src/kgmaker/feature.py:315; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `73 in `src/kgmaker/analysis_model.py`` (name match at line 327; src/kgmaker/feature.py:327; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 108; src/kgmaker/feature.py:108; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 131; src/kgmaker/feature.py:131; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 140; src/kgmaker/feature.py:140; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 185; src/kgmaker/feature.py:185; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 195; src/kgmaker/feature.py:195; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 266; src/kgmaker/feature.py:266; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 267; src/kgmaker/feature.py:267; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 268; src/kgmaker/feature.py:268; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 270; src/kgmaker/feature.py:270; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 298; src/kgmaker/feature.py:298; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 305; src/kgmaker/feature.py:305; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 306; src/kgmaker/feature.py:306; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 314; src/kgmaker/feature.py:314; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 324; src/kgmaker/feature.py:324; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `103 in `src/kgmaker/analysis_model.py`` (name match at line 266; src/kgmaker/feature.py:266; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `103 in `src/kgmaker/analysis_model.py`` (name match at line 268; src/kgmaker/feature.py:268; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `103 in `src/kgmaker/analysis_model.py`` (name match at line 270; src/kgmaker/feature.py:270; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `103 in `src/kgmaker/analysis_model.py`` (name match at line 305; src/kgmaker/feature.py:305; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `103 in `src/kgmaker/analysis_model.py`` (name match at line 306; src/kgmaker/feature.py:306; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `103 in `src/kgmaker/analysis_model.py`` (name match at line 308; src/kgmaker/feature.py:308; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `110 in `src/kgmaker/analysis_validation.py`` (name match at line 278; src/kgmaker/feature.py:278; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `14 in `src/kgmaker/availability.py`` (name match at line 284; src/kgmaker/feature.py:284; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `61 in `src/kgmaker/dataflow.py`` (name match at line 140; src/kgmaker/feature.py:140; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 107; src/kgmaker/feature.py:107; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `146 in `src/kgmaker/dataflow.py`` (name match at line 27; src/kgmaker/feature.py:27; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `31 in `src/kgmaker/flyway.py`` (name match at line 148; src/kgmaker/feature.py:148; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `31 in `src/kgmaker/flyway.py`` (name match at line 65; src/kgmaker/feature.py:65; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `39 in `src/kgmaker/graph_provider.py`` (name match at line 61; src/kgmaker/feature.py:61; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `246 in `src/kgmaker/scanner.py`` (name match at line 61; src/kgmaker/feature.py:61; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 105; src/kgmaker/feature.py:105; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 112; src/kgmaker/feature.py:112; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 165; src/kgmaker/feature.py:165; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 167; src/kgmaker/feature.py:167; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 173; src/kgmaker/feature.py:173; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 179; src/kgmaker/feature.py:179; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 183; src/kgmaker/feature.py:183; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 204; src/kgmaker/feature.py:204; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 210; src/kgmaker/feature.py:210; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 217; src/kgmaker/feature.py:217; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 251; src/kgmaker/feature.py:251; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 254; src/kgmaker/feature.py:254; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 286; src/kgmaker/feature.py:286; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 288; src/kgmaker/feature.py:288; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 344; src/kgmaker/feature.py:344; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 354; src/kgmaker/feature.py:354; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `472 in `src/kgmaker/schema_replay.py`` (name match at line 80; src/kgmaker/feature.py:80; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `394 in `src/kgmaker/schema_replay.py`` (name match at line 151; src/kgmaker/feature.py:151; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `394 in `src/kgmaker/schema_replay.py`` (name match at line 68; src/kgmaker/feature.py:68; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `510 in `src/kgmaker/schema_replay.py`` (name match at line 152; src/kgmaker/feature.py:152; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `510 in `src/kgmaker/schema_replay.py`` (name match at line 98; src/kgmaker/feature.py:98; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `561 in `src/kgmaker/semantic.py`` (name match at line 61; src/kgmaker/feature.py:61; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `101 in `src/kgmaker/workspace.py`` (name match at line 119; src/kgmaker/feature.py:119; INFERRED 0.85)
- `src/kgmaker/feature.py` may call `101 in `src/kgmaker/workspace.py`` (name match at line 59; src/kgmaker/feature.py:59; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 100; src/kgmaker/feature_cli.py:100; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 105; src/kgmaker/feature_cli.py:105; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 48; src/kgmaker/feature_cli.py:48; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 70; src/kgmaker/feature_cli.py:70; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 84; src/kgmaker/feature_cli.py:84; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 93; src/kgmaker/feature_cli.py:93; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `89 in `src/kgmaker/analysis_model.py`` (name match at line 108; src/kgmaker/feature_cli.py:108; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 92; src/kgmaker/feature_cli.py:92; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `135 in `src/kgmaker/analysis_model.py`` (name match at line 52; src/kgmaker/feature_cli.py:52; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `135 in `src/kgmaker/analysis_model.py`` (name match at line 63; src/kgmaker/feature_cli.py:63; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `135 in `src/kgmaker/analysis_model.py`` (name match at line 78; src/kgmaker/feature_cli.py:78; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `73 in `src/kgmaker/analysis_model.py`` (name match at line 127; src/kgmaker/feature_cli.py:127; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `73 in `src/kgmaker/analysis_model.py`` (name match at line 56; src/kgmaker/feature_cli.py:56; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `73 in `src/kgmaker/analysis_model.py`` (name match at line 58; src/kgmaker/feature_cli.py:58; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `73 in `src/kgmaker/analysis_model.py`` (name match at line 61; src/kgmaker/feature_cli.py:61; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `73 in `src/kgmaker/analysis_model.py`` (name match at line 65; src/kgmaker/feature_cli.py:65; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `73 in `src/kgmaker/analysis_model.py`` (name match at line 78; src/kgmaker/feature_cli.py:78; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `73 in `src/kgmaker/analysis_model.py`` (name match at line 82; src/kgmaker/feature_cli.py:82; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `73 in `src/kgmaker/analysis_model.py`` (name match at line 91; src/kgmaker/feature_cli.py:91; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 106; src/kgmaker/feature_cli.py:106; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 127; src/kgmaker/feature_cli.py:127; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 56; src/kgmaker/feature_cli.py:56; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 58; src/kgmaker/feature_cli.py:58; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 61; src/kgmaker/feature_cli.py:61; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 65; src/kgmaker/feature_cli.py:65; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 77; src/kgmaker/feature_cli.py:77; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 82; src/kgmaker/feature_cli.py:82; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 91; src/kgmaker/feature_cli.py:91; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `110 in `src/kgmaker/analysis_validation.py`` (name match at line 98; src/kgmaker/feature_cli.py:98; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `14 in `src/kgmaker/availability.py`` (name match at line 87; src/kgmaker/feature_cli.py:87; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `35 in `src/kgmaker/data_check.py`` (name match at line 56; src/kgmaker/feature_cli.py:56; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `283 in `src/kgmaker/dataflow.py`` (name match at line 152; src/kgmaker/feature_cli.py:152; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 42; src/kgmaker/feature_cli.py:42; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 47; src/kgmaker/feature_cli.py:47; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `53 in `src/kgmaker/feature.py`` (name match at line 151; src/kgmaker/feature_cli.py:151; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `170 in `src/kgmaker/feature.py`` (name match at line 85; src/kgmaker/feature_cli.py:85; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `109 in `src/kgmaker/feature.py`` (name match at line 130; src/kgmaker/feature_cli.py:130; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `161 in `src/kgmaker/feature.py`` (name match at line 130; src/kgmaker/feature_cli.py:130; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `161 in `src/kgmaker/feature.py`` (name match at line 46; src/kgmaker/feature_cli.py:46; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `161 in `src/kgmaker/feature.py`` (name match at line 76; src/kgmaker/feature_cli.py:76; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `157 in `src/kgmaker/feature.py`` (name match at line 83; src/kgmaker/feature_cli.py:83; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `189 in `src/kgmaker/feature.py`` (name match at line 50; src/kgmaker/feature_cli.py:50; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `319 in `src/kgmaker/feature.py`` (name match at line 61; src/kgmaker/feature_cli.py:61; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `272 in `src/kgmaker/feature.py`` (name match at line 128; src/kgmaker/feature_cli.py:128; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `272 in `src/kgmaker/feature.py`` (name match at line 66; src/kgmaker/feature_cli.py:66; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 110; src/kgmaker/feature_cli.py:110; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 112; src/kgmaker/feature_cli.py:112; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 47; src/kgmaker/feature_cli.py:47; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 81; src/kgmaker/feature_cli.py:81; INFERRED 0.85)
- `src/kgmaker/feature_cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 83; src/kgmaker/feature_cli.py:83; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 136; src/kgmaker/flow.py:136; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 18; src/kgmaker/flow.py:18; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 22; src/kgmaker/flow.py:22; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 25; src/kgmaker/flow.py:25; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 65; src/kgmaker/flow.py:65; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 69; src/kgmaker/flow.py:69; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 73; src/kgmaker/flow.py:73; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 127; src/kgmaker/flow.py:127; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 47; src/kgmaker/flow.py:47; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 80; src/kgmaker/flow.py:80; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 84; src/kgmaker/flow.py:84; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `89 in `src/kgmaker/callgraph.py`` (name match at line 119; src/kgmaker/flow.py:119; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 114; src/kgmaker/flow.py:114; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 115; src/kgmaker/flow.py:115; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 129; src/kgmaker/flow.py:129; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 130; src/kgmaker/flow.py:130; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 137; src/kgmaker/flow.py:137; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 140; src/kgmaker/flow.py:140; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 149; src/kgmaker/flow.py:149; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 150; src/kgmaker/flow.py:150; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 151; src/kgmaker/flow.py:151; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 153; src/kgmaker/flow.py:153; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 154; src/kgmaker/flow.py:154; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 155; src/kgmaker/flow.py:155; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 156; src/kgmaker/flow.py:156; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 157; src/kgmaker/flow.py:157; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 158; src/kgmaker/flow.py:158; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 20; src/kgmaker/flow.py:20; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 22; src/kgmaker/flow.py:22; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 53; src/kgmaker/flow.py:53; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 54; src/kgmaker/flow.py:54; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 55; src/kgmaker/flow.py:55; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 67; src/kgmaker/flow.py:67; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 83; src/kgmaker/flow.py:83; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 86; src/kgmaker/flow.py:86; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 89; src/kgmaker/flow.py:89; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 92; src/kgmaker/flow.py:92; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 93; src/kgmaker/flow.py:93; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 94; src/kgmaker/flow.py:94; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `17 in `src/kgmaker/views.py`` (name match at line 19; src/kgmaker/flow.py:19; INFERRED 0.85)
- `src/kgmaker/flow.py` may call `17 in `src/kgmaker/views.py`` (name match at line 66; src/kgmaker/flow.py:66; INFERRED 0.85)
- `src/kgmaker/flyway.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 131; src/kgmaker/flyway.py:131; INFERRED 0.85)
- `src/kgmaker/flyway.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 135; src/kgmaker/flyway.py:135; INFERRED 0.85)
- `src/kgmaker/flyway.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 138; src/kgmaker/flyway.py:138; INFERRED 0.85)
- `src/kgmaker/flyway.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 141; src/kgmaker/flyway.py:141; INFERRED 0.85)
- `src/kgmaker/flyway.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 143; src/kgmaker/flyway.py:143; INFERRED 0.85)
- `src/kgmaker/flyway.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 26; src/kgmaker/flyway.py:26; INFERRED 0.85)
- `src/kgmaker/flyway.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 36; src/kgmaker/flyway.py:36; INFERRED 0.85)
- `src/kgmaker/flyway.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 44; src/kgmaker/flyway.py:44; INFERRED 0.85)
- `src/kgmaker/flyway.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 228; src/kgmaker/flyway.py:228; INFERRED 0.85)
- `src/kgmaker/flyway.py` may call `45 in `src/kgmaker/analysis_model.py`` (name match at line 127; src/kgmaker/flyway.py:127; INFERRED 0.85)
- `src/kgmaker/flyway.py` may call `45 in `src/kgmaker/analysis_model.py`` (name match at line 190; src/kgmaker/flyway.py:190; INFERRED 0.85)
- `src/kgmaker/flyway.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 162; src/kgmaker/flyway.py:162; INFERRED 0.85)
- `src/kgmaker/flyway.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 170; src/kgmaker/flyway.py:170; INFERRED 0.85)
- `src/kgmaker/flyway.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 55; src/kgmaker/flyway.py:55; INFERRED 0.85)
- `src/kgmaker/flyway.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 119; src/kgmaker/flyway.py:119; INFERRED 0.85)
- `src/kgmaker/flyway.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 212; src/kgmaker/flyway.py:212; INFERRED 0.85)
- `src/kgmaker/flyway.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 38; src/kgmaker/flyway.py:38; INFERRED 0.85)
- `src/kgmaker/flyway.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 89; src/kgmaker/flyway.py:89; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 141; src/kgmaker/framework.py:141; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `27 in `src/kgmaker/model.py`` (name match at line 173; src/kgmaker/framework.py:173; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `10 in `src/kgmaker/model.py`` (name match at line 180; src/kgmaker/framework.py:180; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 129; src/kgmaker/framework.py:129; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 157; src/kgmaker/framework.py:157; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 122; src/kgmaker/framework.py:122; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 110; src/kgmaker/framework.py:110; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 139; src/kgmaker/framework.py:139; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 143; src/kgmaker/framework.py:143; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 145; src/kgmaker/framework.py:145; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 156; src/kgmaker/framework.py:156; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 183; src/kgmaker/framework.py:183; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 189; src/kgmaker/framework.py:189; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 207; src/kgmaker/framework.py:207; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 208; src/kgmaker/framework.py:208; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 210; src/kgmaker/framework.py:210; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 211; src/kgmaker/framework.py:211; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 212; src/kgmaker/framework.py:212; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 215; src/kgmaker/framework.py:215; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 221; src/kgmaker/framework.py:221; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 223; src/kgmaker/framework.py:223; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 231; src/kgmaker/framework.py:231; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 235; src/kgmaker/framework.py:235; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 250; src/kgmaker/framework.py:250; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 251; src/kgmaker/framework.py:251; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 258; src/kgmaker/framework.py:258; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 261; src/kgmaker/framework.py:261; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 272; src/kgmaker/framework.py:272; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 273; src/kgmaker/framework.py:273; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 281; src/kgmaker/framework.py:281; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 310; src/kgmaker/framework.py:310; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 314; src/kgmaker/framework.py:314; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 320; src/kgmaker/framework.py:320; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 322; src/kgmaker/framework.py:322; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 323; src/kgmaker/framework.py:323; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 325; src/kgmaker/framework.py:325; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 327; src/kgmaker/framework.py:327; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 331; src/kgmaker/framework.py:331; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 369; src/kgmaker/framework.py:369; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 457; src/kgmaker/framework.py:457; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 460; src/kgmaker/framework.py:460; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 461; src/kgmaker/framework.py:461; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 463; src/kgmaker/framework.py:463; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 475; src/kgmaker/framework.py:475; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 96; src/kgmaker/framework.py:96; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 97; src/kgmaker/framework.py:97; INFERRED 0.85)
- `src/kgmaker/framework.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 98; src/kgmaker/framework.py:98; INFERRED 0.85)
- `src/kgmaker/graph_provider.py` may call `26 in `src/kgmaker/classification.py`` (name match at line 22; src/kgmaker/graph_provider.py:22; INFERRED 0.85)
- `src/kgmaker/graph_provider.py` may call `18 in `src/kgmaker/worker_protocol.py`` (name match at line 18; src/kgmaker/graph_provider.py:18; INFERRED 0.85)
- `src/kgmaker/graph_provider.py` may call `18 in `src/kgmaker/worker_protocol.py`` (name match at line 23; src/kgmaker/graph_provider.py:23; INFERRED 0.85)
- `src/kgmaker/graph_provider.py` may call `18 in `src/kgmaker/worker_protocol.py`` (name match at line 31; src/kgmaker/graph_provider.py:31; INFERRED 0.85)
- `src/kgmaker/graph_provider.py` may call `18 in `src/kgmaker/worker_protocol.py`` (name match at line 35; src/kgmaker/graph_provider.py:35; INFERRED 0.85)
- `src/kgmaker/graph_provider.py` may call `18 in `src/kgmaker/worker_protocol.py`` (name match at line 38; src/kgmaker/graph_provider.py:38; INFERRED 0.85)
- `src/kgmaker/graph_provider.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 22; src/kgmaker/graph_provider.py:22; INFERRED 0.85)
- `src/kgmaker/graph_provider.py` may call `45 in `src/kgmaker/analysis_model.py`` (name match at line 17; src/kgmaker/graph_provider.py:17; INFERRED 0.85)
- `src/kgmaker/graph_provider.py` may call `45 in `src/kgmaker/analysis_model.py`` (name match at line 34; src/kgmaker/graph_provider.py:34; INFERRED 0.85)
- `src/kgmaker/graph_provider.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 33; src/kgmaker/graph_provider.py:33; INFERRED 0.85)
- `src/kgmaker/graph_provider.py` may call `23 in `src/kgmaker/inspection.py`` (name match at line 37; src/kgmaker/graph_provider.py:37; INFERRED 0.85)
- `src/kgmaker/graph_provider.py` may call `246 in `src/kgmaker/scanner.py`` (name match at line 27; src/kgmaker/graph_provider.py:27; INFERRED 0.85)
- `src/kgmaker/graph_provider.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 16; src/kgmaker/graph_provider.py:16; INFERRED 0.85)
- `src/kgmaker/graph_provider.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 19; src/kgmaker/graph_provider.py:19; INFERRED 0.85)
- `src/kgmaker/graph_provider.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 24; src/kgmaker/graph_provider.py:24; INFERRED 0.85)
- `src/kgmaker/graph_provider.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 27; src/kgmaker/graph_provider.py:27; INFERRED 0.85)
- `src/kgmaker/graph_provider.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 30; src/kgmaker/graph_provider.py:30; INFERRED 0.85)
- `src/kgmaker/graph_provider.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 32; src/kgmaker/graph_provider.py:32; INFERRED 0.85)
- `src/kgmaker/graph_provider.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 36; src/kgmaker/graph_provider.py:36; INFERRED 0.85)
- `src/kgmaker/graph_provider.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 48; src/kgmaker/graph_provider.py:48; INFERRED 0.85)
- `src/kgmaker/graph_provider.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 51; src/kgmaker/graph_provider.py:51; INFERRED 0.85)
- `src/kgmaker/graph_provider.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 55; src/kgmaker/graph_provider.py:55; INFERRED 0.85)
- `src/kgmaker/graph_provider.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 56; src/kgmaker/graph_provider.py:56; INFERRED 0.85)
- `src/kgmaker/graph_provider.py` may call `54 in `src/kgmaker/store.py`` (name match at line 47; src/kgmaker/graph_provider.py:47; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 307; src/kgmaker/inspection.py:307; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 310; src/kgmaker/inspection.py:310; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 318; src/kgmaker/inspection.py:318; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 32; src/kgmaker/inspection.py:32; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 320; src/kgmaker/inspection.py:320; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 324; src/kgmaker/inspection.py:324; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 328; src/kgmaker/inspection.py:328; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 35; src/kgmaker/inspection.py:35; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `26 in `src/kgmaker/classification.py`` (name match at line 113; src/kgmaker/inspection.py:113; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `26 in `src/kgmaker/classification.py`` (name match at line 152; src/kgmaker/inspection.py:152; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `27 in `src/kgmaker/model.py`` (name match at line 176; src/kgmaker/inspection.py:176; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `42 in `src/kgmaker/model.py`` (name match at line 242; src/kgmaker/inspection.py:242; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `10 in `src/kgmaker/model.py`` (name match at line 193; src/kgmaker/inspection.py:193; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `10 in `src/kgmaker/model.py`` (name match at line 205; src/kgmaker/inspection.py:205; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `10 in `src/kgmaker/model.py`` (name match at line 216; src/kgmaker/inspection.py:216; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `10 in `src/kgmaker/model.py`` (name match at line 229; src/kgmaker/inspection.py:229; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `18 in `src/kgmaker/worker_protocol.py`` (name match at line 123; src/kgmaker/inspection.py:123; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `18 in `src/kgmaker/worker_protocol.py`` (name match at line 126; src/kgmaker/inspection.py:126; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `18 in `src/kgmaker/worker_protocol.py`` (name match at line 129; src/kgmaker/inspection.py:129; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `18 in `src/kgmaker/worker_protocol.py`` (name match at line 133; src/kgmaker/inspection.py:133; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `18 in `src/kgmaker/worker_protocol.py`` (name match at line 136; src/kgmaker/inspection.py:136; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `18 in `src/kgmaker/worker_protocol.py`` (name match at line 138; src/kgmaker/inspection.py:138; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `18 in `src/kgmaker/worker_protocol.py`` (name match at line 140; src/kgmaker/inspection.py:140; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `18 in `src/kgmaker/worker_protocol.py`` (name match at line 143; src/kgmaker/inspection.py:143; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `18 in `src/kgmaker/worker_protocol.py`` (name match at line 146; src/kgmaker/inspection.py:146; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `18 in `src/kgmaker/worker_protocol.py`` (name match at line 268; src/kgmaker/inspection.py:268; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `18 in `src/kgmaker/worker_protocol.py`` (name match at line 270; src/kgmaker/inspection.py:270; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `18 in `src/kgmaker/worker_protocol.py`` (name match at line 275; src/kgmaker/inspection.py:275; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `18 in `src/kgmaker/worker_protocol.py`` (name match at line 285; src/kgmaker/inspection.py:285; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `18 in `src/kgmaker/worker_protocol.py`` (name match at line 288; src/kgmaker/inspection.py:288; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `18 in `src/kgmaker/worker_protocol.py`` (name match at line 290; src/kgmaker/inspection.py:290; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `18 in `src/kgmaker/worker_protocol.py`` (name match at line 338; src/kgmaker/inspection.py:338; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `18 in `src/kgmaker/worker_protocol.py`` (name match at line 352; src/kgmaker/inspection.py:352; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `18 in `src/kgmaker/worker_protocol.py`` (name match at line 354; src/kgmaker/inspection.py:354; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `18 in `src/kgmaker/worker_protocol.py`` (name match at line 62; src/kgmaker/inspection.py:62; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `18 in `src/kgmaker/worker_protocol.py`` (name match at line 74; src/kgmaker/inspection.py:74; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `18 in `src/kgmaker/worker_protocol.py`` (name match at line 80; src/kgmaker/inspection.py:80; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 113; src/kgmaker/inspection.py:113; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 117; src/kgmaker/inspection.py:117; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 169; src/kgmaker/inspection.py:169; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 215; src/kgmaker/inspection.py:215; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 228; src/kgmaker/inspection.py:228; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 34; src/kgmaker/inspection.py:34; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `45 in `src/kgmaker/analysis_model.py`` (name match at line 267; src/kgmaker/inspection.py:267; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `45 in `src/kgmaker/analysis_model.py`` (name match at line 27; src/kgmaker/inspection.py:27; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `45 in `src/kgmaker/analysis_model.py`` (name match at line 284; src/kgmaker/inspection.py:284; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `45 in `src/kgmaker/analysis_model.py`` (name match at line 289; src/kgmaker/inspection.py:289; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `45 in `src/kgmaker/analysis_model.py`` (name match at line 33; src/kgmaker/inspection.py:33; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `45 in `src/kgmaker/analysis_model.py`` (name match at line 353; src/kgmaker/inspection.py:353; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `45 in `src/kgmaker/analysis_model.py`` (name match at line 87; src/kgmaker/inspection.py:87; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `58 in `src/kgmaker/classification.py`` (name match at line 183; src/kgmaker/inspection.py:183; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `58 in `src/kgmaker/classification.py`` (name match at line 227; src/kgmaker/inspection.py:227; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `219 in `src/kgmaker/control_flow.py`` (name match at line 231; src/kgmaker/inspection.py:231; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 253; src/kgmaker/inspection.py:253; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 300; src/kgmaker/inspection.py:300; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 314; src/kgmaker/inspection.py:314; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 332; src/kgmaker/inspection.py:332; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 40; src/kgmaker/inspection.py:40; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 42; src/kgmaker/inspection.py:42; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 43; src/kgmaker/inspection.py:43; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 87; src/kgmaker/inspection.py:87; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `130 in `src/kgmaker/framework.py`` (name match at line 344; src/kgmaker/inspection.py:344; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `246 in `src/kgmaker/scanner.py`` (name match at line 257; src/kgmaker/inspection.py:257; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `246 in `src/kgmaker/scanner.py`` (name match at line 273; src/kgmaker/inspection.py:273; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `246 in `src/kgmaker/scanner.py`` (name match at line 276; src/kgmaker/inspection.py:276; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `246 in `src/kgmaker/scanner.py`` (name match at line 286; src/kgmaker/inspection.py:286; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `246 in `src/kgmaker/scanner.py`` (name match at line 304; src/kgmaker/inspection.py:304; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `246 in `src/kgmaker/scanner.py`` (name match at line 336; src/kgmaker/inspection.py:336; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `246 in `src/kgmaker/scanner.py`` (name match at line 350; src/kgmaker/inspection.py:350; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 114; src/kgmaker/inspection.py:114; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 122; src/kgmaker/inspection.py:122; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 125; src/kgmaker/inspection.py:125; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 127; src/kgmaker/inspection.py:127; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 132; src/kgmaker/inspection.py:132; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 135; src/kgmaker/inspection.py:135; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 137; src/kgmaker/inspection.py:137; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 139; src/kgmaker/inspection.py:139; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 142; src/kgmaker/inspection.py:142; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 145; src/kgmaker/inspection.py:145; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 163; src/kgmaker/inspection.py:163; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 164; src/kgmaker/inspection.py:164; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 165; src/kgmaker/inspection.py:165; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 166; src/kgmaker/inspection.py:166; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 167; src/kgmaker/inspection.py:167; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 175; src/kgmaker/inspection.py:175; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 177; src/kgmaker/inspection.py:177; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 182; src/kgmaker/inspection.py:182; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 184; src/kgmaker/inspection.py:184; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 187; src/kgmaker/inspection.py:187; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 190; src/kgmaker/inspection.py:190; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 192; src/kgmaker/inspection.py:192; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 193; src/kgmaker/inspection.py:193; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 194; src/kgmaker/inspection.py:194; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 195; src/kgmaker/inspection.py:195; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 204; src/kgmaker/inspection.py:204; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 205; src/kgmaker/inspection.py:205; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 206; src/kgmaker/inspection.py:206; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 207; src/kgmaker/inspection.py:207; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 208; src/kgmaker/inspection.py:208; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 209; src/kgmaker/inspection.py:209; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 210; src/kgmaker/inspection.py:210; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 212; src/kgmaker/inspection.py:212; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 220; src/kgmaker/inspection.py:220; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 222; src/kgmaker/inspection.py:222; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 224; src/kgmaker/inspection.py:224; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 232; src/kgmaker/inspection.py:232; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 235; src/kgmaker/inspection.py:235; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 236; src/kgmaker/inspection.py:236; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 238; src/kgmaker/inspection.py:238; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 240; src/kgmaker/inspection.py:240; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 241; src/kgmaker/inspection.py:241; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 244; src/kgmaker/inspection.py:244; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 283; src/kgmaker/inspection.py:283; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 317; src/kgmaker/inspection.py:317; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 319; src/kgmaker/inspection.py:319; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 323; src/kgmaker/inspection.py:323; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 327; src/kgmaker/inspection.py:327; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 337; src/kgmaker/inspection.py:337; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 351; src/kgmaker/inspection.py:351; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 41; src/kgmaker/inspection.py:41; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `37 in `src/kgmaker/store.py`` (name match at line 292; src/kgmaker/inspection.py:292; INFERRED 0.85)
- `src/kgmaker/inspection.py` may call `37 in `src/kgmaker/store.py`` (name match at line 356; src/kgmaker/inspection.py:356; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 106; src/kgmaker/inspection_cli.py:106; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 173; src/kgmaker/inspection_cli.py:173; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 75; src/kgmaker/inspection_cli.py:75; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 77; src/kgmaker/inspection_cli.py:77; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 84; src/kgmaker/inspection_cli.py:84; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 88; src/kgmaker/inspection_cli.py:88; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 90; src/kgmaker/inspection_cli.py:90; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `73 in `src/kgmaker/analysis_model.py`` (name match at line 109; src/kgmaker/inspection_cli.py:109; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `73 in `src/kgmaker/analysis_model.py`` (name match at line 122; src/kgmaker/inspection_cli.py:122; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `73 in `src/kgmaker/analysis_model.py`` (name match at line 99; src/kgmaker/inspection_cli.py:99; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 119; src/kgmaker/inspection_cli.py:119; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `96 in `src/kgmaker/build_model.py`` (name match at line 122; src/kgmaker/inspection_cli.py:122; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `41 in `src/kgmaker/callgraph.py`` (name match at line 133; src/kgmaker/inspection_cli.py:133; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `50 in `src/kgmaker/callgraph.py`` (name match at line 135; src/kgmaker/inspection_cli.py:135; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `61 in `src/kgmaker/callgraph.py`` (name match at line 137; src/kgmaker/inspection_cli.py:137; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 122; src/kgmaker/inspection_cli.py:122; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 72; src/kgmaker/inspection_cli.py:72; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 99; src/kgmaker/inspection_cli.py:99; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `14 in `src/kgmaker/flow.py`` (name match at line 164; src/kgmaker/inspection_cli.py:164; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `143 in `src/kgmaker/flow.py`` (name match at line 178; src/kgmaker/inspection_cli.py:178; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `122 in `src/kgmaker/flow.py`` (name match at line 175; src/kgmaker/inspection_cli.py:175; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `56 in `src/kgmaker/flow.py`` (name match at line 166; src/kgmaker/inspection_cli.py:166; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `8 in `src/kgmaker/graph_provider.py`` (name match at line 79; src/kgmaker/inspection_cli.py:79; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 111; src/kgmaker/inspection_cli.py:111; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 112; src/kgmaker/inspection_cli.py:112; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 151; src/kgmaker/inspection_cli.py:151; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 155; src/kgmaker/inspection_cli.py:155; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 157; src/kgmaker/inspection_cli.py:157; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 181; src/kgmaker/inspection_cli.py:181; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 80; src/kgmaker/inspection_cli.py:80; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 86; src/kgmaker/inspection_cli.py:86; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `54 in `src/kgmaker/store.py`` (name match at line 73; src/kgmaker/inspection_cli.py:73; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `17 in `src/kgmaker/views.py`` (name match at line 141; src/kgmaker/inspection_cli.py:141; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `17 in `src/kgmaker/views.py`` (name match at line 169; src/kgmaker/inspection_cli.py:169; INFERRED 0.85)
- `src/kgmaker/inspection_cli.py` may call `17 in `src/kgmaker/views.py`` (name match at line 92; src/kgmaker/inspection_cli.py:92; INFERRED 0.85)
- `src/kgmaker/memory.py` may call `27 in `src/kgmaker/model.py`` (name match at line 154; src/kgmaker/memory.py:154; INFERRED 0.85)
- `src/kgmaker/memory.py` may call `10 in `src/kgmaker/model.py`` (name match at line 152; src/kgmaker/memory.py:152; INFERRED 0.85)
- `src/kgmaker/memory.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 337; src/kgmaker/memory.py:337; INFERRED 0.85)
- `src/kgmaker/memory.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 338; src/kgmaker/memory.py:338; INFERRED 0.85)
- `src/kgmaker/memory.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 137; src/kgmaker/memory.py:137; INFERRED 0.85)
- `src/kgmaker/memory.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 197; src/kgmaker/memory.py:197; INFERRED 0.85)
- `src/kgmaker/memory.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 198; src/kgmaker/memory.py:198; INFERRED 0.85)
- `src/kgmaker/memory.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 199; src/kgmaker/memory.py:199; INFERRED 0.85)
- `src/kgmaker/memory.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 200; src/kgmaker/memory.py:200; INFERRED 0.85)
- `src/kgmaker/memory.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 203; src/kgmaker/memory.py:203; INFERRED 0.85)
- `src/kgmaker/memory.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 212; src/kgmaker/memory.py:212; INFERRED 0.85)
- `src/kgmaker/memory.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 213; src/kgmaker/memory.py:213; INFERRED 0.85)
- `src/kgmaker/memory.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 214; src/kgmaker/memory.py:214; INFERRED 0.85)
- `src/kgmaker/memory.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 215; src/kgmaker/memory.py:215; INFERRED 0.85)
- `src/kgmaker/memory.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 223; src/kgmaker/memory.py:223; INFERRED 0.85)
- `src/kgmaker/memory.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 224; src/kgmaker/memory.py:224; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 109; src/kgmaker/model.py:109; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 128; src/kgmaker/model.py:128; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 129; src/kgmaker/model.py:129; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 132; src/kgmaker/model.py:132; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 134; src/kgmaker/model.py:134; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 146; src/kgmaker/model.py:146; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 152; src/kgmaker/model.py:152; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 155; src/kgmaker/model.py:155; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 156; src/kgmaker/model.py:156; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 160; src/kgmaker/model.py:160; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 161; src/kgmaker/model.py:161; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 163; src/kgmaker/model.py:163; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 165; src/kgmaker/model.py:165; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 168; src/kgmaker/model.py:168; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 170; src/kgmaker/model.py:170; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 172; src/kgmaker/model.py:172; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 174; src/kgmaker/model.py:174; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 175; src/kgmaker/model.py:175; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 177; src/kgmaker/model.py:177; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 178; src/kgmaker/model.py:178; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 180; src/kgmaker/model.py:180; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 182; src/kgmaker/model.py:182; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 185; src/kgmaker/model.py:185; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 187; src/kgmaker/model.py:187; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 191; src/kgmaker/model.py:191; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 192; src/kgmaker/model.py:192; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 195; src/kgmaker/model.py:195; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 196; src/kgmaker/model.py:196; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 197; src/kgmaker/model.py:197; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 198; src/kgmaker/model.py:198; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 199; src/kgmaker/model.py:199; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 200; src/kgmaker/model.py:200; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 201; src/kgmaker/model.py:201; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 202; src/kgmaker/model.py:202; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 91; src/kgmaker/model.py:91; INFERRED 0.85)
- `src/kgmaker/model.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 95; src/kgmaker/model.py:95; INFERRED 0.85)
- `src/kgmaker/project_cli.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 109; src/kgmaker/project_cli.py:109; INFERRED 0.85)
- `src/kgmaker/project_cli.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 79; src/kgmaker/project_cli.py:79; INFERRED 0.85)
- `src/kgmaker/project_cli.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 82; src/kgmaker/project_cli.py:82; INFERRED 0.85)
- `src/kgmaker/project_cli.py` may call `73 in `src/kgmaker/analysis_model.py`` (name match at line 104; src/kgmaker/project_cli.py:104; INFERRED 0.85)
- `src/kgmaker/project_cli.py` may call `73 in `src/kgmaker/analysis_model.py`` (name match at line 85; src/kgmaker/project_cli.py:85; INFERRED 0.85)
- `src/kgmaker/project_cli.py` may call `73 in `src/kgmaker/analysis_model.py`` (name match at line 98; src/kgmaker/project_cli.py:98; INFERRED 0.85)
- `src/kgmaker/project_cli.py` may call `103 in `src/kgmaker/analysis_model.py`` (name match at line 95; src/kgmaker/project_cli.py:95; INFERRED 0.85)
- `src/kgmaker/project_cli.py` may call `79 in `src/kgmaker/build_maven.py`` (name match at line 122; src/kgmaker/project_cli.py:122; INFERRED 0.85)
- `src/kgmaker/project_cli.py` may call `96 in `src/kgmaker/build_runner.py`` (name match at line 98; src/kgmaker/project_cli.py:98; INFERRED 0.85)
- `src/kgmaker/project_cli.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 73; src/kgmaker/project_cli.py:73; INFERRED 0.85)
- `src/kgmaker/project_cli.py` may call `69 in `src/kgmaker/inspection_cli.py`` (name match at line 137; src/kgmaker/project_cli.py:137; INFERRED 0.85)
- `src/kgmaker/project_cli.py` may call `56 in `src/kgmaker/model.py`` (name match at line 110; src/kgmaker/project_cli.py:110; INFERRED 0.85)
- `src/kgmaker/project_cli.py` may call `246 in `src/kgmaker/scanner.py`` (name match at line 115; src/kgmaker/project_cli.py:115; INFERRED 0.85)
- `src/kgmaker/project_cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 155; src/kgmaker/project_cli.py:155; INFERRED 0.85)
- `src/kgmaker/project_cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 156; src/kgmaker/project_cli.py:156; INFERRED 0.85)
- `src/kgmaker/project_cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 157; src/kgmaker/project_cli.py:157; INFERRED 0.85)
- `src/kgmaker/project_cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 158; src/kgmaker/project_cli.py:158; INFERRED 0.85)
- `src/kgmaker/project_cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 159; src/kgmaker/project_cli.py:159; INFERRED 0.85)
- `src/kgmaker/project_cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 160; src/kgmaker/project_cli.py:160; INFERRED 0.85)
- `src/kgmaker/project_cli.py` may call `54 in `src/kgmaker/store.py`` (name match at line 107; src/kgmaker/project_cli.py:107; INFERRED 0.85)
- `src/kgmaker/project_cli.py` may call `54 in `src/kgmaker/store.py`` (name match at line 133; src/kgmaker/project_cli.py:133; INFERRED 0.85)
- `src/kgmaker/project_cli.py` may call `37 in `src/kgmaker/store.py`` (name match at line 111; src/kgmaker/project_cli.py:111; INFERRED 0.85)
- `src/kgmaker/project_cli.py` may call `17 in `src/kgmaker/views.py`` (name match at line 143; src/kgmaker/project_cli.py:143; INFERRED 0.85)
- `src/kgmaker/project_cli.py` may call `62 in `src/kgmaker/views.py`` (name match at line 140; src/kgmaker/project_cli.py:140; INFERRED 0.85)
- `src/kgmaker/project_cli.py` may call `32 in `src/kgmaker/workspace.py`` (name match at line 76; src/kgmaker/project_cli.py:76; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 22; src/kgmaker/runtime_evidence.py:22; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 26; src/kgmaker/runtime_evidence.py:26; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 31; src/kgmaker/runtime_evidence.py:31; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 35; src/kgmaker/runtime_evidence.py:35; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 40; src/kgmaker/runtime_evidence.py:40; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 43; src/kgmaker/runtime_evidence.py:43; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 46; src/kgmaker/runtime_evidence.py:46; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 49; src/kgmaker/runtime_evidence.py:49; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 52; src/kgmaker/runtime_evidence.py:52; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 54; src/kgmaker/runtime_evidence.py:54; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 59; src/kgmaker/runtime_evidence.py:59; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 61; src/kgmaker/runtime_evidence.py:61; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 63; src/kgmaker/runtime_evidence.py:63; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 65; src/kgmaker/runtime_evidence.py:65; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 67; src/kgmaker/runtime_evidence.py:67; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 77; src/kgmaker/runtime_evidence.py:77; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `27 in `src/kgmaker/model.py`` (name match at line 90; src/kgmaker/runtime_evidence.py:90; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 88; src/kgmaker/runtime_evidence.py:88; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `45 in `src/kgmaker/analysis_model.py`` (name match at line 25; src/kgmaker/runtime_evidence.py:25; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `45 in `src/kgmaker/analysis_model.py`` (name match at line 34; src/kgmaker/runtime_evidence.py:34; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 24; src/kgmaker/runtime_evidence.py:24; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 72; src/kgmaker/runtime_evidence.py:72; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 19; src/kgmaker/runtime_evidence.py:19; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 20; src/kgmaker/runtime_evidence.py:20; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 27; src/kgmaker/runtime_evidence.py:27; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 28; src/kgmaker/runtime_evidence.py:28; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 29; src/kgmaker/runtime_evidence.py:29; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 39; src/kgmaker/runtime_evidence.py:39; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 42; src/kgmaker/runtime_evidence.py:42; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 44; src/kgmaker/runtime_evidence.py:44; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 47; src/kgmaker/runtime_evidence.py:47; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 51; src/kgmaker/runtime_evidence.py:51; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 53; src/kgmaker/runtime_evidence.py:53; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 60; src/kgmaker/runtime_evidence.py:60; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 64; src/kgmaker/runtime_evidence.py:64; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 66; src/kgmaker/runtime_evidence.py:66; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 83; src/kgmaker/runtime_evidence.py:83; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 86; src/kgmaker/runtime_evidence.py:86; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 87; src/kgmaker/runtime_evidence.py:87; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `54 in `src/kgmaker/store.py`` (name match at line 75; src/kgmaker/runtime_evidence.py:75; INFERRED 0.85)
- `src/kgmaker/runtime_evidence.py` may call `37 in `src/kgmaker/store.py`` (name match at line 101; src/kgmaker/runtime_evidence.py:101; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 358; src/kgmaker/scanner.py:358; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 360; src/kgmaker/scanner.py:360; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `26 in `src/kgmaker/classification.py`` (name match at line 250; src/kgmaker/scanner.py:250; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `26 in `src/kgmaker/classification.py`` (name match at line 359; src/kgmaker/scanner.py:359; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `27 in `src/kgmaker/model.py`` (name match at line 286; src/kgmaker/scanner.py:286; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `27 in `src/kgmaker/model.py`` (name match at line 300; src/kgmaker/scanner.py:300; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `27 in `src/kgmaker/model.py`` (name match at line 310; src/kgmaker/scanner.py:310; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `42 in `src/kgmaker/model.py`` (name match at line 388; src/kgmaker/scanner.py:388; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `10 in `src/kgmaker/model.py`` (name match at line 124; src/kgmaker/scanner.py:124; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `10 in `src/kgmaker/model.py`` (name match at line 153; src/kgmaker/scanner.py:153; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `10 in `src/kgmaker/model.py`` (name match at line 272; src/kgmaker/scanner.py:272; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 364; src/kgmaker/scanner.py:364; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 366; src/kgmaker/scanner.py:366; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 384; src/kgmaker/scanner.py:384; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `58 in `src/kgmaker/classification.py`` (name match at line 277; src/kgmaker/scanner.py:277; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `58 in `src/kgmaker/classification.py`` (name match at line 350; src/kgmaker/scanner.py:350; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `61 in `src/kgmaker/dataflow.py`` (name match at line 340; src/kgmaker/scanner.py:340; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 249; src/kgmaker/scanner.py:249; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `146 in `src/kgmaker/dataflow.py`` (name match at line 227; src/kgmaker/scanner.py:227; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `484 in `src/kgmaker/domain.py`` (name match at line 344; src/kgmaker/scanner.py:344; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `440 in `src/kgmaker/domain.py`` (name match at line 334; src/kgmaker/scanner.py:334; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `475 in `src/kgmaker/domain.py`` (name match at line 337; src/kgmaker/scanner.py:337; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `515 in `src/kgmaker/domain.py`` (name match at line 343; src/kgmaker/scanner.py:343; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 173; src/kgmaker/scanner.py:173; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 226; src/kgmaker/scanner.py:226; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 307; src/kgmaker/scanner.py:307; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 349; src/kgmaker/scanner.py:349; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 352; src/kgmaker/scanner.py:352; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 377; src/kgmaker/scanner.py:377; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 381; src/kgmaker/scanner.py:381; INFERRED 0.85)
- `src/kgmaker/scanner.py` may call `91 in `src/kgmaker/schema_replay.py`` (name match at line 178; src/kgmaker/scanner.py:178; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 117; src/kgmaker/schema_replay.py:117; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 127; src/kgmaker/schema_replay.py:127; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 140; src/kgmaker/schema_replay.py:140; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 152; src/kgmaker/schema_replay.py:152; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 160; src/kgmaker/schema_replay.py:160; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 188; src/kgmaker/schema_replay.py:188; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 211; src/kgmaker/schema_replay.py:211; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 214; src/kgmaker/schema_replay.py:214; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 238; src/kgmaker/schema_replay.py:238; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 254; src/kgmaker/schema_replay.py:254; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 268; src/kgmaker/schema_replay.py:268; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 271; src/kgmaker/schema_replay.py:271; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 284; src/kgmaker/schema_replay.py:284; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 289; src/kgmaker/schema_replay.py:289; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 293; src/kgmaker/schema_replay.py:293; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 301; src/kgmaker/schema_replay.py:301; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 307; src/kgmaker/schema_replay.py:307; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 313; src/kgmaker/schema_replay.py:313; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 319; src/kgmaker/schema_replay.py:319; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 325; src/kgmaker/schema_replay.py:325; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 339; src/kgmaker/schema_replay.py:339; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 365; src/kgmaker/schema_replay.py:365; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 389; src/kgmaker/schema_replay.py:389; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 391; src/kgmaker/schema_replay.py:391; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 393; src/kgmaker/schema_replay.py:393; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 408; src/kgmaker/schema_replay.py:408; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 44; src/kgmaker/schema_replay.py:44; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 58; src/kgmaker/schema_replay.py:58; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 73; src/kgmaker/schema_replay.py:73; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 89; src/kgmaker/schema_replay.py:89; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `27 in `src/kgmaker/model.py`` (name match at line 489; src/kgmaker/schema_replay.py:489; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `27 in `src/kgmaker/model.py`` (name match at line 493; src/kgmaker/schema_replay.py:493; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `27 in `src/kgmaker/model.py`` (name match at line 498; src/kgmaker/schema_replay.py:498; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `27 in `src/kgmaker/model.py`` (name match at line 505; src/kgmaker/schema_replay.py:505; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `27 in `src/kgmaker/model.py`` (name match at line 508; src/kgmaker/schema_replay.py:508; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `27 in `src/kgmaker/model.py`` (name match at line 545; src/kgmaker/schema_replay.py:545; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `10 in `src/kgmaker/model.py`` (name match at line 479; src/kgmaker/schema_replay.py:479; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `10 in `src/kgmaker/model.py`` (name match at line 484; src/kgmaker/schema_replay.py:484; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `10 in `src/kgmaker/model.py`` (name match at line 497; src/kgmaker/schema_replay.py:497; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `10 in `src/kgmaker/model.py`` (name match at line 503; src/kgmaker/schema_replay.py:503; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `10 in `src/kgmaker/model.py`` (name match at line 504; src/kgmaker/schema_replay.py:504; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 130; src/kgmaker/schema_replay.py:130; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 411; src/kgmaker/schema_replay.py:411; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 416; src/kgmaker/schema_replay.py:416; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `45 in `src/kgmaker/analysis_model.py`` (name match at line 410; src/kgmaker/schema_replay.py:410; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `73 in `src/kgmaker/analysis_model.py`` (name match at line 406; src/kgmaker/schema_replay.py:406; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 405; src/kgmaker/schema_replay.py:405; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 424; src/kgmaker/schema_replay.py:424; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 519; src/kgmaker/schema_replay.py:519; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 411; src/kgmaker/schema_replay.py:411; INFERRED 0.85)
- `src/kgmaker/schema_replay.py` may call `148 in `src/kgmaker/flyway.py`` (name match at line 397; src/kgmaker/schema_replay.py:397; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `27 in `src/kgmaker/model.py`` (name match at line 202; src/kgmaker/semantic.py:202; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `10 in `src/kgmaker/model.py`` (name match at line 152; src/kgmaker/semantic.py:152; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 195; src/kgmaker/semantic.py:195; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 267; src/kgmaker/semantic.py:267; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 268; src/kgmaker/semantic.py:268; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 384; src/kgmaker/semantic.py:384; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 93; src/kgmaker/semantic.py:93; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `145 in `src/kgmaker/memory.py`` (name match at line 222; src/kgmaker/semantic.py:222; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `62 in `src/kgmaker/memory.py`` (name match at line 216; src/kgmaker/semantic.py:216; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 103; src/kgmaker/semantic.py:103; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 104; src/kgmaker/semantic.py:104; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 110; src/kgmaker/semantic.py:110; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 112; src/kgmaker/semantic.py:112; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 119; src/kgmaker/semantic.py:119; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 121; src/kgmaker/semantic.py:121; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 131; src/kgmaker/semantic.py:131; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 132; src/kgmaker/semantic.py:132; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 138; src/kgmaker/semantic.py:138; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 140; src/kgmaker/semantic.py:140; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 146; src/kgmaker/semantic.py:146; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 148; src/kgmaker/semantic.py:148; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 160; src/kgmaker/semantic.py:160; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 167; src/kgmaker/semantic.py:167; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 168; src/kgmaker/semantic.py:168; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 180; src/kgmaker/semantic.py:180; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 184; src/kgmaker/semantic.py:184; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 186; src/kgmaker/semantic.py:186; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 190; src/kgmaker/semantic.py:190; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 297; src/kgmaker/semantic.py:297; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 345; src/kgmaker/semantic.py:345; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 358; src/kgmaker/semantic.py:358; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 362; src/kgmaker/semantic.py:362; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 363; src/kgmaker/semantic.py:363; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 364; src/kgmaker/semantic.py:364; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 367; src/kgmaker/semantic.py:367; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 369; src/kgmaker/semantic.py:369; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 371; src/kgmaker/semantic.py:371; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 375; src/kgmaker/semantic.py:375; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 376; src/kgmaker/semantic.py:376; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 377; src/kgmaker/semantic.py:377; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 378; src/kgmaker/semantic.py:378; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 379; src/kgmaker/semantic.py:379; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 402; src/kgmaker/semantic.py:402; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 403; src/kgmaker/semantic.py:403; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 406; src/kgmaker/semantic.py:406; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 407; src/kgmaker/semantic.py:407; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 412; src/kgmaker/semantic.py:412; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 413; src/kgmaker/semantic.py:413; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 421; src/kgmaker/semantic.py:421; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 433; src/kgmaker/semantic.py:433; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 443; src/kgmaker/semantic.py:443; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 444; src/kgmaker/semantic.py:444; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 446; src/kgmaker/semantic.py:446; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 447; src/kgmaker/semantic.py:447; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 449; src/kgmaker/semantic.py:449; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 450; src/kgmaker/semantic.py:450; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 451; src/kgmaker/semantic.py:451; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 462; src/kgmaker/semantic.py:462; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 464; src/kgmaker/semantic.py:464; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 466; src/kgmaker/semantic.py:466; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 467; src/kgmaker/semantic.py:467; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 468; src/kgmaker/semantic.py:468; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 470; src/kgmaker/semantic.py:470; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 472; src/kgmaker/semantic.py:472; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 478; src/kgmaker/semantic.py:478; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 482; src/kgmaker/semantic.py:482; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 484; src/kgmaker/semantic.py:484; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 486; src/kgmaker/semantic.py:486; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 487; src/kgmaker/semantic.py:487; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 489; src/kgmaker/semantic.py:489; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 490; src/kgmaker/semantic.py:490; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 491; src/kgmaker/semantic.py:491; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 493; src/kgmaker/semantic.py:493; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 496; src/kgmaker/semantic.py:496; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 497; src/kgmaker/semantic.py:497; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 502; src/kgmaker/semantic.py:502; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 503; src/kgmaker/semantic.py:503; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 516; src/kgmaker/semantic.py:516; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 518; src/kgmaker/semantic.py:518; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 519; src/kgmaker/semantic.py:519; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 527; src/kgmaker/semantic.py:527; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 528; src/kgmaker/semantic.py:528; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 533; src/kgmaker/semantic.py:533; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 534; src/kgmaker/semantic.py:534; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 535; src/kgmaker/semantic.py:535; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 536; src/kgmaker/semantic.py:536; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 537; src/kgmaker/semantic.py:537; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 538; src/kgmaker/semantic.py:538; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 541; src/kgmaker/semantic.py:541; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 542; src/kgmaker/semantic.py:542; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 544; src/kgmaker/semantic.py:544; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 545; src/kgmaker/semantic.py:545; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 549; src/kgmaker/semantic.py:549; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 557; src/kgmaker/semantic.py:557; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 571; src/kgmaker/semantic.py:571; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 572; src/kgmaker/semantic.py:572; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 573; src/kgmaker/semantic.py:573; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 576; src/kgmaker/semantic.py:576; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 578; src/kgmaker/semantic.py:578; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 579; src/kgmaker/semantic.py:579; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 580; src/kgmaker/semantic.py:580; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 582; src/kgmaker/semantic.py:582; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 583; src/kgmaker/semantic.py:583; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 584; src/kgmaker/semantic.py:584; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 585; src/kgmaker/semantic.py:585; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 590; src/kgmaker/semantic.py:590; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 591; src/kgmaker/semantic.py:591; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 594; src/kgmaker/semantic.py:594; INFERRED 0.85)
- `src/kgmaker/semantic.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 604; src/kgmaker/semantic.py:604; INFERRED 0.85)
- `src/kgmaker/store.py` may call `89 in `src/kgmaker/analysis_model.py`` (name match at line 49; src/kgmaker/store.py:49; INFERRED 0.85)
- `src/kgmaker/store.py` may call `89 in `src/kgmaker/analysis_model.py`` (name match at line 51; src/kgmaker/store.py:51; INFERRED 0.85)
- `src/kgmaker/store.py` may call `89 in `src/kgmaker/analysis_model.py`` (name match at line 52; src/kgmaker/store.py:52; INFERRED 0.85)
- `src/kgmaker/store.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 120; src/kgmaker/store.py:120; INFERRED 0.85)
- `src/kgmaker/store.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 135; src/kgmaker/store.py:135; INFERRED 0.85)
- `src/kgmaker/store.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 136; src/kgmaker/store.py:136; INFERRED 0.85)
- `src/kgmaker/store.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 138; src/kgmaker/store.py:138; INFERRED 0.85)
- `src/kgmaker/store.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 141; src/kgmaker/store.py:141; INFERRED 0.85)
- `src/kgmaker/store.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 142; src/kgmaker/store.py:142; INFERRED 0.85)
- `src/kgmaker/store.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 155; src/kgmaker/store.py:155; INFERRED 0.85)
- `src/kgmaker/store.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 159; src/kgmaker/store.py:159; INFERRED 0.85)
- `src/kgmaker/store.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 161; src/kgmaker/store.py:161; INFERRED 0.85)
- `src/kgmaker/store.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 162; src/kgmaker/store.py:162; INFERRED 0.85)
- `src/kgmaker/store.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 198; src/kgmaker/store.py:198; INFERRED 0.85)
- `src/kgmaker/store.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 199; src/kgmaker/store.py:199; INFERRED 0.85)
- `src/kgmaker/store.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 202; src/kgmaker/store.py:202; INFERRED 0.85)
- `src/kgmaker/store.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 203; src/kgmaker/store.py:203; INFERRED 0.85)
- `src/kgmaker/store.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 237; src/kgmaker/store.py:237; INFERRED 0.85)
- `src/kgmaker/store.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 254; src/kgmaker/store.py:254; INFERRED 0.85)
- `src/kgmaker/store.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 33; src/kgmaker/store.py:33; INFERRED 0.85)
- `src/kgmaker/store.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 95; src/kgmaker/store.py:95; INFERRED 0.85)
- `src/kgmaker/store.py` may call `17 in `src/kgmaker/views.py`` (name match at line 176; src/kgmaker/store.py:176; INFERRED 0.85)
- `src/kgmaker/store.py` may call `17 in `src/kgmaker/views.py`` (name match at line 19; src/kgmaker/store.py:19; INFERRED 0.85)
- `src/kgmaker/store.py` may call `17 in `src/kgmaker/views.py`` (name match at line 230; src/kgmaker/store.py:230; INFERRED 0.85)
- `src/kgmaker/store.py` may call `17 in `src/kgmaker/views.py`` (name match at line 67; src/kgmaker/store.py:67; INFERRED 0.85)
- `src/kgmaker/views.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 44; src/kgmaker/views.py:44; INFERRED 0.85)
- `src/kgmaker/views.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 46; src/kgmaker/views.py:46; INFERRED 0.85)
- `src/kgmaker/views.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 49; src/kgmaker/views.py:49; INFERRED 0.85)
- `src/kgmaker/views.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 53; src/kgmaker/views.py:53; INFERRED 0.85)
- `src/kgmaker/views.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 57; src/kgmaker/views.py:57; INFERRED 0.85)
- `src/kgmaker/views.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 58; src/kgmaker/views.py:58; INFERRED 0.85)
- `src/kgmaker/views.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 59; src/kgmaker/views.py:59; INFERRED 0.85)
- `src/kgmaker/views.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 60; src/kgmaker/views.py:60; INFERRED 0.85)
- `src/kgmaker/views.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 61; src/kgmaker/views.py:61; INFERRED 0.85)
- `src/kgmaker/worker_protocol.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 38; src/kgmaker/worker_protocol.py:38; INFERRED 0.85)
- `src/kgmaker/worker_protocol.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 40; src/kgmaker/worker_protocol.py:40; INFERRED 0.85)
- `src/kgmaker/worker_protocol.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 44; src/kgmaker/worker_protocol.py:44; INFERRED 0.85)
- `src/kgmaker/worker_protocol.py` may call `37 in `src/kgmaker/analysis_model.py`` (name match at line 42; src/kgmaker/worker_protocol.py:42; INFERRED 0.85)
- `src/kgmaker/worker_protocol.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 114; src/kgmaker/worker_protocol.py:114; INFERRED 0.85)
- `src/kgmaker/worker_protocol.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 116; src/kgmaker/worker_protocol.py:116; INFERRED 0.85)
- `src/kgmaker/worker_protocol.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 117; src/kgmaker/worker_protocol.py:117; INFERRED 0.85)
- `src/kgmaker/worker_protocol.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 119; src/kgmaker/worker_protocol.py:119; INFERRED 0.85)
- `src/kgmaker/worker_protocol.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 126; src/kgmaker/worker_protocol.py:126; INFERRED 0.85)
- `src/kgmaker/workflow.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 129; src/kgmaker/workflow.py:129; INFERRED 0.85)
- `src/kgmaker/workflow.py` may call `285 in `src/kgmaker/memory.py`` (name match at line 98; src/kgmaker/workflow.py:98; INFERRED 0.85)
- `src/kgmaker/workflow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 227; src/kgmaker/workflow.py:227; INFERRED 0.85)
- `src/kgmaker/workflow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 228; src/kgmaker/workflow.py:228; INFERRED 0.85)
- `src/kgmaker/workflow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 535; src/kgmaker/workflow.py:535; INFERRED 0.85)
- `src/kgmaker/workflow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 537; src/kgmaker/workflow.py:537; INFERRED 0.85)
- `src/kgmaker/workflow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 539; src/kgmaker/workflow.py:539; INFERRED 0.85)
- `src/kgmaker/workflow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 552; src/kgmaker/workflow.py:552; INFERRED 0.85)
- `src/kgmaker/workflow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 554; src/kgmaker/workflow.py:554; INFERRED 0.85)
- `src/kgmaker/workflow.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 556; src/kgmaker/workflow.py:556; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 134; src/kgmaker/workspace.py:134; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 152; src/kgmaker/workspace.py:152; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 186; src/kgmaker/workspace.py:186; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 188; src/kgmaker/workspace.py:188; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 190; src/kgmaker/workspace.py:190; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 23; src/kgmaker/workspace.py:23; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 26; src/kgmaker/workspace.py:26; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 40; src/kgmaker/workspace.py:40; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 42; src/kgmaker/workspace.py:42; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 46; src/kgmaker/workspace.py:46; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 49; src/kgmaker/workspace.py:49; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 51; src/kgmaker/workspace.py:51; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 54; src/kgmaker/workspace.py:54; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 57; src/kgmaker/workspace.py:57; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 60; src/kgmaker/workspace.py:60; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 65; src/kgmaker/workspace.py:65; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 69; src/kgmaker/workspace.py:69; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 73; src/kgmaker/workspace.py:73; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 75; src/kgmaker/workspace.py:75; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 79; src/kgmaker/workspace.py:79; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 82; src/kgmaker/workspace.py:82; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 87; src/kgmaker/workspace.py:87; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 96; src/kgmaker/workspace.py:96; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 99; src/kgmaker/workspace.py:99; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `26 in `src/kgmaker/classification.py`` (name match at line 121; src/kgmaker/workspace.py:121; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `42 in `src/kgmaker/model.py`` (name match at line 198; src/kgmaker/workspace.py:198; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 122; src/kgmaker/workspace.py:122; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 139; src/kgmaker/workspace.py:139; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 168; src/kgmaker/workspace.py:168; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 197; src/kgmaker/workspace.py:197; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 210; src/kgmaker/workspace.py:210; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 211; src/kgmaker/workspace.py:211; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `45 in `src/kgmaker/analysis_model.py`` (name match at line 124; src/kgmaker/workspace.py:124; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `45 in `src/kgmaker/analysis_model.py`` (name match at line 189; src/kgmaker/workspace.py:189; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `45 in `src/kgmaker/analysis_model.py`` (name match at line 89; src/kgmaker/workspace.py:89; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `73 in `src/kgmaker/analysis_model.py`` (name match at line 138; src/kgmaker/workspace.py:138; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `73 in `src/kgmaker/analysis_model.py`` (name match at line 36; src/kgmaker/workspace.py:36; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 100; src/kgmaker/workspace.py:100; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 135; src/kgmaker/workspace.py:135; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 196; src/kgmaker/workspace.py:196; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 83; src/kgmaker/workspace.py:83; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `103 in `src/kgmaker/analysis_model.py`` (name match at line 196; src/kgmaker/workspace.py:196; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 220; src/kgmaker/workspace.py:220; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 35; src/kgmaker/workspace.py:35; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 58; src/kgmaker/workspace.py:58; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `71 in `src/kgmaker/feature.py`` (name match at line 154; src/kgmaker/workspace.py:154; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `53 in `src/kgmaker/feature.py`` (name match at line 146; src/kgmaker/workspace.py:146; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `22 in `src/kgmaker/feature.py`` (name match at line 117; src/kgmaker/workspace.py:117; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `22 in `src/kgmaker/feature.py`` (name match at line 184; src/kgmaker/workspace.py:184; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 122; src/kgmaker/workspace.py:122; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 129; src/kgmaker/workspace.py:129; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 131; src/kgmaker/workspace.py:131; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 148; src/kgmaker/workspace.py:148; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 166; src/kgmaker/workspace.py:166; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 206; src/kgmaker/workspace.py:206; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 207; src/kgmaker/workspace.py:207; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 222; src/kgmaker/workspace.py:222; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 37; src/kgmaker/workspace.py:37; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 38; src/kgmaker/workspace.py:38; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 39; src/kgmaker/workspace.py:39; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 47; src/kgmaker/workspace.py:47; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 50; src/kgmaker/workspace.py:50; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 63; src/kgmaker/workspace.py:63; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 68; src/kgmaker/workspace.py:68; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 74; src/kgmaker/workspace.py:74; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 77; src/kgmaker/workspace.py:77; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 80; src/kgmaker/workspace.py:80; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 85; src/kgmaker/workspace.py:85; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 94; src/kgmaker/workspace.py:94; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `394 in `src/kgmaker/schema_replay.py`` (name match at line 150; src/kgmaker/workspace.py:150; INFERRED 0.85)
- `src/kgmaker/workspace.py` may call `510 in `src/kgmaker/schema_replay.py`` (name match at line 156; src/kgmaker/workspace.py:156; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 34; src/kgmaker/workspace_cli.py:34; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 40; src/kgmaker/workspace_cli.py:40; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 43; src/kgmaker/workspace_cli.py:43; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 66; src/kgmaker/workspace_cli.py:66; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 75; src/kgmaker/workspace_cli.py:75; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 84; src/kgmaker/workspace_cli.py:84; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `31 in `src/kgmaker/analysis_model.py`` (name match at line 93; src/kgmaker/workspace_cli.py:93; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `73 in `src/kgmaker/analysis_model.py`` (name match at line 45; src/kgmaker/workspace_cli.py:45; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `73 in `src/kgmaker/analysis_model.py`` (name match at line 80; src/kgmaker/workspace_cli.py:80; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 45; src/kgmaker/workspace_cli.py:45; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `49 in `src/kgmaker/analysis_model.py`` (name match at line 80; src/kgmaker/workspace_cli.py:80; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `283 in `src/kgmaker/dataflow.py`` (name match at line 76; src/kgmaker/workspace_cli.py:76; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 29; src/kgmaker/workspace_cli.py:29; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 62; src/kgmaker/workspace_cli.py:62; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 67; src/kgmaker/workspace_cli.py:67; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 68; src/kgmaker/workspace_cli.py:68; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 70; src/kgmaker/workspace_cli.py:70; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 80; src/kgmaker/workspace_cli.py:80; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 81; src/kgmaker/workspace_cli.py:81; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 82; src/kgmaker/workspace_cli.py:82; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 83; src/kgmaker/workspace_cli.py:83; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `161 in `src/kgmaker/feature.py`` (name match at line 82; src/kgmaker/workspace_cli.py:82; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `272 in `src/kgmaker/feature.py`` (name match at line 81; src/kgmaker/workspace_cli.py:81; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 36; src/kgmaker/workspace_cli.py:36; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 38; src/kgmaker/workspace_cli.py:38; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 46; src/kgmaker/workspace_cli.py:46; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 49; src/kgmaker/workspace_cli.py:49; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 83; src/kgmaker/workspace_cli.py:83; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `394 in `src/kgmaker/schema_replay.py`` (name match at line 47; src/kgmaker/workspace_cli.py:47; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `463 in `src/kgmaker/schema_replay.py`` (name match at line 47; src/kgmaker/workspace_cli.py:47; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `54 in `src/kgmaker/store.py`` (name match at line 70; src/kgmaker/workspace_cli.py:70; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `14 in `src/kgmaker/store.py`` (name match at line 88; src/kgmaker/workspace_cli.py:88; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `37 in `src/kgmaker/store.py`` (name match at line 67; src/kgmaker/workspace_cli.py:67; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `32 in `src/kgmaker/workspace.py`` (name match at line 31; src/kgmaker/workspace_cli.py:31; INFERRED 0.85)
- `src/kgmaker/workspace_cli.py` may call `101 in `src/kgmaker/workspace.py`` (name match at line 62; src/kgmaker/workspace_cli.py:62; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java` may call `146 in `src/kgmaker/dataflow.py`` (name match at line 82; workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java:82; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 101; workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java:101; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 102; workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java:102; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 103; workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java:103; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 127; workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java:127; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 130; workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java:130; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 147; workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java:147; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 154; workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java:154; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 172; workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java:172; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 181; workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java:181; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 182; workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java:182; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 187; workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java:187; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 190; workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java:190; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 191; workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java:191; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 195; workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java:195; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 23; workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java:23; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 27; workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java:27; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 54; workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java:54; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 79; workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java:79; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 80; workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java:80; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 81; workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java:81; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java` may call `75 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 77; workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java:77; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java` may call `59 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 194; workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java:194; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java` may call `59 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 197; workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java:197; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java` may call `59 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 99; workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java:99; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java` may call `60 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 109; workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java:109; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java` may call `60 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 113; workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java:113; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java` may call `60 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 97; workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java:97; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java` may call `60 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 98; workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java:98; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `295 in `src/kgmaker/cli.py`` (name match at line 208; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:208; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `295 in `src/kgmaker/cli.py`` (name match at line 211; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:211; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `295 in `src/kgmaker/cli.py`` (name match at line 39; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:39; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `183 in `src/kgmaker/confluence.py`` (name match at line 38; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:38; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `183 in `src/kgmaker/confluence.py`` (name match at line 74; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:74; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 132; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:132; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 135; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:135; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 143; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:143; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 144; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:144; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 147; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:147; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 208; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:208; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 219; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:219; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 220; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:220; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 28; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:28; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 30; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:30; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `75 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 22; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:22; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `75 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 32; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:32; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `59 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 108; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:108; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `59 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 120; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:120; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `59 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 178; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:178; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `59 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 195; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:195; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `59 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 85; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:85; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `201 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 205; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:205; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `201 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 216; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:216; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `211 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 135; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:135; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `211 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 147; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:147; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `211 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 214; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:214; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `211 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 219; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:219; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `211 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 220; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:220; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `211 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 221; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:221; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `211 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 222; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:222; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `211 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 225; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:225; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `211 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 226; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:226; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `211 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 227; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:227; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `211 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 228; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:228; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `211 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 229; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:229; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `211 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 230; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:230; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `211 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 231; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:231; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `211 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 233; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:233; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `211 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 234; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:234; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `211 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 235; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:235; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `211 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 236; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:236; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `211 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 237; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:237; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `210 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 216; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:216; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `210 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 80; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:80; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `35 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 122; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:122; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `35 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 131; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:131; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `35 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 137; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:137; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `35 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 142; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:142; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `35 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 152; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:152; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `35 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 180; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:180; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `35 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 181; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:181; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `35 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 182; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:182; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `35 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 187; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:187; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `35 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 199; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:199; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `35 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 200; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:200; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `35 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 216; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:216; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `35 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 238; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:238; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `35 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 239; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:239; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `35 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 62; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:62; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `60 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 107; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:107; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `60 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 113; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:113; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `60 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 133; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:133; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `60 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 156; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:156; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `46 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 113; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:113; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `46 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 156; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:156; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `46 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 180; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:180; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `46 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 195; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:195; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java` may call `46 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 57; workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java:57; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/State.java` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 38; workers/jvm/src/main/java/org/kgmaker/worker/State.java:38; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/State.java` may call `41 in `src/kgmaker/analysis_model.py`` (name match at line 45; workers/jvm/src/main/java/org/kgmaker/worker/State.java:45; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/State.java` may call `183 in `src/kgmaker/confluence.py`` (name match at line 50; workers/jvm/src/main/java/org/kgmaker/worker/State.java:50; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/State.java` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 67; workers/jvm/src/main/java/org/kgmaker/worker/State.java:67; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/State.java` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 71; workers/jvm/src/main/java/org/kgmaker/worker/State.java:71; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/State.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 102; workers/jvm/src/main/java/org/kgmaker/worker/State.java:102; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/State.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 110; workers/jvm/src/main/java/org/kgmaker/worker/State.java:110; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/State.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 111; workers/jvm/src/main/java/org/kgmaker/worker/State.java:111; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/State.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 114; workers/jvm/src/main/java/org/kgmaker/worker/State.java:114; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/State.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 23; workers/jvm/src/main/java/org/kgmaker/worker/State.java:23; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/State.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 24; workers/jvm/src/main/java/org/kgmaker/worker/State.java:24; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/State.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 25; workers/jvm/src/main/java/org/kgmaker/worker/State.java:25; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/State.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 28; workers/jvm/src/main/java/org/kgmaker/worker/State.java:28; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/State.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 57; workers/jvm/src/main/java/org/kgmaker/worker/State.java:57; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/State.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 62; workers/jvm/src/main/java/org/kgmaker/worker/State.java:62; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/State.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 63; workers/jvm/src/main/java/org/kgmaker/worker/State.java:63; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/State.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 66; workers/jvm/src/main/java/org/kgmaker/worker/State.java:66; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/State.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 70; workers/jvm/src/main/java/org/kgmaker/worker/State.java:70; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/State.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 71; workers/jvm/src/main/java/org/kgmaker/worker/State.java:71; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/State.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 75; workers/jvm/src/main/java/org/kgmaker/worker/State.java:75; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/State.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 79; workers/jvm/src/main/java/org/kgmaker/worker/State.java:79; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/State.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 85; workers/jvm/src/main/java/org/kgmaker/worker/State.java:85; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/State.java` may call `136 in `src/kgmaker/schema_replay.py`` (name match at line 94; workers/jvm/src/main/java/org/kgmaker/worker/State.java:94; INFERRED 0.85)
- `workers/jvm/src/main/java/org/kgmaker/worker/State.java` may call `60 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 81; workers/jvm/src/main/java/org/kgmaker/worker/State.java:81; INFERRED 0.85)
- `workers/jvm/src/main/kotlin/org/kgmaker/worker/JvmWorker.kt` may call `207 in `src/kgmaker/dataflow.py`` (name match at line 29; workers/jvm/src/main/kotlin/org/kgmaker/worker/JvmWorker.kt:29; INFERRED 0.85)
- `workers/jvm/src/main/kotlin/org/kgmaker/worker/JvmWorker.kt` may call `21 in `workers/jvm/src/main/java/org/kgmaker/worker/Bytecode.java`` (name match at line 35; workers/jvm/src/main/kotlin/org/kgmaker/worker/JvmWorker.kt:35; INFERRED 0.85)
- `workers/jvm/src/main/kotlin/org/kgmaker/worker/JvmWorker.kt` may call `20 in `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java`` (name match at line 33; workers/jvm/src/main/kotlin/org/kgmaker/worker/JvmWorker.kt:33; INFERRED 0.85)
- `workers/jvm/src/main/kotlin/org/kgmaker/worker/JvmWorker.kt` may call `21 in `workers/jvm/src/main/java/org/kgmaker/worker/State.java`` (name match at line 26; workers/jvm/src/main/kotlin/org/kgmaker/worker/JvmWorker.kt:26; INFERRED 0.85)
- `workers/jvm/src/main/kotlin/org/kgmaker/worker/JvmWorker.kt` may call `75 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 33; workers/jvm/src/main/kotlin/org/kgmaker/worker/JvmWorker.kt:33; INFERRED 0.85)
- `workers/jvm/src/main/kotlin/org/kgmaker/worker/JvmWorker.kt` may call `75 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 34; workers/jvm/src/main/kotlin/org/kgmaker/worker/JvmWorker.kt:34; INFERRED 0.85)
- `workers/jvm/src/main/kotlin/org/kgmaker/worker/JvmWorker.kt` may call `75 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 36; workers/jvm/src/main/kotlin/org/kgmaker/worker/JvmWorker.kt:36; INFERRED 0.85)
- `workers/jvm/src/main/kotlin/org/kgmaker/worker/JvmWorker.kt` may call `30 in `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt`` (name match at line 34; workers/jvm/src/main/kotlin/org/kgmaker/worker/JvmWorker.kt:34; INFERRED 0.85)
- `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt` may call `183 in `src/kgmaker/confluence.py`` (name match at line 38; workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt:38; INFERRED 0.85)
- `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt` may call `115 in `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java`` (name match at line 102; workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt:102; INFERRED 0.85)
- `workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt` may call `115 in `workers/jvm/src/main/java/org/kgmaker/worker/JavaFrontend.java`` (name match at line 98; workers/jvm/src/main/kotlin/org/kgmaker/worker/KotlinFrontend.kt:98; INFERRED 0.85)
- `src/kgmaker/domain.py` **connects_to** technology `PostgreSQL` in `src/kgmaker/domain.py` — PostgreSQL driver or connection string
- `src/kgmaker/domain.py` **uses_messaging** technology `Kafka` in `src/kgmaker/domain.py` — Kafka import, client, annotation, or configuration
- `src/kgmaker/framework.py` **uses_messaging** technology `Kafka` in `src/kgmaker/domain.py` — Kafka import, client, annotation, or configuration
- `src/kgmaker/inspection_cli.py` **uses_messaging** technology `Kafka` in `src/kgmaker/domain.py` — Kafka import, client, annotation, or configuration

## Reading this graph

File and symbol locations are repository-relative. `contains` edges bind declarations to their files. Domain edges such as `maps_to_table`, `consumes`, and `calls_endpoint` record annotations, SQL definitions, configuration, or literal paths found in source. `calls` edges are conservative name matches and must be verified before relying on them.
