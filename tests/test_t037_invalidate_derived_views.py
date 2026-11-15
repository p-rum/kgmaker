import json
from copy import deepcopy

import pytest

from kgmaker.analysis_model import digest
from kgmaker.architecture_model import ViewDocument, ViewNode
from kgmaker.view_cache import get_or_build_snapshot_view, get_or_build_view
from test_t016_aggregate_service_topology import labelled_handoff
from test_t019_add_architecture_json_cli import run_cli, write
from test_t032_persist_process_review import inputs as review_inputs, write as approve_process


def inputs():
    workspace = {
        "schema_version": 1,
        "workspace_id": "demo",
        "repositories": [{"id": "backend", "role": "backend", "path": "backend"}],
        "services": [{"id": "orders", "backend_repo": "backend",
                      "contract": {"repo_id": "backend", "path": "api.yaml"}}],
        "service_ownership": {"schema_version": 1, "services": [{"id": "orders"}]},
        "remote_mapping": {"providers": []},
    }
    graph = {
        "schema_version": 3,
        "nodes": [{"id": "service:orders", "kind": "service", "name": "Orders"}],
        "edges": [], "contexts": [{"id": "ctx-main", "scope": "production"}],
        "analysis_annotations": [], "generated_at": "ignored metadata",
    }
    rules = {"topology": "topology-rules-1", "projection": "projection-1"}
    return workspace, graph, rules


def build(workspace, graph, rules, *, scope="production", context_selection=None):
    # Public builder used by the cached path.
    public_graph = deepcopy(graph)
    public_graph.pop("generated_at", None)
    nodes = tuple(ViewNode(node["id"], "service", node["name"])
                  for node in graph["nodes"] if node["kind"] == "service")
    count = len(nodes)
    return ViewDocument(
        schema_version=1,
        view_id="topology:demo",
        kind="topology",
        baseline_fingerprint=digest({"workspace": workspace, "graph": public_graph}),
        rules_version=rules["topology"],
        scope=scope,
        context_selection=context_selection or {},
        nodes=nodes,
        edges=(), provenance=(), coverage={"status": "PARTIAL", "counts": {
            "found": count, "resolved": 0, "unresolved": count, "excluded": 0}},
    )


def full_rebuild(workspace, graph, rules, *, scope="production", context_selection=None):
    """Independent canonical rebuild oracle for the simple service fixture."""
    inventory = sorted((row["id"], row["name"]) for row in graph["nodes"]
                       if row.get("kind") == "service")
    clean_graph = {key: value for key, value in graph.items() if key != "generated_at"}
    projected_nodes = tuple(
        ViewNode(identity, "service", label) for identity, label in inventory)
    total = len(projected_nodes)
    serialized = {
        "schema_version": 1,
        "view_id": "topology:demo",
        "kind": "topology",
        "baseline_fingerprint": digest({"workspace": workspace, "graph": clean_graph}),
        "rules_version": rules["topology"],
        "scope": scope,
        "context_selection": context_selection or {},
        "nodes": [node.to_dict() for node in projected_nodes],
        "edges": [],
        "diagnostics": [],
        "coverage": {"status": "PARTIAL", "counts": {
            "found": total, "resolved": 0, "unresolved": total, "excluded": 0}},
        "limits": [],
        "provenance": [],
    }
    return ViewDocument.from_dict(serialized)


def run(path, workspace, graph, rules, *, scope="production", context_selection=None):
    calls = []
    result = get_or_build_view(
        path,
        workspace=workspace,
        graph=graph,
        rules=rules,
        scope=scope,
        context_selection=context_selection or {},
        expected_baseline_fingerprint=build(workspace, graph, rules,
            scope=scope, context_selection=context_selection).baseline_fingerprint,
        builder=lambda: (calls.append(True) or build(workspace, graph, rules,
                                                      scope=scope,
                                                      context_selection=context_selection)),
    )
    return result, calls


