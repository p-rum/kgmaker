"""Normalize workbook facts and resolve a conservative subset of Excel references."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from ..analysis_model import AnalysisError, digest
from ..workbooks import (
    _CELL, _column_number, _formula_calls, _formula_syntax, _reference_matches,
    _unsupported_reference_form,
)
from . import extraction, vba
from .source import MAX_TOTAL_BYTES, VERSION, WORKER, capture, extract, manifest, worker_command

EXTERNAL_PREFIX = re.compile(r"(?<![\w'])\[([^\]\r\n]+)\]([\w.]+)\s*!")
EXTERNAL_SHEET = re.compile(r"^([^\[]*)\[([^\]]+)\](.+)$")
FORMULA_NAME = re.compile(r"(?<![\w.$])([A-Za-z_\\][\w.\\]*)(?![\w.$])")
DYNAMIC_FORMULA = re.compile(r"\b(?:INDIRECT|OFFSET|INDIRECT\.EXT)\s*\(", re.I)
SCOPED_FORMULA = re.compile(r"(?<![\w.])(?:_xlfn\.|_xlws\.)*(?:LET|LAMBDA)\s*\(", re.I)
EVENT_NAME = re.compile(r"^(Workbook|Worksheet)_(\w+)$", re.I)
RANGE_TEXT = re.compile(r"([^:]+)(?::([^:]+))?")
KNOWN_DIAGNOSTICS = {
    "EXCEL_ENCRYPTED": "Workbook is encrypted.",
    "EXCEL_BIFF_UNSUPPORTED": "Only compound BIFF8 .xls is supported.",
    "EXCEL_PARSE_FAILED": "Workbook structure could not be parsed.",
    "EXCEL_FORMAT_MISMATCH": "The extension and workbook format or content type disagree.",
    "EXCEL_XLM_UNSUPPORTED": "Excel 4.0 macro sheets are outside the supported VBA analysis.",
    "EXCEL_EMBEDDED_COMPONENT": "The workbook contains an embedded control or VBA signature.",
    "EXCEL_DATA_CONNECTION": "Refresh behavior and returned data of declared connections require verification.",
    "EXCEL_CONNECTION_UNREADABLE": "Connection or query-table metadata could not be read.",
    "EXCEL_DRAWING_BINDINGS_UNRESOLVED": "Legacy drawing or control bindings require manual inspection.",
    "EXCEL_EXTERNAL_LINK_UNREADABLE": "An external link table is missing or unreadable.",
    "EXCEL_NAME_UNREADABLE": "A defined name has an unreadable formula.",
    "EXCEL_FORMULA_UNREADABLE": "A cell formula could not be decoded.",
    "EXCEL_CELL_LIMIT": "Cell inventory exceeded its configured limit.",
    "EXCEL_VBA_LIMIT": "A VBA source module exceeded the configured limit.",
    "EXCEL_VBA_UNREADABLE": "The VBA project was present but could not be read.",
    "EXCEL_VBA_RELATIONSHIP_UNSUPPORTED": "The VBA project relationship is missing or ambiguous.",
    "EXCEL_FORMAT_UNSUPPORTED": "Workbook extension is outside the supported format matrix.",
    "EXCEL_WORKBOOK_MISSING": "The explicitly declared workbook is unavailable.",
    "EXCEL_INPUT_LIMIT": "Workbook exceeds the per-workbook or aggregate byte limit.",
    "EXCEL_ARCHIVE_LIMIT": "Workbook archive exceeded its configured expansion or entry limit.",
    "EXCEL_UNSAFE_ARCHIVE": "Workbook archive contains encrypted, duplicate or unsafe entries.",
    "EXCEL_UNSAFE_XML": "Workbook XML contains a DTD or entity declaration.",
}


class Inventory:
    def __init__(self, selection):
        self.selection = selection
        self.evidence = {}
        self.relations = defaultdict(set)
        self.gaps = {}
        self.subjects = {}
        self.books = {}
        self.sheets = defaultdict(set)
        self.cells = {}
        self.names = defaultdict(list)
        self.procedures = defaultdict(list)
        self.formulas = []
        self.vba_modules = []
        self.triggers = []
        self.external = {}
        self.builtins = {}

    def add(self, kind, locator, **data):
        key = f"{kind}-{digest(locator)[:24]}"
        self.evidence[key] = {"id": key, "kind": kind, "locator": locator, **data}
        return key

    def require(self, key, label):
        self.subjects[key] = {"id": key, "label": label}

    def link(self, source, target, kind, *, location=None):
        key = self.add("vba-statement", location) if location else source
        self.relations[source, target, kind].add(key)

    def gap(self, code, locator, reason, *, identity=None):
        data = {"code": code, "reason": reason}
        if identity is not None:
            data["reference"] = identity
        key = self.add("gap", {**locator, **data}, **data)
        self.gaps[key] = self.evidence[key]
        location = {k: locator[k] for k in ("workbook", "sheet", "module") if k in locator}
        group = self.add("gap-group", {**location, "code": code}, code=code, reason=reason)
        self.require(group, f"{code} in {' / '.join(location.values())}")
        self.link(group, key, "contains")

    def register(self, book, sha, size, facts, problems):
        locator = {"workbook": book.id}
        format = book.path.suffix.lower().removeprefix(".")
        self.books[book.id] = {"id": book.id, "path": book.relative, "sha256": sha, "bytes": size,
                               "format": format, "parsed": facts is not None}
        for problem in problems:
            code = problem["code"]
            place = {**locator, **{k: problem[k] for k in ("sheet", "cell") if k in problem}}
            self.gap(code, place, KNOWN_DIAGNOSTICS.get(code, "Workbook worker did not complete."))
        if facts is None:
            return
        self.books[book.id]["date_1904"] = facts.get("date_1904", False)
        self.external[book.id] = facts["links"]
        self.builtins[book.id] = {name.casefold() for name in facts["builtin_functions"]}
        sheet_codes = defaultdict(set)
        for row in facts["sheets"]:
            name = row["name"]
            self.add("sheet", {**locator, "sheet": name}, visibility=row["visibility"],
                     code_name=row.get("code_name"))
            self.sheets[book.id, name.casefold()].add(name)
            if row.get("code_name"):
                sheet_codes[row["code_name"].casefold()].add(name)
        for row in facts["cells"]:
            sheet, cell = row["sheet"], row["cell"]
            details = {key: val for key, val in row.items() if key not in {"sheet", "cell"}}
            key = self.add("cell", {**locator, "sheet": sheet, "cell": cell}, **details)
            self.cells[book.id, sheet, cell] = key
            if row["type"] == "FORMULA":
                group = self.add("formula-group", {**locator, "sheet": sheet})
                self.require(group, f"Formula rules in {book.id}/{sheet}")
                self.link(group, key, "contains")
                if row.get("formula"):
                    self.formulas.append((key, row["formula"]))
        for row in facts["names"]:
            place = {**locator, "name": row["name"]}
            if "sheet" in row:
                place["sheet"] = row["sheet"]
            key = self.add("defined-name", place, formula=row.get("formula"))
            scope = row.get("sheet", "")
            self.names[book.id, scope, row["name"].casefold()].append(key)
            if row.get("formula"):
                self.formulas.append((key, row["formula"]))
        for row in facts["tables"]:
            self.add("table", {**locator, "sheet": row["sheet"], "name": row["name"]},
                     range=row["range"])
        connections = defaultdict(list)
        for row in facts.get("connections", []):
            place = {**locator, "part": row["part"], "connection": row["id"], "index": row["index"]}
            source = extraction.add_source(self, None, place, row["mechanism"], row.get("reference"))
            connections[row["id"]].append(source)
        for row in facts.get("query_tables", []):
            place = {**locator, "part": row["part"], "sheet": row["sheet"], "connection": row["id"]}
            query = self.add("query-table", place)
            sources = connections[row["id"]]
            if len(sources) == 1:
                self.link(query, sources[0], "source")
            else:
                self.gap("EXCEL_QUERY_SOURCE_UNRESOLVED", place, "Connection ID is absent or ambiguous.")
            if bounds := RANGE_TEXT.fullmatch(row.get("range", "")):
                target = self.address(book.id, row["sheet"], bounds[1], bounds[2])
                if target:
                    self.link(query, target, "writes")
        for row in facts["modules"]:
            self.vba_modules.append((book.id, row, facts.get("code_name"), sheet_codes))
        self.triggers.extend((book.id, item) for item in facts.get("triggers", []))

    def destination(self, source, identity):
        return self.selection.links.get((source, identity))

    @staticmethod
    def sheet_for_code(sheet_codes, name):
        candidates = sheet_codes.get(name, set())
        return next(iter(candidates)) if len(candidates) == 1 else None

    def address(self, book, sheet, first, last=None):
        if sheet is None:
            return None
        spellings = self.sheets.get((book, sheet.casefold()), set())
        if sheet not in spellings:
            if len(spellings) != 1:
                return None
            sheet = next(iter(spellings))
        normalized = []
        columns, rows = (256, 65536) if self.books[book]["format"] == "xls" else (16384, 1048576)
        for text in (first, last) if last else (first,):
            match = _CELL.fullmatch(text)
            if not match or _column_number(match[1]) > columns or int(match[2]) > rows:
                return None
            normalized.append(text.upper().replace("$", ""))
        if len(normalized) == 1:
            key = self.cells.get((book, sheet, normalized[0]))
            if key:
                return key
        return self.add("address", {"workbook": book, "sheet": sheet, "range": ":".join(normalized)},
                        value_observed=False)

    def formula_edges(self):
        for key, expression in self.formulas:
            locator = self.evidence[key]["locator"]
            book, sheet = locator["workbook"], locator.get("sheet")
            extraction.formula_observations(self, key, expression)
            syntax = _formula_syntax(expression)
            syntax = EXTERNAL_PREFIX.sub(lambda match: "'" + match.group().rstrip("!").strip() + "'!", syntax)
            calls = _formula_calls(syntax)
            if SCOPED_FORMULA.search(calls):
                self.gap("EXCEL_FORMULA_SCOPE_UNSUPPORTED", locator,
                         "Excel LET and LAMBDA declarations require lexical scope analysis.")
                continue
            if DYNAMIC_FORMULA.search(calls):
                self.gap("EXCEL_DYNAMIC_FORMULA", locator, "The formula contains a dynamic reference.")
                continue
            if "#REF!" in calls.upper():
                self.gap("EXCEL_BROKEN_REFERENCE", locator, "The formula contains an invalid Excel reference.")
                continue
            # A quoted external file path can contain a drive or URI colon.
            # Mask just that prefix before testing for a true sheet range.
            local_syntax = re.sub(
                r"'(?:[^']|'')+'(?=\s*!)",
                lambda match: re.sub(r"^'[^\[]*\[[^\]]+\]", "'External", match[0]),
                syntax,
            )
            if "[" in calls or _unsupported_reference_form(local_syntax):
                self.gap("EXCEL_FORMULA_REFERENCE_UNSUPPORTED", locator,
                         "The formula contains a structured, 3D or otherwise unsupported reference.")
                continue
            matches = _reference_matches(syntax)
            if matches is None:
                self.gap("EXCEL_FORMULA_REFERENCE_UNSUPPORTED", locator, "Formula qualifier could not be resolved.")
                continue
            remaining = list(calls)
            for match in matches:
                remaining[match.start():match.end()] = " " * (match.end() - match.start())
                qualifier, first, last = (match[1] or match[2]), match[3], match[4]
                target_book, target_sheet = book, sheet
                if qualifier is not None:
                    target_sheet = qualifier.replace("''", "'")
                    if external := EXTERNAL_SHEET.fullmatch(target_sheet):
                        prefix, token, target_sheet = external.groups()
                        external_links = self.external[book]
                        if prefix:
                            identity = prefix + token
                        elif token.isdecimal() and self.books[book]["format"] != "xls":
                            identity = external_links.get(token)
                        else:
                            identity = external_links.get(token, token)
                        target_book = self.destination(book, identity)
                        extraction.add_source(self, key, {**locator, "external_offset": match.start()},
                                              "external workbook", identity or token,
                                              mapped_workbook=target_book)
                        if not target_book:
                            self.gap("EXCEL_EXTERNAL_WORKBOOK", locator, "External workbook is not mapped.",
                                     identity=identity or token)
                            continue
                target = self.address(target_book, target_sheet, first, last)
                if target:
                    self.link(key, target, "reads")
                else:
                    self.gap("EXCEL_FORMULA_TARGET_UNRESOLVED", locator, "Referenced sheet or address is unresolved.")
            remaining = "".join(remaining)
            for token in FORMULA_NAME.finditer(remaining):
                symbol = token[1].casefold()
                named = (self.names[book, sheet or "", symbol]
                         or self.names[book, "", symbol])
                if remaining[token.end():].lstrip().startswith("("):
                    self.formula_call(key, locator, symbol, named)
                elif len(named) == 1:
                    self.link(key, named[0], "reads")
                elif len(named) > 1:
                    self.gap("EXCEL_NAME_AMBIGUOUS", locator, "Defined name has multiple candidates.")

    def formula_call(self, key, locator, symbol, named):
        book = locator["workbook"]
        if symbol in self.builtins[book] or symbol.startswith(("_xlfn.", "_xlws.")):
            return
        if named:
            self.gap("EXCEL_FORMULA_CALL_UNRESOLVED", locator,
                     "A defined name can shadow a workbook VBA function.")
            return
        if symbol.startswith("_xll."):
            self.gap("EXCEL_UDF_UNRESOLVED", locator, "The formula calls an external XLL function.")
            return
        function = symbol.removeprefix("_xludf.")
        targets = self.lookup(book, "", function, kinds={"function"}, public=True)
        if len(targets) == 1:
            self.link(key, targets[0], "calls")
        elif len(targets) > 1 or symbol.startswith("_xludf."):
            self.gap("EXCEL_UDF_UNRESOLVED", locator, "VBA function binding is unresolved.")

    def register_procedures(self):
        bodies = []
        for book, module, workbook_code, sheet_codes in self.vba_modules:
            name, source = module["name"], module["source"]
            group = self.add("vba-module", {"workbook": book, "module": name},
                             module_type=module.get("type"), source=source)
            if not module.get("type"):
                self.gap("VBA_MODULE_TYPE_UNRESOLVED", self.evidence[group]["locator"],
                         "The VBA module host may be a form or an unsupported project component.")
            for line, statement, _ in vba.statements(source):
                if re.match(r"^\s*(?:Private\s+|Public\s+)?Declare\b", statement, re.I):
                    self.gap("VBA_EXTERNAL_COMPONENT", {"workbook": book, "module": name, "line": line},
                             "Native Windows declaration requires an integration replacement.")
            for proc in vba.procedures(source):
                locator = {"workbook": book, "module": name, "procedure": proc.name,
                           "line": proc.start, "end_line": proc.end}
                key = self.add("vba-procedure", locator, declaration=proc.kind,
                               visibility=proc.visibility, complete=proc.complete)
                self.link(group, key, "contains")
                self.procedures[book, proc.name.casefold()].append((key, proc, name, module.get("type", "")))
                bodies.append((key, proc, name, sheet_codes))
                event = EVENT_NAME.fullmatch(proc.name)
                lower_name = name.casefold()
                kind = module.get("type", "").lower()
                if event and proc.kind == "sub":
                    sheet = self.sheet_for_code(sheet_codes, lower_name)
                    owner = event[1].casefold()
                    bound = (
                        owner == "workbook" and lower_name == (workbook_code or "ThisWorkbook").casefold()
                        and kind == "document"
                    ) or (owner == "worksheet" and sheet is not None and kind == "document")
                    if not bound or not proc.complete or event[2].casefold() not in vba.EVENTS[owner]:
                        self.gap("VBA_EVENT_BINDING_UNRESOLVED", locator, "Event host or event type is unresolved.")
                    else:
                        entry = self.add("entrypoint", {**locator, "event": proc.name}, sheet=sheet)
                        self.link(entry, key, "calls")
                        self.require(entry, f"Event {book}/{name}.{proc.name}")
                elif proc.kind == "sub" and not proc.parameters and proc.visibility == "public" and kind == "module":
                    self.require(key, f"Public macro {book}/{name}.{proc.name}")
                if not proc.complete:
                    self.gap("VBA_PROCEDURE_INCOMPLETE", locator, "Procedure boundary is incomplete.")
        return bodies

    def lookup(self, book, module, reference, *, kinds=None, public=False):
        tokens = reference.casefold().split(".")
        found = []
        local = []
        for key, proc, owner, module_type in self.procedures[book, tokens[-1]]:
            same_module = owner.casefold() == module.casefold()
            if (not proc.complete or (kinds is not None and proc.kind not in kinds)
                    or (len(tokens) == 2 and owner.casefold() != tokens[0])
                    or ((public or not same_module) and proc.visibility != "public")
                    or (not same_module and module_type.casefold() != "module")):
                continue
            found.append(key)
            if same_module:
                local.append(key)
        return local or found

    def call(self, key, locator, module, reference, *, target_book=None, public=False):
        targets = self.lookup(target_book or locator["workbook"], module, reference, public=public)
        if len(targets) == 1:
            self.link(key, targets[0], "calls", location=locator if "line" in locator else None)
        else:
            self.gap("VBA_CALL_UNRESOLVED", locator, "Procedure is absent or has multiple candidates.")

    def run_target(self, key, location, reference, *, local=False):
        book = location["workbook"]
        qualifier, separator, procedure = reference.rpartition("!")
        if not separator:
            if local and re.fullmatch(vba.QUALIFIED, reference):
                self.call(key, location, "", reference, target_book=book, public=True)
            else:
                self.gap("VBA_DYNAMIC_DISPATCH", location, "Macro target depends on the active workbook.")
            return
        identity = qualifier.strip("'").replace("''", "'")
        target_book = book if identity == "[0]" else self.destination(book, identity)
        if target_book and re.fullmatch(vba.QUALIFIED, procedure):
            self.call(key, location, "", procedure, target_book=target_book, public=True)
        else:
            self.gap("VBA_EXTERNAL_MACRO", location, "External macro or workbook binding is unresolved.",
                     identity=identity)

    def vba_edges(self, bodies):
        for key, proc, module, sheet_codes in bodies:
            if not proc.complete:
                continue
            original = self.evidence[key]["locator"]
            book = original["workbook"]
            shadowed = proc.shadowed_names()
            project_dispatch = {
                name for name, reference in (("run", "Run"), ("application", "Application.Run"))
                if self.lookup(book, module, reference)
            }
            if any(re.match(r"^\s*#", statement) for _, statement in proc.statements):
                self.gap("VBA_CONDITIONAL_COMPILATION", original, "Conditional compilation context is unknown.")
                continue
            operations = extraction.vba_observations(self, key, proc)
            for index, (line, statement) in enumerate(proc.statements, 1):
                operation = operations.get(index)
                place = {**original, "line": line, "end_line": line}
                text = vba.mask(statement)
                for code in sorted(vba.dynamic_flags(text, statement)):
                    self.gap(code, place, "VBA behavior depends on dynamic Excel state or an external operation.")
                in_ranges = list(vba.RANGE.finditer(statement))
                for match in in_ranges:
                    if not text[match.start():match.start()+1].strip():
                        continue
                    prefix = text[:match.start()]
                    assignment = bool(vba.ASSIGNMENT_START.search(prefix)
                                      and re.match(r"\s*=", text[match.end():]))
                    if vba.SET_STATEMENT.search(prefix) or (not assignment and not match["property"]):
                        self.gap("VBA_RANGE_OBJECT_UNRESOLVED", place,
                                 "Range object binding or use requires manual alias analysis.")
                        continue
                    workbook_name, sheet_name, receiver, raw_range = map(vba.literal, match.groups()[:4])
                    target_book = book
                    if workbook_name:
                        target_book = self.destination(book, workbook_name)
                    elif sheet_name and not re.match(r"(?i)^ThisWorkbook\b", match.group()):
                        target_book = None
                    if sheet_name is None and receiver:
                        name = receiver.casefold()
                        if name not in shadowed:
                            sheet_name = self.sheet_for_code(sheet_codes, module.casefold() if name == "me" else name)
                    target = None
                    if raw_range and (values := RANGE_TEXT.fullmatch(raw_range)) and target_book:
                        target = self.address(target_book, sheet_name, values[1].strip(),
                                              values[2].strip() if values[2] else None)
                    if target:
                        role = "writes" if assignment else "reads"
                        self.link(key, target, role, location=place)
                        if operation:
                            self.link(operation, target, role)
                    else:
                        self.gap("VBA_RANGE_UNRESOLVED", place, "Workbook, sheet or VBA range is unresolved.",
                                 identity=workbook_name)
                runs = list(vba.run_targets(text, statement, shadowed,
                                            project_dispatch=project_dispatch))
                for reference in runs:
                    if reference is None:
                        self.gap("VBA_DYNAMIC_DISPATCH", place, "The Run macro argument is dynamic.")
                    else:
                        self.run_target(key, place, reference)
                explicit = vba.CALL.match(text)
                if explicit and not runs:
                    self.call(key, place, module, explicit[1])
                elif not runs and not vba.BARE_CONTROL.match(text):
                    bare = vba.BARE.match(text)
                    if (bare and bare[1].split(".")[0].casefold() not in shadowed
                            and self.lookup(book, module, bare[1])):
                        self.call(key, place, module, bare[1])
                for call in vba.FUNCTION_CALL.finditer(text):
                    name = call[1]
                    if name.split(".")[0].casefold() not in shadowed:
                        targets = self.lookup(book, module, name, kinds={"function"})
                        if len(targets) == 1:
                            self.link(key, targets[0], "calls", location=place)
                            if operation and name in self.evidence[operation]["functions"]:
                                self.link(operation, targets[0], "calls")
                        elif len(targets) > 1:
                            self.gap("VBA_CALL_UNRESOLVED", place, "Function call has multiple candidates.")
        for book, row in self.triggers:
            locator = {"workbook": book, "sheet": row["sheet"], "control": row["control"]}
            key = self.add("entrypoint", locator, event="on_action")
            self.require(key, f"Control action in {book}/{row['sheet']}")
            reference = row["macro"]
            if reference.startswith("[0]!"):
                reference = reference[4:]
            self.run_target(key, locator, reference, local=True)

    def document(self):
        procedures = self.register_procedures()
        self.formula_edges()
        self.vba_edges(procedures)
        body = {
            "schema_version": 1, "analyzer": VERSION, "worker": WORKER,
            "manifest_sha256": self.selection.sha256, "main": self.selection.main,
            "status": "PARTIAL" if self.gaps else "ANALYZED",
            "workbooks": list(self.books.values()),
            "evidence": sorted(self.evidence.values(), key=lambda value: value["id"]),
            "subjects": sorted(self.subjects.values(), key=lambda value: value["id"]),
            "relations": [{"source": source, "target": target, "kind": kind,
                           "evidence": sorted(self.relations[source, target, kind])}
                          for source, target, kind in sorted(self.relations)],
        }
        return {**body, "inventory_id": digest(body)}


def analyze(manifest_path: Path, *, selection=None) -> dict:
    return analyze_selection(selection or manifest(manifest_path))


def analyze_selection(selection) -> dict:
    inventory = Inventory(selection)
    command = None
    total = 0
    for book in selection.books:
        if not book.path.exists() and book.id != selection.main:
            sha, size, facts = None, 0, None
            diagnostics = [{"code": "EXCEL_WORKBOOK_MISSING"}]
        elif total + book.path.stat().st_size > MAX_TOTAL_BYTES:
            sha, size = capture(book)
            facts, diagnostics = None, [{"code": "EXCEL_INPUT_LIMIT"}]
        else:
            command = command or worker_command()
            sha, size, facts, diagnostics = extract(command, book)
            if total + size > MAX_TOTAL_BYTES:
                facts, diagnostics = None, [{"code": "EXCEL_INPUT_LIMIT"}]
        if book.id == selection.main and facts is None:
            raise AnalysisError(f"Cannot analyze main workbook {book.id}: {diagnostics[0]['code']}")
        total += size
        inventory.register(book, sha, size, facts, diagnostics)
    return inventory.document()


def assert_fresh(manifest_path: Path, inventory: dict):
    selection = manifest(manifest_path)
    assert_selection_fresh(selection, inventory)
    return selection


def assert_selection_fresh(selection, inventory: dict) -> None:
    if selection.sha256 != inventory["manifest_sha256"]:
        raise AnalysisError("Excel inventory is stale: manifest changed")
    captured = {row["id"]: row["sha256"] for row in inventory["workbooks"]}
    for book in selection.books:
        sha = capture(book)[0] if book.path.exists() else None
        if book.id not in captured or captured[book.id] != sha:
            raise AnalysisError(f"Excel inventory is stale: workbook {book.id} changed")
