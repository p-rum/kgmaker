"""T001 template-to-backend and external PDF boundary fixtures."""
from kgmaker import feature
from kgmaker.analysis_model import INPUT_METADATA
from kgmaker.data_check import data_check
from kgmaker.scanner import scan_repository
from kgmaker.templates import attach_templates


def fixture(root):
    source = root / "src/main/java/example/ReportController.java"
    source.parent.mkdir(parents=True)
    source.write_text(
        """class ReportController {
  String report(Model model) {
    model.addAttribute("account", account);
    return "report";
  }
  byte[] pdf() {
    return pdfService.render("report", account);
  }
}
"""
    )
    template = root / "src/main/resources/templates/report.html"
    template.parent.mkdir(parents=True)
    template.write_text(
        """<html xmlns:th="http://www.thymeleaf.org">
<body><span th:text="${account.balance}">0</span></body>
</html>
"""
    )
    return source, template


def test_thymeleaf_literal_binding_and_pdf_boundary(tmp_path):
    fixture(tmp_path)
    graph = feature.current_graph(tmp_path)[0]
    variable = next(node for node in graph.nodes
                    if node.kind == "template_variable" and node.name == "account.balance")
    template = next(node for node in graph.nodes if node.kind == "template" and node.name == "report")
    method = next(node for node in graph.nodes if node.kind == "function" and node.name == "report")
    assert any(edge.source == method.id and edge.target == template.id and edge.kind == "renders_template"
               for edge in graph.edges)
    assert any(edge.source == method.id and edge.target == variable.id and edge.kind == "binds_template_variable"
               for edge in graph.edges)
    assert any(node.id == "external_service:pdf-renderer" for node in graph.nodes)
    assert any(edge.source == template.id and edge.target == "external_service:pdf-renderer"
               and edge.kind == "rendered_by" for edge in graph.edges)


def test_template_variable_is_exact_line_evidence_for_data_check(tmp_path):
    fixture(tmp_path)
    (tmp_path / "requirement.md").write_text("Render account balance.")
    packet = feature.prepare(tmp_path, "requirement.md", "template", 100_000)
    variable = "template_variable:src/main/resources/templates/report.html:account.balance"
    requirement = "analysis:template:requirement:balance"
    spec = {
        "schema_version": 1, "analysis_id": "template", "requirement_hash": packet["requirement_hash"],
        "requirements": [{"id": requirement, "text": "Render account balance",
                          "kind": "OutputRequirement", "source_quote": "account balance"}],
        "inputs": [{"id": "analysis:template:input:balance", "name": "account balance",
                    "requirement_ids": [requirement], "candidate_entity_ids": [variable],
                    **{key: None for key in INPUT_METADATA}}],
    }
    result = data_check(tmp_path, "template", spec)
    assert result["valid"]
    evidence = next(item for item in result["candidate"]["evidence"]
                    if item.get("source_id") == variable)
    assert evidence["location"] == {"type": "lines", "start": 2, "end": 2}
    assert "${account.balance}" in evidence["quote"]
    assert feature.validate(tmp_path, "template", result["candidate"])["valid"]