def test_cache_hits_same_exact_scope_context_and_dependency_snapshot(tmp_path):
    workspace, graph, rules = inputs()
    cache = tmp_path / ".kgmaker" / "views" / "topology.json"
    first, calls = run(cache, workspace, graph, rules, context_selection={"ctx-main": "selected"})
    second, second_calls = run(cache, workspace, graph, rules, context_selection={"ctx-main": "selected"})
    assert calls == [True] and second_calls == []
    assert second.to_dict(include_generation_metadata=False) == first.to_dict(include_generation_metadata=False)


@pytest.mark.parametrize("mutation", ["service", "contract", "context", "rule", "annotation", "workspace_mapping"])
def test_dependency_mutations_force_rebuild_without_reusing_cached_approval(tmp_path, mutation):
    workspace, graph, rules = inputs()
    cache = tmp_path / "view.json"
    first, _ = run(cache, workspace, graph, rules)
    workspace, graph, rules = deepcopy(workspace), deepcopy(graph), deepcopy(rules)
    if mutation == "service":
        workspace["services"][0]["id"] = "orders-v2"
    elif mutation == "contract":
        workspace["services"][0]["contract"]["path"] = "api-v2.yaml"
    elif mutation == "context":
        graph["contexts"][0]["scope"] = "test"
    elif mutation == "rule":
        rules["topology"] = "topology-rules-2"
    elif mutation == "annotation":
        graph["analysis_annotations"].append({"id": "label:1", "target_ids": ["service:orders"], "text": "reviewed"})
    elif mutation == "workspace_mapping":
        workspace["remote_mapping"]["providers"].append({"id": "provider:new"})
    second, calls = run(cache, workspace, graph, rules)
    assert calls == [True]
    assert second.content_fingerprint != first.content_fingerprint


def test_negative_lookup_new_provider_and_unrelated_edit_invalidate_conservatively(tmp_path):
    workspace, graph, rules = inputs()
    cache = tmp_path / "view.json"
    unresolved, _ = run(cache, workspace, graph, rules)
    # A new provider can satisfy a previously unresolved lookup even if its ID was absent.
    workspace["remote_mapping"]["providers"].append({"id": "provider:orders", "route": "/orders"})
    resolved, calls = run(cache, workspace, graph, rules)
    assert calls == [True] and resolved.content_fingerprint != unresolved.content_fingerprint
    # The first safe implementation may invalidate broadly for an unrelated source edit.
    graph["nodes"].append({"id": "unrelated", "kind": "service", "name": "Other"})
    _, calls = run(cache, workspace, graph, rules)
    assert calls == [True]


@pytest.mark.parametrize("mutation", ["create", "edit", "delete", "rename"])
def test_mutation_refresh_matches_independent_full_rebuild(tmp_path, mutation):
    workspace, graph, rules = inputs()
    cache = tmp_path / "view.json"
    initial, _ = run(cache, workspace, graph, rules)
    before = deepcopy((workspace, graph, rules))
    if mutation == "create":
        graph["nodes"].append({"id": "service:new", "kind": "service", "name": "New"})
    elif mutation == "edit":
        graph["nodes"][0]["name"] = "Orders v2"
    elif mutation == "delete":
        graph["nodes"].clear()
    else:
        graph["nodes"][0]["id"] = "service:orders-renamed"
    refreshed, calls = run(cache, workspace, graph, rules)
    independently_built = full_rebuild(workspace, graph, rules)
    assert calls == [True]
    assert refreshed.to_dict(include_generation_metadata=False) == independently_built.to_dict(include_generation_metadata=False)
    assert (workspace, graph, rules) != before
    assert refreshed.content_fingerprint != initial.content_fingerprint


