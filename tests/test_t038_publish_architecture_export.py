"""Exercise atomic publication through the public architecture export route."""
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from kgmaker import _view_export_cli, architecture_cli, architecture_render, process_cli, view_store
from kgmaker.architecture_model import ViewDocument
from test_t016_aggregate_service_topology import labelled_handoff
from test_t035_render_business_process_mermaid import file_snapshot
from test_t038_publish_view_artifacts_atomically import artifacts


pytestmark = pytest.mark.skipif(os.name != 'posix' or not hasattr(os, 'O_NOFOLLOW'),
                                reason='descriptor-confined publication requires POSIX')
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = 'reports/topology'
FILTERED = ('--focus', 'service:orders', '--max-nodes', '1')


@pytest.fixture
def capture(tmp_path):
    path = tmp_path / 'capture.json'
    path.write_text(json.dumps(labelled_handoff()), encoding='utf-8')
    return path


def run(root, action, *flags):
    return architecture_cli.run([action, '--root', str(root), '--capture-snapshot', 'capture.json', *flags])


def export(root, *flags, output=OUTPUT):
    return run(root, 'export', '--output', output, *flags)


def published(root, output=OUTPUT):
    directory = root / output
    return directory, json.loads((directory / 'manifest.json').read_bytes())


def test_public_export_matches_three_read_formats_and_retains_generations(capture, capsys, monkeypatch):
    root = capture.parent
    before = capture.read_bytes()

    def forbidden(*args, **kwargs):
        pytest.fail('an explicit topology export tried to recapture or execute a process')

    monkeypatch.setattr('kgmaker.service_topology.capture_topology_inputs', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    earlier = None
    for flags in ((), FILTERED):
        assert export(root, *flags) == 0
        directory, manifest = published(root)
        receipt = capsys.readouterr()
        assert receipt.out.encode() == (directory / 'manifest.json').read_bytes() and not receipt.err
        assert manifest['schema_version'] == 1 and manifest['view_kind'] == 'topology'
        files = artifacts(directory, manifest)
        envelope = json.loads(files['json'])
        document = ViewDocument.from_dict(envelope['document'])
        assert manifest['view_fingerprint'] == document.content_fingerprint
        assert document.scope == 'production' and document.coverage['status'] == 'PARTIAL'
        for name, raw in files.items():
            assert run(root, 'topology', '--format', name,
                       '--expected-fingerprint', manifest['view_fingerprint'], *flags) == 0
            output = capsys.readouterr()
            assert output.out.encode() == raw and not output.err
        metadata, = [row.removeprefix(b'  %% topology-meta ') for row in files['mermaid'].splitlines()
                     if row.startswith(b'  %% topology-meta ')]
        assert json.loads(metadata) == envelope
        assert files['markdown'].split(b'```mermaid\n', 1)[1].split(b'```\n', 1)[0] == files['mermaid']
        if earlier is None:
            assert [(edge.source, edge.target, edge.relation) for edge in document.edges] == [
                ('service:checkout', 'service:orders', 'remote_http_request_response')]
            earlier = manifest, files
        else:
            assert [node.id for node in document.nodes] == ['service:orders']
            assert envelope['filtering']['truncated'] and envelope['filtering']['frontier']
            assert manifest['generation'] != earlier[0]['generation']
            assert artifacts(directory, earlier[0]) == earlier[1]

        snapshot = file_snapshot(directory)
        assert export(root, '--expected-fingerprint', manifest['view_fingerprint'], *flags) == 0
        assert json.loads(capsys.readouterr().out) == manifest
        assert file_snapshot(directory) == snapshot and capture.read_bytes() == before


@pytest.mark.parametrize(('failure', 'expected', 'diagnostic'), [
    ('fingerprint', 3, 'EXPECTED_FINGERPRINT_MISMATCH'),
    ('scope', 2, 'CAPTURED_SCOPE_MISMATCH'),
    ('capture', 2, 'INVALID_INPUT'),
    ('renderer', 2, 'INVALID_INPUT'),
    ('late_source', 3, 'EXPORT_INPUT_CHANGED'),
    ('late_cancel', 130, 'CANCELLED'),
    ('late_timeout', 1, 'EXPORT_TIMEOUT'),
])
def test_rejected_or_interrupted_export_preserves_previous_generation(
        capture, capsys, monkeypatch, failure, expected, diagnostic):
    root = capture.parent
    assert export(root) == 0
    capsys.readouterr()
    previous = file_snapshot(root / OUTPUT)
    clock = [0.0]
    flags = [*FILTERED, '--timeout', '1', '--cancel-file', 'cancel']
    if failure == 'fingerprint':
        flags += ['--expected-fingerprint', '0' * 64]
    elif failure == 'scope':
        flags += ['--scope', 'test']
    elif failure == 'capture':
        data = json.loads(capture.read_bytes())
        data['capture_id'] = '0' * 64
        capture.write_text(json.dumps(data), encoding='utf-8')
    elif failure == 'renderer':
        def fail_markdown(*args):
            raise ValueError('injected failure in the second renderer')

        monkeypatch.setattr(architecture_render, '_topology_markdown', fail_markdown)
    before = capture.read_bytes()
    if failure.startswith('late_'):
        monkeypatch.setattr(_view_export_cli.time, 'monotonic', lambda: clock[0])
        same_file = view_store._same_file

        def stop_after_staging(parent, name, identity):
            result = same_file(parent, name, identity)
            if name == 'view.mmd':
                if failure == 'late_source':
                    capture.write_bytes(before + b'\n')
                elif failure == 'late_cancel':
                    (root / 'cancel').touch()
                else:
                    clock[0] = 2.0
            return result

        monkeypatch.setattr(view_store, '_same_file', stop_after_staging)
    assert export(root, *flags) == expected
    result = capsys.readouterr()
    assert not result.out and json.loads(result.err)['code'] == diagnostic
    assert file_snapshot(root / OUTPUT) == previous
    assert capture.read_bytes() == (before + b'\n' if failure == 'late_source' else before)


def test_confinement_and_foreign_kind_are_rejected_without_changes(capture, capsys):
    root = capture.parent
    foreign = root / 'reports/process'
    foreign.mkdir(parents=True)
    external = root / 'separate'
    external.mkdir()
    (root / 'reports/link').symlink_to(external, target_is_directory=True)
    fixture = ROOT / 'fixtures/process-model/checkout.json'
    process = root / 'process.json'
    process.write_bytes(fixture.read_bytes())
    assert process_cli.run(['export', '--root', str(root), '--snapshot', process.name,
                            '--output', 'reports/process']) == 0
    capsys.readouterr()
    previous = file_snapshot(root)
    for destination, code in [('../escaped', 'INVALID_EXPORT_PATH'),
                              ('reports/link', 'INVALID_EXPORT_PATH'),
                              ('reports/process', 'INVALID_EXPORT_MANIFEST')]:
        assert export(root, output=destination) == 2
        result = capsys.readouterr()
        assert not result.out and json.loads(result.err)['code'] == code
        assert file_snapshot(root) == previous and not (root.parent / 'escaped').exists()


def _competing_export(root, focus, barrier, results):
    render = architecture_render.render_topology_artifacts

    def wait_for_writer(*args):
        barrier.wait(timeout=10)
        return render(*args)

    architecture_render.render_topology_artifacts = wait_for_writer
    results.put(export(root, '--focus', focus, '--max-nodes', '1'))


def test_topology_writers_cannot_commit_from_the_same_manifest(capture, capsys):
    root = capture.parent
    assert export(root) == 0
    capsys.readouterr()
    directory, earlier = published(root)
    earlier_files = artifacts(directory, earlier)
    context = multiprocessing.get_context('fork')
    barrier, results = context.Barrier(2), context.Queue()
    writers = [context.Process(target=_competing_export, args=(root, f'service:{focus}', barrier, results))
               for focus in ('orders', 'checkout')]
    try:
        for writer in writers:
            writer.start()
        assert sorted(results.get(timeout=15) for _ in writers) == [0, 3]
        current = published(root)[1]
        assert current['generation'] != earlier['generation']
        assert len(list(directory.glob('generation-*'))) == 2
        assert artifacts(directory, earlier) == earlier_files
        node, = json.loads(artifacts(directory, current)['json'])['document']['nodes']
        assert node['id'] in {'service:checkout', 'service:orders'}
    finally:
        for writer in writers:
            writer.join(timeout=3)
            if writer.is_alive():
                writer.terminate()
                writer.join(timeout=3)
        results.close()


def test_parser_and_renderer_accept_exported_artifacts(capture, capsys):
    from test_t020_render_interface_markdown import parsed

    node = shutil.which('node')
    if node is None:
        pytest.skip('Node is unavailable for the Mermaid renderer test')
    assert export(capture.parent) == 0
    capsys.readouterr()
    directory, manifest = published(capture.parent)
    files = artifacts(directory, manifest)
    fence, = (token for token in parsed(files['markdown'].decode()) if token.type == 'fence')
    assert fence.info == 'mermaid' and fence.content.encode() == files['mermaid']
    mermaid = directory / manifest['artifacts']['mermaid']['path']
    command = [node, str(ROOT / 'tests/rendering/validate_t021_topology.mjs'), str(mermaid)]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False, timeout=20)
    if result.returncode and 'ERR_MODULE_NOT_FOUND' in result.stderr:
        pytest.skip('Mermaid 11.4.1/jsdom test dependencies unavailable')
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {'status': 'PASS', 'vertices': 2, 'edges': 1}
