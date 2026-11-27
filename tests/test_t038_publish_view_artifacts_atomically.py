"""Exercise coherent publication through the public process export command."""
from contextlib import contextmanager
from hashlib import sha256
import json
import multiprocessing
import os

import pytest

from kgmaker import process_cli, process_render, view_store
from kgmaker.process_cli import run
from test_t035_render_business_process_mermaid import FIXTURE, file_snapshot, parse_and_render
from test_t036_render_business_process_report import inspect_report, partial_view


pytestmark = pytest.mark.skipif(os.name != 'posix' or not hasattr(os, 'O_NOFOLLOW'),
                                reason='descriptor-confined publication requires POSIX')


def export(root, *flags, snapshot='process.json', output='reports/process'):
    return run(['export', '--root', str(root), '--snapshot', snapshot, '--output', output, *flags])


def inputs(root):
    path = root / 'process.json'
    path.write_bytes(FIXTURE.read_bytes())
    return path


def variant(root, name):
    data = json.loads(FIXTURE.read_bytes())
    data['technical_view']['nodes'][0]['label'] += f' {name}'
    (root / f'{name}.json').write_text(json.dumps(data), encoding='utf-8')


def published(root):
    directory = root / 'reports/process'
    return directory, json.loads((directory / 'manifest.json').read_bytes())


def artifacts(root, manifest):
    result = {kind: (root / item['path']).read_bytes() for kind, item in manifest['artifacts'].items()}
    assert {kind: sha256(raw).hexdigest() for kind, raw in result.items()} == {
        kind: item['sha256'] for kind, item in manifest['artifacts'].items()
    }
    return result


def test_public_export_publishes_three_artifacts_for_one_snapshot(tmp_path, capsys):
    source = inputs(tmp_path)
    original = source.read_bytes()

    assert export(tmp_path) == 0
    output = capsys.readouterr()
    assert not output.err
    root = tmp_path / 'reports/process'
    manifest = json.loads(output.out)
    assert json.loads((root / 'manifest.json').read_bytes()) == manifest
    assert manifest['schema_version'] == 1
    assert manifest['view_kind'] == 'process'
    assert manifest['view_fingerprint'] == 'fcb448c2df7341791973b0e260d92f4907303dfde1ba06cc1af3ee8a88523387'
    assert set(manifest['artifacts']) == {'json', 'markdown', 'mermaid'}
    assert {item['path'].split('/')[0] for item in manifest['artifacts'].values()} == {
        f"generation-{manifest['generation']}"
    }
    result = artifacts(root, manifest)
    document = json.loads(result['json'])
    assert (document['process_id'], document['revision']) == ('process:checkout', 3)
    assert document['definition']['scope'] == 'production'
    assert document['definition']['context_ids'] == ['ctx-prod']
    assert sha256(result['mermaid']).hexdigest() == '55881e998d92ad88d42a03e3f28f259256827b9429ed1ce1c8be4f3833de57fa'
    assert source.read_bytes() == original


def test_native_export_preserves_partial_boundaries_in_all_artifacts(tmp_path, monkeypatch):
    source = tmp_path / 'process.json'
    raw = partial_view().to_json().encode()
    source.write_bytes(raw)

    def forbidden(*args, **kwargs):
        pytest.fail('explicit artifact rendering started a subprocess or opened a socket')

    with monkeypatch.context() as offline:
        offline.setattr('subprocess.Popen', forbidden)
        offline.setattr('socket.socket', forbidden)
        assert export(tmp_path) == 0

    root, manifest = published(tmp_path)
    result = artifacts(root, manifest)
    document = json.loads(result['json'])
    assert document['technical_status'] == 'PARTIAL' and document['technical_view']['coverage']['truncated']
    assert 'Review flag only' in result['json'].decode()
    assert 'Review flag only' not in result['markdown'].decode() + result['mermaid'].decode()
    tables, diagram = inspect_report(result['markdown'].decode())
    assert diagram.encode() == result['mermaid']
    assert tables['Snapshot'][2]['Captured value'] == manifest['view_fingerprint']
    boundaries = [row for row in tables['Step ID'] if json.loads(row['Step ID']) == 'send']
    assert boundaries[0]['Resolution'] == 'UNRESOLVED'
    assert boundaries[0]['Evidence refs'] == '[]'
    assert parse_and_render(diagram, tmp_path) == {'vertices': 7, 'edges': 9, 'lanes': 0}
    assert source.read_bytes() == raw


