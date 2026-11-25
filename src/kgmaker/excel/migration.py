"""Local preparation and validated exports for the Excel migration skill."""

from __future__ import annotations

from contextlib import suppress
from pathlib import Path

from ..analysis_model import AnalysisError, canonical
from . import inventory, jira, plan
from .source import MAX_ARTIFACT_BYTES, bounded_json, manifest, workbook_selection


def register(actions):
    migration = actions.add_parser("migrate", help="prepare and export a Copilot migration bundle")
    commands = migration.add_subparsers(dest="migration_action", required=True)
    for name in ("prepare", "export"):
        action = commands.add_parser(name)
        source = action.add_mutually_exclusive_group(required=True)
        source.add_argument("--workbook", type=Path, help="main workbook file")
        source.add_argument("--manifest", type=Path, help="existing workbook manifest")
        action.add_argument("--dependency", type=Path, action="append", default=[],
                            help="explicit workbook to include alongside --workbook")
        action.add_argument("--out-dir", type=Path, required=True)
        if name == "prepare":
            action.add_argument("--include-source", action="store_true")
            action.add_argument("--budget", type=int, default=32_000)
        else:
            action.add_argument("--candidate", type=Path, help="defaults to candidate.json in --out-dir")
            action.add_argument("--jira-template", type=Path)


def _selection(args):
    if args.manifest:
        if args.dependency:
            raise AnalysisError("--dependency requires --workbook")
        return manifest(args.manifest)
    return workbook_selection(args.workbook, args.dependency)


def _check_destination(directory: Path, *, new: bool):
    if any(path.is_symlink() for path in (directory, *directory.parents)):
        raise AnalysisError("Migration paths must not traverse symlinks")
    if new and directory.exists():
        raise AnalysisError(f"Migration output already exists: {directory}")
    if not new and not directory.is_dir():
        raise AnalysisError(f"Migration output directory is missing: {directory}")


def _write_bundle(directory, documents, check):
    for content in documents.values():
        if len(content.encode("utf-8")) > MAX_ARTIFACT_BYTES:
            raise AnalysisError("Excel migration artifact exceeds 64 MiB")
    _check_destination(directory, new=True)
    check()
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    created = []
    try:
        for filename, content in documents.items():
            path = directory / filename
            with path.open("x", encoding="utf-8", newline="") as stream:
                created.append(path)
                stream.write(content)
        check()
    except BaseException:
        for path in created:
            with suppress(OSError):
                path.unlink()
        with suppress(OSError):
            directory.rmdir()
        raise


def run(args):
    directory = args.out_dir.absolute()
    if args.migration_action == "prepare":
        _check_destination(directory, new=True)
        value = inventory.analyze_selection(_selection(args))
        packet = plan.packet(value, include_source=args.include_source, budget=args.budget)
        documents = {
            "inventory.json": canonical(value) + "\n",
            "packet.json": canonical(packet) + "\n",
            "subjects.jsonl": "".join(canonical(subject) + "\n" for subject in value["subjects"]),
        }
        _write_bundle(directory, documents,
                      lambda: inventory.assert_selection_fresh(_selection(args), value))
        return {
            "inventory_id": value["inventory_id"], "status": value["status"],
            "output": str(directory), "subjects": len(value["subjects"]),
            "truncated": packet["truncated"],
        }

    _check_destination(directory, new=False)
    result = directory / "result"
    _check_destination(result, new=True)
    value = plan.load_inventory(directory / "inventory.json")
    inventory.assert_selection_fresh(_selection(args), value)
    candidate = bounded_json(args.candidate or directory / "candidate.json", 4 * 1024 * 1024)
    validated = plan.validate(value, candidate)
    profile = bounded_json(args.jira_template, 256 * 1024) if args.jira_template else jira.DEFAULT
    csv, mapping = jira.render(value, validated, profile)
    documents = {
        "migration.csv": csv,
        "migration.md": plan.markdown(value, validated),
        "jira-mapping.json": canonical(mapping) + "\n",
    }
    _write_bundle(result, documents,
                  lambda: inventory.assert_selection_fresh(_selection(args), value))
    return {"inventory_id": value["inventory_id"], "status": "EXPORTED",
            "output": str(result), "rows": mapping["rows"]}
