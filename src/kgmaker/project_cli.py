"""Offline project classification and scoped views over the existing graph."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .analysis_model import AnalysisError, read_json
from .classification import SCOPES
from .scanner import scan_repository
from .store import load_graph
from .views import project, rank


def common(parser):
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--format", choices=("json",), default="json")
    parser.add_argument("--strict", action="store_true", help="fail with exit 4 if coverage is partial")


def register(sub):
    command = sub.add_parser("project", help="offline project inventory and classification (never executes a build)")
    actions = command.add_subparsers(dest="project_command", required=True)
    for action in ("inspect", "classify"):
        p = actions.add_parser(action)
        common(p)
        p.add_argument("--model", type=Path, help="import source_sets JSON; supplied model is not an effective build export")
        p.add_argument("--explain", action="store_true")
    command = sub.add_parser("graph", help="scope projection and purpose-specific deterministic ranking")
    actions = command.add_subparsers(dest="graph_command", required=True)
    p = actions.add_parser("migrate", help="conservatively migrate the stored v1 index to v2")
    common(p)
    p = actions.add_parser("rank")
    common(p)
    p.add_argument("--entry")
    p.add_argument("--scope", choices=sorted(SCOPES | {"all"}), default="production")
    p.add_argument("--profile", choices=("execution", "impact"), default="execution")
    p.add_argument("--explain", action="store_true")
    p = actions.add_parser("view")
    common(p)
    p.add_argument("--scope", choices=sorted(SCOPES | {"all"}), default="production")
    p.add_argument("--view", choices=("architecture", "calls", "configuration", "integrations"), default="architecture")
    command = sub.add_parser("coverage", help="report scoped source coverage and freshness")
    p = command.add_subparsers(dest="coverage_command", required=True).add_parser("report")
    common(p)
    p.add_argument("--scope", choices=sorted(SCOPES | {"all"}), default="production")


def run(args):
    try:
        root = args.root.resolve()
        if not root.is_dir():
            raise AnalysisError("root directory does not exist")
        model = read_json(args.model) if getattr(args, "model", None) else None
        if args.command == "graph" and args.graph_command == "migrate":
            from .store import save_graph
            stored = load_graph(root)
            if stored is None:
                raise AnalysisError("missing or invalid graph index")
            migrated = stored.migrate_legacy()
            save_graph(migrated, root, generate_docs=False)
            print(json.dumps({"status": "PARTIAL", "schema_version": 2, "contexts": migrated.contexts,
                              "diagnostics": migrated.diagnostics}))
            return 4 if args.strict else 0
        graph = scan_repository(root, project_model=model, strict=args.strict)
        files = [n for n in graph.nodes if n.kind == "file"]
        status = "PARTIAL"
        if args.command == "project":
            result = {"schema_version": 1, "status": status, "mode": "SOURCE_ONLY",
                      "contexts": graph.contexts, "diagnostics": graph.diagnostics,
                      "files": [asdict(n) for n in files],
                      "symbols": [asdict(n) for n in graph.nodes if n.kind != "file"],
                      "build_systems": [name for name, path in (("maven", "pom.xml"), ("gradle", "build.gradle"),
                            ("gradle-kotlin", "build.gradle.kts"), ("typescript", "tsconfig.json")) if (root / path).is_file()],
                      "limitations": ["Inventory and supplied source sets are not an effective Maven/Gradle build model.",
                                       "No build script, compiler, application or database has been executed."]}
        else:
            stored = load_graph(root)
            freshness = "MISSING_INDEX" if stored is None else "FRESH" if stored.files == graph.files and stored.contexts == graph.contexts else "STALE"
            if args.command == "graph" and args.graph_command == "rank":
                result = rank(graph, args.entry, args.profile, args.scope)
            elif args.command == "graph":
                result = {"status": status, "scope": args.scope, "view": args.view,
                          "graph": project(graph, args.scope, view=args.view).to_dict()}
            else:
                selected = [n for n in files if args.scope == "all" or n.scope == args.scope]
                result = {"status": status, "mode": "SOURCE_ONLY", "scope": args.scope,
                          "files_found": len(files), "files_in_scope": len(selected),
                          "files_unknown_scope": sum(n.scope == "unknown" for n in files),
                          "methods_compiler_analyzed": 0, "call_sites_compiler_resolved": 0,
                          "resolution_ratio": {"numerator": 0, "denominator": None},
                          "contexts": graph.contexts, "diagnostics": graph.diagnostics,
                          "limitations": ["No compiler resolution or CFG coverage in this source-only index.",
                                           "Unknown scope is omitted from production projection."]}
            result["freshness"] = freshness
            result["analysis_source"] = "CURRENT_SOURCE_IN_MEMORY"
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 4 if args.strict and result["status"] == "PARTIAL" else 0
    except (AnalysisError, ValueError, TypeError, OSError) as error:
        code = getattr(error, "code", 2)
        status = "REJECTED_SNAPSHOT" if code == 3 else "STRICT_COVERAGE_FAILED" if code == 4 else "INVALID_INPUT"
        print(json.dumps({"status": status, "diagnostics": [str(error)]}))
        return code
