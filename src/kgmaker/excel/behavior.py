"""Render the workbook's observed behavior and bounded static data lineage."""

from __future__ import annotations

import re
from collections import Counter, defaultdict, deque

from ..analysis_model import AnalysisError
from ..workbooks import _range_cells

FLOW_LIMIT = 64
OUTPUT_TRACE_LIMIT = 200
OPERATION_LABELS = {
    "assignment": "Assignment", "condition": "Control-flow condition", "display-write": "Display property write",
    "message": "Possible VBA message", "http-open": "Prepare HTTP request", "http-send": "Send HTTP request",
    "unresolved-operation": "Operation with unresolved effects", "return-value": "Return assignment",
}
BRANCH_NOTES = {
    "IF": "Either branch can supply the result, depending on the test.",
    "IFERROR": "The first expression supplies the result unless it errors, in which case the fallback is used.",
    "IFNA": "The fallback is used only if the first expression returns #N/A.",
    "IFS": "The selected result depends on which test is true first.",
    "SWITCH": "The selected result depends on the matching case or the default.",
    "CHOOSE": "The index selects one of the listed values.",
}


def _code(value):
    text = str(value).replace("\r", " ").replace("\n", " ⏎ ")
    text = "".join(char if char.isprintable() else " " for char in text)
    fence = "`" * (1 + max((len(run) for run in re.findall(r"`+", text)), default=0))
    return f"{fence} {text} {fence}"


def _location(row):
    place = {"sheet": row["sheet"], **row["locator"]} if row.get("sheet") else row["locator"]
    parts = [str(place[field]) for field in ("workbook", "sheet", "cell", "range", "module", "procedure",
                                            "control", "name", "part") if field in place]
    if "line" in place:
        parts.append(f"line {place['line']}")
    if "connection" in place:
        parts.append(f"connection {place['connection']}")
    return " / ".join(parts)


def _sort(row):
    place = row["locator"]
    return (place.get("workbook", ""), place.get("sheet", ""), place.get("module", ""),
            place.get("line", 0), place.get("statement", 0), _location(row), row["id"])


def _anchor(row):
    return f"{_code(_location(row))} [{_code(row['id'])}]"


def _site(row):
    place = row["locator"]
    return tuple(place.get(field) for field in ("workbook", "sheet", "cell", "module", "procedure", "line"))


