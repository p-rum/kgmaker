"""JSON-first source CFG/process rendering with preserved origin IDs."""
from __future__ import annotations

import html
from collections import defaultdict

from .analysis_model import AnalysisError, digest
from .callgraph import strongly_connected
from .views import project
from .dataflow import argument_parameter_bindings


def _label(value):
    return html.escape(str(value), quote=True).replace("\n", "<br/>").replace("\r", " ").replace("|", "&#124;")


def control_flow(graph, entry, *, scope="production", max_nodes=500, representation="SOURCE"):
    if max_nodes < 1:
        raise AnalysisError("max-nodes must be positive")
    graph = project(graph, scope)
    variants = [c for c in graph.cfgs if c["method"] == entry and c.get("representation") == representation]
    if len(variants) > 1:
        raise AnalysisError("Explicit context required for CFG variants: " + ", ".join(c.get("context_id", "unknown") for c in variants))
    cfg = variants[0] if variants else None
    if cfg is None:
        raise AnalysisError("Control-flow index unavailable for this symbol/representation")
    if len(cfg["blocks"]) > max_nodes:
        # Keep reachable prefix and replace each omitted edge endpoint by an
        # explicit boundary. Conditions never get rewired to arbitrary steps.
        outgoing = defaultdict(list)
        for edge in cfg["edges"]:
            outgoing[edge["source"]].append(edge)
        selected, pending = set(), [cfg["entry"]]
        while pending and len(selected) < max_nodes:
            node = pending.pop(0)
            if node in selected:
                continue
            selected.add(node)
            pending.extend(e["target"] for e in sorted(outgoing[node], key=lambda e: (e["kind"], e["target"])) if e["target"] not in selected)
        blocks = [b for b in cfg["blocks"] if b["id"] in selected]
        boundaries, edges = {}, []
        for edge in cfg["edges"]:
            if edge["source"] not in selected:
                continue
            if edge["target"] in selected:
                edges.append(edge)
            else:
                identity = "truncated:" + digest(edge["target"])[:20]
                boundaries[identity] = {"id": identity, "kind": "unresolved_boundary", "label": "node limit: omitted detail",
                                        "original_ids": [edge["target"]]}
                edges.append({**edge, "target": identity})
        cfg = {**cfg, "blocks": blocks + list(boundaries.values()), "edges": edges, "truncated": True}
    return {"schema_version": 1, "view": "control-flow", "scope": scope, "entry": entry,
            "contexts": graph.contexts, "cfg": cfg, "truncated": cfg.get("truncated", False),
            "status": "PARTIAL" if cfg.get("truncated") or cfg.get("diagnostics") else "COMPLETE_WITHIN_SUPPORTED_SYNTAX",
            "limitations": cfg.get("limitations", [])}


