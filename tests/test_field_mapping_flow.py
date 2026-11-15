"""W03 public compiler acceptance; source snapshots are not runtime observations."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from kgmaker.inspection import command, inspect_jvm
from kgmaker.model import KnowledgeGraph
from kgmaker.worker_protocol import WorkerError

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'fixtures/field-mapping'


def required(path):
    if not path.is_file():
        message = 'Required actual toolchain unavailable: ' + str(path)
        if os.environ.get('KGMAKER_REQUIRE_WORKERS') == '1':
            pytest.fail(message)
        pytest.skip(message)
    return str(path)


@pytest.fixture(scope='module')
def inspected(tmp_path_factory):
    root = tmp_path_factory.mktemp('field-mapping')
    shutil.copytree(FIXTURE / 'src', root / 'src')
    maven = Path(os.environ.get('KGMAKER_MAPSTRUCT_REPOSITORY', str(Path.home() / '.m2/repository')))
    api = required(maven / 'org/mapstruct/mapstruct/1.6.3/mapstruct-1.6.3.jar')
    processor = required(maven / 'org/mapstruct/mapstruct-processor/1.6.3/mapstruct-processor-1.6.3.jar')
    javac = required(Path(os.environ.get('JAVA_HOME', '/usr/lib/jvm/java-21-openjdk-amd64')) / 'bin/javac')
    try:
        command('jvm')
    except WorkerError as error:
        if os.environ.get('KGMAKER_REQUIRE_WORKERS') == '1': pytest.fail(str(error))
        pytest.skip(str(error))
    generated = root / 'src/generated/java'
    generated.mkdir(parents=True)
    subprocess.run([javac, '--release', '21', '-cp', api, '-processorpath', processor,
                    '-Amapstruct.suppressGeneratorTimestamp=true', '-s', str(generated),
                    '-d', str(root / 'classes'), *map(str, sorted((root / 'src/main/java').rglob('*.java')))], check=True)
    assert (generated / 'mapping/GeneratedMapperImpl.java').is_file()
    result = inspect_jvm(root, classpath=[api], publish=True,
                         build_context={'generated_source_roots': ['src/generated/java']})
    assert not any('.err.' in d.get('code', '') for d in result['diagnostics']), result['diagnostics']
    return root, KnowledgeGraph.from_dict(result['graph'])


def proofs(graph, relation=None):
    return [p for p in graph.evidence if p.get('field_mapping_version') == 1
            and (relation is None or p['relation'] == relation)]


def test_public_manual_and_actual_generated_mapper(inspected):
    from kgmaker.dataflow import impact_paths
    root, graph = inspected
    symbols = {s['id']: s for s in graph.symbols}
    mappings = proofs(graph, 'maps_to')
    assert mappings, 'Missing compiler-proven explicit field mappings'
    assert any(p['source_file'].endswith('Manual.java') and symbols[p['source']]['name'] == 'publicName'
               and symbols[p['target']]['name'] == 'publicName' for p in mappings)
    for filename in ('Manual.java', 'GeneratedMapperImpl.java'):
        mapped = [p for p in mappings if p['source_file'].endswith(filename)
                  and symbols[p['source']]['name'] == symbols[p['target']]['name'] == 'name']
        assert mapped, filename
        assert all(len(p['provenance']) >= 3 for p in mapped)
    assert proofs(graph, 'reads_value') and proofs(graph, 'writes_value')
    assert all(p['availability'] == p['business_equivalence'] == 'UNKNOWN'
               and p['runtime_execution'] == 'NOT_OBSERVED' and p['kind'] == 'SYMBOL_RESOLVED'
               for p in proofs(graph))
    example = mappings[0]
    impact = impact_paths(graph, example['source'])
    assert any(p['entity_ids'][-1] == example['target'] for p in impact['paths'])


def test_unknown_business_transform_dispatch_recursion_and_aliases(inspected):
    _, graph = inspected
    symbols = {s['id']: s for s in graph.symbols}
    mappings = proofs(graph, 'maps_to')
    names = {symbols[p['owner_method']]['name'] for p in mappings}
    assert {'copy', 'overloaded', 'map'} <= names
    assert not names & {'transformed', 'ambiguous', 'unknown', 'overwritten', 'loop', 'vararg'}
    codes = {d['code'] for d in graph.diagnostics}
    assert {'FIELD_MAPPING_CALL_BODY_UNKNOWN', 'FIELD_MAPPING_VALUE_UNKNOWN',
            'FIELD_MAPPING_CONTROL_FLOW_UNKNOWN'} <= codes
    assert not any(p['kind'] == 'RUNTIME_OBSERVED' for p in proofs(graph))
    overload = next(p for p in mappings if symbols[p['owner_method']]['name'] == 'overloaded')
    assert symbols[overload['source']]['name'] == symbols[overload['target']]['name'] == 'publicName'
    # Resolved compiler overload, not a name match, has the two-string descriptor.
    assert any('identity(Ljava/lang/String;Ljava/lang/String;)' in v['method'] for v in overload['provenance'])


def test_source_provenance_and_generated_origin_are_captured(inspected):
    import hashlib
    root, graph = inspected
    for proof in proofs(graph):
        assert proof['provenance']
        for locator in proof['provenance']:
            source = (root / locator['path']).read_bytes()
            assert hashlib.sha256(source).hexdigest() == locator['sha256']
            assert 0 <= locator['range']['start'] < locator['range']['end'] <= len(source)
    generated = [n for n in graph.nodes if n.path.endswith('GeneratedMapperImpl.java')]
    assert generated and any(n.origin == 'generated' for n in generated)


def test_field_store_roundtrip_and_offline_scan_preserve_proofs(inspected, monkeypatch):
    from kgmaker.cli import scan
    from kgmaker.dataflow import field_mapping_bindings
    from kgmaker.store import load_graph
    root, graph = inspected
    expected = field_mapping_bindings(graph)
    monkeypatch.setattr('subprocess.Popen', lambda *a, **kw: pytest.fail('offline process'))
    assert field_mapping_bindings(load_graph(root)) == expected
    assert scan(root, generate_docs=False) == 0
    assert field_mapping_bindings(load_graph(root)) == expected


@pytest.mark.parametrize('version', [1, 2, 3])
def test_legacy_schema_has_no_invented_compiler_mapping(version, tmp_path):
    from kgmaker.dataflow import field_mapping_bindings
    from kgmaker.model import Node
    from kgmaker.store import load_graph, save_graph
    graph = KnowledgeGraph(version, str(tmp_path), '', [Node('field', 'data_field', 'name', 'A.java')], [], {})
    save_graph(graph, tmp_path, generate_docs=False)
    assert field_mapping_bindings(load_graph(tmp_path)) == []


def test_workspace_qualifies_field_occurrences_and_provenance(inspected):
    from kgmaker.workspace import _qualified_node, _qualified_evidence, qualified
    _, graph = inspected
    node = next(n for n in graph.nodes if (n.metadata or {}).get('field_mapping_version') == 1)
    projected = _qualified_node('repo', node)
    assert projected.metadata['owner_method'] == qualified('repo', node.metadata['owner_method'])
    proof = proofs(graph, 'maps_to')[0]
    projected = _qualified_evidence('repo', proof)
    assert projected['owner_method'] == qualified('repo', proof['owner_method'])
    for source, target in zip(proof['provenance'], projected['provenance']):
        assert target['path'] == '@repo/' + source['path']
        assert target['method'] == qualified('repo', source['method'])
        if source['call_site']:
            assert target['call_site'] == qualified('repo', source['call_site'])


def snapshot(root):
    return {p.relative_to(root): p.read_bytes() for p in (root / '.kgmaker').rglob('*') if p.is_file()}


@pytest.mark.parametrize('failure', ['TIMED_OUT', 'CANCELLED', 'INVALID_PROTOCOL'])
def test_failed_inspection_preserves_last_field_generation(inspected, monkeypatch, failure):
    import kgmaker.inspection as inspection
    root, _ = inspected
    before = snapshot(root)
    original = inspection.request_worker
    def fail(*args, **kwargs):
        if failure != 'INVALID_PROTOCOL':
            raise WorkerError('controlled inspection failure', failure)
        response = original(*args, **kwargs)
        # Corrupt actual compiler evidence, not a hand-declared positive manifest.
        pending = [b['body'] for b in response['bodies']]
        from kgmaker.return_flow import _children
        while pending:
            node = pending.pop()
            binding = node.get('value_binding') or {}
            if binding.get('kind') == 'FIELD':
                binding['sha256'] = '0' * 64
                return response
            pending.extend(_children(node))
        pytest.fail('actual field binding missing')
    monkeypatch.setattr(inspection, 'request_worker', fail)
    maven = Path(os.environ.get('KGMAKER_MAPSTRUCT_REPOSITORY', str(Path.home() / '.m2/repository')))
    api = str(maven / 'org/mapstruct/mapstruct/1.6.3/mapstruct-1.6.3.jar')
    with pytest.raises(WorkerError) as caught:
        inspect_jvm(root, classpath=[api], build_context={'generated_source_roots': ['src/generated/java']})
    assert caught.value.status == failure
    assert snapshot(root) == before


def test_changed_field_source_is_stale_without_process(inspected, monkeypatch):
    from kgmaker.graph_provider import validate_context_snapshot
    root, graph = inspected
    source = root / 'src/main/java/mapping/Source.java'
    before = source.read_bytes()
    try:
        source.write_bytes(before + b'\n// changed\n')
        monkeypatch.setattr('subprocess.Popen', lambda *a, **kw: pytest.fail('offline process'))
        context = next(c for c in graph.contexts if c.get('field_flow_rule_version'))
        with pytest.raises(WorkerError) as caught:
            validate_context_snapshot(root, context)
        assert caught.value.status == 'STALE'
    finally:
        source.write_bytes(before)


def test_changed_projection_version_is_stale(inspected, monkeypatch):
    from kgmaker.graph_provider import validate_context_snapshot
    root, graph = inspected
    context = next(c for c in graph.contexts if c.get('field_flow_rule_version'))
    monkeypatch.setattr('subprocess.Popen', lambda *a, **kw: pytest.fail('offline process'))
    with pytest.raises(WorkerError, match='field mapping rules'):
        validate_context_snapshot(root, {**context, 'field_flow_rule_version': 'field-mapping-future'})


def test_source_only_never_runs_generator_or_promotes_mapping(tmp_path, monkeypatch):
    from kgmaker.dataflow import field_mapping_bindings
    from kgmaker.scanner import scan_repository
    shutil.copytree(FIXTURE / 'src', tmp_path / 'src')
    monkeypatch.setattr('subprocess.Popen', lambda *a, **kw: pytest.fail('implicit toolchain'))
    assert field_mapping_bindings(scan_repository(tmp_path)) == []