def test_reader_keeps_one_generation_and_repeating_active_export_is_idempotent(tmp_path, monkeypatch):
    inputs(tmp_path)
    variant(tmp_path, 'new')
    assert export(tmp_path) == 0
    root, first = published(tmp_path)
    previous = artifacts(root, first)
    unchanged = file_snapshot(root)
    assert export(tmp_path) == 0
    assert published(tmp_path)[1] == first and file_snapshot(root) == unchanged
    replace = os.replace
    before_switch = []

    def observe(source, destination, **kwargs):
        assert destination == 'manifest.json'
        before_switch.append(published(tmp_path)[1])
        assert artifacts(root, first) == previous
        return replace(source, destination, **kwargs)

    monkeypatch.setattr(view_store.os, 'replace', observe)
    assert export(tmp_path, snapshot='new.json') == 0
    newest = published(tmp_path)[1]
    assert before_switch == [first]
    assert newest['generation'] != first['generation']
    assert artifacts(root, first) == previous and artifacts(root, newest) != previous


def _competing_export(root, snapshot, barrier, results):
    render = process_render.render_process_artifacts

    def wait_for_writer(view):
        barrier.wait(timeout=20)
        return render(view)

    process_render.render_process_artifacts = wait_for_writer
    results.put(export(root, snapshot=snapshot))


def test_two_processes_cannot_switch_from_the_same_manifest(tmp_path):
    inputs(tmp_path)
    variant(tmp_path, 'writer-a')
    variant(tmp_path, 'writer-b')
    assert export(tmp_path) == 0
    root, before = published(tmp_path)
    before_bytes = artifacts(root, before)
    context = multiprocessing.get_context('fork')
    barrier, results = context.Barrier(2), context.Queue()
    writers = [context.Process(target=_competing_export, args=(tmp_path, f'writer-{name}.json', barrier, results))
               for name in ('a', 'b')]
    try:
        for writer in writers:
            writer.start()
        assert sorted(results.get(timeout=30) for _ in writers) == [0, 3]
        assert artifacts(root, before) == before_bytes
        winner = published(tmp_path)[1]
        label = json.loads(artifacts(root, winner)['json'])['technical_view']['nodes']
        assert any(row['label'].endswith(('writer-a', 'writer-b')) for row in label)
        assert len(list(root.glob('generation-*'))) == 2
    finally:
        for writer in writers:
            writer.join(timeout=3)
            if writer.is_alive():
                writer.terminate()
                writer.join(timeout=3)
        results.close()


def test_aba_cannot_revive_a_stale_writer(tmp_path, monkeypatch, capsys):
    inputs(tmp_path)
    for name in ('intervening', 'stale'):
        variant(tmp_path, name)
    assert export(tmp_path) == 0
    root, original = published(tmp_path)
    original_bytes = artifacts(root, original)
    render = process_render.render_process_artifacts

    def publish_then_restore(view):
        with monkeypatch.context() as nested:
            nested.setattr(process_render, 'render_process_artifacts', render)
            assert export(tmp_path, snapshot='intervening.json') == 0
            assert export(tmp_path) == 0
        capsys.readouterr()
        return render(view)

    monkeypatch.setattr(process_render, 'render_process_artifacts', publish_then_restore)
    assert export(tmp_path, snapshot='stale.json') == 3
    assert json.loads(capsys.readouterr().err)['code'] == 'EXPORT_CONFLICT'
    current = published(tmp_path)[1]
    assert current['view_fingerprint'] == original['view_fingerprint']
    assert current['generation'] != original['generation']
    assert artifacts(root, current) == artifacts(root, original) == original_bytes
    assert len(list(root.glob('generation-*'))) == 3


