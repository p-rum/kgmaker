"""Conservative, non-executing Thymeleaf template and fragment facts."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field, replace
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
import re

from .analysis_model import digest
from .model import Edge, KnowledgeGraph, Node

VERSION = "thymeleaf-bindings-2"
_IDENT = r"[A-Za-z_][A-Za-z0-9_]*"
_PATH_EXPR = re.compile(rf"^{_IDENT}(?:\.{_IDENT})*$")
_FRAGMENT_DECL = re.compile(rf"^\s*({_IDENT})\s*(?:\((.*)\))?\s*$")
_FRAGMENT_CALL = re.compile(rf"^\s*({_IDENT})\s*(?:\((.*)\))?\s*$")
_MODEL_BINDING = re.compile(rf"\b(?:addAttribute|setVariable)\s*\(\s*['\"]({_IDENT})['\"]\s*,")
_VIEW_RETURN = re.compile(r"\breturn\s+['\"]([A-Za-z_][A-Za-z0-9_./-]*)['\"]")
_PDF_CALL = re.compile(r"\b(?:pdfService|pdfRenderer)\s*\.\s*\w+\s*\(\s*['\"]([A-Za-z_][A-Za-z0-9_./-]*)['\"]", re.I)
_VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
_REFERENCE_ATTRIBUTES = {"th:replace", "th:insert", "data-th-replace", "data-th-insert"}
_CONDITION_ATTRIBUTES = {"th:if", "th:unless", "data-th-if", "data-th-unless"}


def _line(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _node_id(kind: str, path: str, name: str) -> str:
    return f"{kind}:{path}:{name}"


def _template_root(path: str) -> str:
    parts = PurePosixPath(path).parts
    if "templates" not in parts:
        return ""
    index = parts.index("templates")
    return PurePosixPath(*parts[:index + 1]).as_posix()


def _expressions(value: str) -> list[tuple[str, bool]]:
    """Extract balanced `${...}` bodies; flag nested or unclosed forms."""
    result: list[tuple[str, bool]] = []
    cursor = 0
    while True:
        start = value.find("${", cursor)
        if start < 0:
            break
        index = start + 2
        depth = 1
        while index < len(value) and depth:
            if value.startswith("${", index):
                depth += 1
                index += 2
                continue
            if value[index] == "}":
                depth -= 1
                if depth == 0:
                    break
            index += 1
        if depth:
            result.append((value[start:], False))
            break
        body = value[start + 2:index]
        result.append((body, body.find("${") < 0))
        cursor = index + 1
    return result


def _parse_fragment_declaration(value: str) -> tuple[str, tuple[str, ...]] | None:
    match = _FRAGMENT_DECL.fullmatch(value)
    if not match:
        return None
    name = match.group(1)
    raw = match.group(2)
    if raw is None or not raw.strip():
        return name, ()
    parameters = tuple(part.strip() for part in raw.split(","))
    if (any(not re.fullmatch(_IDENT, item) for item in parameters)
            or len(set(parameters)) != len(parameters)):
        return None
    return name, parameters


def _split_arguments(raw: str) -> list[str] | None:
    if not raw.strip():
        return []
    # The supported call grammar has no nested calls or comma-bearing literals.
    values = [item.strip() for item in raw.split(",")]
    if any(not item or any(char in item for char in "()") for item in values):
        return None
    return values


def _parse_fragment_reference(value: str) -> tuple[str, str, list[str] | None] | None:
    raw = value.strip()
    if raw.startswith("~{") and raw.endswith("}"):
        raw = raw[2:-1].strip()
    elif "${" in raw or "#{" in raw or "*{" in raw:
        return None
    if raw.count("::") != 1:
        return None
    target, fragment = (part.strip() for part in raw.split("::", 1))
    call = _FRAGMENT_CALL.fullmatch(fragment)
    if not call:
        return None
    arguments = _split_arguments(call.group(2) or "") if call.group(2) is not None else []
    if arguments is None:
        return None
    return target, call.group(1), arguments


@dataclass
class _Fragment:
    node: Node
    name: str
    parameters: tuple[str, ...]
    parameter_nodes: dict[str, Node] = field(default_factory=dict)


@dataclass
class _TemplateFacts:
    template: Node
    fragments: list[_Fragment] = field(default_factory=list)
    variables: dict[str, Node] = field(default_factory=dict)
    conditions: dict[str, Node] = field(default_factory=dict)
    references: list[tuple[str, str, list[str], int]] = field(default_factory=list)
    diagnostics: list[dict] = field(default_factory=list)


class _TemplateParser(HTMLParser):
    def __init__(self, path: str, source: str, file_node: Node, facts: _TemplateFacts):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.source = source
        self.file_node = file_node
        self.facts = facts
        self.stack: list[tuple[str, str | None]] = []
        self.fragments_by_id: dict[str, _Fragment] = {}

    def _owner(self) -> tuple[str, Node]:
        fragment_id = next((item[1] for item in reversed(self.stack) if item[1]), None)
        if fragment_id:
            fragment = self.fragments_by_id[fragment_id]
            return fragment_id, fragment.node
        return self.facts.template.id, self.facts.template

    def _diagnostic(self, code: str, reason: str, line: int, *, expression: str | None = None) -> None:
        item = {"code": code, "path": self.path, "source_line": line, "reason": reason,
                "status": "UNKNOWN"}
        if expression is not None:
            item["expression"] = expression
        self.facts.diagnostics.append(item)

    def _variable(self, expression: str, line: int, usage: str) -> Node | None:
        if not _PATH_EXPR.fullmatch(expression):
            self._diagnostic("TEMPLATE_EXPRESSION_UNSUPPORTED",
                             "Only a literal Thymeleaf property path is retained; expression was not evaluated.",
                             line, expression=expression)
            return None
        owner_id, owner = self._owner()
        is_fragment = owner.kind == "template_fragment"
        identity = (_node_id("template_variable", self.path, expression) if not is_fragment else
                    _node_id("template_variable", self.path,
                             f"fragment:{owner.name}:{owner.line}:{expression}"))
        old = self.facts.variables.get(identity)
        usages = set((old.metadata or {}).get("usages", [])) if old else set()
        usages.add(usage)
        variable = Node(identity, "template_variable", expression, self.path, line=line,
                        summary="${" + expression + "}", scope=self.file_node.scope,
                        role=self.file_node.role, origin=self.file_node.origin,
                        build_membership=self.file_node.build_membership,
                        classification_evidence=self.file_node.classification_evidence,
                        metadata={"dialect": "thymeleaf", "expression": expression,
                                  "root": expression.split(".", 1)[0], "parser": VERSION,
                                  "usages": sorted(usages),
                                  **({"fragment": owner_id} if is_fragment else {})})
        self.facts.variables[identity] = variable
        return variable

    def _condition(self, attribute: str, value: str, line: int) -> None:
        owner_id, owner = self._owner()
        values = _expressions(value)
        if len(values) != 1 or not values[0][1] or not _PATH_EXPR.fullmatch(values[0][0]):
            status = "UNKNOWN"
            expression = value.strip()
            self._diagnostic("TEMPLATE_EXPRESSION_UNSUPPORTED",
                             "Conditional expression is recorded but never evaluated.", line,
                             expression=expression)
            root = None
        else:
            status = "PARTIAL"
            expression = values[0][0]
            root = expression.split(".", 1)[0]
        identity = _node_id("template_condition", self.path,
                            f"{owner.name}:{owner.line or 1}:{attribute}:{line}")
        node = Node(identity, "template_condition", attribute, self.path, line=line,
                    summary="Conditional template expression: " + expression,
                    scope=self.file_node.scope, role=self.file_node.role,
                    origin=self.file_node.origin,
                    build_membership=self.file_node.build_membership,
                    classification_evidence=self.file_node.classification_evidence,
                    metadata={"dialect": "thymeleaf", "attribute": attribute,
                              "expression": expression, "root": root, "status": status,
                              "reason": "Condition is retained as PARTIAL; no template expression is evaluated.",
                              "parser": VERSION, **({"fragment": owner_id} if owner.kind == "template_fragment" else {})})
        self.facts.conditions[identity] = node
        if status == "PARTIAL":
            self._variable(expression, line, "condition")

    def _attribute_expressions(self, name: str, value: str, line: int) -> None:
        unsupported_markers = [marker for marker in ("#{", "*{", "@{", "~{") if marker in value]
        if unsupported_markers:
            self._diagnostic("TEMPLATE_EXPRESSION_UNSUPPORTED",
                             "This Thymeleaf selector form is outside the supported literal property-path subset.",
                             line, expression=value.strip())
        for expression, balanced in _expressions(value):
            if balanced:
                self._variable(expression, line, "output")
            else:
                self._diagnostic("TEMPLATE_EXPRESSION_UNSUPPORTED",
                                 "Unclosed or nested expression is retained as UNKNOWN.", line,
                                 expression=expression)

    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        attr_counts = Counter(name for name, _ in attrs if name)
        values: dict[str, str] = {}
        for name, value in attrs:
            if name:
                values[name] = value or ""
        parent_fragment, _ = self._owner()
        current_fragment = parent_fragment if self.fragments_by_id.get(parent_fragment) else None

        declarations = [(name, value) for name, value in attrs if name in {"th:fragment", "data-th-fragment"}]
        if len(declarations) > 1 or any(attr_counts.get(name, 0) != 1 for name, _ in declarations):
            self._diagnostic("TEMPLATE_FRAGMENT_DECLARATION_AMBIGUOUS",
                             "Multiple fragment declarations on one element are unsupported.", line)
        elif declarations:
            declaration = _parse_fragment_declaration(declarations[0][1] or "")
            if declaration is None:
                self._diagnostic("TEMPLATE_FRAGMENT_DECLARATION_UNSUPPORTED",
                                 "Fragment declaration must use a static name and unique identifier parameters.", line,
                                 expression=declarations[0][1] or "")
            else:
                name, parameters = declaration
                identity = _node_id("template_fragment", self.path, f"{name}:{line}")
                node = Node(identity, "template_fragment", name, self.path, line=line,
                            summary=f"Thymeleaf fragment {name}", scope=self.file_node.scope,
                            role=self.file_node.role, origin=self.file_node.origin,
                            build_membership=self.file_node.build_membership,
                            classification_evidence=self.file_node.classification_evidence,
                            metadata={"dialect": "thymeleaf", "fragment": name,
                                      "parameters": list(parameters), "parser": VERSION})
                fragment = _Fragment(node, name, parameters)
                self.facts.fragments.append(fragment)
                self.fragments_by_id[identity] = fragment
                current_fragment = identity
                for parameter in parameters:
                    parameter_node = Node(
                        _node_id("template_variable", self.path,
                                 f"fragment:{name}:{line}:parameter:{parameter}"),
                        "template_variable", parameter, self.path, line=line,
                        summary=f"Fragment parameter {parameter}", scope=self.file_node.scope,
                        role=self.file_node.role, origin=self.file_node.origin,
                        build_membership=self.file_node.build_membership,
                        classification_evidence=self.file_node.classification_evidence,
                        metadata={"dialect": "thymeleaf", "expression": parameter,
                                  "root": parameter, "fragment": identity,
                                  "fragment_parameter": parameter, "usages": ["parameter"],
                                  "parser": VERSION})
                    fragment.parameter_nodes[parameter] = parameter_node
                    self.facts.variables[parameter_node.id] = parameter_node

        for name, value in attrs:
            if not name:
                continue
            if name in {"th:fragment", "data-th-fragment"}:
                continue
            if name in _REFERENCE_ATTRIBUTES:
                parsed = _parse_fragment_reference(value or "")
                if parsed is None:
                    self._diagnostic("TEMPLATE_FRAGMENT_UNRESOLVED",
                                     "Fragment reference is dynamic or outside the supported literal grammar.",
                                     line, expression=value or "")
                else:
                    target, fragment_name, arguments = parsed
                    self.facts.references.append((current_fragment or self.facts.template.id,
                                                  target, [fragment_name, *arguments], line))
                    for argument in arguments:
                        match = re.fullmatch(rf"({_IDENT})\s*=\s*\$\{{({_IDENT}(?:\.{_IDENT})*)\}}", argument)
                        positional = re.fullmatch(rf"\$\{{({_IDENT}(?:\.{_IDENT})*)\}}", argument)
                        if match:
                            self._variable(match.group(2), line, "fragment_argument")
                        elif positional:
                            self._variable(positional.group(1), line, "fragment_argument")
                continue
            if attr_counts.get(name, 0) > 1:
                self._diagnostic("TEMPLATE_ATTRIBUTE_AMBIGUOUS",
                                 "Duplicate attribute values are not resolved.", line,
                                 expression=value or "")
                continue
            if name in _CONDITION_ATTRIBUTES:
                self._condition(name, value or "", line)
                continue
            if any(marker in (value or "") for marker in ("${", "#{", "*{", "@{", "~{")):
                self._attribute_expressions(name, value or "", line)

        if tag not in _VOID_TAGS:
            self.stack.append((tag, current_fragment))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        line = self.getpos()[0]
        if any(marker in data for marker in ("#{", "*{", "@{", "~{")):
            self._diagnostic("TEMPLATE_EXPRESSION_UNSUPPORTED",
                             "This Thymeleaf selector form is outside the supported literal property-path subset.",
                             line, expression=data.strip())
        for expression, balanced in _expressions(data):
            if balanced:
                self._variable(expression, line, "output")
            else:
                self._diagnostic("TEMPLATE_EXPRESSION_UNSUPPORTED",
                                 "Unclosed or nested expression is retained as UNKNOWN.", line,
                                 expression=expression)


def attach_templates(root: Path, graph: KnowledgeGraph) -> KnowledgeGraph:
    """Attach bounded Thymeleaf variables, fragments and literal bindings."""
    root = root.resolve()
    file_nodes = {node.path: node for node in graph.nodes if node.kind == "file"}
    contexts = {context.get("scope"): context.get("id") for context in graph.contexts
                if context.get("mode") == "SOURCE_ONLY"}
    nodes = {node.id: node for node in graph.nodes}
    edges = set(graph.edges)
    evidence = {item["id"]: item for item in graph.evidence}
    facts_by_path: dict[str, _TemplateFacts] = {}
    pending_edges: list[tuple[str, str, str, str, str, int]] = []
    diagnostics = list(graph.diagnostics)

    for relative, file_node in sorted(file_nodes.items()):
        if Path(relative).suffix.lower() != ".html" or "templates" not in Path(relative).parts:
            continue
        try:
            text = (root / relative).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            diagnostics.append({"code": "TEMPLATE_READ_UNAVAILABLE", "path": relative,
                                "reason": str(error), "status": "UNKNOWN"})
            continue
        template_id = _node_id("template", relative, Path(relative).stem)
        template = Node(template_id, "template", Path(relative).stem, relative, line=1,
                        scope=file_node.scope, role=file_node.role, origin=file_node.origin,
                        build_membership=file_node.build_membership,
                        classification_evidence=file_node.classification_evidence,
                        metadata={"dialect": "thymeleaf", "parser": VERSION})
        facts = _TemplateFacts(template)
        parser = _TemplateParser(relative, text, file_node, facts)
        try:
            parser.feed(text)
            parser.close()
        except (ValueError, AssertionError) as error:
            facts.diagnostics.append({"code": "TEMPLATE_PARSE_UNKNOWN", "path": relative,
                                      "reason": str(error), "status": "UNKNOWN"})
        facts_by_path[relative] = facts
        nodes[template_id] = template
        pending_edges.append((file_node.id, template_id, "defines_template", "Thymeleaf template", relative, 1))
        for fragment in facts.fragments:
            nodes[fragment.node.id] = fragment.node
            pending_edges.append((template_id, fragment.node.id, "declares_template_fragment",
                                  "Static Thymeleaf fragment declaration", relative,
                                  fragment.node.line or 1))
            for parameter_node in fragment.parameter_nodes.values():
                nodes[parameter_node.id] = parameter_node
                pending_edges.append((fragment.node.id, parameter_node.id, "declares_fragment_parameter",
                                      "Static fragment parameter", relative,
                                      parameter_node.line or 1))
        for variable in facts.variables.values():
            nodes[variable.id] = variable
            owner_id = (variable.metadata or {}).get("fragment", template_id)
            relation = "declares_template_variable"
            pending_edges.append((owner_id, variable.id, relation, variable.summary or "Template variable",
                                  relative, variable.line or 1))
            if owner_id != template_id:
                fragment = next((item for item in facts.fragments if item.node.id == owner_id), None)
                root_name = (variable.metadata or {}).get("root")
                parameter = fragment.parameter_nodes.get(root_name) if fragment else None
                if parameter and parameter.id != variable.id:
                    pending_edges.append((parameter.id, variable.id, "uses_fragment_parameter",
                                          f"Fragment parameter {root_name} used by a literal property path",
                                          relative, variable.line or 1))
        for condition in facts.conditions.values():
            nodes[condition.id] = condition
            owner_id = (condition.metadata or {}).get("fragment", template_id)
            pending_edges.append((owner_id, condition.id, "has_template_condition",
                                  condition.summary or "Conditional template expression",
                                  relative, condition.line or 1))
        diagnostics.extend(facts.diagnostics)

    fragment_index: dict[tuple[str, str], list[tuple[_TemplateFacts, _Fragment]]] = {}
    for relative, facts in facts_by_path.items():
        for fragment in facts.fragments:
            fragment_index.setdefault((relative, fragment.name), []).append((facts, fragment))

    for relative, facts in facts_by_path.items():
        template_root = _template_root(relative)
        file_node = file_nodes[relative]
        for owner_id, raw_target, call_parts, line in facts.references:
            fragment_name, *raw_arguments = call_parts
            if not raw_target:
                target_path = relative
            else:
                if (raw_target.startswith("/") or "\\" in raw_target or
                        any(part == ".." for part in PurePosixPath(raw_target).parts) or
                        not re.fullmatch(r"[A-Za-z0-9_./-]+", raw_target)):
                    diagnostics.append({"code": "TEMPLATE_FRAGMENT_UNRESOLVED", "path": relative,
                                        "source_line": line, "expression": raw_target,
                                        "reason": "Fragment target path is not a safe static path.",
                                        "status": "UNKNOWN"})
                    continue
                target = PurePosixPath(raw_target)
                if target.suffix == "":
                    target = target.with_suffix(".html")
                target_path = (PurePosixPath(template_root) / target).as_posix()
            candidates = [(target_facts, fragment) for target_facts, fragment
                          in fragment_index.get((target_path, fragment_name), [])
                          if fragment.node.scope == nodes[owner_id].scope]
            if len(candidates) != 1:
                code = "TEMPLATE_FRAGMENT_AMBIGUOUS" if candidates else "TEMPLATE_FRAGMENT_UNRESOLVED"
                diagnostics.append({"code": code, "path": relative, "source_line": line,
                                    "expression": raw_target + " :: " + fragment_name,
                                    "reason": "Fragment target is not unique within the source scope.",
                                    "status": "UNKNOWN"})
                continue
            target_facts, fragment = candidates[0]
            arguments = _split_arguments(",".join(raw_arguments)) if raw_arguments else []
            if arguments is None:
                diagnostics.append({"code": "TEMPLATE_FRAGMENT_ARGUMENT_UNSUPPORTED", "path": relative,
                                    "source_line": line, "expression": fragment_name,
                                    "reason": "Fragment arguments must be a comma-separated literal list.",
                                    "status": "UNKNOWN"})
                continue
            if len(arguments) != len(fragment.parameters):
                diagnostics.append({"code": "TEMPLATE_FRAGMENT_ARITY_MISMATCH", "path": relative,
                                    "source_line": line, "expression": fragment_name,
                                    "reason": f"Expected {len(fragment.parameters)} literal arguments; found {len(arguments)}.",
                                    "status": "UNKNOWN"})
                continue
            pending_edges.append((owner_id, fragment.node.id, "includes_template_fragment",
                                  "Static unique same-scope Thymeleaf fragment reference",
                                  relative, line))
            named_arguments: dict[str, str] = {}
            positional: list[str] = []
            invalid_named = False
            for argument in arguments:
                match = re.fullmatch(rf"({_IDENT})\s*=\s*(.*)", argument)
                if match:
                    key = match.group(1)
                    if key in named_arguments:
                        invalid_named = True
                        break
                    named_arguments[key] = match.group(2).strip()
                else:
                    positional.append(argument)
            if named_arguments and positional:
                invalid_named = True
            if named_arguments and (set(named_arguments) != set(fragment.parameters) or
                                    len(named_arguments) != len(fragment.parameters)):
                invalid_named = True
            if invalid_named:
                diagnostics.append({"code": "TEMPLATE_FRAGMENT_ARGUMENT_UNSUPPORTED", "path": relative,
                                    "source_line": line, "expression": fragment_name,
                                    "reason": "Named fragment arguments must uniquely name every declared parameter.",
                                    "status": "UNKNOWN"})
                # Keep only the statically proven include; no argument bindings.
                continue
            argument_values = ([named_arguments[name] for name in fragment.parameters]
                               if named_arguments else positional)
            for parameter, raw_value in zip(fragment.parameters, argument_values):
                expression = re.fullmatch(rf"\$\{{({_IDENT}(?:\.{_IDENT})*)\}}", raw_value)
                if not expression:
                    diagnostics.append({"code": "TEMPLATE_FRAGMENT_ARGUMENT_PARTIAL", "path": relative,
                                        "source_line": line, "expression": raw_value,
                                        "reason": "Static include is known, but this argument is not a literal model path.",
                                        "status": "PARTIAL"})
                    continue
                # Add the caller-side model path as an evidence-backed variable
                # so existing literal backend model-key bindings can reach it.
                caller_variable_id = _node_id("template_variable", relative, expression.group(1))
                caller_variable = facts.variables.get(caller_variable_id)
                if caller_variable is None:
                    caller_variable = Node(caller_variable_id, "template_variable", expression.group(1),
                                           relative, line=line, summary="${" + expression.group(1) + "}",
                                           scope=file_node.scope, role=file_node.role, origin=file_node.origin,
                                           build_membership=file_node.build_membership,
                                           classification_evidence=file_node.classification_evidence,
                                           metadata={"dialect": "thymeleaf", "expression": expression.group(1),
                                                     "root": expression.group(1).split(".", 1)[0],
                                                     "usages": ["fragment_argument"], "parser": VERSION})
                    facts.variables[caller_variable_id] = caller_variable
                    nodes[caller_variable_id] = caller_variable
                    pending_edges.append((facts.template.id, caller_variable_id, "declares_template_variable",
                                          "Literal fragment argument model path", relative, line))
                else:
                    metadata = dict(caller_variable.metadata or {})
                    metadata["usages"] = sorted(set(metadata.get("usages", [])) | {"fragment_argument"})
                    caller_variable = replace(caller_variable, metadata=metadata)
                    facts.variables[caller_variable_id] = caller_variable
                    nodes[caller_variable_id] = caller_variable
                parameter_node = fragment.parameter_nodes[parameter]
                pending_edges.append((owner_id, parameter_node.id, "passes_template_fragment_argument",
                                      "Literal model path ${" + expression.group(1) + "} supplied for " + parameter,
                                      relative, line))

    for relative, file_node in sorted(file_nodes.items()):
        if Path(relative).suffix.lower() not in {".java", ".kt", ".kts"}:
            continue
        try:
            text = (root / relative).read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        symbols = sorted((node for node in graph.nodes if node.path == relative
                          and node.kind in {"function", "method"} and node.line), key=lambda n: n.line or 0)
        lines = text.splitlines(keepends=True)
        offsets = [0]
        for value in lines:
            offsets.append(offsets[-1] + len(value))
        for index, symbol in enumerate(symbols):
            start_line = symbol.line or 1
            end_line = (symbols[index + 1].line or len(lines) + 1) - 1 if index + 1 < len(symbols) else len(lines)
            body = text[offsets[start_line - 1]:offsets[end_line]]
            returns = {match.group(1) for match in _VIEW_RETURN.finditer(body)}
            bindings = [(match.group(1), start_line - 1 + _line(body, match.start()))
                        for match in _MODEL_BINDING.finditer(body)]
            for template_name in returns:
                candidates = {facts.template.id: facts for facts in facts_by_path.values()
                              if facts.template.scope == file_node.scope and
                              (Path(facts.template.path).with_suffix("").name == template_name or
                               str(Path(facts.template.path).with_suffix("")).split("templates/", 1)[-1] == template_name)}
                if len(candidates) != 1:
                    if candidates:
                        diagnostics.append({"code": "TEMPLATE_VIEW_AMBIGUOUS", "path": relative,
                                            "source_line": start_line,
                                            "reason": "Literal view name matches multiple templates in the source scope.",
                                            "status": "UNKNOWN"})
                    continue
                facts = next(iter(candidates.values()))
                template = facts.template
                pending_edges.append((symbol.id, template.id, "renders_template", f"return {template_name}",
                                      relative, start_line))
                for key, line in bindings:
                    for variable in facts.variables.values():
                        metadata = variable.metadata or {}
                        # Fragment-local identifiers never bind directly from a
                        # controller; values cross only through a proven call arg.
                        if metadata.get("fragment") or metadata.get("fragment_parameter"):
                            continue
                        if metadata.get("root") == key and set(metadata.get("usages", [])) & {"output", "fragment_argument"}:
                            pending_edges.append((symbol.id, variable.id, "binds_template_variable",
                                                  f"literal model key {key}", relative, line))
            for match in _PDF_CALL.finditer(body):
                template_name = match.group(1)
                candidates = [facts.template for facts in facts_by_path.values()
                              if facts.template.scope == file_node.scope and
                              (Path(facts.template.path).with_suffix("").name == template_name or
                               str(Path(facts.template.path).with_suffix("")).split("templates/", 1)[-1] == template_name)]
                if len(candidates) != 1:
                    continue
                boundary_id = "external_service:pdf-renderer"
                nodes.setdefault(boundary_id, Node(boundary_id, "external_service", "PDF renderer", relative,
                                                    line=start_line, scope=file_node.scope,
                                                    role="resource", origin=file_node.origin,
                                                    metadata={"boundary": "external", "parser": VERSION}))
                line = start_line - 1 + _line(body, match.start())
                pending_edges.append((symbol.id, boundary_id, "calls_pdf_service", "literal PDF renderer call",
                                      relative, line))
                pending_edges.append((candidates[0].id, boundary_id, "rendered_by",
                                      "explicit PDF template argument", relative, line))

    for source_id, target_id, kind, note, source_file, source_line in pending_edges:
        source = nodes.get(source_id)
        context_id = contexts.get(source.scope) if source else None
        record = {"kind": "SYNTAX_CANDIDATE", "extractor": VERSION,
                  "source_file": source_file, "source_line": source_line,
                  "sha256": graph.files.get(source_file), "source": source_id,
                  "target": target_id, "relation": kind, "note": note,
                  "context_ids": [context_id] if context_id else [],
                  "origin_trust": "LOCAL_SOURCE", "freshness": "CONTENT_VERIFIED"}
        evidence_id = "evidence:" + digest(record)
        evidence[evidence_id] = {"id": evidence_id, **record}
        edges.add(Edge(source_id, target_id, kind, note,
                       evidence_kind="SYNTAX_CANDIDATE",
                       context_ids=(context_id,) if context_id else (),
                       evidence_ids=(evidence_id,)))

    result = replace(graph,
                     nodes=sorted(nodes.values(), key=lambda n: (n.path, n.line or 0, n.kind, n.name)),
                     edges=sorted(edges, key=lambda e: (e.source, e.kind, e.target)),
                     evidence=[evidence[key] for key in sorted(evidence)],
                     diagnostics=diagnostics)
    KnowledgeGraph.from_dict(result.to_dict())
    return result
