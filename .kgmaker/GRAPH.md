# Repository knowledge graph

> Generated locally by kgmaker. Structural edges come from source text; name-based call edges are heuristic.
> Review semantic conclusions with the repository's Copilot knowledge-graph agent.

- Files indexed: 11
- Symbols and sections: 85
- Internal imports: 10
- Heuristic cross-file calls: 70
- PostgreSQL tables/columns: 0/0
- Kafka topics: 0
- API endpoints: 0
- TypeScript frontend routes: 0

## Files and symbols

### `README.md`
- **section** `kgmaker` line 1
- **section** `Requirements` line 7
- **section** `Install` line 12
- **section** `Commands` line 26
- **section** `What gets indexed` line 48
- **section** `Copilot workflow` line 56
- **section** `Development` line 62

### `docs/architecture.md`
- **section** `Architecture` line 1
- **section** `Relationship confidence` line 13
- **section** `Hook lifecycle` line 25
- **section** `Extension points` line 29

### `docs/project-scope.md`
- **section** `Project scope` line 1
- **section** `Goals` line 5
- **section** `Out of scope` line 13
- **section** `Initial implementation` line 21
- **section** `Graph workflows` line 27

### `src/kgmaker/__init__.py`
- No declarations extracted.

### `src/kgmaker/__main__.py`
- No declarations extracted.

### `src/kgmaker/cli.py`
- **function** `_write_if_missing` line 61 — `_write_if_missing(path: Path, text: str, force: bool = False)`
- **function** `init` line 69 — `init(root: Path, force: bool = False)`
- **function** `scan` line 97 — `scan(root: Path)`
- **function** `status` line 108 — `status(root: Path)`
- **function** `check` line 128 — `check(root: Path)`
- **function** `docs` line 145 — `docs(root: Path)`
- **function** `impact` line 158 — `impact(root: Path, changed_files: list[str])`
- **function** `query` line 230 — `query(root: Path, terms: str, limit: int = 10)`
- **function** `hook_context` line 259 — `hook_context(root: Path)`
- **function** `build_parser` line 273 — `build_parser`
- **function** `main` line 312 — `main`

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
- **function** `_string_literals` line 184 — `_string_literals(value: str)`
- **function** `_kafka_references` line 188 — `_kafka_references(text: str, path: str, file_id: str)`
- **function** `add` line 193 — `add(topic: str, offset: int, relation: str, evidence: str)`
- **function** `normalize_api_path` line 223 — `normalize_api_path(path: str)`
- **function** `_api_node` line 234 — `_api_node(method: str, path: str, source: str, line: int | None, operation: str | None = None)`
- **function** `_mapping_path` line 247 — `_mapping_path(args: str)`
- **function** `_openapi_yaml` line 252 — `_openapi_yaml(text: str, path: str, file_id: str)`
- **function** `flush` line 264 — `flush(offset: int)`
- **function** `_openapi_json` line 295 — `_openapi_json(text: str, path: str, file_id: str)`
- **function** `_api_references` line 317 — `_api_references(text: str, path: str, language: str, file_id: str)`
- **function** `add` line 322 — `add(method: str, endpoint_path: str, offset: int, relation: str, evidence: str)`
- **function** `_typescript_routes` line 385 — `_typescript_routes(path: str, text: str, file_id: str)`
- **function** `_technology_nodes` line 419 — `_technology_nodes(text: str, path: str, file_id: str)`
- **function** `extract_domain` line 433 — `extract_domain(path: str, text: str, language: str, file_id: str, symbols: list[Node])`
- **function** `extract_openapi` line 468 — `extract_openapi(path: str, text: str, file_id: str)`
- **function** `connect_persistence` line 477 — `connect_persistence(symbols_by_file: dict[str, list[Node]], text_by_file: dict[str, str], nodes: list[Node])`
- **function** `merge_domain_nodes` line 508 — `merge_domain_nodes(nodes: list[Node])`

### `src/kgmaker/model.py`
- **class** `Node` line 10 — `Node`
- **class** `Edge` line 21 — `Edge`
- **class** `KnowledgeGraph` line 29 — `KnowledgeGraph`
- **function** `to_dict` line 36 — `to_dict(self)`
- **function** `from_dict` line 48 — `from_dict(cls, data: dict[str, Any])`