def process(graph, entry, *, scope="production", max_depth=3, max_nodes=500, context_id=None):
    """Expand CFG calls only when a unique body is a safe static representation.

No ordering is derived from a call graph. Recursive, dispatch-uncertain and
size/depth-limited calls remain explicit boundaries with original call-site IDs.
"""
    if type(max_depth) is not int or type(max_nodes) is not int or max_depth < 0 or max_nodes < 1:
        raise AnalysisError("Invalid traversal limits")
    policy_input = graph
    graph = project(graph, scope, context_id=context_id)
    bodies = [c for c in graph.cfgs if c.get("representation") == "SOURCE"]
    if len({c["method"] for c in bodies}) != len(bodies):
        raise AnalysisError("Explicit context required for process CFG variants")
    cfgs = {c["method"]: c for c in bodies}
    sites = {s["id"]: s for s in graph.call_sites}
    if entry not in cfgs:
        raise AnalysisError("Source CFG unavailable for process entry")
    if len(cfgs[entry]["blocks"]) > max_nodes:
        # An oversized root has no safe expansion within the requested budget.
        # Preserve a single explicit entry boundary instead of silently copying
        # its entire CFG or inventing edges between an arbitrary retained prefix.
        cfg = cfgs[entry]
        identity = "process:" + digest({"entry": entry, "boundary": "node limit"})[:24]
        boundary = {"id": identity, "kind": "unresolved_boundary", "label": "node limit",
                    "method": entry, "boundary_reason": "node limit",
                    "original_ids": sorted({entry, cfg["entry"], cfg["exit"], cfg["exceptional_exit"]}),
                    "omitted_blocks": len(cfg["blocks"])}
        return {"schema_version": 1, "view": "process", "entry": entry, "scope": scope,
                "contexts": graph.contexts, "status": "PARTIAL", "truncated": True,
                "diagnostics": [{"code": "PROCESS_ROOT_NODE_LIMIT", "method": entry,
                                 "omitted_blocks": len(cfg["blocks"])}],
                "cfg": {"entry": identity, "exit": identity, "exceptional_exit": identity,
                        "blocks": [boundary], "edges": []},
                "boundaries": [{"target": entry, "reason": "node limit"}],
                "strongly_connected_components": [],
                "limits": {"max_depth": max_depth, "max_nodes": max_nodes},
                "limitations": ["Root CFG omitted; static expansion is not observed execution."]}
    blocks, edges, omitted = {}, [], []
    expanded_methods = set()
    symbols = {symbol["id"]: symbol for symbol in graph.symbols}
    graph_nodes = {node.id: node for node in graph.nodes}
    graph_edges = defaultdict(list)
    for edge in graph.edges:
        graph_edges[edge.source].append(edge)

    def expand(method, depth, ancestry, prefix):
        cfg = cfgs[method]
        expanded_methods.add(method)
        ids = {b["id"]: "process:" + digest({"path": prefix, "id": b["id"]})[:24] for b in cfg["blocks"]}
        for b in cfg["blocks"]:
            identity = ids[b["id"]]
            blocks[identity] = {**b, "id": identity, "method": method, "original_ids": sorted(set(b.get("original_ids", []) + [b["id"], method]))}
        local_edges = [{**e, "source": ids[e["source"]], "target": ids[e["target"]], "original_ids": [digest(e)]} for e in cfg["edges"]]
        for block in cfg["blocks"]:
            call_ids = block.get("call_site_ids", [])
            if block["kind"] != "call" or len(call_ids) != 1:
                continue
            site = sites.get(call_ids[0])
            if not site:
                blocks[ids[block["id"]]]["boundary_reason"] = "call-site proof unavailable"
                blocks[ids[block["id"]]]["original_ids"].append(call_ids[0])
                omitted.append({"call_site": call_ids[0], "target": None, "reason": "call-site proof unavailable"})
                continue
            target = site.get("declared_target")
            candidates = set(site.get("dispatch_candidates", []))
            uncertain = len(candidates) > 1 or (candidates and candidates != {target}) or ((site.get("invocation_kind") in {"VIRTUAL", "INTERFACE", "INVOKEVIRTUAL", "INVOKEINTERFACE"} or (site.get("invocation_kind") == "CALL" and site.get("receiver_type"))) and not site.get("dispatch_complete"))
            target_symbol = symbols.get(target, {})
            annotations = target_symbol.get("annotations") if isinstance(target_symbol.get("annotations"), list) else []
            spring_async_declared = any(isinstance(annotation, dict)
                                        and annotation.get("name") == "org.springframework.scheduling.annotation.Async"
                                        for annotation in annotations)
            site_edges = graph_edges.get(site["id"], [])
            spring_async_bypass = any(edge.kind == "bypasses_proxy" for edge in site_edges)
            proxy_paths = {edge.target for edge in site_edges if edge.kind == "may_traverse_proxy"}
            spring_async_proxy = any(
                (graph_nodes.get(identity) is not None
                 and graph_nodes[identity].kind == "spring_proxy_path"
                 and (graph_nodes[identity].metadata or {}).get("policy_kind") == "ASYNC"
                 and any(edge.kind == "crosses_async_boundary" for edge in graph_edges.get(identity, [])))
                for identity in proxy_paths)
            spring_async = spring_async_declared and spring_async_proxy and not spring_async_bypass
            spring_async_unknown = spring_async_declared and not spring_async_proxy and not spring_async_bypass
            coroutine = target_symbol.get("suspend") is True
            return_type = str(target_symbol.get("return_type", "")).split("<", 1)[0].rstrip("?")
            reactive = return_type in {"reactor.core.publisher.Mono", "reactor.core.publisher.Flux",
                                       "org.reactivestreams.Publisher"}
            transition = ("SPRING_ASYNC" if spring_async else "COROUTINE" if coroutine
                          else "REACTIVE_PUBLISHER" if reactive else None)
            reason = "async boundary" if spring_async else "async proxy resolution unknown" if spring_async_unknown else "coroutine boundary" if coroutine else "reactive boundary" if reactive else "unresolved/opaque callee" if target not in cfgs else "dispatch candidates" if uncertain else "recursive call" if target in ancestry else "depth limit" if depth >= max_depth else "node limit" if len(blocks) + len(cfgs[target]["blocks"]) > max_nodes else None
            source_id = ids[block["id"]]
            blocks[source_id]["original_ids"].append(site["id"])
            if spring_async_declared and spring_async_bypass:
                blocks[source_id].update(proxy_traversal=False, continuation="SYNCHRONOUS",
                                         async_scheduled=False, execution="NOT_OBSERVED",
                                         availability="UNKNOWN")
            blocks[source_id]["argument_parameter_bindings"] = argument_parameter_bindings(graph, site["id"])
            from .return_flow import return_consumer_bindings
            blocks[source_id]["return_consumer_bindings"] = return_consumer_bindings(graph, site["id"])
            blocks[source_id]["return_binding_status"] = {
                "status": site.get("return_mapping_status", "UNKNOWN"),
                "reason": site.get("return_mapping_reason", "LEGACY_RETURN_BINDINGS_UNAVAILABLE"),
                "body": site.get("return_body_status", "UNKNOWN"),
                "availability": "UNKNOWN", "execution": "NOT_OBSERVED"}
            blocks[source_id]["argument_binding_status"] = {
                "status": site.get("argument_mapping_status", "UNKNOWN"),
                "reason": site.get("argument_mapping_reason", "LEGACY_ARGUMENT_BINDINGS_UNAVAILABLE"),
                "omitted_parameters": site.get("argument_omissions", []),
                "availability": "UNKNOWN", "execution": "NOT_OBSERVED"}
            if reason:
                blocks[source_id]["boundary_reason"] = reason
                if transition:
                    blocks[source_id].update(boundary_kind=transition, continuation="SEPARATE",
                                             execution="NOT_OBSERVED", availability="UNKNOWN")
                elif spring_async_unknown:
                    blocks[source_id].update(boundary_kind="SPRING_ASYNC_PROXY",
                                             continuation="UNKNOWN", execution="NOT_OBSERVED",
                                             availability="UNKNOWN")
                omitted.append({"call_site": site["id"], "target": target, "reason": reason})
                continue
            # A single lexical call-site can have several structural CFG clones
            # (for example finally continuations for return and throw). Keep
            # those caller contexts separate without changing the original site.
            child_entry, child_exit, child_exception = expand(
                target, depth + 1, ancestry + (target,), prefix + (site["id"], block["id"]))
            normal = [e for e in local_edges if e["source"] == source_id and e["kind"] == "normal"]
            exceptional = [e for e in local_edges if e["source"] == source_id and e["kind"] == "exception"]
            local_edges = [e for e in local_edges if e not in normal and e not in exceptional]
            local_edges.append({"source": source_id, "target": child_entry, "kind": "call",
                                "call_site": site["id"], "caller_block": block["id"],
                                "original_ids": [site["id"], block["id"]]})
            local_edges.extend({**e, "source": child_exit, "kind": "returns_to", "call_site": site["id"],
                                "caller_block": block["id"],
                                "original_ids": sorted(set(e.get("original_ids", []) + [site["id"], block["id"]]))} for e in normal)
            local_edges.extend({**e, "source": child_exception, "kind": "exception", "call_site": site["id"],
                                "caller_block": block["id"],
                                "original_ids": sorted(set(e.get("original_ids", []) + [site["id"], block["id"]]))} for e in exceptional)
        edges.extend(local_edges)
        return ids[cfg["entry"]], ids[cfg["exit"]], ids[cfg["exceptional_exit"]]

    first, last, exceptional = expand(entry, 0, (entry,), (entry,))
    from .dataflow import http_request_inventory
    http = http_request_inventory(graph, callers=expanded_methods)
    from .kafka_retry import policy_boundaries
    kafka_policy = policy_boundaries(policy_input, expanded_methods)
    policy_diagnostics=[{'code':'KAFKA_POLICY_UNRESOLVED','policy_id':row['policy_id'],
                         'source':row['source'],'reasons':row['reasons']} for row in kafka_policy if row['status']=='UNKNOWN']
    return {"schema_version": 1, "view": "process", "entry": entry, "scope": scope, "contexts": graph.contexts,
            "status": "PARTIAL" if omitted or policy_diagnostics or any(cfgs[m].get("diagnostics") for m in expanded_methods) else "COMPLETE_WITHIN_SUPPORTED_SYNTAX",
            "diagnostics": [d for m in sorted(expanded_methods) for d in cfgs[m].get("diagnostics", [])]+policy_diagnostics, "truncated": any(o["reason"].endswith("limit") for o in omitted),
            "cfg": {"entry": first, "exit": last, "exceptional_exit": exceptional,
                    "blocks": sorted(blocks.values(), key=lambda b: b["id"]),
                    "edges": sorted(edges, key=lambda e: (e["source"], e["target"], e["kind"]))},
            "http": http, "kafka_policy_boundaries": kafka_policy, "boundaries": omitted, "strongly_connected_components": strongly_connected(graph),
            "limits": {"max_depth": max_depth, "max_nodes": max_nodes},
            "limitations": ["Static expansion is not proof of runtime dispatch, input feasibility or global async order."]}


