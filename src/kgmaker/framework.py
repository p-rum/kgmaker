"""Evidence-backed Spring and persistence projections for compiler graphs.

The JVM worker deliberately stops at language and bytecode facts.  This module
adds a small, deterministic framework layer on top of those facts.  It only
uses annotations, declarations and the already imported schema graph; it never
starts an application, loads a Spring context, connects to a database, or
turns a name match into a resolved call.
"""
from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path
from typing import Any

from .analysis_model import AnalysisError, digest
from .model import Edge, KnowledgeGraph, Node


SPRING_STEREOTYPES = {
    "Component", "Service", "Repository", "Controller", "RestController",
    "Configuration", "ControllerAdvice", "RestControllerAdvice",
}
SPRING_ENTRYPOINTS = {
    "KafkaListener": "kafka_listener", "Scheduled": "scheduled",
    "EventListener": "event_listener", "Async": "async_boundary",
    "ApplicationRunner": "application_runner", "CommandLineRunner": "command_runner",
}
SPRING_ADVICE = {"Transactional", "Async", "Cacheable", "CachePut", "CacheEvict", "Secured", "PreAuthorize"}
SPRING_SELECTION = {"Qualifier", "Primary", "Profile"}
HTTP_ANNOTATIONS = {"GetMapping": "GET", "PostMapping": "POST", "PutMapping": "PUT",
                    "PatchMapping": "PATCH", "DeleteMapping": "DELETE", "RequestMapping": None}
JPA_TYPES = {"Entity", "Embeddable", "MappedSuperclass"}
JPA_FIELDS = {
    "Id", "EmbeddedId", "Column", "Embedded", "AttributeOverride", "AttributeOverrides",
    "ManyToOne", "OneToMany", "OneToOne", "ManyToMany", "JoinColumn", "JoinTable",
}
JPA_REPOSITORIES = {"JpaRepository", "CrudRepository", "PagingAndSortingRepository", "Repository"}


def _simple(value: str) -> str:
    return value.rsplit(".", 1)[-1]


