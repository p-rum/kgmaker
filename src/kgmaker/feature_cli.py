"""Argparse integration kept separate from the legacy CLI contracts."""
from __future__ import annotations

import json
from pathlib import Path

from . import feature
from .analysis_model import AnalysisError, atomic_write, digest, inventory_candidate, read_json, safe_path
from .analysis_report import render_report, report_projection
from .analysis_validation import validate_candidate


def register(subparsers):
    parser = subparsers.add_parser("feature", help="offline, isolated feature feasibility analysis")
    commands = parser.add_subparsers(dest="feature_command", required=True)
    for command in ("prepare", "validate", "apply", "report", "status", "revise", "compare", "data-check"):
        child = commands.add_parser(command)
        child.add_argument("--root", type=Path, default=Path.cwd())
        child.add_argument("--workspace", type=Path)
        child.add_argument("--scope", choices=("production", "test", "test_fixture", "development", "unknown", "all"))
        child.add_argument("--context")
        child.add_argument("--require-complete", action="store_true")
        if command == "prepare":
            child.add_argument("--requirement", required=True)
            child.add_argument("--id", required=True)
            child.add_argument("--token-budget", type=int, default=8000)
        else:
            child.add_argument("--analysis", required=True)
        if command in {"validate", "apply"}:
            child.add_argument("--candidate", required=True)
        if command == "revise":
            child.add_argument("--answers", required=True)
        if command == "compare":
            child.add_argument("--variant", required=True)
        if command == "data-check":
            child.add_argument("--inputs", required=True)
            child.add_argument("--format", choices=("markdown", "json"), default="json")
        if command == "report":
            child.add_argument("--output")
            child.add_argument("--format", choices=("markdown", "json"), default="markdown")


def run(args) -> int:
    root = args.root.resolve()
    try:
        command = args.feature_command
        if command != 'prepare' and args.workspace:
            packet = feature.load_packet(root, args.analysis)
            if packet.get('workspace', {}).get('manifest_path') != str(args.workspace.resolve()):
                raise AnalysisError('Command workspace differs from analysis workspace')
        if command != 'prepare' and (args.scope is not None or args.context is not None):
            packet = feature.load_packet(root, args.analysis)
            requested = {"scope": args.scope or packet.get("graph_selection", {}).get("scope", "all"),
                         "context_id": args.context if args.context is not None else packet.get("graph_selection", {}).get("context_id")}
            if requested != packet.get("graph_selection", {"scope": "all", "context_id": None}):
                raise AnalysisError("Command graph selection differs from analysis packet; prepare a new revision")
        if command == "prepare":
            packet = feature.prepare(root, args.requirement, args.id, args.token_budget,
                                     workspace=args.workspace, scope=args.scope or "all",
                                     context_id=args.context)
            result = {"analysis_id": args.id, "revision": packet["revision"], "packet_id": packet["packet_id"],
                      "completion": inventory_candidate(packet)["completion"], "budget": packet["budget"],
                      "template": f".kgmaker/analyses/{args.id}/candidate-template.json", "exit_code": 0}
        elif command == "data-check":
            from .data_check import data_check
            result = data_check(root, args.analysis, read_json(safe_path(root, args.inputs)))
        elif command in {"validate", "apply"}:
            candidate = read_json(safe_path(root, args.candidate))
            result = getattr(feature, command)(root, args.analysis, candidate)
        elif command == "revise":
            packet = feature.revise(root, args.analysis, read_json(safe_path(root, args.answers)))
            result = {"revision": packet["revision"], "packet_id": packet["packet_id"],
                      "completion": inventory_candidate(packet)["completion"], "exit_code": 0}
        elif command == "compare":
            candidate = read_json(safe_path(root, f".kgmaker/analyses/{args.analysis}/analysis.json"))
            result = feature.validate(root, args.analysis, candidate)
            if result["valid"]:
                variants = [v for v in candidate["alternatives"] if v["id"] == args.variant or v["name"] == args.variant]
                if len(variants) != 1:
                    raise AnalysisError("Variant must identify exactly one existing alternative; CLI does not invent variants")
                result.update({"baseline": candidate["baseline"], "variant": variants[0],
                               "changes": candidate["changes"], "questions": candidate["questions"]})
        elif command == "status":
            result = feature.status(root, args.analysis)
        else:
            from .report_publication import ReportGuard
            guard = ReportGuard(root)
            packet = guard.read(safe_path(root, f".kgmaker/analyses/{args.analysis}/packet.json"),
                                lambda: feature.load_packet(root, args.analysis))
            path = safe_path(root, f".kgmaker/analyses/{args.analysis}/analysis.json")
            guard.watch(path)
            applied = path.exists()
            candidate = guard.read(path) if applied else inventory_candidate(packet)
            # Historical reports must validate against the exact revision they used.
            historical = packet
            if candidate.get("packet_id") != packet["packet_id"]:
                historical = guard.read(safe_path(root, f".kgmaker/analyses/{args.analysis}/history/packet-{candidate['revision']}.json"))
                if candidate.get("packet_id") != historical.get("packet_id") or historical.get("packet_id") != feature.packet_identity(historical):
                    raise AnalysisError("Historical packet integrity mismatch")
            guard.bind_sources(historical)
            stale = feature.freshness(root, historical)
            from .availability import observation_staleness
            observed_stale = observation_staleness(candidate)
            stale += observed_stale
            if historical != packet:
                stale.append("Newer analysis packet exists; report uses a historical revision")
            if applied:
                receipt = guard.read(safe_path(root, f".kgmaker/analyses/{args.analysis}/receipts/{candidate['revision']}.json"))
                if receipt != {"candidate_hash": digest(candidate), "packet_id": candidate["packet_id"], "revision": candidate["revision"]}:
                    raise AnalysisError("Stored analysis differs from its validated apply receipt")
            # An unchanged receipt establishes that this historical candidate passed
            # validation at apply. Current-source path proofs may no longer exist,
            # so render them only under the prominent STALE label.
            if not stale:
                errors = validate_candidate(root, historical, candidate)
                if errors:
                    raise AnalysisError("Stored analysis failed validation: " + "; ".join(errors))
            result = {"analysis": candidate, "report_projection": report_projection(candidate, historical, stale), "stale": stale, "completion": candidate["completion"], "exit_code": 3 if stale else 0}
            output = args.output or f"docs/generated/features/{args.analysis}.{'json' if args.format == 'json' else 'md'}"
            # Restrict reports to their reserved directory, keeping them out of evidence.
            if not output.startswith(feature.GENERATED_PREFIX):
                raise AnalysisError("Feature report output must be under docs/generated/features/ to prevent evidence feedback")
            target = safe_path(root, output)
            rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n" if args.format == "json" else render_report(candidate, historical, stale, applied)
            def verify_report():
                guard.verify()
                if observation_staleness(candidate) != observed_stale:
                    raise AnalysisError("Report observation freshness changed during publication", 3)
            atomic_write(target, rendered, before_replace=verify_report)
            result = {"output": output, "completion": candidate["completion"], "stale": stale, "exit_code": result["exit_code"]}
        if not result["exit_code"] and args.require_complete and result["completion"].get("processing_status") != "COMPLETE":
            result["exit_code"] = 4
        if command == "data-check" and args.format == "markdown" and result.get("valid"):
            print(result["report"], end="")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return result["exit_code"]
    except AnalysisError as exc:
        print(json.dumps({"error": str(exc), "exit_code": exc.code}, ensure_ascii=False))
        return exc.code
    except (OSError, UnicodeError) as exc:
        print(json.dumps({"error": str(exc), "exit_code": 1}, ensure_ascii=False))
        return 1


