"""Validate compiler registrar/factory declarations without executing custom code."""
from .analysis_model import AnalysisError

FACTORY = "org.springframework.beans.factory.FactoryBean"
LIMIT = 128


def _schema(value, fields, label):
    if (not isinstance(value, dict) or set(value) != {"schema_version", *fields}
            or type(value["schema_version"]) is not int or value["schema_version"] != 1):
        raise AnalysisError("Invalid compiler " + label + " fact")


def _name(value):
    return isinstance(value, str) and 0 < len(value) <= 1024


def _method(symbols, owner, name, context_id, descriptor=None):
    matches = [s for s in symbols.values() if s.get("kind") == "method" and s.get("owner") == owner
               and s.get("name") == name and s.get("context_id") == context_id and s.get("path")
               and (s.get("descriptor") == descriptor if descriptor else str(s.get("descriptor", "")).startswith("()"))]
    return matches[0] if len(matches) == 1 else None


def registrar_info(symbol, symbols, context_id, reasons=()):
    result = {"kind": "REGISTRAR", "status": "UNKNOWN", "targets": [], "registrations": [],
              "method": None, "reasons": list(reasons)}
    fact = symbol.get("bean_registrar")
    if fact is None:
        result["reasons"].append("REGISTRAR_EXECUTION_UNSUPPORTED")
        return result
    _schema(fact, {"method_owner", "custom_name_generator"}, "registrar")
    if (fact["method_owner"] is not None and not _name(fact["method_owner"])
            or type(fact["custom_name_generator"]) is not bool or symbol.get("context_id") != context_id):
        raise AnalysisError("Invalid compiler registrar context/owner")
    if fact["custom_name_generator"]:
        result["reasons"].append("CUSTOM_REGISTRAR_NAME_GENERATOR")
    method = _method(symbols, fact["method_owner"], "registerBeanDefinitions", context_id,
                     "(Lorg/springframework/core/type/AnnotationMetadata;Lorg/springframework/beans/factory/support/BeanDefinitionRegistry;)V")
    if method is None or "bean_registrations" not in method:
        result["reasons"].append("NO_INDEXED_REGISTRAR_BODY")
        return result
    body = method["bean_registrations"]
    _schema(body, {"status", "values", "reason"}, "registrar body")
    if (not isinstance(body["status"], str) or body["status"] not in {"LITERAL", "UNSUPPORTED"} or not _name(body["reason"])
            or not isinstance(body["values"], list) or len(body["values"]) > LIMIT
            or body["status"] == "UNSUPPORTED" and body["values"]):
        raise AnalysisError("Invalid compiler registrar body values")
    for item in body["values"]:
        if (not isinstance(item, dict) or set(item) != {"name", "type"}
                or not _name(item["name"]) or len(item["name"]) > 512 or item["name"].startswith("&")
                or not item["name"].strip() or not _name(item["type"])):
            raise AnalysisError("Invalid compiler registrar registration")
    result["method"] = method
    if body["status"] == "UNSUPPORTED":
        result["reasons"].append(body["reason"])
    else:
        result["registrations"] = body["values"]
        if len({x["name"] for x in body["values"]}) != len(body["values"]):
            result["reasons"].append("DUPLICATE_REGISTRATION_NAME")
        if not result["reasons"]:
            result["status"] = "RESOLVED_LITERAL"
    return result


