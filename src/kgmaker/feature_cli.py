"""Argparse integration kept separate from the legacy CLI contracts."""
from __future__ import annotations

import json
from pathlib import Path

from . import feature
from .analysis_model import AnalysisError, atomic_write, digest, inventory_candidate, read_json, safe_path
from .analysis_report import render_report
from .analysis_validation import validate_candidate


def register(subparsers):
    parser = subparsers.add_parser("feature", help="offline, isolated feature feasibility analysis")
    commands = parser.add_subparsers(dest="feature_command", required=True)
    for command in ("prepare", "validate", "apply", "report", "status", "revise", "compare", "data-check"):
        child = commands.add_parser(command)
        child.add_argument("--root", type=Path, default=Path.cwd())
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
            child.add_argument("--workspace", help="reserved capability; not yet supported")
            child.add_argument("--format", choices=("markdown", "json"), default="json")
        if command == "report":
            child.add_argument("--output")
            child.add_argument("--format", choices=("markdown", "json"), default="markdown")


def run(args) -> int:
    root = args.root.resolve()
    try:
        command = args.feature_command
        if command == "prepare":
            packet = feature.prepare(root, args.requirement, args.id, args.token_budget)
            result = {"analysis_id": args.id, "revision": packet["revision"], "packet_id": packet["packet_id"],
                      "completion": inventory_candidate(packet)["completion"], "budget": packet["budget"],
                      "template": f".kgmaker/analyses/{args.id}/candidate-template.json", "exit_code": 0}
        elif command == "data-check":
            from .data_check import data_check
            if args.workspace:
                raise AnalysisError("Workspace data-check requires milestone G; single-root fallback is forbidden")
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
            packet = feature.load_packet(root, args.analysis)
            path = safe_path(root, f".kgmaker/analyses/{args.analysis}/analysis.json")
            candidate = read_json(path) if path.exists() else inventory_candidate(packet)
            # Historical reports must validate against the exact revision they used.
            historical = packet
            if candidate.get("packet_id") != packet["packet_id"]:
                historical = read_json(safe_path(root, f".kgmaker/analyses/{args.analysis}/history/packet-{candidate['revision']}.json"))
                if candidate.get("packet_id") != historical.get("packet_id") or historical.get("packet_id") != feature.packet_identity(historical):
                    raise AnalysisError("Historical packet integrity mismatch")
            stale = feature.freshness(root, historical)
            if historical != packet:
                stale.append("Newer analysis packet exists; report uses a historical revision")
            if path.exists():
                receipt = read_json(safe_path(root, f".kgmaker/analyses/{args.analysis}/receipts/{candidate['revision']}.json"))
                if receipt != {"candidate_hash": digest(candidate), "packet_id": candidate["packet_id"], "revision": candidate["revision"]}:
                    raise AnalysisError("Stored analysis differs from its validated apply receipt")
            # An unchanged receipt establishes that this historical candidate passed
            # validation at apply. Current-source path proofs may no longer exist,
            # so render them only under the prominent STALE label.
            if not stale:
                errors = validate_candidate(root, historical, candidate)
                if errors:
                    raise AnalysisError("Stored analysis failed validation: " + "; ".join(errors))
            result = {"analysis": candidate, "stale": stale, "completion": candidate["completion"], "exit_code": 3 if stale else 0}
            output = args.output or f"docs/generated/features/{args.analysis}.{'json' if args.format == 'json' else 'md'}"
            # Restrict reports to their reserved directory, keeping them out of evidence.
            if not output.startswith(feature.GENERATED_PREFIX):
                raise AnalysisError("Feature report output must be under docs/generated/features/ to prevent evidence feedback")
            target = safe_path(root, output)
            rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n" if args.format == "json" else render_report(candidate, historical, stale, path.exists())
            atomic_write(target, rendered)
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


def query_analysis(root: Path, analysis_id: str, terms: str, limit: int) -> int:
    try:
        candidate = read_json(safe_path(root, f".kgmaker/analyses/{analysis_id}/analysis.json"))
        result = feature.validate(root, analysis_id, candidate)
        if result['valid']:
            _, _, _, nodes = feature.snapshot(root)
            candidates = [{'id': n.id, 'name': n.name, 'path': n.path, 'state': 'AS_IS'} for n in nodes]
            candidates += candidate['proposal']['nodes']
            words = terms.lower().split()
            matches = [n for n in candidates if any(w in json.dumps(n, ensure_ascii=False).lower() for w in words)]
            result['matches'] = sorted(matches, key=lambda n: n['id'])[:max(0, limit)]
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return result['exit_code']
    except AnalysisError as exc:
        print(json.dumps({'error': str(exc), 'exit_code': exc.code}))
        return exc.code
    except OSError as exc:
        print(json.dumps({'error': str(exc), 'exit_code': 1}))
        return 1


def impact_entity(root: Path, entity: str, output_format: str) -> int:
    from .dataflow import impact_paths
    from .scanner import scan_repository
    from .semantic import apply_semantic_layer
    try:
        graph, _, semantic_error = apply_semantic_layer(scan_repository(root), root)
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