def test_static_fragment_arguments_bind_scoped_fragment_parameters_without_collisions(tmp_path):
    source = tmp_path / "src/main/java/example/ReportController.java"
    source.parent.mkdir(parents=True)
    source.write_text('''class ReportController {
  String report(Model model) {
    model.addAttribute("order", order);
    return "index";
  }
}
''')
    templates = tmp_path / "src/main/resources/templates"
    (templates / "fragments").mkdir(parents=True)
    (templates / "index.html").write_text('''<html xmlns:th="http://www.thymeleaf.org">
<body><section th:replace="~{fragments/card :: card(account=${order.customer})}"></section></body>
</html>
''')
    (templates / "fragments/card.html").write_text('''<div xmlns:th="http://www.thymeleaf.org" th:fragment="card(account)"
     th:if="${account.enabled}" th:text="${account.title}">
<span th:text="${account.balance}">0</span>
</div>
<div th:fragment="row(account)" th:text="${account.title}"></div>
''')

    graph = feature.current_graph(tmp_path)[0]
    card = next(n for n in graph.nodes if n.kind == "template_fragment" and n.name == "card")
    scoped = next(n for n in graph.nodes if n.kind == "template_variable" and
                  n.path.endswith("fragments/card.html") and n.name == "account.balance")
    same_element = next(n for n in graph.nodes if n.kind == "template_variable" and
                        n.path.endswith("fragments/card.html") and n.name == "account.title" and
                        n.metadata and n.metadata.get("fragment") == card.id)
    row = next(n for n in graph.nodes if n.kind == "template_fragment" and n.name == "row")
    row_expression = next(n for n in graph.nodes if n.kind == "template_variable" and
                          n.path.endswith("fragments/card.html") and n.name == "account.title" and
                          n.metadata and n.metadata.get("fragment") == row.id)
    account_parameter = next(n for n in graph.nodes if n.kind == "template_variable" and
                             n.path.endswith("fragments/card.html") and n.metadata and
                             n.metadata.get("fragment_parameter") == "account" and
                             n.metadata.get("fragment") == card.id)
    report = next(n for n in graph.nodes if n.kind == "function" and n.name == "report")
    parent = next(n for n in graph.nodes if n.kind == "template" and n.name == "index")
    assert scoped.metadata["fragment"] == card.id
    assert any(e.source == parent.id and e.target == card.id and e.kind == "includes_template_fragment"
               for e in graph.edges)
    caller_variable = next(n for n in graph.nodes if n.kind == "template_variable" and
                           n.path.endswith("templates/index.html") and n.name == "order.customer")
    assert any(e.source == caller_variable.id and e.target == account_parameter.id and
               e.kind == "passes_template_fragment_argument" for e in graph.edges)
    assert any(e.source == account_parameter.id and e.target == same_element.id and
               e.kind == "uses_fragment_parameter" for e in graph.edges)
    assert any(e.source == account_parameter.id and e.target == scoped.id and
               e.kind == "uses_fragment_parameter" for e in graph.edges)
    assert same_element.id != row_expression.id
    assert same_element.metadata["fragment"] == card.id
    assert row_expression.metadata["fragment"] == row.id
    assert not any(n.path.endswith("fragments/card.html") and n.name == "account.title" and
                   not (n.metadata or {}).get("fragment") for n in graph.nodes)
    assert any(n.kind == "template_condition" and (n.metadata or {}).get("fragment") == card.id
               for n in graph.nodes)
    fragment_edges = [e for e in graph.edges if e.kind in {
        "includes_template_fragment", "passes_template_fragment_argument", "uses_fragment_parameter"}]
    assert fragment_edges and all(e.evidence_kind == "SYNTAX_CANDIDATE" and e.context_ids
                                  for e in fragment_edges)
    assert any(e.source == report.id and e.target == "template_variable:src/main/resources/templates/index.html:order.customer" and
               e.kind == "binds_template_variable" for e in graph.edges)
    assert not any(e.source == report.id and e.target == scoped.id and e.kind == "binds_template_variable"
                   for e in graph.edges)


