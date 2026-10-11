"""Dependency-free, deterministic repository scanner.

The first release intentionally extracts structural evidence instead of asking
an external model to invent edges. Copilot can add semantic interpretation via
the repository custom agent while every stored edge remains auditable.
"""

from __future__ import annotations

import hashlib
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .domain import connect_persistence, extract_domain, extract_openapi, merge_domain_nodes
from .model import Edge, KnowledgeGraph, Node
from .dataflow import extract_dataflow

SCHEMA_VERSION = 1
EXTENSIONS = {
    ".py": "python",
    ".java": "jvm",
    ".kt": "jvm",
    ".kts": "jvm",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "javascript",
    ".tsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".md": "markdown",
    ".mdx": "markdown",
    ".rst": "markdown",
    ".sql": "sql",
    ".yaml": "config",
    ".yml": "config",
    ".properties": "config",
    ".json": "json",
}
SKIP_DIRS = {
    ".git", ".hg", ".svn", ".idea", ".vscode", ".venv", "venv", "env",
    "node_modules", "vendor", "build", "dist", "target", "out", "coverage",
    "__pycache__", ".gradle", ".next", ".nuxt", ".kgmaker",
}
SENSITIVE_NAMES = {
    ".env", ".npmrc", ".pypirc", "id_rsa", "id_ed25519", "credentials",
    "secrets.yaml", "secrets.yml", "secret.json", "service-account.json",
}
MAX_FILE_BYTES = 1_000_000
MAX_GRAPH_FILES = 20_000

PY_IMPORT = re.compile(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.M)
JVM_IMPORT = re.compile(r"^\s*import\s+(?:static\s+)?([\w.*]+)", re.M)
JS_IMPORT = re.compile(
    r"(?:\bfrom\s*|\bimport\s*\(|\brequire\s*\()\s*['\"]([^'\"]+)['\"]"
)
GO_IMPORT = re.compile(r"^\s*(?:import\s+\(?\s*|\s*)\"([^\"]+)\"", re.M)
RUST_IMPORT = re.compile(r"^\s*use\s+([\w:]+)", re.M)
PY_DEF = re.compile(r"^\s*(?:async\s+)?def\s+(\w+)\s*\(([^\n]*)\)", re.M)
PY_CLASS = re.compile(r"^\s*class\s+(\w+)(?:\(([^\n]*)\))?\s*:", re.M)
JVM_TYPE = re.compile(r"^\s*(?:public\s+|internal\s+|private\s+|protected\s+)*(?:open\s+|abstract\s+|data\s+|sealed\s+|enum\s+)*(class|interface|object|enum\s+class|record)\s+(\w+)([^\n{]*)", re.M)
JVM_FUN = re.compile(r"^\s*(?:(?:public|private|protected|internal|override|suspend|open|static|final|abstract)\s+)*fun\s+(\w+)\s*\(([^\n]*)\)", re.M)
JAVA_METHOD = re.compile(r"^\s*(?:public|private|protected|static|final|synchronized|abstract|\w+[<>?,.\[\]]*\s+)+\s+(\w+)\s*\(([^;{}]*)\)\s*(?:throws\s+[^{}]+)?\{", re.M)
JS_DECL = re.compile(r"^\s*(?:export\s+)?(?:(?:async\s+)?function|class)\s+(\w+)\s*(?:\(([^\n]*)\))?", re.M)
JS_ARROW = re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(([^\n]*)\)\s*=>", re.M)
TS_TYPE = re.compile(r"^\s*(?:export\s+)?(?:interface|type|enum)\s+(\w+)", re.M)
GO_DECL = re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?(\w+)\s*\(([^\n]*)\)", re.M)
RUST_DECL = re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?(?:fn|struct|enum|trait|mod)\s+(\w+)(?:\s*<[^>]+>)?\s*(?:\(([^\n]*)\))?", re.M)
MD_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$", re.M)
CALL_TOKEN = re.compile(r"\b([A-Za-z_][\w]*)\s*\(")


