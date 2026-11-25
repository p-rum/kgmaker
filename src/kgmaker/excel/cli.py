"""Explicit CLI for the Excel inventory and migration plan lifecycle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..analysis_model import AnalysisError, atomic_write, canonical
from . import inventory, jira, plan
from .source import MAX_ARTIFACT_BYTES, bounded_json, manifest


def register(subparsers):
    command = subparsers.add_parser("excel", help="analyze Excel and plan migration to Kotlin/JVM")
    actions = command.add_subparsers(dest="excel_action", required=True)
    analyze = actions.add_parser("analyze", help="read the explicitly declared Excel workbooks")
    analyze.add_argument("--manifest", type=Path, required=True)
    analyze.add_argument("--out", type=Path, required=True)
    packet = actions.add_parser("packet", help="prepare bounded evidence and a Copilot plan template")
    packet.add_argument("--inventory", type=Path, required=True)
    packet.add_argument("--book")
    packet.add_argument("--entity")
    packet.add_argument("--include-source", action="store_true")
    packet.add_argument("--budget", type=int, default=32_000)
    actions.add_parser("jira-template", help="print the default Jira Cloud template")
    planning = actions.add_parser("plan", help="validate and export a migration plan")
    commands = planning.add_subparsers(dest="excel_plan_action", required=True)
    for name in ("validate", "export"):
        action = commands.add_parser(name)
        action.add_argument("--manifest", type=Path, required=True)
        action.add_argument("--inventory", type=Path, required=True)
        action.add_argument("--candidate", type=Path, required=True)
        if name == "export":
            action.add_argument("--format", choices=("json", "markdown", "jira-csv"), default="markdown")
            action.add_argument("--out", type=Path, required=True)
            action.add_argument("--jira-template", type=Path)


def _publish(path, content, inputs, check):
    target = path.absolute()

    def verify():
        if any(part.is_symlink() for part in (target, *target.parents)):
            raise AnalysisError("Excel output must not traverse symlinks")
        if target.resolve() in {item.resolve() for item in inputs}:
            raise AnalysisError("Excel output collides with an input")
        check()

    if len(content.encode("utf-8")) > MAX_ARTIFACT_BYTES:
        raise AnalysisError("Excel output exceeds 64 MiB")
    verify()
    atomic_write(target, content, before_replace=verify)


def _print(value):
    print(json.dumps(value, ensure_ascii=True, sort_keys=True))


def run(args: argparse.Namespace) -> int:
    try:
        if args.excel_action == "jira-template":
            _print(jira.DEFAULT)
            return 0
        if args.excel_action == "analyze":
            selection = manifest(args.manifest)
            value = inventory.analyze(args.manifest, selection=selection)
            sources = [args.manifest, *(book.path for book in selection.books)]
            _publish(args.out, canonical(value) + "\n", sources,
                     lambda: inventory.assert_fresh(args.manifest, value))
            _print({"inventory_id": value["inventory_id"], "status": value["status"],
                    "output": str(args.out), "workbooks": len(value["workbooks"])})
            return 0
        value = plan.load_inventory(args.inventory)
        if args.excel_action == "packet":
            packet = plan.packet(value, book=args.book, entity=args.entity,
                                 include_source=args.include_source, budget=args.budget)
            # Keep the wire representation within the stated byte budget.
            sys.stdout.buffer.write(canonical(packet).encode("utf-8") + b"\n")
            return 0
        selection = inventory.assert_fresh(args.manifest, value)
        validated = plan.validate(value, bounded_json(args.candidate, 4 * 1024 * 1024))
        if args.excel_plan_action == "validate":
            _print({"status": "VALID", "inventory_id": value["inventory_id"],
                    "tasks": len(validated["tasks"]), "deferred": len(validated["deferred"])})
            return 0
        sources = [args.manifest, args.inventory, args.candidate, *(book.path for book in selection.books)]
        result = {"inventory_id": value["inventory_id"], "format": args.format, "output": str(args.out)}
        if args.jira_template and args.format != "jira-csv":
            raise AnalysisError("--jira-template requires --format jira-csv")
        if args.format == "jira-csv":
            profile = jira.DEFAULT
            if args.jira_template:
                sources.append(args.jira_template)
                profile = bounded_json(args.jira_template, 256 * 1024)
            content, fields = jira.render(value, validated, profile)
            result.update(fields)
        elif args.format == "json":
            content = canonical(validated) + "\n"
        else:
            content = plan.markdown(value, validated)
        _publish(args.out, content, sources, lambda: inventory.assert_fresh(args.manifest, value))
        _print(result)
        return 0
    except (AnalysisError, OSError, UnicodeError, ValueError, RecursionError) as exc:
        print(f"kgmaker excel: {exc}", file=sys.stderr)
        return exc.code if isinstance(exc, AnalysisError) else 2
