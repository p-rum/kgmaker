"""Source observations for formula operations and bounded VBA data flow."""

from __future__ import annotations

import re
from collections import defaultdict

from ..workbooks import _formula_calls, _formula_syntax
from . import vba

FORMULA_CALL = re.compile(r"(?<![\w.])([A-Za-z_][\w.]*)\s*\(")
WEB_FORMULA = re.compile(r"(?<![\w.])(?:_xlfn\.)?WEBSERVICE\s*\(", re.I)
FORMULA_URL = re.compile(rf"\s*{vba.STRING}\s*\)")
OPERATORS = {"+": "addition", "-": "subtraction or negation", "*": "multiplication",
             "/": "division", "\\": "integer division", "^": "power", "&": "concatenation"}
CONTROL_FLOW = re.compile(r"^\s*(?:If|ElseIf|Else|Select|Case|For|Do|While|GoTo|GoSub|Resume|Exit|On Error)\b", re.I)
INLINE_IF = re.compile(r"^\s*If\b.*?\bThen\s+(?=\S)", re.I)
BLOCK_END = re.compile(r"^\s*(End\s+If|End\s+Select|Next|Loop|Wend)\b", re.I)
ASSIGN = re.compile(r"^\s*(?:(Set|Let)\s+)?(.+?)\s*(?<![:<>=])=(?!=)", re.I)
SYMBOL = re.compile(vba.IDENTIFIER)
MEMBER = re.compile(rf"{vba.IDENTIFIER}(?:\s*\.\s*{vba.IDENTIFIER})+", re.I)
RANGE_TARGET = re.compile(r"(?:^|\.)\s*(?:Range|Cells)\s*\(", re.I)
VALUE_TOKEN = re.compile(rf"(?<![.\w])({vba.IDENTIFIER})\b(?!\s*[.(])", re.I)
CREATE = re.compile(rf"^\s*CreateObject\s*\(\s*{vba.STRING}\s*\)\s*$", re.I)
NEW_CLIENT = re.compile(rf"^\s*(?:Dim\s+({vba.IDENTIFIER})\s+As\s+)?New\s+([\w.]+)\s*$", re.I)
OPEN = re.compile(rf"^\s*(?:Call\s+)?({vba.IDENTIFIER})\s*\.\s*Open\s*(?:\(\s*)?{vba.STRING}\s*,", re.I)
SEND = re.compile(rf"^\s*(?:Call\s+)?({vba.IDENTIFIER})\s*\.\s*Send\b", re.I)
RESPONSE = re.compile(rf"(?<![.\w])({vba.IDENTIFIER})\s*\.\s*Response(?:Text|Body|XML)\b", re.I)
VBA_URL = re.compile(rf"\s*(?:{vba.STRING}|({vba.IDENTIFIER}))\s*(?=,|\)\s*$|$)", re.I)
HTTP_CLASS = re.compile(r"(?:MSXML2\.(?:Server)?XMLHTTP(?:\.\d+\.\d+|\d+)?|"
                        r"Microsoft\.XMLHTTP|WinHttp\.WinHttpRequest(?:\.\d+\.\d+)?)", re.I)