def query_analysis(root: Path, analysis_id: str, terms: str, limit: int,
                   scope: str = "production", context_id: str | None = None) -> int:
    try:
        candidate = read_json(safe_path(root, f".kgmaker/analyses/{analysis_id}/analysis.json"))
        result = feature.validate(root, analysis_id, candidate)
        if result['valid']:
            graph = feature.graph_for_packet(root, feature.load_packet(root, analysis_id))
            from .views import project, select_context
            context_id = select_context(graph, scope, context_id)
            nodes = project(graph, scope, context_id=context_id).nodes
            candidates = [{'id': n.id, 'name': n.name, 'path': n.path, 'state': 'AS_IS'} for n in nodes]
            candidates += candidate['proposal']['nodes']
            words = terms.lower().split()
            matches = [n for n in candidates if any(w in json.dumps(n, ensure_ascii=False).lower() for w in words)]
            result['matches'] = sorted(matches, key=lambda n: n['id'])[:max(0, limit)]
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return result['exit_code']
    except (AnalysisError, ValueError) as exc:
        code = getattr(exc, 'code', 2)
        print(json.dumps({'error': str(exc), 'exit_code': code}))
        return code
    except OSError as exc:
        print(json.dumps({'error': str(exc), 'exit_code': 1}))
        return 1


def impact_entity(root: Path, entity: str, output_format: str,
                  scope: str = "all", context_id: str | None = None) -> int:
    from .dataflow import impact_paths
    from .scanner import scan_repository
    from .semantic import apply_semantic_layer
    try:
        graph, _, semantic_error = feature.current_graph(root)
        from .views import project, select_context
        context_id = select_context(graph, scope, context_id)
        graph = project(graph, scope, context_id=context_id)
        result = impact_paths(graph, entity)
        if semantic_error:
            result['limitations'] = result['limitations'] + [semantic_error]
        if output_format == 'json':
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print('Static data-flow impact: ' + entity)
            for path in result['paths']:
                print(' → '.join(path['entity_ids']) + ' [' + path['weakest_confidence'] + ']')
                if path['unresolved_boundary']:
                    print('  Boundary: ' + path['unresolved_boundary'])
            print(result['interpretation'])
        return 0
    except ValueError as exc:
        print(json.dumps({'error': str(exc), 'exit_code': 2}))
        return 2
    except OSError as exc:
        print(json.dumps({'error': str(exc), 'exit_code': 1}))
        return 1
