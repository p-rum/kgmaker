"""Exercise the public read-only adapter against two actual Javac captures."""
from copy import deepcopy
import json
import os
import subprocess

import pytest

from kgmaker.analysis_model import write_json
from kgmaker.cli import main
from kgmaker.process_model import ProcessDefinition, ProcessView
from kgmaker.process_triggers import discover_process_triggers
from kgmaker.workspace import load_workspace, snapshot_workspace, split_id
from test_t025_build_local_process_path import capture_two_java_services


def files(root):
    return {path.relative_to(root): path.read_bytes() for path in root.rglob('*') if path.is_file()}


def cli(monkeypatch, capsys, *args):
    monkeypatch.setattr('sys.argv', ['kgmaker', *args])
    with pytest.raises(SystemExit) as exited:
        main()
    out, err = capsys.readouterr()
    return exited.value.code, out, err


def test_workspace_entry_and_stored_process_use_one_current_canonical_view(tmp_path, monkeypatch, capsys):
    manifest = capture_two_java_services(tmp_path)
    workspace = load_workspace(manifest)
    _, coverage, _, graph, _ = snapshot_workspace(manifest, persist_cache=False)
    inventory = discover_process_triggers(workspace, graph, source_coverage=coverage)
    selected = inventory.context_selection['services']
    assert set(selected) == {'orders', 'payments'}
    trigger, = [node for node in inventory.nodes if node.owner_id == 'service:orders']
    orders, = [context for context in selected['orders']['contexts'] if context['status'] == 'CURRENT']
    payments, = [context for context in selected['payments']['contexts'] if context['status'] == 'CURRENT']
    assert orders['context_id'] != payments['context_id']
    pins_document = {'schema_version': 1, 'contexts': [
        {'service_id': name, 'repo_id': name, 'module': 'app', 'context_id': context['context_id']}
        for name, context in [('orders', orders), ('payments', payments)]]}
    write_json(tmp_path / 'contexts.json', pins_document)
    wrong_sibling_pin = deepcopy(pins_document)
    wrong_sibling_pin['contexts'][1]['context_id'] = orders['context_id']
    write_json(tmp_path / 'wrong-sibling-pin.json', wrong_sibling_pin)

    original_popen = subprocess.Popen

    def only_readonly_git(command, *args, **kwargs):
        assert command[0] == 'git' and command[3:5] == ['rev-parse', 'HEAD'], command
        assert os.environ.get('GIT_OPTIONAL_LOCKS') == '0'
        return original_popen(command, *args, **kwargs)

    def no_network(*args, **kwargs):
        pytest.fail('read-only process projection opened a socket')

    monkeypatch.setattr('subprocess.Popen', only_readonly_git)
    monkeypatch.setattr('socket.socket', no_network)
    prefix = ('process', 'render', '--root', str(tmp_path), '--workspace', 'workspace.json')
    pins = ('--context-selection', 'contexts.json')
    entry = ('--entry', trigger.id)
    before = files(tmp_path)

    code, out, err = cli(monkeypatch, capsys, *prefix, *pins, *entry, '--format', 'json')
    assert (code, err) == (0, ''), (code, out, err)
    document = json.loads(out)
    view = ProcessView.from_dict(document)
    identity = 'process:' + trigger.id.removeprefix('trigger:')
    assert document['process_id'] == identity
    assert document['revision'] == 1
    assert view.definition.to_dict()['trigger_ids'] == [trigger.id]
    assert view.technical_view.scope == 'production'
    assert view.technical_status == 'PARTIAL'
    assert view.technical_view.context_selection == {'services': {'orders': selected['orders']}}
    assert {row['scope'] for row in view.technical_view.provenance} == {'production'}
    assert {cid for row in view.technical_view.provenance for cid in row['context_ids']} == {orders['context_id']}
    assert {'true', 'false'} <= {edge.relation for edge in view.transitions}
    assert cli(monkeypatch, capsys, *prefix, *entry) == (0, out, '')
    assert cli(monkeypatch, capsys, *prefix, *pins, *entry, '--strict') == (4, out, '')
    assert files(tmp_path) == before

    (tmp_path / 'saved.json').write_text(out, encoding='utf-8')
    saved = ('--process', identity, '--process-view', 'saved.json')
    # This was the previous valid selected-context representation. Its broad
    # context set still decodes and has the same baseline, but is not current.
    foreign = deepcopy(document)
    foreign['definition']['context_selection'] = inventory.context_selection
    foreign['technical_view']['context_selection'] = inventory.context_selection
    foreign['definition_fingerprint'] = ProcessDefinition.from_dict(foreign['definition']).content_fingerprint
    old = ProcessView.from_dict(foreign)
    assert old.technical_view.baseline_fingerprint == view.technical_view.baseline_fingerprint
    assert old.content_fingerprint != view.content_fingerprint
    write_json(tmp_path / 'old.json', foreign)
    (tmp_path / 'invalid.json').write_text('{"process_id":1,"process_id":2}', encoding='utf-8')
    invalid_revision = {**document, 'revision': 0}
    write_json(tmp_path / 'invalid-revision.json', invalid_revision)
    write_json(tmp_path / 'invalid-pins.json', {'schema_version': 2, 'contexts': []})
    before = files(tmp_path)
    assert cli(monkeypatch, capsys, *prefix, *pins, *saved,
               '--expected-fingerprint', view.content_fingerprint) == (0, out, '')
    invalid_pins = [cli(monkeypatch, capsys, *prefix, *selection, '--context-selection', 'wrong-sibling-pin.json')
                    for selection in (entry, saved)]
    assert [(code, len(stdout)) for code, stdout, _ in invalid_pins] == [(2, 0), (2, 0)]
    assert [json.loads(stderr)['code'] for _, _, stderr in invalid_pins] == ['INVALID_SELECTOR'] * 2
    for extra, exit_code, diagnostic in (
        ((), 2, 'INVALID_ARGUMENTS'),
        ((*entry, *saved), 2, 'INVALID_ARGUMENTS'),
        (('--process', identity), 2, 'PROCESS_VIEW_REQUIRED'),
        ((*entry, '--process-view', 'saved.json'), 2, 'PROCESS_VIEW_UNEXPECTED'),
        (('--process', 'process:other', '--process-view', 'saved.json'), 2, 'PROCESS_ID_MISMATCH'),
        (('--process', identity, '--process-view', 'invalid.json'), 2, 'INVALID_JSON'),
        (('--process', identity, '--process-view', 'invalid-revision.json'), 2, 'INVALID_INPUT'),
        (('--process', identity, '--process-view', 'old.json'), 3, 'PROCESS_VIEW_STALE'),
        ((*entry, '--context-selection', 'invalid-pins.json'), 2, 'INVALID_SELECTOR'),
        ((*saved, '--scope', 'test'), 2, 'PROCESS_SCOPE_MISMATCH'),
        ((*entry, '--scope', 'test'), 2, 'TRIGGER_UNAVAILABLE'),
        ((*entry, '--expected-fingerprint', '0' * 64), 3, 'EXPECTED_FINGERPRINT_MISMATCH'),
    ):
        result, stdout, stderr = cli(monkeypatch, capsys, *prefix, *extra)
        assert (result, stdout, json.loads(stderr)['code']) == (exit_code, '', diagnostic)
    assert files(tmp_path) == before

    code, legacy, err = cli(monkeypatch, capsys, 'flow', 'render', '--root', str(tmp_path / 'orders'),
        '--entry', split_id(trigger.attributes['entry_symbol_id'])[1],
        '--context', split_id(orders['context_id'])[1], '--view', 'process', '--format', 'json')
    assert (code, err) == (0, ''), (code, legacy, err)
    report = json.loads(legacy)
    assert report['schema_version'] == 1 and report['cfg']['blocks']
    assert 'definition' not in report
    assert files(tmp_path) == before

    original_index = tmp_path / 'payments/.kgmaker/graph.json'
    original_index.rename(original_index.with_name('held.json'))
    before = files(tmp_path)
    code, out, err = cli(monkeypatch, capsys, *prefix, *pins, *entry)
    assert (code, out, json.loads(err)['code']) == (2, '', 'ORIGINAL_INDEX_REQUIRED')
    assert files(tmp_path) == before
