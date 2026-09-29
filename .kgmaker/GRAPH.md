# Repository knowledge graph

> Generated locally by kgmaker. Structural edges come from source text; name-based call edges are heuristic.
> Review semantic conclusions with the repository's Copilot knowledge-graph agent.

- Files indexed: 10
- Symbols and sections: 49
- Internal imports: 8
- Heuristic cross-file calls: 30
- Generated: 2026-09-29T07:52:23+00:00

## Files and symbols

### `README.md`
- **section** `kgmaker` line 1
- **section** `Requirements` line 7
- **section** `Install` line 12
- **section** `Commands` line 26
- **section** `What gets indexed` line 40
- **section** `Copilot workflow` line 46
- **section** `Development` line 52

### `docs/architecture.md`
- **section** `Architecture` line 1
- **section** `Relationship confidence` line 12
- **section** `Hook lifecycle` line 20
- **section** `Extension points` line 24

### `docs/project-scope.md`
- **section** `Project scope` line 1
- **section** `Goals` line 5
- **section** `Out of scope` line 13
- **section** `Initial implementation` line 21

### `src/kgmaker/__init__.py`
- No declarations extracted.

### `src/kgmaker/__main__.py`
- No declarations extracted.

### `src/kgmaker/cli.py`
- **function** `_write_if_missing` line 61 — `_write_if_missing(path: Path, text: str, force: bool = False)`
- **function** `init` line 69 — `init(root: Path, force: bool = False)`
- **function** `scan` line 97 — `scan(root: Path)`
- **function** `status` line 108 — `status(root: Path)`
- **function** `query` line 128 — `query(root: Path, terms: str, limit: int = 10)`
- **function** `hook_context` line 157 — `hook_context(root: Path)`
- **function** `build_parser` line 171 — `build_parser`
- **function** `main` line 196 — `main`

### `src/kgmaker/model.py`
- **class** `Node` line 10 — `Node`
- **class** `Edge` line 21 — `Edge`
- **class** `KnowledgeGraph` line 29 — `KnowledgeGraph`
- **function** `to_dict` line 36 — `to_dict(self)`
- **function** `from_dict` line 48 — `from_dict(cls, data: dict[str, Any])`

### `src/kgmaker/scanner.py`
- **function** `_safe_text` line 67 — `_safe_text(path: Path)`
- **function** `_file_digest` line 76 — `_file_digest(text: str)`
- **function** `_stable_id` line 80 — `_stable_id(kind: str, path: str, name: str, line: int | None = None)`
- **function** `_line_for` line 85 — `_line_for(text: str, offset: int)`
- **function** `_doc_for_line` line 89 — `_doc_for_line(lines: list[str], index: int)`
- **function** `_extract_symbols` line 97 — `_extract_symbols(text: str, path: str, language: str)`
- **function** `_imports` line 151 — `_imports(text: str, language: str)`
- **function** `_candidate_paths` line 169 — `_candidate_paths(root: Path, source: str, import_name: str, known_files: set[str])`
- **function** `_should_skip` line 198 — `_should_skip(path: Path, relative: Path)`
- **function** `scan_repository` line 207 — `scan_repository(root: Path)`

### `src/kgmaker/store.py`
- **function** `save_graph` line 13 — `save_graph(graph: KnowledgeGraph, root: Path)`
- **function** `load_graph` line 23 — `load_graph(root: Path)`
- **function** `render_markdown` line 31 — `render_markdown(graph: KnowledgeGraph)`
- **function** `render_context` line 81 — `render_context(graph: KnowledgeGraph, limit: int = 8_000, root: Path | None = None)`

### `tests/test_scanner.py`
- **class** `ScannerTests` line 11 — `ScannerTests(unittest.TestCase)`
- **function** `test_extracts_python_symbols_and_internal_imports` line 14 — `test_extracts_python_symbols_and_internal_imports(self)`
- **function** `test_skips_secrets_and_dependency_folders` line 28 — `test_skips_secrets_and_dependency_folders(self)`
- **function** `test_persists_and_loads_graph` line 41 — `test_persists_and_loads_graph(self)`
- **function** `test_resolves_python_package_relative_import` line 55 — `test_resolves_python_package_relative_import(self)`
- **function** `test_init_preserves_existing_user_files` line 70 — `test_init_preserves_existing_user_files(self)`
- **function** `test_hook_emits_session_context_json` line 82 — `test_hook_emits_session_context_json(self)`