def test_invalid_inputs_and_builder_failure_leave_input_and_last_valid_artifact_unchanged(tmp_path):
    workspace, graph, rules = inputs()
    cache = tmp_path / "view.json"
    valid, _ = run(cache, workspace, graph, rules)
    stored_before = cache.read_bytes()
    inputs_before = deepcopy((workspace, graph, rules))
    with pytest.raises(ValueError):
        get_or_build_view(cache, workspace=workspace, graph=graph, rules={"bad": object()},
                          scope="production", context_selection={}, expected_baseline_fingerprint=valid.baseline_fingerprint,
                          builder=lambda: valid)
    with pytest.raises(RuntimeError, match="reproducible builder failure"):
        get_or_build_view(cache, workspace=workspace, graph=graph, rules={"topology": "changed"},
                          scope="production", context_selection={}, expected_baseline_fingerprint=valid.baseline_fingerprint,
                          builder=lambda: (_ for _ in ()).throw(RuntimeError("reproducible builder failure")))
    assert cache.read_bytes() == stored_before
    assert (workspace, graph, rules) == inputs_before


def test_dependency_change_during_builder_does_not_publish_candidate(tmp_path):
    workspace, graph, rules = inputs()
    cache = tmp_path / "view.json"
    valid, _ = run(cache, workspace, graph, rules)
    previous = cache.read_bytes()
    graph["nodes"].append({"id": "late", "kind": "service", "name": "Late"})
    current_doc = build(workspace, graph, rules)
    with pytest.raises(ValueError, match="VIEW_CACHE_INPUT_CHANGED_DURING_BUILD"):
        get_or_build_view(cache, workspace=workspace, graph=graph, rules=rules,
            scope="production", context_selection={},
            expected_baseline_fingerprint=current_doc.baseline_fingerprint,
            builder=lambda: (workspace["services"].append({"id": "late"}) or current_doc))
    assert cache.read_bytes() == previous


def test_stale_builder_result_cannot_be_published_under_a_new_dependency_binding(tmp_path):
    workspace, graph, rules = inputs()
    cache = tmp_path / "view.json"
    stale, _ = run(cache, workspace, graph, rules)
    previous = cache.read_bytes()
    graph["nodes"][0]["name"] = "Orders v2"
    current_baseline = build(workspace, graph, rules).baseline_fingerprint
    with pytest.raises(ValueError, match="VIEW_CACHE_BUILDER_BINDING_MISMATCH"):
        get_or_build_view(cache, workspace=workspace, graph=graph, rules=rules,
            scope="production", context_selection={},
            expected_baseline_fingerprint=current_baseline, builder=lambda: stale)
    assert cache.read_bytes() == previous


def test_corrupt_cache_is_a_miss_and_failed_rebuild_preserves_corrupt_bytes(tmp_path):
    workspace, graph, rules = inputs()
    cache = tmp_path / "view.json"
    cache.write_text('{"schema_version": 1, broken', encoding="utf-8")
    damaged = cache.read_bytes()
    with pytest.raises(RuntimeError):
        get_or_build_view(cache, workspace=workspace, graph=graph, rules=rules,
                          scope="production", context_selection={},
                          expected_baseline_fingerprint=build(workspace, graph, rules).baseline_fingerprint,
                          builder=lambda: (_ for _ in ()).throw(RuntimeError("no result")))
    assert cache.read_bytes() == damaged
    result, calls = run(cache, workspace, graph, rules)
    assert calls == [True] and result.scope == "production"


def test_symlinked_cache_parent_is_rejected_before_builder_or_write(tmp_path):
    workspace, graph, rules = inputs()
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "linked"
    link.symlink_to(real, target_is_directory=True)
    called = []
    with pytest.raises(ValueError, match="VIEW_CACHE_UNSAFE_PATH"):
        get_or_build_view(link / "view.json", workspace=workspace, graph=graph, rules=rules,
            scope="production", context_selection={}, expected_baseline_fingerprint="baseline",
            builder=lambda: called.append(True))
    assert called == [] and list(real.iterdir()) == []


