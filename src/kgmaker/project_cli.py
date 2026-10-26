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
    parser.add_argument("--workspace", type=Path, help="workspace manifest selecting an explicit checkout")
    parser.add_argument("--repo", help="repository ID in --workspace")
    parser.add_argument("--format", choices=("json",), default="json")
    parser.add_argument("--strict", action="store_true", help="fail with exit 4 if coverage is partial")


def register(sub):
    command = sub.add_parser("project", help="project inventory, classification and explicit build workflows")
    actions = command.add_subparsers(dest="project_command", required=True)
    p = actions.add_parser("build-import", help="validate/import an existing content-bound build manifest; never executes a build")
    common(p)
    p.add_argument("--manifest", type=Path, required=True)
    p = actions.add_parser("build-plan", help="prepare explicit content-bound build execution; does not execute")
    common(p)
    p.add_argument("--phase", choices=("compile", "test-compile", "test"), default="test-compile")
    p.add_argument("--build-system", choices=("maven", "gradle"))
    p.add_argument("--executable")
    p.add_argument("--profile", action="append", default=[])
    p.add_argument("--timeout", type=float, default=300)
    p.add_argument("--worker-home", type=Path)
    p.add_argument("--java-home", type=Path,
                   help="explicit JDK home bound into the plan and enforced during build execution")
    p.add_argument("--output", type=Path)
    p.add_argument("--offline", action="store_true")
    p = actions.add_parser("build-run", help="execute one explicit content-bound LOCAL_TRUSTED plan")
    common(p)
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--cancel-file", type=Path)
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
    p.add_argument("--context")
    p = actions.add_parser("view")
    common(p)
    p.add_argument("--scope", choices=sorted(SCOPES | {"all"}), default="production")
    p.add_argument("--view", choices=("architecture", "calls", "configuration", "integrations"), default="architecture")
    p.add_argument("--context")
    command = sub.add_parser("coverage", help="report scoped source coverage and freshness")
    p = command.add_subparsers(dest="coverage_command", required=True).add_parser("report")
    common(p)
    p.add_argument("--scope", choices=sorted(SCOPES | {"all"}), default="production")
    p.add_argument("--context")


def run(args):
    try:
        root = args.root.resolve()
        if getattr(args, "workspace", None):
            from .workspace import load_workspace
            manifest = load_workspace(args.workspace)
            matches = [repo for repo in manifest["repositories"] if repo["id"] == args.repo]
            if len(matches) != 1:
                raise AnalysisError("--workspace requires an existing --repo")
            root = Path(matches[0]["_root"])
        if not root.is_dir():
            raise AnalysisError("root directory does not exist")
        if args.command == "project" and args.project_command == "build-import":
            from .build_model import import_manifest
            result = import_manifest(root, read_json(args.manifest))
            print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
            return 4 if args.strict and result["status"] == "PARTIAL" else 0
        if args.command == "project" and args.project_command in {"build-plan", "build-run"}:
            from .build_runner import create_plan, run_plan
            from .analysis_model import write_json
            if args.project_command == "build-plan":
                result = create_plan(root, phase=args.phase, build_system=args.build_system, executable=args.executable,
                                     profiles=args.profile, timeout=args.timeout, home=args.worker_home,
                                     offline=args.offline, java_home=args.java_home)
                if args.output:
                    write_json(args.output, result)
                code = 0
            else:
                result = run_plan(read_json(args.plan), cancel_file=args.cancel_file)
                code = 0 if result["result"]["status"] == "SUCCESS" else 3
                if args.strict and result["status"] == "PARTIAL":
                    code = 4
            print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
            return code
        model = read_json(args.model) if getattr(args, "model", None) else None
        if args.command == "graph" and args.graph_command == "migrate":
            from .store import save_graph
            stored = load_graph(root)
            if stored is None:
                raise AnalysisError("missing or invalid graph index")
            migrated = stored.migrate_legacy()
            save_graph(migrated, root, generate_docs=False)
            print(json.dumps({"status": "PARTIAL", "schema_version": migrated.schema_version, "contexts": migrated.contexts,
                              "diagnostics": migrated.diagnostics}))
            return 4 if args.strict else 0
        graph = scan_repository(root, project_model=model, strict=args.strict)
        files = [n for n in graph.nodes if n.kind == "file"]
        status = "PARTIAL"
        if args.command == "project":
            build_model = None
            if args.project_command == "inspect" and (root / "pom.xml").is_file():
                from .build_maven import discover
                build_model = discover(root)
            result = {"schema_version": 1, "status": status, "mode": "SOURCE_ONLY",
                      "contexts": graph.contexts, "diagnostics": graph.diagnostics,
                      "files": [asdict(n) for n in files],
                      "symbols": [asdict(n) for n in graph.nodes if n.kind != "file"],
                      "build_systems": [name for name, path in (("maven", "pom.xml"), ("gradle", "build.gradle"),
                            ("gradle-kotlin", "build.gradle.kts"), ("typescript", "tsconfig.json")) if (root / path).is_file()],
                      "build_model": build_model,
                      "limitations": ["Inventory and supplied source sets are not an effective Maven/Gradle build model.",
                                       "No build script, compiler, application or database has been executed."]}
        else:
            stored = load_graph(root)
            freshness = "MISSING_INDEX" if stored is None else "FRESH" if stored.files == graph.files and stored.contexts == graph.contexts else "STALE"
            if stored is not None and stored.schema_version == 3:
                from .inspection_cli import indexed
                graph = indexed(args)
                freshness = "CONTENT_VERIFIED"
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
            if args.command == "coverage" and graph.schema_version == 3:
                contexts = [c for c in graph.contexts if c.get("analyzer_version")]
                coverage = contexts[0].get("coverage", {}) if contexts else {}
                result.update(mode=contexts[0].get("mode") if contexts else None, contexts=graph.contexts,
                              methods_compiler_analyzed=coverage.get("methods_analyzed", 0),
                              call_sites_compiler_resolved=coverage.get("calls_resolved", 0),
                              resolution_ratio={"numerator": coverage.get("calls_resolved", 0), "denominator": coverage.get("calls_found")},
                              diagnostics=graph.diagnostics, limitations=["Coverage applies only to the selected compiler context and supported matrix."])
            result["freshness"] = freshness
            result["analysis_source"] = "VALIDATED_COMPILER_INDEX" if graph.schema_version == 3 else "CURRENT_SOURCE_IN_MEMORY"
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 4 if args.strict and result["status"] == "PARTIAL" else 0
    except (AnalysisError, ValueError, TypeError, OSError) as error:
        code = getattr(error, "code", 2)
        status = "REJECTED_SNAPSHOT" if code == 3 else "STRICT_COVERAGE_FAILED" if code == 4 else "INVALID_INPUT"
        print(json.dumps({"status": status, "diagnostics": [str(error)]}))
        return code
