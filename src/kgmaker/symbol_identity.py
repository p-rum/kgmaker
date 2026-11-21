"""Versioned logical identities for the proven Kotlin top-level subset."""

import re

from .analysis_model import digest


_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_TYPES = {"kotlin.Int": "I", "kotlin.String": "Ljava/lang/String;", "kotlin.Boolean": "Z"}


def _name(value):
    return isinstance(value, str) and _NAME.fullmatch(value) is not None


def valid_declaration(value):
    return (type(value) is dict
            and set(value) == {"schema_version", "package", "name", "parameters", "return_type"}
            and type(value["schema_version"]) is int and value["schema_version"] == 1
            and isinstance(value["package"], str)
            and isinstance(value["name"], str) and bool(value["name"])
            and type(value["parameters"]) is list
            and all(isinstance(item, str) and item in _TYPES for item in value["parameters"])
            and isinstance(value["return_type"], str) and value["return_type"] in _TYPES)


def _identity(symbol, node, context):
    declaration = symbol.get("kotlin_declaration")
    if not valid_declaration(declaration) or node is None or not context:
        return None
    if not _name(declaration["name"]) or not all(_name(part) for part in declaration["package"].split(".")):
        return None
    repo, module, source_set, scope = (context.get(key) for key in ("repo_id", "module", "source_set", "scope"))
    if (context.get("mode") != "BUILD_IMPORT" or context.get("language") != "jvm"
            or (context.get("origin_trust"), context.get("freshness")) not in (
                ("LOCAL_COMPILER_INPUTS", "CONTENT_VERIFIED"), ("HOST_EXECUTION", "EXECUTION_BOUND"))
            or context.get("build_profiles") or context.get("spring_profiles")
            or not all(isinstance(value, str) and value for value in (repo, module, source_set))
            or scope not in ("production", "test") or symbol.get("scope") != scope or node.scope != scope
            or node.build_membership != (module + ":" + source_set,)
            or symbol.get("origin") != "handwritten" or node.origin != "handwritten"):
        return None
    path, owner = symbol.get("path"), symbol.get("owner")
    if (not isinstance(path, str) or path != node.path or not path.endswith(".kt")
            or not isinstance(owner, str) or owner.rpartition(".")[0] != declaration["package"]
            or not _name(owner.rpartition(".")[2]) or not isinstance(symbol.get("range"), dict)
            or symbol.get("jvm_static") is not True or symbol.get("kind") != "method"
            or symbol.get("name") != declaration["name"]):
        return None
    inputs, files = context.get("compiler_inputs"), context.get("source_files")
    relative = path.removeprefix("@" + repo + "/")
    checksum = symbol.get("sha256")
    if (type(inputs) is not list or relative not in inputs or type(files) is not dict
            or not isinstance(checksum, str) or files.get(path) != checksum):
        return None
    parameters = declaration["parameters"]
    result = declaration["return_type"]
    descriptor = "(" + "".join(_TYPES[item] for item in parameters) + ")" + _TYPES[result]
    if symbol.get("descriptor") != descriptor:
        return None
    return (1, repo, "kotlin", module, source_set, scope, declaration["package"],
            "top_level_function", declaration["name"], tuple(parameters), result)


def occurrence_keys(symbols, nodes, contexts):
    """Map proven occurrences without collapsing distinct contexts or overloads."""
    candidates = {}
    for symbol in symbols:
        occurrence = symbol["id"]
        context = symbol["context_id"]
        identity = _identity(symbol, nodes.get(occurrence), contexts.get(context))
        if identity is not None:
            # Return type contributes to the key but cannot disambiguate
            # Kotlin overloads with equal value parameters in the same context.
            candidates.setdefault((context, identity[:-1]), []).append((occurrence, identity))
    return {occurrence: "logical:kotlin-function-v1:" + digest(identity)
            for group in candidates.values() if len(group) == 1
            for occurrence, identity in group}