def test_cached_artifact_never_crosses_scope_or_context_selection(tmp_path):
    workspace, graph, rules = inputs()
    cache = tmp_path / "view.json"
    first, _ = run(cache, workspace, graph, rules, context_selection={"ctx-main": "one"})
    second, calls = run(cache, workspace, graph, rules, scope="test", context_selection={"ctx-main": "one"})
    assert calls == [True] and second.scope == "test" and second.scope != first.scope
    third, calls = run(cache, workspace, graph, rules, scope="test", context_selection={"ctx-main": "two"})
    assert calls == [True] and third.context_selection == {"ctx-main": "two"}


def test_cache_file_is_versioned_and_contains_no_approval_or_runtime_upgrade(tmp_path):
    workspace, graph, rules = inputs()
    cache = tmp_path / "view.json"
    view, _ = run(cache, workspace, graph, rules)
    value = json.loads(cache.read_text(encoding="utf-8"))
    assert value["schema_version"] == 1
    assert ViewDocument.from_dict(value["view"]).content_fingerprint == view.content_fingerprint
    assert "approval" not in json.dumps(value).lower()
    assert "runtime_observed" not in json.dumps(value).lower()


def test_public_topology_projection_cache_is_used_and_review_transition_invalidates(tmp_path, monkeypatch):
    import kgmaker.service_topology as topology
    from kgmaker.process_store import read_process_reviews

    captured = labelled_handoff()
    path = tmp_path / "topology.json"
    review_root = tmp_path / "reviews"
    review_root.mkdir()
    process, packet, candidate = review_inputs()
    approve_process(review_root, process, packet, candidate)
    approved_review = read_process_reviews(review_root, process)
    assert approved_review["effective_status"] == "APPROVED"
    assert approved_review["active_annotations"]
    calls = []
    original = topology._aggregate

    def counted(snapshot):
        calls.append(snapshot["capture_id"])
        return original(snapshot)

    monkeypatch.setattr(topology, "_aggregate", counted)
    first = topology.aggregate_service_topology_cached(
        captured, path, annotations=approved_review)
    assert calls == [captured["capture_id"]]
    second = topology.aggregate_service_topology_cached(
        captured, path, annotations=approved_review)
    assert calls == [captured["capture_id"]]
    assert second.content_fingerprint == first.content_fingerprint
    process["technical_view"]["nodes"][0]["label"] = "Changed technical presentation"
    revalidated_review = read_process_reviews(review_root, process)
    assert revalidated_review["effective_status"] == "NEEDS_REVALIDATION"
    assert revalidated_review["active_annotations"] == []
    refreshed = topology.aggregate_service_topology_cached(captured, path, annotations=revalidated_review)
    assert calls == [captured["capture_id"], captured["capture_id"]]
    assert refreshed.content_fingerprint == first.content_fingerprint
    assert "APPROVED" not in json.dumps(refreshed.to_dict())


def test_snapshot_view_cache_rejects_stale_builder_result_without_replacing_last_valid(tmp_path):
    workspace, graph, rules = inputs()
    path = tmp_path / "view.json"
    first = build(workspace, graph, rules)
    captured = {"id": "capture-one"}
    expected = digest(["topology", "capture-one"])
    valid = ViewDocument(
        schema_version=1, view_id=first.view_id, kind=first.kind,
        baseline_fingerprint=expected, rules_version=first.rules_version, scope=first.scope,
        context_selection={}, nodes=first.nodes, edges=first.edges,
        provenance=first.provenance, coverage=first.coverage)
    get_or_build_snapshot_view(path, snapshot=captured, rules=rules,
        scope="production", context_selection={}, expected_baseline_fingerprint=expected,
        builder=lambda: valid)
    stored = path.read_bytes()
    captured["id"] = "capture-two"
    stale = get_or_build_snapshot_view
    with pytest.raises(ValueError, match="VIEW_CACHE_BUILDER_BINDING_MISMATCH"):
        stale(path, snapshot=captured, rules=rules, scope="production", context_selection={},
              expected_baseline_fingerprint=digest(["topology", "capture-two"]),
              builder=lambda: valid)
    assert path.read_bytes() == stored


