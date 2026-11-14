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
import hashlib
import xml.etree.ElementTree as ET
from xml.parsers import expat
from dataclasses import replace
from pathlib import Path
from typing import Any

from .analysis_model import AnalysisError, digest
from .model import Edge, KnowledgeGraph, Node
from .spring_imports import selector_info
from .spring_conditions import AnnotationArguments, evaluate_conditions
from .spring_beans import FACTORY, factory_info, registration_assignability

SPRING_RULE_VERSION = "annotation-source-v7-proxy-async"
JPA_RULE_VERSION = "annotation-source-v7-schema-compatibility"
JPA_XML_NAMESPACES = {
    "https://jakarta.ee/xml/ns/persistence/orm",
    "http://xmlns.jcp.org/xml/ns/persistence/orm",
    "http://java.sun.com/xml/ns/persistence/orm",
}
JPA_PERSISTENCE_NAMESPACES = {
    "https://jakarta.ee/xml/ns/persistence",
    "http://xmlns.jcp.org/xml/ns/persistence",
    "http://java.sun.com/xml/ns/persistence",
}
JPA_XML_VERSIONS = {"1.0", "2.0", "2.1", "2.2", "3.0", "3.1", "3.2"}
MAX_JPA_XML_BYTES = 2 * 1024 * 1024


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
SPRING_PROXY_POLICIES = {
    "org.springframework.context.annotation.EnableAspectJAutoProxy": "AOP",
    "org.springframework.transaction.annotation.EnableTransactionManagement": "TRANSACTION",
    "org.springframework.scheduling.annotation.EnableAsync": "ASYNC",
    "org.springframework.cache.annotation.EnableCaching": "CACHE",
    "org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity": "SECURITY",
}
SPRING_ADVICE_POLICIES = {
    "Transactional": "TRANSACTION", "Async": "ASYNC",
    "Cacheable": "CACHE", "CachePut": "CACHE", "CacheEvict": "CACHE",
    "Secured": "SECURITY", "PreAuthorize": "SECURITY",
}
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


def _jpa_name_arg(args: str, names=("name", "value")) -> str | None:
    """Decode a compiler constant's JSON string, preserving SQL quote markers."""
    import json
    for name in names:
        match = re.search(r"\b" + re.escape(name) + r"\s*=\s*", args)
        if match:
            try:
                value, _ = json.JSONDecoder().raw_decode(args[match.end():])
            except (ValueError, TypeError):
                return None
            return value if isinstance(value, str) else None
    return _string_arg(args, names)


def _sql_identifier(value: str | None) -> str | None:
    from .schema_replay import identifier, statements
    if not isinstance(value, str):
        return None
    try:
        parsed = statements(value)
        if len(parsed) != 1 or len(parsed[0][0]) != 1 or parsed[0][0][0] != value:
            return None
        return identifier(parsed[0][0][0])
    except AnalysisError:
        return None


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


def _xml_local(element: ET.Element) -> tuple[str, str]:
    tag = element.tag if isinstance(element.tag, str) else ""
    if tag.startswith("{") and "}" in tag:
        namespace, local = tag[1:].split("}", 1)
        return namespace, local
    return "", tag


def _xml_bool(value: str | None) -> bool | None:
    if value is None:
        return False
    if value.strip().lower() == "true":
        return True
    if value.strip().lower() == "false":
        return False
    return None


def _safe_jpa_xml(root: Path, relative: str) -> tuple[ET.Element | None, dict[str, Any] | None]:
    """Parse only small, root-confined XML data without DTD/entity processing."""
    base = root.resolve()
    try:
        target = (root / relative).resolve(strict=True)
        target.relative_to(base)
        if not target.is_file():
            return None, {"code": "ORM_XML_FILE_INVALID", "path": relative,
                          "reason": "Mapping path is not a regular file inside the selected project root."}
        # Read at most one byte beyond the contract limit. XML mappings are
        # untrusted project input and must not cause an unbounded allocation.
        with target.open("rb") as stream:
            raw = stream.read(MAX_JPA_XML_BYTES + 1)
    except (OSError, RuntimeError, ValueError):
        return None, {"code": "ORM_XML_FILE_INVALID", "path": relative,
                      "reason": "Mapping file is missing or escapes the selected project root."}
    if len(raw) > MAX_JPA_XML_BYTES:
        return None, {"code": "ORM_XML_SIZE_LIMIT", "path": relative,
                      "reason": "XML exceeds the bounded 2 MiB metadata input limit."}
    try:
        # Expat recognizes BOMs and XML-declared UTF-16 encodings, unlike a
        # byte regex. Reject declarations at parser level before ElementTree
        # can expand internal entities.
        guard = expat.ParserCreate()
        def reject_doctype(*_args):
            raise ValueError("DTD")
        guard.StartDoctypeDeclHandler = reject_doctype
        guard.EntityDeclHandler = reject_doctype
        guard.Parse(raw, True)
        document = ET.fromstring(raw)
    except ValueError:
        return None, {"code": "ORM_XML_UNSAFE_DECLARATION", "path": relative,
                      "reason": "DTD and entity declarations are unsupported; external content is never fetched."}
    except LookupError:
        return None, {"code": "ORM_XML_ENCODING_UNSUPPORTED", "path": relative,
                      "reason": "XML declares an unsupported character encoding."}
    except (ET.ParseError, expat.ExpatError):
        return None, {"code": "ORM_XML_PARSE_INVALID", "path": relative,
                      "reason": "XML is malformed; annotation fallback is suppressed for the selected mapping scope."}
    return document, {"path": target.relative_to(base).as_posix(),
                      "sha256": hashlib.sha256(raw).hexdigest()}