@pytest.mark.parametrize('failure,exit_code,diagnostic', [
    ('renderer', 2, 'PROCESS_MARKDOWN_LIMIT'),
    ('source', 3, 'EXPORT_INPUT_CHANGED'),
    ('timeout', 1, 'EXPORT_TIMEOUT'),
    ('cancel', 130, 'CANCELLED'),
    ('late_timeout', 1, 'EXPORT_TIMEOUT'),
    ('late_cancel', 130, 'CANCELLED'),
    ('late_source', 3, 'EXPORT_INPUT_CHANGED'),
    ('write', 1, 'EXPORT_IO_ERROR'),
    ('replace', 1, 'EXPORT_IO_ERROR'),
])
def test_failures_preserve_previous_generation(tmp_path, monkeypatch, capsys, failure, exit_code, diagnostic):
    inputs(tmp_path)
    variant(tmp_path, 'candidate')
    assert export(tmp_path) == 0
    capsys.readouterr()
    root, _ = published(tmp_path)
    prior = file_snapshot(root)
    candidate = tmp_path / 'candidate.json'
    expected = candidate.read_bytes()
    now = [0.0]
    monkeypatch.setattr('kgmaker.process_cli.time.monotonic', lambda: now[0])

    def fail_report(*args):
        raise process_render.ProcessMarkdownError('PROCESS_MARKDOWN_LIMIT')

    def fail_replace(*args, **kwargs):
        raise OSError('injected before manifest replacement')

    write_file = view_store._write_file

    def fail_when_staged(parent, name, raw, identities):
        write_file(parent, name, raw, identities)
        if name.startswith('.manifest-'):
            if failure == 'cancel':
                (tmp_path / 'cancel').touch()
            elif failure == 'timeout':
                now[0] = 2.0
            elif failure == 'source':
                candidate.write_bytes(expected + b'\n')
            elif failure == 'write':
                raise OSError('injected write failure after staging')

    same_file = view_store._same_file

    def stop_after_staged_checks(parent, name, identity):
        unchanged = same_file(parent, name, identity)
        if name == 'view.mmd':
            if failure == 'late_timeout':
                now[0] = 2.0
            elif failure == 'late_cancel':
                (tmp_path / 'cancel').touch()
            else:
                candidate.write_bytes(expected + b'\n')
        return unchanged

    if failure.startswith('late_'):
        monkeypatch.setattr(view_store, '_same_file', stop_after_staged_checks)
    elif failure == 'renderer':
        monkeypatch.setattr(process_render, '_markdown', fail_report)
    elif failure == 'replace':
        monkeypatch.setattr(view_store.os, 'replace', fail_replace)
    else:
        monkeypatch.setattr(view_store, '_write_file', fail_when_staged)
    assert export(tmp_path, '--timeout', '1', '--cancel-file', 'cancel', snapshot='candidate.json') == exit_code
    out, err = capsys.readouterr()
    assert not out and json.loads(err)['code'] == diagnostic
    assert file_snapshot(root) == prior
    assert candidate.read_bytes() == (expected + b'\n' if failure in {'source', 'late_source'} else expected)


def test_cancel_before_first_switch_leaves_no_artifact_paths(tmp_path, monkeypatch):
    inputs(tmp_path)
    replace = os.replace

    def stop(source, destination, **kwargs):
        if destination == 'manifest.json':
            raise KeyboardInterrupt
        return replace(source, destination, **kwargs)

    monkeypatch.setattr(view_store.os, 'replace', stop)
    assert export(tmp_path) == 130
    assert sorted(path.name for path in tmp_path.iterdir()) == ['process.json']


def test_interrupt_after_switch_reports_the_committed_manifest(tmp_path, capsys, monkeypatch):
    inputs(tmp_path)
    replace = os.replace

    def stop_after_replace(*args, **kwargs):
        replace(*args, **kwargs)
        raise KeyboardInterrupt

    monkeypatch.setattr(view_store.os, 'replace', stop_after_replace)
    assert export(tmp_path) == 0
    root, manifest = published(tmp_path)
    out, err = capsys.readouterr()
    assert json.loads(out) == manifest and not err
    assert len(artifacts(root, manifest)) == 3