def test_architecture_topology_cli_uses_only_explicit_cache_flag(tmp_path):
    captured = write(tmp_path / "capture.json", labelled_handoff())
    cache = tmp_path / "explicit-view-cache.json"
    uncached = run_cli("topology", "--capture-snapshot", captured)
    first = run_cli("topology", "--capture-snapshot", captured, "--view-cache", cache)
    assert uncached.returncode == first.returncode == 0
    assert json.loads(uncached.stdout) == json.loads(first.stdout)
    cache_bytes = cache.read_bytes()
    cache_time = cache.stat().st_mtime_ns
    second = run_cli("topology", "--capture-snapshot", captured, "--view-cache", cache)
    assert second.returncode == 0 and json.loads(second.stdout) == json.loads(uncached.stdout)
    assert cache.read_bytes() == cache_bytes and cache.stat().st_mtime_ns == cache_time


def filesystem_snapshot(root):
    return {str(path.relative_to(root)): (path.read_bytes(), path.stat().st_mtime_ns)
            if path.is_file() else None for path in root.rglob('*')}


def cache_fixture(tmp_path, state):
    captured = write(tmp_path / 'capture.json', labelled_handoff())
    cache = tmp_path / 'new-parent' / 'cache.json'
    if state == 'stale':
        workspace, graph, rules = inputs()
        run(cache, workspace, graph, rules)
    elif state == 'hit':
        result = run_cli('topology', '--capture-snapshot', captured, '--view-cache', cache)
        assert result.returncode == 0, result.stderr
    return captured, cache


@pytest.mark.parametrize('state', ['missing', 'stale', 'hit'])
@pytest.mark.parametrize(('extra', 'code'), [
    (['--filter-contexts', 'ctx-that-does-not-exist'], 2),
    (['--focus', 'secret=hidden'], 2),
    (['--max-nodes', '0'], 2),
    (['--expected-fingerprint', '0' * 64], 3),
    (['--format', 'unsupported'], 2),
    (['--strict'], 4),
])
def test_cli_rejected_request_preserves_inputs_and_cache(tmp_path, state, extra, code):
    captured, cache = cache_fixture(tmp_path, state)
    before = filesystem_snapshot(tmp_path)
    result = run_cli('topology', '--capture-snapshot', captured, '--view-cache', cache, *extra)
    assert result.returncode == code, result.stderr
    assert filesystem_snapshot(tmp_path) == before


@pytest.mark.parametrize('state', ['missing', 'stale', 'hit'])
@pytest.mark.parametrize('failure', ['output_limit', 'unsafe_output', 'write', 'flush', 'cancel'])
def test_cli_late_output_failure_never_publishes(tmp_path, monkeypatch, capsys, state, failure):
    import kgmaker.architecture_cli as cli
    captured, cache = cache_fixture(tmp_path, state)
    before = filesystem_snapshot(tmp_path)
    expected = 2
    if failure == 'output_limit':
        monkeypatch.setattr(cli, '_MAX_OUTPUT_CHARS', 1)
    elif failure == 'unsafe_output':
        monkeypatch.setattr(cli, 'sanitize', lambda value: {'redacted': True})
    elif failure == 'cancel':
        calls = []
        def cancel(args):
            calls.append(True)
            if len(calls) == 2:
                raise KeyboardInterrupt
        monkeypatch.setattr(cli, '_cancel', cancel)
        expected = 130
    else:
        class BrokenOutput:
            def write(self, value):
                if failure == 'write':
                    raise BrokenPipeError('closed')
            def flush(self):
                raise BrokenPipeError('closed')
        monkeypatch.setattr(cli.sys, 'stdout', BrokenOutput())
        expected = 141
    assert cli.run(['topology', '--capture-snapshot', str(captured), '--view-cache', str(cache)]) == expected
    assert filesystem_snapshot(tmp_path) == before