def test_nested_fragment_arguments_follow_exact_scoped_variables(tmp_path):
    source = tmp_path / "src/main/java/example/ReportController.java"
    source.parent.mkdir(parents=True)
    source.write_text('''class ReportController {
  String report(Model model) {
    model.addAttribute("order", order);
    return "index";
  }
}
''')
    templates = tmp_path / "src/main/resources/templates"
    (templates / "fragments").mkdir(parents=True)
    (templates / "index.html").write_text('''<section th:replace="~{fragments/card :: card(item=${order})}"></section>
''')
    (templates / "fragments/card.html").write_text('''<div th:fragment="card(item)">
  <section th:replace="~{:: row(item=${item.customer})}"></section>
</div>
<span th:fragment="row(item)" th:text="${item.name}"></span>
''')

    graph = feature.current_graph(tmp_path)[0]
    card = next(n for n in graph.nodes if n.kind == "template_fragment" and n.name == "card")
    row = next(n for n in graph.nodes if n.kind == "template_fragment" and n.name == "row")
    card_parameter = next(n for n in graph.nodes if n.kind == "template_variable" and n.metadata and
                          n.metadata.get("fragment_parameter") == "item" and n.metadata.get("fragment") == card.id)
    row_parameter = next(n for n in graph.nodes if n.kind == "template_variable" and n.metadata and
                         n.metadata.get("fragment_parameter") == "item" and n.metadata.get("fragment") == row.id)
    nested_argument = next(n for n in graph.nodes if n.kind == "template_variable" and n.name == "item.customer")
    row_value = next(n for n in graph.nodes if n.kind == "template_variable" and n.name == "item.name")
    report = next(n for n in graph.nodes if n.kind == "function" and n.name == "report")
    root_argument = next(n for n in graph.nodes if n.kind == "template_variable" and n.name == "order")

    assert nested_argument.metadata["fragment"] == card.id
    assert row_value.metadata["fragment"] == row.id
    assert any(e.source == report.id and e.target == root_argument.id and e.kind == "binds_template_variable"
               for e in graph.edges)
    assert any(e.source == root_argument.id and e.target == card_parameter.id and
               e.kind == "passes_template_fragment_argument" for e in graph.edges)
    assert any(e.source == card_parameter.id and e.target == nested_argument.id and
               e.kind == "uses_fragment_parameter" for e in graph.edges)
    assert any(e.source == nested_argument.id and e.target == row_parameter.id and
               e.kind == "passes_template_fragment_argument" for e in graph.edges)
    assert any(e.source == row_parameter.id and e.target == row_value.id and
               e.kind == "uses_fragment_parameter" for e in graph.edges)
    assert not any(n.path.endswith("fragments/card.html") and n.name in {"item.customer", "item.name"}
                   and not (n.metadata or {}).get("fragment") for n in graph.nodes)


def test_loop_and_local_alias_scopes_do_not_bind_model_variables(tmp_path):
    source = tmp_path / "src/main/java/example/PageController.java"
    source.parent.mkdir(parents=True)
    source.write_text('''class PageController {
  String page(Model model) {
    model.addAttribute("item", item);
    return "page";
  }
}
''')
    templates = tmp_path / "src/main/resources/templates"
    templates.mkdir(parents=True)
    (templates / "page.html").write_text('''<span th:text="${item.outside}"></span>
<div th:each="item : ${orders}" th:if="${item.visible}">
  <span th:text="${item.total}"></span>
  <section th:replace="~{:: row(item=${item})}"></section>
</div>
<div data-th-with="item=${other}"><span th:text="${item.local}"></span></div>
<div data-th-each="item : ${rows}"><span th:text="${item.rowValue}"></span></div>
<i th:fragment="row(item)" th:text="${item.name}"></i>
''')

    graph = feature.current_graph(tmp_path)[0]
    page = next(n for n in graph.nodes if n.kind == "template" and n.name == "page")
    outside = next(n for n in graph.nodes if n.kind == "template_variable" and n.name == "item.outside")
    controller = next(n for n in graph.nodes if n.kind == "function" and n.name == "page")
    assert any(e.source == controller.id and e.target == outside.id and e.kind == "binds_template_variable"
               for e in graph.edges)
    assert not any(n.kind == "template_variable" and n.name in {
        "item.total", "item.local", "item.rowValue"} for n in graph.nodes)
    assert not any(e.kind in {"includes_template_fragment", "passes_template_fragment_argument"}
                   and e.source == page.id for e in graph.edges)
    diagnostics = [d for d in graph.diagnostics if d["code"] == "TEMPLATE_VARIABLE_SCOPE_UNSUPPORTED"]
    assert len(diagnostics) >= 4
    assert all(d["status"] == "UNKNOWN" for d in diagnostics)
    loop_condition = next(n for n in graph.nodes if n.kind == "template_condition" and
                          n.metadata and n.metadata.get("expression") == "${item.visible}")
    assert loop_condition.metadata["status"] == "UNKNOWN"


