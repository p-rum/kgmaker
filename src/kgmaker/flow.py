"""JSON-first source CFG/process rendering with preserved origin IDs."""
from __future__ import annotations

from collections import defaultdict

from .analysis_model import AnalysisError, digest
from .callgraph import strongly_connected
from .views import project
from .dataflow import argument_parameter_bindings
from .flow_report import ordered_cfg


def _control_flow(graph, entry, *, scope="production", max_nodes=500, representation="SOURCE"):
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
        # Budget includes boundary vertices. Keep a real CFG prefix only when
        # every outgoing omitted endpoint fits; otherwise shrink to an opaque root.
        order=ordered_cfg(cfg)[1]
        selected=set()
        for count in range(min(max_nodes,len(order)),0,-1):
            candidate=set(order[:count])
            omitted={e['target'] for e in cfg['edges'] if e['source'] in candidate and e['target'] not in candidate}
            if len(candidate)+len(omitted)<=max_nodes:
                selected=candidate;break
        boundaries,edges={},[]
        for edge in cfg['edges']:
            if edge['source'] not in selected: continue
            if edge['target'] in selected: edges.append(edge)
            else:
                identity='truncated:'+digest(edge['target'])[:20]
                boundaries[identity]={'id':identity,'kind':'unresolved_boundary','label':'node limit: omitted detail',
                                      'original_ids':[edge['target']]}
                edges.append({**edge,'target':identity})
        blocks=[b for b in cfg['blocks'] if b['id'] in selected]+list(boundaries.values())
        if not selected:
            identity='truncated:'+digest({'method':entry,'root':cfg['entry']})[:20]
            blocks=[{'id':identity,'kind':'unresolved_boundary','label':'node limit: root CFG omitted',
                     'original_ids':sorted({entry,cfg['entry'],cfg['exit'],cfg['exceptional_exit']})}]
        original=cfg
        cfg={**cfg,'blocks':blocks,'edges':edges,'truncated':True,
             'entry':cfg['entry'] if selected else blocks[0]['id']}
        for key in ('exit','exceptional_exit'):
            if original.get(key) not in selected:
                cfg['omitted_'+key]=original.get(key);cfg[key]=None
    return {"schema_version": 1, "view": "control-flow", "scope": scope, "entry": entry,
            "contexts": graph.contexts, "cfg": cfg, "truncated": cfg.get("truncated", False),
            "status": "PARTIAL" if cfg.get("truncated") or cfg.get("diagnostics") else "COMPLETE_WITHIN_SUPPORTED_SYNTAX",
            "limitations": cfg.get("limitations", []), "diagnostics": cfg.get("diagnostics", [])}


def _process(graph, entry, *, scope="production", max_depth=3, max_nodes=500, context_id=None):
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
                    "context_ids": [cfg["context_id"]], "evidence_ids": list(cfg.get("evidence_ids", [])),
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
        caller_admission = _cfg_admission(graph, cfg)
        expanded_methods.add(method)
        ids = {b["id"]: "process:" + digest({"path": prefix, "id": b["id"]})[:24] for b in cfg["blocks"]}
        for b in cfg["blocks"]:
            identity = ids[b["id"]]
            blocks[identity] = {**b, "id": identity, "method": method, "context_ids": [cfg["context_id"]], "evidence_ids": list(cfg.get("evidence_ids", [])), "original_ids": sorted(set(b.get("original_ids", []) + [b["id"], method]))}
        local_edges = [{**e, "source": ids[e["source"]], "target": ids[e["target"]], "context_ids": [cfg["context_id"]], "evidence_ids": list(cfg.get("evidence_ids", [])), "original_ids": [digest(e)]} for e in cfg["edges"]]
        for block in ordered_cfg(cfg)[0]["blocks"]:
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
            occurrence_admission = _site_occurrence(graph, site, cfg, block)
            admission = caller_admission or occurrence_admission or _site_admission(graph, site)
            if not admission and target in cfgs:
                callee_admission = _cfg_admission(graph, cfgs[target])
                if callee_admission:
                    admission = "callee " + callee_admission
            reason = admission or ("async boundary" if spring_async else "async proxy resolution unknown" if spring_async_unknown else "coroutine boundary" if coroutine else "reactive boundary" if reactive else "unresolved/opaque callee" if target not in cfgs else "dispatch candidates" if uncertain else "recursive call" if target in ancestry else "depth limit" if depth >= max_depth else "node limit" if len(blocks) + len(cfgs[target]["blocks"]) > max_nodes else None)
            source_id = ids[block["id"]]
            blocks[source_id]["original_ids"].append(site["id"])
            if not admission:
                if spring_async_declared and spring_async_bypass:
                    blocks[source_id].update(proxy_traversal=False, continuation="SYNCHRONOUS",
                                             async_scheduled=False, execution="NOT_OBSERVED",
                                             availability="UNKNOWN")
            if not occurrence_admission:
                # Existing bindings remain reference information even when weak
                # or stale CFG authority prevents interprocedural expansion.
                if admission:
                    blocks[source_id]["binding_projection"] = "REFERENCE_ONLY"
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
                if transition and not admission:
                    blocks[source_id].update(boundary_kind=transition, continuation="SEPARATE",
                                             execution="NOT_OBSERVED", availability="UNKNOWN")
                elif spring_async_unknown and not admission:
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
                                "context_ids": [site["context_id"]], "evidence_ids": list(site.get("evidence_ids", [])),
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