@pytest.mark.parametrize('state', ['missing', 'stale'])
@pytest.mark.parametrize(('error', 'code', 'diagnostic'), [(OSError, 2, 'INVALID_INPUT'), (KeyboardInterrupt, 130, 'CANCELLED')])
def test_cli_failed_atomic_publication_preserves_files_and_removes_temporary_paths(tmp_path, monkeypatch, capsys, state, error, code, diagnostic):
    import kgmaker.architecture_cli as cli
    import kgmaker.analysis_model as model
    captured, cache = cache_fixture(tmp_path, state)
    before = filesystem_snapshot(tmp_path)
    def failed_replace(source, destination):
        raise error('publication unavailable')
    monkeypatch.setattr(model.os, 'replace', failed_replace)
    assert cli.run(['topology', '--capture-snapshot', str(captured), '--view-cache', str(cache)]) == code
    output = capsys.readouterr()
    # stdout is a stream, not a transactional export; the process reports the
    # failed cache commit even though the valid view was already delivered.
    assert json.loads(output.out)['document']['kind'] == 'topology'
    assert json.loads(output.err)['code'] == diagnostic
    assert filesystem_snapshot(tmp_path) == before


@pytest.mark.parametrize('alias', ['capture', 'selector', 'hardlink', 'symlink', 'symlink_parent'])
def test_cli_cache_input_aliases_are_rejected_without_writes(tmp_path, alias):
    import os
    captured = write(tmp_path / 'capture.json', labelled_handoff())
    selector = write(tmp_path / 'selector.json', {'schema_version': 1, 'contexts': []})
    cache = captured
    if alias == 'selector':
        cache = selector
    elif alias == 'hardlink':
        cache = tmp_path / 'linked.json'
        os.link(captured, cache)
    elif alias == 'symlink':
        cache = tmp_path / 'linked.json'
        cache.symlink_to(captured)
    elif alias == 'symlink_parent':
        link = tmp_path / 'linked'
        link.symlink_to(tmp_path, target_is_directory=True)
        cache = link / 'capture.json'
    before = filesystem_snapshot(tmp_path)
    result = run_cli('topology', '--capture-snapshot', captured, '--context-selection', selector,
                     '--view-cache', cache)
    assert result.returncode == 2, result.stderr
    assert result.stdout == ''
    assert filesystem_snapshot(tmp_path) == before


from test_t019_add_architecture_json_cli import explicit_contract_fixture


@pytest.mark.parametrize('destination', ['manifest', 'source', 'index'])
def test_local_capture_cache_cannot_overwrite_workspace_or_source(explicit_contract_fixture, destination):
    from kgmaker.model import KnowledgeGraph
    manifest, *_ = explicit_contract_fixture
    for name in ['backend', 'client']:
        index = manifest.parent / name / '.kgmaker/graph.json'
        index.parent.mkdir()
        write(index, KnowledgeGraph(3, '.', 'old', [], [], {}).to_dict())
    cache = manifest
    if destination == 'source':
        cache = next((manifest.parent / 'backend').rglob('*.java'))
    elif destination == 'index':
        cache = manifest.parent / 'backend/.kgmaker/graph.json'
    before = filesystem_snapshot(manifest.parent)
    result = run_cli('topology', '--capture-local', '--workspace', manifest, '--view-cache', cache)
    assert result.returncode == 2, result.stderr
    assert result.stdout == ''
    assert filesystem_snapshot(manifest.parent) == before


