"""Graph persistence and human-readable views."""

from __future__ import annotations

import json
from pathlib import Path

from .model import KnowledgeGraph

STATE_DIR = Path(".kgmaker")
GRAPH_FILE = STATE_DIR / "graph.json"
MARKDOWN_FILE = STATE_DIR / "GRAPH.md"


def save_graph(graph: KnowledgeGraph, root: Path) -> tuple[Path, Path]:
    state_dir = root / STATE_DIR
    state_dir.mkdir(parents=True, exist_ok=True)
    graph_path = root / GRAPH_FILE
    markdown_path = root / MARKDOWN_FILE
    graph_path.write_text(json.dumps(graph.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(graph), encoding="utf-8")
    return graph_path, markdown_path


def load_graph(root: Path) -> KnowledgeGraph | None:
    graph_path = root / GRAPH_FILE
    try:
        return KnowledgeGraph.from_dict(json.loads(graph_path.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError, KeyError):
        return None


def render_markdown(graph: KnowledgeGraph) -> str:
    files = [node for node in graph.nodes if node.kind == "file"]
    symbols = [node for node in graph.nodes if node.kind != "file"]
    imports = [edge for edge in graph.edges if edge.kind == "imports"]
    calls = [edge for edge in graph.edges if edge.kind == "calls"]
    domain_edges = [edge for edge in graph.edges if edge.kind not in {"contains", "imports", "calls"}]
    by_kind = {kind: sum(node.kind == kind for node in graph.nodes) for kind in (
        "db_table", "db_column", "kafka_topic", "api_endpoint", "frontend_route", "external_service", "technology"
    )}
    by_path: dict[str, list] = {}
    for symbol in symbols:
        by_path.setdefault(symbol.path, []).append(symbol)

    lines = [
        "# Repository knowledge graph",
        "",
        "> Generated locally by kgmaker. Structural edges come from source text; name-based call edges are heuristic.",
        "> Review semantic conclusions with the repository's Copilot knowledge-graph agent.",
        "",
        f"- Files indexed: {len(files)}",
        f"- Symbols and sections: {len(symbols)}",
        f"- Internal imports: {len(imports)}",
        f"- Heuristic cross-file calls: {len(calls)}",
        f"- PostgreSQL tables/columns: {by_kind['db_table']}/{by_kind['db_column']}",
        f"- Kafka topics: {by_kind['kafka_topic']}",
        f"- API endpoints: {by_kind['api_endpoint']}",
        f"- TypeScript frontend routes: {by_kind['frontend_route']}",
        f"- Generated: {graph.generated_at}",
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

    paths = {node.id: node.path for node in graph.nodes}
    node_index = {node.id: node for node in graph.nodes}
    lines.extend(["## Internal relationships", ""])
    for edge in imports:
        lines.append(f"- `{paths.get(edge.source, edge.source)}` imports `{paths.get(edge.target, edge.target)}` (`{edge.evidence}`)")
    for edge in calls:
        target = next((node for node in graph.nodes if node.id == edge.target), None)
        target_label = f"{edge.target.split(':')[-1]} in `{target.path}`" if target else edge.target
        lines.append(f"- `{paths.get(edge.source, edge.source)}` may call `{target_label}` ({edge.evidence})")
    for edge in domain_edges:
        source = node_index.get(edge.source)
        target = node_index.get(edge.target)
        source_label = source.path if source and source.kind == "file" else f"{source.name} in `{source.path}`" if source else edge.source
        target_label = f"{target.kind} `{target.name}` in `{target.path}`" if target else edge.target
        evidence = f" — {edge.evidence}" if edge.evidence else ""
        lines.append(f"- `{source_label}` **{edge.kind}** {target_label}{evidence}")
    if not imports and not calls and not domain_edges:
        lines.append("- No internal relationships were detected.")
    lines.extend(["", "## Reading this graph", "", "File and symbol locations are repository-relative. `contains` edges bind declarations to their files. Domain edges such as `maps_to_table`, `consumes`, and `calls_endpoint` record annotations, SQL definitions, configuration, or literal paths found in source. `calls` edges are conservative name matches and must be verified before relying on them.", ""])
    return "\n".join(lines)


def render_context(graph: KnowledgeGraph, limit: int = 8_000, root: Path | None = None) -> str:
    """Compact context intended for Copilot's sessionStart additionalContext."""
    files = [node for node in graph.nodes if node.kind == "file"]
    symbols = [node for node in graph.nodes if node.kind != "file"]
    outgoing: dict[str, list[str]] = {}
    nodes = {node.id: node for node in graph.nodes}
    for edge in graph.edges:
        if edge.kind != "contains":
            target = nodes.get(edge.target)
            if target:
                outgoing.setdefault(edge.source, []).append(f"{edge.kind} {target.name} ({target.path})")

    lines = [
        "## kgmaker repository context",
        f"Indexed {len(files)} files and {len(symbols)} declarations/sections.",
        "Use these entries as navigation hints; inspect source files before drawing conclusions.",
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
