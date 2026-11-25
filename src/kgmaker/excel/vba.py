"""A deliberately bounded VBA recognizer with original line locations."""

from __future__ import annotations

import re
from dataclasses import dataclass

IDENTIFIER = r"[A-Za-z_][\w]*"
QUALIFIED = rf"(?:{IDENTIFIER}\.)?{IDENTIFIER}"
STRING = r'"((?:[^"]|"")*)"'
DECLARATION = re.compile(
    rf"^\s*(?:(Private|Public|Friend)\s+)?(?:Static\s+)?"
    rf"(Sub|Function|Property\s+(?:Get|Let|Set))\s+({IDENTIFIER})"
    r"\s*(?:\((.*?)\))?", re.I
)
END = re.compile(r"^\s*End\s+(?:Sub|Function|Property)\s*$", re.I)
LEXEME = re.compile(r'''"(?:[^"]|"")*"|'[^\n]*''')
CALL = re.compile(rf"^\s*Call\s+({QUALIFIED})(?!\w)", re.I)
BARE = re.compile(rf"^\s*({QUALIFIED})(?:\s+[^\s=].*|\([^=]*\))?\s*$", re.I)
FUNCTION_CALL = re.compile(rf"(?<![.\w])({QUALIFIED})\s*\(")
RUN = re.compile(r"(?:(?<![.\w])(?P<application>Application)\s*\.\s*|^\s*(?:Call\s+)?)Run\b", re.I)
RUN_LITERAL = re.compile(
    rf"\s*(?:(?P<parenthesis>\()\s*)?{STRING}"
    r"(?=\s*(?:,|(?(parenthesis)\)\s*(?=,|\)|$)|$)))"
)
RANGE = re.compile(
    rf"(?<![.\w])(?:"
    rf"(?:(?:ThisWorkbook\s*\.\s*|Workbooks\s*\(\s*{STRING}\s*\)\s*\.\s*))?"
    rf"(?:Worksheets|Sheets)\s*\(\s*{STRING}\s*\)\s*\.\s*"
    rf"|(?:({IDENTIFIER})\s*\.\s*)?"
    rf")Range\s*\(\s*{STRING}\s*\)(?:\s*\.\s*(?P<property>Value2?|Formula2?))?\s*(?=\s|=|$|[,;)])",
    re.I
)
EVENTS = {
    "workbook": frozenset({
        "open", "beforeclose", "beforesave", "aftersave", "activate", "deactivate",
        "newsheet", "sheetactivate", "sheetchange", "sheetcalculate", "sheetselectionchange",
    }),
    "worksheet": frozenset({
        "activate", "deactivate", "change", "calculate", "selectionchange", "beforedoubleclick",
        "beforerightclick", "followhyperlink",
    }),
}
SIDE_EFFECTS = (
    (re.compile(r"\b(?:CreateObject|GetObject|Declare)\b", re.I), "VBA_EXTERNAL_COMPONENT"),
    (re.compile(r"\b(?:Shell|Open\s+.+?\s+For|Kill|FileCopy|SaveAs|SaveCopyAs|ExportAsFixedFormat|"
                r"Workbooks\s*\.\s*Open|XMLHTTP|WinHttpRequest|ADODB|FollowHyperlink)\b", re.I),
     "VBA_EXTERNAL_EFFECT"),
    (re.compile(r"\b(?:Evaluate|CallByName|OnTime|OnKey|RaiseEvent)\b", re.I), "VBA_DYNAMIC_DISPATCH"),
    (re.compile(r"\b(?:ActiveWorkbook|ActiveSheet|ActiveCell|Selection|Offset|Cells)\b", re.I), "VBA_DYNAMIC_RANGE"),
    (re.compile(r"\b(?:EnableEvents|Calculation|CalculateFull|Calculate)\b", re.I), "VBA_EXCEL_STATE"),
)
ASSIGNMENT_START = re.compile(r"(?:^|\b(?:Then|Else)\b)\s*(?:Let\s+)?$", re.I)
SET_STATEMENT = re.compile(r"(?:^|\b(?:Then|Else)\b)\s*Set\s+", re.I)
BARE_CONTROL = re.compile(
    r"^\s*(?:Rem|If|ElseIf|Else|End|For|Next|Do|Loop|While|Wend|Select|Case|GoTo|GoSub|"
    r"Exit|Resume|On|Dim|Redim|Set|Let|Const|Static|With|Attribute)\b", re.I
)


