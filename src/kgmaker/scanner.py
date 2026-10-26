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
from dataclasses import asdict, replace

from .domain import connect_persistence, extract_domain, extract_openapi, merge_domain_nodes
from .model import Edge, KnowledgeGraph, Node
from .dataflow import extract_dataflow
from .classification import Classifier
from .analysis_model import AnalysisError, digest

SCHEMA_VERSION = 2
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
    ".html": "html",
}
SKIP_DIRS = {
    ".git", ".hg", ".svn", ".idea", ".vscode", ".venv", "venv", "env",
    "node_modules", "vendor", "build", "dist", "target", "target-k2", "out", "coverage",
    "__pycache__", ".gradle", ".next", ".nuxt", ".kgmaker", "graphify-out",
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
JAVA_METHOD = re.compile(
    r"^\s*(?:(?:public|private|protected|static|final|synchronized|abstract|native|default)\s+)*"
    r"(?!(?:class|interface|enum|record)\s)(?:[\w$<>?,.\[\]]+\s+)+(\w+)\s*\(([^;{}]*)\)\s*"
    r"(?:throws\s+[^{}]+)?\{",
    re.M,
)
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


def _candidate_files(root: Path, project_model: dict | None = None) -> list[Path]:
    candidates: list[Path] = []
    explicit_roots = [r for s in (project_model or {}).get("source_sets", []) for r in s.get("roots", [])]
    for current, directories, filenames in os.walk(root):
        current_path = Path(current)
        def selected_directory(name):
            relative = (current_path / name).relative_to(root).as_posix()
            explicit = any(r == relative or r.startswith(relative + "/") for r in explicit_roots)
            return ((name.lower() not in SKIP_DIRS and not name.startswith(".")) or explicit) and not name.endswith(".egg-info")
        directories[:] = sorted(name for name in directories if selected_directory(name))
        for filename in filenames:
            path = current_path / filename
            relative = path.relative_to(root)
            in_explicit_root = any(relative.as_posix().startswith(r.rstrip("/") + "/") for r in explicit_roots)
            if not _should_skip(path, relative) or (in_explicit_root and not path.is_symlink()
                    and path.suffix.lower() in EXTENSIONS and path.name.lower() not in SENSITIVE_NAMES
                    and not any(token in path.name.lower() for token in (".pem", ".key", "secret", "credential"))):
                candidates.append(path)
                if len(candidates) > MAX_GRAPH_FILES:
                    raise ValueError(f"Repository exceeds the safe limit of {MAX_GRAPH_FILES:,} source files")
    return sorted(candidates, key=lambda p: p.relative_to(root).as_posix())


def scan_repository(root: Path, *, project_model: dict | None = None, strict: bool = False) -> KnowledgeGraph:
    root = root.resolve()
    classifier = Classifier(root, project_model, strict)
    candidates = _candidate_files(root, project_model)

    relative_files = sorted(path.relative_to(root).as_posix() for path in candidates)
    known_files = set(relative_files)
    file_nodes: dict[str, Node] = {}
    symbols_by_file: dict[str, list[Node]] = defaultdict(list)
    content_by_file: dict[str, str] = {}
    file_hashes: dict[str, str] = {}
    edges: set[Edge] = set()
    attempted_reads = {}

    for relative, absolute in zip(relative_files, sorted(candidates, key=lambda p: p.relative_to(root).as_posix())):
        text = _safe_text(absolute)
        attempted_reads[relative] = text
        if text is None:
            classifier.diagnostics.append({"path": relative, "code": "SOURCE_NOT_ANALYZED",
                                           "reason": "Unreadable, non-UTF8 or exceeds source size limit"})
            continue
        language = EXTENSIONS[absolute.suffix.lower()]
        file_hashes[relative] = _file_digest(text)
        content_by_file[relative] = text
        file_node = Node(
            id=_stable_id("file", relative, Path(relative).name),
            kind="file",
            name=Path(relative).name,
            path=relative,
            **asdict(classifier.classify(relative)),
        )
        file_nodes[relative] = file_node
        symbols = [replace(n, scope=file_node.scope, role=file_node.role, origin=file_node.origin,
                           build_membership=file_node.build_membership,
                           classification_evidence=file_node.classification_evidence)
                   for n in _extract_symbols(text, relative, language)]
        symbols_by_file[relative] = symbols
        for symbol in symbols:
            edges.add(Edge(file_node.id, symbol.id, "contains"))

    symbol_names: dict[tuple[str, str], list[Node]] = defaultdict(list)
    for target_symbols in symbols_by_file.values():
        for node in target_symbols:
            if node.role == "executable_code":
                symbol_names[(node.scope, node.name)].append(node)

    for relative, text in content_by_file.items():
        language = EXTENSIONS[Path(relative).suffix.lower()]
        for imported in _imports(text, language):
            allowed = {p for p in content_by_file if file_nodes[p].scope == file_nodes[relative].scope}
            for target in _candidate_paths(root, relative, imported, allowed):
                if target != relative:
                    edges.add(Edge(file_nodes[relative].id, file_nodes[target].id, "imports", imported))

        source_symbols = {node.name: node for node in symbols_by_file[relative]}
        for match in CALL_TOKEN.finditer(text) if file_nodes[relative].role == "executable_code" else ():
            name = match.group(1)
            if name in source_symbols:
                continue
            destinations = symbol_names.get((file_nodes[relative].scope, name), [])
            if len(destinations) == 1 and destinations[0].path != relative:
                edges.add(
                    Edge(
                        file_nodes[relative].id,
                        destinations[0].id,
                        "calls",
                        f"name match at line {_line_for(text, match.start())}",
                        confidence="INFERRED",
                        confidence_score=0.85,
                        source_file=relative,
                        source_line=_line_for(text, match.start()),
                    )
                )

    domain_nodes: list[Node] = []
    # Partition *before* persistence/dataflow resolution and shared-domain merging.
    # A test table/topic/implementation never contributes to production selection.
    for scope in sorted({n.scope for n in file_nodes.values()}):
        sources = {p: t for p, t in content_by_file.items() if file_nodes[p].scope == scope}
        symbols = {p: symbols_by_file[p] for p in sources}
        local_nodes, local_edges = [], set()
        for relative, text in sources.items():
            if file_nodes[relative].role == "documentation":
                continue
            file_id = file_nodes[relative].id
            language = EXTENSIONS[Path(relative).suffix.lower()]
            found_nodes, found_edges = extract_domain(relative, text, language, file_id, symbols[relative])
            local_nodes.extend(found_nodes)
            local_edges.update(found_edges)
            found_nodes, found_edges = extract_openapi(relative, text, file_id)
            local_nodes.extend(found_nodes)
            local_edges.update(found_edges)
        dataflow = extract_dataflow({p: t for p, t in sources.items() if file_nodes[p].role == "executable_code"})
        local_nodes.extend(dataflow.nodes)
        local_edges.update(dataflow.edges)
        local_nodes = merge_domain_nodes(local_nodes)
        local_edges.update(connect_persistence(symbols, sources, local_nodes))
        mapping = {n.id: f"scope:{scope}:{n.id}" if scope != "production" and n.kind in {
            "db_table", "db_column", "kafka_topic", "api_endpoint", "external_service", "technology"}
            else n.id for n in local_nodes}
        for n in local_nodes:
            c = file_nodes.get(n.path)
            local = asdict(classifier.classify(n.path)) if c else {"scope": scope}
            domain_nodes.append(replace(n, id=mapping[n.id], **local))
        edges.update(replace(e, source=mapping.get(e.source, e.source), target=mapping.get(e.target, e.target)) for e in local_edges)
    nodes = [*file_nodes.values()]
    nodes.extend(symbol for symbols in symbols_by_file.values() for symbol in symbols)
    nodes.extend(domain_nodes)
    nodes.sort(key=lambda node: (node.path, node.line or 0, node.kind, node.name))
    if _candidate_files(root, project_model) != candidates or any(_safe_text(root / path) != text for path, text in attempted_reads.items()):
        raise AnalysisError("Source snapshot changed during analysis", 3)
    if Classifier(root, project_model, strict).fingerprint != classifier.fingerprint:
        raise AnalysisError("Classification configuration changed during analysis", 3)
    contexts = []
    for scope in sorted({n.scope for n in file_nodes.values()}):
        scoped_files = {p: h for p, h in file_hashes.items() if file_nodes[p].scope == scope}
        context_id = digest({"classifier": classifier.fingerprint, "scope": scope, "files": scoped_files})
        contexts.append({"id": context_id, "scope": scope, "mode": "SOURCE_ONLY", "classifier_version": "classification-1",
                         "classification_fingerprint": classifier.fingerprint, "content_hash": digest(scoped_files),
                         "origin_trust": "SUPPLIED_MODEL_UNVERIFIED" if project_model is not None else "LOCAL_SOURCE",
                         "freshness": "CONTENT_VERIFIED", "coverage": "PARTIAL",
                         "limitations": ["Source pattern extraction is not compiler resolution.",
                             "Path conventions are fallback; unknown scope is excluded from production views."]})
    by_scope = {c["scope"]: c["id"] for c in contexts}
    by_id = {n.id: n for n in nodes}
    edges = {replace(e, context_ids=tuple(sorted({by_scope[by_id[i].scope] for i in (e.source, e.target)
                                                if i in by_id and by_id[i].scope in by_scope}))) for e in edges}
    evidence, evidenced_edges = {}, set()
    for edge in edges:
        source = by_id.get(edge.source)
        path = edge.source_file or (source.path if source else None)
        record = {"kind": "SYNTAX_CANDIDATE", "extractor": "source-patterns-2", "source_file": path,
                  "source_line": edge.source_line or (source.line if source else None),
                  "sha256": file_hashes.get(path), "source": edge.source, "target": edge.target,
                  "relation": edge.kind, "note": edge.evidence, "context_ids": list(edge.context_ids),
                  "origin_trust": "LOCAL_SOURCE", "freshness": "CONTENT_VERIFIED"}
        evidence_id = "evidence:" + digest(record)
        evidence[evidence_id] = {"id": evidence_id, **record}
        evidenced_edges.add(replace(edge, evidence_ids=(evidence_id,)))
    edges = evidenced_edges
    return KnowledgeGraph(
        schema_version=SCHEMA_VERSION,
        root=".",
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        nodes=nodes,
        edges=sorted(edges, key=lambda edge: (edge.source, edge.kind, edge.target, edge.evidence or "")),
        files=file_hashes,
        contexts=contexts,
        diagnostics=classifier.diagnostics,
        evidence=[evidence[i] for i in sorted(evidence)],
    )