def _jpa_xml_model(root: Path, context: dict[str, Any]) -> dict[str, Any]:
    """Read a selected persistence unit and bounded ORM XML class metadata."""
    descriptor = root / "META-INF/persistence.xml"
    model: dict[str, Any] = {"classes": {}, "diagnostics": [], "active": False,
                             "global_unknown": False, "metadata_complete": False,
                             "persistence_unit": context.get("persistence_unit"),
                             "descriptor_path": None, "descriptor_sha256": None}
    descriptor_info: dict[str, Any] | None = None
    units: list[ET.Element] = []
    descriptor_complete = False
    if descriptor.exists():
        parsed, descriptor_info = _safe_jpa_xml(root, "META-INF/persistence.xml")
        if parsed is None:
            model["diagnostics"].append(descriptor_info)
            model["global_unknown"] = True
            return model
        namespace, local = _xml_local(parsed)
        if local != "persistence" or namespace not in JPA_PERSISTENCE_NAMESPACES:
            model["diagnostics"].append({"code": "ORM_XML_NAMESPACE_UNSUPPORTED",
                                         "path": descriptor_info["path"],
                                         "reason": "persistence.xml root or namespace is not a supported Jakarta/Javax JPA descriptor."})
            model["global_unknown"] = True
            return model
        if parsed.get("version") not in JPA_XML_VERSIONS:
            model["diagnostics"].append({"code": "ORM_XML_VERSION_UNSUPPORTED",
                                         "path": descriptor_info["path"],
                                         "version": parsed.get("version"),
                                         "reason": "persistence.xml version is outside the supported JPA XML subset."})
            model["global_unknown"] = True
            return model
        if any(_xml_local(item)[0] != namespace for item in parsed.iter()):
            model["diagnostics"].append({"code": "ORM_XML_NAMESPACE_UNSUPPORTED",
                                         "path": descriptor_info["path"],
                                         "reason": "persistence.xml contains a foreign namespace element."})
            model["global_unknown"] = True
            return model
        units = [child for child in parsed if _xml_local(child)[1] == "persistence-unit"]
        model["descriptor_path"] = descriptor_info["path"]
        model["descriptor_sha256"] = descriptor_info["sha256"]
        selected_name = context.get("persistence_unit")
        named = [item for item in units if item.get("name") == selected_name] if isinstance(selected_name, str) else []
        if selected_name:
            if len(named) != 1:
                model["diagnostics"].append({"code": "ORM_XML_PERSISTENCE_UNIT_UNRESOLVED",
                                             "path": descriptor_info["path"],
                                             "persistence_unit": selected_name,
                                             "reason": "Selected persistence unit is absent or duplicated in persistence.xml."})
                model["global_unknown"] = True
                return model
            selected = named[0]
        elif len(units) == 1:
            selected = units[0]
            selected_name = selected.get("name")
        else:
            model["diagnostics"].append({"code": "ORM_XML_PERSISTENCE_UNIT_AMBIGUOUS",
                                         "path": descriptor_info["path"],
                                         "reason": "A persistence unit must be selected when the descriptor has zero or multiple units."})
            model["global_unknown"] = True
            return model
        model["persistence_unit"] = selected_name
        explicit_files = [child.text.strip() for child in selected
                          if _xml_local(child)[1] == "mapping-file" and child.text and child.text.strip()]
        listed_classes = [child.text.strip() for child in selected
                          if _xml_local(child)[1] == "class" and child.text and child.text.strip()]
        excluded_node = next((child for child in selected if _xml_local(child)[1] == "exclude-unlisted-classes"), None)
        excluded = _xml_bool((excluded_node.text or "true") if excluded_node is not None else None)
        if excluded is None:
            model["diagnostics"].append({"code": "ORM_XML_CLASS_LIST_UNKNOWN",
                                         "path": descriptor_info["path"],
                                         "reason": "exclude-unlisted-classes must be a literal true or false."})
            model["global_unknown"] = True
            return model
        model["listed_classes"] = listed_classes
        model["exclude_unlisted"] = bool(excluded)
        pu_metadata = [child for child in selected if _xml_local(child)[1] == "persistence-unit-metadata"]
        if len(pu_metadata) > 1:
            model["diagnostics"].append({"code": "ORM_XML_METADATA_UNKNOWN", "path": descriptor_info["path"],
                                         "reason": "Persistence unit declares duplicate metadata sections."})
            model["global_unknown"] = True
        for metadata in pu_metadata:
            for child in metadata:
                child_name = _xml_local(child)[1]
                if child_name == "xml-mapping-metadata-complete" and len(child) == 0:
                    descriptor_complete = True
                elif child_name == "persistence-unit-defaults":
                    for default in child:
                        if _xml_local(default)[1] == "access" and (default.text or "").strip() in {"FIELD", "PROPERTY"}:
                            model["default_access"] = (default.text or "").strip()
                        else:
                            model["diagnostics"].append({"code": "ORM_XML_DEFAULT_UNSUPPORTED", "path": descriptor_info["path"],
                                                         "construct": _xml_local(default)[1],
                                                         "reason": "Persistence-unit metadata default is outside the supported access-only subset."})
                            model["global_unknown"] = True
                else:
                    model["diagnostics"].append({"code": "ORM_XML_METADATA_UNKNOWN", "path": descriptor_info["path"],
                                                 "construct": child_name,
                                                 "reason": "Persistence-unit metadata construct is outside the supported subset."})
                    model["global_unknown"] = True
        model["metadata_complete"] = descriptor_complete
    else:
        explicit_files = []

    default_file = "META-INF/orm.xml"
    mapping_files = [default_file] if (root / default_file).exists() else []
    mapping_files.extend(item for item in explicit_files if item not in mapping_files)
    if not mapping_files:
        return model
    model["active"] = True
    for order, relative in enumerate(mapping_files):
        document, info = _safe_jpa_xml(root, relative)
        if document is None:
            model["diagnostics"].append(info)
            model["global_unknown"] = True
            continue
        namespace, local = _xml_local(document)
        if local != "entity-mappings" or namespace not in JPA_XML_NAMESPACES:
            model["diagnostics"].append({"code": "ORM_XML_NAMESPACE_UNSUPPORTED", "path": info["path"],
                                         "reason": "orm.xml root or namespace is not a supported Jakarta/Javax ORM mapping descriptor."})
            model["global_unknown"] = True
            continue
        if document.get("version") not in JPA_XML_VERSIONS:
            model["diagnostics"].append({"code": "ORM_XML_VERSION_UNSUPPORTED", "path": info["path"],
                                         "version": document.get("version"),
                                         "reason": "orm.xml version is outside the supported JPA XML subset."})
            model["global_unknown"] = True
            continue
        if any(_xml_local(item)[0] != namespace for item in document.iter()):
            model["diagnostics"].append({"code": "ORM_XML_NAMESPACE_UNSUPPORTED", "path": info["path"],
                                         "reason": "orm.xml contains a foreign namespace element."})
            model["global_unknown"] = True
            continue
        root_complete = _xml_bool(document.get("metadata-complete"))
        if root_complete is None:
            model["diagnostics"].append({"code": "ORM_XML_METADATA_COMPLETE_UNKNOWN", "path": info["path"],
                                         "reason": "metadata-complete must be the literal true or false."})
            model["global_unknown"] = True
            continue
        root_access = document.get("access", model.get("default_access"))
        if root_access is not None and root_access not in {"FIELD", "PROPERTY"}:
            model["diagnostics"].append({"code": "ORM_XML_ACCESS_UNKNOWN", "path": info["path"],
                                         "reason": "Mapping-level access must be FIELD or PROPERTY."})
            model["global_unknown"] = True
            continue
        metadata_sections = [child for child in document if _xml_local(child)[1] == "persistence-unit-metadata"]
        if len(metadata_sections) > 1:
            model["diagnostics"].append({"code": "ORM_XML_METADATA_UNKNOWN", "path": info["path"],
                                         "reason": "orm.xml declares duplicate persistence-unit-metadata sections."})
            model["global_unknown"] = True
        standard_complete = False
        defaults_sections = [child for child in document if _xml_local(child)[1] == "persistence-unit-defaults"]
        for metadata in metadata_sections:
            for nested in metadata:
                nested_kind = _xml_local(nested)[1]
                if nested_kind == "xml-mapping-metadata-complete" and len(nested) == 0:
                    standard_complete = True
                elif nested_kind == "persistence-unit-defaults":
                    defaults_sections.append(nested)
                else:
                    model["diagnostics"].append({"code": "ORM_XML_METADATA_UNKNOWN", "path": info["path"],
                                                 "construct": nested_kind,
                                                 "reason": "Persistence-unit metadata construct is outside the supported subset."})
                    model["global_unknown"] = True
        for defaults in defaults_sections:
            for default in defaults:
                default_kind = _xml_local(default)[1]
                if default_kind == "access" and (default.text or "").strip() in {"FIELD", "PROPERTY"}:
                    root_access = (default.text or "").strip()
                else:
                    model["diagnostics"].append({"code": "ORM_XML_DEFAULT_UNSUPPORTED", "path": info["path"],
                                                 "construct": default_kind,
                                                 "reason": "Persistence-unit mapping default is outside the supported access-only subset."})
                    model["global_unknown"] = True
        if root_access is not None:
            model["default_access"] = root_access
        model["metadata_complete"] = model["metadata_complete"] or root_complete or standard_complete
        packages = [child.text.strip() for child in document if _xml_local(child)[1] == "package"
                    and child.text and child.text.strip()]
        if len(packages) > 1:
            model["diagnostics"].append({"code": "ORM_XML_PACKAGE_AMBIGUOUS", "path": info["path"],
                                         "reason": "orm.xml declares more than one default package."})
            model["global_unknown"] = True
            continue
        package = packages[0] if packages else ""
        class_elements = [child for child in document if _xml_local(child)[1] in
                          {"entity", "mapped-superclass", "embeddable"}]
        seen_in_file: set[str] = set()
        for class_element in class_elements:
            kind = _xml_local(class_element)[1]
            raw_class = class_element.get("class", "").strip()
            owner = raw_class if "." in raw_class or "$" in raw_class else f"{package}.{raw_class}" if package else ""
            if not owner:
                model["diagnostics"].append({"code": "ORM_XML_CLASS_UNRESOLVED", "path": info["path"],
                                             "reason": "XML class must resolve to a fully qualified compiler owner."})
                model["global_unknown"] = True
                continue
            if owner in seen_in_file:
                record = model["classes"].setdefault(owner, {"owner": owner, "kind": kind, "unknown": False,
                                                               "attributes": {}, "overrides": {}, "files": []})
                record["unknown"] = True
                model["diagnostics"].append({"code": "ORM_XML_CLASS_MAPPING_AMBIGUOUS", "path": info["path"],
                                             "class": owner, "reason": "A class is mapped more than once in the same orm.xml."})
                continue
            seen_in_file.add(owner)
            complete = _xml_bool(class_element.get("metadata-complete"))
            if complete is None:
                model["diagnostics"].append({"code": "ORM_XML_METADATA_COMPLETE_UNKNOWN", "path": info["path"],
                                             "class": owner, "reason": "Class metadata-complete must be a literal true or false."})
                complete = True
            class_access = class_element.get("access", root_access)
            if class_access is not None and class_access not in {"FIELD", "PROPERTY"}:
                model["diagnostics"].append({"code": "ORM_XML_ACCESS_UNKNOWN", "path": info["path"],
                                             "class": owner, "reason": "Class access must be FIELD or PROPERTY."})
                class_access = "UNKNOWN"
            provenance = {"xml_sha256": info["sha256"], "xml_mapping_file": info["path"],
                          "persistence_xml_sha256": model["descriptor_sha256"],
                          "persistence_xml_path": model["descriptor_path"],
                          "persistence_unit": model["persistence_unit"], "xml_mapping_order": order,
                          "xml_precedence": "ORM_XML_OVER_ANNOTATIONS"}
            record = model["classes"].setdefault(owner, {"owner": owner, "kind": kind, "unknown": False,
                                                           "attributes": {}, "overrides": {}, "files": []})
            record["kind"] = kind
            record["metadata_complete"] = bool(record.get("metadata_complete") or complete or root_complete or standard_complete)
            if class_access is not None:
                record["access"] = class_access
                if class_access == "UNKNOWN":
                    record["unknown"] = True
            record["order"] = order
            record["provenance"] = provenance
            record["files"].append(info["path"])
            for child in class_element:
                child_name = _xml_local(child)[1]
                if child_name == "table":
                    record["table"] = {"name": child.get("name"), "schema": child.get("schema"),
                                       "catalog": child.get("catalog"), "provenance": provenance}
                elif child_name == "attributes":
                    for attr in child:
                        attr_kind = _xml_local(attr)[1]
                        if attr_kind not in {"id", "embedded-id", "basic", "version", "embedded",
                                             "many-to-one", "one-to-one", "one-to-many", "many-to-many",
                                             "element-collection"}:
                            record["unknown"] = True
                            model["diagnostics"].append({"code": "ORM_XML_CONSTRUCT_UNSUPPORTED", "path": info["path"],
                                                         "class": owner, "construct": attr_kind,
                                                         "reason": "Unsupported XML attribute mapping remains UNKNOWN."})
                            continue
                        attr_name = attr.get("name", "").strip()
                        if not attr_name:
                            record["unknown"] = True
                            model["diagnostics"].append({"code": "ORM_XML_ATTRIBUTE_UNRESOLVED", "path": info["path"],
                                                         "class": owner, "reason": "XML attribute mapping has no name."})
                            continue
                        column = next((entry for entry in attr if _xml_local(entry)[1] == "column"), None)
                        if any(_xml_local(entry)[1] != "column" for entry in attr):
                            record["unknown"] = True
                            model["diagnostics"].append({"code": "ORM_XML_CONSTRUCT_UNSUPPORTED", "path": info["path"],
                                                         "class": owner, "attribute": attr_name,
                                                         "reason": "Nested XML mapping construct is not supported by the scalar binding subset."})
                        if column is not None and column.get("table"):
                            record["unknown"] = True
                            model["diagnostics"].append({"code": "ORM_XML_COLUMN_TABLE_UNSUPPORTED", "path": info["path"],
                                                         "class": owner, "attribute": attr_name,
                                                         "reason": "Column table remapping is outside the selected single-table attribute projection."})
                        spec = {"kind": attr_kind, "column": column.get("name") if column is not None else None,
                                "column_present": column is not None, "provenance": provenance}
                        previous = record["attributes"].get(attr_name)
                        if previous and previous.get("provenance", {}).get("xml_mapping_order") == order:
                            spec["ambiguous"] = True
                            previous["ambiguous"] = True
                        record["attributes"][attr_name] = spec
                elif child_name == "attribute-override":
                    attr_name = child.get("name", "").strip()
                    column = next((entry for entry in child if _xml_local(entry)[1] == "column"), None)
                    spec = {"column": column.get("name") if column is not None else None,
                            "column_present": column is not None, "provenance": provenance}
                    if not attr_name:
                        record["unknown"] = True
                        model["diagnostics"].append({"code": "ORM_XML_ATTRIBUTE_UNRESOLVED", "path": info["path"],
                                                     "class": owner, "reason": "Attribute override has no attribute name."})
                    else:
                        previous = record["overrides"].get(attr_name)
                        if previous and previous.get("provenance", {}).get("xml_mapping_order") == order:
                            spec["ambiguous"] = True
                            previous["ambiguous"] = True
                        record["overrides"][attr_name] = spec
                elif child_name == "inheritance":
                    strategy = child.get("strategy") or "SINGLE_TABLE"
                    if strategy not in {"SINGLE_TABLE", "JOINED", "TABLE_PER_CLASS"}:
                        record["unknown"] = True
                        model["diagnostics"].append({"code": "ORM_XML_INHERITANCE_UNKNOWN", "path": info["path"],
                                                     "class": owner, "strategy": strategy,
                                                     "reason": "XML inheritance strategy is outside the supported JPA enum values."})
                    else:
                        record["inheritance_strategy"] = strategy
                elif child_name != "description":
                    record["unknown"] = True
                    model["diagnostics"].append({"code": "ORM_XML_CONSTRUCT_UNSUPPORTED", "path": info["path"],
                                                 "class": owner, "construct": child_name,
                                                 "reason": "Unsupported class-level ORM XML construct remains UNKNOWN."})
    return model


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
    if "annotations" not in symbol and symbol.get("path") and (symbol.get("range") or {}).get("start_line"):
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
    # Reproject only this context's framework layer after an explicit replay
    # attachment; compiler facts and other contexts remain immutable inputs.
    owned_proofs = {p['id'] for p in graph.evidence if isinstance(p, dict) and isinstance(p.get('id'), str)
                    and p.get('kind') == 'FRAMEWORK_DERIVED' and p.get('context_ids') == [context_id]
                    and isinstance(p.get('framework_rules'), dict)}
    owned_edges = {e for e in graph.edges if e.evidence_kind == "FRAMEWORK_DERIVED"
                   and e.context_ids == (context_id,) and e.evidence_ids
                   and set(e.evidence_ids) <= owned_proofs}
    other_edges = [e for e in graph.edges if e not in owned_edges]
    foreign_references = {endpoint for e in other_edges for endpoint in (e.source, e.target)}
    owned_nodes = ({endpoint for e in owned_edges for endpoint in (e.source, e.target)
                    if endpoint.startswith("framework:")} | {n.id for n in graph.nodes
                    if n.id.startswith("framework:") and (n.metadata or {}).get("context_id") == context_id}) - foreign_references
    nodes = {node.id: node for node in graph.nodes if node.id not in owned_nodes}
    compiler_contexts = {c.get('id') for c in graph.contexts if c.get('language') == 'jvm'}
    symbols = {item.get("id"): item for item in graph.symbols if isinstance(item, dict)
               and isinstance(item.get("id"), str) and (item.get('context_id') == context_id
               or item.get('context_id') is None and compiler_contexts == {context_id})}
    captured = context.get('source_files')
    source_text = {path: _path_text(root, path) for path in graph.files
                   if Path(path).suffix.lower() in {".java", ".kt", ".kts"}
                   and (not isinstance(captured, dict) or captured.get(path) == graph.files[path])}
    evidence = {item["id"]: item for item in graph.evidence if isinstance(item, dict)
                and isinstance(item.get("id"), str) and item['id'] not in owned_proofs}
    edges = {(item.source, item.target, item.kind): item for item in other_edges}
    previous_diagnostics = [d for d in graph.diagnostics if d.get("framework_context_id") != context_id]
    diagnostics = []
    jpa_xml = _jpa_xml_model(root, context)
    diagnostics.extend(jpa_xml["diagnostics"])
    annotations: list[dict[str, Any]] = list(graph.analysis_annotations)
    spring_beans: list[dict[str, Any]] = []
    spring_proxy_policies: list[dict[str, Any]] = []
    entity_decls: list[dict[str, Any]] = []
    embeddable_decls: list[dict[str, Any]] = []
    mapped_superclass_decls: list[dict[str, Any]] = []
    class_by_name: dict[str, list[str]] = {}
    annotation_types = {str(item.get("owner")): item for item in symbols.values()
                        if item.get("kind") == "annotation_type" and isinstance(item.get("owner"), str)}

    def evidence_for(kind: str, source: str, target: str, relation: str, path: str, line: int | None, detail: str,
                     compiler_fact: dict | None = None, xml_provenance: dict[str, Any] | None = None, supporting_facts: list | None = None) -> str:
        record = {"kind": kind, "source": source, "target": target, "relation": relation,
                  "context_ids": [context_id], "source_file": path, "source_line": line,
                  "detail": detail, "framework_rules": context.get("framework_rule_versions", {})}
        if relation in {"query_reads", "query_writes", "query_deletes", "resolves_to_schema_table", "resolves_to_schema_column"}:
            record["persistence_selection"] = {key: context.get(key) for key in
                ("database_id", "schema_stream_id", "persistence_unit", "persistence_schema", "flyway_target")}
            target_node = nodes.get(target)
            if target_node is not None and isinstance((target_node.metadata or {}).get("persistence_realm"), dict):
                record["persistence_realm"] = dict(target_node.metadata["persistence_realm"])
            elif target_node is not None and target_node.kind == 'orm_table':
                physical = [nodes[e.target] for e in edges.values() if e.source == target
                            and e.kind == 'resolves_to_schema_table' and e.context_ids == (context_id,)
                            and e.target in nodes]
                if len(physical) == 1 and isinstance((physical[0].metadata or {}).get('persistence_realm'), dict):
                    record['persistence_realm'] = dict(physical[0].metadata['persistence_realm'])
        if compiler_fact is not None:
            record.update(compiler_symbol_id=compiler_fact["id"], sha256=compiler_fact.get("sha256"),
                          compiler_backend=compiler_fact.get("compiler_backend", "javac"))
        if xml_provenance:
            record.update(xml_provenance)
        if supporting_facts:
            record["compiler_sources"] = [{"symbol_id": fact["id"], "sha256": fact.get("sha256"),
                "path": fact.get("path"), "context_id": fact.get("context_id")} for fact in supporting_facts]
        identity = "evidence:" + digest(record)
        evidence.setdefault(identity, {"id": identity, **record})
        return identity

    def add_edge(source: str, target: str, kind: str, path: str, line: int | None, detail: str,
                 evidence_kind: str = "FRAMEWORK_DERIVED", compiler_fact: dict | None = None,
                 xml_provenance: dict[str, Any] | None = None, supporting_facts: list | None = None) -> None:
        if source not in nodes or target not in nodes:
            return
        key = (source, target, kind)
        if key in edges:
            # Keep the stronger, context-bound framework proof when the source
            # scanner produced a weaker domain candidate for the same relation.
            old = edges[key]
            if old.evidence_kind == evidence_kind or evidence_kind != "FRAMEWORK_DERIVED":
                return
        proof = evidence_for(evidence_kind, source, target, kind, path, line, detail,
                             compiler_fact=compiler_fact, xml_provenance=xml_provenance,
                             supporting_facts=supporting_facts)
        edges[key] = Edge(source, target, kind, detail, evidence_kind=evidence_kind,
                          context_ids=(context_id,), evidence_ids=(proof,), source_file=path, source_line=line)

    def add_node(kind: str, name: str, path: str, line: int | None, source: Node | None = None,
                 declaration_identity: str | None = None,
                 **metadata: Any) -> str:
        identity_fields = {"context": context_id, "path": path, "line": line, "name": name}
        if declaration_identity is not None:
            identity_fields["declaration_identity"] = declaration_identity
        identity = _node_id(kind, identity_fields)
        if identity not in nodes:
            metadata["context_id"] = context_id
            nodes[identity] = Node(identity, kind, name, path, line=line,
                                    signature=metadata.pop("signature", None),
                                    summary=metadata.pop("summary", None),
                                    scope=source.scope if source else context.get("scope", "unknown"),
                                    role="contract" if kind in {"spring_endpoint", "spring_entrypoint", "orm_query"} else "executable_code",
                                    origin="generated", metadata=metadata or None)
        return identity

    def bind_persistent_attribute(attribute: str, owner: str, name: str, path: str, *, access="FIELD", relation="projects_persistent_attribute") -> None:
        # This edge is an explicit compiler declaration witness, not a type-name
        # resolver. Missing/overloaded/unsupported getter bindings remain absent.
        facts = [fact for fact in symbols.values() if fact.get("owner") == owner
                 and fact.get("name") == name and fact.get("path") == path
                 and fact.get("kind") == ("field" if access == "FIELD" else "method")]
        if len(facts) != 1 or facts[0].get("id") not in nodes:
            return
        fact = facts[0]
        add_edge(fact["id"], attribute, relation, path,
                 (fact.get("range") or {}).get("start_line"),
                 "Exact compiler declaration of the effective persistent attribute",
                 compiler_fact=fact)

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
    registrar_candidates: dict[tuple[str, str], tuple[dict, str]] = {}

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
                    if info["kind"] == "REGISTRAR":
                        declaration = target["symbol"]
                        registrar = add_node("spring_registrar", exact, declaration["path"],
                            (declaration.get("range") or {}).get("start_line"), symbol_node(declaration),
                            registration_status=info["status"], reasons=info["reasons"], execution="NOT_EXECUTED")
                        registrar_candidates[(owner, exact)] = (info, registrar)
                        add_edge(importer["id"], registrar, "uses_bean_registrar", importer["path"],
                                 (importer.get("range") or {}).get("start_line"), "Compiler-qualified @Import registrar")
                        if info["status"] == "UNKNOWN" and exact not in reported_dynamic:
                            reported_dynamic.add(exact)
                            diagnostics.append({"code": "SPRING_REGISTRAR_BOUNDARY", "path": declaration["path"],
                                "type": exact, "reasons": info["reasons"], "reason": "Custom registrar body is not executed."})
                        continue
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

    jpa_declarations = {
        "entity": entity_decls,
        "mapped-superclass": mapped_superclass_decls,
        "embeddable": embeddable_decls,
    }
    for owner, xml_class in jpa_xml["classes"].items():
        type_record = type_records.get(owner)
        if type_record is None:
            diagnostics.append({"code": "ORM_XML_CLASS_UNRESOLVED",
                                "path": xml_class.get("provenance", {}).get("xml_mapping_file"),
                                "class": owner,
                                "reason": "XML class name does not match an exact compiler-attributed owner in this context."})
            jpa_xml["global_unknown"] = True
            xml_class["unknown"] = True
            continue
        selected_declarations = [declaration for collection in jpa_declarations.values()
                                 for declaration in collection
                                 if declaration["symbol"].get("owner") == owner]
        if selected_declarations:
            if len(selected_declarations) != 1 or selected_declarations[0] not in jpa_declarations.get(xml_class["kind"], []):
                diagnostics.append({"code": "ORM_XML_CLASS_KIND_MISMATCH",
                                    "path": xml_class.get("provenance", {}).get("xml_mapping_file"),
                                    "class": owner, "xml_kind": xml_class["kind"],
                                    "reason": "XML entity/mapped-superclass/embeddable kind conflicts with compiler-resolved annotation classification."})
                xml_class["unknown"] = True
            else:
                selected_declarations[0]["xml_mapping"] = xml_class
            continue
        item = type_record["symbol"]
        source_path = item.get("path")
        node = symbol_node(item)
        if node is None or not isinstance(source_path, str) or source_path not in source_text:
            diagnostics.append({"code": "ORM_XML_CLASS_UNRESOLVED",
                                "path": xml_class.get("provenance", {}).get("xml_mapping_file"),
                                "class": owner,
                                "reason": "Compiler class node or source declaration is absent from the selected context."})
            xml_class["unknown"] = True
            jpa_xml["global_unknown"] = True
            continue
        kind_label = xml_class["kind"]
        jpa_annotations = [("jakarta.persistence." + {"entity": "Entity", "mapped-superclass": "MappedSuperclass",
                                                        "embeddable": "Embeddable"}[kind_label], "")]
        declaration = {"node": node, "symbol": item, "annotations": jpa_annotations,
                       "path": source_path, "line": (item.get("range") or {}).get("start_line"),
                       "source": source_text[source_path], "imports": type_record["imports"],
                       "xml_mapping": xml_class}
        jpa_declarations[kind_label].append(declaration)

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
                if name == "Async":
                    boundary = add_node("spring_async_boundary", f"async:{node.name}", path, line, node,
                                        boundary_kind="TASK_EXECUTOR", continuation="SEPARATE",
                                        scheduling="FRAMEWORK_MANAGED", execution="NOT_OBSERVED",
                                        availability="UNKNOWN")
                    add_edge(node.id, boundary, "declares_async_transition", path, line,
                             "@Async declares a task-executor transition; scheduling is not observed")
                elif name == "EventListener":
                    boundary = add_node("spring_event_boundary", f"event-listener:{node.name}", path, line, node,
                                        boundary_kind="APPLICATION_EVENT", continuation="SEPARATE",
                                        scheduling="CALLER_THREAD_BY_DEFAULT", execution="NOT_OBSERVED",
                                        availability="UNKNOWN")
                    add_edge(node.id, boundary, "declares_event_transition", path, line,
                             "@EventListener declares event delivery, not a direct synchronous call edge")
            if name in SPRING_ADVICE:
                if _allowed_annotation(annotation, imports, ("org.springframework.",)):
                    advice = add_node("spring_advice", f"{name}:{node.name}", path, line, node, advice=name,
                                      application_status="DECLARATION_ONLY", execution="NOT_OBSERVED",
                                      availability="UNKNOWN")
                    add_edge(node.id, advice, "advised_by", path, line, f"@{name} advice declaration")

        return_type = str(item.get("return_type", "")).split("<", 1)[0].rstrip("?")
        spring_owner = any(symbols.get(bean["node"].id, {}).get("owner") == item.get("owner")
                           and bean.get("condition_status") != "INACTIVE" for bean in spring_beans)
        if spring_owner and return_type in {"reactor.core.publisher.Mono", "reactor.core.publisher.Flux",
                                            "org.reactivestreams.Publisher"}:
            boundary = add_node("spring_reactive_boundary", f"reactive:{node.name}", path, line, node,
                                boundary_kind="REACTIVE_PUBLISHER", continuation="SUBSCRIPTION_DEPENDENT",
                                publisher_type=return_type, execution="NOT_OBSERVED", availability="UNKNOWN")
            add_edge(node.id, boundary, "declares_reactive_transition", path, line,
                     "Exact reactive publisher return type; subscription and execution are not observed")

    # Proxy selection is declaration-only.  A later call-site projection may
    # reference an ACTIVE policy, but neither this annotation nor a compatible
    # source call proves that advice ran.
    for owner, record in type_records.items():
        if not record["configuration"]:
            continue
        for annotation, args in record["values"]:
            policy_kind = SPRING_PROXY_POLICIES.get(annotation)
            if policy_kind is None:
                continue
            simple = _simple(annotation)
            if not isinstance(args, AnnotationArguments) \
                    or args.resolved is not True or not isinstance(args.members, dict):
                mode, strategy, status = "UNKNOWN", "UNKNOWN", "UNKNOWN"
                reasons = ["typed compiler annotation members are unavailable"]
            else:
                members = args.members
                proxy_target = members.get("proxyTargetClass", False)
                advice_mode = members.get("mode", "org.springframework.context.annotation.AdviceMode.PROXY")
                if type(proxy_target) is not bool:
                    mode, strategy, status = "UNKNOWN", "UNKNOWN", "UNKNOWN"
                    reasons = ["proxyTargetClass is not a compiler-resolved boolean"]
                elif policy_kind != "AOP" and isinstance(advice_mode, str) and advice_mode.endswith(".ASPECTJ"):
                    mode, strategy, status = "ASPECTJ", "ASPECTJ_WEAVING", "UNKNOWN"
                    reasons = ["AspectJ mode is declared but no compile/load-time weaving artifact is observed"]
                elif policy_kind != "AOP" and (not isinstance(advice_mode, str) or not advice_mode.endswith(".PROXY")):
                    mode, strategy, status = "UNKNOWN", "UNKNOWN", "UNKNOWN"
                    reasons = ["async advice mode is unresolved or unsupported"]
                else:
                    mode = "PROXY"
                    strategy = "CGLIB_SUBCLASS" if proxy_target else "JDK_DYNAMIC"
                    status = configuration_states.get(owner, "INACTIVE")
                    reasons = list(record["direct_reasons"])
            declaration = record["symbol"]
            line = (declaration.get("range") or {}).get("start_line")
            policy = add_node("spring_proxy_policy", f"{simple}:{owner}", declaration["path"], line,
                              symbol_node(declaration), policy_kind=policy_kind,
                              mode=mode, strategy=strategy, activation_status=status,
                              condition_status=configuration_states.get(owner, "INACTIVE"),
                              reasons=reasons, execution="NOT_EXECUTED")
            add_edge(declaration["id"], policy, "enables_proxy_policy", declaration["path"], line,
                     f"@{simple} compiler-resolved proxy policy declaration")
            spring_proxy_policies.append({"node": policy,
                                          "kind": policy_kind,
                                          "mode": mode, "strategy": strategy, "status": status,
                                          "path": declaration["path"], "line": line})
            if status == "UNKNOWN":
                diagnostics.append({"code": "SPRING_WEAVING_UNVERIFIED" if mode == "ASPECTJ" else "SPRING_PROXY_POLICY_UNRESOLVED",
                                    "path": declaration["path"], "source_line": line, "policy": policy,
                                    "reasons": reasons})

    # Registrar declarations inherit the importing configuration's condition;
    # RootBeanDefinition does not evaluate the target class's @Profile itself.
    def registration_types(declared_type):
        if not declared_type:
            return []
        hierarchy = (type_records.get(declared_type, {}).get("symbol", {}).get("type_hierarchy") or {})
        names = hierarchy.get("types", []) if hierarchy.get("complete") is True else []
        return list(dict.fromkeys([declared_type.rsplit(".", 1)[-1], *[name.rsplit(".", 1)[-1] for name in names]]))

    declarations = {}
    for (owner, exact), (info, registrar) in registrar_candidates.items():
        method = info["method"]
        for registration in info["registrations"]:
            state = _combined_state(configuration_states[owner], "ACTIVE" if info["status"] == "RESOLVED_LITERAL" else "UNKNOWN")
            key = (exact, method["id"], registration["name"], registration["type"])
            previous = declarations.get(key)
            if previous is None or rank[state] > rank[previous[3]]:
                declarations[key] = (info, registrar, registration, state, owner, exact)
    for info, registrar, registration, state, owner, exact in declarations.values():
        method = info["method"]
        target = type_records.get(registration["type"])
        if (target is None or target["configuration"] or processor(registration["type"]) is not None
                or factory_info(target["symbol"], symbols, context_id) is not None
                or target["symbol"].get("kind") != "class"
                or "abstract" in target["symbol"].get("modifiers", [])):
            diagnostics.append({"code": "SPRING_REGISTRAR_TARGET_UNSUPPORTED", "path": method["path"],
                "type": registration["type"], "reason": "Registration target is not an indexed ordinary concrete class."})
            old = nodes[registrar]
            nodes[registrar] = replace(old, metadata={**(old.metadata or {}), "registration_status": "UNKNOWN",
                "reasons": [*(old.metadata or {}).get("reasons", []), "TARGET_UNSUPPORTED:" + registration["type"]]})
            continue
        name, product = registration["name"], registration["type"].rsplit(".", 1)[-1]
        product_types = registration_types(registration["type"])
        line = (method.get("range") or {}).get("start_line")
        bean = add_node("spring_bean", name, method["path"], line, symbol_node(method),
            declaration_identity=exact,
            registration_origin="REGISTRAR_LITERAL", registering_type=exact, declared_type=registration["type"],
            types=product_types, qualifier=name, qualifiers=[], primary=False, profiles=[],
            condition_status=state, condition_reasons=[f"importing configuration {owner} is {configuration_states[owner]}", *info["reasons"]])
        add_edge(registrar, bean, "registers_bean", method["path"], line,
                 "Compiler-attributed literal registry declaration; registrar never executed", compiler_fact=method)
        spring_beans.append({"node": symbol_node(method), "bean": bean, "type": product, "types": product_types,
            "name": name, "qualifiers": [], "primary": False, "profiles": [], "condition_status": state,
            "condition_reasons": info["reasons"], "path": method["path"], "line": line})

    # A FactoryBean object is dereferenced with '&'; its product is a different
    # declaration. Unknown/custom production never becomes an ACTIVE product.
    for bean in list(spring_beans):
        source = symbols.get(bean["node"].id, {})
        info = factory_info(source, symbols, context_id)
        if info is None:
            continue
        original = nodes.pop(bean["bean"])
        original_name = bean["name"]
        object_types = (["FactoryBean"] if source.get("kind") == "method" else list(dict.fromkeys(
            [source.get("name", "FactoryBean"), "FactoryBean", *[name.rsplit(".", 1)[-1]
             for name in (source.get("type_hierarchy") or {}).get("types", [])]])))
        object_state = _combined_state(bean["condition_status"], "UNKNOWN" if "FACTORY_NOT_CONCRETE" in info["reasons"] else "ACTIVE")
        obj = add_node("spring_bean", "&" + original_name, original.path, original.line, bean["node"],
                       **{**(original.metadata or {}), "types": object_types, "qualifier": "&" + original_name,
                          "condition_status": object_state,
                          "registration_origin": "FACTORY_OBJECT", "factory_name": original_name,
                          "declared_type": info["factory_type"],
                          "factory_product_type": info["product_type"]})
        for key, edge in list(edges.items()):
            if edge.target == original.id:
                del edges[key]
                add_edge(edge.source, obj, edge.kind, edge.source_file or original.path, edge.source_line,
                         "FactoryBean object declaration; product is separate")
        bean.update(bean=obj, name="&" + original_name, types=object_types, type=object_types[0], qualifiers=[], condition_status=object_state)
        product = info["product_type"]
        if product not in type_records:
            info["reasons"].append("FACTORY_PRODUCT_NOT_INDEXED")
            info["status"] = "UNKNOWN"
        state = _combined_state(bean["condition_status"], "ACTIVE" if info["status"] == "RESOLVED_LITERAL" else "UNKNOWN")
        product_types = registration_types(product)
        product_node = add_node("spring_bean", original_name, original.path, original.line, bean["node"],
            **{**(original.metadata or {}), "registration_origin": "FACTORY_PRODUCT", "factory_name": original_name,
               "declared_type": product, "types": product_types, "condition_status": state,
               "condition_reasons": [*bean["condition_reasons"], *info["reasons"]], "execution": "NOT_EXECUTED"})
        proof = info["method"] or source
        add_edge(obj, product_node, "produces_bean", proof.get("path") or original.path,
                 (proof.get("range") or {}).get("start_line") or original.line,
                 "Compiler factory product declaration; custom code never executed", compiler_fact=proof,
                 supporting_facts=info["sources"])
        spring_beans.append({**bean, "bean": product_node, "name": original_name, "types": product_types,
                             "type": product_types[0] if product_types else "", "condition_status": state,
                             "qualifiers": (original.metadata or {}).get("qualifiers", [])})
        if info["status"] == "UNKNOWN":
            diagnostics.append({"code": "SPRING_FACTORY_BOUNDARY", "path": original.path,
                "source_line": original.line, "bean": product_node, "reasons": info["reasons"],
                "reason": "Custom or unproven FactoryBean product remains UNKNOWN."})

    # No registry override order is executed. Conflicting registration names
    # remain alternatives even when a Primary declaration exists elsewhere.
    names = {}
    for bean in spring_beans:
        if bean["condition_status"] != "INACTIVE":
            names.setdefault(bean["name"], []).append(bean)
    for name, candidates in names.items():
        if len({bean["bean"] for bean in candidates}) < 2 or not any(
                (nodes[bean["bean"]].metadata or {}).get("registration_origin") for bean in candidates):
            continue
        for bean in candidates:
            bean["condition_status"] = "UNKNOWN"
            old = nodes[bean["bean"]]
            nodes[old.id] = replace(old, metadata={**(old.metadata or {}), "condition_status": "UNKNOWN",
                "condition_reasons": [*(old.metadata or {}).get("condition_reasons", []), "REGISTRATION_NAME_COLLISION"]})
        diagnostics.append({"code": "SPRING_REGISTRATION_NAME_COLLISION", "name": name,
            "reason": "Registry override order is not executed; competing declarations remain UNKNOWN."})

    # Constructor/field injection is intentionally conservative.  A matching
    # type is a candidate, while qualifier/primary/profile controls the result.
    def resolve_query_property(model_owner: str, property_name: str) -> tuple[str | None, str | None]:
        normalized = property_name.replace("_", "").casefold()
        direct = entity_attributes.get(model_owner, {}).get(normalized)
        if direct:
            return direct, property_name
        for outer, outer_id in entity_attributes.get(model_owner, {}).items():
            if not normalized.startswith(outer) or len(normalized) == len(outer):
                continue
            embedded_type = entity_embedded_types.get((model_owner, outer))
            suffix = normalized[len(outer):]
            nested = next((identity for (owner, name), identity in embeddable_attributes.items()
                           if owner == embedded_type and name.casefold() == suffix), None)
            if nested:
                return nested, f"{outer}.{suffix}"
            associated_type = entity_association_types.get((model_owner, outer))
            associated_owners = entity_owners_by_simple.get(associated_type or "", [])
            associated = (entity_attributes.get(associated_owners[0], {}).get(suffix)
                          if len(associated_owners) == 1 else None)
            if associated:
                return associated, f"{outer}.{suffix}"
        return None, None

    repository_models: dict[str, str] = {}

    def repository_entity_owner(repository_symbol: dict[str, Any] | None) -> str | None:
        """Select a repository entity only from compiler-resolved generic facts."""
        if not repository_symbol:
            return None
        owners: set[str] = set()
        for supertype in repository_symbol.get("supertypes", []):
            match = re.fullmatch(r"([\w.$]+)\s*<(.+)>", str(supertype))
            if not match:
                continue
            repository_type = match.group(1).replace("$", ".")
            if not repository_type.startswith("org.springframework.data.") \
                    or _simple(repository_type) not in JPA_REPOSITORIES:
                continue
            model_type = match.group(2).split(",", 1)[0].strip().replace("$", ".")
            if model_type in entity_decls_by_owner:
                owners.add(model_type)
        return next(iter(owners)) if len(owners) == 1 else None

    for path, source in source_text.items():
        imports = _imports(source)
        if not any(item.startswith("org.springframework") or item.startswith("jakarta.inject") or item.startswith("javax.inject") for item in imports):
            continue
        type_lines = [(node, (symbols.get(node.id) or {}).get("range", {}).get("start_line", 0))
                      for node in nodes.values() if node.id in symbols and node.path == path and node.kind in {"class", "interface"}]
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
            # A user interface named FactoryBean is not the Spring contract.
            # Use the compiler field's qualified type for this factory boundary.
            owner_symbol = symbols.get(owner.id, {})
            field = next((item for item in symbols.values() if item.get("kind") == "field"
                          and item.get("owner") == owner_symbol.get("owner")
                          and item.get("name") == match.group("name")
                          and item.get("context_id") == context_id), {})
            qualified_candidates = []
            for candidate in candidates:
                metadata = nodes[candidate["bean"]].metadata or {}
                origin = metadata.get("registration_origin")
                official_factory = str(field.get("type", "")).split("<", 1)[0] == FACTORY
                if origin in {"REGISTRAR_LITERAL", "FACTORY_PRODUCT"} or origin == "FACTORY_OBJECT" and not official_factory:
                    assignability = registration_assignability(metadata.get("declared_type"), field.get("type"), injection_kind, type_records)
                    if assignability == "INCOMPATIBLE":
                        continue
                    if assignability == "UNKNOWN":
                        candidate = {**candidate, "condition_status": _combined_state(candidate["condition_status"], "UNKNOWN")}
                        diagnostics.append({"code": "SPRING_REGISTRATION_ASSIGNABILITY_BOUNDARY", "path": path,
                            "source_line": line, "reason": "Qualified registration/product/factory-object assignability is unproven."})
                qualified_candidates.append(candidate)
            candidates = qualified_candidates
            if str(field.get("type", "")).split("<", 1)[0] == FACTORY:
                candidates = [bean for bean in candidates
                              if (nodes[bean["bean"]].metadata or {}).get("registration_origin") == "FACTORY_OBJECT"]
                requested = str(field.get("type", ""))
                generic = re.fullmatch(re.escape(FACTORY) + r"<([\w.$]+)>", requested)
                if generic:
                    candidates = [bean for bean in candidates if (nodes[bean["bean"]].metadata or {}).get("factory_product_type") == generic.group(1)]
                elif "<" in requested:
                    candidates = [{**bean, "condition_status": _combined_state(bean["condition_status"], "UNKNOWN")}
                                  for bean in candidates]
                    diagnostics.append({"code": "SPRING_FACTORY_GENERIC_INJECTION_BOUNDARY", "path": path,
                        "source_line": line, "type": requested, "reason": "Non-concrete FactoryBean generic selection remains UNKNOWN."})
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
                                 injection_kind=injection_kind, qualifier=qualifier,
                                 owner=str(owner_symbol.get("owner", "")), field=match.group("name"))
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
    from .schema_replay import persistence_pair, schema_node_realm, persistence_selection
    selected_pair = persistence_pair(context.get("database_id"), context.get("schema_stream_id"))
    selected_schema = context.get("persistence_schema")
    selected_target = context.get("flyway_target")
    valid_selectors = all(v is None or isinstance(v, str) and v and v == v.strip()
                          for v in (selected_schema, selected_target))
    recorded_contexts = [c for c in graph.contexts if c.get('id') == context_id]
    try:
        selection = persistence_selection(context)
        valid_selection = (len(recorded_contexts) == 1
            and persistence_selection(recorded_contexts[0]) == selection
            and context.get('persistence_selection_hash') == digest(selection)
            and recorded_contexts[0].get('persistence_selection_hash') == digest(selection))
    except (ValueError, TypeError):
        valid_selection = False
    valid_selectors = valid_selectors and valid_selection
    if entity_decls and (selected_pair is None or not valid_selectors):
        diagnostics.append({"code": "PERSISTENCE_REALM_UNPROVEN",
                            "reason": "Explicit database_id and schema_stream_id with valid optional schema/target selectors are required for physical schema binding."})

    def in_schema_realm(candidate: Node, declared_schema: str | None = None) -> bool:
        realm = schema_node_realm(candidate)
        if selected_pair is None or not valid_selectors or not isinstance(realm, dict):
            return False
        if persistence_pair(realm.get("database_id"), realm.get("stream_id")) != selected_pair:
            return False
        if not {"database_id", "stream_id"} <= set(realm.get("explicit_keys", [])):
            return False
        if selected_target is not None and realm.get("target") != selected_target:
            return False
        declared_name = _sql_identifier(declared_schema)
        selected_name = _sql_identifier(selected_schema)
        if declared_schema is not None and declared_name is None or selected_schema is not None and selected_name is None:
            return False
        if declared_name is not None and selected_name is not None and declared_name != selected_name:
            return False
        expected_schema = selected_name or declared_name
        if expected_schema is None:
            available = set(realm['schemas'])
            if len(available) != 1:
                return False
            expected_schema = next(iter(available))
        return realm.get('schema') == expected_schema

    def schema_table_matches(candidate: Node, table_name, table_schema) -> bool:
        return (in_schema_realm(candidate, table_schema)
                and candidate.metadata['schema_object'][1] == _sql_identifier(table_name))

    def schema_column_matches(candidate: Node, table_name, table_schema, column_name) -> bool:
        return (in_schema_realm(candidate, table_schema)
                and candidate.metadata['schema_object'][1:] == [_sql_identifier(table_name), _sql_identifier(column_name)])

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
                           _jpa_name_arg(column_annotation, ("name", "value")) if column_annotation else field_name)
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

    mapped_superclass_ids_by_owner: dict[str, str] = {}
    mapped_superclasses_by_owner: dict[str, dict[str, Any]] = {}
    mapped_superclasses_by_simple: dict[str, list[dict[str, Any]]] = {}
    for declaration in mapped_superclass_decls:
        source_node: Node = declaration["node"]
        owner = str(declaration["symbol"].get("owner", ""))
        mapped_id = add_node("orm_mapped_superclass", source_node.name, declaration["path"], declaration["line"], source_node,
                             java_type=owner or source_node.name)
        if owner:
            mapped_superclass_ids_by_owner[owner] = mapped_id
            mapped_superclasses_by_owner[owner] = declaration
            mapped_superclasses_by_simple.setdefault(_simple(owner), []).append(declaration)
        add_edge(source_node.id, mapped_id, "declares_mapped_superclass", declaration["path"], declaration["line"],
                 "Compiler-resolved JPA @MappedSuperclass declaration")

    entity_decls_by_owner = {
        str(item["symbol"]["owner"]): item for item in entity_decls
        if isinstance(item["symbol"].get("owner"), str) and item["symbol"].get("owner")
    }
    entity_decls_by_simple: dict[str, list[dict[str, Any]]] = {}
    for declaration in entity_decls:
        entity_decls_by_simple.setdefault(declaration["node"].name, []).append(declaration)
    entity_owners_by_simple = {
        name: [str(item["symbol"].get("owner", "")) for item in declarations
               if isinstance(item["symbol"].get("owner"), str) and item["symbol"].get("owner")]
        for name, declarations in entity_decls_by_simple.items()
    }
    # A simple name is suitable for display, but never selects one of multiple
    # compiler-resolved entity owners.
    entity_nodes = {name: declarations[0]["node"].id for name, declarations in entity_decls_by_simple.items()
                    if len(declarations) == 1}
    entity_nodes_by_owner = {owner: item["node"].id for owner, item in entity_decls_by_owner.items() if owner}
    entity_query_owners: dict[str, list[str]] = {}
    for owner, declaration in entity_decls_by_owner.items():
        entity_annotation = next((item for item in declaration["symbol"].get("annotations", [])
                                  if isinstance(item, dict) and isinstance(item.get("name"), str)
                                  and _simple(item["name"]) == "Entity"), None)
        if entity_annotation is None or entity_annotation.get("values_resolved") is False:
            continue
        raw_entity_values = entity_annotation.get("values") if isinstance(entity_annotation.get("values"), dict) else {}
        explicit_entity_name = raw_entity_values.get("name", raw_entity_values.get("value"))
        if explicit_entity_name is not None and not isinstance(explicit_entity_name, str):
            continue
        entity_name = explicit_entity_name or declaration["node"].name
        entity_query_owners.setdefault(entity_name, []).append(owner)

    def entity_index_key(declaration: dict[str, Any]) -> str:
        owner = declaration["symbol"].get("owner")
        # A graph node ID is an opaque per-declaration key for incomplete test or
        # legacy inputs; it cannot be confused with a compiler-qualified owner.
        return owner if isinstance(owner, str) and owner else "unresolved-owner:" + declaration["node"].id

    entity_table_nodes: dict[str, str] = {}
    entity_table_by_owner: dict[str, str] = {}
    entity_attributes: dict[str, dict[str, str]] = {entity_index_key(item): {} for item in entity_decls}
    entity_embedded_types: dict[tuple[str, str], str] = {}
    embeddable_inherited_accesses: dict[str, set[str]] = {}
    entity_association_types: dict[tuple[str, str], str] = {}
    named_queries: dict[str, dict[str, Any]] = {}
    association_records: list[dict[str, Any]] = []

    def java_mapped_fields(declaration: dict[str, Any]) -> list[dict[str, Any]]:
        if not str(declaration["path"]).endswith(".java"):
            return []
        text_lines = str(declaration["source"]).splitlines()
        start = int(declaration["line"] or 1)
        later_types = [int((item["symbol"].get("range") or {}).get("start_line") or item["line"])
                       for item in [*entity_decls, *mapped_superclass_decls]
                       if item["path"] == declaration["path"] and (item["line"] or 0) > start]
        end = min(later_types or [len(text_lines) + 1])
        body = "\n".join(text_lines[start - 1:end - 1])
        field_pattern = re.compile(
            r"(?P<annotations>(?:@[\w.]+(?:\([^\n]*?\))?\s*)+)"
            r"(?:(?:public|protected|private|static|final|transient|volatile)\s+)*"
            r"(?P<type>[A-Za-z_$][\w.$<>?, \[\]]*)\s+(?P<name>[A-Za-z_$][\w$]*)\s*(?:[;=]|$)", re.M)
        result = []
        for match in field_pattern.finditer(body):
            annotations = [(name, args) for name, args in re.findall(r"@([\w.]+)\s*(\([^\n]*?\))?", match.group("annotations"))
                           if _allowed_jpa_annotation(name, declaration["imports"])]
            result.append({"name": match.group("name"), "type": match.group("type").strip(),
                           "annotations": annotations,
                           "line": start + body[:match.start()].count("\n")})
        return result

    def inherited_mapped_access(symbol: dict[str, Any]) -> str | None:
        """Return one compiler-proven access mode from mapped-superclass IDs."""
        modes: set[str] = set()
        visited: set[str] = set()

        def visit(owner: str) -> None:
            if owner in visited:
                return
            visited.add(owner)
            declaration = mapped_superclasses_by_owner.get(owner)
            if declaration is None:
                matches = mapped_superclasses_by_simple.get(_simple(owner), []) if "." not in owner else []
                declaration = matches[0] if len(matches) == 1 else None
            if declaration is None:
                parent_entity = entity_decls_by_owner.get(owner)
                if parent_entity:
                    for parent_value in parent_entity["symbol"].get("supertypes", []):
                        visit(str(parent_value).split("<", 1)[0].strip().replace("/", "."))
                return
            access_annotation = _annotation(declaration["annotations"], "Access")
            if access_annotation and access_annotation[1] != "__UNRESOLVED__":
                mode = (_string_arg(access_annotation[1], ("value",)) or "").rsplit(".", 1)[-1]
                if mode in {"FIELD", "PROPERTY"}:
                    modes.add(mode)
            for field in symbols.values():
                if field.get("kind") != "field" or field.get("owner") != declaration["symbol"].get("owner"):
                    continue
                for annotation in field.get("annotations", []):
                    if not isinstance(annotation, dict) or not isinstance(annotation.get("name"), str):
                        continue
                    if _simple(annotation["name"]) not in {"Id", "EmbeddedId"} or not _allowed_jpa_annotation(
                            annotation["name"], declaration["imports"]):
                        continue
                    target = str(annotation.get("use_site_target", "")).upper()
                    if target in {"FIELD", "BACKING_FIELD"}:
                        modes.add("FIELD")
                    elif target in {"GET", "GETTER", "PROPERTY_GETTER"}:
                        modes.add("PROPERTY")
            if str(declaration["path"]).endswith(".java"):
                for field in java_mapped_fields(declaration):
                    if any(_simple(name) in {"Id", "EmbeddedId"} for name, _ in field["annotations"]):
                        modes.add("FIELD")
                for method in symbols.values():
                    if method.get("kind") != "method" or method.get("owner") != declaration["symbol"].get("owner"):
                        continue
                    if not re.fullmatch(r"(?:get|is)[A-Z].*", str(method.get("name", ""))):
                        continue
                    method_values = _annotation_map(method, declaration["source"])
                    if any(_simple(name) in {"Id", "EmbeddedId"} and
                           _allowed_jpa_annotation(name, declaration["imports"]) for name, _ in method_values):
                        modes.add("PROPERTY")
            for parent_value in declaration["symbol"].get("supertypes", []):
                visit(str(parent_value).split("<", 1)[0].strip().replace("/", "."))

        for parent_value in symbol.get("supertypes", []):
            visit(str(parent_value).split("<", 1)[0].strip().replace("/", "."))
        return next(iter(modes)) if len(modes) == 1 else None

    for entity in entity_decls:
        node: Node = entity["node"]
        entity_owner = entity_index_key(entity)
        values = entity["annotations"]
        table_annotation = _annotation(values, "Table")
        table_values_unknown = bool(table_annotation and table_annotation[1] == "__UNRESOLVED__")
        table_name = _jpa_name_arg(table_annotation[1], ("name", "value")) if table_annotation and not table_values_unknown else None
        table_schema = _jpa_name_arg(table_annotation[1], ("schema",)) if table_annotation else None
        inferred = table_name is None
        inferred = inferred and not table_values_unknown
        table_name = table_name or (None if table_values_unknown else node.name)
        qualified_table = f"{table_schema}.{table_name}" if table_schema else table_name
        table_id = None
        if table_name is not None:
            inheritance_annotation = _annotation(values, "Inheritance")
            inheritance_strategy = (_named_string_arg(inheritance_annotation[1], "strategy") or "").rsplit(".", 1)[-1] if inheritance_annotation else "SINGLE_TABLE"
            table_id = add_node("orm_table", qualified_table, entity["path"], entity["line"], node,
                                logical_name=table_name, schema=table_schema, inferred=inferred,
                                inheritance_strategy=inheritance_strategy if inheritance_strategy in {"SINGLE_TABLE", "JOINED", "TABLE_PER_CLASS"} else "UNKNOWN",
                                database_id=context.get("database_id"),
                                schema_stream_id=context.get("schema_stream_id"),
                                persistence_unit=context.get("persistence_unit"),
                                naming_strategy=context.get("naming_strategy"))
            entity_table_nodes[entity_owner] = table_id
            if entity["symbol"].get("owner"):
                entity_table_by_owner[entity_owner] = table_id
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
            super_name = str(supertype).split("<", 1)[0].strip().replace("/", ".")
            candidates = ([mapped_superclasses_by_owner[super_name]] if super_name in mapped_superclasses_by_owner
                          else mapped_superclasses_by_simple.get(_simple(super_name), []) if "." not in super_name else [])
            if len(candidates) == 1:
                mapped_decl = candidates[0]
                mapped = mapped_superclass_ids_by_owner.get(str(mapped_decl["symbol"].get("owner", "")))
                if not mapped:
                    continue
                add_edge(node.id, mapped, "inherits_mapping", entity["path"], entity["line"],
                         "Compiler-resolved @MappedSuperclass inheritance")
            elif len(candidates) > 1:
                diagnostics.append({"code": "ORM_MAPPED_SUPERCLASS_AMBIGUOUS", "path": entity["path"],
                                    "source_line": entity["line"], "entity": node.id,
                                    "supertype": super_name,
                                    "candidates": [item["symbol"].get("owner") for item in candidates],
                                    "reason": "Mapped superclass simple name is ambiguous; no inheritance edge is published."})
        matches = [candidate for candidate in schema_tables if table_id and schema_table_matches(candidate, table_name, table_schema)]
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
            mapped_access = inherited_mapped_access(entity["symbol"])
            local_access = ("FIELD" if has_field_id and not has_getter_id else
                            "PROPERTY" if has_getter_id and not has_field_id else None)
            access_conflict = bool(mapped_access and (
                explicit_access in {"FIELD", "PROPERTY"} and explicit_access != mapped_access or
                local_access and local_access != mapped_access))
            entity_access = ("UNKNOWN" if access_values_unknown or access_conflict else
                             explicit_access if explicit_access in {"FIELD", "PROPERTY"} else
                             local_access or mapped_access or "UNKNOWN")
            if access_conflict:
                diagnostics.append({"code": "ORM_MAPPED_SUPERCLASS_ACCESS_AMBIGUOUS", "path": entity["path"],
                                    "source_line": entity["line"], "entity": node.id,
                                    "local_access": local_access, "explicit_access": explicit_access,
                                    "mapped_superclass_access": mapped_access,
                                    "reason": "Entity and mapped superclass access evidence conflicts; persistence access remains UNKNOWN."})
            if access_values_unknown:
                diagnostics.append({"code": "ORM_ACCESS_STRATEGY_UNKNOWN", "path": entity["path"],
                                    "source_line": entity["line"], "entity": node.id,
                                    "reason": "Explicit @Access value is unresolved; identifier placement cannot override it."})
            if entity_access == "UNKNOWN":
                diagnostics.append({"code": "ORM_KOTLIN_ACCESS_AMBIGUOUS", "path": entity["path"],
                                    "source_line": entity["line"], "entity": node.id,
                                    "reason": "Kotlin JPA identifier has no unique @field:/@get: target or explicit @Access; persistence access is not inferred."})
        else:
            mapped_access = inherited_mapped_access(entity["symbol"])
            local_access = "PROPERTY" if property_id and not field_id else "FIELD" if field_id else None
            access_conflict = bool(mapped_access and (
                local_access and local_access != mapped_access or
                explicit_access in {"FIELD", "PROPERTY"} and explicit_access != mapped_access))
            entity_access = ("UNKNOWN" if access_conflict or access_values_unknown else
                             explicit_access if explicit_access in {"FIELD", "PROPERTY"} else
                             local_access or mapped_access or "FIELD")
            if access_conflict:
                diagnostics.append({"code": "ORM_MAPPED_SUPERCLASS_ACCESS_AMBIGUOUS", "path": entity["path"],
                                    "source_line": entity["line"], "entity": node.id,
                                    "local_access": local_access, "mapped_superclass_access": mapped_access,
                                    "reason": "Entity and mapped superclass access evidence conflicts; persistence access remains UNKNOWN."})
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
                                 identifier=identifier, embedded=embedded, declaring_owner=entity["symbol"].get("owner"))
            bind_persistent_attribute(attribute, entity["symbol"].get("owner"), field_name, entity["path"])
            entity_attributes[entity_owner][field_name.casefold()] = attribute
            if table_id:
                add_edge(attribute, table_id, "declared_on_table", entity["path"], field_line, "JPA persistent attribute")
            if identifier:
                add_edge(node.id, attribute, "has_embedded_id" if embedded_id_annotation is not None else "has_id",
                         entity["path"], field_line, "JPA identifier placement determines FIELD access")
            if embedded:
                embedded_type = re.findall(r"[A-Za-z_]\w*", field_type)[-1]
                entity_embedded_types[(entity_owner, field_name.casefold())] = embedded_type
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
                entity_association_types[(entity_owner, field_name.casefold())] = target_type
                association = add_node("orm_association", f"{node.name}.{field_name}", entity["path"], field_line, node,
                                       association=_simple(relation), target_type=target_type,
                                       mapped_by=mapped_by, association_role="INVERSE" if mapped_by else "OWNING")
                bind_persistent_attribute(association, entity["symbol"].get("owner"), field_name, entity["path"], relation="projects_persistent_association")
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
            column_name = _jpa_name_arg(column_annotation, ("name", "value")) if column_annotation else field_name
            column_id = add_node("orm_column", column_name, entity["path"], field_line, node,
                                 logical_name=column_name, inferred=not bool(column_annotation))
            add_edge(attribute, column_id, "maps_to_column", entity["path"], field_line,
                     "@Column name" if column_annotation else "Persistent attribute name; converter/naming strategy not verified")
            column_matches = [candidate for candidate in schema_columns if table_name
                              and schema_column_matches(candidate, table_name, table_schema, column_name)]
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
                                     identifier=identifier, embedded=embedded, getter=getter_name, declaring_owner=entity["symbol"].get("owner"))
                bind_persistent_attribute(attribute, entity["symbol"].get("owner"), getter_name, entity["path"], access="PROPERTY")
                entity_attributes[entity_owner][property_name.casefold()] = attribute
                if table_id:
                    add_edge(attribute, table_id, "declared_on_table", entity["path"], property_line,
                             "JPA property-access persistent attribute")
                if identifier:
                    add_edge(node.id, attribute, "has_embedded_id" if embedded_id else "has_id",
                             entity["path"], property_line, "JPA identifier placement determines PROPERTY access")
                if embedded:
                    embedded_type = re.findall(r"[A-Za-z_]\w*", property_type)[-1]
                    entity_embedded_types[(entity_owner, property_name.casefold())] = embedded_type
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
                    entity_association_types[(entity_owner, property_name.casefold())] = target_type
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
                column_name = _jpa_name_arg(column_annotation, ("name", "value")) if column_annotation else property_name
                column_id = add_node("orm_column", column_name, entity["path"], property_line, node,
                                     logical_name=column_name, inferred=not bool(column_annotation))
                add_edge(attribute, column_id, "maps_to_column", entity["path"], property_line,
                         "Property @Column name" if column_annotation else "Property name; naming strategy not verified")

    # A mapped superclass has no table of its own. Build a declaration fact for
    # each compiler-attributed persistent property, then project it per entity
    # so the declaration owner and effective entity owner are never conflated.
    def mapped_ancestors(owner: str, seen: set[str] | None = None) -> list[dict[str, Any]] | None:
        seen = set() if seen is None else seen
        if owner in seen:
            return None
        seen.add(owner)
        declaration = mapped_superclasses_by_owner.get(owner)
        if declaration is None:
            return []
        result: list[dict[str, Any]] = []
        for parent_value in declaration["symbol"].get("supertypes", []):
            parent = str(parent_value).split("<", 1)[0].strip().replace("/", ".")
            parent_decl = mapped_superclasses_by_owner.get(parent)
            if parent_decl is None:
                matches = mapped_superclasses_by_simple.get(_simple(parent), []) if "." not in parent else []
                if len(matches) > 1:
                    return None
                parent_decl = matches[0] if matches else None
            if parent_decl:
                parent_chain = mapped_ancestors(str(parent_decl["symbol"].get("owner", "")), seen)
                if parent_chain is None:
                    return None
                result.extend(parent_chain)
        result.append(declaration)
        return result

    def entity_ancestors(owner: str, seen: set[str] | None = None) -> list[dict[str, Any]] | None:
        seen = set() if seen is None else seen
        if owner in seen:
            return None
        seen.add(owner)
        declaration = entity_decls_by_owner.get(owner)
        if declaration is None:
            return []
        result: list[dict[str, Any]] = []
        for parent_value in declaration["symbol"].get("supertypes", []):
            parent = str(parent_value).split("<", 1)[0].strip().replace("/", ".")
            if parent not in entity_decls_by_owner:
                continue
            chain = entity_ancestors(parent, seen)
            if chain is None:
                return None
            result.extend(chain)
            result.append(entity_decls_by_owner[parent])
        return result

    def mapped_ancestors_for_entity(owner: str, seen: set[str] | None = None) -> list[dict[str, Any]] | None:
        seen = set() if seen is None else seen
        if owner in seen:
            return None
        seen.add(owner)
        declaration = entity_decls_by_owner.get(owner)
        if declaration is None:
            return []
        result: list[dict[str, Any]] = []
        for parent_value in declaration["symbol"].get("supertypes", []):
            parent = str(parent_value).split("<", 1)[0].strip().replace("/", ".")
            mapped = mapped_superclasses_by_owner.get(parent)
            if mapped:
                chain = mapped_ancestors(str(mapped["symbol"].get("owner", "")))
                if chain is None:
                    return None
                result.extend(chain)
            elif parent in entity_decls_by_owner:
                chain = mapped_ancestors_for_entity(parent, seen)
                if chain is None:
                    return None
                result.extend(chain)
        return result

    for entity in entity_decls:
        node: Node = entity["node"]
        raw_effective_owner = entity["symbol"].get("owner")
        if not isinstance(raw_effective_owner, str) or not raw_effective_owner:
            diagnostics.append({"code": "ORM_ENTITY_OWNER_UNKNOWN", "path": entity["path"],
                                "source_line": entity["line"], "entity": node.id,
                                "reason": "Compiler-qualified entity owner is absent; inherited persistence attributes are not projected."})
            continue
        effective_owner = raw_effective_owner
        inherited_declarations: list[dict[str, Any]] = []
        ancestry_unknown = False
        for parent_value in entity["symbol"].get("supertypes", []):
            parent = str(parent_value).split("<", 1)[0].strip().replace("/", ".")
            parent_decl = mapped_superclasses_by_owner.get(parent)
            if parent_decl is None:
                matches = mapped_superclasses_by_simple.get(_simple(parent), []) if "." not in parent else []
                if len(matches) > 1:
                    ancestry_unknown = True
                    diagnostics.append({"code": "ORM_MAPPED_SUPERCLASS_AMBIGUOUS", "path": entity["path"],
                                        "source_line": entity["line"], "entity": node.id,
                                        "supertype": parent, "candidates": [item["symbol"].get("owner") for item in matches],
                                        "reason": "Mapped superclass identity is ambiguous; inherited attributes are omitted."})
                elif matches:
                    parent_decl = matches[0]
            if parent_decl:
                chain = mapped_ancestors(str(parent_decl["symbol"].get("owner", "")))
                if chain is None:
                    ancestry_unknown = True
                    diagnostics.append({"code": "ORM_MAPPED_SUPERCLASS_HIERARCHY_UNKNOWN", "path": entity["path"],
                                        "source_line": entity["line"], "entity": node.id, "supertype": parent,
                                        "reason": "Mapped superclass hierarchy is cyclic or ambiguous; inherited attributes are omitted."})
                else:
                    inherited_declarations.extend(chain)
            elif parent in entity_decls_by_owner:
                chain = mapped_ancestors_for_entity(parent)
                if chain is None:
                    ancestry_unknown = True
                    diagnostics.append({"code": "ORM_MAPPED_SUPERCLASS_HIERARCHY_UNKNOWN", "path": entity["path"],
                                        "source_line": entity["line"], "entity": node.id, "supertype": parent,
                                        "reason": "Entity ancestry is cyclic or ambiguous; mapped superclass attributes are omitted."})
                else:
                    inherited_declarations.extend(chain)
        if not inherited_declarations or ancestry_unknown:
            continue
        table_id = entity_table_nodes.get(effective_owner)
        table = nodes.get(table_id) if table_id else None
        access = str((table.metadata or {}).get("access_strategy", "UNKNOWN")) if table else "UNKNOWN"
        if access not in {"FIELD", "PROPERTY"}:
            diagnostics.append({"code": "ORM_MAPPED_SUPERCLASS_ACCESS_UNKNOWN", "path": entity["path"],
                                "source_line": entity["line"], "entity": node.id,
                                "reason": "The effective entity access strategy is unknown; mapped superclass attributes are not projected."})
            continue
        inherited_entity_declarations = entity_ancestors(effective_owner)
        mapping_table_id = table_id
        if inherited_entity_declarations is None:
            mapping_table_id = None
            diagnostics.append({"code": "ORM_ENTITY_INHERITANCE_UNKNOWN", "path": entity["path"],
                                "source_line": entity["line"], "entity": node.id,
                                "reason": "Entity inheritance is cyclic or ambiguous; no effective table is selected."})
        elif inherited_entity_declarations:
            root_owner = str(inherited_entity_declarations[0]["symbol"].get("owner", ""))
            root_table_id = entity_table_by_owner.get(root_owner)
            root_table = nodes.get(root_table_id) if root_table_id else None
            strategy = str((root_table.metadata or {}).get("inheritance_strategy", "UNKNOWN")) if root_table else "UNKNOWN"
            if strategy in {"SINGLE_TABLE", "JOINED"}:
                mapping_table_id = root_table_id
            elif strategy == "TABLE_PER_CLASS":
                mapping_table_id = table_id
            else:
                mapping_table_id = None
                diagnostics.append({"code": "ORM_ENTITY_INHERITANCE_UNKNOWN", "path": entity["path"],
                                    "source_line": entity["line"], "entity": node.id,
                                    "root_entity": root_owner,
                                    "reason": "Root @Inheritance strategy is unresolved; inherited table mapping remains UNKNOWN."})
        seen_decls: dict[str, list[dict[str, Any]]] = {}
        for declaration in inherited_declarations:
            owner = str(declaration["symbol"].get("owner", ""))
            if str(declaration["path"]).endswith(".java"):
                field_candidates = java_mapped_fields(declaration) if access == "FIELD" else []
                if access == "PROPERTY":
                    field_candidates = []
                    for method in symbols.values():
                        if method.get("kind") != "method" or method.get("owner") != owner:
                            continue
                        getter = str(method.get("name", ""))
                        if not re.fullmatch(r"(?:get|is)[A-Z].*", getter):
                            continue
                        method_annotations = [(name, args) for name, args in _annotation_map(method, declaration["source"])
                                              if _allowed_jpa_annotation(name, declaration["imports"])]
                        property_name = getter[3:] if getter.startswith("get") else getter[2:]
                        property_name = property_name[:1].lower() + property_name[1:]
                        field_candidates.append({"name": property_name,
                                                 "type": method.get("return_type", "UNKNOWN"),
                                                 "annotations": method_annotations,
                                                 "line": (method.get("range") or {}).get("start_line") or declaration["line"]})
            else:
                field_candidates = []
                for field in symbols.values():
                    if field.get("kind") != "field" or field.get("owner") != owner:
                        continue
                    raw_annotations = field.get("annotations", [])
                    targets = {"FIELD", "BACKING_FIELD"} if access == "FIELD" else {"GET", "GETTER", "PROPERTY_GETTER"}
                    selected_items = [item for item in raw_annotations if isinstance(item, dict)
                                      and str(item.get("use_site_target", "")).upper() in targets]
                    selected = {**field, "annotations": selected_items}
                    field_annotations = [(name, args) for name, args in _annotation_map(selected, declaration["source"])
                                         if _allowed_jpa_annotation(name, declaration["imports"])]
                    field_candidates.append({"name": field.get("name"), "type": field.get("type", "UNKNOWN"),
                                             "annotations": field_annotations,
                                             "line": (field.get("range") or {}).get("start_line") or declaration["line"]})
            for field in field_candidates:
                field_annotations = field["annotations"]
                if not field_annotations or any(_simple(name) == "Transient" for name, _ in field_annotations):
                    continue
                if not any(_simple(name) in JPA_FIELDS for name, _ in field_annotations):
                    continue
                attribute_name = str(field.get("name", ""))
                if attribute_name:
                    seen_decls.setdefault(attribute_name.casefold(), []).append(
                        {"declaration": declaration, "field": field, "annotations": field_annotations,
                         "name": attribute_name, "owner": owner,
                         "line": field.get("line") or declaration["line"]})
        override_map: dict[str, list[tuple[str, str | None, bool]]] = {}
        unknown_class_override = False
        override_declarations = [*inherited_declarations, *(inherited_entity_declarations or []), entity]
        for override_declaration in override_declarations:
            override_owner = str(override_declaration["symbol"].get("owner", ""))
            imports = override_declaration["imports"]
            for annotation in override_declaration["symbol"].get("annotations", []):
                if not isinstance(annotation, dict) or not isinstance(annotation.get("name"), str):
                    continue
                name = annotation["name"]
                if _simple(name) != "AttributeOverride" or not _allowed_jpa_annotation(name, imports):
                    continue
                unknown_class_override |= annotation.get("values_resolved") is False
                values = annotation.get("values") if isinstance(annotation.get("values"), dict) else {}
                attribute_name = values.get("name")
                if not isinstance(attribute_name, str) or not attribute_name:
                    continue
                nested = values.get("column")
                column_name = None
                unresolved = annotation.get("values_resolved") is False
                if isinstance(nested, dict):
                    nested_name = nested.get("name")
                    nested_values = nested.get("values") if isinstance(nested.get("values"), dict) else {}
                    if not isinstance(nested_name, str) or not _allowed_jpa_annotation(nested_name, imports):
                        continue
                    nested_column = nested_values.get("name") or nested_values.get("value")
                    column_name = nested_column if isinstance(nested_column, str) and nested_column else None
                    unresolved = unresolved or nested.get("values_resolved") is False
                else:
                    unresolved = True
                override_map.setdefault(attribute_name.casefold(), []).append((override_owner, column_name, unresolved))
        for normalized, candidates in seen_decls.items():
            attribute_name = candidates[0]["name"]
            existing = entity_attributes.get(effective_owner, {}).get(normalized)
            if existing or len(candidates) != 1:
                for identity in ([existing] if existing else []):
                    if identity in nodes:
                        nodes[identity] = replace(nodes[identity], metadata={**(nodes[identity].metadata or {}),
                                                                              "mapping_status": "UNKNOWN"})
                        removed_columns = set()
                        for edge_key, edge in list(edges.items()):
                            if edge.source == identity and edge.kind == "maps_to_column":
                                removed_columns.add(edge.target)
                                edges.pop(edge_key, None)
                        for column in removed_columns:
                            if not any(edge.source == column or edge.target == column for edge in edges.values()):
                                nodes.pop(column, None)
                diagnostics.append({"code": "ORM_INHERITED_ATTRIBUTE_COLLISION", "path": entity["path"],
                                    "source_line": entity["line"], "effective_owner": effective_owner,
                                    "attribute": attribute_name,
                                    "declarations": [item["owner"] for item in candidates],
                                    "reason": "Inherited and declared persistent attributes share a name; no winner is selected."})
                continue
            item = candidates[0]
            declaration = item["declaration"]
            field = item["field"]
            owner = item["owner"]
            field_annotations = item["annotations"]
            args = next((value for name, value in field_annotations if _simple(name) == "Column"), "")
            embedded_id = any(_simple(name) == "EmbeddedId" for name, _ in field_annotations)
            embedded = embedded_id or any(_simple(name) == "Embedded" for name, _ in field_annotations)
            identifier = embedded_id or any(_simple(name) == "Id" for name, _ in field_annotations)
            relation_entry = next(((name, value) for name, value in field_annotations
                                   if _simple(name) in {"ManyToOne", "OneToMany", "OneToOne", "ManyToMany"}), None)
            column_name = _string_arg(args, ("name", "value")) if args else attribute_name
            status = "PARTIAL"
            override_values = override_map.get(normalized, [])
            latest_override_owner = override_values[-1][0] if override_values else None
            selected_overrides = [item for item in override_values if item[0] == latest_override_owner]
            if len(selected_overrides) > 1:
                status, column_name = "UNKNOWN", None
                diagnostics.append({"code": "ORM_ATTRIBUTE_OVERRIDE_AMBIGUOUS", "path": entity["path"],
                                    "source_line": entity["line"], "entity": node.id, "attribute": attribute_name,
                                    "reason": "Multiple class-level @AttributeOverride declarations match; no physical column is selected."})
            elif selected_overrides:
                _, override_column, unresolved = selected_overrides[0]
                if unresolved or override_column is None:
                    status, column_name = "UNKNOWN", None
                    diagnostics.append({"code": "ORM_ATTRIBUTE_OVERRIDE_UNKNOWN", "path": entity["path"],
                                        "source_line": entity["line"], "entity": node.id, "attribute": attribute_name,
                                        "reason": "Explicit @AttributeOverride column is incomplete or unresolved; no fallback is published."})
                else:
                    column_name = override_column
            elif unknown_class_override:
                status, column_name = "UNKNOWN", None
                diagnostics.append({"code": "ORM_ATTRIBUTE_OVERRIDE_UNKNOWN", "path": entity["path"],
                                    "source_line": entity["line"], "entity": node.id,
                                    "attribute": attribute_name,
                                    "reason": "An explicit class-level @AttributeOverride is unresolved; inherited column fallback is omitted."})
            if args == "__UNRESOLVED__":
                status, column_name = "UNKNOWN", None
                diagnostics.append({"code": "ORM_COLUMN_MAPPING_UNKNOWN", "path": declaration["path"],
                                    "source_line": item["line"], "effective_owner": effective_owner,
                                    "attribute": attribute_name,
                                    "reason": "Explicit mapped superclass @Column is unresolved; no physical column is published."})
            declaration_node = add_node("orm_attribute", f"{declaration['node'].name}.{attribute_name}",
                                        declaration["path"], item["line"], declaration["node"],
                                        attribute=attribute_name, type=field.get("type", "UNKNOWN"),
                                        access=access, inherited=False, declaring_owner=owner,
                                        effective_owner=None, identifier=identifier, embedded=embedded,
                                        mapping_status="PARTIAL")
            inherited_attribute = add_node("orm_attribute", f"{node.name}.{attribute_name}", declaration["path"],
                                           item["line"], declaration["node"],
                                           attribute=attribute_name, type=field.get("type", "UNKNOWN"),
                                           access=access, inherited=True, declaring_owner=owner,
                                           effective_owner=effective_owner, identifier=identifier, embedded=embedded,
                                           getter=field.get("name") if access == "PROPERTY" else None,
                                           mapping_status=status,
                                           override=bool(override_values))
            add_edge(inherited_attribute, declaration_node, "inherits_attribute", declaration["path"], item["line"],
                     "Compiler-attributed persistent property projected from its mapped superclass")
            add_edge(node.id, inherited_attribute, "has_persistent_attribute", entity["path"], entity["line"],
                     "Mapped superclass property effective for this entity")
            bind_persistent_attribute(inherited_attribute, owner, field.get("name"), declaration["path"], access=access)
            entity_attributes.setdefault(effective_owner, {})[normalized] = inherited_attribute
            if mapping_table_id:
                add_edge(inherited_attribute, mapping_table_id, "declared_on_table", entity["path"], item["line"],
                         "Effective mapped superclass property on entity table")
            elif status != "UNKNOWN":
                nodes[inherited_attribute] = replace(nodes[inherited_attribute], metadata={**(nodes[inherited_attribute].metadata or {}),
                                                                                          "mapping_status": "UNKNOWN"})
                status = "UNKNOWN"
                column_name = None
            if identifier:
                add_edge(node.id, inherited_attribute, "has_embedded_id" if embedded_id else "has_id",
                         entity["path"], item["line"],
                         "Mapped superclass identifier is effective for this entity")
            if embedded:
                embedded_type = re.findall(r"[A-Za-z_]\w*", str(field.get("type", "")))[-1:]
                embedded_name = embedded_type[0] if embedded_type else ""
                target = embeddable_nodes.get(embedded_name)
                if target:
                    entity_embedded_types[(effective_owner, normalized)] = embedded_name
                    add_edge(inherited_attribute, target, "embeds_type", entity["path"], item["line"],
                             "Mapped superclass embedded attribute")
                else:
                    diagnostics.append({"code": "ORM_EMBEDDABLE_TYPE_UNRESOLVED", "path": entity["path"],
                                        "source_line": item["line"], "attribute": inherited_attribute,
                                        "type": field.get("type")})
                column_name = None
            elif relation_entry:
                relation_name, relation_args = relation_entry
                mapped_by = _named_string_arg(relation_args, "mappedBy")
                target_type = re.findall(r"[A-Za-z_]\w*", str(field.get("type", "")))[-1:]
                target_type = target_type[0] if target_type else "UNKNOWN"
                entity_association_types[(effective_owner, normalized)] = target_type
                association = add_node("orm_association", f"{node.name}.{attribute_name}", entity["path"],
                                       item["line"], node, association=_simple(relation_name),
                                       target_type=target_type, mapped_by=mapped_by,
                                       association_role="INVERSE" if mapped_by else "OWNING", access=access)
                add_edge(inherited_attribute, association, "declares_association", entity["path"], item["line"],
                         f"Mapped superclass JPA relationship @{_simple(relation_name)}")
                association_records.append({"id": association, "owner": node.name, "field": attribute_name,
                                            "target": target_type, "mapped_by": mapped_by,
                                            "path": entity["path"], "line": item["line"]})
                join_entry = next(((name, value) for name, value in field_annotations
                                   if _simple(name) in {"JoinColumn", "JoinTable"}), None)
                join_name = _string_arg(join_entry[1], ("name", "value")) if join_entry else None
                if join_name:
                    join_kind = "orm_join_table" if _simple(join_entry[0]) == "JoinTable" else "orm_column"
                    join_node = add_node(join_kind, join_name, entity["path"], item["line"], node,
                                         logical_name=join_name, inferred=False, join=True)
                    add_edge(association, join_node,
                             "maps_to_join_table" if join_kind == "orm_join_table" else "maps_to_join_column",
                             entity["path"], item["line"], "Explicit mapped superclass join mapping")
                column_name = None
            if column_name:
                column_id = add_node("orm_column", column_name, entity["path"], item["line"], node,
                                     logical_name=column_name, inferred=not bool(args or override_values),
                                     override=bool(override_values), mapping_status=status)
                add_edge(inherited_attribute, column_id, "maps_to_column", entity["path"], item["line"],
                         "Mapped superclass column or entity-level AttributeOverride")
            elif status == "UNKNOWN":
                diagnostics.append({"code": "ORM_INHERITED_COLUMN_UNKNOWN", "path": entity["path"],
                                    "source_line": item["line"], "entity": node.id, "attribute": attribute_name,
                                    "reason": "No physical column is published for unresolved inherited mapping."})

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
            repo_name, declared_model = match.group(1), generic.group(1).rsplit(".", 1)[-1]
            line = _line(source, match.start())
            repo = next((node for node in nodes.values() if node.id in symbols and node.path == path and node.name == repo_name and node.kind in {"class", "interface"}), None)
            repository_symbol = symbols.get(repo.id) if repo else None
            model_owner = repository_entity_owner(repository_symbol)
            model_name = _simple(model_owner) if model_owner else declared_model
            if repo and model_owner:
                model_node = nodes.get(entity_nodes_by_owner[model_owner])
                if model_node:
                    add_edge(repo.id, model_node.id, "repository_for", path, line,
                             "Compiler-resolved Spring Data repository generic entity")
                    repository_owner = str((repository_symbol or {}).get("owner", ""))
                    if repository_owner:
                        repository_models[repository_owner] = model_owner
                else:
                    model_owner = None
            if repo and model_owner is None:
                diagnostics.append({"code": "SPRING_DATA_MODEL_UNRESOLVED", "path": path, "source_line": line,
                                    "repository": repo.id, "model": declared_model,
                                    "reason": "Repository generic does not resolve to exactly one compiler-owned entity; no simple-name fallback is used."})
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
                    method = next((node for node in nodes.values() if node.id in symbols and node.path == path and node.kind == "method" and node.name == method_name), None)
                    if method is None:
                        continue
                    query_line = line + body[:derived.start()].count("\n")
                    resolved_predicates = []
                    unresolved_predicates = []
                    for predicate in parsed["predicates"]:
                        target, resolved_path = resolve_query_property(model_owner or "", predicate["property"])
                        value = {**predicate, "resolved_path": resolved_path, "attribute_id": target}
                        resolved_predicates.append(value)
                        if target is None:
                            unresolved_predicates.append(predicate["property"])
                    resolved_orders = []
                    for order in parsed["order_by"]:
                        target, resolved_path = resolve_query_property(model_owner or "", order["property"])
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
                    entity_id = entity_nodes_by_owner.get(model_owner or "")
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

    type_nodes_by_owner: dict[str, Node] = {}
    for symbol in symbols.values():
        symbol_node_value = nodes.get(str(symbol.get("id", "")))
        owner = symbol.get("owner")
        if symbol_node_value is None or symbol_node_value.kind not in {"class", "interface", "type"} \
                or not isinstance(owner, str) or not owner:
            continue
        type_nodes_by_owner[owner.replace("$", ".")] = symbol_node_value

    def descriptor_return_owner(descriptor: Any) -> str | None:
        if not isinstance(descriptor, str):
            return None
        match = re.search(r"\)(?:\[*)L([^;<]+);$", descriptor)
        return match.group(1).replace("/", ".").replace("$", ".") if match else None

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
        projection_type_ref = return_parts[-1].replace("$", ".") if return_parts else None
        projection_type = _simple(projection_type_ref) if projection_type_ref else None
        projection_node = type_nodes_by_owner.get(projection_type_ref or "")
        return_owner = descriptor_return_owner(item.get("descriptor"))
        if (projection_node is None and return_owner and projection_type
                and _simple(return_owner) == projection_type):
            # A source-level simple name does not prove its owner. The compiler
            # method descriptor does: use its exact erased class identity only
            # when it agrees with the declared return type's simple name. This
            # also keeps type variables (whose erasure is Object) from binding
            # to an unrelated local class with the same name.
            projection_node = type_nodes_by_owner.get(return_owner)
        model_owner = repository_models[str(item.get("owner"))]
        model_name = _simple(model_owner)
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
            if projection_node:
                projection_owner = next((owner for owner, node_id in entity_nodes_by_owner.items()
                                         if node_id == projection_node.id), None)
                add_edge(query_id, projection_node.id,
                         "returns_entity" if projection_owner is not None else "returns_projection",
                         path, line, "Compiler-qualified return type of repository query")
            else:
                diagnostics.append({"code": "SPRING_DATA_QUERY_PROJECTION_UNRESOLVED", "path": path,
                                    "source_line": line, "method": method.id, "projection_type": projection_type_ref})
                query_node = nodes.get(query_id)
                if query_node:
                    nodes[query_id] = replace(query_node, metadata={**(query_node.metadata or {}), "validated": False})
        query_lower = value.lstrip().casefold()
        action = "query_deletes" if query_lower.startswith("delete") else "query_writes" if query_lower.startswith(("update", "insert")) else "query_reads"
        if language == "JPQL":
            entity_match = re.search(r"\b(?:from|update)\s+([\w.$]+)(?:\s+(?:as\s+)?([A-Za-z_]\w*))?", value, re.I)
            query_entity = entity_match.group(1).replace("$", ".") if entity_match else None
            alias = entity_match.group(2) if entity_match else None
            query_owners = entity_query_owners.get(query_entity or "", [])
            query_owner = query_owners[0] if len(query_owners) == 1 else None
            entity_id = entity_nodes_by_owner.get(query_owner or "")
            if entity_id:
                add_edge(query_id, entity_id, action, path, line, "JPQL entity resolved against compiler JPA model")
            else:
                diagnostics.append({"code": "JPQL_ENTITY_UNRESOLVED", "path": path, "source_line": line,
                                    "method": method.id, "entity": query_entity or "UNKNOWN",
                                    "candidates": query_owners,
                                    "reason": "JPQL entity name must resolve to exactly one compiler-owned JPA entity; repository generic owner is not used as a fallback."})
                current_query = nodes.get(query_id)
                if current_query:
                    nodes[query_id] = replace(current_query, metadata={**(current_query.metadata or {}), "validated": False})
            if alias:
                for attribute_path in sorted(set(re.findall(rf"\b{re.escape(alias)}\.([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)", value))):
                    property_name = "".join(part[:1].upper() + part[1:] if index else part
                                            for index, part in enumerate(attribute_path.split(".")))
                    target, resolved_path = resolve_query_property(query_owner or "", property_name)
                    if target:
                        add_edge(query_id, target, "filters_by", path, line,
                                 f"JPQL path {resolved_path} resolved against entity model")
                    else:
                        diagnostics.append({"code": "JPQL_ATTRIBUTE_UNRESOLVED", "path": path,
                                            "source_line": line, "method": method.id, "attribute": attribute_path})
                        current_query = nodes.get(query_id)
                        if current_query:
                            nodes[query_id] = replace(current_query, metadata={**(current_query.metadata or {}), "validated": False})
        else:
            tables = sorted(set(re.findall(r"\b(?:from|join|update|into)\s+([A-Za-z_][\w.$]*)", value, re.I)))
            for table_name in tables:
                query_parts = table_name.split('.')
                query_schema = query_parts[0] if len(query_parts) == 2 else None
                matches = [candidate for candidate in nodes.values() if candidate.kind == "orm_table"
                           and (candidate.metadata or {}).get('context_id') == context_id
                           and len(query_parts) <= 2
                           and _sql_identifier((candidate.metadata or {}).get("logical_name", candidate.name)) == _sql_identifier(query_parts[-1])
                           and (query_schema is None or _sql_identifier((candidate.metadata or {}).get('schema')) == _sql_identifier(query_schema))]
                if len(matches) == 1:
                    add_edge(query_id, matches[0].id, action, path, line,
                             "Native SQL exact table name in selected ORM projection")
                else:
                    diagnostics.append({"code": "NATIVE_QUERY_TABLE_UNRESOLVED" if not matches else "NATIVE_QUERY_TABLE_AMBIGUOUS",
                                        "path": path, "source_line": line, "method": method.id,
                                        "table": table_name, "candidates": [candidate.id for candidate in matches]})

    # A proxy-eligible path needs all of: an external compiler call, one active
    # Spring injection, one active compatible policy and an interceptable
    # declaration.  It is still a may-edge with execution NOT_OBSERVED.
    advice_edges = [edge for edge in edges.values() if edge.kind == "advised_by"
                    and nodes.get(edge.target) is not None and nodes[edge.target].kind == "spring_advice"]
    advice_by_method: dict[str, list[str]] = {}
    for edge in advice_edges:
        advice_by_method.setdefault(edge.source, []).append(edge.target)
    bean_records = {bean["bean"]: bean for bean in spring_beans}
    injection_edges = [edge for edge in edges.values() if edge.kind == "injects_bean"
                       and nodes.get(edge.source) is not None and nodes[edge.source].kind == "spring_injection"]

    def unresolved_proxy(site: dict[str, Any], target: Node, reason: str, code: str) -> None:
        boundary = add_node("spring_proxy_boundary", f"proxy-unresolved:{target.name}", target.path, target.line,
                            target, declaration_identity=str(site.get("id")), proxy_traversal=None,
                            boundary_kind="PROXY_RESOLUTION", reason=reason,
                            execution="NOT_OBSERVED", availability="UNKNOWN")
        add_edge(str(site.get("id")), boundary, "proxy_resolution_unknown", target.path, target.line,
                 "Proxy advice application remains UNKNOWN: " + reason)
        diagnostics.append({"code": code, "path": target.path, "source_line": target.line,
                            "call_site": site.get("id"), "target": target.id, "reason": reason})

    for site in graph.call_sites:
        caller_symbol = symbols.get(site.get("caller"))
        if caller_symbol is None or site.get("id") not in nodes:
            continue
        candidate_ids = [site.get("declared_target"), *site.get("dispatch_candidates", [])]
        candidates = list(dict.fromkeys(identity for identity in candidate_ids if identity in advice_by_method))
        if not candidates:
            continue
        if len(candidates) != 1:
            target = nodes.get(candidates[0])
            if target is not None:
                unresolved_proxy(site, target, "multiple advised dispatch candidates", "SPRING_PROXY_TARGET_AMBIGUOUS")
            continue
        target = nodes.get(candidates[0])
        target_symbol = symbols.get(candidates[0], {})
        if target is None:
            continue
        caller_owner, target_owner = caller_symbol.get("owner"), target_symbol.get("owner")
        if caller_owner == target_owner:
            advice_names = {(nodes[identity].metadata or {}).get("advice")
                            for identity in advice_by_method[target.id]}
            boundary = add_node("spring_proxy_boundary", f"self-invocation:{target.name}", target.path,
                                target.line, target, declaration_identity=str(site.get("id")),
                                proxy_traversal=False, boundary_kind="SELF_INVOCATION",
                                continuation="SYNCHRONOUS", async_scheduled=False,
                                reason="same-owner invocation bypasses external proxy",
                                execution="NOT_OBSERVED", availability="UNKNOWN")
            add_edge(site["id"], boundary, "bypasses_proxy", target.path, target.line,
                     "Same-class call to advised method bypasses an external Spring proxy")
            diagnostics.append({"code": "SPRING_SELF_INVOCATION_PROXY_BOUNDARY", "path": target.path,
                                "source_line": target.line, "call_site": site["id"], "target": target.id,
                                "async_scheduled": False if "Async" in advice_names else None})
            continue

        selected_injections = []
        declared_symbol = symbols.get(site.get("declared_target"), {})
        receiver_type = _simple(str(declared_symbol.get("owner", "")))
        for injection_edge in injection_edges:
            injection = nodes[injection_edge.source]
            metadata = injection.metadata or {}
            bean = bean_records.get(injection_edge.target)
            if metadata.get("owner") != caller_owner or bean is None or bean.get("condition_status") != "ACTIVE":
                continue
            target_type = _simple(str(target_owner or ""))
            if metadata.get("type") == receiver_type and (target_type in bean.get("types", [])
                    or receiver_type in bean.get("types", [])):
                selected_injections.append((injection, bean))
        if len(selected_injections) != 1:
            unresolved_proxy(site, target, "proxy receiver does not map to one active injected bean",
                             "SPRING_PROXY_RECEIVER_UNRESOLVED")
            continue
        injection, bean = selected_injections[0]
        bean_symbol = symbols.get(bean["node"].id, {})
        bean_owner = str(bean_symbol.get("owner", ""))

        advice_groups: dict[str, list[str]] = {}
        for advice_id in advice_by_method[target.id]:
            advice_name = (nodes[advice_id].metadata or {}).get("advice")
            policy_kind = SPRING_ADVICE_POLICIES.get(str(advice_name))
            if policy_kind:
                advice_groups.setdefault(policy_kind, []).append(advice_id)
        for policy_kind, advice_ids in advice_groups.items():
            if not advice_ids:
                continue
            policies = [policy for policy in spring_proxy_policies
                        if policy["kind"] == policy_kind and policy["status"] == "ACTIVE"]
            strategies = {policy["strategy"] for policy in policies}
            if len(strategies) != 1:
                unresolved_proxy(site, target, "no unique active " + policy_kind + " proxy strategy",
                                 "SPRING_PROXY_POLICY_UNRESOLVED")
                continue
            strategy = next(iter(strategies))
            injection_type = str((injection.metadata or {}).get("type", ""))
            target_modifiers = set(target_symbol.get("modifiers", []))
            bean_modifiers = set(bean_symbol.get("modifiers", []))
            if strategy == "JDK_DYNAMIC":
                interface_owners = [owner for owner, record in type_records.items()
                                    if record["symbol"].get("kind") == "interface"
                                    and record["symbol"].get("name") == injection_type]
                eligible = (len(interface_owners) == 1 and injection_type in bean.get("types", [])
                            and "public" in target_modifiers)
                reason = "JDK proxy requires one injected compiler interface and a public advised method"
            else:
                eligible = (target_owner == bean_owner and "final" not in bean_modifiers
                            and not ({"final", "private", "static"} & target_modifiers)
                            and bool({"public", "protected"} & target_modifiers))
                reason = "CGLIB proxy requires an injected non-final bean and an interceptable class method"
            if not eligible:
                unresolved_proxy(site, target, reason, "SPRING_PROXY_METHOD_UNSUPPORTED")
                continue
            proxy_path = add_node("spring_proxy_path", f"{strategy}:{target.name}", target.path, target.line,
                                  target, declaration_identity=f"{site['id']}:{policy_kind}:{strategy}",
                                  call_site=site["id"], target=target.id, bean=bean["bean"],
                                  injection=injection.id, policy_kind=policy_kind,
                                  mode="PROXY", strategy=strategy, eligibility="SUPPORTED",
                                  execution="NOT_OBSERVED", availability="UNKNOWN")
            add_edge(site["id"], proxy_path, "may_traverse_proxy", target.path, target.line,
                     "Compiler call plus unique active injection and explicit compatible proxy policy",
                     compiler_fact=site)
            for policy in policies:
                add_edge(policy["node"], proxy_path, "governs_proxy_path", policy["path"], policy["line"],
                         "Active compiler-resolved proxy policy")
            for advice_id in advice_ids:
                add_edge(proxy_path, advice_id, "may_apply_advice", target.path, target.line,
                         "Advice is eligible only through this evidenced proxy path; execution is not observed")
            if policy_kind == "ASYNC":
                async_boundaries = [edge.target for edge in edges.values()
                                    if edge.source == target.id and edge.kind == "declares_async_transition"]
                for boundary in async_boundaries:
                    add_edge(proxy_path, boundary, "crosses_async_boundary", target.path, target.line,
                             "Eligible @Async proxy path separates caller continuation from task execution")

    # ORM XML is an explicit, root-confined mapping input. Apply it after the
    # existing annotation projection so the same ORM entities/attributes are
    # updated in place and XML never creates a parallel persistence catalog.
    jpa_rule_metadata = {"jpa_rule_version": JPA_RULE_VERSION}

    def remove_attribute_columns(attribute_id: str) -> None:
        removed: set[str] = set()
        for key, edge in list(edges.items()):
            if edge.source == attribute_id and edge.kind == "maps_to_column":
                removed.add(edge.target)
                edges.pop(key, None)
        for column_id in removed:
            # A mapped-superclass column node can be shared by several
            # effective entity attributes. Detach only this owner's edge;
            # erase the physical node and its schema links once no attribute
            # mapping still refers to it.
            if any(edge.kind == "maps_to_column" and edge.target == column_id
                   for edge in edges.values()):
                continue
            for key, edge in list(edges.items()):
                if edge.source == column_id or edge.target == column_id:
                    edges.pop(key, None)
            if not any(edge.source == column_id or edge.target == column_id for edge in edges.values()):
                nodes.pop(column_id, None)

    def remove_entity_tables(entity_id: str) -> list[str]:
        table_ids = []
        for key, edge in list(edges.items()):
            if edge.source == entity_id and edge.kind == "maps_to_table":
                table_ids.append(edge.target)
                edges.pop(key, None)
        for table_id in table_ids:
            for key, edge in list(edges.items()):
                if edge.source == table_id or edge.target == table_id:
                    edges.pop(key, None)
            if not any(edge.source == table_id or edge.target == table_id for edge in edges.values()):
                nodes.pop(table_id, None)
        return table_ids

    def entity_attribute_targets(owner: str, attribute_name: str, class_kind: str) -> list[str]:
        type_record = type_records.get(owner)
        symbol = type_record["symbol"] if type_record else {}
        simple_name = str(symbol.get("name") or _simple(owner))
        source_path = symbol.get("path")
        result = []
        for candidate in nodes.values():
            if candidate.kind != "orm_attribute" or (candidate.metadata or {}).get("context_id") != context_id \
                    or (candidate.metadata or {}).get("attribute") != attribute_name:
                continue
            metadata = candidate.metadata or {}
            if class_kind == "entity":
                if metadata.get("effective_owner") == owner or (
                        metadata.get("effective_owner") is None and candidate.path == source_path
                        and candidate.name == f"{simple_name}.{attribute_name}"):
                    result.append(candidate.id)
            elif class_kind == "mapped-superclass":
                if metadata.get("declaring_owner") == owner:
                    result.append(candidate.id)
                elif metadata.get("effective_owner") is None and candidate.path == source_path and candidate.name == f"{simple_name}.{attribute_name}":
                    result.append(candidate.id)
        return sorted(set(result))

    def xml_unknown(owner: str, record: dict[str, Any] | None, reason: str) -> None:
        declaration = entity_decls_by_owner.get(owner) or mapped_superclasses_by_owner.get(owner)
        if not declaration:
            return
        entity_id = declaration["node"].id
        if owner in entity_decls_by_owner:
            for table_id in remove_entity_tables(entity_id):
                nodes.pop(table_id, None)
        attribute_ids = set(entity_attributes.get(owner, {}).values())
        attribute_ids.update(candidate.id for candidate in nodes.values()
                             if candidate.kind == "orm_attribute"
                             and (candidate.metadata or {}).get("context_id") == context_id
                             and ((candidate.metadata or {}).get("effective_owner") == owner
                                  or (candidate.metadata or {}).get("declaring_owner") == owner))
        for attribute_id in attribute_ids:
            current = nodes.get(attribute_id)
            if current is None:
                continue
            remove_attribute_columns(attribute_id)
            metadata = {**(current.metadata or {}), "mapping_status": "UNKNOWN",
                        "mapping_source": "ORM_XML_UNKNOWN", **jpa_rule_metadata}
            if record:
                metadata.update(record.get("provenance", {}))
            nodes[attribute_id] = replace(current, metadata=metadata)
        symbol = declaration["symbol"]
        source_path = declaration["path"]
        prefix = declaration["node"].name + "."
        for candidate in list(nodes.values()):
            if candidate.kind not in {"orm_association", "orm_named_query", "orm_attribute_override"} \
                    or (candidate.metadata or {}).get("context_id") != context_id \
                    or candidate.path != source_path or not candidate.name.startswith(prefix):
                continue
            for key, edge in list(edges.items()):
                if edge.source == candidate.id or edge.target == candidate.id:
                    edges.pop(key, None)
                    if edge.target in nodes and nodes[edge.target].kind in {"orm_column", "orm_join_table"}:
                        target = edge.target
                        if not any(item.source == target or item.target == target for item in edges.values()):
                            nodes.pop(target, None)
            nodes.pop(candidate.id, None)
        diagnostics.append({"code": "ORM_XML_MAPPING_UNKNOWN",
                            "path": (record or {}).get("provenance", {}).get("xml_mapping_file"),
                            "class": owner, "reason": reason})

    def apply_xml_column(attribute_id: str, owner: str, attribute_name: str,
                         spec: dict[str, Any], record: dict[str, Any], *, override: bool) -> None:
        current = nodes.get(attribute_id)
        provenance = spec.get("provenance") or record.get("provenance", {})
        if current is None:
            return
        if spec.get("ambiguous"):
            remove_attribute_columns(attribute_id)
            nodes[attribute_id] = replace(current, metadata={**(current.metadata or {}),
                "mapping_status": "UNKNOWN", "mapping_source": "ORM_XML", **provenance,
                **jpa_rule_metadata})
            diagnostics.append({"code": "ORM_XML_ATTRIBUTE_AMBIGUOUS", "path": provenance.get("xml_mapping_file"),
                                "class": owner, "attribute": attribute_name,
                                "reason": "Conflicting XML attribute mappings have the same declared mapping-file order."})
            return
        if not spec.get("column_present") and override:
            remove_attribute_columns(attribute_id)
            nodes[attribute_id] = replace(current, metadata={**(current.metadata or {}),
                "mapping_status": "UNKNOWN", "mapping_source": "ORM_XML", **provenance,
                **jpa_rule_metadata})
            diagnostics.append({"code": "ORM_XML_COLUMN_UNKNOWN", "path": provenance.get("xml_mapping_file"),
                                "class": owner, "attribute": attribute_name,
                                "reason": "Explicit XML attribute override has no complete nested column mapping."})
            return
        column_name = spec.get("column") if spec.get("column_present") else attribute_name
        if not isinstance(column_name, str) or not column_name.strip():
            remove_attribute_columns(attribute_id)
            nodes[attribute_id] = replace(current, metadata={**(current.metadata or {}),
                "mapping_status": "UNKNOWN", "mapping_source": "ORM_XML", **provenance,
                **jpa_rule_metadata})
            diagnostics.append({"code": "ORM_XML_COLUMN_UNKNOWN", "path": provenance.get("xml_mapping_file"),
                                "class": owner, "attribute": attribute_name,
                                "reason": "XML column name is explicitly empty or unresolved; annotation fallback is suppressed."})
            return
        remove_attribute_columns(attribute_id)
        mapping_status = "PARTIAL"
        nodes[attribute_id] = replace(current, metadata={**(current.metadata or {}),
            "mapping_status": mapping_status, "mapping_source": "ORM_XML", "xml_override": override,
            "column_name": column_name, "inferred_column": not bool(spec.get("column_present")),
            **provenance, **jpa_rule_metadata})
        column_id = add_node("orm_column", column_name, provenance["xml_mapping_file"], None,
                             symbol_node(type_records[owner]["symbol"]),
                             logical_name=column_name, inferred=not bool(spec.get("column_present")),
                             override=override, mapping_source="ORM_XML", mapping_status=mapping_status,
                             **provenance, **jpa_rule_metadata)
        add_edge(attribute_id, column_id, "maps_to_column", provenance["xml_mapping_file"], None,
                 "ORM XML mapping overrides annotation metadata" if override else "ORM XML attribute mapping",
                 xml_provenance=provenance)

    if jpa_xml["global_unknown"]:
        for owner in list(entity_decls_by_owner):
            xml_unknown(owner, jpa_xml["classes"].get(owner),
                        "Selected persistence XML scope is incomplete or unsupported; annotation physical bindings are suppressed.")
    else:
        if jpa_xml["metadata_complete"] or jpa_xml.get("exclude_unlisted"):
            for owner in list(entity_decls_by_owner):
                excluded_by_xml = (jpa_xml["metadata_complete"] and owner not in jpa_xml["classes"])
                excluded_by_persistence = (jpa_xml.get("exclude_unlisted") and owner not in jpa_xml["classes"]
                                           and owner not in jpa_xml.get("listed_classes", []))
                if excluded_by_xml or excluded_by_persistence:
                    declaration = entity_decls_by_owner[owner]
                    remove_entity_tables(declaration["node"].id)
                    attribute_ids = set(entity_attributes.get(owner, {}).values())
                    attribute_ids.update(candidate.id for candidate in nodes.values()
                                         if candidate.kind == "orm_attribute"
                                         and (candidate.metadata or {}).get("context_id") == context_id
                                         and (candidate.metadata or {}).get("effective_owner") == owner)
                    for attribute_id in attribute_ids:
                        remove_attribute_columns(attribute_id)
                        for key, edge in list(edges.items()):
                            if edge.source == attribute_id or edge.target == attribute_id:
                                edges.pop(key, None)
                        nodes.pop(attribute_id, None)
                    for candidate in list(nodes.values()):
                        if candidate.kind in {"orm_association", "orm_named_query", "orm_attribute_override"} \
                                and (candidate.metadata or {}).get("context_id") == context_id \
                                and candidate.path == declaration["path"] \
                                and candidate.name.startswith(declaration["node"].name + "."):
                            for key, edge in list(edges.items()):
                                if edge.source == candidate.id or edge.target == candidate.id:
                                    edges.pop(key, None)
                            nodes.pop(candidate.id, None)
                    diagnostics.append({"code": "ORM_XML_METADATA_COMPLETE_CLASS_UNMAPPED",
                                        "path": jpa_xml.get("descriptor_path"), "class": owner,
                                        "reason": ("Complete XML metadata contains no entity mapping for this annotated class; annotation mapping is ignored."
                                                    if excluded_by_xml else
                                                    "The selected persistence unit excludes this unlisted class; annotation mapping is ignored.")})
            for owner in list(mapped_superclasses_by_owner):
                excluded_mapped = (jpa_xml["metadata_complete"] and owner not in jpa_xml["classes"])
                excluded_mapped |= (jpa_xml.get("exclude_unlisted") and owner not in jpa_xml["classes"]
                                    and owner not in jpa_xml.get("listed_classes", []))
                if excluded_mapped:
                    xml_unknown(owner, None,
                                "Selected XML persistence-unit metadata excludes this mapped superclass; annotation inheritance is suppressed.")
        for owner, record in jpa_xml["classes"].items():
            declaration = entity_decls_by_owner.get(owner) or mapped_superclasses_by_owner.get(owner)
            if declaration is None:
                diagnostics.append({"code": "ORM_XML_CLASS_KIND_UNSUPPORTED",
                                    "path": record.get("provenance", {}).get("xml_mapping_file"),
                                    "class": owner,
                                    "reason": "This XML mapping kind has no matching compiler-resolved entity projection in the selected subset."})
                continue
            if record.get("unknown"):
                xml_unknown(owner, record, "The XML class mapping contains an unsupported or ambiguous construct; annotation fallback is suppressed.")
                continue
            entity_id = declaration["node"].id
            xml_table = record.get("table")
            if record["kind"] != "entity" and xml_table is not None:
                xml_unknown(owner, record, "A table mapping is not valid for this XML class kind; annotation fallback is suppressed.")
                continue
            if record.get("access") in {"FIELD", "PROPERTY"} and record["kind"] == "entity":
                current_access = next(((nodes.get(edge.target).metadata or {}).get("access_strategy")
                                       for edge in edges.values() if edge.source == entity_id
                                       and edge.kind == "maps_to_table" and nodes.get(edge.target)), None)
                if current_access in {"FIELD", "PROPERTY"} and current_access != record["access"]:
                    diagnostics.append({"code": "ORM_XML_ACCESS_OVERRIDE_UNSUPPORTED",
                                        "path": record.get("provenance", {}).get("xml_mapping_file"),
                                        "class": owner, "annotation_access": current_access,
                                        "xml_access": record["access"],
                                        "reason": "XML changes the annotated access target; this subset does not rebind compiler properties across access modes."})
                    xml_unknown(owner, record, "Conflicting XML access override cannot reuse the annotated property identity safely.")
                    continue
            if record["kind"] == "entity" and (record.get("metadata_complete") or xml_table is not None
                                                  or record.get("inheritance_strategy") is not None):
                table_spec = xml_table or {"name": declaration["node"].name, "schema": None,
                                           "catalog": None, "provenance": record.get("provenance", {})}
                table_name = table_spec.get("name")
                table_schema = table_spec.get("schema")
                provenance = table_spec.get("provenance") or record.get("provenance", {})
                if (not isinstance(table_name, str) or not table_name.strip()
                        or table_spec.get("catalog")):
                    xml_unknown(owner, record, "XML table mapping is incomplete or uses an unsupported catalog; no annotation table fallback is allowed.")
                    continue
                prior_table_nodes = [nodes[edge.target] for edge in edges.values()
                                     if edge.source == entity_id and edge.kind == "maps_to_table"
                                     and edge.target in nodes]
                prior_table_metadata = (prior_table_nodes[0].metadata or {}) if len(prior_table_nodes) == 1 else {}
                old_tables = remove_entity_tables(entity_id)
                qualified = f"{table_schema}.{table_name}" if table_schema else table_name
                table_id = add_node("orm_table", qualified, provenance["xml_mapping_file"], None,
                                    declaration["node"], logical_name=table_name, schema=table_schema,
                                    catalog=None, inferred=xml_table is None,
                                    mapping_source="ORM_XML", mapping_status="PARTIAL",
                                    access_strategy=("UNKNOWN" if record.get("metadata_complete") else
                                                     prior_table_metadata.get("access_strategy")),
                                    inheritance_strategy=(record.get("inheritance_strategy") or
                                                          prior_table_metadata.get("inheritance_strategy", "UNKNOWN")),
                                    database_id=context.get("database_id"),
                                    schema_stream_id=context.get("schema_stream_id"),
                                    naming_strategy=context.get("naming_strategy"),
                                    metadata_complete=bool(record.get("metadata_complete")),
                                    **provenance, **jpa_rule_metadata)
                add_edge(entity_id, table_id, "maps_to_table", provenance["xml_mapping_file"], None,
                         "ORM XML table mapping overrides annotation metadata" if xml_table else
                         "JPA default table name under complete XML metadata",
                         xml_provenance=provenance)
                entity_table_by_owner[owner] = table_id
                entity_table_nodes[declaration["node"].name] = table_id
                for old_table in old_tables:
                    for key, edge in list(edges.items()):
                        if edge.target == old_table and edge.kind == "declared_on_table":
                            edges.pop(key, None)
                            add_edge(edge.source, table_id, "declared_on_table", provenance["xml_mapping_file"], None,
                                     "Effective attribute belongs to ORM XML mapped table", xml_provenance=provenance)
                        elif edge.target == old_table and edge.kind not in {"maps_to_table", "resolves_to_schema_table"}:
                            edges.pop(key, None)
                            diagnostics.append({"code": "ORM_XML_TABLE_REFERENCE_UNRESOLVED",
                                                "path": provenance["xml_mapping_file"], "class": owner,
                                                "reason": "Existing query/table reference was invalidated by an XML table override."})
                if xml_table is not None:
                    matches = [candidate for candidate in schema_tables if schema_table_matches(candidate, table_name, table_schema)]
                    if len(matches) == 1:
                        add_edge(table_id, matches[0].id, "resolves_to_schema_table",
                                 provenance["xml_mapping_file"], None,
                                 "Exact XML table name in selected schema realm", xml_provenance=provenance)
                    else:
                        diagnostics.append({"code": "ORM_SCHEMA_TABLE_UNRESOLVED" if not matches else "ORM_SCHEMA_TABLE_AMBIGUOUS",
                                            "path": provenance["xml_mapping_file"], "entity": entity_id,
                                            "table": qualified, "candidates": [item.id for item in matches],
                                            "reason": "XML table has no unique exact schema binding in the selected realm."})
                simple_name = declaration["node"].name
                class_path = declaration["path"]
                for attr in [candidate for candidate in nodes.values() if candidate.kind == "orm_attribute"
                and (candidate.metadata or {}).get("context_id") == context_id]:
                    metadata = attr.metadata or {}
                    belongs = (metadata.get("effective_owner") == owner or
                               attr.path == class_path and attr.name.startswith(simple_name + "."))
                    if belongs and not any(edge.source == attr.id and edge.kind == "declared_on_table"
                                           and edge.target == table_id for edge in edges.values()):
                        add_edge(attr.id, table_id, "declared_on_table", provenance["xml_mapping_file"], None,
                                 "Persistent attribute belongs to the XML mapped table", xml_provenance=provenance)

            xml_attributes = record.get("attributes", {})
            xml_overrides = record.get("overrides", {})
            selected_names = set(xml_attributes) | set(xml_overrides)
            if record.get("metadata_complete"):
                current_attribute_ids = set(entity_attributes.get(owner, {}).values())
                current_attribute_ids.update(candidate.id for candidate in nodes.values()
                                             if candidate.kind == "orm_attribute"
                                             and (candidate.metadata or {}).get("context_id") == context_id
                                             and ((candidate.metadata or {}).get("effective_owner") == owner
                                                  or (candidate.metadata or {}).get("declaring_owner") == owner))
                for attribute_id in current_attribute_ids:
                    current = nodes.get(attribute_id)
                    if current is None:
                        continue
                    attr_name = str((current.metadata or {}).get("attribute", ""))
                    if attr_name not in selected_names:
                        remove_attribute_columns(attribute_id)
                        nodes[attribute_id] = replace(current, metadata={**(current.metadata or {}),
                            "mapping_status": "UNKNOWN", "mapping_source": "ORM_XML_METADATA_COMPLETE",
                            **record.get("provenance", {}), **jpa_rule_metadata})
                        diagnostics.append({"code": "ORM_XML_ATTRIBUTE_UNMAPPED",
                                            "path": record.get("provenance", {}).get("xml_mapping_file"),
                                            "class": owner, "attribute": attr_name,
                                            "reason": "Complete XML metadata has no mapping for this compiler attribute; annotation fallback is suppressed."})
            for attribute_name, spec in xml_attributes.items():
                if spec.get("kind") not in {"id", "embedded-id", "basic", "version"}:
                    attribute_ids = entity_attribute_targets(owner, attribute_name, record["kind"])
                    for attribute_id in attribute_ids:
                        remove_attribute_columns(attribute_id)
                        nodes[attribute_id] = replace(nodes[attribute_id], metadata={**(nodes[attribute_id].metadata or {}),
                            "mapping_status": "UNKNOWN", "mapping_source": "ORM_XML", **spec.get("provenance", {}),
                            **jpa_rule_metadata})
                    diagnostics.append({"code": "ORM_XML_ATTRIBUTE_KIND_UNSUPPORTED",
                                        "path": spec.get("provenance", {}).get("xml_mapping_file"),
                                        "class": owner, "attribute": attribute_name, "kind": spec.get("kind"),
                                        "reason": "Association or embedded XML mapping is outside the scalar column projection subset."})
                    continue
                attribute_ids = entity_attribute_targets(owner, attribute_name, record["kind"])
                if not attribute_ids:
                    symbol = type_records[owner]["symbol"]
                    fields = [item for item in symbols.values()
                              if item.get("kind") == "field" and item.get("owner") == owner
                              and item.get("name") == attribute_name]
                    getters = [item for item in symbols.values() if item.get("kind") == "method"
                               and item.get("owner") == owner
                               and re.fullmatch(r"(?:get|is)[A-Z].*", str(item.get("name", "")))
                               and ((str(item.get("name", ""))[3:] if str(item.get("name", "")).startswith("get")
                                     else str(item.get("name", ""))[2:]).casefold() == attribute_name.casefold())]
                    access = record.get("access")
                    selected_member = None
                    if not str(symbol.get("path", "")).endswith(".kt"):
                        if access == "FIELD" and len(fields) == 1:
                            selected_member = (fields[0], "FIELD", None)
                        elif access == "PROPERTY" and len(getters) == 1:
                            selected_member = (getters[0], "PROPERTY", str(getters[0].get("name")))
                        elif access is None and len(fields) == 1 and not getters:
                            selected_member = (fields[0], "FIELD", None)
                        elif access is None and len(getters) == 1 and not fields:
                            selected_member = (getters[0], "PROPERTY", str(getters[0].get("name")))
                    if selected_member is None:
                        diagnostics.append({"code": "ORM_XML_ATTRIBUTE_UNRESOLVED",
                                            "path": spec.get("provenance", {}).get("xml_mapping_file"),
                                            "class": owner, "attribute": attribute_name,
                                            "reason": "XML attribute does not identify one supported compiler member/access target; no fallback binding is published."})
                        continue
                    field, access, getter_name = selected_member
                    is_id = spec.get("kind") in {"id", "embedded-id"}
                    attribute_id = add_node("orm_attribute", f"{declaration['node'].name}.{attribute_name}",
                                            symbol["path"], (field.get("range") or {}).get("start_line"),
                                            declaration["node"], attribute=attribute_name,
                                            type=field.get("type") if access == "FIELD" else field.get("return_type", "UNKNOWN"),
                                            access=access, getter=getter_name,
                                            identifier=is_id, embedded=spec.get("kind") == "embedded-id",
                                            mapping_status="PARTIAL", mapping_source="ORM_XML",
                                            declaring_owner=owner, effective_owner=owner, inherited=False,
                                            **spec.get("provenance", {}), **jpa_rule_metadata)
                    entity_attributes.setdefault(owner, {})[attribute_name.casefold()] = attribute_id
                    attribute_ids = [attribute_id]
                    if is_id:
                        add_edge(entity_id, attribute_id, "has_embedded_id" if spec.get("kind") == "embedded-id" else "has_id",
                                 spec["provenance"]["xml_mapping_file"], None,
                                 "Compiler field identity mapped by JPA ORM XML", xml_provenance=spec["provenance"])
                    table_edges = [edge for edge in edges.values() if edge.source == entity_id and edge.kind == "maps_to_table"]
                    if table_edges:
                        add_edge(attribute_id, table_edges[0].target, "declared_on_table",
                                 spec["provenance"]["xml_mapping_file"], None,
                                 "XML persistent attribute belongs to mapped table", xml_provenance=spec["provenance"])
                        if is_id and nodes.get(table_edges[0].target):
                            table_node = nodes[table_edges[0].target]
                            nodes[table_node.id] = replace(table_node, metadata={**(table_node.metadata or {}),
                                                                                 "access_strategy": access})
                if not attribute_ids:
                    diagnostics.append({"code": "ORM_XML_ATTRIBUTE_AMBIGUOUS",
                                        "path": spec.get("provenance", {}).get("xml_mapping_file"),
                                        "class": owner, "attribute": attribute_name,
                                        "reason": "XML attribute matches multiple compiler-proven ORM attributes; no column is selected."})
                    continue
                if record["kind"] == "mapped-superclass":
                    for attribute_id in attribute_ids:
                        apply_xml_column(attribute_id, owner, attribute_name, spec, record, override=False)
                elif len(attribute_ids) == 1:
                    apply_xml_column(attribute_ids[0], owner, attribute_name, spec, record, override=False)
                else:
                    diagnostics.append({"code": "ORM_XML_ATTRIBUTE_AMBIGUOUS",
                                        "path": spec.get("provenance", {}).get("xml_mapping_file"),
                                        "class": owner, "attribute": attribute_name,
                                        "reason": "XML attribute matches multiple compiler-proven effective attributes."})
                    for attribute_id in attribute_ids:
                        remove_attribute_columns(attribute_id)
                        nodes[attribute_id] = replace(nodes[attribute_id], metadata={**(nodes[attribute_id].metadata or {}),
                            "mapping_status": "UNKNOWN", "mapping_source": "ORM_XML", **spec.get("provenance", {}),
                            **jpa_rule_metadata})
            for attribute_name, spec in xml_overrides.items():
                attribute_ids = entity_attribute_targets(owner, attribute_name, record["kind"])
                if not attribute_ids:
                    diagnostics.append({"code": "ORM_XML_OVERRIDE_TARGET_UNRESOLVED",
                                        "path": spec.get("provenance", {}).get("xml_mapping_file"),
                                        "class": owner, "attribute": attribute_name,
                                        "reason": "XML attribute override target is absent or ambiguous in the compiler-owned hierarchy."})
                    continue
                if record["kind"] == "mapped-superclass":
                    for attribute_id in attribute_ids:
                        apply_xml_column(attribute_id, owner, attribute_name, spec, record, override=True)
                elif len(attribute_ids) == 1:
                    apply_xml_column(attribute_ids[0], owner, attribute_name, spec, record, override=True)
                else:
                    diagnostics.append({"code": "ORM_XML_OVERRIDE_TARGET_UNRESOLVED",
                                        "path": spec.get("provenance", {}).get("xml_mapping_file"),
                                        "class": owner, "attribute": attribute_name,
                                        "reason": "XML override matches multiple compiler-proven attributes."})
                    for attribute_id in attribute_ids:
                        remove_attribute_columns(attribute_id)
                        nodes[attribute_id] = replace(nodes[attribute_id], metadata={**(nodes[attribute_id].metadata or {}),
                            "mapping_status": "UNKNOWN", "mapping_source": "ORM_XML", **spec.get("provenance", {}),
                            **jpa_rule_metadata})

    # XML may replace the root inheritance strategy after the initial annotation
    # projection. Rebind inherited attributes from the compiler-owned hierarchy
    # using the final effective root table metadata.
    for effective_owner, declaration in entity_decls_by_owner.items():
        ancestors = entity_ancestors(effective_owner)
        if not ancestors:
            continue
        root_owner = str(ancestors[0]["symbol"].get("owner", ""))
        root_table_id = entity_table_by_owner.get(root_owner)
        root_table = nodes.get(root_table_id) if root_table_id else None
        strategy = str((root_table.metadata or {}).get("inheritance_strategy", "UNKNOWN")) if root_table else "UNKNOWN"
        if strategy in {"SINGLE_TABLE", "JOINED"}:
            target_table_id = root_table_id
        elif strategy == "TABLE_PER_CLASS":
            target_table_id = entity_table_by_owner.get(effective_owner)
        else:
            target_table_id = None
        for attribute in list(nodes.values()):
            metadata = attribute.metadata or {}
            if attribute.kind != "orm_attribute" or metadata.get("context_id") != context_id \
                    or metadata.get("effective_owner") != effective_owner \
                    or not metadata.get("inherited"):
                continue
            for key, edge in list(edges.items()):
                if edge.source == attribute.id and edge.kind == "declared_on_table":
                    edges.pop(key, None)
            if target_table_id is not None and target_table_id in nodes:
                add_edge(attribute.id, target_table_id, "declared_on_table", attribute.path,
                         (attribute.metadata or {}).get("source_line"),
                         "Inherited attribute table follows final ORM XML inheritance strategy")
            else:
                nodes[attribute.id] = replace(attribute, metadata={**metadata, "mapping_status": "UNKNOWN",
                                                                     "mapping_source": "ORM_XML_UNKNOWN"})
                diagnostics.append({"code": "ORM_XML_INHERITANCE_UNKNOWN", "path": declaration["path"],
                                    "entity": declaration["node"].id, "root_entity": root_owner,
                                    "reason": "Final XML inheritance strategy is unresolved; inherited table mapping remains UNKNOWN."})

    for owner, declaration in entity_decls_by_owner.items():
        for key, item in list(edges.items()):
            if key[0] != declaration["node"].id:
                continue
            if key[2] in {"maps_to_table", "has_id", "has_embedded_id"} and not jpa_xml["active"]:
                metadata = nodes.get(key[1])
                if metadata is not None:
                    nodes[key[1]] = replace(metadata, metadata={**(metadata.metadata or {}), **jpa_rule_metadata})

    # Finish physical column binding for effective PROPERTY/inherited mappings
    # through the same selected-realm matcher used by declared FIELD mappings.
    # XML has its own hashed-input projection and is deliberately not inferred.
    for mapping in list(edges.values()):
        if mapping.kind != "maps_to_column" or mapping.context_ids != (context_id,):
            continue
        attribute, column = nodes.get(mapping.source), nodes.get(mapping.target)
        if attribute is None or column is None or attribute.kind != "orm_attribute" or (attribute.metadata or {}).get("mapping_status") == "UNKNOWN":
            continue
        if any("xml_mapping_file" in evidence.get(ref, {}) for ref in mapping.evidence_ids):
            continue
        column_metadata = column.metadata or {}
        tables = [edge for edge in edges.values() if edge.source == attribute.id
                  and edge.kind == "declared_on_table" and edge.context_ids == (context_id,)]
        if len(tables) != 1 or column_metadata.get("inferred") is not False or column_metadata.get("mapping_status") == "UNKNOWN":
            continue
        table = nodes.get(tables[0].target)
        table_metadata = table.metadata or {} if table is not None else {}
        if table_metadata.get("inferred") is not False or table_metadata.get("naming_strategy") not in (None, "") or table_metadata.get("mapping_status") == "UNKNOWN":
            continue
        matches = [candidate for candidate in schema_columns if schema_column_matches(candidate,
            table_metadata.get("logical_name"), table_metadata.get("schema"), column_metadata.get("logical_name"))]
        if len(matches) == 1:
            add_edge(column.id, matches[0].id, "resolves_to_schema_column", mapping.source_file,
                     mapping.source_line, "Exact effective column in selected physical table/realm")

    # Make the capability and provenance visible in the selected context.
    contexts = list(graph.contexts)
    for index, current in enumerate(contexts):
        if current.get("id") == context_id:
            contexts[index] = {**current, "framework_analysis": {"spring": SPRING_RULE_VERSION, "jpa": JPA_RULE_VERSION,
                                                                  "schema_binding": "explicit-replay-realm-1", "coverage": "PARTIAL"}}
            break
    result = replace(graph, nodes=sorted(nodes.values(), key=lambda item: item.id),
                     edges=sorted(edges.values(), key=lambda item: (item.source, item.kind, item.target)),
                     contexts=contexts, diagnostics=previous_diagnostics + [{**d, "framework_context_id": context_id} for d in diagnostics], evidence=sorted(evidence.values(), key=lambda item: item["id"]),
                     analysis_annotations=annotations)
    KnowledgeGraph.from_dict(result.to_dict())
    return result
