"""Explicit compiler navigation/render commands; never an implicit build."""
from __future__ import annotations

import json
from pathlib import Path

from .analysis_model import AnalysisError, read_json
from .inspection import inspect_frontend, inspect_jvm
from .store import GRAPH_FILE, load_graph
from .worker_protocol import WorkerError


def common(parser):
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--scope", choices=("production", "test", "test_fixture", "development", "unknown", "all"), default="production")
    parser.add_argument("--context")
    parser.add_argument("--strict", action="store_true")


def register(sub):
    inspect = sub.add_parser("inspect", help="explicit offline compiler inspection (does not build the project)")
    kinds = inspect.add_subparsers(dest="inspection_kind", required=True)
    for name in ("code", "frontend"):
        p = kinds.add_parser(name)
        common(p)
        p.add_argument("--worker-home", type=Path)
        p.add_argument("--timeout", type=float, default=120)
        p.add_argument("--cancel-file", type=Path)
        p.add_argument("--repo-id", default="local")
        p.add_argument("--module", default="root" if name == "code" else "frontend")
        p.add_argument("--source-set", default="main")
        p.add_argument("--manifest", type=Path)
        p.add_argument("--format", choices=("json",), default="json")
        if name == "frontend":
            p.add_argument("--tsconfig", default="tsconfig.json")
            p.add_argument("--ui-framework", choices=("react", "angular", "vue"))
        else:
            p.add_argument("--build-id")
            p.add_argument("--classpath", action="append", default=[])
            p.add_argument("--kotlin-backend", choices=("k1", "k2"), default="k1")
            p.add_argument("--kotlin-version", default="2.1.10", help="pinned compiler version; unsupported versions fail before publication")
    graph = sub.add_parser("callgraph", help="compiler callers/callees and bounded static paths")
    actions = graph.add_subparsers(dest="callgraph_command", required=True)
    for name in ("callers", "callees", "path"):
        p = actions.add_parser(name)
        common(p)
        p.add_argument("--format", choices=("json",), default="json")
        if name == "path":
            p.add_argument("--from", dest="from_symbol", required=True)
            p.add_argument("--to", dest="to_symbol", required=True)
            p.add_argument("--max-depth", type=int, default=30)
        else:
            p.add_argument("--symbol", required=True)
        p.add_argument("--include-dispatch-candidates", action="store_true")
    p = sub.add_parser("entrypoints", help="show evidence-backed entrypoints from the selected compiler context")
    common(p); p.add_argument("--format", choices=("json",), default="json")
    flow = sub.add_parser("flow", help="deterministic source CFG/process rendering")
    p = flow.add_subparsers(dest="flow_command", required=True).add_parser("render")
    common(p)
    p.add_argument("--entry", required=True)
    p.add_argument("--view", choices=("control-flow", "process", "integrations", "data-flow"), default="control-flow")
    p.add_argument("--format", choices=("json", "mermaid", "markdown"), default="mermaid")
    p.add_argument("--max-depth", type=int, default=3)
    p.add_argument("--max-nodes", type=int, default=500)
    runtime = sub.add_parser("runtime", help="import scoped runtime observations; never starts the application")
    actions = runtime.add_subparsers(dest="runtime_command", required=True)
    p = actions.add_parser("import", help="validate and import a sanitized runtime manifest")
    p.add_argument("--root", type=Path, default=Path.cwd())
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--format", choices=("json",), default="json")


def indexed(args):
    root = args.root.resolve()
    graph = load_graph(root)
    if graph is None:
        raise AnalysisError("INVALID_INDEX" if (root / GRAPH_FILE).exists() else "MISSING_INDEX: run an explicit compiler inspection")
    if graph.schema_version != 3:
        raise AnalysisError("UNSUPPORTED_INDEX: source-only/legacy index has no compiler call sites or CFG")
    from .graph_provider import validate_compiler_snapshot
    validate_compiler_snapshot(root, graph)
    all_contexts = [c for c in graph.contexts if c.get("analyzer_version")]
    stale = [c for c in all_contexts if c.get("freshness") == "STALE"]
    contexts = [c for c in all_contexts if c.get("freshness") != "STALE"]
    if args.context:
        invalid = [c for c in stale if c["id"] == args.context]
        if invalid:
            raise AnalysisError("STALE_INDEX: " + invalid[0].get("stale_reason", "context is stale")
                                + "; run `" + invalid[0]["next_command"] + "`")
        selected = [c for c in contexts if c["id"] == args.context]
        if not selected:
            raise AnalysisError("Unknown analysis context; available: " + ", ".join(c["id"] for c in contexts))
    else:
        selected = [c for c in contexts if args.scope == "all" or c.get("scope") == args.scope]
        if len(selected) > 1:
            raise AnalysisError("Explicit --context required; available: " + ", ".join(c["id"] for c in selected))
    if len(selected) != 1:
        raise AnalysisError("No matching compiler analysis context")
    if getattr(args,"command",None)=="flow" and getattr(args,"view",None)=="process":
        # Preserve original proof tuples until process applies its selected CFG
        # scope. Otherwise projection could hide a malformed cross-scope edge.
        args._flow_context_id=selected[0]["id"]
        return graph
    from .views import project
    return project(graph, args.scope, context_id=selected[0]["id"])