HTTP_METHODS = {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE", "CONNECT"}
HTTP_URL = re.compile(r"https?://[^\s]+", re.I)
MAX_ALTERNATIVES = 8
DISPLAY_MEMBER = re.compile(r"\.\s*(?:Caption|Text|Visible)\s*$", re.I)
MESSAGE = re.compile(r"^\s*(?:Call\s+)?MsgBox\b", re.I)
NON_MUTATING_INTRINSICS = {
    "abs", "asc", "atn", "cbool", "cbyte", "ccur", "cdate", "cdbl", "cdec", "cint", "clng",
    "csng", "cstr", "cvar", "dateadd", "datediff", "datepart", "dateserial", "datevalue", "day",
    "exp", "fix", "format", "formatcurrency", "formatdatetime", "formatnumber", "formatpercent",
    "hour", "instr", "instrrev", "int", "isarray", "isdate", "isempty", "iserror", "ismissing",
    "isnull", "isnumeric", "isobject", "lcase", "left", "len", "log", "ltrim", "mid", "minute",
    "month", "monthname", "now", "replace", "right", "rnd", "second", "sgn", "sin", "space",
    "sqr", "strcomp", "string", "strreverse", "time", "timer", "timeserial", "timevalue", "trim",
    "typename", "ucase", "val", "vartype", "weekday", "year",
}


def operators(masked, *, excel=False):
    symbols = OPERATORS if not excel else {**OPERATORS, "%": "percentage"}
    return [description for symbol, description in symbols.items() if symbol in masked]


def add_source(inventory, owner, locator, mechanism, reference=None, **details):
    key = inventory.add("external-source", {**locator, "mechanism": mechanism},
                        mechanism=mechanism, reference=reference, **details)
    if owner is not None:
        inventory.link(owner, key, "source")
    return key


def formula_observations(inventory, key, expression):
    calls = _formula_calls(_formula_syntax(expression))
    item = inventory.evidence[key]
    # Strip sheet qualifiers and path punctuation before describing arithmetic.
    arithmetic = re.sub(r"(?:\[[^]]*\])?[\w.]+\s*!", "", calls)
    item["operators"] = operators(arithmetic, excel=True)
    item["functions"] = sorted({match[1].upper().removeprefix("_XLFN.").removeprefix("_XLWS.")
                                for match in FORMULA_CALL.finditer(calls)})
    for index, site in enumerate(WEB_FORMULA.finditer(calls), 1):
        argument = FORMULA_URL.match(expression, site.end())
        reference = vba.literal(argument[1]) if argument else None
        add_source(inventory, key, {**item["locator"], "source_index": index},
                   "WEBSERVICE", reference if reference and HTTP_URL.fullmatch(reference) else None)


def _assignment(text, statement):
    match = ASSIGN.match(text)
    if match is None:
        return None
    # The mask preserves offsets but can erase an entire literal right-hand side.
    target = statement[match.start(2):match.end(2)].strip()
    value = statement[match.end():].strip()
    if value and not vba.BARE_CONTROL.match(target) and (
        SYMBOL.fullmatch(target) or MEMBER.fullmatch(target) or RANGE_TARGET.search(vba.mask(target))
    ):
        return match[1], target, value
    return None


def _literal(expression):
    match = re.fullmatch(vba.STRING, expression)
    return vba.literal(match[1]) if match else None


def _forget_opaque_writes(tokens, variables, clients, requests):
    for token in tokens:
        variables.pop(token, None)
        clients.discard(token)
        requests.pop(token, None)


def _non_mutating_calls(expression, inventory, owner, proc):
    functions = [match[1].casefold() for match in vba.FUNCTION_CALL.finditer(expression)]
    if not functions:
        return False
    locator = inventory.evidence[owner]["locator"]
    shadowed = proc.shadowed_names()
    return all(name in NON_MUTATING_INTRINSICS and name not in shadowed
               and not inventory.lookup(locator["workbook"], locator["module"], name, kinds={"function"})
               for name in functions)


def _block_start(text, inline):
    if inline:
        return None
    if re.match(r"^\s*If\b", text, re.I) and re.search(r"\bThen\s*$", text, re.I):
        return "if"
    if re.match(r"^\s*Select\s+Case\b", text, re.I):
        return "select"
    if re.match(r"^\s*For\b", text, re.I):
        return "for"
    if re.match(r"^\s*Do\b", text, re.I):
        return "loop"
    if re.match(r"^\s*While\b", text, re.I):
        return "while"
    return None


def _close_block(blocks, text):
    match = BLOCK_END.match(text)
    if not match:
        return
    kind = " ".join(match[1].casefold().split())
    closures = 1
    if kind == "next":
        counters = text[match.end():].split(",")
        if all(SYMBOL.fullmatch(counter.strip()) for counter in counters):
            closures = len(counters)
    kind = "if" if kind == "end if" else "select" if kind == "end select" else (
        "for" if kind == "next" else "loop" if kind == "loop" else "while"
    )
    for index in range(len(blocks) - 1, -1, -1):
        if blocks[index][0] == kind:
            del blocks[index:]
            closures -= 1
            if not closures:
                return


def vba_observations(inventory, owner, proc):
    """Record textual operations and possible local definitions without executing VBA."""
    definition = inventory.evidence[owner]["locator"]
    local_names = proc.shadowed_names()
    variables = defaultdict(list)
    literals = {}
    clients = set()
    requests = defaultdict(list)
    operations = {}
    blocks = []
    for index, (line, statement) in enumerate(proc.statements, 1):
        text = vba.mask(statement)
        locator = {**definition, "line": line, "end_line": line, "statement": index}
        control = bool(CONTROL_FLOW.match(text))
        inline = INLINE_IF.match(text)
        _close_block(blocks, text)
        branch_flow = bool(blocks) or control or bool(inline)
        block_start = _block_start(text, inline)
        offset = inline.end() if inline else 0
        action = text[offset:]
        raw = statement[offset:]
        assignment = _assignment(action, raw)
        request = OPEN.match(raw)
        send = SEND.match(action)
        expression = action
        role = "statement"
        symbol = None
        initializes_http = False
        if assignment:
            modifier, target, expression = assignment
            role = "display-write" if DISPLAY_MEMBER.search(target) else "assignment"
            if SYMBOL.fullmatch(target):
                symbol = target.casefold()
                if proc.kind == "function" and symbol == proc.name.casefold():
                    role = "return-value"
                if modifier and modifier.casefold() == "set":
                    created = CREATE.fullmatch(expression)
                    new = NEW_CLIENT.fullmatch(expression)
                    class_name = vba.literal(created[1]) if created else new[2] if new else ""
                    requests.pop(symbol, None)
                    if HTTP_CLASS.fullmatch(class_name):
                        clients.add(symbol)
                        initializes_http = True
                    else:
                        clients.discard(symbol)
        elif (new := NEW_CLIENT.fullmatch(raw)) and new[1] and HTTP_CLASS.fullmatch(new[2]):
            clients.add(new[1].casefold())
            initializes_http = True
        elif request and request[1].casefold() in clients:
            role = "http-open"
        elif send and send[1].casefold() in clients:
            role = "http-send"
        elif MESSAGE.match(action):
            role = "message"
        elif control:
            role = "condition"
        elif vba.dynamic_flags(action, raw):
            role = "unresolved-operation"

        # Ordinary declarations and comments are not functional evidence. The
        # inventory still retains the original module and call/reference edges.
        non_mutating = _non_mutating_calls(action, inventory, owner, proc)
        if role == "statement":
            if not initializes_http:
                if not non_mutating:
                    literals.clear()
                tokens = {match[1].casefold() for match in VALUE_TOKEN.finditer(action)}
                if not non_mutating:
                    _forget_opaque_writes(tokens, variables, clients, requests)
            continue
        rhs = vba.mask(expression)
        functions = sorted({match[1] for match in vba.FUNCTION_CALL.finditer(rhs)}, key=str.casefold)
        non_mutating = _non_mutating_calls(rhs, inventory, owner, proc)
        item = inventory.add("vba-operation", locator, operation=role, source=statement.strip(),
                             operators=operators(rhs), functions=functions, conditional=branch_flow)
        operations[index] = item
        inventory.link(owner, item, "contains")
        if blocks:
            kind, previous = blocks[-1]
            inventory.link(item, previous, "guarded-by")
            if ((kind == "if" and re.match(r"^\s*Else(?:If)?\b", text, re.I))
                    or (kind == "select" and re.match(r"^\s*Case\b", text, re.I))):
                blocks[-1] = (kind, item)
        alternatives = {}
        tokens = sorted({match[1].casefold() for match in VALUE_TOKEN.finditer(rhs)})
        for token in tokens:
            definitions = variables.get(token, ())
            definitions = definitions[-MAX_ALTERNATIVES:]
            for candidate in definitions:
                inventory.link(item, candidate, "depends-on")
            if len(definitions) > 1:
                alternatives[token] = list(definitions)
        if alternatives:
            inventory.evidence[item]["alternatives"] = alternatives
        for response in RESPONSE.finditer(rhs):
            for source in requests.get(response[1].casefold(), ())[-MAX_ALTERNATIVES:]:
                inventory.link(item, source, "source")
        if role == "http-open":
            receiver, method = request[1].casefold(), vba.literal(request[2]).upper()
            argument = VBA_URL.match(raw, request.end())
            url = None
            binding = None
            if argument:
                if argument[1] is not None:
                    url = vba.literal(argument[1])
                elif argument[2].casefold() in literals:
                    url, binding = literals[argument[2].casefold()]
            source = add_source(inventory, item, locator, "VBA HTTP",
                                url if url and HTTP_URL.fullmatch(url) else None,
                                method=method if method in HTTP_METHODS else None)
            if binding is not None:
                inventory.link(source, binding, "depends-on")
            if not branch_flow:
                requests[receiver].clear()
            requests[receiver].append(source)
        elif role == "http-send":
            for source in requests.get(send[1].casefold(), ())[-MAX_ALTERNATIVES:]:
                inventory.link(item, source, "source")
        elif not initializes_http and (
            role == "unresolved-operation"
            or (functions and not _non_mutating_calls(rhs, inventory, owner, proc))
        ):
            _forget_opaque_writes(tokens, variables, clients, requests)
        if symbol:
            if not branch_flow:
                variables[symbol].clear()
            variables[symbol].append(item)
        # Only use literal bindings across statements that cannot pass a local
        # string ByRef. An opaque call, property write, or other expression can
        # change it. Keep the request declaration but leave its endpoint open.
        value = _literal(expression) if not branch_flow and symbol in local_names else None
        if value is not None:
            literals[symbol] = (value, item)
        elif not initializes_http:
            if non_mutating and symbol:
                literals.pop(symbol, None)
            elif not non_mutating:
                literals.clear()
        if block_start:
            blocks.append((block_start, item))
    if proc.kind == "function":
        for result in variables.get(proc.name.casefold(), ())[-MAX_ALTERNATIVES:]:
            inventory.link(owner, result, "returns")
    return operations
