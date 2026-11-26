"""One compiler-bound observation of reference presence, without value data."""
from datetime import datetime, timezone

from .analysis_model import AnalysisError, digest
from .dataflow import argument_parameter_bindings, field_mapping_bindings

FACT = "value_presence"
RELATION = "runtime_value_presence"
PROOF = "RUNTIME_PRESENT_VALUE_PATH"
_STRING = "Ljava/lang/String;"
_HOOK = ("org.kgmaker.runtime.RuntimeTrace", "observeValuePresence", f"({_STRING}{_STRING})V")
_FRAME_FIELDS = ("caller_owner", "caller_name", "caller_descriptor")
_RECORD_FIELDS = {"id", "kind", "relation", "source", "target", "context_id", "runtime_id", "build_id",
                  "config_fingerprint", "service_id", "service_version", "source_identity", "presence",
                  "field_mapping_evidence_id", "hook_call_site", "run_started_at"}


def valid_proof_reference(proof):
    return (set(proof) == {"kind", "runtime_evidence_id", "mapping_decision_id"}
            and all(type(proof[key]) is str and 0 < len(proof[key]) <= 200
                    for key in ("runtime_evidence_id", "mapping_decision_id")))


def run_start(value):
    """Validate the preserved producer clock without refreshing it on import."""
    try:
        if type(value) is not str or len(value) > 40:
            raise ValueError
        instant = datetime.fromisoformat(value)
        if instant.tzinfo is None or instant.utcoffset().total_seconds() != 0 or instant > datetime.now(timezone.utc):
            raise ValueError
    except (ValueError, OverflowError):
        raise AnalysisError("RUNTIME_VALUE_CLOCK: expected a nonfuture UTC run start", 3) from None
    return instant


def _signature(symbol):
    return tuple(symbol.get(key) for key in ("owner", "name", "descriptor"))


def _on_line(location, line):
    return isinstance(location, dict) and location.get("start_line") == location.get("end_line") == line


def _direct_mapping(binding, context, symbols):
    fields = [symbols.get(binding.get(key), {}) for key in ("source", "target")]
    source = binding.get("source_file")
    owner = symbols.get(binding.get("owner_method"), {})
    return (binding.get("relation") == "maps_to" and binding.get("kind") == "SYMBOL_RESOLVED"
            and binding.get("context_ids") == [context["id"]] and binding.get("transformation") == "DIRECT_ASSIGNMENT"
            and binding.get("identity_scope") == "FIELD_DECLARATION" and not binding.get("branch_guards")
            and binding["source"] != binding["target"] and isinstance(source, str) and source.endswith(".java")
            and owner.get("kind") == "method" and owner.get("path") == source and source in context["source_files"]
            and binding.get("sha256") == context["source_files"][source]
            and all(field.get("kind") == "field" and field.get("descriptor") == _STRING
                    and field.get("path") in context["source_files"] for field in fields))