def _line(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _args(annotation: str) -> str:
    match = re.search(r"\((.*)\)\s*$", annotation, re.S)
    return match.group(1).strip() if match else ""


def _string_arg(args: str, names: tuple[str, ...] = ("name", "value", "path")) -> str | None:
    for name in names:
        match = re.search(rf"\b{name}\s*=\s*(?:[\"']([^\"']+)[\"']|([A-Za-z0-9_./:$-]+))", args)
        if match:
            return match.group(1) or match.group(2)
    match = re.match(r"\s*(?:[\"']([^\"']+)[\"']|([A-Za-z0-9_./:$-]+))", args)
    return (match.group(1) or match.group(2)) if match else None


def _named_string_arg(args: str, name: str) -> str | None:
    match = re.search(rf"\b{name}\s*=\s*(?:[\"']([^\"']+)[\"']|([A-Za-z0-9_./:$-]+))", args)
    return (match.group(1) or match.group(2)) if match else None


def _annotation_values(text: str, line: int) -> list[tuple[str, str]]:
    """Read annotations immediately preceding a declaration.

    A short look-behind is intentional: annotations belong to the following
    declaration, while a broad search would attach a class annotation to an
    unrelated method and create false framework edges.
    """
    lines = text.splitlines()
    start = max(0, line - 9)
    values: list[tuple[str, str]] = []
    for raw in lines[start:line]:
        for match in re.finditer(r"@([A-Za-z_][\w.]*)\s*(\([^\n]*\))?", raw):
            values.append((match.group(1), _args(match.group(0))))
    return values


def _imports(text: str) -> set[str]:
    return set(re.findall(r"(?:^|[;\n])\s*import\s+([\w.*]+)", text))


def _allowed_annotation(name: str, imports: set[str], families: tuple[str, ...]) -> bool:
    if "." in name:
        return any(name.startswith(prefix) for prefix in families)
    return any(
        item == name or item.endswith("." + name) or item.endswith(".*") and any(
            item[:-1].startswith(prefix) for prefix in families
        )
        for item in imports
    )


def _annotation_map(symbol: dict[str, Any], source: str) -> list[tuple[str, str]]:
    values = []
    for item in symbol.get("annotations", []) if isinstance(symbol.get("annotations"), list) else []:
        if isinstance(item, dict) and isinstance(item.get("name"), str):
            raw_values = item.get("values", {})
            if isinstance(raw_values, dict):
                parts = []
                for key, value in raw_values.items():
                    if isinstance(value, list):
                        value = value[0] if value else None
                    if value not in (None, ""):
                        parts.append(f'{key}="{value}"')
                args = ",".join(parts)
            else:
                args = str(raw_values)
            values.append((item["name"], args))
    if not values and symbol.get("path") and symbol.get("range", {}).get("start_line"):
        values = _annotation_values(source, int(symbol["range"]["start_line"]))
    return values


def _annotation(values: list[tuple[str, str]], name: str) -> tuple[str, str] | None:
    return next((item for item in values if _simple(item[0]) == name), None)


def _path_text(root: Path, path: str) -> str:
    candidate = root / path
    try:
        candidate.resolve().relative_to(root.resolve())
        return candidate.read_text(encoding="utf-8", errors="replace")
    except (OSError, ValueError):
        return ""


def _node_id(prefix: str, payload: Any) -> str:
    return f"framework:{prefix}:{digest(payload)[:32]}"


def augment_framework_graph(root: Path, graph: KnowledgeGraph, context: dict[str, Any]) -> KnowledgeGraph:
    """Add Spring/JPA facts to one compiler context.

    The returned graph is still schema 3.  Framework facts have their own
    evidence kind and context ID, so callers can filter them independently of
    compiler-resolved calls and source-only domain edges.
    """
    context_id = context.get("id")
    if not isinstance(context_id, str) or not context_id:
        raise AnalysisError("Framework augmentation requires an analysis context")
    nodes = {node.id: node for node in graph.nodes}
    symbols = {item.get("id"): item for item in graph.symbols if isinstance(item, dict) and isinstance(item.get("id"), str)}
    source_text = {path: _path_text(root, path) for path in graph.files if Path(path).suffix.lower() in {".java", ".kt", ".kts"}}
    evidence = {item["id"]: item for item in graph.evidence if isinstance(item, dict) and isinstance(item.get("id"), str)}
    edges = {(item.source, item.target, item.kind): item for item in graph.edges}
    diagnostics = list(graph.diagnostics)
    annotations: list[dict[str, Any]] = list(graph.analysis_annotations)
    spring_beans: list[dict[str, Any]] = []
    entity_decls: list[dict[str, Any]] = []
    class_by_name: dict[str, list[str]] = {}

    def evidence_for(kind: str, source: str, target: str, relation: str, path: str, line: int | None, detail: str) -> str:
        record = {"kind": kind, "source": source, "target": target, "relation": relation,
                  "context_ids": [context_id], "source_file": path, "source_line": line,
                  "detail": detail, "framework_rules": context.get("framework_rule_versions", {})}
        identity = "evidence:" + digest(record)
        evidence.setdefault(identity, {"id": identity, **record})
        return identity

    def add_edge(source: str, target: str, kind: str, path: str, line: int | None, detail: str,
                 evidence_kind: str = "FRAMEWORK_DERIVED") -> None:
        if source not in nodes or target not in nodes:
            return
        key = (source, target, kind)
        if key in edges:
            # Keep the stronger, context-bound framework proof when the source
            # scanner produced a weaker domain candidate for the same relation.
            old = edges[key]
            if old.evidence_kind == evidence_kind or evidence_kind != "FRAMEWORK_DERIVED":
                return
        proof = evidence_for(evidence_kind, source, target, kind, path, line, detail)
        edges[key] = Edge(source, target, kind, detail, evidence_kind=evidence_kind,
                          context_ids=(context_id,), evidence_ids=(proof,), source_file=path, source_line=line)

    def add_node(kind: str, name: str, path: str, line: int | None, source: Node | None = None,
                 **metadata: Any) -> str:
        identity = _node_id(kind, {"context": context_id, "path": path, "line": line, "name": name})
        if identity not in nodes:
            nodes[identity] = Node(identity, kind, name, path, line=line,
                                    signature=metadata.pop("signature", None),
                                    summary=metadata.pop("summary", None),
                                    scope=source.scope if source else context.get("scope", "unknown"),
                                    role="contract" if kind in {"spring_endpoint", "spring_entrypoint", "orm_query"} else "executable_code",
                                    origin="generated", metadata=metadata or None)
        return identity

    def symbol_node(item: dict[str, Any]) -> Node | None:
        return nodes.get(item.get("id"))

    def bean_selection(values: list[tuple[str, str]]) -> tuple[list[str], bool, list[str]]:
        qualifiers = []
        primary = False
        profiles = []
        for name, args in values:
            simple = _simple(name)
            value = _string_arg(args, ("value", "name"))
            if simple == "Qualifier" and value:
                qualifiers.append(value)
            elif simple == "Primary":
                primary = True
            elif simple == "Profile" and value:
                profiles.append(value)
        return qualifiers, primary, profiles

    def class_for(item: dict[str, Any]) -> dict[str, Any] | None:
        path = item.get("path")
        line = (item.get("range") or {}).get("start_line")
        candidates = [candidate for candidate in symbols.values()
                      if candidate.get("path") == path and candidate.get("kind") in {"class", "interface", "enum"}
                      and (candidate.get("range") or {}).get("start_line", 0) <= (line or 0)]
        return max(candidates, key=lambda candidate: (candidate.get("range") or {}).get("start_line", 0), default=None)

    for item in symbols.values():
        path = item.get("path")
        if not isinstance(path, str) or path not in source_text:
            continue
        source = source_text[path]
        imports = _imports(source)
        values = _annotation_map(item, source)
        simple_kind = _simple(str(item.get("kind", "")))
        if simple_kind in {"class", "interface", "enum", "type"}:
            class_by_name.setdefault(str(item.get("name", "")), []).append(item["id"])
        spring = [value for value in values if _simple(value[0]) in SPRING_STEREOTYPES and
                  _allowed_annotation(value[0], imports, ("org.springframework.",))]
        jpa = [value for value in values if _simple(value[0]) in JPA_TYPES and
               _allowed_annotation(value[0], imports, ("jakarta.persistence.", "javax.persistence."))]
        node = symbol_node(item)
        if node is None:
            continue
        path_line = (item.get("range") or {}).get("start_line")
        if spring:
            bean_name = _string_arg(spring[0][1], ("value", "name")) or node.name
            qualifiers, primary, profiles = bean_selection(values)
            types = [node.name] + [_simple(str(supertype)) for supertype in item.get("supertypes", [])]
            bean_id = add_node("spring_bean", bean_name, path, path_line, node,
                               stereotype=_simple(spring[0][0]), qualifier=bean_name,
                               qualifiers=qualifiers, primary=primary, profiles=profiles, types=types)
            add_edge(node.id, bean_id, "defines_bean", path, path_line, "Spring stereotype with resolved FQ import")
            spring_beans.append({"node": node, "bean": bean_id, "type": node.name, "types": types,
                                 "name": bean_name, "qualifiers": qualifiers, "primary": primary,
                                 "profiles": profiles, "annotations": values, "path": path, "line": path_line})
        if jpa:
            entity_decls.append({"node": node, "symbol": item, "annotations": values, "path": path, "line": path_line,
                                 "source": source, "imports": imports})

    # @Bean methods are bean definitions even when the containing class is a
    # configuration class.  They are kept separate from class stereotypes.
    for item in symbols.values():
        path = item.get("path")
        if not isinstance(path, str) or path not in source_text or item.get("kind") not in {"method", "constructor"}:
            continue
        values = _annotation_map(item, source_text[path])
        bean_annotation = _annotation(values, "Bean")
        if bean_annotation and _allowed_annotation(bean_annotation[0], _imports(source_text[path]), ("org.springframework.",)):
            node = symbol_node(item)
            if node:
                line = (item.get("range") or {}).get("start_line")
                name = _string_arg(bean_annotation[1], ("name", "value")) or node.name
                qualifiers, primary, profiles = bean_selection(values)
                return_type = item.get("return_type", node.name).split("<", 1)[0].rsplit(".", 1)[-1]
                types = [return_type]
                bean_id = add_node("spring_bean", name, path, line, node, stereotype="Bean", qualifier=name,
                                   qualifiers=qualifiers, primary=primary, profiles=profiles, types=types)
                add_edge(node.id, bean_id, "defines_bean", path, line, "@Bean method")
                spring_beans.append({"node": node, "bean": bean_id, "type": return_type, "types": types,
                                     "name": name, "qualifiers": qualifiers, "primary": primary,
                                     "profiles": profiles, "annotations": values, "path": path, "line": line})

    # Explicit HTTP/listener/scheduler entrypoints and framework advice.
    for item in symbols.values():
        path = item.get("path")
        if not isinstance(path, str) or path not in source_text or item.get("kind") not in {"method", "constructor"}:
            continue
        source = source_text[path]
        imports = _imports(source)
        values = _annotation_map(item, source)
        node = symbol_node(item)
        if node is None:
            continue
        line = (item.get("range") or {}).get("start_line")
        for annotation, args in values:
            name = _simple(annotation)
            if name in HTTP_ANNOTATIONS and _allowed_annotation(annotation, imports, ("org.springframework.web.",)):
                verb = HTTP_ANNOTATIONS[name]
                if verb is None:
                    method_match = re.search(r"\bmethod\s*=\s*(?:RequestMethod\.)?([A-Z]+)", args)
                    verb = method_match.group(1) if method_match else None
                path_value = _string_arg(args, ("path", "value")) or "/"
                endpoint = add_node("spring_endpoint", f"{verb or 'REQUEST'} {path_value}", path, line, node,
                                    http_method=verb, endpoint_path=path_value)
                add_edge(node.id, endpoint, "exposes_endpoint", path, line, f"@{name} with Spring web annotation")
            if name in SPRING_ENTRYPOINTS:
                if not _allowed_annotation(annotation, imports, ("org.springframework.",)):
                    continue
                entry = add_node("spring_entrypoint", f"{SPRING_ENTRYPOINTS[name]}:{node.name}", path, line, node,
                                 entrypoint_kind=SPRING_ENTRYPOINTS[name], async_boundary=name in {"Async", "EventListener", "KafkaListener"})
                add_edge(node.id, entry, "declares_entrypoint", path, line, f"@{name} framework entrypoint")
            if name in SPRING_ADVICE:
                if _allowed_annotation(annotation, imports, ("org.springframework.",)):
                    advice = add_node("spring_advice", f"{name}:{node.name}", path, line, node, advice=name)
                    add_edge(node.id, advice, "advised_by", path, line, f"@{name} advice declaration")

    # Constructor/field injection is intentionally conservative.  A matching
    # type is a candidate, while qualifier/primary/profile controls the result.
    for path, source in source_text.items():
        imports = _imports(source)
        if not any(item.startswith("org.springframework") or item.startswith("jakarta.inject") or item.startswith("javax.inject") for item in imports):
            continue
        type_lines = [(node, (symbols.get(node.id) or {}).get("range", {}).get("start_line", 0))
                      for node in nodes.values() if node.path == path and node.kind in {"class", "interface"}]
        for match in re.finditer(r"(?P<ann>@(?:Autowired|Inject|Resource|Qualifier)(?:\([^\n]*\))?\s*)*(?P<type>[A-Z][\w.]*(?:\s*<[^;=]+>)?)\s+(?P<name>\w+)\s*(?:[;=]|(?:=\s*lateinit))", source):
            line = _line(source, match.start())
            owner = max((node for node, start in type_lines if start <= line), key=lambda node: (symbols.get(node.id) or {}).get("range", {}).get("start_line", 0), default=None)
            if owner is None:
                continue
            type_name = match.group("type").split("<", 1)[0].rsplit(".", 1)[-1]
            qualifiers = _annotation_values(source, line)
            qualifier = next((_string_arg(args, ("value", "name")) for name, args in qualifiers if _simple(name) == "Qualifier"), None)
            candidates = [bean for bean in spring_beans if type_name in bean.get("types", [bean["type"]])]
            if qualifier:
                candidates = [bean for bean in candidates if qualifier in {bean["name"], *bean.get("qualifiers", [])}]
            active_profiles = context.get("spring_profiles")
            if isinstance(active_profiles, list):
                candidates = [bean for bean in candidates if not bean.get("profiles") or
                              set(bean["profiles"]) & set(active_profiles)]
            elif any(bean.get("profiles") for bean in candidates):
                diagnostics.append({"code": "SPRING_PROFILE_UNRESOLVED", "path": path, "source_line": line,
                                    "type": type_name, "reason": "Active Spring profiles were not supplied; profile-specific candidates remain unresolved."})
            if len(candidates) > 1:
                primaries = [bean for bean in candidates if bean.get("primary")]
                if len(primaries) == 1:
                    candidates = primaries
                else:
                    diagnostics.append({"code": "SPRING_AMBIGUOUS_BEAN", "path": path, "source_line": line,
                                        "type": type_name, "candidates": [bean["bean"] for bean in candidates],
                                        "reason": "Multiple type-compatible beans; no unique Qualifier/Primary evidence."})
            injection = add_node("spring_injection", f"{owner.name}.{match.group('name')}", path, line, owner,
                                 type=type_name, qualifier=qualifier)
            if not candidates:
                diagnostics.append({"code": "SPRING_UNRESOLVED_INJECTION", "path": path, "source_line": line,
                                    "type": type_name, "reason": "No type-compatible bean declaration in indexed source scope."})
            for bean in candidates:
                add_edge(injection, bean["bean"], "injects_bean", path, line, "Explicit injection point and type-compatible bean candidate")

    # ORM entities, persistent attributes and repository/query declarations.
    schema_tables = [node for node in nodes.values() if node.kind == "db_table"]
    schema_columns = [node for node in nodes.values() if node.kind == "db_column"]
    realm_prefix = None
    if context.get("database_id") and context.get("schema_stream_id"):
        realm_prefix = f"schema:{context['database_id']}:{context['schema_stream_id']}:"

    def in_schema_realm(candidate: Node) -> bool:
        return realm_prefix is None or candidate.id.startswith(realm_prefix)
    for entity in entity_decls:
        node: Node = entity["node"]
        values = entity["annotations"]
        table_annotation = _annotation(values, "Table")
        table_name = _string_arg(table_annotation[1], ("name", "value")) if table_annotation else None
        table_schema = _named_string_arg(table_annotation[1], "schema") if table_annotation else None
        inferred = table_name is None
        table_name = table_name or node.name
        qualified_table = f"{table_schema}.{table_name}" if table_schema else table_name
        table_id = add_node("orm_table", qualified_table, entity["path"], entity["line"], node,
                            logical_name=table_name, schema=table_schema, inferred=inferred,
                            database_id=context.get("database_id"),
                            schema_stream_id=context.get("schema_stream_id"),
                            persistence_unit=context.get("persistence_unit"),
                            naming_strategy=context.get("naming_strategy"))
        add_edge(node.id, table_id, "maps_to_table", entity["path"], entity["line"],
                 "@Table name" if not inferred else "Entity name fallback; physical naming strategy not verified")
        matches = [candidate for candidate in schema_tables if in_schema_realm(candidate)
                   and (candidate.name.casefold() == qualified_table.casefold()
                        if table_schema else candidate.name.casefold().rsplit(".", 1)[-1] == table_name.casefold())]
        if inferred:
            matches = []
            diagnostics.append({"code": "ORM_NAMING_STRATEGY_UNVERIFIED", "path": entity["path"],
                                "source_line": entity["line"], "entity": node.id,
                                "reason": "Entity without explicit @Table cannot be bound to a physical table without a verified naming strategy."})
        elif len(matches) == 1:
            add_edge(table_id, matches[0].id, "resolves_to_schema_table", entity["path"], entity["line"], "Exact Flyway/schema table name")
        elif len(matches) == 0:
            diagnostics.append({"code": "ORM_SCHEMA_TABLE_UNRESOLVED", "path": entity["path"], "source_line": entity["line"],
                                "entity": node.id, "table": qualified_table,
                                "reason": "No matching table in the indexed schema scope; deployment availability is unknown."})
        else:
            diagnostics.append({"code": "ORM_SCHEMA_TABLE_AMBIGUOUS", "path": entity["path"],
                                "source_line": entity["line"], "entity": node.id,
                                "table": qualified_table, "candidates": [item.id for item in matches],
                                "reason": "Multiple database/stream tables match; supply an explicit persistence realm."})
        text = entity["source"]
        start = entity["line"] or 1
        next_types = [item.get("line") for item in entity_decls if item.get("line") and item["line"] > start]
        body = "\n".join(text.splitlines()[start - 1:min(next_types or [len(text.splitlines()) + 1])])
        for field_match in re.finditer(r"(?P<annotations>(?:@[\w.]+(?:\([^\n]*\))?\s*)*)(?P<type>[A-Za-z_][\w.<>, ?\[\]]*)\s+(?P<name>[A-Za-z_]\w*)\s*(?:[;=]|$)", body, re.M):
            field_annotations = [(name, args) for name, args in re.findall(r"@([\w.]+)\s*(\([^\n]*\))?", field_match.group("annotations"))]
            if not field_annotations or not any(_simple(name) in JPA_FIELDS for name, _ in field_annotations):
                continue
            field_line = start + body[:field_match.start()].count("\n")
            attribute = add_node("orm_attribute", f"{node.name}.{field_match.group('name')}", entity["path"], field_line, node,
                                 attribute=field_match.group("name"), type=field_match.group("type").strip())
            add_edge(attribute, table_id, "declared_on_table", entity["path"], field_line, "JPA persistent attribute")
            relation_names = {"ManyToOne", "OneToMany", "OneToOne", "ManyToMany"}
            relation = next((name for name, _ in field_annotations if _simple(name) in relation_names), None)
            if relation:
                association = add_node("orm_association", f"{node.name}.{field_match.group('name')}", entity["path"], field_line, node,
                                       association=_simple(relation), target_type=field_match.group("type").strip())
                add_edge(attribute, association, "declares_association", entity["path"], field_line,
                         f"JPA relationship @{_simple(relation)}")
                join = next((args for name, args in field_annotations if _simple(name) in {"JoinColumn", "JoinTable"}), "")
                join_name = _string_arg(join, ("name", "value")) if join else None
                if join_name:
                    join_node = add_node("orm_column", join_name, entity["path"], field_line, node,
                                         logical_name=join_name, inferred=False, join=True)
                    add_edge(association, join_node, "maps_to_join_column", entity["path"], field_line,
                             "Explicit JPA join column/table name")
            column_annotation = next((args for name, args in field_annotations if _simple(name) == "Column"), "")
            column_name = _string_arg(column_annotation, ("name", "value")) if column_annotation else field_match.group("name")
            column_id = add_node("orm_column", column_name, entity["path"], field_line, node,
                                 logical_name=column_name, inferred=not bool(column_annotation))
            add_edge(attribute, column_id, "maps_to_column", entity["path"], field_line,
                     "@Column name" if column_annotation else "Persistent attribute name; converter/naming strategy not verified")
            column_matches = [candidate for candidate in schema_columns if in_schema_realm(candidate)
                              and candidate.name.casefold().rsplit(".", 1)[-1] == column_name.casefold()
                              and len(candidate.name.split(".")) >= 2
                              and candidate.name.split(".")[-2].casefold() == table_name.casefold()]
            if not inferred and len(column_matches) == 1:
                add_edge(column_id, column_matches[0].id, "resolves_to_schema_column", entity["path"], field_line, "Exact schema column name in selected table/realm")
            elif not inferred and len(column_matches) > 1:
                diagnostics.append({"code": "ORM_SCHEMA_COLUMN_AMBIGUOUS", "path": entity["path"],
                                    "source_line": field_line, "attribute": attribute,
                                    "column": column_name, "candidates": [item.id for item in column_matches]})

    for path, source in source_text.items():
        imports = _imports(source)
        repository_matches = list(re.finditer(r"(?:interface|class)\s+(\w+)\s*(?::|extends)\s*([^\{\n]+)", source))
        for match in repository_matches:
            generic = re.search(r"(?:JpaRepository|CrudRepository|PagingAndSortingRepository|Repository)\s*<\s*([\w.]+)", match.group(2))
            if not generic or not any(item.startswith("org.springframework.data") for item in imports):
                continue
            repo_name, model_name = match.group(1), generic.group(1).rsplit(".", 1)[-1]
            line = _line(source, match.start())
            repo = next((node for node in nodes.values() if node.path == path and node.name == repo_name and node.kind in {"class", "interface"}), None)
            models = [candidate for candidate in nodes.values() if candidate.name == model_name and candidate.kind in {"class", "type"}]
            if repo and len(models) == 1:
                add_edge(repo.id, models[0].id, "repository_for", path, line, "Spring Data repository generic")
            elif repo and not models:
                diagnostics.append({"code": "SPRING_DATA_MODEL_UNRESOLVED", "path": path, "source_line": line, "repository": repo.id, "model": model_name})
            if repo:
                # Derived query names are a bounded grammar.  The parser keeps
                # the method and predicate text, while entity/property typing
                # remains unresolved unless the compiler/entity model proves it.
                body_start = match.end()
                body_end = source.find("}", body_start)
                body = source[body_start:body_end if body_end >= 0 else len(source)]
                for derived in re.finditer(
                        r"\b(find|read|get|query|count|exists|delete|remove|stream)\w*By(?P<pred>[A-Z][A-Za-z0-9_]*(?:And|Or|OrderBy)?[A-Z]?[A-Za-z0-9_]*)\s*\(", body):
                    method_name = derived.group(0).split("(", 1)[0].strip()
                    method = next((node for node in nodes.values() if node.path == path and node.kind == "method" and node.name == method_name), None)
                    if method is None:
                        continue
                    query_line = line + body[:derived.start()].count("\n")
                    predicates = re.sub(r"OrderBy.*$", "", method_name.split("By", 1)[1]) if "By" in method_name else ""
                    fields = [part for part in re.split(r"And|Or", predicates) if part]
                    query_id = add_node("orm_query", f"{method_name}:DERIVED", path, query_line, method,
                                        query_language="DERIVED", entity=model_name,
                                        predicates=fields, dynamic=False)
                    add_edge(method.id, query_id, "declares_query", path, query_line,
                             "Spring Data derived query method")
        for query in re.finditer(r"@Query\s*\(([^\n]*)\)", source):
            line = _line(source, query.start())
            raw = query.group(1)
            language = "NATIVE_SQL" if re.search(r"nativeQuery\s*=\s*true", raw, re.I) else "JPQL"
            value = _string_arg(raw, ("value", "query")) or _string_arg(raw, ("value",))
            method = next((node for node in nodes.values() if node.path == path and node.kind in {"method"} and (node.line or 0) >= line), None)
            if method is None:
                diagnostics.append({"code": "SPRING_DATA_QUERY_OWNER_UNRESOLVED", "path": path, "source_line": line})
                continue
            query_id = add_node("orm_query", f"{method.name}:{language}", path, line, method,
                                query_language=language, query=value, dynamic=value is None)
            add_edge(method.id, query_id, "declares_query", path, line, f"@Query {language}")
            if value is None or "#{" in (value or "") or "${" in (value or ""):
                diagnostics.append({"code": "ORM_DYNAMIC_QUERY_UNRESOLVED", "path": path, "source_line": line,
                                    "method": method.id, "query_language": language})

    # Self-invocation is a framework boundary, not a normal proxy traversal.
    for site in graph.call_sites:
        caller = nodes.get(site.get("caller")); target = nodes.get(site.get("declared_target"))
        if not caller or not target or caller.id == target.id:
            continue
        caller_symbol = symbols.get(caller.id, {}); target_symbol = symbols.get(target.id, {})
        if caller_symbol.get("owner") != target_symbol.get("owner"):
            continue
        target_annotations = _annotation_map(target_symbol, source_text.get(target.path, ""))
        if any(_simple(name) in SPRING_ADVICE for name, _ in target_annotations):
            boundary = add_node("spring_proxy_boundary", f"self-invocation:{target.name}", target.path, target.line, target,
                                proxy_traversal=False, reason="same-owner invocation bypasses external proxy")
            add_edge(site["id"], boundary, "bypasses_proxy", target.path, target.line,
                     "Same-class call to advised method; runtime proxy traversal is not observed")
            diagnostics.append({"code": "SPRING_SELF_INVOCATION_PROXY_BOUNDARY", "path": target.path,
                                "source_line": target.line, "call_site": site["id"], "target": target.id})

    # Make the capability and provenance visible in the selected context.
    contexts = list(graph.contexts)
    for index, current in enumerate(contexts):
        if current.get("id") == context_id:
            contexts[index] = {**current, "framework_analysis": {"spring": "annotation-source-v1", "jpa": "annotation-source-v1",
                                                                  "schema_binding": "exact-name-only", "coverage": "PARTIAL"}}
            break
    result = replace(graph, nodes=sorted(nodes.values(), key=lambda item: item.id),
                     edges=sorted(edges.values(), key=lambda item: (item.source, item.kind, item.target)),
                     contexts=contexts, diagnostics=diagnostics, evidence=sorted(evidence.values(), key=lambda item: item["id"]),
                     analysis_annotations=annotations)
    KnowledgeGraph.from_dict(result.to_dict())
    return result