from .flow_report import finalize, mermaid, markdown, render, publish, RenderBudget


def _source_span(value):
    return (isinstance(value, dict) and type(value.get('start')) is int
            and type(value.get('end')) is int and 0 <= value['start'] <= value['end'])


def _cfg_admission(graph, cfg):
    """Require the current source-body proof of this exact CFG owner."""
    from .views import execution_authority_gaps, evidence_freshness_gaps, is_execution_entity
    nodes={n.id:n for n in graph.nodes}; symbols={s['id']:s for s in graph.symbols}
    contexts={c['id']:c for c in graph.contexts}; proofs={p['id']:p for p in graph.evidence}
    owner=nodes.get(cfg.get('method')); symbol=symbols.get(cfg.get('method'),{})
    context=contexts.get(cfg.get('context_id'),{}); refs=cfg.get('evidence_ids',[])
    if (not is_execution_entity(owner) or symbol.get('context_id')!=cfg.get('context_id')
            or context.get('scope')!=owner.scope
            or ('scope' in symbol and symbol['scope']!=owner.scope)
            or ('path' in symbol and symbol['path']!=owner.path)
            or ('sha256' in symbol and symbol['sha256']!=graph.files.get(owner.path))):
        return 'CFG owner/context/scope unavailable'
    if (not refs or execution_authority_gaps(contexts,graph.files,proofs,[cfg.get('context_id')],refs)
            or evidence_freshness_gaps(proofs,refs)):
        return 'current caller CFG authority/proof unavailable'
    for ref in refs:
        proof=proofs.get(ref,{})
        if (proof.get('kind')!='SYNTAX_CANDIDATE' or proof.get('relation')!='control_flow'
                or proof.get('source')!=cfg['method'] or proof.get('target')!=cfg['method']
                or proof.get('representation')!='SOURCE'
                or set(proof.get('context_ids',[]))!={cfg['context_id']}
                or proof.get('source_file')!=owner.path
                or not proof.get('sha256') or proof['sha256']!=graph.files.get(owner.path)
                or context.get('source_files',{}).get(owner.path)!=proof['sha256']
                or not _source_span(proof.get('source_range'))):
            return 'CFG owner/source proof mismatch or unavailable'
    return None


def _site_occurrence(graph, site, cfg, block):
    """Source identity only; it never establishes executable CFG authority."""
    nodes={node.id:node for node in graph.nodes}
    if site.get('caller')!=cfg['method']:
        return 'call-site caller does not own expanded CFG'
    if site.get('context_id')!=cfg['context_id']:
        return 'call-site context differs from expanded CFG'
    owner=nodes.get(cfg['method'])
    span=block.get('source_range'); occurrence=site.get('range')
    if (owner is None or block.get('source_file')!=owner.path or site.get('path')!=owner.path
            or nodes.get(site['id']) is None or nodes[site['id']].path!=owner.path
            or not block.get('sha256') or block['sha256']!=site.get('sha256')
            or block['sha256']!=graph.files.get(owner.path)
            or not _source_span(span) or not _source_span(occurrence) or span!=occurrence):
        return 'call-site source occurrence differs from CFG block'
    proofs={p['id']:p for p in graph.evidence}
    for ref in cfg.get('evidence_ids',[]):
        body=proofs.get(ref,{}).get('source_range')
        if _source_span(body) and not body['start']<=span['start']<=span['end']<=body['end']:
            return 'call-site occurrence outside caller CFG body'
    return None