def resolve_capture(graph, context, fact):
    if type(fact) is not dict:
        raise AnalysisError("RUNTIME_VALUE_FACT: unsupported presence fields", 3)
    fact = dict(fact)
    if (set(fact) != {"kind", "source_line", "presence", *_FRAME_FIELDS}
            or type(fact.get("kind")) is not str or fact["kind"] != FACT
            or type(fact["presence"]) is not str or fact["presence"] not in {"PRESENT", "ABSENT"}
            or type(fact["source_line"]) is not int or fact["source_line"] <= 0
            or any(type(fact[field]) is not str or not 0 < len(fact[field]) <= 2048 for field in _FRAME_FIELDS)):
        raise AnalysisError("RUNTIME_VALUE_FACT: unsupported presence fields", 3)
    if context.get("language") != "jvm" or context.get("freshness") != "EXECUTION_BOUND" or not context.get("bytecode_artifacts"):
        raise AnalysisError("RUNTIME_VALUE_CONTEXT: expected execution-bound JVM bytecode", 3)
    symbols = {item["id"]: item for item in graph.symbols if item.get("context_id") == context["id"]}
    signature = tuple(fact[field] for field in _FRAME_FIELDS)
    line = fact["source_line"]
    bindings = field_mapping_bindings(graph)
    transfers = [row for row in bindings if row.get("relation") == "maps_to"
                 and _signature(symbols.get(row.get("owner_method"), {})) == signature
                 and _on_line(row.get("source_range"), line)]
    if len(transfers) != 1 or not _direct_mapping(transfers[0], context, symbols):
        raise AnalysisError("RUNTIME_VALUE_BINDING: expected one selected direct String assignment on the frame line", 3)
    transfer, = transfers
    owner = transfer["owner_method"]
    writes = [row for row in bindings if row.get("relation") == "writes_value" and row.get("owner_method") == owner
              and row.get("context_ids") == [context["id"]] and _on_line(row.get("source_range"), line)]
    if (len(writes) != 1 or writes[0]["target"] != transfer["target"]
            or writes[0]["source_range"] != transfer["source_range"]):
        raise AnalysisError("RUNTIME_VALUE_BINDING: expected exactly one field write on the frame line", 3)
    physical_callers = {item["id"] for item in symbols.values() if item.get("kind") == "bytecode_method"
                        and _signature(item) == signature}
    bytecode = [site for site in graph.call_sites if site.get("context_id") == context["id"]
                and site.get("representation") == "BYTECODE" and site.get("caller") in physical_callers]
    if (len(physical_callers) != 1 or any(type(site.get("source_line")) is not int or site["source_line"] <= 0
            or site.get("artifact_hashes") != context["bytecode_artifacts"] for site in bytecode)):
        raise AnalysisError("RUNTIME_VALUE_SITE: missing selected bytecode line authority", 3)
    physical, = physical_callers
    hooks = [site for site in bytecode if site["source_line"] == line]
    sources = [site for site in graph.call_sites if site.get("context_id") == context["id"]
               and site.get("caller") == owner and _on_line(site.get("range"), line)]
    if (symbols[physical].get("source_mapping_ids") != [owner] or len(hooks) != 1 or len(sources) != 1
            or any(site.get("evidence_kind") != "SYMBOL_RESOLVED"
                   or _signature(symbols.get(site.get("declared_target"), {})) != _HOOK for site in (*hooks, *sources))
            or sources[0].get("path") != transfer["source_file"]
            or sources[0]["range"].get("start", -1) <= transfer["source_range"].get("end", -1)):
        raise AnalysisError("RUNTIME_VALUE_SITE: expected one resolved hook after the assignment", 3)
    hook = sources[0]
    arguments = argument_parameter_bindings(graph, hook["id"])
    if len(arguments) != 2 or hook.get("argument_mapping_status") != "PROVEN":
        raise AnalysisError("RUNTIME_VALUE_ARGUMENTS: expected two compiler-bound field reads", 3)
    for index, endpoint in enumerate(("source", "target")):
        argument = arguments[index]
        span = symbols.get(argument["argument"], {}).get("range")
        matches = [row for row in bindings if row.get("relation") == "reads_value" and row.get("owner_method") == owner
                   and row.get("source_range") == span and row.get("context_ids") == [context["id"]]
                   and row.get("source_file") == transfer["source_file"] and row.get("sha256") == transfer["sha256"]]
        if (not _on_line(span, line) or argument["argument_index"] != index or argument["parameter_index"] != index
                or argument["context_ids"] != [context["id"]] or argument["transformation"] != "DIRECT"
                or len(matches) != 1 or matches[0]["target"] != transfer[endpoint] or matches[0].get("branch_guards")):
            raise AnalysisError("RUNTIME_VALUE_ARGUMENTS: hook arguments do not match the selected field reads", 3)
    return {"kind": FACT, "source": transfer["source"], "target": transfer["target"], "presence": fact["presence"],
            "field_mapping_evidence_id": transfer["id"], "hook_call_site": hook["id"]}


def current_record(graph, packet, identity):
    if (type(identity) is not str or identity not in packet.get("graph_evidence_ids", ()) or packet.get("workspace")):
        raise AnalysisError("Runtime presence requires a record from the exact local analysis packet")
    records = [row for row in graph.evidence if row["id"] == identity]
    selected = packet.get("graph_selection", {})
    contexts = [row for row in graph.contexts if row["id"] == selected.get("context_id")]
    if len(records) != 1 or len(contexts) != 1:
        raise AnalysisError("Runtime presence record or explicit context is unavailable")
    record, = records
    context, = contexts
    if (set(record) != _RECORD_FIELDS or record.get("kind") != "RUNTIME_OBSERVED" or record.get("relation") != RELATION
            or record.get("context_id") != context["id"] or context.get("freshness") != "EXECUTION_BOUND"
            or context.get("scope") != selected.get("scope")
            or identity != "evidence:" + digest({key: value for key, value in record.items() if key != "id"})
            or record.get("build_id") != context.get("build_id")
            or record.get("config_fingerprint") != context.get("config_fingerprint")
            or record.get("source_identity") != {"context_fingerprint": digest(context),
               "source_manifest_fingerprint": digest(context.get("source_files"))}):
        raise AnalysisError("Runtime presence record is outside the current selected context", 3)
    source, target = record.get("source"), record.get("target")
    if not any(edge.kind == RELATION and edge.evidence_kind == "RUNTIME_OBSERVED" and edge.source == source
               and edge.target == target and edge.context_ids == (context["id"],) and identity in edge.evidence_ids
               for edge in graph.edges):
        raise AnalysisError("Runtime presence record has no current scoped graph relation")
    symbols = {item["id"]: item for item in graph.symbols if item.get("context_id") == context["id"]}
    bindings = [row for row in field_mapping_bindings(graph) if row["id"] == record.get("field_mapping_evidence_id")]
    if (len(bindings) != 1 or not _direct_mapping(bindings[0], context, symbols)
            or (bindings[0]["source"], bindings[0]["target"]) != (source, target)):
        raise AnalysisError("Runtime presence has no current matching compiler field proof", 3)
    locations = {symbols[source]["path"], symbols[target]["path"], bindings[0]["source_file"]}
    if any(packet["source_manifest"].get(path, {}).get("sha256") != context["source_files"][path] for path in locations):
        raise AnalysisError("Runtime presence source differs from the analysis packet", 3)
    return record