## Internal relationships

- `src/kgmaker/__main__.py` imports `src/kgmaker/cli.py` (`.cli`)
- `src/kgmaker/cli.py` imports `src/kgmaker/scanner.py` (`.scanner`)
- `src/kgmaker/cli.py` imports `src/kgmaker/store.py` (`.store`)
- `src/kgmaker/scanner.py` imports `src/kgmaker/model.py` (`.model`)
- `src/kgmaker/store.py` imports `src/kgmaker/model.py` (`.model`)
- `tests/test_scanner.py` imports `src/kgmaker/cli.py` (`kgmaker.cli`)
- `tests/test_scanner.py` imports `src/kgmaker/scanner.py` (`kgmaker.scanner`)
- `tests/test_scanner.py` imports `src/kgmaker/store.py` (`kgmaker.store`)
- `src/kgmaker/__main__.py` may call `196 in `src/kgmaker/cli.py`` (name match at line 3)
- `src/kgmaker/cli.py` may call `207 in `src/kgmaker/scanner.py`` (name match at line 100)
- `src/kgmaker/cli.py` may call `207 in `src/kgmaker/scanner.py`` (name match at line 115)
- `src/kgmaker/cli.py` may call `207 in `src/kgmaker/scanner.py`` (name match at line 162)
- `src/kgmaker/cli.py` may call `23 in `src/kgmaker/store.py`` (name match at line 111)
- `src/kgmaker/cli.py` may call `23 in `src/kgmaker/store.py`` (name match at line 131)
- `src/kgmaker/cli.py` may call `81 in `src/kgmaker/store.py`` (name match at line 164)
- `src/kgmaker/cli.py` may call `13 in `src/kgmaker/store.py`` (name match at line 101)
- `src/kgmaker/cli.py` may call `13 in `src/kgmaker/store.py`` (name match at line 163)
- `src/kgmaker/scanner.py` may call `21 in `src/kgmaker/model.py`` (name match at line 251)
- `src/kgmaker/scanner.py` may call `21 in `src/kgmaker/model.py`` (name match at line 263)
- `src/kgmaker/scanner.py` may call `21 in `src/kgmaker/model.py`` (name match at line 273)
- `src/kgmaker/scanner.py` may call `29 in `src/kgmaker/model.py`` (name match at line 284)
- `src/kgmaker/scanner.py` may call `10 in `src/kgmaker/model.py`` (name match at line 113)
- `src/kgmaker/scanner.py` may call `10 in `src/kgmaker/model.py`` (name match at line 140)
- `src/kgmaker/scanner.py` may call `10 in `src/kgmaker/model.py`` (name match at line 241)
- `src/kgmaker/store.py` may call `48 in `src/kgmaker/model.py`` (name match at line 28)
- `src/kgmaker/store.py` may call `36 in `src/kgmaker/model.py`` (name match at line 20)
- `tests/test_scanner.py` may call `157 in `src/kgmaker/cli.py`` (name match at line 92)
- `tests/test_scanner.py` may call `69 in `src/kgmaker/cli.py`` (name match at line 78)
- `tests/test_scanner.py` may call `196 in `src/kgmaker/cli.py`` (name match at line 100)
- `tests/test_scanner.py` may call `196 in `src/kgmaker/cli.py`` (name match at line 17)
- `tests/test_scanner.py` may call `196 in `src/kgmaker/cli.py`` (name match at line 89)
- `tests/test_scanner.py` may call `36 in `src/kgmaker/model.py`` (name match at line 40)
- `tests/test_scanner.py` may call `207 in `src/kgmaker/scanner.py`` (name match at line 20)
- `tests/test_scanner.py` may call `207 in `src/kgmaker/scanner.py`` (name match at line 37)
- `tests/test_scanner.py` may call `207 in `src/kgmaker/scanner.py`` (name match at line 46)
- `tests/test_scanner.py` may call `207 in `src/kgmaker/scanner.py`` (name match at line 65)
- `tests/test_scanner.py` may call `23 in `src/kgmaker/store.py`` (name match at line 49)
- `tests/test_scanner.py` may call `13 in `src/kgmaker/store.py`` (name match at line 47)

## Reading this graph

File and symbol locations are repository-relative. `contains` edges bind declarations to their files. `imports` edges are resolved from local import statements. `calls` edges are conservative name matches and must be verified before relying on them.
