"""T003-S09-W02: unsupported legacy spreadsheets never produce cell evidence."""
import copy
import hashlib
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from kgmaker import feature
from kgmaker.analysis_model import AnalysisError, INPUT_METADATA
from kgmaker.classification import Classifier
from kgmaker.data_check import data_check
from kgmaker.model import KnowledgeGraph
from kgmaker.store import save_graph, load_graph
from kgmaker.workbooks import extract, locate_cell

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/workbooks/legacy-biff2.xls"


@pytest.mark.parametrize("name", ["legacy.xls", "renamed.xlsx", "UPPER.XLSX"])
def test_real_biff2_fixture_is_unsupported_before_zip_parse_or_process(tmp_path, name):
    raw = FIXTURE.read_bytes()
    path = tmp_path / name
    path.write_bytes(raw)
    with patch("kgmaker.workbooks.zipfile.ZipFile", side_effect=AssertionError("XLSX parser")), \
            patch("subprocess.Popen", side_effect=AssertionError("implicit process")):
        graph = feature.current_graph(tmp_path)[0]
    diagnostic, = [d for d in graph.diagnostics if d["path"] == name]
    assert diagnostic["code"] == "BINARY_XLS_UNSUPPORTED"
    assert diagnostic["status"] == "UNSUPPORTED"
    assert diagnostic["detected_format"] == "BIFF"
    assert diagnostic["sha256"] == hashlib.sha256(raw).hexdigest()
    assert diagnostic["locator"] == {"type": "file", "path": name}
    assert graph.files[name] == diagnostic["sha256"]
    assert not [n for n in graph.nodes if n.kind.startswith("workbook")]
    assert not graph.evidence
    assert not [c for c in graph.contexts if c.get("mode") == "WORKBOOK_OFFLINE"]
    sources, _ = feature.source_inventory(tmp_path)
    assert sources[name]["kind"] == "WORKBOOK"
    assert sources[name]["supported"] is False


def test_compound_container_signature_does_not_claim_a_valid_excel_workbook(tmp_path):
    (tmp_path / "renamed.xlsx").write_bytes(bytes.fromhex("d0cf11e0a1b11ae1") + bytes(504))
    graph = feature.current_graph(tmp_path)[0]
    diagnostic, = graph.diagnostics
    assert diagnostic["status"] == "UNSUPPORTED"
    assert diagnostic["detected_format"] == "OLE_COMPOUND"
    assert "valid workbook" in diagnostic["reason"]
    assert not [n for n in graph.nodes if n.kind.startswith("workbook")]


@pytest.mark.parametrize("raw", [b"", b"not Excel", bytes.fromhex("d0cf11"), b"PK\x03\x04broken"])
def test_malformed_declared_xls_remains_unsupported_without_invented_cells(tmp_path, raw):
    path = tmp_path / "malformed.xls"
    path.write_bytes(raw)
    graph = feature.current_graph(tmp_path)[0]
    diagnostic, = graph.diagnostics
    assert diagnostic["status"] == "UNSUPPORTED"
    assert diagnostic["sha256"] == hashlib.sha256(raw).hexdigest()
    assert diagnostic["detected_format"] == "UNKNOWN"
    assert not [n for n in graph.nodes if n.kind.startswith("workbook")]
    with pytest.raises(AnalysisError, match="unsupported"):
        locate_cell(path, "Sheet1", "A1")