@pytest.mark.parametrize('cleanup', ['temporary', 'destination'])
def test_post_commit_cleanup_does_not_cancel_published_export(tmp_path, capsys, monkeypatch, cleanup):
    inputs(tmp_path)
    destination = tmp_path / 'reports/process'
    committed = destination / 'manifest.json'
    unlink_owned = view_store._unlink_owned
    directory = view_store._directory
    interrupted = []

    def interrupt_unlink(parent, files):
        if committed.exists():
            raise KeyboardInterrupt
        unlink_owned(parent, files)

    @contextmanager
    def interrupt_close(parent, parts, created=None):
        with directory(parent, parts, created) as target:
            yield target
        if parts == ('reports', 'process') and committed.exists():
            interrupted.append(True)
            raise KeyboardInterrupt

    if cleanup == 'temporary':
        monkeypatch.setattr(view_store, '_unlink_owned', interrupt_unlink)
    else:
        monkeypatch.setattr(view_store, '_directory', interrupt_close)

    assert export(tmp_path) == 0
    root, manifest = published(tmp_path)
    out, err = capsys.readouterr()
    assert json.loads(out) == manifest and not err
    assert len(artifacts(root, manifest)) == 3
    assert interrupted == ([True] if cleanup == 'destination' else [])


@pytest.mark.parametrize('handoff', ['publisher', 'cli'])
def test_interrupt_after_publication_handoff_preserves_replacement(tmp_path, capsys, monkeypatch, handoff):
    source = inputs(tmp_path)
    variant(tmp_path, 'revision')
    revised = tmp_path / 'revision.json'
    source_bytes, revised_bytes = source.read_bytes(), revised.read_bytes()
    assert export(tmp_path) == 0
    capsys.readouterr()
    root, previous = published(tmp_path)
    previous_bytes = artifacts(root, previous)
    module, name = ((view_store, '_stage_and_switch') if handoff == 'publisher'
                    else (process_cli, 'publish_view_artifacts'))
    publish = getattr(module, name)
    interrupted = []

    def interrupt_handoff(*args, **kwargs):
        publish(*args, **kwargs)
        _, manifest = published(tmp_path)
        interrupted.append(manifest)
        assert manifest['generation'] != previous['generation']
        assert artifacts(root, manifest) != previous_bytes
        raise KeyboardInterrupt

    monkeypatch.setattr(module, name, interrupt_handoff)
    status = export(tmp_path, snapshot='revision.json')
    _, current = published(tmp_path)
    assert interrupted == [current]
    assert artifacts(root, previous) == previous_bytes
    assert source.read_bytes() == source_bytes and revised.read_bytes() == revised_bytes
    output = capsys.readouterr()
    if handoff == 'publisher':
        assert status == 0, output.err
        assert json.loads(output.out) == current and not output.err
    else:
        assert status == 1, output.err
        assert not output.out and json.loads(output.err) == {'code': 'EXPORT_RECEIPT_INTERRUPTED', 'exit_code': 1}

def test_interrupt_during_receipt_leaves_committed_manifest(tmp_path, capsys, monkeypatch):
    inputs(tmp_path)

    def interrupt_receipt(_):
        raise KeyboardInterrupt

    with monkeypatch.context() as interrupted:
        interrupted.setattr(process_cli.sys.stdout, 'write', interrupt_receipt)
        assert export(tmp_path) == 1

    root, manifest = published(tmp_path)
    out, err = capsys.readouterr()
    assert not out and json.loads(err)['code'] == 'EXPORT_RECEIPT_INTERRUPTED'
    assert len(artifacts(root, manifest)) == 3


def test_confirmed_holder_cannot_authorize_a_second_export(tmp_path, capsys, monkeypatch):
    inputs(tmp_path)
    variant(tmp_path, 'revision')
    holder = view_store.ViewPublication()
    monkeypatch.setattr(process_cli, 'ViewPublication', lambda: holder)
    assert export(tmp_path) == 0
    capsys.readouterr()
    root, active = published(tmp_path)
    prior = file_snapshot(root)
    paths = sorted(root.iterdir())
    writes = []

    def fail_write(parent, name, raw, owned):
        writes.append(name)
        raise OSError('injected before a second publication')

    monkeypatch.setattr(view_store, '_write_file', fail_write)
    assert export(tmp_path, snapshot='revision.json') == 2
    out, err = capsys.readouterr()
    assert not out and json.loads(err)['code'] == 'EXPORT_RECEIPT_ALREADY_SET'
    assert not writes and holder.manifest == published(tmp_path)[1] == active
    assert file_snapshot(root) == prior and sorted(root.iterdir()) == paths