@pytest.mark.parametrize('mutation', ['replace', 'add', 'delete', 'nested', 'list'])
def test_snapshot_wrapper_detects_original_input_mutations(tmp_path, mutation):
    workspace, graph, rules = inputs()
    valid = build(workspace, graph, rules)
    snapshot = {'id': 'one', 'nested': {'value': 'old'}, 'items': ['one']}
    path = tmp_path / 'cache.json'
    kwargs = dict(snapshot=snapshot, rules=rules, scope='production', context_selection={},
                  expected_baseline_fingerprint=valid.baseline_fingerprint)
    first = get_or_build_snapshot_view(path, **kwargs, builder=lambda: valid)
    stored = path.read_bytes()
    snapshot['id'] = 'two'  # Force a miss before the builder starts.
    def mutate():
        if mutation == 'replace': snapshot['id'] = 'new'
        elif mutation == 'add': snapshot['new-key'] = 'new'
        elif mutation == 'delete': del snapshot['id']
        elif mutation == 'nested': snapshot['nested']['value'] = 'new'
        else: snapshot['items'].append('new')
        return first
    with pytest.raises(ValueError, match='VIEW_CACHE_INPUT_CHANGED_DURING_BUILD'):
        get_or_build_snapshot_view(path, **kwargs, builder=mutate)
    assert path.read_bytes() == stored


def test_snapshot_wrapper_unchanged_build_hit_and_deferred_guard(tmp_path):
    from kgmaker.view_cache import prepare_snapshot_view
    workspace, graph, rules = inputs()
    valid = build(workspace, graph, rules)
    snapshot = {'id': 'one', 'nested': {'value': 'old'}}
    path = tmp_path / 'cache.json'
    kwargs = dict(snapshot=snapshot, rules=rules, scope='production', context_selection={},
                  expected_baseline_fingerprint=valid.baseline_fingerprint)
    before = deepcopy(snapshot)
    pending = prepare_snapshot_view(path, **kwargs, builder=lambda: valid)
    assert not path.exists()
    assert pending.publish().content_fingerprint == valid.content_fingerprint
    stored = path.read_bytes()
    def forbidden(): raise AssertionError('cache hit must not build')
    assert get_or_build_snapshot_view(path, **kwargs, builder=forbidden) == valid
    assert snapshot == before
    hit = prepare_snapshot_view(path, **kwargs, builder=forbidden)
    snapshot['id'] = 'changed-after-prepare'
    with pytest.raises(ValueError, match='VIEW_CACHE_INPUT_CHANGED_DURING_BUILD'):
        hit.publish()
    assert path.read_bytes() == stored


def test_local_capture_explicit_cache_directory_preserves_all_source_inputs(explicit_contract_fixture):
    from kgmaker.model import KnowledgeGraph
    manifest, *_ = explicit_contract_fixture
    for name in ['backend', 'client']:
        index = manifest.parent / name / '.kgmaker/graph.json'
        index.parent.mkdir()
        write(index, KnowledgeGraph(3, '.', 'old', [], [], {}).to_dict())
    cache = manifest.parent / 'backend/.kgmaker/views/topology.json'
    before = {str(p): p.read_bytes() for p in manifest.parent.rglob('*') if p.is_file()}
    result = run_cli('topology', '--capture-local', '--workspace', manifest, '--view-cache', cache)
    assert result.returncode == 0, result.stderr
    assert ViewDocument.from_dict(json.loads(cache.read_text())['view']).kind == 'topology'
    after = {str(p): p.read_bytes() for p in manifest.parent.rglob('*') if p.is_file() and p != cache}
    assert after == before


@pytest.mark.parametrize('state', ['missing', 'stale'])
def test_deferred_snapshot_miss_rechecks_original_before_publication(tmp_path, state):
    from kgmaker.view_cache import prepare_snapshot_view
    workspace, graph, rules = inputs()
    valid = build(workspace, graph, rules)
    path = tmp_path / 'cache.json'
    if state == 'stale':
        run(path, workspace, graph, rules)
    before = filesystem_snapshot(tmp_path)
    snapshot = {'id': 'one'}
    pending = prepare_snapshot_view(path, snapshot=snapshot, rules=rules, scope='production',
        context_selection={}, expected_baseline_fingerprint=valid.baseline_fingerprint,
        builder=lambda: valid)
    snapshot['id'] = 'changed-after-build'
    with pytest.raises(ValueError, match='VIEW_CACHE_INPUT_CHANGED_DURING_BUILD'):
        pending.publish()
    assert filesystem_snapshot(tmp_path) == before
