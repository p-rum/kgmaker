"""Public topology Markdown uses the already captured, filtered topology."""
import builtins
from copy import deepcopy
from html import unescape
import json
from pathlib import Path
import socket
import subprocess

import pytest

from kgmaker.architecture_cli import run
from kgmaker.architecture_render import render_topology_markdown, render_topology_mermaid
from test_t016_aggregate_service_topology import labelled_handoff
from test_t019_add_architecture_json_cli import run_cli, write
from test_t021_render_topology_mermaid import golden_topology, ROOT
from test_t037_invalidate_derived_views import filesystem_snapshot


def test_public_topology_three_formats_share_model_and_ids(tmp_path, capsys):
    path = tmp_path / 'topology-inputs.json'
    path.write_text(json.dumps(labelled_handoff()), encoding='utf-8')
    before = path.read_bytes()
    args = ['topology', '--root', str(tmp_path), '--capture-snapshot', path.name]
    outputs = {}
    for mode in ('json', 'mermaid', 'markdown'):
        status = run([*args, '--format', mode])
        output = capsys.readouterr()
        assert status == 0, output.err
        outputs[mode] = output.out
    envelope = json.loads(outputs['json'])
    nodes = envelope['document']['nodes']
    assert [item['id'] for item in nodes] == ['service:checkout', 'service:orders']
    edge, = envelope['document']['edges']
    assert (edge['source'], edge['target'], edge['relation']) == (
        'service:checkout', 'service:orders', 'remote_http_request_response',
    )
    markdown = outputs['markdown']
    start = markdown.index('```mermaid\n') + len('```mermaid\n')
    end = markdown.index('```\n', start)
    assert markdown[start:end] == outputs['mermaid']
    meta, = [line.removeprefix('  %% topology-meta ') for line in outputs['mermaid'].splitlines()
             if line.startswith('  %% topology-meta ')]
    assert json.loads(meta) == envelope
    visible = unescape(markdown[:start] + markdown[end:])
    assert '| service:checkout |' in visible and '| service:orders |' in visible
    assert f'| {edge["id"]} | service:checkout | service:orders | remote\\_http\\_request\\_response |' in visible
    assert path.read_bytes() == before and list(tmp_path.iterdir()) == [path]


def test_public_partial_topology_exposes_all_frontiers_and_preserves_cache(tmp_path):
    capture = write(tmp_path / 'capture.json', labelled_handoff('KAFKA'))
    cache = tmp_path / '.kgmaker/views/topology.json'
    args = ('topology', '--root', tmp_path, '--capture-snapshot', capture, '--view-cache', cache)
    seeded = run_cli(*args)
    assert seeded.returncode == 0 and cache.is_file(), seeded.stderr
    before = filesystem_snapshot(tmp_path)
    limits = ('--focus', 'service:orders', '--max-nodes', '1', '--strict')
    json_result = run_cli(*args, *limits)
    markdown = run_cli(*args, *limits, '--format', 'markdown')
    assert json_result.returncode == markdown.returncode == 4, markdown.stderr
    visible = unescape(markdown.stdout.split('## Scope, limits and omitted boundaries\n')[1])
    filtering = json.loads(json_result.stdout)['filtering']
    assert filtering['truncated'] is True and filtering['frontier']
    for item in filtering['frontier']:
        reason = item['reason'].replace('_', r'\_')
        assert f'| {item["id"]} | {reason} |' in visible
        for omitted in item['omitted_node_ids'] + item['omitted_edge_ids']:
            assert omitted in visible
    assert filesystem_snapshot(tmp_path) == before


@pytest.mark.parametrize(('flags', 'status', 'diagnostic'), [
    (('--expected-fingerprint', '0' * 64), 3, 'EXPECTED_FINGERPRINT_MISMATCH'),
    (('--scope', 'test'), 2, 'CAPTURED_SCOPE_MISMATCH'),
])
def test_public_rejected_topology_markdown_keeps_last_artifact(tmp_path, flags, status, diagnostic):
    capture = write(tmp_path / 'capture.json', labelled_handoff())
    cache = tmp_path / 'valid.json'
    args = ('topology', '--root', tmp_path, '--capture-snapshot', capture, '--view-cache', cache)
    assert run_cli(*args).returncode == 0 and cache.is_file()
    before = filesystem_snapshot(tmp_path)
    result = run_cli(*args, '--format', 'markdown', *flags)
    assert result.returncode == status and result.stdout == ''
    assert json.loads(result.stderr)['code'] == diagnostic
    assert filesystem_snapshot(tmp_path) == before