@dataclass
class Procedure:
    name: str
    kind: str
    visibility: str
    parameters: str
    start: int
    end: int
    statements: list[tuple[int, str]]
    complete: bool

    def shadowed_names(self) -> set[str]:
        names = set()
        declarations = [self.parameters]
        for _, statement in self.statements:
            match = re.match(r"^\s*(?:Dim|Static|Const|ReDim(?:\s+Preserve)?)\s+(.+)", statement, re.I)
            if match:
                declarations.append(match.group(1))
        for declaration in declarations:
            for part in declaration.split(","):
                name = re.match(
                    rf"\s*(?:(?:Optional|ByVal|ByRef|ParamArray)\s+)*({IDENTIFIER})", part, re.I)
                if name:
                    names.add(name.group(1).casefold())
        return names


def mask(text: str) -> str:
    return LEXEME.sub(lambda match: " " * len(match.group()), text)


def _commentless(text: str) -> str:
    for token in LEXEME.finditer(text):
        if token.group().startswith("'"):
            return text[:token.start()]
    return text


def statements(source: str):
    pending = ""
    start = 0
    for line, raw in enumerate(source.splitlines(), 1):
        clean = _commentless(raw).rstrip()
        if not pending:
            start = line
        if clean.endswith(" _"):
            pending += clean[:-2] + " "
            continue
        combined = pending + clean
        pending = ""
        offset = 0
        for separator in re.finditer(r":(?![=])", mask(combined)):
            segment = combined[offset:separator.start()]
            if re.match(r"^\s*Rem(?:\s|$)", segment, re.I):
                break
            if segment.strip():
                yield start, segment, line
            offset = separator.end()
        else:
            tail = combined[offset:]
            if tail.strip() and not re.match(r"^\s*Rem(?:\s|$)", tail, re.I):
                yield start, tail, line
    if pending.strip():
        yield start, pending, start


def procedures(source: str) -> list[Procedure]:
    result = []
    current = None
    for first, statement, last in statements(source):
        declaration = DECLARATION.match(statement)
        if declaration:
            visibility, kind, name, parameters = declaration.groups()
            current = Procedure(name, kind.lower(), (visibility or "public").lower(),
                                parameters or "", first, last, [], False)
            result.append(current)
        elif current is not None:
            current.end = last
            if END.match(statement):
                current.complete = True
                current = None
            else:
                current.statements.append((first, statement))
    return result


def literal(value: str | None) -> str | None:
    return None if value is None else value.replace('""', '"')


def run_targets(text: str, statement: str, shadowed: set[str], *, project_dispatch: set[str]):
    """Find Excel dispatch sites in masked VBA and parse the entire first argument."""
    for site in RUN.finditer(text):
        receiver = "application" if site["application"] else "run"
        if receiver in shadowed:
            yield None
            continue
        if receiver in project_dispatch:
            continue
        match = RUN_LITERAL.match(statement, site.end())
        yield literal(match[2]) if match else None


def dynamic_flags(text: str, statement: str) -> set[str]:
    flags = {code for pattern, code in SIDE_EFFECTS if pattern.search(text)}
    if re.search(r"\bRange\s*\(", text, re.I) and not RANGE.search(statement):
        flags.add("VBA_DYNAMIC_RANGE")
    if re.search(r"^\s*#(?:If|ElseIf|Else|End If)\b", text, re.I):
        flags.add("VBA_CONDITIONAL_COMPILATION")
    return flags