def test_direct_extractor_rejects_renamed_binary_and_does_not_touch_store(tmp_path):
    path = tmp_path / "renamed.xlsx"
    path.write_bytes(FIXTURE.read_bytes())
    store = tmp_path / ".kgmaker/graph.json"
    store.parent.mkdir()
    store.write_bytes(b"last valid generation")
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    with patch("kgmaker.workbooks.zipfile.ZipFile", side_effect=AssertionError("XLSX parser")), \
            patch("subprocess.Popen", side_effect=AssertionError("implicit process")):
        with pytest.raises(AnalysisError, match="unsupported"):
            extract(path, path.name, Classifier(tmp_path))
    assert {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before


def test_packet_and_audit_preserve_hash_bound_gap_without_confirming_missing_data(tmp_path):
    name = "renamed.xlsx"
    (tmp_path / name).write_bytes(FIXTURE.read_bytes())
    (tmp_path / "requirement.md").write_text("Use legacy amount.")
    graph = feature.current_graph(tmp_path)[0]
    save_graph(graph, tmp_path)
    before_store = (tmp_path / ".kgmaker/graph.json").read_bytes()
    packet = feature.prepare(tmp_path, "requirement.md", "legacy", 100_000)
    assert name in packet["coverage"]["unsupported_sources"]
    diagnostic, = packet["coverage"]["artifact_diagnostics"]
    assert diagnostic["status"] == "UNSUPPORTED"
    assert diagnostic["sha256"] == packet["source_manifest"][name]["sha256"]
    requirement_id = "analysis:legacy:requirement:amount"
    spec = {"schema_version": 1, "analysis_id": "legacy", "requirement_hash": packet["requirement_hash"],
            "requirements": [{"id": requirement_id, "text": "Use legacy amount", "kind": "InputRequirement",
                              "source_quote": "legacy amount"}],
            "inputs": [{"id": "analysis:legacy:input:amount", "name": "amount", "requirement_ids": [requirement_id],
                        **{key: None for key in INPUT_METADATA}}]}
    real_popen = subprocess.Popen
    def git_baseline_only(argv, *args, **kwargs):
        assert argv == ["git", "-C", str(tmp_path), "rev-parse", "HEAD"]
        return real_popen(argv, *args, **kwargs)
    with patch("subprocess.Popen", side_effect=git_baseline_only):
        result = data_check(tmp_path, "legacy", spec)
    assert result["valid"]
    assert result["candidate"]["input_requirements"][0]["availability"] == "UNKNOWN"
    assert not result["data_delivery_gaps"]
    assert not result["candidate_sources"]
    assert any(gap["kind"] == "ARTIFACT_DIAGNOSTICS" and diagnostic in gap["details"]
               for gap in result["coverage_gaps"])
    assert (tmp_path / ".kgmaker/graph.json").read_bytes() == before_store
    assert load_graph(tmp_path).diagnostics == graph.diagnostics
    for version in (1, 2, 3):
        payload = copy.deepcopy(graph.to_dict())
        payload["schema_version"] = version
        assert KnowledgeGraph.from_dict(payload).schema_version == version


def test_malformed_xlsx_diagnostic_is_hash_bound_and_has_no_values(tmp_path):
    (tmp_path / "broken.xlsx").write_bytes(b"not a ZIP")
    graph = feature.current_graph(tmp_path)[0]
    diagnostic, = graph.diagnostics
    assert diagnostic["code"] == "XLSX_PARSE_FAILED"
    assert diagnostic["status"] == "UNSUPPORTED"
    assert diagnostic["sha256"] == hashlib.sha256(b"not a ZIP").hexdigest()
    assert diagnostic["locator"] == {"type": "file", "path": "broken.xlsx"}
    assert not graph.evidence


def test_packet_gap_respects_scope_and_changes_in_binary_content_are_stale(tmp_path):
    for name in ("src/main/resources/legacy.xls", "src/test/resources/legacy.xls"):
        path = tmp_path / name
        path.parent.mkdir(parents=True)
        path.write_bytes(FIXTURE.read_bytes())
    (tmp_path / "requirement.md").write_text("Inspect legacy amounts.")
    packet = feature.prepare(tmp_path, "requirement.md", "production", 100_000, scope="production")
    diagnostic, = packet["coverage"]["artifact_diagnostics"]
    assert diagnostic["path"] == "src/main/resources/legacy.xls"
    assert diagnostic["scope"] == "production"
    (tmp_path / diagnostic["path"]).write_bytes(b"changed invalid workbook")
    assert feature.freshness(tmp_path, packet)


def test_workspace_preserves_repo_qualified_binary_gap_without_nodes(tmp_path):
    import json
    from kgmaker.workspace import snapshot_workspace
    coordinator = tmp_path / "coordinator"
    coordinator.mkdir()
    for repo in ("first", "second"):
        root = tmp_path / repo
        (root / "src").mkdir(parents=True)
        (root / "src/legacy.xlsx").write_bytes(FIXTURE.read_bytes() + (b"" if repo == "first" else b"different"))
    manifest = tmp_path / "workspace.json"
    manifest.write_text(json.dumps({"schema_version": 1, "workspace_id": "legacy",
                                    "repositories": [{"id": name, "path": name, "role": "shared"} for name in ("first", "second")]}))
    _, coverage, sources, graph, _ = snapshot_workspace(manifest)
    diagnostics = coverage["artifact_diagnostics"]
    assert len(diagnostics) == 2
    assert {item["repo_id"] for item in diagnostics} == {"first", "second"}
    for item in diagnostics:
        assert item["sha256"] == sources[f"@{item['repo_id']}/{item['path']}"]["sha256"]
        assert item["status"] == "UNSUPPORTED"
    assert diagnostics[0]["sha256"] != diagnostics[1]["sha256"]
    assert not [n for n in graph.nodes if n.kind.startswith("workbook")]
    (coordinator / "requirement.md").write_text("Inspect legacy amounts.")
    packet = feature.prepare(coordinator, "requirement.md", "legacy", 100_000, workspace=manifest,
                             scope="production")
    assert packet["coverage"]["artifact_diagnostics"] == diagnostics


def test_inventory_excluded_large_xls_is_content_bound_without_unbounded_reads(tmp_path, monkeypatch):
    from kgmaker.scanner import MAX_FILE_BYTES
    path = tmp_path / "src/legacy.xls"
    path.parent.mkdir()
    raw = FIXTURE.read_bytes()
    with path.open("wb") as stream:
        stream.write(raw)
        stream.truncate(MAX_FILE_BYTES + 1)
    (tmp_path / "requirement.md").write_text("Inspect legacy amount.")
    original_read_bytes = Path.read_bytes
    def bounded_sources_only(selected):
        assert selected != path, "oversized XLS must not be loaded into memory"
        return original_read_bytes(selected)
    monkeypatch.setattr(Path, "read_bytes", bounded_sources_only)
    packet = feature.prepare(tmp_path, "requirement.md", "large", 100_000, scope="production")
    diagnostic, = packet["coverage"]["artifact_diagnostics"]
    assert diagnostic["status"] == "UNSUPPORTED"
    assert packet["source_manifest"]["src/legacy.xls"]["sha256"] == diagnostic["sha256"]
    assert packet["source_manifest"]["src/legacy.xls"]["supported"] is False
    before_packet = feature.load_packet(tmp_path, "large")
    with path.open("r+b") as stream:
        stream.seek(-1, 2)
        stream.write(b"x")
    assert feature.freshness(tmp_path, packet)
    assert feature.load_packet(tmp_path, "large") == before_packet


def test_oversized_renamed_compound_rejected_before_full_hash_or_zip_parse(tmp_path):
    from kgmaker.workbooks import MAX_ARCHIVE_BYTES
    path = tmp_path / "oversized.xlsx"
    with path.open("wb") as stream:
        stream.write(bytes.fromhex("d0cf11e0a1b11ae1"))
        stream.truncate(MAX_ARCHIVE_BYTES + 1)
    with patch("kgmaker.workbooks.file_hash", side_effect=AssertionError("unbounded checksum")), \
            patch("kgmaker.workbooks.zipfile.ZipFile", side_effect=AssertionError("XLSX parser")):
        with pytest.raises(AnalysisError, match="exceeds"):
            extract(path, path.name, Classifier(tmp_path))


def test_oversized_workspace_xls_cache_refreshes_when_same_length_content_changes(tmp_path):
    import json
    from kgmaker.scanner import MAX_FILE_BYTES
    from kgmaker.workspace import snapshot_workspace
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    path = root / "src/legacy.xls"
    with path.open("wb") as stream:
        stream.write(FIXTURE.read_bytes())
        stream.truncate(MAX_FILE_BYTES + 1)
    manifest = tmp_path / "workspace.json"
    manifest.write_text(json.dumps({"schema_version": 1, "workspace_id": "large",
                                    "repositories": [{"id": "repo", "role": "shared", "path": "repo"}]}))
    coordinator = tmp_path / "coordinator"
    coordinator.mkdir()
    (coordinator / "requirement.md").write_text("Inspect legacy amount.")
    packet = feature.prepare(coordinator, "requirement.md", "large", 100_000, workspace=manifest,
                             scope="production")
    old = packet["coverage"]["artifact_diagnostics"][0]["sha256"]
    before_store = {p: p.read_bytes() for p in (coordinator / ".kgmaker").rglob("*") if p.is_file()}
    with path.open("r+b") as stream:
        stream.seek(-1, 2)
        stream.write(b"x")
    assert feature.freshness(coordinator, packet)
    assert {p: p.read_bytes() for p in (coordinator / ".kgmaker").rglob("*") if p.is_file()} == before_store
    coverage = snapshot_workspace(manifest)[1]
    assert coverage["artifact_diagnostics"][0]["sha256"] != old
