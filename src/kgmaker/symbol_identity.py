"""Versioned logical identities for the proven Kotlin top-level subset."""

import re

from .analysis_model import digest
from .classification import source_set_contains


_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_TYPES = {"kotlin.Int": "I", "kotlin.String": "Ljava/lang/String;", "kotlin.Boolean": "Z"}
# The workspace projection of this snapshot qualifies its compiler inputs.
_RAW_JVM_SNAPSHOT = "selected-source-set-raw-1"


def _name(value):
    return isinstance(value, str) and _NAME.fullmatch(value) is not None


def valid_declaration(value):
    return (type(value) is dict
            and set(value) == {"schema_version", "package", "name", "parameters", "return_type"}
            and type(value["schema_version"]) is int and value["schema_version"] in {1, 2}
            and isinstance(value["package"], str)
            and isinstance(value["name"], str) and bool(value["name"])
            and type(value["parameters"]) is list
            and all(isinstance(item, str) and item in _TYPES for item in value["parameters"])
            and isinstance(value["return_type"], str) and value["return_type"] in _TYPES)


def _selected_realm(context):
    realm = tuple(context.get(key) for key in ("repo_id", "module", "source_set", "scope"))
    if (context.get("mode") != "BUILD_IMPORT" or context.get("language") != "jvm"
            or (context.get("origin_trust"), context.get("freshness")) not in (
                ("LOCAL_COMPILER_INPUTS", "CONTENT_VERIFIED"), ("HOST_EXECUTION", "EXECUTION_BOUND"))
            or context.get("build_profiles") or context.get("spring_profiles")
            or not all(isinstance(value, str) and value for value in realm)
            or realm[3] not in ("production", "test")):
        return None
    return realm


def _source_sets(context):
    model = context.get("project_model")
    entries = model.get("source_sets") if isinstance(model, dict) else None
    if not isinstance(entries, list):
        return []
    for source in entries:
        if (not isinstance(source, dict)
                or not all(isinstance(source.get(key), str) and source[key] for key in ("module", "id", "scope"))
                or type(source.get("generated", False)) is not bool):
            return []
        for key in ("roots", "files"):
            paths = source.get(key, [])
            if not isinstance(paths, list) or any(not isinstance(path, str) or not path for path in paths):
                return []
    return [{**source, "files": set(source.get("files", []))} for source in entries]


def _complete_kotlin_namespace(context, realm):
    """Map captured Kotlin paths to whether their exact owner can receive a key."""
    repo, module, source_set, scope = realm
    files, inputs = context.get("source_files"), context.get("compiler_inputs")
    if (not isinstance(files, dict) or any(not isinstance(path, str) for path in files)
            or not isinstance(inputs, list) or any(not isinstance(path, str) for path in inputs)):
        return {}

    prefix = ""
    context_id = context.get("id")
    if isinstance(context_id, str) and context_id.startswith("repo:"):
        from .workspace import split_id
        try:
            projected_repo, _ = split_id(context_id)
        except ValueError:
            return {}
        prefix = f"@{repo}/"
        if projected_repo != repo or any(not path.startswith(prefix) for path in files):
            return {}
        if context.get("source_snapshot_version") == _RAW_JVM_SNAPSHOT:
            if any(not path.startswith(prefix) for path in inputs):
                return {}
            inputs = [path[len(prefix):] for path in inputs]

    entries = _source_sets(context)
    selected = [entry for entry in entries if entry["module"] == module and entry["scope"] == scope
                and (entry["id"] == source_set or
                     (entry["id"] == source_set + ":generated" and entry.get("generated") is True))]
    selected_paths = {path for entry in selected for path in entry["files"] if path.endswith(".kt")}
    captured_paths = {path[len(prefix):] for path in files if path.endswith(".kt")}
    if not selected_paths <= captured_paths:
        return {}
    namespace = {}
    for path in captured_paths:
        memberships = [entry for entry in entries if source_set_contains(entry, path)]
        if any(entry in selected for entry in memberships):
            selected_paths.add(path)
            namespace[prefix + path] = (len(memberships) == 1 and memberships[0]["id"] == source_set
                                         and memberships[0].get("generated") is not True)
    return namespace if selected_paths <= set(inputs) else {}


def _identity(symbol, node, context, realm):
    declaration = symbol.get("kotlin_declaration")
    if not valid_declaration(declaration) or declaration["schema_version"] != 2 or node is None:
        return None
    if not _name(declaration["name"]) or not all(_name(part) for part in declaration["package"].split(".")):
        return None
    repo, module, source_set, scope = realm
    if symbol.get("scope") != scope or node.scope != scope:
        return None
    path, owner = symbol.get("path"), symbol.get("owner")
    if (not isinstance(path, str) or path != node.path or not path.endswith(".kt")
            or not isinstance(owner, str) or owner.rpartition(".")[0] != declaration["package"]
            or not _name(owner.rpartition(".")[2]) or not isinstance(symbol.get("range"), dict)
            or symbol.get("jvm_static") is not True or symbol.get("kind") != "method"
            or symbol.get("name") != declaration["name"]):
        return None
    checksum = symbol.get("sha256")
    if not isinstance(checksum, str) or context["source_files"].get(path) != checksum:
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
    witnessed = {symbol["context_id"] for symbol in symbols if "kotlin_declaration" in symbol}
    realms = {identity: realm for identity in witnessed
              if (realm := _selected_realm(contexts.get(identity, {}))) is not None}
    namespaces = {identity: _complete_kotlin_namespace(contexts[identity], realm)
                  for identity, realm in realms.items()}
    candidates = {}
    for symbol in symbols:
        occurrence = symbol["id"]
        context = symbol["context_id"]
        path = symbol.get("path")
        namespace = namespaces.get(context, {})
        if not isinstance(path, str) or path not in namespace:
            continue
        node = nodes.get(occurrence)
        identity = _identity(symbol, node, contexts[context], realms[context])
        if identity is not None:
            # Return type contributes to the key but cannot disambiguate
            # Kotlin overloads with equal value parameters in the same context.
            _, module, source_set, _ = realms[context]
            eligible = (namespace[path] and symbol.get("origin") == node.origin == "handwritten"
                        and node.build_membership == (module + ":" + source_set,))
            candidates.setdefault((context, identity[:-1]), []).append((occurrence, identity, eligible))
    return {occurrence: "logical:kotlin-function-v1:" + digest(identity)
            for group in candidates.values() if len(group) == 1
            for occurrence, identity, eligible in group if eligible}
