import copy
import json
import shutil
import subprocess
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

import kgmaker.workspace as workspace_module
from kgmaker.analysis_model import AnalysisError, digest, write_json
from kgmaker.build_runner import snapshot
from kgmaker.graph_provider import resolve_context_classpath_artifact
from kgmaker.inspection import artifact_hash, context
from kgmaker.scanner import scan_repository
from kgmaker.store import load_graph, save_graph
from kgmaker.workspace import qualified, snapshot_workspace
from kgmaker.views import select_service_contexts


def _jar(path: Path, marker: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "META-INF/maven/example/shared/pom.properties",
            "groupId=example\nartifactId=shared\nversion=1.0\n",
        )
        archive.writestr("example/Shared.class", marker)
    return path


def _producer(root: Path, marker: bytes, build_id: str) -> tuple[Path, str]:
    root.mkdir()
    (root / "pom.xml").write_text(
        "<project><modelVersion>4.0.0</modelVersion><groupId>example</groupId>"
        "<artifactId>shared</artifactId><version>1.0</version></project>"
    )
    (root / "src/main/java/example").mkdir(parents=True)
    (root / "src/main/java/example/Shared.java").write_text(
        "package example; public class Shared {}"
    )
    output = _jar(root / "build/libs/shared-1.0.jar", marker)
    sources = snapshot(root)
    manifest = {
        "schema_version": 1,
        "build_id": build_id,
        "snapshot": {
            "sources": sources,
            "content_hash": digest(sources),
            "inventory": "ALL_BUILD_INPUTS_V1",
        },
        "build_result": {
            "status": "SUCCESS",
            "execution_id": build_id,
            "freshness": "EXECUTION_BOUND",
        },
        "contexts": [
            {
                "id": "shared:main",
                "repo_id": root.name,
                "module": "shared",
                "source_set": "main",
                "scope": "production",
                "source_roots": ["src/main/java"],
                "source_files": ["src/main/java/example/Shared.java"],
                "classpath": [],
                "outputs": [
                    {
                        "path": "build/libs/shared-1.0.jar",
                        "sha256": artifact_hash(output),
                        "execution_id": build_id,
                        "snapshot_hash": digest(sources),
                        "freshness": "EXECUTION_BOUND",
                    }
                ],
            }
        ],
        "diagnostics": [],
    }
    manifest_path = root / ".kgmaker/builds" / build_id / "manifest.json"
    write_json(manifest_path, manifest)
    return manifest_path, artifact_hash(output)


def _consumer(root: Path, artifacts: list[Path]) -> str:
    root.mkdir(exist_ok=True)
    source = root / "src/main/java/example/App.java"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("package example; public class App { Shared value; }")
    base = scan_repository(root)
    selected = context(
        root,
        base,
        "jvm",
        {},
        repo_id=root.name,
        module="app",
        source_set="main",
        scope="production",
        build_context={
            "build_id": "consumer-build",
            "build_context_id": "app:main",
            "classpath": [
                {"path": str(path.resolve()), "sha256": artifact_hash(path)}
                for path in artifacts
            ],
            "bytecode_artifacts": [],
        },
    )
    base.contexts.append(selected)
    save_graph(base, root)
    return selected["id"]


def _workspace(tmp_path: Path, consumer_context: str, output_hash: str) -> tuple[Path, Path]:
    coordinator = tmp_path / "coordinator"
    coordinator.mkdir()
    manifest = tmp_path / "workspace.json"
    write_json(
        manifest,
        {
            "schema_version": 1,
            "workspace_id": "artifacts",
            "repositories": [
                {"id": "producer-a", "role": "shared", "path": "producer-a"},
                {"id": "producer-b", "role": "shared", "path": "producer-b"},
                {"id": "consumer", "role": "backend", "path": "consumer"},
            ],
            "release_mapping": {
                "schema_version": 1,
                "mappings": [
                    {
                        "id": "shared-to-app",
                        "producer": {
                            "repo_id": "producer-a",
                            "manifest_path": ".kgmaker/builds/build-a/manifest.json",
                            "context_id": "shared:main",
                        },
                        "consumer": {
                            "repo_id": "consumer",
                            "context_id": consumer_context,
                        },
                        "output_sha256": output_hash,
                    }
                ],
            },
        },
    )
    return coordinator, manifest