def run(args):
    try:
        if args.command == "runtime":
            from .runtime_evidence import import_manifest
            result = import_manifest(args.root.resolve(), read_json(args.manifest))
            print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
            return 0
        if args.command == "inspect":
            options = dict(scope=args.scope, repo_id=args.repo_id, module=args.module, source_set=args.source_set,
                           home=args.worker_home, timeout=args.timeout, cancel_file=args.cancel_file, strict=args.strict)
            if args.scope == "all":
                raise AnalysisError("Compiler inspection requires a concrete source-set scope")
            if args.inspection_kind == "frontend":
                if args.manifest:
                    manifest = read_json(args.manifest)
                    options.update({k: manifest[k] for k in ("scope", "repo_id", "module", "source_set") if k in manifest})
                    result = inspect_frontend(args.root, tsconfig=manifest.get("tsconfig", args.tsconfig),
                                              ui_framework=manifest.get("ui_framework", args.ui_framework), **options)
                else:
                    result = inspect_frontend(args.root, tsconfig=args.tsconfig, ui_framework=args.ui_framework, **options)
            else:
                options.update(kotlin_backend=args.kotlin_backend, kotlin_version=args.kotlin_version)
                manifest = args.manifest
                if args.build_id:
                    from .analysis_model import safe_path
                    manifest = safe_path(args.root, ".kgmaker/builds/" + args.build_id + "/manifest.json")
                if manifest:
                    from .build_model import inspection_inputs
                    imported = inspection_inputs(args.root.resolve(), read_json(manifest), context_id=args.context, scope=args.scope)
                    result = inspect_jvm(args.root, **{**options, **imported})
                else:
                    result = inspect_jvm(args.root, classpath=args.classpath, **options)
            code = result.pop("exit_code", 0)
            print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
            return code
        graph = indexed(args)
        if args.command == "callgraph":
            from . import callgraph
            if args.callgraph_command == "callees":
                result = callgraph.callees(graph, args.symbol, scope=args.scope, include_candidates=args.include_dispatch_candidates)
            elif args.callgraph_command == "callers":
                result = callgraph.callers(graph, args.symbol, scope=args.scope)
            else:
                result = callgraph.path(graph, args.from_symbol, args.to_symbol, scope=args.scope,
                                        max_depth=args.max_depth, include_candidates=args.include_dispatch_candidates)
        elif args.command == "entrypoints":
            from .views import project
            selected = project(graph, args.scope)
            results = []
            generated = {node.id: node for node in selected.nodes
                          if node.kind in {"spring_entrypoint", "spring_endpoint"}}
            for node in generated.values():
                results.append({"id": node.id, "kind": node.kind, "name": node.name,
                                "path": node.path, "line": node.line,
                                "metadata": node.metadata or {},
                                "evidence_kind": "FRAMEWORK_DERIVED"})
            for s in selected.symbols:
                annotations = {a.get("name") for a in s.get("annotations", [])}
                supported = annotations & {"org.springframework.web.bind.annotation.GetMapping", "org.springframework.web.bind.annotation.PostMapping",
                    "org.springframework.web.bind.annotation.RequestMapping", "org.springframework.kafka.annotation.KafkaListener",
                    "org.springframework.scheduling.annotation.Scheduled", "org.springframework.context.event.EventListener"}
                if supported or (s.get("name") == "main" and s.get("descriptor") == "([Ljava/lang/String;)V"):
                    results.append({"id": s["id"], "kind": "compiler_entrypoint", "annotations": sorted(supported),
                                    "path": s.get("path"), "range": s.get("range"), "evidence_kind": "SYMBOL_RESOLVED"})
            result = {"status": "PARTIAL" if selected.diagnostics else "COMPLETE_WITHIN_INDEXED_SCOPE", "scope": args.scope,
                      "contexts": selected.contexts, "results": sorted(results, key=lambda r: r["id"]),
                      "limitations": ["Generated framework entrypoints are annotation-derived; runtime registration is not observed."]}
        else:
            from . import flow
            if args.view == "control-flow":
                result = flow.control_flow(graph, args.entry, scope=args.scope, max_nodes=args.max_nodes)
            elif args.view == "process":
                result = flow.process(graph, args.entry, scope=args.scope, max_depth=args.max_depth, max_nodes=args.max_nodes, context_id=getattr(args,"_flow_context_id",None))
            else:
                from .views import project
                selected = project(graph, args.scope, view=args.view)
                result = {"status": "PARTIAL", "view": args.view, "scope": args.scope, "contexts": selected.contexts,
                          "entry": args.entry, "nodes": [n.id for n in selected.nodes], "edges": [e.__dict__ for e in selected.edges]}
                from .dataflow import http_request_inventory
                result["http"] = http_request_inventory(selected)
                if args.format != "json":
                    raise AnalysisError("Integration/data views require --format json until the framework view renderer is available")
            if args.format == "mermaid":
                print(flow.mermaid(result), end="")
                return 4 if args.strict and result["status"] == "PARTIAL" else 0
            if args.format == "markdown":
                print(flow.markdown(result), end="")
                return 4 if args.strict and result["status"] == "PARTIAL" else 0
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 4 if args.strict and result.get("status") in {"PARTIAL", "UNKNOWN"} else 0
    except (AnalysisError, ValueError, OSError) as error:
        print(json.dumps({"status": getattr(error, "status", "INVALID_INPUT"), "diagnostics": [str(error)]}, ensure_ascii=False))
        return getattr(error, "code", 2)
