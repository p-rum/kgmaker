"""T047-S02 compiler-attested Kotlin declarations and occurrence boundaries."""

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import runpy

import pytest

from kgmaker.inspection import command, inspect_jvm
from kgmaker.model import KnowledgeGraph
from kgmaker.worker_protocol import WorkerError
from kgmaker.workspace import snapshot_workspace


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = runpy.run_path(str(ROOT / "fixtures/incremental-integrity/workspace_fixture.py"))


def expected_key(repo, module, source_set, scope, parameter, *, name="score"):
    key = [1, repo, "kotlin", module, source_set, scope, "fixture", "top_level_function",
           name, [parameter], "kotlin.Int"]
    encoded = json.dumps(key, separators=(",", ":")).encode("utf-8")
    return "logical:kotlin-function-v1:" + hashlib.sha256(encoded).hexdigest()


def require_worker(backend):
    home = ROOT / "workers"
    try:
        command("jvm", home, kotlin_backend=backend)
    except WorkerError as error:
        if os.environ.get("KGMAKER_REQUIRE_WORKERS") == "1" or (
                backend == "k2" and os.environ.get("KGMAKER_REQUIRE_K2") == "1"):
            raise
        pytest.skip(str(error))
    return home


def kotlin_file(root, name, declarations):
    path = f"src/main/kotlin/{name}.kt"
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"package fixture\n{declarations}\n", encoding="utf-8")
    return path


@pytest.mark.parametrize("backend", ["k1", "k2"])
def test_native_incomplete_kotlin_selection_cannot_prove_realm_uniqueness(tmp_path, backend):
    home = require_worker(backend)
    first = kotlin_file(tmp_path, "First", "fun score(value: Int): Int = value + 1\n"
                                          "fun control(value: Int): Int = value")
    second = kotlin_file(tmp_path, "Second", "fun score(value: Int): Int = value + 2")
    model = {"source_sets": [{"module": "api", "id": "main", "scope": "production",
                              "roots": ["src/main/kotlin"]}]}

    def capture(inputs):
        result = inspect_jvm(tmp_path, repo_id="backend", module="api", source_set="main", sources=inputs,
                             project_model=model, home=home, kotlin_backend=backend, publish=False)
        assert result["exit_code"] == 0
        assert {first, second} <= result["context"]["source_files"].keys()
        graph = KnowledgeGraph.from_dict(result["graph"])
        symbols = {(s["path"], s["name"]): s for s in graph.symbols if s["name"] in {"score", "control"}}
        assert set(symbols) == {(path, name) for path in inputs
                                for name in (("score", "control") if path == first else ("score",))}
        assert all(s["context_id"] == result["context"]["id"] for s in symbols.values())
        assert not (tmp_path / ".kgmaker").exists()
        return symbols

    first_only, second_only, complete = capture([first]), capture([second]), capture([first, second])
    assert first_only[(first, "score")]["owner"] == "fixture.FirstKt"
    assert second_only[(second, "score")]["owner"] == "fixture.SecondKt"
    assert not any("logical_key" in symbol for symbols in (first_only, second_only) for symbol in symbols.values())
    assert "logical_key" not in complete[(first, "score")] and "logical_key" not in complete[(second, "score")]
    assert complete[(first, "control")]["logical_key"] == expected_key(
        "backend", "api", "main", "production", "kotlin.Int", name="control")


