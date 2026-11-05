"""Pure compatibility regression: JVM Spring rules must not fork TS contexts."""
import json
from pathlib import Path

import pytest

from kgmaker.inspection import context
from kgmaker.model import KnowledgeGraph


@pytest.mark.parametrize("variant", ["ordinary", "react"])
def test_spring_rule_bump_preserves_exact_typescript_context_with_return_extension(tmp_path, variant):
    baseline = json.loads((Path(__file__).resolve().parents[1] /
                          "fixtures/spring-imports/typescript-contexts-return-v1.json").read_text())[variant]
    graph = KnowledgeGraph(3, str(tmp_path), "", [], [], {})
    metadata = {"protocol_version": 1, "worker": "typescript-worker-1",
                "compiler_version": "typescript-5.7.3", "distribution": []}
    build_context = {"ui_framework": "react", "framework_rule_versions": {"react": "react18-intrinsic-events-1"}} if variant == "react" else None
    actual = context(tmp_path, graph, "typescript", metadata, repo_id="local", module="root",
                     source_set="main", scope="production", build_context=build_context)
    assert actual == baseline