def _fixture(tmp_path: Path, *, consumer_markers: tuple[bytes, ...] = (b"A",)):
    _, hash_a = _producer(tmp_path / "producer-a", b"A", "build-a")
    _, hash_b = _producer(tmp_path / "producer-b", b"B", "build-b")
    artifacts = [
        _jar(tmp_path / "consumer" / ".kgmaker/classpath" / f"shared-{index}.jar", marker)
        for index, marker in enumerate(consumer_markers)
    ]
    consumer_context = _consumer(tmp_path / "consumer", artifacts)
    coordinator, manifest = _workspace(tmp_path, consumer_context, hash_a)
    return coordinator, manifest, hash_a, hash_b


def _workspace_selection_fixture(tmp_path: Path):
    coordinator, manifest, output_hash, _ = _fixture(tmp_path)
    producer_root = tmp_path / "producer-a"
    producer_graph = scan_repository(producer_root)
    producer_context = context(
        producer_root, producer_graph, "jvm", {}, repo_id="producer-a", module="shared",
        source_set="main", scope="production",
        build_context={"build_id": "build-a", "build_context_id": "shared:main",
                       "classpath": [], "bytecode_artifacts": []},
    )
    producer_graph.contexts.append(producer_context)
    save_graph(producer_graph, producer_root)
    _, coverage, _, graph, metadata = snapshot_workspace(manifest)
    consumer_context = next(item for item in graph.contexts
                            if item.get("repo_id") == "consumer" and item.get("module") == "app")
    requests = [
        {"service_id": "shared-lib", "repo_id": "producer-a", "module": "shared",
         "context_id": qualified("producer-a", producer_context["id"])},
        {"service_id": "app", "repo_id": "consumer", "module": "app",
         "context_id": consumer_context["id"]},
    ]
    selection = {"declaration": metadata["release_mapping"], "report": coverage["release_mapping"]}
    roots = {key: Path(value) for key, value in metadata["roots"].items()}
    return graph, requests, selection, roots, producer_context, consumer_context, output_hash


def test_t006_selects_nonempty_workspace_contexts_and_real_release_mapping(tmp_path):
    graph, requests, release_mapping, roots, producer_context, consumer_context, output_hash = (
        _workspace_selection_fixture(tmp_path))
    assert producer_context["id"] != "shared:main"
    assert producer_context["build_context_id"] == "shared:main"
    assert consumer_context["source_files"]
    assert all(path.startswith("@consumer/") for path in consumer_context["source_files"])

    selection = select_service_contexts(graph, requests, scope="production", repo_roots=roots,
                                        release_mapping=release_mapping)

    assert len(selection["release_compatibility"]) == 1
    assert selection["release_compatibility"][0] == {
        "mapping_id": "shared-to-app", "producer_service": "shared-lib",
        "consumer_service": "app", "status": "CONTENT_VERIFIED",
    }
    assert selection["context_selection"]["shared-lib"]["context_id"] == qualified(
        "producer-a", producer_context["id"])
    assert selection["services"][0]["context_fingerprint"]
    assert output_hash == release_mapping["report"]["mappings"][0]["sha256"]


@pytest.mark.parametrize(("field", "value"), [
    ("producer_repo", "other"),
    ("consumer_repo", "other"),
    ("sha256", "a" * 64),
    ("status", "PARTIAL"),
])
def test_t006_release_report_must_match_declaration_and_graph_evidence(tmp_path, field, value):
    graph, requests, release_mapping, roots, *_ = _workspace_selection_fixture(tmp_path)
    release_mapping["report"]["mappings"][0][field] = value

    selection = select_service_contexts(graph, requests, scope="production", repo_roots=roots,
                                        release_mapping=release_mapping)

    assert selection["release_compatibility"] == []
    assert any(item["code"] == "RELEASE_MAPPING_REPORT_MISMATCH"
               for item in selection["diagnostics"])


