"""Conservative Thymeleaf variable and backend-binding extraction."""
from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

from .analysis_model import digest
from .model import Edge, KnowledgeGraph, Node

VERSION = "thymeleaf-bindings-1"
_VARIABLE = re.compile(r"\$\{\s*([A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*)*)\s*}")
_BINDING = re.compile(r"\b(?:addAttribute|setVariable)\s*\(\s*[\"']([A-Za-z_][\w]*)[\"']\s*,")
_RETURN = re.compile(r"\breturn\s+[\"']([A-Za-z_][\w/-]*)[\"']")
_PDF = re.compile(r"\b(?:pdfService|pdfRenderer)\s*\.\s*\w+\s*\(\s*[\"']([A-Za-z_][\w/-]*)[\"']", re.I)


def _line(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _node_id(kind: str, path: str, name: str) -> str:
    return f"{kind}:{path}:{name}"


def attach_templates(root: Path, graph: KnowledgeGraph) -> KnowledgeGraph:
    """Attach evidenced Thymeleaf variables and literal backend bindings."""
    root = root.resolve()
    file_nodes = {node.path: node for node in graph.nodes if node.kind == "file"}
    contexts = {context.get("scope"): context.get("id") for context in graph.contexts
                if context.get("mode") == "SOURCE_ONLY"}
    nodes = {node.id: node for node in graph.nodes}
    edges = set(graph.edges)
    evidence = {item["id"]: item for item in graph.evidence}
    variables_by_template: dict[str, list[Node]] = {}
    templates_by_name: dict[str, list[Node]] = {}
    pending_edges: list[tuple[Edge, str, int]] = []

    for relative, file_node in sorted(file_nodes.items()):
        if Path(relative).suffix.lower() != ".html" or "templates" not in Path(relative).parts:
            continue
        try:
            text = (root / relative).read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        template_id = _node_id("template", relative, Path(relative).stem)
        template = Node(template_id, "template", Path(relative).stem, relative, line=1,
                        scope=file_node.scope, role=file_node.role, origin=file_node.origin,
                        build_membership=file_node.build_membership,
                        classification_evidence=file_node.classification_evidence,
                        metadata={"dialect": "thymeleaf", "parser": VERSION})
        nodes[template_id] = template
        templates_by_name.setdefault(Path(relative).with_suffix("").name, []).append(template)
        templates_by_name.setdefault(str(Path(relative).with_suffix("")).split("templates/", 1)[-1], []).append(template)
        found: dict[str, Node] = {}
        for match in _VARIABLE.finditer(text):
            expression = match.group(1)
            identity = _node_id("template_variable", relative, expression)
            variable = Node(identity, "template_variable", expression, relative, line=_line(text, match.start()),
                            summary="${" + expression + "}", scope=file_node.scope, role=file_node.role,
                            origin=file_node.origin, build_membership=file_node.build_membership,
                            classification_evidence=file_node.classification_evidence,
                            metadata={"dialect": "thymeleaf", "expression": expression,
                                      "root": expression.split(".", 1)[0], "parser": VERSION})
            found.setdefault(identity, variable)
        variables_by_template[template_id] = list(found.values())
        nodes.update(found)
        pending_edges.append((Edge(file_node.id, template_id, "defines_template", "Thymeleaf template"), relative, 1))
        for variable in found.values():
            pending_edges.append((Edge(template_id, variable.id, "declares_template_variable", variable.summary),
                                  relative, variable.line or 1))

    for relative, file_node in sorted(file_nodes.items()):
        if Path(relative).suffix.lower() not in {".java", ".kt", ".kts"}:
            continue
        try:
            text = (root / relative).read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        symbols = sorted((node for node in graph.nodes if node.path == relative
                          and node.kind in {"function", "method"} and node.line), key=lambda n: n.line or 0)
        lines = text.splitlines(keepends=True)
        offsets = [0]
        for value in lines:
            offsets.append(offsets[-1] + len(value))
        for index, symbol in enumerate(symbols):
            start_line = symbol.line or 1
            end_line = (symbols[index + 1].line or len(lines) + 1) - 1 if index + 1 < len(symbols) else len(lines)
            body = text[offsets[start_line - 1]:offsets[end_line]]
            returns = {match.group(1) for match in _RETURN.finditer(body)}
            bindings = [(match.group(1), start_line - 1 + _line(body, match.start())) for match in _BINDING.finditer(body)]
            for template_name in returns:
                targets = list({node.id: node for node in templates_by_name.get(template_name, [])}.values())
                if len(targets) != 1:
                    continue
                template = targets[0]
                pending_edges.append((Edge(symbol.id, template.id, "renders_template", f"return {template_name}"),
                                      relative, start_line))
                for key, line in bindings:
                    for variable in variables_by_template.get(template.id, []):
                        if variable.metadata and variable.metadata.get("root") == key:
                            pending_edges.append((Edge(symbol.id, variable.id, "binds_template_variable",
                                                       f"literal model key {key}"), relative, line))
            for match in _PDF.finditer(body):
                template_name = match.group(1)
                targets = list({node.id: node for node in templates_by_name.get(template_name, [])}.values())
                if len(targets) != 1:
                    continue
                boundary_id = "external_service:pdf-renderer"
                nodes.setdefault(boundary_id, Node(boundary_id, "external_service", "PDF renderer", relative,
                                                    line=start_line, scope=file_node.scope,
                                                    role="resource", origin=file_node.origin,
                                                    metadata={"boundary": "external", "parser": VERSION}))
                line = start_line - 1 + _line(body, match.start())
                pending_edges.append((Edge(symbol.id, boundary_id, "calls_pdf_service", "literal PDF renderer call"),
                                      relative, line))
                pending_edges.append((Edge(targets[0].id, boundary_id, "rendered_by", "explicit PDF template argument"),
                                      relative, line))

    for edge, source_file, source_line in pending_edges:
        context_id = contexts.get(nodes[edge.source].scope) if edge.source in nodes else None
        record = {"kind": "SYNTAX_CANDIDATE", "extractor": VERSION, "source_file": source_file,
                  "source_line": source_line, "sha256": graph.files.get(source_file),
                  "source": edge.source, "target": edge.target, "relation": edge.kind,
                  "note": edge.evidence, "context_ids": [context_id] if context_id else [],
                  "origin_trust": "LOCAL_SOURCE", "freshness": "CONTENT_VERIFIED"}
        evidence_id = "evidence:" + digest(record)
        evidence[evidence_id] = {"id": evidence_id, **record}
        edges.add(replace(edge, context_ids=(context_id,) if context_id else (),
                          evidence_ids=(evidence_id,)))

    result = replace(graph, nodes=sorted(nodes.values(), key=lambda n: (n.path, n.line or 0, n.kind, n.name)),
                     edges=sorted(edges, key=lambda e: (e.source, e.kind, e.target)),
                     evidence=[evidence[key] for key in sorted(evidence)])
    KnowledgeGraph.from_dict(result.to_dict())
    return result
