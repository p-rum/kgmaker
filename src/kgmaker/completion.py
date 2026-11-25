"""Read-only completion planning from KGMAKER's repository inventory and specs."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from graphlib import CycleError, TopologicalSorter
from pathlib import Path

INVENTORY = Path("docs/production-analysis-progress.md")
ITEM_ID = r"T\d{3,}(?:-S\d{2}(?:-W\d{2})?)?"
REFERENCE = re.compile(rf"\b{ITEM_ID}\b(?!-[A-Z]\d)")
RANGE = re.compile(rf"\b({ITEM_ID})\s*(?:až|–)\s*({ITEM_ID})\b")
MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
DEPENDENCY_LINE = re.compile(r"^- (?:Depends on|Závislosti): (.+)$", re.MULTILINE)
VERIFICATION_DEPENDENCY_LINE = re.compile(
    r"^- (?:Verified dependencies|Povinně ověřené závislosti): (.+)$", re.MULTILINE,
)
ROW = re.compile(rf"^\| \[({ITEM_ID})\]\((tasks/[^)]+\.md)\) \| (.+) \|$")
DELIVERY = {"PLANNED", "IN_PROGRESS", "PR_OPEN", "MERGED", "DEFERRED", "BLOCKED"}
VERIFICATION = {"VERIFIED_IN_SCOPE", "PARTIAL", "NOT_RUN", "FAIL"}
NO_DEPENDENCIES = {"none", "baseline", "pouze baseline", "bez závislostí", "žádné"}


@dataclass(frozen=True)
class Item:
    specification: str
    specification_fingerprint: str
    delivery: str
    verification: str
    evidence: str
    pull_requests: tuple[int, ...]
    owner: str
    dependencies: tuple[str, ...] | None
    conditional_dependencies: tuple[str, ...]
    verification_dependencies: tuple[str, ...]


def _specification_step(source: str, item_id: str) -> str:
    # Several tasks share a specification. Read the corresponding step only.
    step_heading = re.search(rf"^### {item_id} — .+$", source, re.MULTILINE)
    if step_heading:
        source = re.split(r"^#{2,3} ", source[step_heading.end():], maxsplit=1,
                          flags=re.MULTILINE)[0]
    return source


def _dependency_text(source: str, item_id: str) -> str | None:
    line = DEPENDENCY_LINE.search(source)
    if not line:
        return None
    text = MARKDOWN_LINK.sub(r"\1", line[1].replace(chr(96), ""))
    if item_id.startswith("T047-"):
        text = re.sub(r"\b(T\d{3,})-(S\d{2})((?:/S\d{2})+)",
                      lambda m: m[1] + "-" + m[2] + "".join(
                          " " + m[1] + "-" + part for part in m[3].split("/")[1:]), text)
        text = re.sub(r"\b(T\d{3,}-S\d{2})-(W\d{2})((?:/W\d{2})+)",
                      lambda m: m[1] + "-" + m[2] + "".join(
                          " " + m[1] + "-" + part for part in m[3].split("/")[1:]), text)
        text = re.sub(r"(?<![\w-])S(\d{2})\b", r"T047-S\1", text)
    return text


def _dependencies(text: str, ids: set[str], current: str) -> tuple[str, ...] | None:
    def expand(match: re.Match[str]) -> str:
        first, last = match.groups()
        if first not in ids or last not in ids or first > last:
            raise ValueError(f"unknown or reversed dependency range: {match[0]}")
        return " ".join(sorted(item_id for item_id in ids
                               if len(item_id) == len(first) and first <= item_id <= last))

    dependencies = set()
    for reference in REFERENCE.findall(RANGE.sub(expand, text)):
        if (reference not in ids and re.fullmatch(r"T003-S\d{2}", reference)
                and f"offline boundary {reference}" not in text):
            packages = {item_id for item_id in ids
                        if item_id.startswith(reference + "-W") and item_id != current}
            dependencies.update(packages or {reference})
        else:
            dependencies.add(reference)
    if not dependencies and text.split(';', 1)[0].strip().rstrip('.').casefold() not in NO_DEPENDENCIES:
        return None
    return tuple(sorted(dependencies))


def _read_items(root: Path, inventory: str) -> dict[str, Item]:
    entries = {}
    for line in inventory.splitlines():
        match = ROW.fullmatch(line)
        if not match:
            if re.match(rf"^\| \[{ITEM_ID}\]", line):
                raise ValueError("malformed completion inventory row")
            continue
        item_id, relative, body = match.groups()
        if item_id in entries:
            raise ValueError(f"duplicate completion inventory ID: {item_id}")
        fields = body.split(" | ", maxsplit=5)
        if len(fields) != 6 or fields[0] not in DELIVERY:
            raise ValueError(f"invalid delivery for {item_id}")
        fields[1] = re.split(r"[; (]", fields[1], maxsplit=1)[0]
        if fields[1] not in VERIFICATION:
            raise ValueError(f"invalid verification for {item_id}")
        entries[item_id] = relative, fields
    if not entries:
        raise ValueError("no completion inventory rows found")

    ids = set(entries)
    tasks_dir = root.resolve() / "docs/tasks"
    specs = {}
    items = {}
    for item_id, (relative, fields) in entries.items():
        path = (root / "docs" / relative).resolve()
        if not path.is_relative_to(tasks_dir):
            raise ValueError(f"task specification outside docs/tasks: {relative}")
        if path not in specs:
            raw = path.read_bytes()
            specs[path] = raw.decode("utf-8"), hashlib.sha256(raw).hexdigest()
        source, fingerprint = specs[path]
        source = _specification_step(source, item_id)
        text = _dependency_text(source, item_id)
        conditional = ""
        if text is not None and item_id.startswith("T047-"):
            parts = re.split(r"; (?=integrace odvozených view|T047-S02 pro symbol references"
                             r"|T047-S09 pro selektivní|T037 pro uložené views)", text, maxsplit=1)
            text = parts[0].replace("T003-S11 benchmark/budget metodiku",
                                    "T003-S11-W05 a T003-S11-W06")
            conditional = parts[1] if len(parts) == 2 else ""
        dependencies = _dependencies(text, ids, item_id) if text is not None else None
        verified_line = VERIFICATION_DEPENDENCY_LINE.search(source)
        verification_dependencies = ()
        if verified_line:
            declared = MARKDOWN_LINK.sub(r"\1", verified_line[1].replace(chr(96), ""))
            required = _dependencies(declared, ids, item_id)
            if not required or not set(required) <= set(dependencies or ()):
                raise ValueError(f"invalid verified dependencies for {item_id}: use declared dependencies")
            verification_dependencies = required
        owner = re.match(rf"Upstream owner: ({ITEM_ID})\b", fields[5])
        pulls = re.findall(r"github\.com/p-rum/kgmaker/pull/(\d+)\b", fields[4])
        items[item_id] = Item(
            specification="docs/" + relative,
            specification_fingerprint=fingerprint,
            delivery=fields[0],
            verification=fields[1],
            evidence=fields[2],
            pull_requests=tuple(dict.fromkeys(map(int, pulls))),
            owner=owner[1] if owner else item_id,
            dependencies=dependencies,
            conditional_dependencies=_dependencies(conditional, ids, item_id) or (),
            verification_dependencies=verification_dependencies,
        )
    return items


def _action(item: Item) -> tuple[int, str]:
    if item.delivery in {"DEFERRED", "BLOCKED"}:
        return 5, "hold"
    if item.verification == "FAIL":
        return 0, "repair"
    if item.delivery in {"IN_PROGRESS", "PR_OPEN"}:
        return 1, "resume"
    if item.delivery == "MERGED":
        return (5, "none") if item.verification == "VERIFIED_IN_SCOPE" else (4, "verify")
    # Prefer closing the outstanding incremental integrity work before other new work.
    if item.specification.startswith(("docs/tasks/47_", "docs/tasks/T003-S10-")):
        return 2, "implement"
    return 3, "implement"



def _indirect_failures(item_id: str, items: dict[str, Item]) -> list[str]:
    """Find current failures hidden behind an otherwise merged direct dependency."""
    direct = set(items[item_id].dependencies or ())
    remaining = list(direct.intersection(items))
    seen = {item_id}
    failures = set()
    while remaining:
        dependency = remaining.pop()
        if dependency in seen:
            continue
        seen.add(dependency)
        item = items[dependency]
        if dependency not in direct and item.verification == "FAIL":
            failures.add(dependency)
        remaining.extend(set(item.dependencies or ()).intersection(items).difference(seen))
    return sorted(failures)


def plan(root: Path, jobs: int = 1) -> dict:
    if type(jobs) is not int or not 1 <= jobs <= 32:
        raise ValueError("jobs must be an integer from 1 to 32")
    raw = (root / INVENTORY).read_bytes()
    items = _read_items(root, raw.decode("utf-8"))
    # Historical references among delivered items cannot deadlock new work.
    pending = {item_id for item_id, item in items.items()
               if item.delivery != "MERGED" or item.verification == "FAIL"}
    graph = {item_id: set(items[item_id].dependencies or ()).intersection(pending)
             for item_id in sorted(pending)}
    try:
        tuple(TopologicalSorter(graph).static_order())
    except CycleError as error:
        raise ValueError("completion dependency cycle: " + " -> ".join(error.args[1])) from None

    backlog = {}
    dispatch = []
    for item_id, item in sorted(items.items(), key=lambda pair: (*_action(pair[1]), pair[0])):
        priority, action = _action(item)
        blockers = []
        if item_id != item.owner:
            action = "shared"
            blockers.append(f"handled by upstream owner {item.owner}")
        elif action in {"repair", "resume", "implement", "verify"}:
            if item.dependencies is None:
                blockers.append("dependency declaration requires source review")
            for dependency in item.dependencies or ():
                upstream = items.get(dependency)
                if upstream is None:
                    blockers.append(f"{dependency}: dependency requires source review")
                elif upstream.verification == "FAIL" or upstream.delivery != "MERGED":
                    blockers.append(f"{dependency}: {upstream.delivery}/{upstream.verification}")
                elif dependency in item.verification_dependencies and upstream.verification != "VERIFIED_IN_SCOPE":
                    blockers.append(
                        f"{dependency}: {upstream.delivery}/{upstream.verification}; VERIFIED_IN_SCOPE required"
                    )
            blockers.extend(f"{failure}: indirect dependency FAIL"
                            for failure in _indirect_failures(item_id, items))
            if not blockers and len(dispatch) < jobs:
                dispatch.append(item_id)
        backlog[item_id] = {**asdict(item), "priority": priority, "action": action,
                            "blockers": blockers}

    return {"inventory_fingerprint": hashlib.sha256(raw).hexdigest(),
            "items": backlog, "dispatch": dispatch}


def register(sub) -> None:
    parser = sub.add_parser("completion", help="plan completion work from the repository inventory")
    commands = parser.add_subparsers(dest="completion_command", required=True)
    command = commands.add_parser(
        "plan", help="show dependency and dispatch candidates as JSON")
    command.add_argument("--root", type=Path, default=Path.cwd())
    command.add_argument("--jobs", type=int, default=1)
    from .completion_handoff import register as register_handoff
    from .completion_review import register as register_review
    register_handoff(commands)
    register_review(commands)


def run(args) -> int:
    try:
        handler = getattr(args, 'handler', None)
        output = handler(args) if handler else plan(args.root, args.jobs)
    except (ValueError, OSError) as error:
        print(f"Cannot prepare completion: {error}", file=sys.stderr)
        return 2
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0