def test_conditional_and_unsupported_expressions_remain_partial_unknown(tmp_path):
    templates = tmp_path / "src/main/resources/templates"
    templates.mkdir(parents=True)
    (templates / "conditional.html").write_text('''<div xmlns:th="http://www.thymeleaf.org"
  th:if="${account.enabled}" th:text="${account.name}">name</div>
<span th:if="${account.enabled and account.ready}">dynamic</span>
<i th:if="true">literal-condition-not-evaluated</i>
<b th:text="#{messages.title}">message</b>
''')

    graph = feature.current_graph(tmp_path)[0]
    conditions = [n for n in graph.nodes if n.kind == "template_condition"]
    assert len(conditions) == 3
    simple = next(n for n in conditions if n.metadata["expression"] == "account.enabled")
    unsupported = next(n for n in conditions if n.metadata["status"] == "UNKNOWN")
    assert simple.metadata["status"] == "PARTIAL"
    assert "no template expression is evaluated" in simple.metadata["reason"]
    assert "and" in unsupported.metadata["expression"]
    literal = next(n for n in conditions if n.metadata["expression"] == "true")
    assert literal.metadata["status"] == "UNKNOWN"
    assert any(d["code"] == "TEMPLATE_EXPRESSION_UNSUPPORTED" and "#{messages.title}" in d.get("expression", "")
               for d in graph.diagnostics)
    assert not any(e.kind == "evaluates_template_condition" for e in graph.edges)


def test_duplicate_reference_attributes_and_aliases_are_ambiguous_without_edges(tmp_path):
    templates = tmp_path / "src/main/resources/templates"
    templates.mkdir(parents=True)
    (templates / "index.html").write_text('''<section th:replace="~{:: card(item=${first})}"
         th:replace="~{:: card(item=${second})}"></section>
<div th:replace="~{:: card(item=${first})}"
     data-th-replace="~{:: card(item=${second})}"></div>
<i th:fragment="card(item)"></i>
''')

    graph = feature.current_graph(tmp_path)[0]
    assert not any(edge.kind == "includes_template_fragment" for edge in graph.edges)
    assert not any(edge.kind == "passes_template_fragment_argument" for edge in graph.edges)
    assert sum(item["code"] == "TEMPLATE_FRAGMENT_REFERENCE_AMBIGUOUS"
               for item in graph.diagnostics) == 2


def test_dynamic_ambiguous_and_wrong_arity_fragments_have_diagnostics_and_no_edges(tmp_path):
    templates = tmp_path / "src/main/resources/templates"
    templates.mkdir(parents=True)
    (templates / "index.html").write_text('''<div xmlns:th="http://www.thymeleaf.org">
<span th:replace="~{${dynamicTarget} :: card(account=${user})}"></span>
<span th:replace="~{:: card}"></span>
<span th:replace="~{:: pair(account=${user})}"></span>
</div>
<i th:fragment="card(user)"></i>
<b th:fragment="card(user)"></b>
<section th:fragment="pair(left,right)"></section>
''')
    before = scan_repository(tmp_path)
    snapshot = before.to_dict()
    graph = attach_templates(tmp_path, before)

    assert before.to_dict() == snapshot
    assert not any(edge.kind == "includes_template_fragment" for edge in graph.edges)
    codes = {item["code"] for item in graph.diagnostics}
    assert "TEMPLATE_FRAGMENT_UNRESOLVED" in codes
    assert "TEMPLATE_FRAGMENT_AMBIGUOUS" in codes
    assert "TEMPLATE_FRAGMENT_ARITY_MISMATCH" in codes