def test_t006_duplicate_release_report_rows_are_ambiguous(tmp_path):
    graph, requests, release_mapping, roots, *_ = _workspace_selection_fixture(tmp_path)
    release_mapping["report"]["mappings"].append(
        dict(release_mapping["report"]["mappings"][0]))

    selection = select_service_contexts(graph, requests, scope="production", repo_roots=roots,
                                        release_mapping=release_mapping)

    assert selection["release_compatibility"] == []
    assert any(item["code"] == "RELEASE_MAPPING_REPORT_AMBIGUOUS"
               for item in selection["diagnostics"])


def test_t006_release_mapping_becomes_stale_when_reported_output_changes(tmp_path):
    graph, requests, release_mapping, roots, *_ = _workspace_selection_fixture(tmp_path)
    (tmp_path / "producer-a/build/libs/shared-1.0.jar").write_bytes(b"changed after workspace snapshot")

    selection = select_service_contexts(graph, requests, scope="production", repo_roots=roots,
                                        release_mapping=release_mapping)

    assert selection["release_compatibility"] == []
    assert any(item["code"] == "RELEASE_MAPPING_STALE"
               for item in selection["diagnostics"])


def test_t006_release_report_without_graph_proof_stays_unresolved(tmp_path):
    graph, requests, release_mapping, roots, *_ = _workspace_selection_fixture(tmp_path)
    graph.edges = [edge for edge in graph.edges if edge.kind != "supplies_classpath"]

    selection = select_service_contexts(graph, requests, scope="production", repo_roots=roots,
                                        release_mapping=release_mapping)

    assert selection["release_compatibility"] == []
    assert any(item["code"] == "RELEASE_MAPPING_EVIDENCE_UNAVAILABLE"
               for item in selection["diagnostics"])


def test_t006_external_cache_classpath_is_bound_to_selected_entry(tmp_path):
    graph, requests, release_mapping, roots, _, consumer_context, _ = _workspace_selection_fixture(tmp_path)
    entry = consumer_context["classpath"][0]
    original = Path(entry["path"])
    external = tmp_path / "maven-cache" / original.name
    external.parent.mkdir()
    external.write_bytes(original.read_bytes())
    entry["path"] = str(external)
    report = release_mapping["report"]["mappings"][0]
    report["consumer_classpath_path"] = str(external)

    selection = select_service_contexts(graph, requests, scope="production", repo_roots=roots,
                                        release_mapping=release_mapping)

    assert selection["release_compatibility"][0]["status"] == "CONTENT_VERIFIED"

    # Matching bytes alone cannot substitute for the exact selected classpath path.
    unrelated = tmp_path / "other-cache" / original.name
    unrelated.parent.mkdir()
    unrelated.write_bytes(external.read_bytes())
    report["consumer_classpath_path"] = str(unrelated)
    selection = select_service_contexts(graph, requests, scope="production", repo_roots=roots,
                                        release_mapping=release_mapping)
    assert selection["release_compatibility"] == []
    assert any(item["code"] == "RELEASE_MAPPING_PATH_INVALID"
               for item in selection["diagnostics"])


def test_t006_shared_context_does_not_choose_an_arbitrary_service_owner(tmp_path):
    graph, requests, release_mapping, roots, *_ = _workspace_selection_fixture(tmp_path)
    requests.insert(1, {**requests[0], "service_id": "shared-lib-alias"})

    selection = select_service_contexts(graph, requests, scope="production", repo_roots=roots,
                                        release_mapping=release_mapping)

    assert selection["release_compatibility"] == []
    assert any(item["code"] == "RELEASE_MAPPING_SERVICE_AMBIGUOUS"
               for item in selection["diagnostics"])


