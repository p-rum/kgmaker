"""Graph persistence and human-readable views."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path

from .model import KnowledgeGraph

STATE_DIR = Path(".kgmaker")
GRAPH_FILE = STATE_DIR / "graph.json"
MARKDOWN_FILE = STATE_DIR / "GRAPH.md"
MERMAID_FILE = STATE_DIR / "GRAPH.mmd"


def query_nodes(graph: KnowledgeGraph, terms: str, limit: int = 10, scope: str = "all",
                context_id: str | None = None) -> list[tuple]:
    """Shared navigation ranking; a match never establishes data availability."""
    from .views import project
    graph = project(graph, scope, context_id=context_id)
    words = terms.lower().split()
    nodes = {node.id: node for node in graph.nodes}
    scores = {}
    for node in graph.nodes:
        haystack = f"{node.name} {node.path} {node.signature or ''} {node.summary or ''}".lower()
        score = sum(4 if word == node.name.lower() else 2 if word in node.name.lower()
                    else 1 if word in haystack else 0 for word in words)
        if score:
            scores[node.id] = score
    if not scores:
        return []
    for edge in graph.edges:
        if edge.source in scores and edge.target in nodes:
            scores[edge.target] = max(scores.get(edge.target, 0), scores[edge.source] - 1)
    ranked = sorted(scores, key=lambda identity: (
        -scores[identity], identity))
    return [(nodes[identity], scores[identity]) for identity in ranked[:max(0, limit)]]


def _graph_target(root, relative):
    from .analysis_model import safe_path
    path = safe_path(root, relative.as_posix())
    if path.exists():
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError('Unsafe graph output target')
    return path


def _file_state(path):
    if not path.exists(): return None
    info = path.stat()
    return (info.st_dev, info.st_ino, path.read_bytes())


def save_graph(graph: KnowledgeGraph, root: Path, generate_docs: bool = True, *,
               before_replace=None) -> tuple[Path, Path]:
    """Publish one graph/cache generation after preparing every derived output.

    Graph JSON is the sole authoritative commit and is replaced last. Within a
    single writer, ordinary exceptions restore only generated files this call
    still owns. This is not a multi-writer transaction or crash-recovery journal.
    """
    root = Path(root)
    state_dir = root / STATE_DIR
    graph_path = root / GRAPH_FILE
    markdown_path = root / MARKDOWN_FILE
    mermaid_path = root / MERMAID_FILE
    # Serialization, validation and both renders happen before the first write.
    payload = json.dumps(graph.to_dict(include_cache=True), indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    KnowledgeGraph.from_dict(json.loads(payload))
    outputs = []
    if generate_docs:
        outputs.extend([(MERMAID_FILE, render_mermaid(graph)), (MARKDOWN_FILE, render_markdown(graph))])
    outputs.append((GRAPH_FILE, payload))
    targets = [(relative, _graph_target(root, relative), text.encode('utf-8')) for relative, text in outputs]
    originals = {path: _file_state(path) for _, path, _ in targets}
    prepared, backups, replaced, created = {}, {}, {}, []
    def guard():
        if before_replace is not None: before_replace()
        for relative, path, _ in targets:
            _graph_target(root, relative)
            expected = replaced.get(path, originals[path])
            if _file_state(path) != expected:
                raise ValueError('Graph output changed during publication')
    def temporary(data):
        fd, name = tempfile.mkstemp(prefix='.kgmaker-', dir=state_dir)
        path = Path(name)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            path.unlink(missing_ok=True)
            raise
        return path
    try:
        guard()
        directory = state_dir
        while not directory.exists():
            created.append(directory)
            directory = directory.parent
        state_dir.mkdir(parents=True, exist_ok=True)
        for _, path, data in targets:
            prepared[path] = temporary(data)
            if originals[path] is not None:
                backups[path] = temporary(originals[path][2])
        for _, path, _ in targets:
            guard()
            # Capture ownership before the commit operation: no fallible read
            # may turn a successful final graph replacement into an exception.
            owned = _file_state(prepared[path])
            os.replace(prepared[path], path)
            replaced[path] = owned
    except BaseException:
        for path, owned in reversed(list(replaced.items())):
            # A concurrently changed file is not ours to restore or delete.
            if _file_state(path) != owned: continue
            if originals[path] is None:
                path.unlink()
            else:
                os.replace(backups[path], path)
        raise
    finally:
        for path in [*prepared.values(), *backups.values()]:
            path.unlink(missing_ok=True)
        for directory in created:
            try: directory.rmdir()
            except OSError: pass
    return graph_path, markdown_path


def load_graph(root: Path) -> KnowledgeGraph | None:
    graph_path = root / GRAPH_FILE
    try:
        return KnowledgeGraph.from_dict(json.loads(graph_path.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError, KeyError):
        return None


def load_graph_generation(root: Path) -> tuple[KnowledgeGraph, str] | None:
    """Read the graph and its generation identity from the same atomic file."""
    from .analysis_model import read_regular_bytes

    try:
        graph_path = _graph_target(root, GRAPH_FILE)
        payload = read_regular_bytes(graph_path)
        graph = KnowledgeGraph.from_dict(json.loads(payload.decode("utf-8")))
        if graph.schema_version >= 2:
            # The evidence index uses these fields as keys. Dataclass loading
            # alone does not enforce the scalar types of stored nodes and edges.
            if any(not all(isinstance(value, str) for value in (node.id, node.kind, node.path)) for node in graph.nodes):
                return None
            if any(not isinstance(edge.kind, str) or not isinstance(edge.source_file, (str, type(None)))
                   for edge in graph.edges):
                return None
        return graph, hashlib.sha256(payload).hexdigest()
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return None


def render_markdown(graph: KnowledgeGraph, scope: str = "production") -> str:
    from .views import project
    omitted = sum(n.kind == "file" and scope != "all" and n.scope != scope for n in graph.nodes)
    graph = project(graph, scope)
    files = [node for node in graph.nodes if node.kind == "file"]
    episodes = [node for node in graph.nodes if node.kind == "implementation_episode"]
    symbols = [node for node in graph.nodes if node.kind not in {"file", "implementation_episode"}]
    imports = [edge for edge in graph.edges if edge.kind == "imports"]
    calls = [edge for edge in graph.edges if edge.kind == "calls"]
    domain_edges = [
        edge for edge in graph.edges
        if edge.kind not in {"contains", "imports", "calls", "affected"}
    ]
    by_kind = {kind: sum(node.kind == kind for node in graph.nodes) for kind in (
        "db_table", "db_column", "kafka_topic", "api_endpoint", "frontend_route",
        "external_service", "technology", "concept", "workbook", "workbook_cell",
        "template", "template_fragment", "template_variable", "template_condition"
    )}
    inferred_edges = sum(edge.confidence == "INFERRED" for edge in graph.edges)
    ambiguous_edges = sum(edge.confidence == "AMBIGUOUS" for edge in graph.edges)
    by_path: dict[str, list] = {}
    for symbol in symbols:
        by_path.setdefault(symbol.path, []).append(symbol)

    lines = [
        "# Repository knowledge graph",
        "",
        "> Generated locally by kgmaker. Structural edges come from source text; name-based call edges are heuristic.",
        "> Review semantic conclusions with the repository's Copilot knowledge-graph agent.",
        "",
        f"- Scope: {scope}; omitted files: {omitted}",
        "- Mode: SOURCE_ONLY; coverage: PARTIAL; no build/test/runtime result is implied.",
        "- Freshness below describes the captured snapshot; use `kgmaker status` to compare current inputs.",
        *[f"- Context: `{c.get('id', 'unknown')}`; content: `{c.get('content_hash', 'unknown')}`; freshness: {c.get('freshness', 'UNKNOWN')}" for c in graph.contexts],
        f"- Files indexed: {len(files)}",
        f"- Symbols and sections: {len(symbols)}",
        f"- Internal imports: {len(imports)}",
        f"- Heuristic cross-file calls: {len(calls)}",
        f"- PostgreSQL tables/columns: {by_kind['db_table']}/{by_kind['db_column']}",
        f"- Kafka topics: {by_kind['kafka_topic']}",
        f"- API endpoints: {by_kind['api_endpoint']}",
        f"- TypeScript frontend routes: {by_kind['frontend_route']}",
        f"- Workbooks/cells: {by_kind['workbook']}/{by_kind['workbook_cell']}",
        f"- Templates/fragments/variables/conditions: {by_kind['template']}/{by_kind['template_fragment']}/{by_kind['template_variable']}/{by_kind['template_condition']}",
        f"- Semantic concepts: {by_kind['concept']}",
        f"- Implementation episodes: {len(episodes)}",
        f"- Inferred/ambiguous relationships: {inferred_edges}/{ambiguous_edges}",
        "",
        "## Architecture diagram",
        "",
        "The diagram groups declarations under their source files and shows detected imports and domain relationships. Heuristic call edges are omitted. An editable standalone Mermaid source is available at `.kgmaker/GRAPH.mmd`.",
        "",
        "```mermaid",
        render_mermaid(graph, scope=scope).rstrip(),
        "```",
        "",
        "## Files and symbols",
        "",
    ]
    for file_node in files:
        children = by_path.get(file_node.path, [])
        lines.append(f"### `{file_node.path}`")
        if not children:
            lines.append("- No declarations extracted.")
        for symbol in children:
            location = f"line {symbol.line}" if symbol.line else ""
            signature = f" — `{symbol.signature}`" if symbol.signature else ""
            summary = f" — {symbol.summary}" if symbol.summary else ""
            lines.append(f"- **{symbol.kind}** `{symbol.name}` {location}{signature}{summary}".strip())
        lines.append("")

    lines.extend(["## Implementation history", ""])
    if episodes:
        for episode in sorted(episodes, key=lambda item: item.id):
            metadata = episode.metadata or {}
            freshness = metadata.get("freshness", "unknown")
            changed = metadata.get("changed_files", [])
            paths = ", ".join(
                item.get("path", "") for item in changed[:5] if isinstance(item, dict)
            ) or "no paths"
            validations = ", ".join(
                f"{item.get('label')}={item.get('status')}"
                for item in metadata.get("validations", [])[:5] if isinstance(item, dict)
            ) or "none"
            lines.append(
                f"- **{episode.name}** — {freshness}; files: {paths}; validation: {validations}"
            )
    else:
        lines.append("- No implementation episodes recorded.")
    lines.append("")

    paths = {node.id: node.path for node in graph.nodes}
    node_index = {node.id: node for node in graph.nodes}
    lines.extend(["## Internal relationships", ""])
    for edge in imports:
        lines.append(f"- `{paths.get(edge.source, edge.source)}` imports `{paths.get(edge.target, edge.target)}` ({_edge_details(edge)})")
    for edge in calls:
        target = next((node for node in graph.nodes if node.id == edge.target), None)
        target_label = f"{edge.target.split(':')[-1]} in `{target.path}`" if target else edge.target
        lines.append(f"- `{paths.get(edge.source, edge.source)}` may call `{target_label}` ({_edge_details(edge)})")
    for edge in domain_edges:
        source = node_index.get(edge.source)
        target = node_index.get(edge.target)
        source_label = source.path if source and source.kind == "file" else f"{source.name} in `{source.path}`" if source else edge.source
        target_label = f"{target.kind} `{target.name}` in `{target.path}`" if target else edge.target
        evidence = f" — {_edge_details(edge)}"
        lines.append(f"- `{source_label}` **{edge.kind}** {target_label}{evidence}")
    if not imports and not calls and not domain_edges:
        lines.append("- No internal relationships were detected.")
    lines.extend(["", "## Reading this graph", "", "File and symbol locations are repository-relative. `contains` edges bind declarations to their files. Domain edges such as `maps_to_table`, `consumes`, and `calls_endpoint` record annotations, SQL definitions, configuration, or literal paths found in source. `calls` edges are conservative name matches and must be verified before relying on them.", ""])
    return "\n".join(lines)


def render_mermaid(graph: KnowledgeGraph, scope: str = "production") -> str:
    """Render a compact architecture map, grouping code symbols by source file."""
    from .views import project
    graph = project(graph, scope)
    file_nodes = {node.id: node for node in graph.nodes if node.kind == "file"}
    file_by_path = {node.path: node.id for node in file_nodes.values()}
    all_nodes = {node.id: node for node in graph.nodes}

    # Preserve meaningful domain objects as distinct vertices. Source declarations
    # are represented by their file to keep the diagram navigable on larger repos.
    domain_kinds = {
        "db_table", "db_column", "kafka_topic", "api_endpoint", "frontend_route",
        "external_service", "technology", "concept", "workbook", "workbook_sheet",
        "workbook_cell", "workbook_named_range", "template", "template_fragment",
        "template_variable", "template_condition",
    }
    selected: dict[str, tuple[str, str]] = {}
    for node in graph.nodes:
        if node.kind == "file":
            selected[node.id] = (node.path, "file")
        elif node.kind in domain_kinds:
            selected[node.id] = (f"{node.kind}: {node.name}", node.kind)

    relationships: set[tuple[str, str, str]] = set()
    for edge in graph.edges:
        if edge.kind in {"contains", "calls", "affected"}:
            continue
        source = all_nodes.get(edge.source)
        target = all_nodes.get(edge.target)
        if source is None or target is None:
            continue
        source_id = source.id if source.id in selected else file_by_path.get(source.path)
        target_id = target.id if target.id in selected else file_by_path.get(target.path)
        if source_id and target_id and source_id != target_id:
            relationships.add((source_id, target_id, edge.kind))

    used_ids = {endpoint for source, target, _ in relationships for endpoint in (source, target)}
    used_ids.update(node_id for node_id, (_, kind) in selected.items() if kind != "file")
    id_map = {node_id: f"n{index}" for index, node_id in enumerate(sorted(used_ids))}
    lines = ["flowchart LR"]
    for node_id in sorted(used_ids):
        label, kind = selected[node_id]
        safe_label = " ".join(label.replace('"', "'").replace("[", "(").replace("]", ")").split())
        if kind == "file":
            lines.append(f'  {id_map[node_id]}["{safe_label}"]')
        else:
            lines.append(f'  {id_map[node_id]}{{"{safe_label}"}}')
    for source, target, kind in sorted(relationships):
        label = kind.replace("|", "/").replace("[", "(").replace("]", ")")
        lines.append(f"  {id_map[source]} -->|{label}| {id_map[target]}")
    if not used_ids:
        lines.append('  empty["No architecture relationships detected"]')
    return "\n".join(lines) + "\n"


def render_context(graph: KnowledgeGraph, limit: int = 8_000, root: Path | None = None) -> str:
    """Compact context intended for Copilot's sessionStart additionalContext."""
    from .views import project
    unknown = sum(n.scope == "unknown" and n.kind == "file" for n in graph.nodes)
    graph = project(graph, "production")
    files = [node for node in graph.nodes if node.kind == "file"]
    symbols = [node for node in graph.nodes if node.kind not in {"file", "implementation_episode"}]
    outgoing: dict[str, list[str]] = {}
    nodes = {node.id: node for node in graph.nodes}
    for edge in graph.edges:
        if edge.kind not in {"contains", "affected"}:
            target = nodes.get(edge.target)
            if target:
                confidence = "" if edge.confidence == "EXTRACTED" else f" [{edge.confidence} {edge.confidence_score:.2f}]"
                outgoing.setdefault(edge.source, []).append(f"{edge.kind} {target.name} ({target.path}){confidence}")

    lines = [
        "## kgmaker repository context",
        f"Indexed {len(files)} files and {len(symbols)} declarations/sections.",
        "Use these entries as navigation hints; inspect source files before drawing conclusions.",
        f"Production scope; {unknown} files with unknown scope omitted. SOURCE_ONLY, partial coverage.",
    ]
    for file_node in files:
        declarations = [node for node in symbols if node.path == file_node.path]
        decl_text = ", ".join(
            f"{node.name} ({node.kind}{', line ' + str(node.line) if node.line else ''})"
            for node in declarations[:12]
        ) or "no declarations extracted"
        relations = "; ".join(outgoing.get(file_node.id, [])[:5])
        line = f"- {file_node.path}: {decl_text}"
        if relations:
            line += f"; {relations}"
        lines.append(line)
    notes_file = (root or Path(graph.root)) / ".kgmaker" / "NOTES.md"
    try:
        notes = notes_file.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        notes = ""
    if notes:
        lines.extend(["", "### Verified repository notes", notes])
    result = "\n".join(lines)
    if len(result) > limit:
        result = result[: limit - 80].rsplit("\n", 1)[0] + "\n… graph context truncated; run `kgmaker query`."
    return result