def mermaid(report):
    cfg = report["cfg"]
    lines = ["flowchart TD"]
    ids = {b["id"]: "n" + digest(b["id"])[:20] for b in cfg["blocks"]}
    for block in sorted(cfg["blocks"], key=lambda b: b["id"]):
        label = _label(block.get("label", block["kind"]))
        if block.get("boundary_reason"):
            label += "<br/>" + _label(block["boundary_reason"])
        shape = '{"' + label + '"}' if block["kind"] in {"condition", "exception_dispatch"} else '["' + label + '"]'
        lines.append("  " + ids[block["id"]] + shape)
    for edge in sorted(cfg["edges"], key=lambda e: (e["source"], e["target"], e["kind"])):
        if edge["source"] not in ids or edge["target"] not in ids:
            raise AnalysisError("Renderer received dangling CFG edge")
        label = _label(edge.get("condition") or edge["kind"])
        arrow = "-.->" if edge["kind"] in {"exception", "resume", "suspend", "async"} else "-->"
        lines.append(f"  {ids[edge['source']]} {arrow}|{label}| {ids[edge['target']]}")
    if report.get("truncated"):
        lines.append('  truncated["PARTIAL: traversal/node limit reached"]')
    return "\n".join(lines) + "\n"


def markdown(report):
    lines = ["# Deterministic " + report["view"] + " view", "", "- Status: " + report["status"],
             "- Scope: " + report["scope"], "- Entry: `" + report["entry"] + "`", "",
             "```mermaid", mermaid(report).rstrip(), "```", "", "## Source/provenance", ""]
    for context in report.get("contexts", []):
        lines.append("- Context: `" + context.get("id", "unknown") + "`; mode: " + str(context.get("mode", "unknown"))
                     + "; freshness: " + str(context.get("freshness", "unknown")) + "; origin trust: " + str(context.get("origin_trust", "unknown")))
    for block in report["cfg"]["blocks"]:
        position = block.get("source_range") or {}
        source = block.get("source_file")
        location = f"{source}:{position.get('start_line', '?')}" if source else "synthetic control node"
        lines.append(f"- `{block['id']}`: {location}; original IDs: " + ", ".join("`" + i + "`" for i in block.get("original_ids", [])))
    bindings = {p["id"]: p for block in report["cfg"]["blocks"] for p in block.get("return_consumer_bindings", [])}
    if bindings:
        lines.extend(["", "## Static return/consumer bindings (availability UNKNOWN)", ""])
        for p in sorted(bindings.values(), key=lambda item: item["id"]):
            lines.append("- `" + p["source"] + "` → `" + p["target"] + "`: " + p["transformation"])
    lines.extend(["", "## Coverage/limits", "", *["- " + x for x in report.get("limitations", [])]])
    if report.get("http"):
        lines.extend(["", "## HTTP request intent (runtime availability UNKNOWN)", ""])
        for item in report['http']['requests']:
            lines.append("- `" + item['id'] + "`: " + item['execution_status'])
    if report.get("kafka_policy_boundaries"):
        lines.extend(["", "## Kafka retry/DLT policy declarations (execution NOT_OBSERVED)", ""])
        for item in report['kafka_policy_boundaries']:
            lines.append("- `" + item['policy_id'] + "`: " + item['kind'] + "; " + item['status']
                         + "; delivery NOT_OBSERVED; runtime/data availability UNKNOWN")
    if report.get("truncated"):
        lines.append("- PARTIAL: diagram is truncated; omitted detail is explicitly bounded.")
    return "\n".join(lines) + "\n"