### `src/kgmaker/scanner.py`
- **function** `_safe_text` line 74 — `_safe_text(path: Path)`
- **function** `_file_digest` line 83 — `_file_digest(text: str)`
- **function** `_stable_id` line 87 — `_stable_id(kind: str, path: str, name: str, line: int | None = None)`
- **function** `_line_for` line 92 — `_line_for(text: str, offset: int)`
- **function** `_doc_for_line` line 96 — `_doc_for_line(lines: list[str], index: int)`
- **function** `_extract_symbols` line 104 — `_extract_symbols(text: str, path: str, language: str)`
- **function** `_imports` line 160 — `_imports(text: str, language: str)`
- **function** `_candidate_paths` line 178 — `_candidate_paths(root: Path, source: str, import_name: str, known_files: set[str])`
- **function** `_should_skip` line 207 — `_should_skip(path: Path, relative: Path)`
- **function** `scan_repository` line 216 — `scan_repository(root: Path)`

### `src/kgmaker/store.py`
- **function** `save_graph` line 13 — `save_graph(graph: KnowledgeGraph, root: Path)`
- **function** `load_graph` line 23 — `load_graph(root: Path)`
- **function** `render_markdown` line 31 — `render_markdown(graph: KnowledgeGraph)`
- **function** `render_context` line 96 — `render_context(graph: KnowledgeGraph, limit: int = 8_000, root: Path | None = None)`

### `tests/test_scanner.py`
- **class** `ScannerTests` line 11 — `ScannerTests(unittest.TestCase)`
- **function** `test_extracts_python_symbols_and_internal_imports` line 14 — `test_extracts_python_symbols_and_internal_imports(self)`
- **function** `test_skips_secrets_and_dependency_folders` line 28 — `test_skips_secrets_and_dependency_folders(self)`
- **function** `test_persists_and_loads_graph` line 41 — `test_persists_and_loads_graph(self)`
- **function** `test_resolves_python_package_relative_import` line 55 — `test_resolves_python_package_relative_import(self)`
- **function** `test_init_preserves_existing_user_files` line 70 — `test_init_preserves_existing_user_files(self)`
- **function** `test_hook_emits_session_context_json` line 82 — `test_hook_emits_session_context_json(self)`
- **function** `test_impact_reports_exact_transitive_import_dependents` line 97 — `test_impact_reports_exact_transitive_import_dependents(self)`
- **function** `test_check_detects_stale_graph_and_docs_regenerate_markdown` line 116 — `test_check_detects_stale_graph_and_docs_regenerate_markdown(self)`
- **function** `test_maps_kotlin_entities_repositories_and_columns_to_postgres_schema` line 131 — `test_maps_kotlin_entities_repositories_and_columns_to_postgres_schema(self)`
- **function** `test_finds_kafka_topics_and_postgres_connection_from_kotlin_and_yaml` line 166 — `test_finds_kafka_topics_and_postgres_connection_from_kotlin_and_yaml(self)`
- **function** `test_links_openapi_server_and_typescript_client_paths` line 198 — `test_links_openapi_server_and_typescript_client_paths(self)`

## Internal relationships

