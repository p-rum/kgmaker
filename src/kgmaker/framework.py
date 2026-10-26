"""Evidence-backed Spring and persistence projections for compiler graphs.

The JVM worker deliberately stops at language and bytecode facts.  This module
adds a small, deterministic framework layer on top of those facts.  It only
uses annotations, declarations and the already imported schema graph; it never
starts an application, loads a Spring context, connects to a database, or
turns a name match into a resolved call.
"""
from __future__ import annotations

import re
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from .analysis_model import AnalysisError, digest
from .model import Edge, KnowledgeGraph, Node
from .spring_imports import selector_info
from .spring_conditions import AnnotationArguments, evaluate_conditions

SPRING_RULE_VERSION = "annotation-source-v6"


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
SPRING_CONDITIONS = {"Conditional", "ConditionalOnProperty", "ConditionalOnClass"}
HTTP_ANNOTATIONS = {"GetMapping": "GET", "PostMapping": "POST", "PutMapping": "PUT",
                    "PatchMapping": "PATCH", "DeleteMapping": "DELETE", "RequestMapping": None}
JPA_TYPES = {"Entity", "Embeddable", "MappedSuperclass"}
JPA_FIELDS = {
    "Id", "EmbeddedId", "Column", "Embedded", "AttributeOverride", "AttributeOverrides",
    "ManyToOne", "OneToMany", "OneToOne", "ManyToMany", "JoinColumn", "JoinTable",
    "Access", "Transient",
}
JPA_REPOSITORIES = {"JpaRepository", "CrudRepository", "PagingAndSortingRepository", "Repository"}
JPA_ANNOTATION_NAMES = JPA_TYPES | JPA_FIELDS | {
    "Query", "NamedQuery", "NamedQueries", "NamedNativeQuery", "NamedNativeQueries",
    "Basic", "Version", "GeneratedValue", "SequenceGenerator", "TableGenerator",
    "Enumerated", "Temporal", "Lob", "ElementCollection", "CollectionTable",
    "MapKey", "OrderBy", "OrderColumn", "Convert", "Converts", "EntityGraph",
    "NamedEntityGraph", "IdClass", "Inheritance", "DiscriminatorColumn", "DiscriminatorValue",
}
JPA_ANNOTATION_PACKAGES = {"jakarta.persistence", "javax.persistence"}

DERIVED_QUERY_OPERATORS = (
    "IsNotNull", "NotNull", "IsNull", "Null", "LessThanEqual", "GreaterThanEqual",
    "StartingWith", "EndingWith", "NotContaining", "Containing", "Contains",
    "NotLike", "Like", "NotIn", "In", "Between", "LessThan", "GreaterThan",
    "Before", "After", "IsTrue", "True", "IsFalse", "False", "IsNot", "Not",
)


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
    # Compiler annotations include default named members (e.g. proxyBeanMethods).
    # An unrelated member name is not the positional bean/name/value argument.
    return (match.group(1) or match.group(2)) if match and not re.match(r"\s*=", args[match.end():]) else None


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


def _allowed_jpa_annotation(name: str, imports: set[str]) -> bool:
    """Accept only known annotations from the canonical JPA packages.

    Prefix checks are appropriate for extensible frameworks, but a subpackage
    such as ``jakarta.persistence.fake`` must never impersonate the API.
    """
    simple = _simple(name)
    if simple not in JPA_ANNOTATION_NAMES:
        return False
    if "." in name:
        return name.rsplit(".", 1)[0] in JPA_ANNOTATION_PACKAGES
    return any(
        item == f"{package}.{simple}" or item == f"{package}.*"
        for package in JPA_ANNOTATION_PACKAGES for item in imports
    )


def _annotation_map(symbol: dict[str, Any], source: str) -> list[tuple[str, str]]:
    def render_value(value: Any) -> str:
        if isinstance(value, dict) and isinstance(value.get("name"), str):
            nested = value.get("values", {})
            args = ",".join(f"{key}={render_value(item)}" for key, item in nested.items()) if isinstance(nested, dict) else ""
            return f"@{value['name']}({args})"
        if isinstance(value, str):
            return json.dumps(value, ensure_ascii=False)
        if isinstance(value, list):
            return "{" + ",".join(render_value(item) for item in value) + "}"
        if isinstance(value, bool):
            return str(value).lower()
        return json.dumps(value, ensure_ascii=False)

    values = []
    for item in symbol.get("annotations", []) if isinstance(symbol.get("annotations"), list) else []:
        if isinstance(item, dict) and isinstance(item.get("name"), str):
            raw_values = item.get("values", {})
            unresolved = item.get("values_resolved") is False
            if unresolved:
                raw_values = {}
            if isinstance(raw_values, dict):
                parts = []
                for key, value in raw_values.items():
                    if isinstance(value, list):
                        if all(isinstance(entry, (str, int, float, bool)) for entry in value):
                            parts.extend(f"{key}={render_value(entry)}" for entry in value)
                        else:
                            parts.append(f"{key}={render_value(value)}")
                    elif value not in (None, ""):
                        parts.append(f"{key}={render_value(value)}")
                args = ",".join(parts)
            else:
                args = str(raw_values)
            if unresolved:
                args = "__UNRESOLVED__"
            values.append((item["name"], AnnotationArguments(args, raw_values,
                           item.get("values_resolved", True) is True)))
    if "annotations" not in symbol and symbol.get("path") and symbol.get("range", {}).get("start_line"):
        values = _annotation_values(source, int(symbol["range"]["start_line"]))
    return values


def _format_annotation_value(value: Any) -> str:
    if isinstance(value, dict) and isinstance(value.get("name"), str):
        nested = value.get("values", {})
        args = ",".join(f"{key}={_format_annotation_value(item)}" for key, item in nested.items()) if isinstance(nested, dict) else ""
        return f"@{value['name']}({args})"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "{" + ",".join(_format_annotation_value(item) for item in value) + "}"
    if isinstance(value, bool):
        return str(value).lower()
    return json.dumps(value, ensure_ascii=False)


def _annotation(values: list[tuple[str, str]], name: str) -> tuple[str, str] | None:
    return next((item for item in values if _simple(item[0]) == name), None)


def _class_args(args: str) -> list[str]:
    """Return class names from compiler or source annotation arguments."""
    values = re.findall(r'["\']([\w.$]+)["\']|\b([A-Za-z_]\w*(?:\.[A-Za-z_$]\w*)+)\s*\.class\b', args)
    return [quoted or literal for quoted, literal in values]


def _combined_state(*states: str) -> str:
    return "INACTIVE" if "INACTIVE" in states else "UNKNOWN" if "UNKNOWN" in states else "ACTIVE"