class WorkbookBehavior:
    def __init__(self, inventory, include_source, book, sheet):
        self.inventory = inventory
        self.include_source = include_source
        self.book = book
        self.sheet = sheet
        self.rows = {row["id"]: row for row in inventory["evidence"]}
        self.by_kind = defaultdict(list)
        self.links = defaultdict(list)
        self.writers = defaultdict(list)
        self.used = set()
        self.cells = {}
        self.visible = set()
        self.range_writers = defaultdict(list)
        self.site_gaps = defaultdict(list)
        self.traced = set()
        for row in sorted(self.rows.values(), key=_sort):
            self.by_kind[row["kind"]].append(row)
            place = row["locator"]
            if row["kind"] == "cell":
                self.cells[place["workbook"], place["sheet"], place["cell"]] = row["id"]
            elif row["kind"] == "sheet" and row.get("visibility") == "VISIBLE":
                self.visible.add((place["workbook"], place["sheet"]))
            elif row["kind"] == "gap":
                self.site_gaps[_site(row)].append(row)
        for edge in inventory["relations"]:
            source, target, kind = edge["source"], edge["target"], edge["kind"]
            self.links[source, kind].append(target)
            if kind == "reads":
                self.used.add(target)
            elif kind == "writes" and self.rows[source]["kind"] in {"vba-operation", "query-table"}:
                self.writers[target].append(source)
        # Expand only ranges that can contribute to output lineage. Larger
        # ranges stay in the report as cited range endpoints.
        range_budget = 50_000
        for key in sorted(self.writers.keys() | self.used):
            if self.rows[key]["kind"] != "address" or range_budget <= 0:
                continue
            members, inspected = self.members(self.rows[key], min(range_budget, 1_000))
            range_budget -= inspected
            for cell in members:
                if key in self.used:
                    self.used.add(cell)
                self.range_writers[cell].extend(self.writers.get(key, ()))
        if book and not any(item["id"] == book for item in inventory["workbooks"]):
            raise AnalysisError("Unknown workbook selector")
        if sheet and not any(self.in_scope(row) for row in self.by_kind["sheet"]):
            raise AnalysisError("Unknown sheet for the selected workbook")

    def in_scope(self, row):
        locator = row["locator"]
        return ((self.book is None or locator.get("workbook") == self.book)
                and (self.sheet is None or locator.get("sheet", row.get("sheet")) == self.sheet))

    def relevant(self, row):
        return row["id"] in self.traced or self.in_scope(row)

    def members(self, row, maximum):
        place = row["locator"]
        first, colon, last = place["range"].partition(":")
        addresses = _range_cells(first, last if colon else None, maximum=maximum)
        return [key for address in addresses
                if (key := self.cells.get((place["workbook"], place["sheet"], address)))], len(addresses)

    def refs(self, keys):
        return ", ".join(_anchor(self.rows[key]) for key in keys)

    def connections(self, row, *kinds):
        return [key for kind in kinds for key in self.links.get((row["id"], kind), ())]

    def prerequisites(self, row):
        key = row["id"]
        if row["kind"] == "vba-procedure":
            # Calls and reads of a procedure describe effects of executing it,
            # which need not contribute to its return value.
            return self.connections(row, "returns")
        direct = self.connections(row, "reads", "depends-on", "source", "calls")
        direct.extend(self.writers.get(key, ()))
        direct.extend(self.range_writers.get(key, ()))
        if row["kind"] == "address":
            members, _ = self.members(row, FLOW_LIMIT)
            direct.extend(members)
        return direct

    def lineage(self, root):
        parents = {root["id"]: None}
        observed = {root["id"]}
        traced = []
        pending = deque((key, root["id"]) for key in self.prerequisites(root))
        while pending and len(traced) < FLOW_LIMIT:
            key, parent = pending.popleft()
            row = self.rows[key]
            if key not in observed:
                observed.add(key)
                traced.append(row)
            # A VBA read observes a cell at a particular moment. A later
            # worksheet write or recalculation cannot explain that read.
            parent_row = self.rows[parent]
            if (key in parents or (row["kind"] in {"cell", "address"}
                    and parent_row["kind"] == "vba-operation"
                    and key in self.links.get((parent, "reads"), ()))):
                continue
            parents[key] = parent
            pending.extend((child, key) for child in self.prerequisites(row))
        paths = []
        for row in traced:
            if row["kind"] != "external-source":
                continue
            path, cursor = [], row["id"]
            while cursor is not None:
                path.append(cursor)
                cursor = parents[cursor]
            paths.append(path)
        return traced, paths, any(key not in observed for key, _ in pending)

    def declared_sources(self, lines):
        lines.extend(("", "## Declared data sources", ""))
        sources = self.by_kind["external-source"]
        if not sources:
            lines.append("No supported source declaration was extracted from this inventory.")
        for row in sources:
            detail = row["mechanism"]
            if row.get("method"):
                detail += f" {row['method']}"
            reference = row.get("reference")
            if reference:
                detail += f" · {_code(reference)}" if self.include_source else " · literal identity redacted"
            else:
                detail += " · endpoint not resolved from supported syntax"
            if mapped := row.get("mapped_workbook"):
                detail += f" · mapped input {_code(mapped)}"
            lines.append(f"- **Declared in source** · {detail} · {_anchor(row)}")
            if bindings := self.connections(row, "depends-on"):
                lines.append(f"  - Static endpoint binding from literal assignment {self.refs(bindings)}")
        for row in self.by_kind["query-table"]:
            inputs = self.connections(row, "source")
            outputs = self.connections(row, "writes")
            lines.append(f"- **Declared query-table binding** · {_anchor(row)}")
            if inputs:
                lines.append(f"  - Connection {self.refs(inputs)}")
            lines.append(f"  - Destination {self.refs(outputs)}" if outputs else
                         "  - Declaration locates the sheet. The destination range is unresolved.")

    def action(self, row, lines):
        if self.include_source and row.get("source"):
            lines.append(f"  - Statement {_code(row['source'])}")
        if row.get("operators"):
            lines.append(f"  - Operators {', '.join(row['operators'])}")
        if functions := row.get("functions"):
            lines.append(f"  - Functions {', '.join(_code(name) for name in functions)}")
        for kind, name in (("reads", "Reads"), ("writes", "Writes"), ("source", "Associated source"), ("calls", "Calls"),
                           ("depends-on", "Possible local definitions")):
            if keys := self.connections(row, kind):
                lines.append(f"  - {name} {self.refs(keys)}")
        for symbol, choices in row.get("alternatives", {}).items():
            lines.append(f"  - **Alternative definitions** of {_code(symbol)} · {self.refs(choices)}. "
                         "Branch selection and effects of opaque calls require verification.")
        for gap in self.site_gaps[_site(row)]:
            if row["kind"] == "defined-name" and row["locator"].get("name") != gap["locator"].get("name"):
                continue
            lines.append(f"  - **Unresolved at this location** · {_code(gap['reason'])} {_anchor(gap)}")

    def calculations(self, lines):
        lines.extend(("", "## Calculations and VBA steps", ""))
        for kind in ("cell", "defined-name"):
            for row in self.by_kind[kind]:
                if not self.relevant(row) or (
                    row.get("type") != "FORMULA" and (kind != "defined-name" or not row.get("formula"))
                ):
                    continue
                lines.append(f"- **Formula in source** · {_anchor(row)}")
                if self.include_source and row.get("formula"):
                    lines.append(f"  - Expression {_code('=' + row['formula'])}")
                if self.include_source and "cached_value" in row:
                    lines.append(f"  - Stored result {_code(row['cached_value'])} · freshness unverified")
                self.action(row, lines)
                for name in row.get("functions", ()):
                    if name in BRANCH_NOTES:
                        lines.append(f"  - **Conditional result** · {name}. {BRANCH_NOTES[name]}")
        for proc in self.by_kind["vba-procedure"]:
            actions = [self.rows[key] for key in self.connections(proc, "contains")
                       if self.rows[key]["kind"] == "vba-operation" and self.relevant(self.rows[key])]
            if not self.relevant(proc) and not actions:
                continue
            calls = self.connections(proc, "calls")
            lines.append(f"- **VBA procedure in source** · {_anchor(proc)}")
            if calls:
                lines.append(f"  - Calls {self.refs(calls)}")
            for action in sorted(actions, key=_sort):
                label = OPERATION_LABELS[action["operation"]]
                lines.append(f"  - {label} · {_anchor(action)}")
                details = []
                self.action(action, details)
                lines.extend("  " + line for line in details)

    def displays(self, lines):
        lines.extend(("", "## Presentation and data flow", "",
                      "Visible terminal cells are output candidates. They may also be helper values or inputs used outside this workbook."))
        outputs = []
        for row in self.by_kind["cell"] + self.by_kind["address"]:
            place, key = row["locator"], row["id"]
            if (self.in_scope(row) and (place["workbook"], place["sheet"]) in self.visible
                    and (self.sheet is not None or key not in self.used)
                    and (row.get("type") == "FORMULA" or key in self.writers)):
                outputs.append(row)
        outputs.extend(row for row in self.by_kind["vba-operation"]
                       if self.in_scope(row) and row["operation"] in {"display-write", "message"})
        for index, row in enumerate(sorted(outputs, key=_sort)):
            label = OPERATION_LABELS[row["operation"]] if row["kind"] == "vba-operation" else "Visible output candidate"
            lines.append(f"- **Static inference** · {label} · {_anchor(row)}")
            if row["id"] in self.used:
                lines.append("  - Other workbook rules also reference this cell or range.")
            if self.include_source and (pattern := row.get("number_format")):
                lines.append(f"  - Declared display format {_code(pattern)}")
            if index >= OUTPUT_TRACE_LIMIT:
                continue
            observed, paths, limited = self.lineage(row)
            self.traced.update(item["id"] for item in observed)
            rules = [item["id"] for item in observed if item["kind"] not in {"external-source"}]
            if rules:
                lines.append(f"  - Statically connected inputs and steps {self.refs(rules)}")
            for path in paths:
                route = " → ".join(_anchor(self.rows[key]) for key in path)
                lines.append(f"  - Possible source-to-output path {route}")
            if limited:
                lines.append(f"  - Trace limited to {FLOW_LIMIT} observations.")
        if len(outputs) > OUTPUT_TRACE_LIMIT:
            lines.append(f"Lineage is expanded for the first {OUTPUT_TRACE_LIMIT} outputs. "
                         "The calculations section lists the direct dependencies for the remaining outputs.")

    def report(self):
        lines = ["# Workbook behavior", "", f"Inventory {_code(self.inventory['inventory_id'])}", "",
                 f"{len(self.inventory['workbooks'])} workbooks · {len(self.by_kind['sheet'])} sheets", "",
                 "**Source observations** cite stored declarations or statements. **Static inferences** connect "
                 "their likely data flow. Runtime values, branch selection and refresh success are unverified.", "",
                 "## Entry points", ""]
        for row in self.by_kind["entrypoint"]:
            if not self.in_scope(row):
                continue
            event = row.get("event") or row["locator"].get("event", "event")
            lines.append(f"- {_code(event)} · {_anchor(row)}")
            if calls := self.connections(row, "calls"):
                lines.append(f"  - Invokes {self.refs(calls)}")
        self.declared_sources(lines)
        self.displays(lines)
        referenced = [row for row in self.by_kind["cell"]
                      if self.relevant(row) and row["id"] in self.used and row.get("type") != "FORMULA"]
        if referenced:
            lines.extend(("", "## Values stored in referenced cells", "",
                          "A stored value may come from manual entry, an import, or a prior refresh."))
            for row in referenced:
                detail = f" · {_code(row['type'])}" if row.get("type") else ""
                if self.include_source and "value" in row:
                    detail += f" · {_code(row['value'])}"
                lines.append(f"- **Stored in source** · {_anchor(row)}{detail}")
        self.calculations(lines)
        lines.extend(("", "## Limits and remaining questions", "",
                      "Ranges in lineage are expanded only within the report's bounds. Opaque external responses, "
                      "dynamic VBA bindings and workbook-specific runtime state require independent verification. "
                      "VBA flow shows up to eight preceding candidate definitions per variable or request. "
                      "A VBA read stops at the observed cell or range because write order and recalculation are unverified."))
        gaps = Counter(row["code"] for row in self.by_kind["gap"] if row.get("code"))
        lines.extend(f"- {_code(code)} · {count} occurrences" for code, count in sorted(gaps.items()))
        return "\n".join(lines) + "\n"


def markdown(inventory, *, include_source=False, book=None, sheet=None):
    return WorkbookBehavior(inventory, include_source, book, sheet).report()