def test_content_bound_release_output_links_exact_consumer_classpath(tmp_path):
    coordinator, manifest, hash_a, hash_b = _fixture(tmp_path)
    assert hash_a != hash_b

    real_popen = subprocess.Popen

    def git_only(argv, *args, **kwargs):
        assert isinstance(argv, list)
        assert argv[0] == "git", "workspace artifact mapping spawned a project/build process"
        return real_popen(argv, *args, **kwargs)

    with patch("subprocess.Popen", side_effect=git_only):
        _, coverage, _, graph, metadata = snapshot_workspace(manifest)

    mapping = coverage["release_mapping"]
    assert mapping["status"] == "COMPLETE"
    assert mapping["mappings"][0]["status"] == "CONTENT_VERIFIED"
    assert mapping["mappings"][0]["sha256"] == hash_a
    edges = [edge for edge in graph.edges if edge.kind == "supplies_classpath"]
    assert len(edges) == 1
    assert edges[0].evidence_kind == "SYMBOL_RESOLVED"
    assert metadata["release_mapping"]["schema_version"] == 1


def test_same_gav_and_class_name_with_different_bytes_stays_partial(tmp_path):
    coordinator, manifest, hash_a, hash_b = _fixture(tmp_path, consumer_markers=(b"B",))
    assert hash_a != hash_b
    before = list(coordinator.rglob("*"))

    _, coverage, _, graph, _ = snapshot_workspace(manifest)

    assert coverage["release_mapping"]["status"] == "PARTIAL"
    assert coverage["release_mapping"]["mappings"][0]["status"] == "PARTIAL"
    assert any(
        item["code"] == "RELEASE_CLASSPATH_HASH_MISMATCH"
        for item in coverage["release_mapping"]["diagnostics"]
    )
    assert not any(edge.kind == "supplies_classpath" for edge in graph.edges)
    assert before == list(coordinator.rglob("*"))


def test_duplicate_content_match_is_ambiguous_and_creates_no_edge(tmp_path):
    _, manifest, hash_a, _ = _fixture(tmp_path, consumer_markers=(b"A", b"A"))

    _, coverage, _, graph, _ = snapshot_workspace(manifest)

    assert coverage["release_mapping"]["status"] == "PARTIAL"
    assert any(
        item["code"] == "RELEASE_CLASSPATH_AMBIGUOUS"
        for item in coverage["release_mapping"]["diagnostics"]
    )
    assert not any(edge.kind == "supplies_classpath" for edge in graph.edges)


def test_invalid_release_mapping_preserves_existing_store_and_legacy_absence(tmp_path):
    coordinator, manifest, hash_a, _ = _fixture(tmp_path)
    store = coordinator / ".kgmaker/graph.json"
    store.parent.mkdir()
    store.write_bytes(b"last-valid-generation")
    before = store.read_bytes()
    data = json.loads(manifest.read_text())
    invalid = copy.deepcopy(data)
    invalid["release_mapping"]["mappings"][0]["output_sha256"] = "not-a-hash"
    write_json(manifest, invalid)

    with pytest.raises(AnalysisError, match="release mapping"):
        snapshot_workspace(manifest)
    assert store.read_bytes() == before

    data.pop("release_mapping")
    write_json(manifest, data)
    _, coverage, _, graph, metadata = snapshot_workspace(manifest)
    assert "release_mapping" not in coverage
    assert metadata["release_mapping"] is None
    assert graph.schema_version == 3


def test_artifact_mutation_during_snapshot_is_stale_and_preserves_store(tmp_path):
    coordinator, manifest, _, _ = _fixture(tmp_path)
    store = coordinator / ".kgmaker/graph.json"
    store.parent.mkdir()
    store.write_bytes(b"last-valid-generation")
    real = workspace_module._release_artifact_links

    def mutate_after_resolution(workspace, graphs):
        result = real(workspace, graphs)
        (tmp_path / "producer-a/build/libs/shared-1.0.jar").write_bytes(b"changed")
        return result

    with patch("kgmaker.workspace._release_artifact_links", side_effect=mutate_after_resolution):
        with pytest.raises(AnalysisError, match="RELEASE_ARTIFACT_CHANGED_DURING_SNAPSHOT"):
            snapshot_workspace(manifest, cache_root=coordinator, persist_cache=True)
    assert store.read_bytes() == b"last-valid-generation"
    assert not (coordinator / ".kgmaker/workspace-cache").exists()


