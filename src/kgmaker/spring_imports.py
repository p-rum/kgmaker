"""Validate bounded compiler selector facts; never evaluate Java/Kotlin or Spring."""
from __future__ import annotations

import re

from .analysis_model import AnalysisError

SELECTOR = "org.springframework.context.annotation.ImportSelector"
DEFERRED = "org.springframework.context.annotation.DeferredImportSelector"
REGISTRAR = "org.springframework.context.annotation.ImportBeanDefinitionRegistrar"
KINDS = {SELECTOR: "IMPORT_SELECTOR", DEFERRED: "DEFERRED_IMPORT_SELECTOR", REGISTRAR: "REGISTRAR"}
DESCRIPTOR = "(Lorg/springframework/core/type/AnnotationMetadata;)[Ljava/lang/String;"
LIMIT = 128


def selector_info(record: dict, types: dict, symbols: dict, context_id: str) -> dict | None:
    """None proves an ordinary imported type; UNKNOWN never becomes such a bean."""
    symbol = record["symbol"]
    hierarchy = symbol.get("type_hierarchy")
    if hierarchy is not None:
        if (not isinstance(hierarchy, dict) or set(hierarchy) != {"schema_version", "complete", "types"}
                or type(hierarchy["schema_version"]) is not int or hierarchy["schema_version"] != 1
                or type(hierarchy["complete"]) is not bool or not isinstance(hierarchy["types"], list)
                or len(hierarchy["types"]) > LIMIT
                or any(not isinstance(value, str) or not value or len(value) > 1024 for value in hierarchy["types"])
                or len(set(hierarchy["types"])) != len(hierarchy["types"])):
            raise AnalysisError("Invalid compiler selector type hierarchy")
        ancestry, complete = set(hierarchy["types"]), hierarchy["complete"]
    else:
        # Legacy protocol-v1 facts remain readable. Walk exact indexed FQNs;
        # an absent superclass is incomplete proof, never a simple-name guess.
        def legacy_supertypes(item):
            values = item.get("supertypes", [])
            if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
                raise AnalysisError("Invalid compiler selector legacy hierarchy")
            return values
        ancestry, complete, pending = set(), True, list(legacy_supertypes(symbol))
        while pending:
            if len(ancestry) >= LIMIT:
                complete = False
                break
            name = str(pending.pop()).split("<", 1)[0]
            if name in ancestry:
                continue
            ancestry.add(name)
            if name in KINDS or name == "java.lang.Object":
                continue
            if name not in types:
                complete = False
            else:
                pending.extend(legacy_supertypes(types[name]["symbol"]))
    kind = (KINDS[DEFERRED] if DEFERRED in ancestry else KINDS[SELECTOR] if SELECTOR in ancestry
            else KINDS[REGISTRAR] if REGISTRAR in ancestry else None)
    contract = symbol.get("import_selector")
    if kind is None and complete:
        if contract is not None:
            raise AnalysisError("Invalid selector contract on a non-selector type")
        return None
    result = {"kind": kind or "UNKNOWN_IMPORT_PROCESSOR", "status": "UNKNOWN", "targets": [],
              "method": None, "reasons": []}
    if not complete:
        result["reasons"].append("INCOMPLETE_TYPE_HIERARCHY")
    if kind == KINDS[REGISTRAR]:
        result["reasons"].append("REGISTRAR_EXECUTION_UNSUPPORTED")
        return result
    if contract is None:
        result["reasons"].append("NO_COMPILER_SELECTOR_CONTRACT")
        return result
    if (not isinstance(contract, dict) or set(contract) != {"schema_version", "kind", "method_owner", "custom_filter", "custom_group"}
            or type(contract["schema_version"]) is not int or contract["schema_version"] != 1 or contract["kind"] != kind
            or type(contract["custom_filter"]) is not bool or type(contract["custom_group"]) is not bool
            or contract["method_owner"] is not None and not isinstance(contract["method_owner"], str)
            or symbol.get("context_id") != context_id):
        raise AnalysisError("Invalid compiler selector contract/context")
    if contract["custom_filter"]:
        result["reasons"].append("CUSTOM_EXCLUSION_FILTER")
    if contract["custom_group"]:
        result["reasons"].append("CUSTOM_DEFERRED_GROUP")
    methods = [item for item in symbols.values() if item.get("kind") == "method"
               and item.get("owner") == contract["method_owner"] and item.get("name") == "selectImports"
               and item.get("descriptor") == DESCRIPTOR and item.get("context_id") == context_id
               and item.get("path")]
    if len(methods) != 1 or "static_import_return" not in methods[0]:
        result["reasons"].append("NO_INDEXED_LITERAL_RETURN")
        return result
    method = methods[0]
    fact = method["static_import_return"]
    if (not isinstance(fact, dict) or set(fact) != {"schema_version", "status", "values", "reason"}
            or type(fact["schema_version"]) is not int or fact["schema_version"] != 1
            or not isinstance(fact["status"], str) or fact["status"] not in {"LITERAL", "UNSUPPORTED"}
            or not isinstance(fact["reason"], str) or not 1 <= len(fact["reason"]) <= 512
            or not isinstance(fact["values"], list) or len(fact["values"]) > LIMIT
            or any(not isinstance(value, str) or len(value) > 512
                   or not re.fullmatch(r"[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)+", value) for value in fact["values"])
            or fact["status"] == "UNSUPPORTED" and fact["values"]):
        raise AnalysisError("Invalid compiler selector literal-return fact")
    result["method"] = method
    if fact["status"] == "UNSUPPORTED":
        result["reasons"].append(fact["reason"])
    else:
        result["targets"] = list(dict.fromkeys(fact["values"]))
        if not result["reasons"]:
            result["status"] = "RESOLVED_LITERAL"
    return result