@pytest.mark.parametrize("backend", ["k1", "k2"])
def test_native_kotlin_conflicts_include_unwitnessed_source_declarations(tmp_path, backend):
    home = require_worker(backend)
    conflicts = {
        "nativePeer": "external fun nativePeer(value: Int): Int",
        "suspendPeer": "suspend fun suspendPeer(value: Int): Int = value",
        "renamedPeer": '@JvmName("renamed") fun renamedPeer(value: Int): Int = value',
        "annotatedPeer": '@Suppress("UNUSED_PARAMETER") fun annotatedPeer(value: Int): Int = 0',
        "inferredPeer": "fun inferredPeer(value: Int) = value",
        "aliasedPeer": "fun aliasedPeer(value: SameInt): Int = value",
        "internalPeer": "internal fun internalPeer(value: Int): Int = value",
        "privatePeer": "private fun privatePeer(value: Int): Int = value",
        "suppressedPeer": '@Suppress("CONFLICTING_OVERLOADS", "ERROR_SUPPRESSION") '
                          "private fun suppressedPeer(value: Int): Int = value",
        "unknownPeer": "fun unknownPeer(value: MissingType): Int = 0",
        "suppressedUnknown": '@Suppress("UNRESOLVED_REFERENCE") '
                             "fun suppressedUnknown(value: MissingType): Int = 0",
    }
    blocked = set(conflicts) | {"fileSuppressed"}
    controls = {"legalPrivate", "realOverload", "otherPackage", "unresolvedBody"}
    primary = kotlin_file(tmp_path, "Primary", "\n".join(
        f"fun {name}(value: Int): Int = {'missing(value)' if name == 'unresolvedBody' else 'value'}"
        for name in sorted(blocked | controls)))
    peers = kotlin_file(tmp_path, "Rivals", "\n".join([
        "typealias SameInt = Int",
        *conflicts.values(),
        "private fun legalPrivate(value: String): Int = value.length",
        "fun realOverload(value: String): Int = value.length",
        "fun unrelated(value: MissingType): Int = 0",
    ]))
    foreign = kotlin_file(tmp_path, "Foreign", "fun otherPackage(value: Int): Int = value")
    (tmp_path / foreign).write_text("package other\nfun otherPackage(value: Int): Int = value\n",
                                    encoding="utf-8")
    suppressed = kotlin_file(tmp_path, "Suppressed", "")
    (tmp_path / suppressed).write_text('@file:Suppress("CONFLICTING_OVERLOADS")\npackage fixture\n'
                                       "private fun fileSuppressed(value: Int): Int = value\n",
                                       encoding="utf-8")
    sources = [primary, peers, foreign, suppressed]
    model = {"source_sets": [{"module": "api", "id": "main", "scope": "production",
                              "roots": ["src/main/kotlin"]}]}
    lib = "target-k2" if backend == "k2" else "target"
    classpath = [str(home / "jvm" / lib / "lib" / "kotlin-stdlib.jar")]
    result = inspect_jvm(tmp_path, repo_id="backend", module="api", source_set="main", sources=sources,
                         project_model=model, home=home, kotlin_backend=backend, classpath=classpath,
                         publish=False)
    assert result["exit_code"] == 0
    assert set(result["context"]["compiler_inputs"]) == set(sources)
    graph = KnowledgeGraph.from_dict(result["graph"])
    local = {symbol["name"]: symbol for symbol in graph.symbols
             if symbol["path"] == primary and symbol["kind"] == "method"}
    assert set(local) == blocked | controls
    assert all(local[name]["descriptor"] == "(I)I" for name in local)
    actual_keys = {name for name, symbol in local.items() if "logical_key" in symbol}
    assert actual_keys == controls
    assert all("kotlin_declaration" not in local[name] for name in blocked)
    for name in controls:
        assert local[name]["logical_key"] == expected_key(
            "backend", "api", "main", "production", "kotlin.Int", name=name)
    overload, = [symbol for symbol in graph.symbols
                 if symbol["path"] == peers and symbol["name"] == "realOverload"]
    assert overload["logical_key"] == expected_key(
        "backend", "api", "main", "production", "kotlin.String", name="realOverload")
    assert not (tmp_path / ".kgmaker").exists()


@pytest.mark.parametrize("backend", ["k1", "k2"])
def test_native_structured_source_sets_do_not_share_flattened_membership(tmp_path, backend):
    home = require_worker(backend)
    own = kotlin_file(tmp_path, "Own", "fun score(value: Int): Int = value")
    foreign = kotlin_file(tmp_path, "Foreign", "fun other(value: Int): Int = value")
    model = {"source_sets": [
        {"module": "left:right", "id": "main", "scope": "production", "files": [own]},
        {"module": "left", "id": "right:main", "scope": "production", "files": [foreign]},
    ]}

    def capture(module, source_set, accepted_name, rejected_name):
        result = inspect_jvm(tmp_path, repo_id="backend", module=module, source_set=source_set,
                             sources=[own, foreign], project_model=model, home=home,
                             kotlin_backend=backend, publish=False)
        assert result["exit_code"] == 0
        graph = KnowledgeGraph.from_dict(result["graph"])
        symbols = {s["name"]: s for s in graph.symbols if s.get("kotlin_declaration")}
        assert set(symbols) == {accepted_name, rejected_name}
        assert {node.build_membership for node in graph.nodes
                if node.id in {s["id"] for s in symbols.values()}} == {("left:right:main",)}
        assert symbols[accepted_name]["logical_key"] == expected_key(
            "backend", module, source_set, "production", "kotlin.Int", name=accepted_name)
        assert "logical_key" not in symbols[rejected_name]

    capture("left:right", "main", "score", "other")
    capture("left", "right:main", "other", "score")
    assert not (tmp_path / ".kgmaker").exists()