- `src/kgmaker/__main__.py` imports `src/kgmaker/cli.py` (`.cli`)
- `src/kgmaker/cli.py` imports `src/kgmaker/scanner.py` (`.scanner`)
- `src/kgmaker/cli.py` imports `src/kgmaker/store.py` (`.store`)
- `src/kgmaker/domain.py` imports `src/kgmaker/model.py` (`.model`)
- `src/kgmaker/scanner.py` imports `src/kgmaker/domain.py` (`.domain`)
- `src/kgmaker/scanner.py` imports `src/kgmaker/model.py` (`.model`)
- `src/kgmaker/store.py` imports `src/kgmaker/model.py` (`.model`)
- `tests/test_scanner.py` imports `src/kgmaker/cli.py` (`kgmaker.cli`)
- `tests/test_scanner.py` imports `src/kgmaker/scanner.py` (`kgmaker.scanner`)
- `tests/test_scanner.py` imports `src/kgmaker/store.py` (`kgmaker.store`)
- `src/kgmaker/__main__.py` may call `312 in `src/kgmaker/cli.py`` (name match at line 3)
- `src/kgmaker/cli.py` may call `216 in `src/kgmaker/scanner.py`` (name match at line 100)
- `src/kgmaker/cli.py` may call `216 in `src/kgmaker/scanner.py`` (name match at line 115)
- `src/kgmaker/cli.py` may call `216 in `src/kgmaker/scanner.py`` (name match at line 132)
- `src/kgmaker/cli.py` may call `216 in `src/kgmaker/scanner.py`` (name match at line 264)
- `src/kgmaker/cli.py` may call `23 in `src/kgmaker/store.py`` (name match at line 111)
- `src/kgmaker/cli.py` may call `23 in `src/kgmaker/store.py`` (name match at line 149)
- `src/kgmaker/cli.py` may call `23 in `src/kgmaker/store.py`` (name match at line 162)
- `src/kgmaker/cli.py` may call `23 in `src/kgmaker/store.py`` (name match at line 233)
- `src/kgmaker/cli.py` may call `96 in `src/kgmaker/store.py`` (name match at line 266)
- `src/kgmaker/cli.py` may call `31 in `src/kgmaker/store.py`` (name match at line 134)
- `src/kgmaker/cli.py` may call `31 in `src/kgmaker/store.py`` (name match at line 155)
- `src/kgmaker/cli.py` may call `13 in `src/kgmaker/store.py`` (name match at line 101)
- `src/kgmaker/cli.py` may call `13 in `src/kgmaker/store.py`` (name match at line 265)
- `src/kgmaker/domain.py` may call `21 in `src/kgmaker/model.py`` (name match at line 118)
- `src/kgmaker/domain.py` may call `21 in `src/kgmaker/model.py`` (name match at line 135)
- `src/kgmaker/domain.py` may call `21 in `src/kgmaker/model.py`` (name match at line 155)
- `src/kgmaker/domain.py` may call `21 in `src/kgmaker/model.py`` (name match at line 172)
- `src/kgmaker/domain.py` may call `21 in `src/kgmaker/model.py`` (name match at line 182)
- `src/kgmaker/domain.py` may call `21 in `src/kgmaker/model.py`` (name match at line 199)
- `src/kgmaker/domain.py` may call `21 in `src/kgmaker/model.py`` (name match at line 269)
- `src/kgmaker/domain.py` may call `21 in `src/kgmaker/model.py`` (name match at line 315)
- `src/kgmaker/domain.py` may call `21 in `src/kgmaker/model.py`` (name match at line 328)
- `src/kgmaker/domain.py` may call `21 in `src/kgmaker/model.py`` (name match at line 373)
- `src/kgmaker/domain.py` may call `21 in `src/kgmaker/model.py`` (name match at line 410)
- `src/kgmaker/domain.py` may call `21 in `src/kgmaker/model.py`` (name match at line 417)
- `src/kgmaker/domain.py` may call `21 in `src/kgmaker/model.py`` (name match at line 427)
- `src/kgmaker/domain.py` may call `21 in `src/kgmaker/model.py`` (name match at line 431)
- `src/kgmaker/domain.py` may call `21 in `src/kgmaker/model.py`` (name match at line 502)
- `src/kgmaker/domain.py` may call `21 in `src/kgmaker/model.py`` (name match at line 506)
- `src/kgmaker/domain.py` may call `10 in `src/kgmaker/model.py`` (name match at line 126)
- `src/kgmaker/domain.py` may call `10 in `src/kgmaker/model.py`` (name match at line 239)
- `src/kgmaker/domain.py` may call `10 in `src/kgmaker/model.py`` (name match at line 408)
- `src/kgmaker/domain.py` may call `10 in `src/kgmaker/model.py`` (name match at line 84)
- `src/kgmaker/scanner.py` may call `21 in `src/kgmaker/model.py`` (name match at line 260)
- `src/kgmaker/scanner.py` may call `21 in `src/kgmaker/model.py`` (name match at line 272)
- `src/kgmaker/scanner.py` may call `21 in `src/kgmaker/model.py`` (name match at line 282)
- `src/kgmaker/scanner.py` may call `29 in `src/kgmaker/model.py`` (name match at line 307)
- `src/kgmaker/scanner.py` may call `10 in `src/kgmaker/model.py`` (name match at line 120)
- `src/kgmaker/scanner.py` may call `10 in `src/kgmaker/model.py`` (name match at line 149)
- `src/kgmaker/scanner.py` may call `10 in `src/kgmaker/model.py`` (name match at line 250)
- `src/kgmaker/scanner.py` may call `477 in `src/kgmaker/domain.py`` (name match at line 302)
- `src/kgmaker/scanner.py` may call `433 in `src/kgmaker/domain.py`` (name match at line 294)
- `src/kgmaker/scanner.py` may call `468 in `src/kgmaker/domain.py`` (name match at line 297)
- `src/kgmaker/scanner.py` may call `508 in `src/kgmaker/domain.py`` (name match at line 301)
- `src/kgmaker/store.py` may call `48 in `src/kgmaker/model.py`` (name match at line 28)
- `src/kgmaker/store.py` may call `36 in `src/kgmaker/model.py`` (name match at line 20)
- `tests/test_scanner.py` may call `128 in `src/kgmaker/cli.py`` (name match at line 123)
- `tests/test_scanner.py` may call `128 in `src/kgmaker/cli.py`` (name match at line 126)
- `tests/test_scanner.py` may call `145 in `src/kgmaker/cli.py`` (name match at line 129)
- `tests/test_scanner.py` may call `259 in `src/kgmaker/cli.py`` (name match at line 92)
- `tests/test_scanner.py` may call `158 in `src/kgmaker/cli.py`` (name match at line 111)
- `tests/test_scanner.py` may call `69 in `src/kgmaker/cli.py`` (name match at line 78)
- `tests/test_scanner.py` may call `312 in `src/kgmaker/cli.py`` (name match at line 17)
- `tests/test_scanner.py` may call `312 in `src/kgmaker/cli.py`` (name match at line 254)
- `tests/test_scanner.py` may call `312 in `src/kgmaker/cli.py`` (name match at line 89)
- `tests/test_scanner.py` may call `36 in `src/kgmaker/model.py`` (name match at line 40)
- `tests/test_scanner.py` may call `216 in `src/kgmaker/scanner.py`` (name match at line 107)
- `tests/test_scanner.py` may call `216 in `src/kgmaker/scanner.py`` (name match at line 122)
- `tests/test_scanner.py` may call `216 in `src/kgmaker/scanner.py`` (name match at line 157)
- `tests/test_scanner.py` may call `216 in `src/kgmaker/scanner.py`` (name match at line 190)
- `tests/test_scanner.py` may call `216 in `src/kgmaker/scanner.py`` (name match at line 20)
- `tests/test_scanner.py` may call `216 in `src/kgmaker/scanner.py`` (name match at line 238)
- `tests/test_scanner.py` may call `216 in `src/kgmaker/scanner.py`` (name match at line 37)
- `tests/test_scanner.py` may call `216 in `src/kgmaker/scanner.py`` (name match at line 46)
- `tests/test_scanner.py` may call `216 in `src/kgmaker/scanner.py`` (name match at line 65)
- `tests/test_scanner.py` may call `23 in `src/kgmaker/store.py`` (name match at line 49)
- `tests/test_scanner.py` may call `13 in `src/kgmaker/store.py`` (name match at line 107)
- `tests/test_scanner.py` may call `13 in `src/kgmaker/store.py`` (name match at line 122)
- `tests/test_scanner.py` may call `13 in `src/kgmaker/store.py`` (name match at line 47)
- `src/kgmaker/domain.py` **connects_to** technology `PostgreSQL` in `src/kgmaker/domain.py` — PostgreSQL driver or connection string
- `src/kgmaker/domain.py` **uses_messaging** technology `Kafka` in `src/kgmaker/domain.py` — Kafka import, client, annotation, or configuration
- `tests/test_scanner.py` **connects_to** technology `PostgreSQL` in `src/kgmaker/domain.py` — PostgreSQL driver or connection string
- `tests/test_scanner.py` **uses_messaging** technology `Kafka` in `src/kgmaker/domain.py` — Kafka import, client, annotation, or configuration

## Reading this graph

File and symbol locations are repository-relative. `contains` edges bind declarations to their files. Domain edges such as `maps_to_table`, `consumes`, and `calls_endpoint` record annotations, SQL definitions, configuration, or literal paths found in source. `calls` edges are conservative name matches and must be verified before relying on them.
