"""Real Java evidence, narrow read-only use, and unchanged legacy data proofs."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
from unittest.mock import patch

import pytest

from kgmaker import feature
from kgmaker.analysis_model import AnalysisError, INPUT_METADATA, digest, inventory_candidate, write_json
from kgmaker.availability import evaluate_proof
from kgmaker.callgraph import adjacency
from kgmaker.cli import build_parser
from kgmaker.data_check import data_check
from kgmaker.dataflow import field_mapping_bindings, impact_paths
from kgmaker.feature_cli import run as run_feature
from kgmaker.runtime_evidence import import_manifest, produce_manifest
from kgmaker.runtime_value import FACT, PROOF, RELATION, resolve_capture
from kgmaker.store import GRAPH_FILE, MARKDOWN_FILE, MERMAID_FILE, load_graph
from tests.test_runtime_trace_producer import compile_runtime_fixture, inspect_runtime_fixture


ARTIFACT = Path('.kgmaker/runtime/presence.json')
VALUE = 'SYNTHETIC_FIXTURE_VALUE_49F95_NO_EXPORT'


@pytest.fixture(scope='module')
def application(tmp_path_factory, request):
    name = 'ValuePresenceApplication.java'
    source_text = None
    if getattr(request, 'param', 'same-line') == 'adjacent-line':
        source_text = (Path(__file__).with_name('fixtures') / 'runtime-trace' / name).read_text(encoding='utf-8')
        assignment_and_hook = 'Target.status = Source.status; TRACE.observeValuePresence(Source.status, Target.status);'
        assert source_text.count(assignment_and_hook) == 1
        source_text = source_text.replace(assignment_and_hook, assignment_and_hook.replace('; ', ';\n        ', 1))
    root, java, classes = compile_runtime_fixture(tmp_path_factory, 'runtime-value-presence', name, source_text=source_text)
    (root / 'requirement.md').write_text('Use the current status for a scoped audit.\n')
    context = inspect_runtime_fixture(root, classes, 'w03-presence', digest({'fixture': 'presence'}))
    (root / ARTIFACT).parent.mkdir(exist_ok=True)
    argv = [str(java), '-cp', str(classes), 'fixture.ValuePresenceApplication']
    return root, argv, context


def produce(application, mode, *args):
    root, argv, context = application
    return produce_manifest(root, [*argv, mode, *args], context_id=context['id'], runtime_id='value-' + mode,
                            build_id=context['build_id'], config_fingerprint=context['config_fingerprint'],
                            service_id='presence-fixture', service_version='1', output=ARTIFACT)


def outputs(root):
    return {path: (root / path).read_bytes() for path in (ARTIFACT, GRAPH_FILE, MARKDOWN_FILE, MERMAID_FILE)}


def proof_input(requirement, input_id, target, evidence_id, metadata):
    return {'id': input_id, 'name': 'status', 'requirement_ids': [requirement['id']], **metadata,
            'candidate_entity_ids': [target], 'availability_proof': {
                'kind': PROOF, 'runtime_evidence_id': evidence_id, 'mapping_decision_id': 'approved-status',
            }}


def check_projected_hook_authority(root, packet, candidate, item):
    graph = feature.graph_for_packet(root, packet)
    original, = [row for row in graph.evidence if row['id'] == item['availability_proof']['runtime_evidence_id']]
    hook, = [site for site in graph.call_sites if site['id'] == original['hook_call_site']]
    other_hook, = [site['id'] for site in graph.call_sites if site.get('declared_target') == hook['declared_target']
                   and 'ValuePresenceApplication.reversed(' in site['caller'] and site.get('range')]
    missing = replace(graph, call_sites=[site for site in graph.call_sites if site['id'] != hook['id']])
    with pytest.raises(AnalysisError, match='RUNTIME_VALUE_SITE'):
        evaluate_proof(root, packet, candidate, item, missing)
    physical, = [row for row in graph.call_sites if row.get('representation') == 'BYTECODE'
                 and row.get('source_mapping_ids') == [hook['caller']]]
    cfg, = [row for row in graph.cfgs if row['method'] == physical['caller']]
    body, = [row for row in graph.evidence if row['id'] in cfg['evidence_ids']]
    assert [row['target'] for row in body['physical_field_operands'] if row['target'] in (original['source'], original['target'])] == [
        original['source'], original['target'], original['source'], original['target'],
    ]
    missing = replace(graph, evidence=[row for row in graph.evidence if row['id'] != body['id']])
    with pytest.raises(AnalysisError, match='RUNTIME_VALUE_BYTECODE'):
        evaluate_proof(root, packet, candidate, item, missing)
    wrong_ordinal = replace(graph, evidence=[{**row, 'parameter_index': 1} if row.get('call_site') == hook['id']
                                            and row.get('argument_index') == 0 else row for row in graph.evidence])
    with pytest.raises(AnalysisError, match='RUNTIME_VALUE_ARGUMENTS'):
        evaluate_proof(root, packet, candidate, item, wrong_ordinal)
    for endpoint in ('source', 'target'):
        missing_static = replace(graph, symbols=[{**symbol, 'modifiers': []} if symbol['id'] == original[endpoint]
                                                else symbol for symbol in graph.symbols])
        with pytest.raises(AnalysisError, match='no current matching compiler field proof'):
            evaluate_proof(root, packet, candidate, item, missing_static)
    for field, value, error in (
        ('hook_call_site', other_hook, 'matching compiler hook proof'),
        ('runtime_id', 'invalid\n' + VALUE, 'identifier: runtime_id'),
        ('service_id', 'invalid\n' + VALUE, 'identifier: service_id'),
        ('service_version', 'invalid\n' + VALUE, 'identifier: service_version'),
    ):
        modified = {key: field_value for key, field_value in original.items() if key != 'id'}
        modified[field] = value
        modified['id'] = 'evidence:' + digest(modified)
        changed = replace(graph, evidence=[modified if row['id'] == original['id'] else row for row in graph.evidence],
                          edges=[replace(edge, evidence_ids=tuple(modified['id'] if ref == original['id'] else ref
                                                                 for ref in edge.evidence_ids)) for edge in graph.edges])
        changed_packet = {**packet, 'graph_evidence_ids': [*packet['graph_evidence_ids'], modified['id']]}
        input_item = {**item, 'availability_proof': {**item['availability_proof'], 'runtime_evidence_id': modified['id']}}
        with pytest.raises(AnalysisError, match=error) as exc:
            evaluate_proof(root, changed_packet, candidate, input_item, changed)
        assert VALUE not in str(exc.value)


@pytest.mark.parametrize(('application', 'line_delta'), [('same-line', 0), ('adjacent-line', 1)],
                         indirect=['application'], ids=['same-line', 'adjacent-line'])
def test_actual_java_value_presence_affects_only_matching_live_data_check(application, line_delta, monkeypatch, capsys):
    root, argv, context = application
    monkeypatch.setenv('FIXTURE_ONLY_VALUE', VALUE)
    monkeypatch.delenv('KGMAKER_RUNTIME_TRACE', raising=False)
    assert subprocess.run([*argv, 'present'], cwd=root, capture_output=True, check=True).stdout == b''
    graph = load_graph(root)
    symbols = {item['name']: item for item in graph.symbols if item.get('kind') == 'method'
               and item.get('owner') == 'fixture.ValuePresenceApplication'}
    bindings = field_mapping_bindings(graph)
    mapping, = [row for row in bindings if row['relation'] == 'maps_to' and row['owner_method'] == symbols['copy']['id']]
    source, target = mapping['source'], mapping['target']
    call = produce(application, 'call', symbols['main']['id'], symbols['plain']['id'])
    assert call['schema_version'] == 2 and call['facts'][0]['kind'] == 'call'
    call['observations'] = [{'caller': symbols['main']['id'], 'target': symbols['plain']['id'], 'kind': 'call'}]
    with patch('subprocess.Popen', side_effect=AssertionError('Offline import spawned a process')):
        assert import_manifest(root, call)['observations_imported'] == 1
    call_graph = load_graph(root)
    call_record, = [row for row in call_graph.evidence if row.get('runtime_id') == 'value-call']
    caller, copy, plain = (symbols[name]['id'] for name in ('main', 'copy', 'plain'))
    assertions = {}
    present = None
    combined_runs = (('combined-present', 'PRESENT'), ('combined-absent', 'ABSENT'), ('combined-threw', 'PRESENT'))
    for run, expected in (*combined_runs, ('present', 'PRESENT'), ('absent', 'ABSENT')):
        combined = run.startswith('combined-')
        threw = run == 'combined-threw'
        companion = symbols['throwingCompanion']['id'] if threw else plain
        arguments = (caller, copy, companion) if combined else ()
        before_capture = outputs(root)
        if combined:
            raw = subprocess.run([*argv, run, *arguments], cwd=root, capture_output=True, check=True,
                                 env={**os.environ, 'KGMAKER_RUNTIME_TRACE': '1'}).stdout
            assert VALUE.encode() not in raw and sha256(VALUE.encode()).hexdigest().encode() not in raw
            capture = json.loads(raw)
            assert capture['status'] == 'PARTIAL' and capture['diagnostics'] == ['INSTRUMENTED_SCOPE_ONLY']
            earlier, presence, later = capture['facts']
            assert earlier == {'kind': 'call', 'caller': caller, 'target': companion,
                               'outcome': 'THREW' if threw else 'RETURNED'}
            assert later == {'kind': 'call', 'caller': caller, 'target': copy, 'outcome': 'RETURNED'}
            assert presence['kind'] == FACT
        manifest = produce(application, run, *arguments)
        assert manifest['schema_version'] == 4 and manifest['observations'] == []
        assert all((root / path).read_bytes() == before_capture[path] for path in (GRAPH_FILE, MARKDOWN_FILE, MERMAID_FILE))
        assert json.loads((root / ARTIFACT).read_bytes()) == manifest
        if combined:
            assert {key: manifest[key] for key in capture} == capture
            fact = manifest['facts'][1]
        else:
            fact, = manifest['facts']
        assert fact['presence'] == expected and fact['kind'] == FACT
        assert fact['source_line'] == mapping['source_range']['end_line'] + line_delta
        with patch('subprocess.Popen', side_effect=AssertionError('Offline import spawned a process')):
            imported = import_manifest(root, manifest)
        assert imported['observations_imported'] == 1
        assertions[run], = imported['value_evidence_ids']
        if run == 'present':
            present = manifest
    before_replay = outputs(root)
    with pytest.raises(AnalysisError, match='RUNTIME_VALUE_AMBIGUOUS'):
        import_manifest(root, {**present, 'facts': manifest['facts']})
    assert outputs(root) == before_replay
    older = {**manifest, 'facts': [dict(manifest['facts'][0], presence='PRESENT')], 'runtime_id': 'expired',
             'run_started_at': (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()}
    assertions['expired'], = import_manifest(root, older)['value_evidence_ids']
    after = load_graph(root)
    assert field_mapping_bindings(after) == bindings
    assert impact_paths(after, source) == impact_paths(call_graph, source)
    assert adjacency(after) == adjacency(call_graph)
    assert [edge for edge in after.edges if edge.kind != RELATION] == call_graph.edges
    for run, _ in combined_runs:
        record, = [row for row in after.evidence if row.get('runtime_id') == 'value-' + run]
        assert record['id'] == assertions[run] and record['relation'] == RELATION
    packet = feature.prepare(root, 'requirement.md', 'w03', scope='production', context_id=context['id'])
    input_id, question_id = 'analysis:w03:input:status', 'analysis:w03:question:mapping'
    candidate = inventory_candidate(packet)
    requirement = {key: candidate['requirements'][0][key] for key in ('id', 'text', 'kind', 'source_quote')}
    candidate['questions'] = [{'id': question_id, 'text': 'Approve this exact status input?', 'owner_role': 'Analyst',
                              'status': 'OPEN', 'requirement_ids': [requirement['id']], 'blocking': True}]
    assert feature.apply(root, 'w03', candidate)['valid']
    metadata = dict.fromkeys(INPUT_METADATA)
    metadata.update(definition='Current status', data_type='string', freshness='PT1H', keys=['accountId'], quality=['nonempty'])
    answer = {'question_id': question_id, 'decision_id': 'approved-status', 'approval_status': 'APPROVED', 'revision': 1,
              'answer': json.dumps({'input_id': input_id, 'entity_id': target, 'metadata': metadata})}
    packet = feature.revise(root, 'w03', {'answers': [answer]})
    specification = {'schema_version': 1, 'analysis_id': 'w03', 'requirement_hash': packet['requirement_hash'],
                     'requirements': [requirement], 'inputs': [proof_input(requirement, input_id, target, assertions['present'], metadata)]}
    path = Path('.kgmaker/analyses/w03/live-inputs.json')
    write_json(root / path, specification)
    before = outputs(root)
    tracked = {file: file.read_bytes() for file in (root / '.kgmaker/analyses/w03').rglob('*.json')}
    real_popen = subprocess.Popen

    def read_only_git(command, *args, **kwargs):
        assert command == ['git', '-C', str(root), 'rev-parse', 'HEAD'], command
        return real_popen(command, *args, **kwargs)

    with patch('subprocess.Popen', side_effect=read_only_git):
        parsed = build_parser().parse_args(['feature', 'data-check', '--root', str(root), '--analysis', 'w03', '--inputs', str(path)])
        assert run_feature(parsed) == 0
        live = json.loads(capsys.readouterr().out)
        item, = live['candidate']['input_requirements']
        assert (item['availability'], item['usability']) == ('PARTIAL', 'UNASSESSED')
        assert 'value-present' in item['verification_scope'] and assertions['present'] in item['verification_scope']
        check_projected_hook_authority(root, packet, live['candidate'], item)
        assert not feature.apply(root, 'w03', live['candidate'])['valid']
        for run in ('combined-present', 'combined-threw'):
            combined = deepcopy(specification)
            combined['inputs'][0]['availability_proof']['runtime_evidence_id'] = assertions[run]
            combined_result = data_check(root, 'w03', combined)
            combined_item, = combined_result['candidate']['input_requirements']
            assert combined_result['valid']
            assert (combined_item['availability'], combined_item['usability']) == ('PARTIAL', 'UNASSESSED')
            assert 'value-' + run in combined_item['verification_scope']
        for evidence_id in (assertions['absent'], assertions['combined-absent'], assertions['expired'],
                            call_record['id'], 'evidence:arbitrary'):
            rejected = deepcopy(specification)
            rejected['inputs'][0]['availability_proof']['runtime_evidence_id'] = evidence_id
            result = data_check(root, 'w03', rejected)
            assert result['valid'] and result['candidate']['input_requirements'][0]['availability'] == 'UNKNOWN'
        for changes in ({'definition': 'Different business definition'}, {'candidate_entity_ids': [source]},
                        {'candidate_entity_ids': []}):
            rejected = deepcopy(specification)
            rejected['inputs'][0].update(changes)
            result = data_check(root, 'w03', rejected)
            assert result['valid'] and result['candidate']['input_requirements'][0]['availability'] == 'UNKNOWN'
        for updates in ({'raw_value': VALUE}, {'mapping_decision_id': VALUE}, {'runtime_evidence_id': VALUE}):
            rejected = deepcopy(specification)
            rejected['inputs'][0]['availability_proof'].update(updates)
            result = data_check(root, 'w03', rejected)
            assert result['valid'] and result['candidate']['input_requirements'][0]['availability'] == 'UNKNOWN'
            assert VALUE not in json.dumps(result)
    assert {file: file.read_bytes() for file in (root / '.kgmaker/analyses/w03').rglob('*.json')} == tracked
    assert outputs(root) == before
    forbidden = (VALUE.encode(), sha256(VALUE.encode()).hexdigest().encode())
    assert all(marker not in content for content in [*before.values(), json.dumps(live).encode()] for marker in forbidden)


def test_actual_java_value_capture_and_import_reject_unbound_evidence(application, monkeypatch):
    root, _, _ = application
    monkeypatch.setenv('FIXTURE_ONLY_VALUE', VALUE)
    valid = produce(application, 'present')
    before = outputs(root)
    for mode in ('reversed', 'ambiguous'):
        with pytest.raises(AnalysisError, match='RUNTIME_VALUE_(ARGUMENTS|BINDING)'):
            produce(application, mode)
        assert outputs(root) == before
    with patch('subprocess.Popen', side_effect=AssertionError('Offline import spawned a process')):
        for updates, reason in [({'facts': [{**valid['facts'][0], 'raw_value': VALUE}]}, 'RUNTIME_VALUE_FACT'),
                                ({'facts': [{**valid['facts'][0], 'caller_name': 'plain'}]}, 'RUNTIME_VALUE_BINDING'),
                                ({'config_fingerprint': 'foreign'}, 'STALE_RUNTIME'),
                                ({'run_started_at': (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()}, 'RUNTIME_VALUE_CLOCK')]:
            with pytest.raises(AnalysisError, match=reason) as error:
                import_manifest(root, {**valid, **updates})
            assert VALUE not in str(error.value)
        java = root / 'src/main/java/ValuePresenceApplication.java'
        original = java.read_bytes()
        try:
            java.write_bytes(original + b'\n// changed\n')
            with pytest.raises(AnalysisError, match='STALE_RUNTIME'):
                import_manifest(root, valid)
            with pytest.raises(AnalysisError, match='STALE_RUNTIME'):
                produce(application, 'present')
        finally:
            java.write_bytes(original)
    assert outputs(root) == before


def test_actual_java_value_capture_rejects_invalid_companions(application, monkeypatch):
    root, _, _ = application
    monkeypatch.setenv('FIXTURE_ONLY_VALUE', VALUE)
    symbols = {item['name']: item['id'] for item in load_graph(root).symbols if item.get('kind') == 'method'
               and item.get('owner') == 'fixture.ValuePresenceApplication'}
    caller, copy, plain = (symbols[name] for name in ('main', 'copy', 'plain'))
    valid = produce(application, 'combined-present', caller, copy, plain)
    before = outputs(root)
    earlier, presence, later = valid['facts']
    with pytest.raises(AnalysisError, match='out-of-context symbol'):
        produce(application, 'combined-present', 'unbound-caller', copy, plain)
    assert outputs(root) == before

    with patch('subprocess.Popen', side_effect=AssertionError('Offline import spawned a process')):
        for facts, reason in (
            ([earlier, later], 'RUNTIME_VALUE_FACT'),
            ([earlier, presence, presence, later], 'RUNTIME_VALUE_FACT'),
            ([earlier, presence, {'kind': 'interface_dispatch'}], 'RUNTIME_VALUE_FACT'),
            ([earlier, presence, {'kind': 'condition', 'owner': caller, 'predicate': copy, 'matched': True}],
             'RUNTIME_VALUE_FACT'),
            ([earlier, presence, {**later, 'target': 'unbound-target'}], 'out-of-context symbol'),
            ([earlier, presence, {**later, 'outcome': 'UNKNOWN'}], 'call outcome'),
            ([earlier, presence, {**later, 'raw_value': VALUE}], 'missing or unsupported fields'),
        ):
            with pytest.raises(AnalysisError, match=reason) as failure:
                import_manifest(root, {**valid, 'facts': facts})
            assert VALUE not in str(failure.value) and outputs(root) == before

    java = root / 'src/main/java/ValuePresenceApplication.java'
    original = java.read_bytes()
    try:
        java.write_bytes(original + b'\n// source change\n')
        with pytest.raises(AnalysisError, match='STALE_RUNTIME'):
            produce(application, 'combined-present', caller, copy, plain)
        with patch('subprocess.Popen', side_effect=AssertionError('Offline import spawned a process')):
            with pytest.raises(AnalysisError, match='STALE_RUNTIME'):
                import_manifest(root, valid)
    finally:
        java.write_bytes(original)
    assert outputs(root) == before


@pytest.mark.parametrize('entrypoint', ['produce', 'offline-import'])
def test_actual_java_value_rejects_reads_on_other_receiver_instances(application, monkeypatch, entrypoint):
    root, argv, _ = application
    monkeypatch.setenv('FIXTURE_ONLY_VALUE', VALUE)
    valid = produce(application, 'present')
    before = outputs(root)
    mode = 'different-receivers'
    raw = subprocess.run([*argv, mode], cwd=root, check=True, capture_output=True,
                         env={**os.environ, 'KGMAKER_RUNTIME_TRACE': '1'}).stdout
    assert VALUE.encode() not in raw
    exported = json.loads(raw)
    fact, = exported['facts']
    assert fact['presence'] == 'PRESENT' and fact['caller_name'] == 'misleading'

    with pytest.raises(AnalysisError, match='RUNTIME_VALUE_BINDING'):
        if entrypoint == 'produce':
            produce(application, mode)
        else:
            manifest = {**valid, 'runtime_id': 'other-receivers', 'facts': [fact]}
            with patch('subprocess.Popen', side_effect=AssertionError('Offline import spawned a process')):
                import_manifest(root, manifest)
    assert outputs(root) == before


@pytest.mark.parametrize('missing', ['cfg', 'ambiguous-cfg', 'cfg-evidence', 'ambiguous-path'])
def test_actual_java_value_requires_selected_physical_proof(application, monkeypatch, missing):
    root, _, context = application
    monkeypatch.setenv('FIXTURE_ONLY_VALUE', VALUE)
    manifest = produce(application, 'present')
    graph = load_graph(root)
    context, = [row for row in graph.contexts if row['id'] == context['id']]
    physical, = [symbol['id'] for symbol in graph.symbols if symbol.get('kind') == 'bytecode_method'
                 and symbol.get('owner') == 'fixture.ValuePresenceApplication' and symbol.get('name') == 'copy']
    cfg, = [item for item in graph.cfgs if item['method'] == physical]
    before = outputs(root)
    if missing == 'cfg':
        incomplete = replace(graph, cfgs=[item for item in graph.cfgs if item != cfg])
    elif missing == 'ambiguous-cfg':
        incomplete = replace(graph, cfgs=[*graph.cfgs, cfg])
    elif missing == 'cfg-evidence':
        incomplete = replace(graph, evidence=[row for row in graph.evidence if row['id'] not in cfg['evidence_ids']])
    else:
        ambiguous = {**cfg, 'edges': [*cfg['edges'], {'source': cfg['entry'], 'target': cfg['exit'], 'kind': 'normal'}]}
        incomplete = replace(graph, cfgs=[ambiguous if item == cfg else item for item in graph.cfgs])
    with pytest.raises(AnalysisError, match='RUNTIME_VALUE_BYTECODE'):
        resolve_capture(incomplete, context, manifest['facts'][0])
    with (patch('kgmaker.store.load_graph', return_value=incomplete),
          patch('kgmaker.store.save_graph', side_effect=AssertionError('Unproven import attempted publication')),
          patch('subprocess.Popen', side_effect=AssertionError('Offline import spawned a process'))):
        with pytest.raises(AnalysisError, match='RUNTIME_VALUE_BYTECODE'):
            import_manifest(root, manifest)
    assert outputs(root) == before


@pytest.mark.parametrize('application', ['same-line', 'adjacent-line'], indirect=True)
def test_actual_java_value_capture_rechecks_late_source_change_before_replace(application, monkeypatch):
    from kgmaker import analysis_model

    root, _, _ = application
    monkeypatch.setenv('FIXTURE_ONLY_VALUE', VALUE)
    produce(application, 'present')
    before = outputs(root)
    source = root / 'src/main/java/ValuePresenceApplication.java'
    original = source.read_bytes()
    real_atomic = analysis_model.atomic_write

    def changed_input(path, text, *, before_replace=None):
        if path == root / ARTIFACT:
            assert before_replace is not None
            source.write_bytes(original + b'\n// changed during publication\n')
        return real_atomic(path, text, before_replace=before_replace)

    monkeypatch.setattr(analysis_model, 'atomic_write', changed_input)
    try:
        with pytest.raises(AnalysisError, match='STALE_RUNTIME: source changed'):
            produce(application, 'present')
    finally:
        source.write_bytes(original)
    assert outputs(root) == before