@pytest.mark.parametrize("backend", ["k1", "k2"])
def test_native_named_callables_preserve_logical_keys_across_range_change(tmp_path, backend):
    home = require_worker(backend)
    FIXTURE["make_workspace"](tmp_path)
    root = tmp_path / "backend"
    target, caller = FIXTURE["TARGET"], FIXTURE["CALLER"]
    model = {"source_sets": [{"module": "api", "id": "main", "scope": "production",
                              "files": [target, caller]}]}

    def capture(params):
        result = inspect_jvm(root, repo_id="backend", module="api", source_set="main",
                             sources=[target, caller], project_model=model, home=home,
                             kotlin_backend=backend, publish=False)
        assert result["exit_code"] == 0
        graph = KnowledgeGraph.from_dict(result["graph"])
        overloads = {s["descriptor"]: s for s in graph.symbols
                     if s.get("path") == target and s.get("name") == "score"}
        assert set(overloads) == set(params)
        for descriptor, symbol in overloads.items():
            assert symbol["owner"] == "fixture.ScoringKt"
            assert result["context"]["source_files"][target] == symbol["sha256"] == hashlib.sha256(
                (root / target).read_bytes()).hexdigest()
            assert symbol.get("logical_key") == expected_key(
                "backend", "api", "main", "production", params[descriptor])
            resolves = any(site["declared_target"] == symbol["id"] and
                           site["context_id"] == symbol["context_id"] for site in graph.call_sites)
            assert resolves == (descriptor != "(Z)I")
        assert len({s["logical_key"] for s in overloads.values()}) == 2
        assert not (root / ".kgmaker").exists()
        return overloads

    string_descriptor = "(Ljava/lang/String;)I"
    params = {"(I)I": "kotlin.Int", string_descriptor: "kotlin.String"}
    replay = FIXTURE["mutations"](tmp_path)
    before = capture(params)
    assert next(replay)[0] == "comment"
    after = capture(params)
    for descriptor, prior in before.items():
        latest = after[descriptor]
        assert latest["logical_key"] == prior["logical_key"]
        assert latest["id"] != prior["id"] and latest["context_id"] != prior["context_id"]
        assert latest["range"]["start_line"] == prior["range"]["start_line"] + 1
    assert [next(replay)[0] for _ in range(3)] == ["body", "add", "signature"]
    replacement = capture({"(Z)I": "kotlin.Boolean", string_descriptor: "kotlin.String"})
    assert replacement[string_descriptor]["logical_key"] == before[string_descriptor]["logical_key"]
    assert replacement["(Z)I"]["logical_key"] != before["(I)I"]["logical_key"]