def test_artifact_kind_swap_during_snapshot_is_stale_and_preserves_store(tmp_path):
    coordinator, manifest, _, _ = _fixture(tmp_path)
    store = coordinator / ".kgmaker/graph.json"
    store.parent.mkdir()
    store.write_bytes(b"last-valid-generation")
    producer_manifest = tmp_path / "producer-a/.kgmaker/builds/build-a/manifest.json"
    producer_build = json.loads(producer_manifest.read_text())
    producer_build["contexts"][0]["outputs"][0]["path"] = str(
        (tmp_path / "producer-a/build/libs/shared-1.0.jar").resolve()
    )
    write_json(producer_manifest, producer_build)
    real = workspace_module._release_artifact_links

    def replace_output_with_same_byte_symlink(workspace, graphs):
        result = real(workspace, graphs)
        output = tmp_path / "producer-a/build/libs/shared-1.0.jar"
        moved = output.with_name("shared-1.0-real.jar")
        output.rename(moved)
        output.symlink_to(moved.name)
        assert artifact_hash(output) == artifact_hash(moved)
        return result

    with patch(
        "kgmaker.workspace._release_artifact_links",
        side_effect=replace_output_with_same_byte_symlink,
    ):
        with pytest.raises(AnalysisError, match="RELEASE_ARTIFACT_CHANGED_DURING_SNAPSHOT"):
            snapshot_workspace(manifest, cache_root=coordinator, persist_cache=True)
    assert store.read_bytes() == b"last-valid-generation"
    assert not (coordinator / ".kgmaker/workspace-cache").exists()


def test_directory_outputs_are_not_misreported_as_content_identical(tmp_path):
    coordinator, manifest, _, _ = _fixture(tmp_path)
    producer = tmp_path / "producer-a"
    producer_output = producer / "build/classes/java/main"
    (producer_output / "example").mkdir(parents=True)
    (producer_output / "example/Shared.class").write_bytes(b"same-class")
    (producer_output / "application.properties").write_text("owner=producer\n")
    producer_hash = artifact_hash(producer_output)

    manifest_path = producer / ".kgmaker/builds/build-a/manifest.json"
    build = json.loads(manifest_path.read_text())
    build["contexts"][0]["outputs"] = [{
        "path": "build/classes/java/main",
        "sha256": producer_hash,
        "execution_id": "build-a",
        "snapshot_hash": build["snapshot"]["content_hash"],
        "freshness": "EXECUTION_BOUND",
    }]
    write_json(manifest_path, build)

    consumer_output = tmp_path / "consumer/.kgmaker/classpath/shared"
    (consumer_output / "example").mkdir(parents=True)
    (consumer_output / "example/Shared.class").write_bytes(b"same-class")
    (consumer_output / "application.properties").write_text("owner=consumer\n")
    assert artifact_hash(consumer_output) == producer_hash
    consumer_context = _consumer(tmp_path / "consumer", [consumer_output])

    workspace = json.loads(manifest.read_text())
    mapping = workspace["release_mapping"]["mappings"][0]
    mapping["consumer"]["context_id"] = consumer_context
    mapping["output_sha256"] = producer_hash
    write_json(manifest, workspace)

    _, coverage, _, graph, _ = snapshot_workspace(manifest)

    assert coverage["release_mapping"]["status"] == "PARTIAL"
    assert any(item["code"] == "RELEASE_OUTPUT_KIND_UNSUPPORTED"
               for item in coverage["release_mapping"]["diagnostics"])
    assert not any(edge.kind == "supplies_classpath" for edge in graph.edges)


def test_directory_consumer_classpath_is_rejected_by_resolver(tmp_path):
    consumer = tmp_path / "consumer"
    directory = consumer / ".kgmaker/classpath/shared"
    (directory / "example").mkdir(parents=True)
    (directory / "example/Shared.class").write_bytes(b"same-class")
    context_id = _consumer(consumer, [directory])
    selected = next(item for item in load_graph(consumer).contexts if item["id"] == context_id)

    with pytest.raises(AnalysisError, match="RELEASE_CLASSPATH_KIND_UNSUPPORTED"):
        resolve_context_classpath_artifact(consumer, selected, artifact_hash(directory))