def test_markdown_render_failure_never_publishes_prepared_cache(tmp_path, capsys, monkeypatch):
    capture = write(tmp_path / 'capture.json', labelled_handoff())
    cache = tmp_path / 'last-valid.json'
    # Seed a valid older artifact so successful preparation would replace it on publication.
    previous = write(tmp_path / 'previous.json', labelled_handoff('KAFKA'))
    assert run_cli('topology', '--root', tmp_path, '--capture-snapshot', previous,
                   '--view-cache', cache).returncode == 0
    diagram = run_cli('topology', '--root', tmp_path, '--capture-snapshot', capture, '--format', 'mermaid')
    assert diagram.returncode == 0
    state = filesystem_snapshot(tmp_path)
    monkeypatch.setattr('kgmaker.architecture_render._MAX_OUTPUT_BYTES', len(diagram.stdout.encode()) + 20)
    code = run(['topology', '--root', str(tmp_path), '--capture-snapshot', capture.name,
                '--view-cache', cache.name, '--format', 'markdown'])
    result = capsys.readouterr()
    assert code == 2 and result.out == ''
    assert json.loads(result.err)['code'] == 'INVALID_INPUT'
    assert filesystem_snapshot(tmp_path) == state


def test_report_is_pure_deterministic_and_abstains_on_missing_source(monkeypatch):
    model = golden_topology()
    before = deepcopy(model)

    def forbidden(*args, **kwargs):
        pytest.fail('topology Markdown renderer attempted I/O')

    with monkeypatch.context() as guard:
        guard.setattr(subprocess, 'Popen', forbidden)
        guard.setattr(socket, 'socket', forbidden)
        guard.setattr(Path, 'open', forbidden)
        guard.setattr(builtins, 'open', forbidden)
        first = render_topology_markdown(model)
        second = render_topology_markdown(model)
    assert first.encode() == second.encode() and model == before
    sources = unescape(first.split('## Sources and provenance\n')[1])
    assert 'SOURCE\\_LOCATOR\\_UNAVAILABLE' in sources
    assert '| proof:http | SOURCE\\_ONLY | UNKNOWN | UNKNOWN | production |' in sources
    assert '| Source observation | NOT\\_CHECKED |' in first
    relationships = unescape(first.split('## Relationships\n')[1].split('## Scope')[0])
    unresolved = next(line for line in relationships.splitlines() if line.startswith('| edge:unknown |'))
    assert '| UNRESOLVED | UNKNOWN |' in unresolved and 'RUNTIME' not in relationships


@pytest.mark.parametrize(('subject', 'field', 'foreign'), [
    ('item', 'scope', 'test'),
    ('item', 'context_ids', ['ctx:foreign']),
    ('proof', 'scope', 'test'),
    ('proof', 'context_ids', ['ctx:foreign']),
])
def test_foreign_visible_claim_or_proof_is_rejected_without_mutation(subject, field, foreign):
    model = golden_topology()
    model['filtering']['criteria']['context_ids'] = ['ctx:prod']
    target = (model['document']['nodes'][0]['attributes'] if subject == 'item' else
              next(row for row in model['document']['provenance'] if row['id'] == 'proof:http'))
    target[field] = foreign
    before = deepcopy(model)
    with pytest.raises(ValueError, match='Invalid topology Markdown input'):
        render_topology_markdown(model)
    assert model == before


def test_explicit_context_report_does_not_display_uncited_proof_as_selected():
    model = golden_topology()
    model['filtering']['criteria']['context_ids'] = ['ctx:prod']
    model['document']['context_selection']['contexts'].append({'id': 'ctx:foreign'})
    model['document']['provenance'].append({'id': 'proof:outside', 'scope': 'test',
                                            'context_ids': ['ctx:foreign']})
    text = render_topology_markdown(model)
    head, diagram, rest = text.split('```', 2)
    assert 'ctx:foreign' in diagram and 'proof:outside' in diagram
    assert 'ctx:prod' in unescape(head)
    visible = unescape(head + rest)
    assert 'ctx:foreign' not in visible and 'proof:outside' not in visible


def test_markdown_parser_keeps_exact_embedded_diagram_and_escapes_captured_labels(tmp_path):
    from test_t020_render_interface_markdown import parsed, visible

    model = golden_topology()
    model['document']['nodes'][0]['label'] = 'Acme | Checkout ``` <b>API</b>'
    text = render_topology_markdown(model)
    tokens = parsed(text)
    fence, = (token for token in tokens if token.type == 'fence')
    assert fence.info == 'mermaid' and fence.content == render_topology_mermaid(model)
    assert not any(token.type == 'html_inline' for row in tokens for token in (row.children or ()))
    assert 'Acme | Checkout ``` <b>API</b>' in visible(tokens)

    output = tmp_path / 'embedded.mmd'
    output.write_text(fence.content, encoding='utf-8')
    harness = ROOT / 'tests/rendering/validate_t021_topology.mjs'
    result = subprocess.run(['node', str(harness), str(output)], cwd=ROOT, text=True,
                            capture_output=True, check=False)
    if result.returncode and 'ERR_MODULE_NOT_FOUND' in result.stderr:
        pytest.skip('Mermaid 11.4.1/jsdom test dependencies unavailable')
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt['status'] == 'PASS' and receipt['vertices'] == 5 and receipt['edges'] == 4