@pytest.mark.parametrize("backend", ["k1", "k2"])
def test_native_logical_keys_isolate_realms_and_unsupported_declarations(tmp_path, backend):
    home = require_worker(backend)
    FIXTURE["make_workspace"](tmp_path)
    manifest = tmp_path / "identity-workspace.json"
    manifest.write_text(json.dumps({"schema_version": 1, "workspace_id": "identity-fixture", "repositories": [
        {"id": "backend", "role": "backend", "path": "backend"},
        {"id": "frontend", "role": "frontend", "path": "frontend"},
    ]}))
    root = tmp_path / "backend"
    target = FIXTURE["TARGET"]
    test_target = target.replace("/main/", "/test/")
    source = (root / target).read_text()
    frontend = tmp_path / "frontend"
    for checkout, relative in ((root, test_target), (frontend, target)):
        fixture_source = checkout / relative
        fixture_source.parent.mkdir(parents=True, exist_ok=True)
        fixture_source.write_text(source)
    boundary = Path(target).with_name("Boundary.kt").as_posix()
    (root / boundary).write_text('''package fixture
fun generic(value: List<String>): Int = value.size
fun incompatible(value: Int?): Int = value ?: 1
fun outer(): Int { fun nested(): Int { return 1 }; return nested() }
fun collision(value: Int): Int = value
private fun hidden(value: Int): Int = value
''')
    other = Path(target).with_name("OtherBoundary.kt").as_posix()
    (root / other).write_text("package fixture\nfun collision(value: Int): Int = value + 1\n"
                              "private fun hidden(value: Int): Int = value + 1\n")
    main = {"module": "api", "id": "main", "scope": "production", "files": [target, boundary, other]}
    test = {"module": "api", "id": "test", "scope": "test", "files": [test_target]}
    options = {"module": "api", "home": home, "kotlin_backend": backend}

    syntax = snapshot_workspace(manifest)[3]
    assert not syntax.symbols
    assert any(n.name == "score" and "logical_key" not in (n.metadata or {}) for n in syntax.nodes)

    competing_membership = {**main, "module": "competing-module", "files": [target]}
    unproved = inspect_jvm(root, repo_id="backend", sources=[target], publish=False,
                           project_model={"source_sets": [main, test, competing_membership]}, **options)["graph"]
    assert any(s.get("kotlin_declaration") for s in unproved["symbols"])
    assert not any("logical_key" in s for s in unproved["symbols"])

    prod = inspect_jvm(root, repo_id="backend", sources=main["files"],
                       project_model={"source_sets": [main, test]}, **options)["graph"]
    exclusions = [s for s in prod["symbols"] if s["name"] in {"generic", "incompatible", "nested", "collision", "hidden"}]
    assert {s["name"] for s in exclusions} >= {"generic", "incompatible", "collision", "hidden"}
    for name in ("collision", "hidden"):
        assert len({s["owner"] for s in exclusions if s["name"] == name}) == 2
    assert not any("logical_key" in s for s in exclusions)
    assert not any("kotlin_declaration" in s for s in exclusions if s["name"] == "hidden")
    inspect_jvm(root, repo_id="backend", source_set="test", scope="test", sources=[test_target],
                project_model={"source_sets": [main, test]}, **options)
    inspect_jvm(frontend, repo_id="frontend", sources=[target],
                project_model={"source_sets": [{**main, "files": [target]}]}, **options)

    workspace = snapshot_workspace(manifest)[3]
    round_trip = KnowledgeGraph.from_dict(workspace.to_dict())
    symbols = [s for s in round_trip.symbols if s.get("name") == "score" and s.get("logical_key")]
    expectations = {(f"@{repo}/{relative}", expected_key(repo, "api", source_set, scope, param))
                    for repo, relative, source_set, scope in (("backend", target, "main", "production"),
                        ("backend", test_target, "test", "test"), ("frontend", target, "main", "production"))
                    for param in ("kotlin.Int", "kotlin.String")}
    assert {(s["path"], s["logical_key"]) for s in symbols} == expectations

    # Adapt legacy inputs to the raw wire shape. Keep native raw inputs as captured.
    raw_version = "selected-source-set-raw-1"
    raw_wire = deepcopy(round_trip.to_dict())
    for context in raw_wire["contexts"]:
        if "compiler_inputs" in context and context.get("source_snapshot_version") != raw_version:
            context["source_snapshot_version"] = raw_version
            context["compiler_inputs"] = [f"@{context['repo_id']}/{path}" for path in context["compiler_inputs"]]
    raw_symbols = KnowledgeGraph.from_dict(raw_wire).symbols
    assert {(s["path"], s["logical_key"]) for s in raw_symbols if s.get("name") == "score"
            and s.get("logical_key")} == expectations
    foreign_inputs = deepcopy(raw_wire)
    selected = next(c for c in foreign_inputs["contexts"] if c["id"] == symbols[0]["context_id"])
    selected["compiler_inputs"] = [f"@different/{path.split('/', 1)[1]}" for path in selected["compiler_inputs"]]
    with pytest.raises(ValueError, match="Invalid Kotlin logical symbol key"):
        KnowledgeGraph.from_dict(foreign_inputs)

    alias_manifest = tmp_path / "alias-workspace.json"
    alias_manifest.write_text(json.dumps({"schema_version": 1, "workspace_id": "alias-fixture", "repositories": [
        {"id": "other-realm", "role": "backend", "path": "backend"},
    ]}))
    aliased = snapshot_workspace(alias_manifest)[3]
    declarations = [s for s in aliased.symbols if s.get("name") == "score"]
    assert declarations and not any("logical_key" in s or "kotlin_declaration" in s for s in declarations)

    draft = deepcopy(prod)
    old_witness = next(s for s in draft["symbols"] if s.get("logical_key"))
    old_witness["kotlin_declaration"]["schema_version"] = 1
    occurrences = KnowledgeGraph.from_dict(draft).symbols
    retained, = [s for s in occurrences if s["id"] == old_witness["id"]]
    assert retained == {key: value for key, value in old_witness.items() if key != "logical_key"}
    assert "logical_key" in old_witness

    forged = deepcopy(prod)
    symbol = next(s for s in forged["symbols"] if s.get("logical_key"))
    symbol["logical_key"] = expected_key("foreign", "api", "main", "production", "kotlin.Int")
    with pytest.raises(ValueError, match="Invalid Kotlin logical symbol key"):
        KnowledgeGraph.from_dict(forged)
    for field, altered in (("origin_trust", "SUPPLIED_EXPORT_UNVERIFIED"), ("spring_profiles", ["blue"]),
                           ("module", "wrong-module"), ("source_set", "wrong-set"), ("scope", "test"),
                           ("source_files", {})):
        foreign_context = deepcopy(prod)
        container = next(c for c in foreign_context["contexts"] if c.get("id") == symbol["context_id"])
        container[field] = altered
        with pytest.raises(ValueError, match="Invalid Kotlin logical symbol key"):
            KnowledgeGraph.from_dict(foreign_context)


@pytest.mark.parametrize("version", [1, 2, 3])
def test_legacy_graphs_read_without_logical_proof(version):
    base = {"schema_version": version, "nodes": [], "edges": [], "files": {}}
    assert KnowledgeGraph.from_dict(base).symbols == []