def _derived_query(method_name: str) -> dict[str, Any] | None:
    match = re.match(
        r"^(?P<action>find|read|get|query|search|stream|count|exists|delete|remove)"
        r"(?:Distinct)?(?:(?:First|Top)\d*)?By(?P<body>[A-Z].*)$", method_name)
    if not match:
        return None
    predicate_text, _, order_text = match.group("body").partition("OrderBy")
    chunks = [item for item in re.split(r"(?<=[a-z0-9])(?:And|Or)(?=[A-Z])", predicate_text) if item]
    predicates = []
    for chunk in chunks:
        operator = "Equals"
        property_name = chunk
        for candidate in DERIVED_QUERY_OPERATORS:
            if chunk.endswith(candidate) and len(chunk) > len(candidate):
                property_name = chunk[:-len(candidate)]
                operator = candidate
                break
        predicates.append({"property": property_name[:1].lower() + property_name[1:], "operator": operator})
    orders = []
    cursor = order_text
    while cursor:
        order = re.match(r"([A-Z][A-Za-z0-9]*?)(Asc|Desc)(?=[A-Z]|$)", cursor)
        if not order:
            orders.append({"property": cursor[:1].lower() + cursor[1:], "direction": "ASC"})
            break
        orders.append({"property": order.group(1)[:1].lower() + order.group(1)[1:],
                       "direction": order.group(2).upper()})
        cursor = cursor[order.end():]
    return {"action": match.group("action"), "predicates": predicates, "order_by": orders}


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
    embeddable_decls: list[dict[str, Any]] = []
    mapped_superclass_decls: list[dict[str, Any]] = []
    class_by_name: dict[str, list[str]] = {}
    annotation_types = {str(item.get("owner")): item for item in symbols.values()
                        if item.get("kind") == "annotation_type" and isinstance(item.get("owner"), str)}

    def evidence_for(kind: str, source: str, target: str, relation: str, path: str, line: int | None, detail: str,
                     compiler_fact: dict | None = None) -> str:
        record = {"kind": kind, "source": source, "target": target, "relation": relation,
                  "context_ids": [context_id], "source_file": path, "source_line": line,
                  "detail": detail, "framework_rules": context.get("framework_rule_versions", {})}
        if compiler_fact is not None:
            record.update(compiler_symbol_id=compiler_fact["id"], sha256=compiler_fact.get("sha256"),
                          compiler_backend=compiler_fact.get("compiler_backend", "javac"))
        identity = "evidence:" + digest(record)
        evidence.setdefault(identity, {"id": identity, **record})
        return identity

    def add_edge(source: str, target: str, kind: str, path: str, line: int | None, detail: str,
                 evidence_kind: str = "FRAMEWORK_DERIVED", compiler_fact: dict | None = None) -> None:
        if source not in nodes or target not in nodes:
            return
        key = (source, target, kind)
        if key in edges:
            # Keep the stronger, context-bound framework proof when the source
            # scanner produced a weaker domain candidate for the same relation.
            old = edges[key]
            if old.evidence_kind == evidence_kind or evidence_kind != "FRAMEWORK_DERIVED":
                return
        proof = evidence_for(evidence_kind, source, target, kind, path, line, detail, compiler_fact)
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
                raw = args.members.get("value") if isinstance(args, AnnotationArguments) and isinstance(args.members, dict) else None
                profiles.extend(raw if isinstance(raw, list) and all(isinstance(x, str) for x in raw) else [value])
        return qualifiers, primary, profiles

    def expanded_annotations(values: list[tuple[str, str]], imports: set[str]) -> list[tuple[str, str]]:
        result = list(values)
        seen: set[str] = set()
        frontier = [name for name, _ in values]
        for _ in range(8):
            following = []
            for name in frontier:
                if "." in name:
                    fqn = name
                else:
                    exact = [item for item in imports if item.endswith("." + name)]
                    local = [owner for owner in annotation_types if owner.rsplit(".", 1)[-1] == name]
                    choices = sorted(set(exact + local))
                    fqn = choices[0] if len(choices) == 1 else ""
                if not fqn or fqn in seen:
                    continue
                seen.add(fqn)
                declaration = annotation_types.get(fqn)
                if declaration is None:
                    continue
                path = declaration.get("path")
                meta = _annotation_map(declaration, source_text.get(path, "")) if isinstance(path, str) else []
                for item in meta:
                    if item not in result:
                        result.append(item);following.append(item[0])
            frontier = following
            if not frontier:
                break
        return result

    def component_scan_state(item: dict[str, Any]) -> tuple[str, list[str]]:
        packages = context.get("spring_component_packages")
        owner = str(item.get("owner", ""))
        package = owner.rsplit(".", 1)[0] if "." in owner else ""
        if not isinstance(packages, list):
            return "UNKNOWN", ["component-scan packages were not supplied"]
        active = any(package == candidate or package.startswith(candidate.rstrip(".") + ".")
                     for candidate in packages if isinstance(candidate, str) and candidate)
        return ("ACTIVE", [f"package {package} is in component scan"]) if active else (
            "INACTIVE", [f"package {package} is outside component scan"])

    def condition_state(values: list[tuple[str, str]], path: str, line: int | None) -> tuple[str, list[str]]:
        imports = _imports(source_text.get(path, ""))
        canonical = []
        for name, args in values:
            if "." not in name:
                # Legacy source-only annotation spellings cannot supply typed
                # condition proof; recognize imports only to retain UNKNOWN.
                candidates = [package + name for package in (
                    "org.springframework.context.annotation.",
                    "org.springframework.boot.autoconfigure.condition.")
                    if package + name in imports or package + "*" in imports]
                if len(candidates) == 1:
                    name = candidates[0]
            canonical.append((name, args))
        return evaluate_conditions(canonical, context)

    def class_for(item: dict[str, Any]) -> dict[str, Any] | None:
        path = item.get("path")
        line = (item.get("range") or {}).get("start_line")
        candidates = [candidate for candidate in symbols.values()
                      if candidate.get("path") == path and candidate.get("kind") in {"class", "interface", "enum"}
                      and (candidate.get("range") or {}).get("start_line", 0) <= (line or 0)]
        return max(candidates, key=lambda candidate: (candidate.get("range") or {}).get("start_line", 0), default=None)

    # Resolve configuration reachability before creating beans. Component scan
    # is one source; @Import may deliberately reach configurations outside it.
    type_records: dict[str, dict[str, Any]] = {}
    for item in symbols.values():
        path = item.get("path")
        if (not isinstance(path, str) or path not in source_text or
                _simple(str(item.get("kind", ""))) not in {"class", "interface", "enum", "type", "annotation_type"}):
            continue
        imports = _imports(source_text[path])
        values = expanded_annotations(_annotation_map(item, source_text[path]), imports)
        direct_state, direct_reasons = condition_state(values, path, (item.get("range") or {}).get("start_line"))
        scan_state, scan_reasons = component_scan_state(item)
        configuration = any(_simple(name) == "Configuration" and
                            _allowed_annotation(name, imports, ("org.springframework.",)) for name, _ in values)
        type_records[str(item.get("owner"))] = {
            "symbol": item, "values": values, "imports": imports,
            "configuration": configuration, "direct_state": direct_state,
            "direct_reasons": direct_reasons, "scan_state": scan_state,
            "scan_reasons": scan_reasons,
        }

    configuration_states = {
        owner: _combined_state(record["direct_state"], record["scan_state"])
        for owner, record in type_records.items() if record["configuration"]
    }
    imported_states: dict[str, str] = {}
    imported_reasons: dict[str, list[str]] = {}
    rank = {"INACTIVE": 0, "UNKNOWN": 1, "ACTIVE": 2}
    dynamic_imports: set[str] = set()
    reported_missing: set[tuple[str, str]] = set()
    reported_dynamic: set[str] = set()
    selector_cache: dict[str, dict | None] = {}

    def processor(exact: str) -> dict | None:
        if exact not in selector_cache:
            selector_cache[exact] = selector_info(type_records[exact], type_records, symbols, context_id)
        return selector_cache[exact]

    def import_state(exact: str, state: str, reason: str) -> bool:
        if rank[state] <= rank.get(imported_states.get(exact, "INACTIVE"), 0):
            return False
        target = type_records[exact]
        imported_states[exact] = state
        imported_reasons[exact] = [reason, *target["direct_reasons"]]
        if target["configuration"]:
            configuration_states[exact] = state
        return True

    for _ in range(max(1, len(type_records))):
        changed = False
        for owner, record in type_records.items():
            if not record["configuration"] or configuration_states.get(owner) == "INACTIVE":
                continue
            for annotation_name, args in record["values"]:
                if (_simple(annotation_name) != "Import" or
                        not _allowed_annotation(annotation_name, record["imports"], ("org.springframework.",))):
                    continue
                for imported in _class_args(args):
                    simple = imported.rsplit(".", 1)[-1]
                    explicit = [value for value in record["imports"] if value.endswith("." + simple) and not value.endswith(".*")]
                    local = owner.rsplit(".", 1)[0] + "." + simple if "." in owner else simple
                    candidates = ([imported] if imported in type_records else []) + explicit + ([local] if local in type_records else [])
                    candidates = sorted({value for value in candidates if value in type_records})
                    exact = candidates[0] if len(candidates) == 1 else ""
                    if not exact:
                        missing_key = (owner, imported)
                        if missing_key not in reported_missing:
                            reported_missing.add(missing_key)
                            diagnostics.append({"code": "SPRING_IMPORT_UNRESOLVED", "path": record["symbol"].get("path"),
                                                "source_line": (record["symbol"].get("range") or {}).get("start_line"),
                                                "type": imported, "reason": "Imported type is absent from the indexed compiler context."})
                        continue
                    target = type_records[exact]
                    info = processor(exact)
                    importer = record["symbol"]
                    if info is None:
                        candidate_state = _combined_state(configuration_states[owner], target["direct_state"])
                        changed |= import_state(exact, candidate_state, f"imported by {owner}")
                        add_edge(importer["id"], target["symbol"]["id"], "imports_configuration", importer["path"],
                                 (importer.get("range") or {}).get("start_line"), "Compiler-resolved static @Import")
                        continue
                    dynamic_imports.add(exact)
                    info = {**info, "reasons": list(info["reasons"])}
                    selected = []
                    for name in info["targets"]:
                        if name not in type_records:
                            info["reasons"].append("TARGET_NOT_INDEXED:" + name)
                        elif processor(name) is not None:
                            info["reasons"].append("NESTED_SELECTOR_TARGET_UNSUPPORTED:" + name)
                        else:
                            selected.append(name)
                    if info["reasons"]:
                        info["status"] = "UNKNOWN"
                    declaration = target["symbol"]
                    selector_node = add_node("spring_import_selector", exact, declaration["path"],
                        (declaration.get("range") or {}).get("start_line"), symbol_node(declaration),
                        selector_type=exact, processor_kind=info["kind"], selection_status=info["status"],
                        phase="DEFERRED" if info["kind"] == "DEFERRED_IMPORT_SELECTOR" else "NORMAL",
                        targets=info["targets"], reasons=info["reasons"],
                        literal_method=(info["method"] or {}).get("id"), execution="NOT_EXECUTED")
                    add_edge(importer["id"], selector_node, "uses_import_selector", importer["path"],
                             (importer.get("range") or {}).get("start_line"), "Compiler-qualified @Import processor")
                    if info["status"] == "UNKNOWN" and exact not in reported_dynamic:
                        reported_dynamic.add(exact)
                        diagnostics.append({"code": "SPRING_DYNAMIC_IMPORT_BOUNDARY", "path": target["symbol"].get("path"),
                                            "source_line": (target["symbol"].get("range") or {}).get("start_line"),
                                            "type": exact, "reasons": info["reasons"],
                                            "reason": "Unsupported selector/registrar selection remains UNKNOWN; nothing was executed."})
                    for name in selected:
                        selected_record = type_records[name]
                        state = _combined_state(configuration_states[owner], selected_record["direct_state"],
                                                "ACTIVE" if info["status"] == "RESOLVED_LITERAL" else "UNKNOWN")
                        changed |= import_state(name, state, f"literal import candidate from {exact} used by {owner}")
                        method = info["method"]
                        add_edge(selector_node, selected_record["symbol"]["id"],
                                 "selects_import" if info["status"] == "RESOLVED_LITERAL" else "may_select_import",
                                 method["path"], (method.get("range") or {}).get("start_line"),
                                 f"Single compiler-attributed literal array return: {name}; selector never executed",
                                 compiler_fact=method)
        if not changed:
            break

    for item in symbols.values():
        path = item.get("path")
        if not isinstance(path, str) or path not in source_text:
            continue
        source = source_text[path]
        imports = _imports(source)
        values = _annotation_map(item, source)
        unresolved_jpa_values = [annotation for annotation in item.get("annotations", [])
                                 if isinstance(annotation, dict) and annotation.get("values_resolved") is False
                                 and _allowed_jpa_annotation(str(annotation.get("name", "")), imports)]
        for annotation in unresolved_jpa_values:
            diagnostics.append({"code": "ORM_ANNOTATION_VALUE_UNRESOLVED", "path": path,
                                "source_line": (item.get("range") or {}).get("start_line"),
                                "annotation": annotation.get("name"),
                                "reason": "K2 could not resolve all annotation argument values; source spelling is not treated as a constant."})
        effective_values = expanded_annotations(values, imports)
        simple_kind = _simple(str(item.get("kind", "")))
        is_type = simple_kind in {"class", "interface", "enum", "type", "annotation_type"}
        if is_type:
            class_by_name.setdefault(str(item.get("name", "")), []).append(item["id"])
        spring = [value for value in effective_values if is_type and _simple(value[0]) in SPRING_STEREOTYPES and
                  _allowed_annotation(value[0], imports, ("org.springframework.",))]
        if is_type and str(item.get("owner")) in imported_states and str(item.get("owner")) not in dynamic_imports and not spring:
            spring = [("org.springframework.context.annotation.Import", "")]
        jpa = [value for value in values if is_type and _simple(value[0]) in JPA_TYPES and
               _allowed_jpa_annotation(value[0], imports)]
        node = symbol_node(item)
        if node is None:
            continue
        path_line = (item.get("range") or {}).get("start_line")
        if spring:
            bean_name = _string_arg(spring[0][1], ("value", "name")) or node.name
            qualifiers, primary, profiles = bean_selection(effective_values)
            condition, condition_reasons = condition_state(effective_values, path, path_line)
            scan_state, scan_reasons = component_scan_state(item)
            if str(item.get("owner")) in imported_states:
                condition = imported_states[str(item.get("owner"))]
                condition_reasons += imported_reasons[str(item.get("owner"))]
            else:
                condition = _combined_state(condition, scan_state)
                condition_reasons += scan_reasons
            types = [node.name] + [_simple(str(supertype)) for supertype in item.get("supertypes", [])]
            bean_id = add_node("spring_bean", bean_name, path, path_line, node,
                               stereotype=_simple(spring[0][0]), qualifier=bean_name,
                               qualifiers=qualifiers, primary=primary, profiles=profiles, types=types,
                               condition_status=condition, condition_reasons=condition_reasons,
                               stereotype_chain=[name for name, _ in effective_values])
            add_edge(node.id, bean_id, "defines_bean", path, path_line, "Spring stereotype with resolved FQ import")
            spring_beans.append({"node": node, "bean": bean_id, "type": node.name, "types": types,
                                 "name": bean_name, "qualifiers": qualifiers, "primary": primary,
                                 "profiles": profiles, "condition_status": condition,
                                 "condition_reasons": condition_reasons,
                                 "annotations": effective_values, "path": path, "line": path_line})
            if condition == "UNKNOWN":
                diagnostics.append({"code": "SPRING_CONDITION_UNRESOLVED", "path": path, "source_line": path_line,
                                    "bean": bean_id, "reasons": condition_reasons})
        if jpa:
            declaration = {"node": node, "symbol": item, "annotations": values, "path": path, "line": path_line,
                           "source": source, "imports": imports}
            kinds = {_simple(name) for name, _ in jpa}
            if "Entity" in kinds:
                entity_decls.append(declaration)
            if "Embeddable" in kinds:
                embeddable_decls.append(declaration)
            if "MappedSuperclass" in kinds:
                mapped_superclass_decls.append(declaration)

    # @Bean methods only define beans when their containing configuration is
    # reachable. Method conditions refine the class/import condition.
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
                owner = str(item.get("owner", ""))
                configuration = type_records.get(owner)
                if not configuration or not configuration["configuration"]:
                    diagnostics.append({"code": "SPRING_BEAN_OUTSIDE_CONFIGURATION", "path": path,
                                        "source_line": line, "method": item.get("id"),
                                        "reason": "@Bean method is not enclosed by an indexed @Configuration type."})
                    continue
                name = _string_arg(bean_annotation[1], ("name", "value")) or node.name
                qualifiers, primary, profiles = bean_selection(values)
                condition, condition_reasons = condition_state(values, path, line)
                parent_state = configuration_states.get(owner, "INACTIVE")
                condition = _combined_state(parent_state, condition)
                condition_reasons = [f"containing configuration {owner} is {parent_state}", *condition_reasons]
                descriptor = str(item.get("descriptor", ""))
                descriptor_return = re.search(r"\)L([^;]+);$", descriptor)
                return_type = str(item.get("return_type") or
                                  (descriptor_return.group(1).replace("/", ".") if descriptor_return else node.name))
                return_type = return_type.split("<", 1)[0].rsplit(".", 1)[-1]
                types = [return_type]
                bean_id = add_node("spring_bean", name, path, line, node, stereotype="Bean", qualifier=name,
                                   qualifiers=qualifiers, primary=primary, profiles=profiles, types=types,
                                   condition_status=condition, condition_reasons=condition_reasons)
                add_edge(node.id, bean_id, "defines_bean", path, line, "@Bean method")
                spring_beans.append({"node": node, "bean": bean_id, "type": return_type, "types": types,
                                     "name": name, "qualifiers": qualifiers, "primary": primary,
                                     "profiles": profiles, "condition_status": condition,
                                     "condition_reasons": condition_reasons,
                                     "annotations": values, "path": path, "line": line})
                if condition == "UNKNOWN":
                    diagnostics.append({"code": "SPRING_CONDITION_UNRESOLVED", "path": path, "source_line": line,
                                        "bean": bean_id, "reasons": condition_reasons})

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
    def resolve_query_property(model_name: str, property_name: str) -> tuple[str | None, str | None]:
        normalized = property_name.replace("_", "").casefold()
        direct = entity_attributes.get(model_name, {}).get(normalized)
        if direct:
            return direct, property_name
        for outer, outer_id in entity_attributes.get(model_name, {}).items():
            if not normalized.startswith(outer) or len(normalized) == len(outer):
                continue
            embedded_type = entity_embedded_types.get((model_name, outer))
            suffix = normalized[len(outer):]
            nested = next((identity for (owner, name), identity in embeddable_attributes.items()
                           if owner == embedded_type and name.casefold() == suffix), None)
            if nested:
                return nested, f"{outer}.{suffix}"
            associated_type = entity_association_types.get((model_name, outer))
            associated = entity_attributes.get(associated_type or "", {}).get(suffix)
            if associated:
                return associated, f"{outer}.{suffix}"
        return None, None

    repository_models: dict[str, str] = {}
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
            declared_type = re.sub(r"\s+", "", match.group("type"))
            outer = declared_type.split("<", 1)[0].rsplit(".", 1)[-1]
            generic = declared_type.split("<", 1)[1].rsplit(">", 1)[0] if "<" in declared_type else ""
            arguments = [item.strip().rsplit(".", 1)[-1] for item in generic.split(",") if item.strip()]
            if outer in {"List", "Set", "Collection", "Iterable"} and arguments:
                injection_kind, type_name = "collection", arguments[0]
            elif outer == "Map" and len(arguments) == 2 and arguments[0] in {"String", "java.lang.String"}:
                injection_kind, type_name = "map", arguments[1]
            elif outer in {"ObjectProvider", "Provider"} and arguments:
                injection_kind, type_name = "provider", arguments[0]
            elif outer == "Optional" and arguments:
                injection_kind, type_name = "optional", arguments[0]
            else:
                injection_kind, type_name = "single", outer
            qualifiers = [(item.group(1), _args(item.group(0))) for item in
                          re.finditer(r"@([A-Za-z_][\w.]*)\s*(\([^\n]*\))?", match.group("ann") or "")]
            qualifier = next((_string_arg(args, ("value", "name")) for name, args in qualifiers if _simple(name) == "Qualifier"), None)
            candidates = [bean for bean in spring_beans if type_name in bean.get("types", [bean["type"]])]
            candidates = [bean for bean in candidates if bean.get("condition_status", "ACTIVE") != "INACTIVE"]
            if qualifier:
                candidates = [bean for bean in candidates if qualifier in {bean["name"], *bean.get("qualifiers", [])}]
            # Profile expressions were already evaluated in condition_status;
            # a second literal-name filter would discard proven !dev/OR matches.
            if len(candidates) > 1 and injection_kind in {"single", "optional"}:
                primaries = [bean for bean in candidates if bean.get("primary")]
                if len(primaries) == 1:
                    candidates = primaries
                else:
                    diagnostics.append({"code": "SPRING_AMBIGUOUS_BEAN", "path": path, "source_line": line,
                                        "type": type_name, "candidates": [bean["bean"] for bean in candidates],
                                        "reason": "Multiple type-compatible beans; no unique Qualifier/Primary evidence."})
            injection = add_node("spring_injection", f"{owner.name}.{match.group('name')}", path, line, owner,
                                 type=type_name, declared_type=declared_type,
                                 injection_kind=injection_kind, qualifier=qualifier)
            if not candidates and injection_kind not in {"optional", "provider"}:
                diagnostics.append({"code": "SPRING_UNRESOLVED_INJECTION", "path": path, "source_line": line,
                                    "type": type_name, "reason": "No type-compatible bean declaration in indexed source scope."})
            for bean in candidates:
                resolved = (bean.get("condition_status", "ACTIVE") == "ACTIVE" and
                            (injection_kind in {"collection", "map"} or
                             injection_kind in {"single", "optional"} and len(candidates) == 1))
                add_edge(injection, bean["bean"], "injects_bean" if resolved else "may_inject_bean", path, line,
                         ("Active collection/map member" if resolved and injection_kind in {"collection", "map"}
                          else "Unique active bean selected" if resolved
                          else "Lazy provider or type-compatible bean with unresolved condition or ambiguity"))

    # ORM entities, persistent attributes and repository/query declarations.
    schema_tables = [node for node in nodes.values() if node.kind == "db_table"]
    schema_columns = [node for node in nodes.values() if node.kind == "db_column"]
    realm_prefix = None
    if context.get("database_id") and context.get("schema_stream_id"):
        realm_prefix = f"schema:{context['database_id']}:{context['schema_stream_id']}:"

    def in_schema_realm(candidate: Node) -> bool:
        return realm_prefix is None or candidate.id.startswith(realm_prefix)

    embeddable_nodes: dict[str, str] = {}
    embeddable_attributes: dict[tuple[str, str], str] = {}
    embeddable_mapping_access: dict[str, str] = {}
    for declaration in embeddable_decls:
        source_node: Node = declaration["node"]
        embedded_id = add_node("orm_embeddable", source_node.name, declaration["path"], declaration["line"], source_node,
                               java_type=str(declaration["symbol"].get("owner", source_node.name)))
        embeddable_nodes[source_node.name] = embedded_id
        add_edge(source_node.id, embedded_id, "declares_embeddable", declaration["path"], declaration["line"],
                 "Compiler-resolved JPA @Embeddable declaration")
        members = [item for item in symbols.values()
                   if item.get("owner") == declaration["symbol"].get("owner") and item.get("kind") == "field"]
        embedded_access_annotation = _annotation(declaration["annotations"], "Access")
        embedded_access_value = (_string_arg(embedded_access_annotation[1], ("value",)) or "").rsplit(".", 1)[-1] \
            if embedded_access_annotation and embedded_access_annotation[1] != "__UNRESOLVED__" else ""
        embedded_access_unknown = bool(embedded_access_annotation and embedded_access_annotation[1] == "__UNRESOLVED__")
        embeddable_mapping_access[source_node.name] = (
            embedded_access_value if embedded_access_value in {"FIELD", "PROPERTY"}
            else "UNKNOWN" if embedded_access_unknown else "INHERIT")
        for field in members:
            source_annotations = field.get("annotations", [])
            annotations_for_field = [(name, args) for name, args in _annotation_map(field, declaration["source"])
                                     if _allowed_jpa_annotation(name, declaration["imports"])]
            getter_column_without_access = False
            if declaration["path"].endswith(".kt"):
                allowed_targets = ({"PROPERTY_GETTER", "GETTER", "GET"} if embedded_access_value == "PROPERTY"
                                   else {"FIELD", "BACKING_FIELD"})
                getter_column_without_access = (
                    not embedded_access_value and not embedded_access_unknown
                    and any(isinstance(item, dict) and _simple(str(item.get("name", ""))) == "Column"
                            and str(item.get("use_site_target", "")).upper() in {"PROPERTY_GETTER", "GETTER", "GET"}
                            for item in source_annotations))
                if embedded_access_unknown:
                    annotations_for_field = []
                else:
                    selected_items = [item for item in source_annotations if isinstance(item, dict)
                                      and str(item.get("use_site_target", "")).upper() in allowed_targets]
                    selected_symbol = {**field, "annotations": selected_items}
                    annotations_for_field = [(name, args) for name, args in _annotation_map(selected_symbol, declaration["source"])
                                             if _allowed_jpa_annotation(name, declaration["imports"])]
            if any(_simple(name) == "Transient" for name, _ in annotations_for_field):
                continue
            field_name = str(field.get("name"))
            column_annotation = next((args for name, args in annotations_for_field if _simple(name) == "Column"), "")
            column_name = (None if column_annotation == "__UNRESOLVED__" or embedded_access_unknown else
                           _string_arg(column_annotation, ("name", "value")) if column_annotation else field_name)
            field_line = (field.get("range") or {}).get("start_line")
            if column_annotation == "__UNRESOLVED__":
                diagnostics.append({"code": "ORM_COLUMN_MAPPING_UNKNOWN", "path": declaration["path"],
                                    "source_line": field_line, "attribute": field_name,
                                    "reason": "Explicit @Column values are unresolved; no default embeddable column is published."})
            elif getter_column_without_access or embedded_access_unknown:
                diagnostics.append({"code": "ORM_EMBEDDABLE_ACCESS_UNKNOWN", "path": declaration["path"],
                                    "source_line": field_line, "attribute": field_name,
                                    "reason": "Embeddable property mapping depends on inherited or unresolved @Access; physical column is not inferred."})
            attribute_id = add_node("orm_embeddable_attribute", f"{source_node.name}.{field_name}", declaration["path"],
                                    field_line, source_node, attribute=field_name,
                                    type=str(field.get("type") or field.get("descriptor") or "UNKNOWN"), default_column=column_name,
                                    mapping_status="UNKNOWN" if column_name is None or getter_column_without_access else "PARTIAL",
                                    _access_inheritance_unresolved=(column_name if getter_column_without_access else None))
            embeddable_attributes[(source_node.name, field_name)] = attribute_id
            add_edge(embedded_id, attribute_id, "contains_attribute", declaration["path"], field_line,
                     "Persistent attribute declared by @Embeddable")

    mapped_superclass_nodes: dict[str, str] = {}
    for declaration in mapped_superclass_decls:
        source_node: Node = declaration["node"]
        mapped_id = add_node("orm_mapped_superclass", source_node.name, declaration["path"], declaration["line"], source_node,
                             java_type=str(declaration["symbol"].get("owner", source_node.name)))
        mapped_superclass_nodes[source_node.name] = mapped_id
        add_edge(source_node.id, mapped_id, "declares_mapped_superclass", declaration["path"], declaration["line"],
                 "Compiler-resolved JPA @MappedSuperclass declaration")

    entity_nodes = {declaration["node"].name: declaration["node"].id for declaration in entity_decls}
    entity_table_nodes: dict[str, str] = {}
    entity_attributes: dict[str, dict[str, str]] = {name: {} for name in entity_nodes}
    entity_embedded_types: dict[tuple[str, str], str] = {}
    embeddable_inherited_accesses: dict[str, set[str]] = {}
    entity_association_types: dict[tuple[str, str], str] = {}
    named_queries: dict[str, dict[str, Any]] = {}
    association_records: list[dict[str, Any]] = []
    for entity in entity_decls:
        node: Node = entity["node"]
        values = entity["annotations"]
        table_annotation = _annotation(values, "Table")
        table_values_unknown = bool(table_annotation and table_annotation[1] == "__UNRESOLVED__")
        table_name = _string_arg(table_annotation[1], ("name", "value")) if table_annotation and not table_values_unknown else None
        table_schema = _named_string_arg(table_annotation[1], "schema") if table_annotation else None
        inferred = table_name is None
        inferred = inferred and not table_values_unknown
        table_name = table_name or (None if table_values_unknown else node.name)
        qualified_table = f"{table_schema}.{table_name}" if table_schema else table_name
        table_id = None
        if table_name is not None:
            table_id = add_node("orm_table", qualified_table, entity["path"], entity["line"], node,
                                logical_name=table_name, schema=table_schema, inferred=inferred,
                                database_id=context.get("database_id"),
                                schema_stream_id=context.get("schema_stream_id"),
                                persistence_unit=context.get("persistence_unit"),
                                naming_strategy=context.get("naming_strategy"))
            entity_table_nodes[node.name] = table_id
            add_edge(node.id, table_id, "maps_to_table", entity["path"], entity["line"],
                     "@Table name" if not inferred else "Entity name fallback; physical naming strategy not verified")
        if table_values_unknown:
            diagnostics.append({"code": "ORM_ANNOTATION_VALUE_UNRESOLVED", "path": entity["path"],
                                "source_line": entity["line"], "annotation": "Table",
                                "reason": "Explicit @Table values are unresolved; no physical table fallback is published."})
        for annotation_name, annotation_args in values:
            named_kind = _simple(annotation_name)
            if named_kind not in {"NamedQuery", "NamedNativeQuery"} or not _allowed_jpa_annotation(
                    annotation_name, entity["imports"]):
                continue
            query_name = _named_string_arg(annotation_args, "name")
            query_text = _named_string_arg(annotation_args, "query")
            if not query_name or not query_text:
                diagnostics.append({"code": "ORM_NAMED_QUERY_UNRESOLVED", "path": entity["path"],
                                    "source_line": entity["line"], "entity": node.id,
                                    "reason": "Named query name or static query text is unavailable."})
                continue
            language = "NATIVE_SQL" if named_kind == "NamedNativeQuery" else "JPQL"
            named_id = add_node("orm_named_query", query_name, entity["path"], entity["line"], node,
                                query_language=language, query=query_text, entity=node.name, dynamic=False)
            add_edge(node.id, named_id, "defines_named_query", entity["path"], entity["line"],
                     f"Static JPA @{named_kind}")
            action = "query_deletes" if query_text.lstrip().casefold().startswith("delete") else (
                "query_writes" if query_text.lstrip().casefold().startswith(("update", "insert")) else "query_reads")
            if language == "JPQL" or table_id:
                add_edge(named_id, node.id if language == "JPQL" else table_id, action, entity["path"], entity["line"],
                         "Named query owner entity/table; static intent only")
            named_queries[query_name] = {"id": named_id, "language": language, "entity": node.name}
        for supertype in entity["symbol"].get("supertypes", []):
            mapped = mapped_superclass_nodes.get(_simple(str(supertype)))
            if mapped:
                add_edge(node.id, mapped, "inherits_mapping", entity["path"], entity["line"],
                         "Compiler-resolved @MappedSuperclass inheritance")
        matches = [candidate for candidate in schema_tables if table_id and in_schema_realm(candidate)
                   and (candidate.name.casefold() == qualified_table.casefold()
                        if table_schema else candidate.name.casefold().rsplit(".", 1)[-1] == table_name.casefold())]
        if table_values_unknown:
            diagnostics.append({"code": "ORM_TABLE_MAPPING_UNKNOWN", "path": entity["path"],
                                "source_line": entity["line"], "entity": node.id,
                                "reason": "An explicit @Table value is unresolved; physical table mapping remains unknown."})
        elif inferred:
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
        access_annotation = _annotation(values, "Access")
        access_values_unknown = bool(access_annotation and access_annotation[1] == "__UNRESOLVED__")
        explicit_access = (_string_arg(access_annotation[1], ("value",)) or "").rsplit(".", 1)[-1] if access_annotation and not access_values_unknown else ""
        property_id = bool(re.search(r"@(?:[\w.]*\.)?(?:Id|EmbeddedId)\b[^;{}]*\b(?:get|is)[A-Z]\w*\s*\(\s*\)", body, re.S))
        field_id = any(re.search(r"@(?:[\w.]*\.)?(?:Id|EmbeddedId)\b", candidate.group("annotations"))
                       for candidate in re.finditer(
                           r"(?P<annotations>(?:@[\w.]+(?:\([^\n]*\))?\s*)*)(?P<type>[A-Za-z_][\w.<>, ?\[\]]*)\s+"
                           r"(?P<name>[A-Za-z_]\w*)\s*(?:[;=]|$)", body, re.M))
        kotlin = entity["path"].endswith(".kt")
        kotlin_properties = [candidate for candidate in symbols.values()
                             if kotlin and candidate.get("owner") == entity["symbol"].get("owner")
                             and candidate.get("kind") == "field" and candidate.get("path") == entity["path"]]
        def property_site_annotations(candidate: dict[str, Any]) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
            field_values, getter_values = [], []
            for annotation in candidate.get("annotations", []):
                if not isinstance(annotation, dict) or not isinstance(annotation.get("name"), str):
                    continue
                if not _allowed_jpa_annotation(annotation["name"], entity["imports"]):
                    continue
                site = str(annotation.get("use_site_target", "")).upper()
                unresolved = annotation.get("values_resolved") is False
                raw = annotation.get("values", {})
                args = ("__UNRESOLVED__" if unresolved else
                        ",".join(f"{key}={_format_annotation_value(value)}" for key, value in raw.items())
                        if isinstance(raw, dict) else "")
                pair = (annotation["name"], args)
                if site in {"FIELD", "BACKING_FIELD"}:
                    field_values.append(pair)
                elif site in {"PROPERTY_GETTER", "GETTER", "GET"}:
                    getter_values.append(pair)
            return field_values, getter_values
        if kotlin:
            placed = [(candidate, *property_site_annotations(candidate)) for candidate in kotlin_properties]
            has_field_id = any(_simple(name) in {"Id", "EmbeddedId"} for _, annotations, _ in placed for name, _ in annotations)
            has_getter_id = any(_simple(name) in {"Id", "EmbeddedId"} for _, _, annotations in placed for name, _ in annotations)
            if (explicit_access == "FIELD" and has_getter_id and not has_field_id) or (
                    explicit_access == "PROPERTY" and has_field_id and not has_getter_id):
                diagnostics.append({"code": "ORM_KOTLIN_ACCESS_TARGET_MISMATCH", "path": entity["path"],
                                    "source_line": entity["line"], "entity": node.id,
                                    "reason": f"Explicit {explicit_access} access conflicts with the compiler-reported Kotlin JPA identifier use-site target."})
            entity_access = ("UNKNOWN" if access_values_unknown else
                             explicit_access if explicit_access in {"FIELD", "PROPERTY"} else
                             "FIELD" if has_field_id and not has_getter_id else "PROPERTY" if has_getter_id and not has_field_id else "UNKNOWN")
            if access_values_unknown:
                diagnostics.append({"code": "ORM_ACCESS_STRATEGY_UNKNOWN", "path": entity["path"],
                                    "source_line": entity["line"], "entity": node.id,
                                    "reason": "Explicit @Access value is unresolved; identifier placement cannot override it."})
            if entity_access == "UNKNOWN":
                diagnostics.append({"code": "ORM_KOTLIN_ACCESS_AMBIGUOUS", "path": entity["path"],
                                    "source_line": entity["line"], "entity": node.id,
                                    "reason": "Kotlin JPA identifier has no unique @field:/@get: target or explicit @Access; persistence access is not inferred."})
        else:
            entity_access = explicit_access if explicit_access in {"FIELD", "PROPERTY"} else "PROPERTY" if property_id and not field_id else "FIELD"
        table_node = nodes.get(table_id)
        if table_node is not None:
            nodes[table_id] = replace(table_node, metadata={**(table_node.metadata or {}), "access_strategy": entity_access})
        if kotlin:
            field_records = []
            for candidate, field_annotations, getter_annotations in placed:
                selected_annotations = field_annotations if entity_access == "FIELD" else getter_annotations
                if entity_access == "UNKNOWN" or not any(_simple(name) in JPA_FIELDS for name, _ in selected_annotations):
                    continue
                field_records.append({"name": candidate.get("name"), "type": candidate.get("type", ""),
                                      "annotations": selected_annotations,
                                      "line": (candidate.get("range") or {}).get("start_line") or entity["line"]})
        else:
            field_records = [{"name": match.group("name"), "type": match.group("type").strip(),
                              "annotations": [(name, args) for name, args in re.findall(r"@([\w.]+)\s*(\([^\n]*\))?", match.group("annotations"))],
                              "line": start + body[:match.start()].count("\n")}
                             for match in re.finditer(r"(?P<annotations>(?:@[\w.]+(?:\([^\n]*\))?\s*)*)(?P<type>[A-Za-z_][\w.<>, ?\[\]]*)\s+(?P<name>[A-Za-z_]\w*)\s*(?:[;=]|$)", body, re.M)]
        for field_match in field_records:
            if entity_access != "FIELD":
                continue
            field_annotations = field_match["annotations"]
            if not field_annotations or not any(_simple(name) in JPA_FIELDS for name, _ in field_annotations):
                continue
            if any(_simple(name) == "Transient" for name, _ in field_annotations):
                continue
            field_line = field_match["line"]
            field_name = field_match["name"]
            field_type = field_match["type"].strip()
            embedded_id_annotation = next((args for name, args in field_annotations if _simple(name) == "EmbeddedId"), None)
            embedded = embedded_id_annotation is not None or any(_simple(name) == "Embedded" for name, _ in field_annotations)
            identifier = embedded_id_annotation is not None or any(_simple(name) == "Id" for name, _ in field_annotations)
            attribute = add_node("orm_attribute", f"{node.name}.{field_name}", entity["path"], field_line, node,
                                 attribute=field_name, type=field_type, access="FIELD",
                                 identifier=identifier, embedded=embedded)
            entity_attributes[node.name][field_name.casefold()] = attribute
            if table_id:
                add_edge(attribute, table_id, "declared_on_table", entity["path"], field_line, "JPA persistent attribute")
            if identifier:
                add_edge(node.id, attribute, "has_embedded_id" if embedded_id_annotation is not None else "has_id",
                         entity["path"], field_line, "JPA identifier placement determines FIELD access")
            if embedded:
                embedded_type = re.findall(r"[A-Za-z_]\w*", field_type)[-1]
                entity_embedded_types[(node.name, field_name.casefold())] = embedded_type
                embeddable_inherited_accesses.setdefault(embedded_type, set()).add(entity_access)
                target = embeddable_nodes.get(embedded_type)
                if target:
                    add_edge(attribute, target, "embeds_type", entity["path"], field_line,
                             "@Embedded/@EmbeddedId targets compiler-resolved @Embeddable")
                else:
                    diagnostics.append({"code": "ORM_EMBEDDABLE_TYPE_UNRESOLVED", "path": entity["path"],
                                        "source_line": field_line, "attribute": attribute, "type": embedded_type})
                override = next((args for name, args in field_annotations if _simple(name) == "AttributeOverride"), "")
                if override == "__UNRESOLVED__":
                    diagnostics.append({"code": "ORM_ATTRIBUTE_OVERRIDE_UNKNOWN", "path": entity["path"],
                                        "source_line": field_line, "attribute": attribute,
                                        "reason": "Explicit @AttributeOverride values are unresolved; physical override bindings are omitted."})
                    nodes[attribute] = replace(nodes[attribute], metadata={**(nodes[attribute].metadata or {}),
                                                                           "mapping_status": "UNKNOWN"})
                    continue
                if override:
                    overridden = _named_string_arg(override, "name")
                    column_match = re.search(r"@(?:[\w.]*\.)?Column\s*\([^)]*\bname\s*=\s*[\"']([^\"']+)", override)
                    override_column = column_match.group(1) if column_match else None
                    override_id = add_node("orm_attribute_override", f"{node.name}.{field_name}.{overridden or '?'}",
                                           entity["path"], field_line, node, attribute=overridden,
                                           column=override_column, embedded_attribute=field_name)
                    add_edge(attribute, override_id, "overrides_embedded_attribute", entity["path"], field_line,
                             "Explicit @AttributeOverride on embedded value")
                    overridden_id = embeddable_attributes.get((embedded_type, overridden or ""))
                    if overridden_id:
                        add_edge(override_id, overridden_id, "overrides_attribute", entity["path"], field_line,
                                 "AttributeOverride name resolves within compiler-resolved embeddable")
                    else:
                        diagnostics.append({"code": "ORM_ATTRIBUTE_OVERRIDE_TARGET_UNRESOLVED", "path": entity["path"],
                                            "source_line": field_line, "attribute": overridden,
                                            "embeddable_type": embedded_type})
                    if override_column:
                        override_column_id = add_node("orm_column", override_column, entity["path"], field_line, node,
                                                      logical_name=override_column, inferred=False, override=True)
                        add_edge(override_id, override_column_id, "maps_to_column", entity["path"], field_line,
                                 "Nested @Column name from @AttributeOverride")
            relation_names = {"ManyToOne", "OneToMany", "OneToOne", "ManyToMany"}
            relation_entry = next(((name, args) for name, args in field_annotations if _simple(name) in relation_names), None)
            relation = relation_entry[0] if relation_entry else None
            if relation:
                mapped_by = _named_string_arg(relation_entry[1], "mappedBy")
                target_type = re.findall(r"[A-Za-z_]\w*", field_type)[-1]
                entity_association_types[(node.name, field_name.casefold())] = target_type
                association = add_node("orm_association", f"{node.name}.{field_name}", entity["path"], field_line, node,
                                       association=_simple(relation), target_type=target_type,
                                       mapped_by=mapped_by, association_role="INVERSE" if mapped_by else "OWNING")
                add_edge(attribute, association, "declares_association", entity["path"], field_line,
                         f"JPA relationship @{_simple(relation)}")
                association_records.append({"id": association, "owner": node.name, "field": field_name,
                                            "target": target_type, "mapped_by": mapped_by,
                                            "path": entity["path"], "line": field_line})
                join_entry = next(((name, args) for name, args in field_annotations if _simple(name) in {"JoinColumn", "JoinTable"}), None)
                join_name = _string_arg(join_entry[1], ("name", "value")) if join_entry else None
                if join_name:
                    join_kind = "orm_join_table" if _simple(join_entry[0]) == "JoinTable" else "orm_column"
                    join_node = add_node(join_kind, join_name, entity["path"], field_line, node,
                                         logical_name=join_name, inferred=False, join=True)
                    add_edge(association, join_node,
                             "maps_to_join_table" if join_kind == "orm_join_table" else "maps_to_join_column",
                             entity["path"], field_line, "Explicit JPA join column/table name")
            column_annotation = next((args for name, args in field_annotations if _simple(name) == "Column"), "")
            if relation or embedded:
                continue
            if column_annotation == "__UNRESOLVED__":
                diagnostics.append({"code": "ORM_COLUMN_MAPPING_UNKNOWN", "path": entity["path"],
                                    "source_line": field_line, "attribute": attribute,
                                    "reason": "Explicit @Column values are unresolved; no default physical column is published."})
                nodes[attribute] = replace(nodes[attribute], metadata={**(nodes[attribute].metadata or {}),
                                                                       "mapping_status": "UNKNOWN"})
                continue
            column_name = _string_arg(column_annotation, ("name", "value")) if column_annotation else field_name
            column_id = add_node("orm_column", column_name, entity["path"], field_line, node,
                                 logical_name=column_name, inferred=not bool(column_annotation))
            add_edge(attribute, column_id, "maps_to_column", entity["path"], field_line,
                     "@Column name" if column_annotation else "Persistent attribute name; converter/naming strategy not verified")
            column_matches = [candidate for candidate in schema_columns if table_name and in_schema_realm(candidate)
                              and candidate.name.casefold().rsplit(".", 1)[-1] == column_name.casefold()
                              and len(candidate.name.split(".")) >= 2
                              and candidate.name.split(".")[-2].casefold() == table_name.casefold()]
            if not inferred and len(column_matches) == 1:
                add_edge(column_id, column_matches[0].id, "resolves_to_schema_column", entity["path"], field_line, "Exact schema column name in selected table/realm")
            elif not inferred and len(column_matches) > 1:
                diagnostics.append({"code": "ORM_SCHEMA_COLUMN_AMBIGUOUS", "path": entity["path"],
                                    "source_line": field_line, "attribute": attribute,
                                    "column": column_name, "candidates": [item.id for item in column_matches]})

        if entity_access == "PROPERTY":
            if kotlin:
                getter_records = [{"name": candidate.get("name"), "type": candidate.get("type", ""),
                                   "annotations": getter_annotations,
                                   "line": (candidate.get("range") or {}).get("start_line") or entity["line"]}
                                  for candidate, _, getter_annotations in placed]
            else:
                getter_pattern = re.compile(
                    r"(?P<annotations>(?:@[\w.]+(?:\([^\n]*\))?\s*)+)"
                    r"(?:(?:public|protected|private|final|open|abstract)\s+)*"
                    r"(?P<type>[A-Za-z_][\w.<>, ?\[\]]*)\s+(?P<getter>get[A-Z]\w*|is[A-Z]\w*)\s*\(\s*\)", re.M)
                getter_records = []
                for getter in getter_pattern.finditer(body):
                    getter_name = getter.group("getter")
                    prefix = "is" if getter_name.startswith("is") else "get"
                    property_name = getter_name[len(prefix):]
                    property_name = property_name[:1].lower() + property_name[1:]
                    getter_records.append({"name": property_name, "type": getter.group("type"),
                                           "annotations": [(name, args) for name, args in re.findall(r"@([\w.]+)\s*(\([^\n]*\))?", getter.group("annotations"))],
                                           "line": start + body[:getter.start()].count("\n"), "getter": getter_name})
            for getter in getter_records:
                property_annotations = getter["annotations"]
                if any(_simple(name) == "Transient" for name, _ in property_annotations):
                    continue
                if not any(_simple(name) in JPA_FIELDS for name, _ in property_annotations):
                    continue
                getter_name = getter.get("getter") or "get" + str(getter["name"][:1]).upper() + str(getter["name"])[1:]
                property_name = getter["name"]
                property_type = getter["type"].strip()
                property_line = getter["line"]
                embedded_id = any(_simple(name) == "EmbeddedId" for name, _ in property_annotations)
                embedded = embedded_id or any(_simple(name) == "Embedded" for name, _ in property_annotations)
                identifier = embedded_id or any(_simple(name) == "Id" for name, _ in property_annotations)
                attribute = add_node("orm_attribute", f"{node.name}.{property_name}", entity["path"], property_line, node,
                                     attribute=property_name, type=property_type, access="PROPERTY",
                                     identifier=identifier, embedded=embedded, getter=getter_name)
                entity_attributes[node.name][property_name.casefold()] = attribute
                if table_id:
                    add_edge(attribute, table_id, "declared_on_table", entity["path"], property_line,
                             "JPA property-access persistent attribute")
                if identifier:
                    add_edge(node.id, attribute, "has_embedded_id" if embedded_id else "has_id",
                             entity["path"], property_line, "JPA identifier placement determines PROPERTY access")
                if embedded:
                    embedded_type = re.findall(r"[A-Za-z_]\w*", property_type)[-1]
                    entity_embedded_types[(node.name, property_name.casefold())] = embedded_type
                    embeddable_inherited_accesses.setdefault(embedded_type, set()).add(entity_access)
                    if embedded_type in embeddable_nodes:
                        add_edge(attribute, embeddable_nodes[embedded_type], "embeds_type", entity["path"], property_line,
                                 "Property-access embedded value")
                    continue
                relation_entry = next(((name, args) for name, args in property_annotations
                                       if _simple(name) in {"ManyToOne", "OneToMany", "OneToOne", "ManyToMany"}), None)
                if relation_entry:
                    mapped_by = _named_string_arg(relation_entry[1], "mappedBy")
                    target_type = re.findall(r"[A-Za-z_]\w*", property_type)[-1]
                    entity_association_types[(node.name, property_name.casefold())] = target_type
                    association = add_node("orm_association", f"{node.name}.{property_name}", entity["path"], property_line, node,
                                           association=_simple(relation_entry[0]), target_type=target_type,
                                           mapped_by=mapped_by, association_role="INVERSE" if mapped_by else "OWNING",
                                           access="PROPERTY")
                    add_edge(attribute, association, "declares_association", entity["path"], property_line,
                             f"JPA property relationship @{_simple(relation_entry[0])}")
                    association_records.append({"id": association, "owner": node.name, "field": property_name,
                                                "target": target_type, "mapped_by": mapped_by,
                                                "path": entity["path"], "line": property_line})
                    continue
                column_annotation = next((args for name, args in property_annotations if _simple(name) == "Column"), "")
                if column_annotation == "__UNRESOLVED__":
                    diagnostics.append({"code": "ORM_COLUMN_MAPPING_UNKNOWN", "path": entity["path"],
                                        "source_line": property_line, "attribute": attribute,
                                        "reason": "Explicit @Column values are unresolved; no default physical column is published."})
                    nodes[attribute] = replace(nodes[attribute], metadata={**(nodes[attribute].metadata or {}),
                                                                           "mapping_status": "UNKNOWN"})
                    continue
                column_name = _string_arg(column_annotation, ("name", "value")) if column_annotation else property_name
                column_id = add_node("orm_column", column_name, entity["path"], property_line, node,
                                     logical_name=column_name, inferred=not bool(column_annotation))
                add_edge(attribute, column_id, "maps_to_column", entity["path"], property_line,
                         "Property @Column name" if column_annotation else "Property name; naming strategy not verified")

    for declaration in embeddable_decls:
        name = declaration["node"].name
        if embeddable_mapping_access.get(name) != "INHERIT":
            continue
        inherited = embeddable_inherited_accesses.get(name, set())
        for (embeddable_name, attribute_name), attribute_id in embeddable_attributes.items():
            if embeddable_name != name:
                continue
            current = nodes[attribute_id]
            metadata = dict(current.metadata or {})
            getter_candidate = metadata.pop("_access_inheritance_unresolved", None)
            if inherited == {"FIELD"}:
                if getter_candidate is not None:
                    metadata["mapping_status"] = "PARTIAL"
                    metadata["default_column"] = getter_candidate
                    nodes[attribute_id] = replace(current, metadata=metadata)
                elif metadata.get("mapping_status") != "UNKNOWN":
                    nodes[attribute_id] = replace(current, metadata=metadata)
                continue
            metadata["default_column"] = None
            metadata["mapping_status"] = "UNKNOWN"
            nodes[attribute_id] = replace(current, metadata=metadata)
            diagnostics.append({"code": "ORM_EMBEDDABLE_ACCESS_UNKNOWN", "path": declaration["path"],
                                "source_line": declaration["line"], "attribute": attribute_id,
                                "reason": "Embeddable access is inherited from a container with non-FIELD or unknown access; physical column mapping is not projected."})

    for association in association_records:
        target = entity_nodes.get(association["target"])
        if target:
            add_edge(association["id"], target, "targets_entity", association["path"], association["line"],
                     "Compiler-resolved association target entity name")
        else:
            diagnostics.append({"code": "ORM_ASSOCIATION_TARGET_UNRESOLVED", "path": association["path"],
                                "source_line": association["line"], "association": association["id"],
                                "target_type": association["target"]})
        if association["mapped_by"]:
            owners = [candidate for candidate in association_records
                      if candidate["owner"] == association["target"] and candidate["field"] == association["mapped_by"]]
            if len(owners) == 1:
                add_edge(association["id"], owners[0]["id"], "inverse_of", association["path"], association["line"],
                         "mappedBy names the owning association attribute")
            else:
                diagnostics.append({"code": "ORM_MAPPED_BY_UNRESOLVED", "path": association["path"],
                                    "source_line": association["line"], "association": association["id"],
                                    "mapped_by": association["mapped_by"]})

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
                repository_owner = str((symbols.get(repo.id) or {}).get("owner", ""))
                if repository_owner:
                    repository_models[repository_owner] = model_name
            elif repo and not models:
                diagnostics.append({"code": "SPRING_DATA_MODEL_UNRESOLVED", "path": path, "source_line": line, "repository": repo.id, "model": model_name})
            if repo:
                # Derived query names use a bounded Spring Data grammar and are
                # checked against the selected entity/embedded attribute model.
                body_start = match.end()
                body_end = source.find("}", body_start)
                body = source[body_start:body_end if body_end >= 0 else len(source)]
                for derived in re.finditer(r"\b(?P<method>(?:find|read|get|query|search|count|exists|delete|remove|stream)\w*By[A-Z]\w*)\s*\(", body):
                    method_name = derived.group("method")
                    parsed = _derived_query(method_name)
                    if parsed is None:
                        continue
                    method = next((node for node in nodes.values() if node.path == path and node.kind == "method" and node.name == method_name), None)
                    if method is None:
                        continue
                    query_line = line + body[:derived.start()].count("\n")
                    resolved_predicates = []
                    unresolved_predicates = []
                    for predicate in parsed["predicates"]:
                        target, resolved_path = resolve_query_property(model_name, predicate["property"])
                        value = {**predicate, "resolved_path": resolved_path, "attribute_id": target}
                        resolved_predicates.append(value)
                        if target is None:
                            unresolved_predicates.append(predicate["property"])
                    resolved_orders = []
                    for order in parsed["order_by"]:
                        target, resolved_path = resolve_query_property(model_name, order["property"])
                        resolved_orders.append({**order, "resolved_path": resolved_path, "attribute_id": target})
                        if target is None:
                            unresolved_predicates.append(order["property"])
                    query_id = add_node("orm_query", f"{method_name}:DERIVED", path, query_line, method,
                                        query_language="DERIVED", entity=model_name,
                                        action=parsed["action"], predicates=resolved_predicates,
                                        order_by=resolved_orders, dynamic=False,
                                        validated=not unresolved_predicates)
                    add_edge(method.id, query_id, "declares_query", path, query_line,
                             "Spring Data derived query method")
                    entity_id = entity_nodes.get(model_name)
                    if entity_id:
                        relation = "query_deletes" if parsed["action"] in {"delete", "remove"} else "query_reads"
                        add_edge(query_id, entity_id, relation, path, query_line,
                                 "Derived query action against repository entity; static persistence intent only")
                    for predicate in resolved_predicates:
                        if predicate["attribute_id"]:
                            add_edge(query_id, predicate["attribute_id"], "filters_by", path, query_line,
                                     f"Derived predicate {predicate['operator']} resolved against entity model")
                    for order in resolved_orders:
                        if order["attribute_id"]:
                            add_edge(query_id, order["attribute_id"], "orders_by", path, query_line,
                                     f"Derived order {order['direction']} resolved against entity model")
                    if unresolved_predicates:
                        diagnostics.append({"code": "SPRING_DATA_DERIVED_PROPERTY_UNRESOLVED", "path": path,
                                            "source_line": query_line, "method": method.id,
                                            "entity": model_name, "properties": sorted(set(unresolved_predicates)),
                                            "reason": "Derived query property does not resolve in the indexed entity model."})

    # Explicit @Query is owned by its compiler method symbol. Static JPQL is
    # resolved against entity attributes; native SQL is limited to exact table
    # names in the selected persistence realm. Dynamic expressions stay unresolved.
    for item in symbols.values():
        if item.get("kind") != "method" or str(item.get("owner", "")) not in repository_models:
            continue
        path = item.get("path")
        if not isinstance(path, str) or path not in source_text:
            continue
        values = _annotation_map(item, source_text[path])
        query_annotation = _annotation(values, "Query")
        if not query_annotation or not _allowed_annotation(query_annotation[0], _imports(source_text[path]),
                                                            ("org.springframework.data.",)):
            continue
        method = nodes.get(item["id"])
        if method is None:
            continue
        line = (item.get("range") or {}).get("start_line")
        raw = query_annotation[1]
        language = "NATIVE_SQL" if (_named_string_arg(raw, "nativeQuery") or "false").casefold() == "true" else "JPQL"
        value = _named_string_arg(raw, "value") or _named_string_arg(raw, "query")
        dynamic = value is None or "#{" in value or "${" in value
        parameter_names = [str(name) for name in item.get("parameter_names", [])]
        query_parameters = sorted(set(re.findall(r":([A-Za-z_]\w*)", value or "")))
        unbound = sorted(set(query_parameters) - set(parameter_names))
        return_type = str(item.get("return_type", ""))
        return_parts = re.findall(r"[A-Za-z_$][\w.$]*", return_type)
        projection_type = _simple(return_parts[-1]) if return_parts else None
        model_name = repository_models[str(item.get("owner"))]
        named_query_name = _named_string_arg(raw, "name")
        if value is None and named_query_name:
            named = named_queries.get(named_query_name)
            language = str(named.get("language")) if named else "NAMED"
            query_id = add_node("orm_query", f"{method.name}:{language}", path, line, method,
                                query_language=language, query=None, query_name=named_query_name,
                                dynamic=False, entity=model_name, parameters=[],
                                method_parameters=parameter_names, unbound_parameters=[],
                                return_type=return_type or None, projection_type=projection_type,
                                validated=named is not None)
            add_edge(method.id, query_id, "declares_query", path, line, "Compiler-owned named repository query")
            if named:
                add_edge(query_id, named["id"], "uses_named_query", path, line,
                         "@Query name resolves to static JPA named query")
            else:
                diagnostics.append({"code": "SPRING_DATA_NAMED_QUERY_UNRESOLVED", "path": path,
                                    "source_line": line, "method": method.id, "query_name": named_query_name})
            continue
        query_id = add_node("orm_query", f"{method.name}:{language}", path, line, method,
                            query_language=language, query=value, dynamic=dynamic,
                            entity=model_name, parameters=query_parameters,
                            method_parameters=parameter_names, unbound_parameters=unbound,
                            return_type=return_type or None, projection_type=projection_type,
                            validated=False if dynamic or unbound else True)
        add_edge(method.id, query_id, "declares_query", path, line, f"Compiler-owned @Query {language}")
        if dynamic:
            diagnostics.append({"code": "ORM_DYNAMIC_QUERY_UNRESOLVED", "path": path, "source_line": line,
                                "method": method.id, "query_language": language})
            continue
        if unbound:
            diagnostics.append({"code": "SPRING_DATA_QUERY_PARAMETER_UNBOUND", "path": path, "source_line": line,
                                "method": method.id, "parameters": unbound})
        if projection_type and projection_type not in {"void", "boolean", "Boolean", "long", "Long", "int", "Integer"}:
            projection = next((candidate for candidate in nodes.values()
                               if candidate.name == projection_type and candidate.kind in {"class", "interface", "type"}), None)
            if projection:
                add_edge(query_id, projection.id, "returns_entity" if projection_type in entity_nodes else "returns_projection",
                         path, line, "Compiler return type of repository query")
            else:
                diagnostics.append({"code": "SPRING_DATA_QUERY_PROJECTION_UNRESOLVED", "path": path,
                                    "source_line": line, "method": method.id, "projection_type": projection_type})
        query_lower = value.lstrip().casefold()
        action = "query_deletes" if query_lower.startswith("delete") else "query_writes" if query_lower.startswith(("update", "insert")) else "query_reads"
        if language == "JPQL":
            entity_match = re.search(r"\b(?:from|update)\s+([\w.$]+)(?:\s+(?:as\s+)?([A-Za-z_]\w*))?", value, re.I)
            query_entity = _simple(entity_match.group(1)) if entity_match else model_name
            alias = entity_match.group(2) if entity_match else None
            entity_id = entity_nodes.get(query_entity)
            if entity_id:
                add_edge(query_id, entity_id, action, path, line, "JPQL entity resolved against compiler JPA model")
            else:
                diagnostics.append({"code": "JPQL_ENTITY_UNRESOLVED", "path": path, "source_line": line,
                                    "method": method.id, "entity": query_entity})
            if alias:
                for attribute_path in sorted(set(re.findall(rf"\b{re.escape(alias)}\.([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)", value))):
                    property_name = "".join(part[:1].upper() + part[1:] if index else part
                                            for index, part in enumerate(attribute_path.split(".")))
                    target, resolved_path = resolve_query_property(query_entity, property_name)
                    if target:
                        add_edge(query_id, target, "filters_by", path, line,
                                 f"JPQL path {resolved_path} resolved against entity model")
                    else:
                        diagnostics.append({"code": "JPQL_ATTRIBUTE_UNRESOLVED", "path": path,
                                            "source_line": line, "method": method.id, "attribute": attribute_path})
        else:
            tables = sorted(set(re.findall(r"\b(?:from|join|update|into)\s+([A-Za-z_][\w.$]*)", value, re.I)))
            for table_name in tables:
                matches = [candidate for candidate in nodes.values() if candidate.kind == "orm_table" and
                           str((candidate.metadata or {}).get("logical_name", candidate.name)).casefold() == table_name.rsplit(".", 1)[-1].casefold()]
                if len(matches) == 1:
                    add_edge(query_id, matches[0].id, action, path, line,
                             "Native SQL exact table name in selected ORM projection")
                else:
                    diagnostics.append({"code": "NATIVE_QUERY_TABLE_UNRESOLVED" if not matches else "NATIVE_QUERY_TABLE_AMBIGUOUS",
                                        "path": path, "source_line": line, "method": method.id,
                                        "table": table_name, "candidates": [candidate.id for candidate in matches]})

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
            contexts[index] = {**current, "framework_analysis": {"spring": SPRING_RULE_VERSION, "jpa": "annotation-source-v4",
                                                                  "schema_binding": "exact-name-only", "coverage": "PARTIAL"}}
            break
    result = replace(graph, nodes=sorted(nodes.values(), key=lambda item: item.id),
                     edges=sorted(edges.values(), key=lambda item: (item.source, item.kind, item.target)),
                     contexts=contexts, diagnostics=diagnostics, evidence=sorted(evidence.values(), key=lambda item: item["id"]),
                     analysis_annotations=annotations)
    KnowledgeGraph.from_dict(result.to_dict())
    return result
