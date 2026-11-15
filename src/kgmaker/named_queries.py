"""Bounded decoding of compiler-owned JPA named-query declarations.

Javac's protocol represents nested annotation mirrors as strings; Kotlin may
use structured name/values records. Neither representation is source scanning.
"""
from __future__ import annotations

import ast
import re


KINDS = {"NamedQuery": "JPQL", "NamedNativeQuery": "NATIVE_SQL"}
CONTAINERS = {"NamedQueries": "NamedQuery", "NamedNativeQueries": "NamedNativeQuery"}
PACKAGES = {"jakarta.persistence", "javax.persistence"}


def _members(text: str) -> dict:
    """Decode top-level annotation members without reading inside query strings."""
    parts, start, depth, quoted, escaped = [], 0, 0, False, False
    for index, char in enumerate(text):
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "({[":
            depth += 1
        elif char in ")}]":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append(text[start:index])
            start = index + 1
    if depth or quoted:
        return {}
    parts.append(text[start:])
    result = {}
    for part in parts:
        key, separator, value = part.strip().partition("=")
        key, value = key.strip(), value.strip()
        if not separator or key in result:
            return {}
        if key not in {"name", "query", "resultClass", "resultSetMapping"}:
            continue
        try:
            # AnnotationMirror.toString() uses Java escapes, including \\'
            # inside double-quoted strings, which JSON does not accept.
            decoded = ast.literal_eval(value)
            result[key] = decoded if isinstance(decoded, str) else None
        except (ValueError, SyntaxError):
            if key == "resultClass" and re.fullmatch(r"[\w.$]+\.class", value):
                result[key] = value[:-6]
            else:
                result[key] = None
    return result


def declarations(annotations: list[dict]):
    """Yield records, retaining invalid named declarations as collision blockers."""
    for annotation in annotations:
        if not isinstance(annotation, dict):
            continue
        name = annotation.get("name", "")
        package, _, kind = name.rpartition(".")
        if package not in PACKAGES or kind not in KINDS.keys() | CONTAINERS.keys():
            continue
        members = annotation.get("values", {})
        resolved = annotation.get("values_resolved", True) is True
        if kind in CONTAINERS:
            entries = members.get("value", []) if isinstance(members, dict) else []
            entries = entries if isinstance(entries, list) else [entries]
            if not resolved or not entries:
                yield {"name": None, "query": None, "language": KINDS[CONTAINERS[kind]]}
            for entry in entries:
                if isinstance(entry, str):
                    match = re.fullmatch(r"@([\w.]+)\((.*)\)", entry, re.S)
                    entry = {"name": match[1], "values": _members(match[2])} if match else {}
                if isinstance(entry, dict) and entry.get("name") == package + "." + CONTAINERS[kind]:
                    yield from declarations([{**entry, "values_resolved": False}] if not resolved else [entry])
                else:
                    yield {"name": None, "query": None, "language": KINDS[CONTAINERS[kind]]}
            continue
        members = members if isinstance(members, dict) else {}
        query_name, query = members.get("name"), members.get("query")
        yield {"name": query_name if isinstance(query_name, str) and query_name.strip() else None,
               "query": query if resolved and isinstance(query, str) and query.strip() else None,
               "language": KINDS[kind], "result_class": members.get("resultClass")
               if isinstance(members.get("resultClass"), (str, type(None))) else "UNRESOLVED",
               "result_set_mapping": members.get("resultSetMapping")}


def parameters(query: str) -> tuple[list[str], list[int]]:
    """Exclude SQL/JPQL strings, quoted identifiers, comments and PostgreSQL casts."""
    text = re.sub(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|--[^\n]*|/\*.*?\*/", " ", query, flags=re.S)
    named = sorted(set(re.findall(r"(?<!:):([A-Za-z_]\w*)", text)))
    positional = sorted({int(value) for value in re.findall(r"\?(\d+)", text)})
    return named, positional
