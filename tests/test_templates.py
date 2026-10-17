"""T001 template-to-backend and external PDF boundary fixtures."""
from kgmaker import feature
from kgmaker.analysis_model import INPUT_METADATA
from kgmaker.data_check import data_check


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