def factory_info(symbol, symbols, context_id):
    field = "factory_bean_return" if symbol.get("kind") == "method" else "factory_bean"
    fact = symbol.get(field)
    hierarchy = symbol.get("type_hierarchy") or {}
    if not isinstance(hierarchy, dict) or not isinstance(hierarchy.get("types", []), list):
        raise AnalysisError("Invalid compiler factory hierarchy")
    ancestry = list(hierarchy.get("types", []))
    if not hierarchy:
        # Legacy/Kotlin source can prove the qualified API identity without
        # supplying Java body facts. Such products remain explicitly UNKNOWN.
        pending = list(symbol.get("supertypes", []))
        declarations = {s.get("owner"): s for s in symbols.values()
                        if s.get("kind") in {"class", "interface"} and s.get("context_id") == context_id}
        visited = set()
        while pending and len(visited) < LIMIT:
            raw = pending.pop()
            if not isinstance(raw, str):
                raise AnalysisError("Invalid compiler factory legacy hierarchy")
            name = raw.split("<", 1)[0]
            if name in visited:
                continue
            visited.add(name)
            ancestry.append(name)
            if name in declarations:
                parents = declarations[name].get("supertypes", [])
                if not isinstance(parents, list):
                    raise AnalysisError("Invalid compiler factory legacy hierarchy")
                pending.extend(parents)
    if fact is None and FACTORY not in ancestry:
        return None
    result = {"status": "UNKNOWN", "product_type": None, "method": None, "reasons": [], "sources": []}
    if field == "factory_bean" and hierarchy.get("complete") is not True:
        result["reasons"].append("INCOMPLETE_FACTORY_HIERARCHY")
    if field == "factory_bean" and (symbol.get("kind") != "class" or "abstract" in symbol.get("modifiers", [])):
        result["reasons"].append("FACTORY_NOT_CONCRETE")
    if fact is None:
        result["reasons"].append("LEGACY_FACTORY_CONTRACT_UNAVAILABLE")
        return result
    _schema(fact, {"product_type", "get_object_owner", "get_type_owner"}, "factory")
    if field == "factory_bean" and FACTORY not in ancestry:
        raise AnalysisError("Invalid compiler factory namespace")
    if (any(v is not None and not _name(v) for k, v in fact.items() if k != "schema_version")
            or symbol.get("context_id") != context_id):
        raise AnalysisError("Invalid compiler factory context/types")
    result["product_type"] = fact["product_type"]
    if fact["product_type"] is None:
        result["reasons"].append("FACTORY_PRODUCT_TYPE_UNKNOWN")
    if field == "factory_bean_return":
        result["method"] = symbol
        result["sources"].append(symbol)
        producer = symbol.get("factory_producer")
        if producer is None:
            result["reasons"].append("FACTORY_PRODUCER_IMPLEMENTATION_UNPROVEN")
            return result
        _schema(producer, {"status", "type", "reason"}, "factory producer")
        if (not isinstance(producer["status"], str) or producer["status"] not in {"LITERAL", "UNSUPPORTED"}
                or not _name(producer["reason"]) or producer["status"] == "LITERAL" and not _name(producer["type"])
                or producer["status"] == "UNSUPPORTED" and producer["type"] is not None):
            raise AnalysisError("Invalid compiler factory producer values")
        if producer["status"] != "LITERAL":
            result["reasons"].append(producer["reason"])
            return result
        declaration = next((s for s in symbols.values() if s.get("owner") == producer["type"]
                            and s.get("kind") == "class" and s.get("context_id") == context_id), None)
        if declaration is None or declaration.get("factory_bean") != fact:
            result["reasons"].append("FACTORY_PRODUCER_NOT_INDEXED_OR_GENERIC")
            return result
    returns = []
    for kind, owner, method_name in (("OBJECT", fact["get_object_owner"], "getObject"),
                                      ("TYPE", fact["get_type_owner"], "getObjectType")):
        method = _method(symbols, owner, method_name, context_id)
        if method is None or "factory_return" not in method:
            result["reasons"].append("NO_INDEXED_FACTORY_" + kind)
            continue
        result["sources"].append(method)
        if kind == "OBJECT" and field != "factory_bean_return":
            result["method"] = method
        body = method["factory_return"]
        _schema(body, {"kind", "status", "type", "reason"}, "factory return")
        if (body["kind"] != kind or not isinstance(body["status"], str) or body["status"] not in {"LITERAL", "UNSUPPORTED"}
                or not _name(body["reason"]) or body["status"] == "LITERAL" and not _name(body["type"])
                or body["status"] == "UNSUPPORTED" and body["type"] is not None):
            raise AnalysisError("Invalid compiler factory return values")
        if body["status"] == "LITERAL":
            returns.append(body["type"])
        else:
            result["reasons"].append(body["reason"])
    if len(returns) == 2 and set(returns) != {fact["product_type"]}:
        result["reasons"].append("FACTORY_PRODUCT_TYPE_MISMATCH")
    if len(returns) == 2 and not result["reasons"]:
        result["status"] = "RESOLVED_LITERAL"
    return result


def registration_assignability(declared_type, field_type, injection_kind, types):
    """Compare qualified compiler types; absence of a proof is not assignability."""
    requested = str(field_type or "").replace(" ", "")
    if injection_kind in {"collection", "provider", "optional", "map"}:
        if "<" not in requested or not requested.endswith(">"):
            return "UNKNOWN"
        inner = requested.split("<", 1)[1][:-1]
        requested = inner.split(",", 1)[-1] if injection_kind == "map" else inner
    if not requested or any(char in requested for char in "<>?,[]"):
        return "UNKNOWN"
    if requested == declared_type:
        return "ASSIGNABLE"
    hierarchy = (types.get(declared_type, {}).get("symbol", {}).get("type_hierarchy") or {})
    if hierarchy.get("complete") is not True:
        return "UNKNOWN"
    return "ASSIGNABLE" if requested in hierarchy.get("types", []) else "INCOMPATIBLE"
