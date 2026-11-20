"""Regression cases for overlapping publishers of the same graph store."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event

import pytest

from kgmaker import feature, store
from kgmaker.cli import scan
from kgmaker.scanner import scan_repository


def test_competing_publisher_cannot_cross_the_first_graph_commit(tmp_path):
    source = tmp_path / "source.py"
    source.write_text("def previous(): pass\n")
    previous = scan_repository(tmp_path)
    store.save_graph(previous, tmp_path)
    source.write_text("def newer(): pass\n")
    newer = scan_repository(tmp_path)

    about_to_publish = Event()
    release = Event()
    checkpoints = 0

    def pause_after_first_output():
        nonlocal checkpoints
        checkpoints += 1
        if checkpoints == 3:
            about_to_publish.set()
            assert release.wait(5)

    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(store.save_graph, newer, tmp_path,
                            before_replace=pause_after_first_output)
        try:
            assert about_to_publish.wait(5)
            assert store.load_graph(tmp_path).files == previous.files
            with pytest.raises(ValueError, match="Graph publication is already in progress"):
                store.save_graph(previous, tmp_path)
        finally:
            release.set()
        first.result(timeout=5)

    assert store.load_graph(tmp_path).files == newer.files
    assert (tmp_path / store.MARKDOWN_FILE).read_text() == store.render_markdown(newer)
    assert (tmp_path / store.MERMAID_FILE).read_text() == store.render_mermaid(newer)


def test_scan_does_not_replace_a_generation_published_during_capture(tmp_path, monkeypatch, capsys):
    source = tmp_path / "source.py"
    source.write_text("def previous(): pass\n")
    previous = scan_repository(tmp_path)
    store.save_graph(previous, tmp_path)
    source.write_text("def newer(): pass\n")
    newer = scan_repository(tmp_path)

    def capture(root):
        store.save_graph(newer, root)
        return previous, (0, 0), None

    monkeypatch.setattr(feature, "current_graph", capture)
    assert scan(tmp_path, generate_docs=False) == 3
    assert "Graph generation changed" in capsys.readouterr().err
    assert store.load_graph(tmp_path).files == newer.files
    assert (tmp_path / store.MARKDOWN_FILE).read_text() == store.render_markdown(newer)


@pytest.fixture
def newer_graph(tmp_path):
    source = tmp_path / "source.py"
    source.write_text("def previous(): pass\n")
    previous = scan_repository(tmp_path)
    store.save_graph(previous, tmp_path)
    source.write_text("def newer(): pass\n")
    return previous, scan_repository(tmp_path)


def test_runtime_import_cannot_overwrite_generation_published_during_validation(tmp_path, monkeypatch, newer_graph):
    from kgmaker import runtime_evidence

    previous, newer = newer_graph
    previous = replace(previous, schema_version=3)
    newer = replace(newer, schema_version=3)
    store.save_graph(previous, tmp_path)

    def validate(graph, root, manifest):
        store.save_graph(newer, root)
        return manifest, {"id": "test-context"}

    monkeypatch.setattr(runtime_evidence, "validate_manifest", validate)
    manifest = {"runtime_id": "test-run", "context_id": "test-context", "observations": []}
    with pytest.raises(ValueError, match="Graph generation changed"):
        runtime_evidence.import_manifest(tmp_path, manifest)
    assert store.load_graph(tmp_path).files == newer.files


def test_graph_migration_cannot_overwrite_generation_published_during_conversion(tmp_path, monkeypatch, newer_graph):
    from kgmaker import project_cli
    from kgmaker.cli import build_parser

    previous, newer = newer_graph

    def migrate(graph):
        store.save_graph(newer, tmp_path)
        return previous

    monkeypatch.setattr(type(previous), "migrate_legacy", migrate)
    args = build_parser().parse_args(["graph", "migrate", "--root", str(tmp_path)])
    assert project_cli.run(args) == 3
    assert store.load_graph(tmp_path).files == newer.files


def test_workspace_scan_rejects_an_intervening_graph_generation(tmp_path, monkeypatch, newer_graph):
    from kgmaker import workspace, workspace_cli
    from kgmaker.cli import build_parser

    previous, newer = newer_graph

    def capture(*args, **kwargs):
        store.save_graph(newer, tmp_path)
        return {}, {}, {}, previous, {}

    monkeypatch.setattr(workspace, "snapshot_workspace", capture)
    args = build_parser().parse_args(["scan", "--root", str(tmp_path), "--workspace", str(tmp_path / "w.json")])
    assert workspace_cli.workspace_command(args) == 3
    assert store.load_graph(tmp_path).files == newer.files


def test_stale_scan_does_not_replace_confluence_assertions_or_report(tmp_path, monkeypatch, newer_graph):
    previous, newer = newer_graph
    export = tmp_path / "export"
    export.mkdir()
    (export / "index.html").write_text("<html><title>Updated documentation</title></html>")
    report = tmp_path / "report.md"
    report.write_text("committed report\n")
    index = tmp_path / ".kgmaker/confluence-index.json"
    index.write_text("committed assertions\n")

    def capture(root):
        store.save_graph(newer, root)
        return previous, (0, 0), None

    monkeypatch.setattr(feature, "current_graph", capture)
    assert scan(tmp_path, confluence_dir="export", report="report.md") == 3
    assert report.read_text() == "committed report\n"
    assert index.read_text() == "committed assertions\n"
    assert store.load_graph(tmp_path).files == newer.files


@pytest.mark.parametrize("report_path", [store.GRAPH_FILE, store.MARKDOWN_FILE, store.MERMAID_FILE,
                                         store.PUBLICATION_LOCK, ".kgmaker/confluence-index.json",
                                         ".kgmaker/confluence-index.json/nested.md"])
def test_confluence_report_cannot_replace_reserved_state(tmp_path, capsys, newer_graph, report_path):
    export = tmp_path / "export"
    export.mkdir()
    graph_path = tmp_path / store.GRAPH_FILE
    before = graph_path.read_bytes()

    assert scan(tmp_path, confluence_dir="export", report=str(report_path)) == 2
    assert "overlaps KGMAKER graph state" in capsys.readouterr().err
    assert graph_path.read_bytes() == before


@pytest.mark.parametrize("existing_side_outputs", [False, True])
def test_confluence_graph_commit_failure_rolls_back_related_outputs(tmp_path, monkeypatch, existing_side_outputs):
    root = tmp_path / "repo"
    export = root / "export"
    export.mkdir(parents=True)
    source = root / "payment.py"
    source.write_text("class PaymentService: pass\n")
    page = export / "Routing.html"
    page.write_text("<h1>Routing</h1><p>PaymentService calls FirstGateway.</p>")
    report = tmp_path / "reports" / "nested" / "report.md"
    index = root / ".kgmaker/confluence-index.json"
    if existing_side_outputs:
        assert scan(root, confluence_dir="export", report=str(report)) == 0
        assert "FirstGateway" in report.read_text()
    else:
        store.save_graph(scan_repository(root), root)
    paths = [root / path for path in (store.GRAPH_FILE, store.MARKDOWN_FILE, store.MERMAID_FILE)] + [index, report]
    before = {path: path.read_bytes() if path.exists() else None for path in paths}
    page.write_text("<h1>Routing</h1><p>PaymentService calls SecondGateway.</p>")

    real_replace = store.os.replace

    def fail_graph(source, target):
        if target == root / store.GRAPH_FILE:
            raise OSError("injected graph commit failure")
        real_replace(source, target)

    monkeypatch.setattr(store.os, "replace", fail_graph)
    with pytest.raises(OSError, match="injected graph commit failure"):
        scan(root, confluence_dir="export", report=str(report))
    assert {path: path.read_bytes() if path.exists() else None for path in paths} == before
    assert report.parent.exists() == existing_side_outputs
    assert not list(tmp_path.rglob(".kgmaker-*"))


def test_runtime_import_rejects_stale_supplied_graph_before_losing_context(tmp_path):
    from kgmaker.analysis_model import file_hash
    from kgmaker.model import KnowledgeGraph, Node
    from kgmaker.runtime_evidence import import_manifest

    source = tmp_path / "A.java"
    source.write_text("class A {}\n")
    checksum = file_hash(source)
    context = {"id": "ctx", "scope": "production", "build_id": "build-1", "config_fingerprint": "cfg",
               "source_files": {"A.java": checksum}, "worker": {"distribution": []}}
    nodes = [Node(item, "method", item, "A.java", line=1, scope="production",
                  role="executable_code", origin="handwritten") for item in ("caller", "target")]
    previous = KnowledgeGraph(3, str(tmp_path), "now", nodes, [], {"A.java": checksum}, [context])
    newer = replace(previous, contexts=[context, {**context, "id": "newer-context"}])
    manifest = {"schema_version": 1, "runtime_id": "run-1", "context_id": "ctx", "build_id": "build-1",
                "config_fingerprint": "cfg", "source_hashes": {"A.java": checksum}, "worker_distribution": [],
                "observations": [{"caller": "caller", "target": "target", "kind": "dispatch"}]}
    store.save_graph(newer, tmp_path)
    path = tmp_path / store.GRAPH_FILE
    before = path.read_bytes()
    with pytest.raises(store.GraphPublicationConflict, match="Explicit runtime graph"):
        import_manifest(tmp_path, manifest, graph=previous)
    assert path.read_bytes() == before
    assert import_manifest(tmp_path, manifest, graph=newer)["observations_imported"] == 1
    updated = store.load_graph(tmp_path)
    assert [item["id"] for item in updated.contexts] == ["ctx", "newer-context"]
    assert any(edge.evidence_kind == "RUNTIME_OBSERVED" for edge in updated.edges)


@pytest.mark.parametrize("destination", ["relative", "absolute", "symlink"])
def test_confluence_scan_stages_related_outputs_on_destination_filesystem(tmp_path, monkeypatch, destination):
    import errno

    root = tmp_path / "repo"
    export = root / "export"
    export.mkdir(parents=True)
    (root / "payment.py").write_text("class PaymentService: pass\n")
    (export / "Routing.html").write_text("<h1>Routing</h1><p>PaymentService calls Gateway.</p>")
    report = tmp_path / "reports" / "report.md"
    if destination == "relative":
        report = root / "reports" / "report.md"
        report_arg = report.relative_to(root)
    elif destination == "symlink":
        report_arg = root / "report.md"
        try:
            report_arg.symlink_to(report)
        except OSError as error:
            pytest.skip(f"Report symlink unavailable: {error}")
    else:
        report_arg = report
    index = root / ".kgmaker/confluence-index.json"
    graph = root / store.GRAPH_FILE
    replaced = []
    real_replace = store.os.replace

    def no_cross_directory_replace(source, target):
        if source.parent != target.parent:
            raise OSError(errno.EXDEV, "injected cross-filesystem replacement")
        replaced.append(target)
        real_replace(source, target)

    monkeypatch.setattr(store.os, "replace", no_cross_directory_replace)
    assert scan(root, generate_docs=False, confluence_dir="export", report=str(report_arg)) == 0
    assert replaced == [report, index, graph]
    assert "Gateway" in report.read_text()
    assert "Routing.html" in index.read_text()
    assert any(node.id == "confluence:Routing.html" for node in store.load_graph(root).nodes)
    if destination == "symlink":
        assert report_arg.is_symlink() and report_arg.read_text() == report.read_text()