def _site_admission(graph, site):
    from .views import execution_authority_gaps, evidence_freshness_gaps, is_execution_callsite, is_execution_entity
    nodes={node.id:node for node in graph.nodes}
    endpoints=[nodes.get(site.get(key)) for key in ("caller","id","declared_target")]
    if not all(is_execution_entity(node) for node in endpoints):
        return "non-executable caller/site/target role"
    if (len({node.scope for node in endpoints})!=1
            or ('scope' in site and site['scope']!=endpoints[0].scope)):
        return "cross-scope execution boundary"
    if not is_execution_callsite(site):
        return "non-execution call-site kind"
    if site.get('evidence_kind') not in {'SYMBOL_RESOLVED','DISPATCH_CANDIDATE'}:
        return "resolved static call-site proof unavailable"
    contexts={c['id']:c for c in graph.contexts}; proofs={p['id']:p for p in graph.evidence}
    refs=site.get('evidence_ids',[])
    if not refs or execution_authority_gaps(contexts,graph.files,proofs,[site.get('context_id')],refs,site) or evidence_freshness_gaps(proofs,refs):
        return "current compiler authority/proof unavailable"
    links=[('declares_call',site['caller'],site['id']),('resolves_to',site['id'],site.get('declared_target'))]
    for kind,source,target in links:
        witnesses=[e for e in graph.edges if (e.kind,e.source,e.target)==(kind,source,target)
                   and e.evidence_kind in {'SYMBOL_RESOLVED','DISPATCH_CANDIDATE'}]
        if not any(e.evidence_ids and not execution_authority_gaps(contexts,graph.files,proofs,e.context_ids,e.evidence_ids,site)
                   and not evidence_freshness_gaps(proofs,e.evidence_ids) for e in witnesses):
            return "current executable caller/site/target path unavailable"
    return None


def build_report(graph, entry, *, view='control-flow', scope='production', max_depth=3,
                 max_nodes=500, context_id=None, representation='SOURCE', budget=None):
    from .model import KnowledgeGraph
    from .views import select_context
    if representation not in {'SOURCE','BYTECODE'} or (view=='process' and representation!='SOURCE'):
        raise AnalysisError('Unsupported flow representation')
    if view not in {'control-flow','process','integrations','data-flow'}:
        raise AnalysisError('Unsupported flow view')
    if type(max_depth) is not int or type(max_nodes) is not int or max_depth<0 or max_nodes<1:
        raise AnalysisError('Invalid traversal limits')
    if budget: budget.check()
    graph=KnowledgeGraph.from_dict(graph.to_dict())
    policy_graph=graph
    if context_id is None:
        context_id=select_context(graph,scope)
    graph=project(graph,scope,context_id=context_id)
    if entry not in {n.id for n in graph.nodes}:
        raise AnalysisError('Flow entry is absent from selected scope/context')
    if budget: budget.check()
    if view in {'control-flow','process'}:
        variants=[c for c in graph.cfgs if c['method']==entry and c.get('representation')==representation]
        if not variants:
            report={'schema_version':1,'view':view,'entry':entry,'scope':scope,'contexts':graph.contexts,
                    'cfg':{'entry':None,'exit':None,'exceptional_exit':None,'blocks':[],'edges':[]},
                    'status':'UNKNOWN','truncated':False,'diagnostics':[],
                    'limitations':['Missing CFG does not establish absence of executable behavior.']}
        elif view=='control-flow':
            report=_control_flow(graph,entry,scope=scope,max_nodes=max_nodes,representation=representation)
        else:
            report=_process(policy_graph,entry,scope=scope,max_depth=max_depth,max_nodes=max_nodes,context_id=context_id)
    else:
        from .dataflow import http_request_inventory
        from .return_flow import return_consumer_bindings
        selected=project(graph,scope,view=view,context_id=context_id)
        chosen=sorted(selected.nodes,key=lambda n:(n.id!=entry,n.id))[:max_nodes]
        ids={n.id for n in chosen}; edges=[e for e in selected.edges if e.source in ids and e.target in ids]
        report={'schema_version':1,'view':view,'entry':entry,'scope':scope,'contexts':selected.contexts,
                'status':'PARTIAL','truncated':len(chosen)<len(selected.nodes),'diagnostics':[],
                'nodes':[n.id for n in chosen],'edges':[e.__dict__ for e in edges],
                'cfg':{'entry':entry,'blocks':[{'id':n.id,'kind':n.kind,'label':n.name,'source_file':n.path,
                    'original_ids':[n.id],'context_ids':sorted({c for e in edges if n.id in {e.source,e.target} for c in e.context_ids}),
                    'evidence_ids':sorted({p for e in edges if n.id in {e.source,e.target} for p in e.evidence_ids})} for n in chosen],
                    'edges':[e.__dict__ for e in edges]},'http':http_request_inventory(selected),
                'limitations':['Relationship view is not an executable CFG or evidence of runtime availability.']}
        if view=='data-flow': report['return_consumer_bindings']=return_consumer_bindings(selected)
    report.setdefault('limits',{'max_nodes':max_nodes,'max_depth':max_depth})
    report['diagnostics']=report.get('diagnostics',[])+[d for d in graph.diagnostics if d.get('code')=='COMPILER_CONTEXT_BOUNDARY_UNKNOWN']
    result=finalize(report,graph)
    if budget: budget.check()
    return result


def control_flow(graph, entry, *, scope='production', max_nodes=500, representation='SOURCE'):
    return build_report(graph,entry,scope=scope,max_nodes=max_nodes,representation=representation)


def process(graph, entry, *, scope='production', max_depth=3, max_nodes=500, context_id=None):
    return build_report(graph,entry,view='process',scope=scope,max_depth=max_depth,max_nodes=max_nodes,context_id=context_id)