def test_invalid_scope_and_untrusted_output_paths_fail_before_writes(tmp_path, capsys):
    source = inputs(tmp_path)
    unsafe = tmp_path / 'elsewhere'
    unsafe.mkdir()
    (tmp_path / 'link').symlink_to(unsafe, target_is_directory=True)
    original = file_snapshot(tmp_path)
    for target in ('../escape', str(tmp_path.parent / 'escape'), 'link/process', '.kgmaker/flows', '.git/export'):
        assert export(tmp_path, output=target) == 2
        assert json.loads(capsys.readouterr().err)['code'] == 'INVALID_EXPORT_PATH'
    assert export(tmp_path, '--expected-fingerprint', '0' * 64) == 3
    assert file_snapshot(tmp_path) == original
    invalid = partial_view().to_dict()
    invalid['technical_view']['provenance'][0]['scope'] = 'test'
    source.write_text(json.dumps(invalid), encoding='utf-8')
    before = file_snapshot(tmp_path)
    assert export(tmp_path) == 2
    assert file_snapshot(tmp_path) == before


def test_unknown_manifest_is_not_replaced(tmp_path, capsys):
    inputs(tmp_path)
    root = tmp_path / 'reports/process'
    root.mkdir(parents=True)
    (root / 'manifest.json').write_text('{"schema_version":42}', encoding='utf-8')
    before = file_snapshot(tmp_path)
    assert export(tmp_path) == 2
    assert json.loads(capsys.readouterr().err)['code'] == 'INVALID_EXPORT_MANIFEST'
    assert file_snapshot(tmp_path) == before


def test_output_symlink_substitution_cannot_escape_after_render(tmp_path, monkeypatch, capsys):
    inputs(tmp_path)
    variant(tmp_path, 'other')
    assert export(tmp_path) == 0
    capsys.readouterr()
    root, manifest = published(tmp_path)
    before = {path.relative_to(root): value for path, value in file_snapshot(root).items()}
    moved = tmp_path / 'previous'
    outside = tmp_path / 'outside'
    outside.mkdir()
    render = process_render.render_process_artifacts

    def substitute(view):
        result = render(view)
        root.rename(moved)
        root.symlink_to(outside, target_is_directory=True)
        return result

    monkeypatch.setattr(process_render, 'render_process_artifacts', substitute)
    assert export(tmp_path, snapshot='other.json') == 2
    assert json.loads(capsys.readouterr().err)['code'] == 'INVALID_EXPORT_PATH'
    assert {path.relative_to(moved): value for path, value in file_snapshot(moved).items()} == before
    assert artifacts(moved, manifest)
    assert not list(outside.iterdir())


def test_output_path_cannot_be_rebound_during_validation(tmp_path, monkeypatch, capsys):
    source = inputs(tmp_path)
    original = source.read_bytes()
    selected = tmp_path / 'reports' / 'process'
    selected.parent.mkdir()
    unrelated = tmp_path / 'unrelated'
    unrelated.mkdir()
    safe_path = view_store.safe_path

    def substitute_after_symlink_check(root, value):
        checked = safe_path(root, value)
        if checked == selected and not selected.is_symlink():
            selected.symlink_to(unrelated, target_is_directory=True)
            return checked.resolve()
        return checked

    monkeypatch.setattr(view_store, 'safe_path', substitute_after_symlink_check)
    assert export(tmp_path) == 2
    assert json.loads(capsys.readouterr().err)['code'] == 'INVALID_EXPORT_PATH'
    assert not list(unrelated.iterdir())
    assert source.read_bytes() == original


def test_staged_artifact_change_during_final_input_read_preserves_active(tmp_path, monkeypatch, capsys):
    inputs(tmp_path)
    variant(tmp_path, 'other')
    assert export(tmp_path) == 0
    capsys.readouterr()
    root, manifest = published(tmp_path)
    before = file_snapshot(root)
    active = root / manifest['artifacts']['mermaid']['path']
    read_snapshot = process_cli.read_export_snapshot
    changed = []

    def change_staged_artifact(*args):
        result = read_snapshot(*args)
        staged = [path for path in root.glob('generation-*/view.mmd') if path != active]
        if staged:
            path, = staged
            path.write_bytes(path.read_bytes() + b'%% changed after staging\n')
            changed.append(path)
        return result

    monkeypatch.setattr(process_cli, 'read_export_snapshot', change_staged_artifact)
    assert export(tmp_path, snapshot='other.json') == 3
    assert changed and json.loads(capsys.readouterr().err)['code'] == 'EXPORT_CONFLICT'
    assert file_snapshot(root) == before