def _safe_text(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return None
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def _file_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _stable_id(kind: str, path: str, name: str, line: int | None = None) -> str:
    suffix = f"::{line}" if line is not None else ""
    return f"{kind}:{path}:{name}{suffix}"


def _line_for(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _doc_for_line(lines: list[str], index: int) -> str | None:
    if index + 1 < len(lines):
        candidate = lines[index + 1].strip()
        if candidate.startswith(('"""', "'''", "//", "*", "#")):
            return candidate.strip('"\'/*# ').strip()[:240] or None
    return None


def _extract_symbols(text: str, path: str, language: str) -> list[Node]:
    patterns: list[tuple[str, re.Pattern[str]]] = []
    if language == "python":
        patterns = [("class", PY_CLASS), ("function", PY_DEF)]
    elif language == "jvm":
        patterns = [("type", JVM_TYPE), ("function", JVM_FUN), ("function", JAVA_METHOD)]
    elif language == "javascript":
        patterns = [("symbol", JS_DECL), ("function", JS_ARROW), ("type", TS_TYPE)]
    elif language == "go":
        patterns = [("function", GO_DECL)]
    elif language == "rust":
        patterns = [("symbol", RUST_DECL)]
    elif language == "markdown":
        return [
            Node(
                id=_stable_id("section", path, match.group(2), _line_for(text, match.start())),
                kind="section",
                name=match.group(2).strip(),
                path=path,
                line=_line_for(text, match.start()),
            )
            for match in MD_HEADING.finditer(text)
        ]

    found: list[Node] = []
    occupied: set[tuple[int, str]] = set()
    lines = text.splitlines()
    for kind, pattern in patterns:
        for match in pattern.finditer(text):
            name = match.group(2) if kind == "type" and match.lastindex and match.lastindex >= 2 else match.group(1)
            if not name:
                continue
            if language == "javascript" and Path(path).suffix.lower() in {".tsx", ".jsx"} and name[:1].isupper() and (kind == "function" or "function" in match.group(0)):
                kind = "component"
            line = _line_for(text, match.start())
            key = (line, name)
            if key in occupied:
                continue
            occupied.add(key)
            args_index = 3 if kind == "type" else 2
            args = match.group(args_index) if match.lastindex and match.lastindex >= args_index else None
            signature = f"{name}({args.strip()})" if args else name
            found.append(
                Node(
                    id=_stable_id(kind, path, name, line),
                    kind=kind,
                    name=name,
                    path=path,
                    line=line,
                    signature=signature[:300],
                    summary=_doc_for_line(lines, line - 1),
                )
            )
    return found


def _imports(text: str, language: str) -> list[str]:
    pattern = {
        "python": PY_IMPORT,
        "jvm": JVM_IMPORT,
        "javascript": JS_IMPORT,
        "go": GO_IMPORT,
        "rust": RUST_IMPORT,
    }.get(language)
    if pattern is None:
        return []
    imports: list[str] = []
    for match in pattern.finditer(text):
        value = next((group for group in match.groups() if group), "").strip()
        if value:
            imports.append(value)
    return imports


def _candidate_paths(root: Path, source: str, import_name: str, known_files: set[str]) -> list[str]:
    """Resolve an import to internal files when its path is unambiguous."""
    source_path = Path(source)
    stem = import_name.split(".")[-1].split("/")[-1].split("::")[-1]
    candidates: set[str] = set()
    if import_name.startswith(".") or import_name.startswith("/"):
        if import_name.startswith(".") and not import_name.startswith("./") and not import_name.startswith("../"):
            leading_dots = len(import_name) - len(import_name.lstrip("."))
            base = source_path.parent
            for _ in range(max(0, leading_dots - 1)):
                base = base.parent
            module = import_name[leading_dots:].replace(".", "/")
            relative = (base / module).as_posix()
        else:
            relative = (source_path.parent / import_name).as_posix()
        relative = str(Path(relative))
        for suffix in ("", ".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".java", ".kt", ".go", ".rs", "/index.ts", "/index.js"):
            if relative + suffix in known_files:
                candidates.add(relative + suffix)
    else:
        # Match package/module paths and class-like imports without guessing between duplicates.
        normalized = import_name.replace(".", "/").replace("::", "/")
        for file in known_files:
            without_ext = str(Path(file).with_suffix(""))
            if without_ext.endswith(normalized) or Path(file).stem == stem:
                candidates.add(file)
    return sorted(candidates) if len(candidates) == 1 else []


def _should_skip(path: Path, relative: Path) -> bool:
    if "/docs/generated/features/" in "/" + relative.as_posix() or path.is_symlink():
        return True
    name = path.name.lower()
    if any(part.lower() in SKIP_DIRS for part in relative.parts):
        return True
    if name in SENSITIVE_NAMES or any(token in name for token in (".pem", ".key", "secret", "credential")):
        return True
    return path.suffix.lower() not in EXTENSIONS


def scan_repository(root: Path) -> KnowledgeGraph:
    root = root.resolve()
    candidates: list[Path] = []
    for current, directories, filenames in os.walk(root):
        current_path = Path(current)
        directories[:] = sorted(
            name for name in directories
            if name.lower() not in SKIP_DIRS and not name.startswith(".") and not name.endswith(".egg-info")
        )
        for filename in filenames:
            path = current_path / filename
            relative = path.relative_to(root)
            if not _should_skip(path, relative):
                candidates.append(path)
                if len(candidates) > MAX_GRAPH_FILES:
                    raise ValueError(f"Repository exceeds the safe limit of {MAX_GRAPH_FILES:,} source files")

    relative_files = sorted(path.relative_to(root).as_posix() for path in candidates)
    known_files = set(relative_files)
    file_nodes: dict[str, Node] = {}
    symbols_by_file: dict[str, list[Node]] = defaultdict(list)
    content_by_file: dict[str, str] = {}
    file_hashes: dict[str, str] = {}
    edges: set[Edge] = set()

    for relative, absolute in zip(relative_files, sorted(candidates, key=lambda p: p.relative_to(root).as_posix())):
        text = _safe_text(absolute)
        if text is None:
            continue
        language = EXTENSIONS[absolute.suffix.lower()]
        file_hashes[relative] = _file_digest(text)
        content_by_file[relative] = text
        file_node = Node(
            id=_stable_id("file", relative, Path(relative).name),
            kind="file",
            name=Path(relative).name,
            path=relative,
        )
        file_nodes[relative] = file_node
        symbols = _extract_symbols(text, relative, language)
        symbols_by_file[relative] = symbols
        for symbol in symbols:
            edges.add(Edge(file_node.id, symbol.id, "contains"))

    symbol_names: dict[str, list[Node]] = defaultdict(list)
    for target_symbols in symbols_by_file.values():
        for node in target_symbols:
            symbol_names[node.name].append(node)

    for relative, text in content_by_file.items():
        language = EXTENSIONS[Path(relative).suffix.lower()]
        for imported in _imports(text, language):
            for target in _candidate_paths(root, relative, imported, set(content_by_file)):
                if target != relative:
                    edges.add(Edge(file_nodes[relative].id, file_nodes[target].id, "imports", imported))

        source_symbols = {node.name: node for node in symbols_by_file[relative]}
        for match in CALL_TOKEN.finditer(text):
            name = match.group(1)
            if name in source_symbols:
                continue
            destinations = symbol_names.get(name, [])
            if len(destinations) == 1 and destinations[0].path != relative:
                edges.add(
                    Edge(
                        file_nodes[relative].id,
                        destinations[0].id,
                        "calls",
                        f"name match at line {_line_for(text, match.start())}",
                        confidence="INFERRED",
                        confidence_score=0.85,
                    )
                )

    domain_nodes: list[Node] = []
    for relative, text in content_by_file.items():
        file_id = file_nodes[relative].id
        language = EXTENSIONS[Path(relative).suffix.lower()]
        found_nodes, found_edges = extract_domain(relative, text, language, file_id, symbols_by_file[relative])
        domain_nodes.extend(found_nodes)
        edges.update(found_edges)
        openapi_nodes, openapi_edges = extract_openapi(relative, text, file_id)
        domain_nodes.extend(openapi_nodes)
        edges.update(openapi_edges)

    dataflow = extract_dataflow(content_by_file)
    domain_nodes.extend(dataflow.nodes)
    edges.update(dataflow.edges)
    domain_nodes = merge_domain_nodes(domain_nodes)
    edges.update(connect_persistence(symbols_by_file, content_by_file, domain_nodes))
    nodes = [*file_nodes.values()]
    nodes.extend(symbol for symbols in symbols_by_file.values() for symbol in symbols)
    nodes.extend(domain_nodes)
    nodes.sort(key=lambda node: (node.path, node.line or 0, node.kind, node.name))
    return KnowledgeGraph(
        schema_version=SCHEMA_VERSION,
        root=".",
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        nodes=nodes,
        edges=sorted(edges, key=lambda edge: (edge.source, edge.kind, edge.target, edge.evidence or "")),
        files=file_hashes,
    )