def render_bootstrap(graph: KnowledgeGraph, limit: int = 8_000) -> str:
    """Render lean session guidance; request-specific details come from memory recall."""
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 80:
        raise ValueError("bootstrap limit must be an integer of at least 80 characters")
    files = sorted(node.path for node in graph.nodes if node.kind == "file")
    unknown = sum(node.scope == "unknown" and node.kind == "file" for node in graph.nodes)
    declarations = sum(node.kind not in {"file", "implementation_episode"} for node in graph.nodes)
    episodes = sum(node.kind == "implementation_episode" for node in graph.nodes)
    lines = [
        "## kgmaker bootstrap",
        f"Indexed {len(files)} files, {declarations} declarations/sections, and {episodes} implementation episodes.",
        f"Production scope; {unknown} files with unknown scope omitted.",
        "Before implementation run `kgmaker memory recall \"<request>\"`, then inspect the cited source and tests.",
        "Graph hints may be stale or heuristic; verify them in source.",
    ]
    stale = [context for context in graph.contexts
             if context.get("analyzer_version") and context.get("freshness") == "STALE"]
    for context in stale:
        lines.append("Compiler context is stale ("
                     + "/".join(str(context.get(key, "?")) for key in ("module", "source_set", "scope"))
                     + "): " + str(context.get("stale_reason", "inputs changed"))
                     + ". Run `" + str(context.get("next_command", "kgmaker inspect")) + "`.")
    result = "\n".join(lines)
    if len(result) > limit:
        suffix = "\n… bootstrap truncated; use `kgmaker memory recall`."
        result = result[: max(0, limit - len(suffix))].rsplit("\n", 1)[0] + suffix
    return result[:limit]


def _edge_details(edge) -> str:
    details = [edge.evidence] if edge.evidence else []
    if edge.source_file:
        location = f"{edge.source_file}:{edge.source_line}" if edge.source_line else edge.source_file
        details.append(location)
    if edge.confidence != "EXTRACTED":
        details.append(f"{edge.confidence} {edge.confidence_score:.2f}")
    return "; ".join(details) or edge.confidence
