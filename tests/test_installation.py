"""Target installation lifecycle; all mutations stay in isolated projects."""
import json
import os
from pathlib import Path

import pytest

from kgmaker import installation as install
from kgmaker.cli import init, main


def snapshot(root):
    return {p.relative_to(root).as_posix():
            ('link', os.readlink(p)) if p.is_symlink() else
            ('dir',) if p.is_dir() else
            (p.read_bytes(), p.stat().st_mtime_ns, p.stat().st_mode)
            for p in root.rglob('*')}


def manifest(root):
    return json.loads((root / install.MANIFEST).read_text())


def test_manifest_tracks_only_written_files_and_init_is_idempotent(tmp_path):
    foreign = tmp_path / '.github/copilot-instructions.md'
    foreign.parent.mkdir()
    foreign.write_text('team instructions')
    (tmp_path / '.gitignore').write_bytes(b'build/\r\n')
    assert init(tmp_path) == 0
    data = manifest(tmp_path)
    assert foreign.relative_to(tmp_path).as_posix() in data['preserved']
    assert '.github/copilot-instructions.md' not in data['files']
    for name, digest in data['files'].items():
        assert digest == install._hash((tmp_path / name).read_bytes())
    before = snapshot(tmp_path)
    assert init(tmp_path) == 0
    assert snapshot(tmp_path) == before


def test_upgrade_all_categories_retirement_missing_files_and_repeat(tmp_path, monkeypatch):
    assert init(tmp_path) == 0
    original = install.bundled_files()
    upgraded = {name: content + b'\nNew release\n' for name, content in original.items()}
    retired = '.github/agents/kgmaker-extract.agent.md'
    upgraded.pop(retired)
    upgraded['.kgmaker/NOTES.md'] = original['.kgmaker/NOTES.md']
    new = '.github/agents/kgmaker-new.agent.md'
    upgraded[new] = b'new agent'
    (tmp_path / '.github/hooks/kgmaker.json').unlink()
    (tmp_path / '.kgmaker/graph.json').write_bytes(b'graph retained byte for byte')
    monkeypatch.setattr(install, 'bundled_files', lambda: upgraded)
    monkeypatch.setattr(install, '_version', lambda: '9.0.0')
    assert install.run(tmp_path, 'upgrade') == 0
    assert not (tmp_path / retired).exists()
    assert manifest(tmp_path)['package_version'] == '9.0.0'
    assert all((tmp_path / name).read_bytes() == text for name, text in upgraded.items())
    assert (tmp_path / '.kgmaker/graph.json').read_bytes() == b'graph retained byte for byte'
    before = snapshot(tmp_path)
    assert install.run(tmp_path, 'upgrade') == 0
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('command', ['upgrade', 'uninstall'])
def test_conflict_is_global_force_is_explicit(tmp_path, command, monkeypatch):
    assert init(tmp_path) == 0
    path = tmp_path / '.agents/skills/kgmaker-context/SKILL.md'
    path.write_bytes(b'local customization')
    current = install.bundled_files()
    current['.github/agents/kgmaker.agent.md'] += b'\nnew release'
    monkeypatch.setattr(install, 'bundled_files', lambda: current)
    before = snapshot(tmp_path)
    assert install.run(tmp_path, command) == 2
    assert snapshot(tmp_path) == before
    assert install.run(tmp_path, command, force=True) == 0
    if command == 'upgrade':
        assert path.read_bytes() == current['.agents/skills/kgmaker-context/SKILL.md']
    else:
        assert not path.exists()
        assert not (tmp_path / '.kgmaker').exists()


@pytest.mark.parametrize('command', ['upgrade', 'uninstall'])
def test_dry_run_and_conflicting_dry_run_never_write(tmp_path, command, monkeypatch):
    assert init(tmp_path) == 0
    current = install.bundled_files()
    current['.github/agents/kgmaker.agent.md'] += b'\nnew release'
    monkeypatch.setattr(install, 'bundled_files', lambda: current)
    before = snapshot(tmp_path)
    assert install.run(tmp_path, command, dry_run=True) == 0
    assert snapshot(tmp_path) == before
    (tmp_path / '.github/agents/kgmaker.agent.md').write_bytes(b'local')
    before = snapshot(tmp_path)
    assert install.run(tmp_path, command, dry_run=True) == 2
    assert install.run(tmp_path, command, dry_run=True, force=True) == 0
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('ignore', [None, b'', b'build/\r\n', b'build/', b'.kgmaker/graph.json\nother/\n'])
def test_uninstall_roundtrip_preserves_foreign_files_and_ignore_bytes(tmp_path, ignore):
    foreign = {
        '.github/copilot-instructions.md': b'ours',
        '.github/agents/custom.agent.md': b'ours',
        '.agents/skills/kgmaker-context/custom.txt': b'ours',
        '.junie/commands/ours.md': b'ours',
        'src/app.py': b'print(1)',
        '.codex/config.toml': b'ours',
    }
    if ignore is not None:
        foreign['.gitignore'] = ignore
    for name, content in foreign.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    assert init(tmp_path) == 0
    (tmp_path / '.kgmaker/NOTES.md').write_text('user notes are part of removed data')
    (tmp_path / '.kgmaker/graph.json').write_bytes(b'graph')
    assert install.run(tmp_path, 'uninstall') == 0
    assert {p.relative_to(tmp_path).as_posix(): p.read_bytes()
            for p in tmp_path.rglob('*') if p.is_file()} == foreign
    before = snapshot(tmp_path)
    # No installation left: foreign instructions must not become legacy conflicts.
    assert install.run(tmp_path, 'uninstall') == 0
    assert snapshot(tmp_path) == before


def test_gitignore_later_edits_survive_and_managed_block_conflicts(tmp_path):
    assert init(tmp_path) == 0
    path = tmp_path / '.gitignore'
    path.write_bytes(path.read_bytes() + b'new-user-rule\n')
    assert install.run(tmp_path, 'uninstall') == 0
    assert path.read_bytes() == b'new-user-rule\n'
    assert init(tmp_path) == 0
    path.write_text(path.read_text().replace('.kgmaker/graph.json', '.kgmaker/my-custom-rule'))
    before = snapshot(tmp_path)
    assert install.run(tmp_path, 'uninstall', force=True) == 2
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('command', ['upgrade', 'uninstall'])
def test_legacy_known_hashes_and_retired_files(tmp_path, command, monkeypatch):
    from kgmaker.installation_history import KNOWN_HASHES
    assert init(tmp_path) == 0
    (tmp_path / install.MANIFEST).unlink()
    retired = tmp_path / '.junie/commands/kgmaker.md'
    retired.write_bytes(b'known retired command')
    monkeypatch.setitem(KNOWN_HASHES, '.junie/commands/kgmaker.md',
                        [install._hash(retired.read_bytes())])
    # Historical init ignore layout with unrelated rules.
    (tmp_path / '.gitignore').write_text('user-rule\n\n# Local kgmaker index\n' + '\n'.join(install.IGNORE_ENTRIES) + '\n')
    current = install.bundled_files()
    current['.github/hooks/kgmaker.json'] += b'\n'
    monkeypatch.setattr(install, 'bundled_files', lambda: current)
    assert install.run(tmp_path, command) == 0
    assert not retired.exists()
    if command == 'upgrade':
        assert manifest(tmp_path)['schema_version'] == 1
        assert (tmp_path / '.github/hooks/kgmaker.json').read_bytes() == current['.github/hooks/kgmaker.json']
        assert install.run(tmp_path, 'uninstall') == 0
    assert (tmp_path / '.gitignore').read_text() == 'user-rule\n\n'
    assert not (tmp_path / '.kgmaker').exists()


def test_unknown_legacy_content_is_not_adopted_by_name(tmp_path):
    assert init(tmp_path) == 0
    (tmp_path / install.MANIFEST).unlink()
    (tmp_path / '.github/agents/kgmaker.agent.md').write_bytes(b'unknown older release or user edits')
    before = snapshot(tmp_path)
    for command in ('upgrade', 'uninstall'):
        assert install.run(tmp_path, command) == 2
        assert snapshot(tmp_path) == before


@pytest.mark.parametrize('command', ['init', 'upgrade', 'uninstall'])
@pytest.mark.parametrize('invalid', ['version', 'path', 'hash', 'json', 'duplicate', 'ignore'])
def test_invalid_manifest_zero_mutation_even_with_force(tmp_path, command, invalid):
    assert init(tmp_path) == 0
    data = manifest(tmp_path)
    if invalid == 'version':
        data['schema_version'] = True
    elif invalid == 'path':
        data['files']['../outside'] = 'a' * 64
    elif invalid == 'hash':
        data['files'][next(iter(data['files']))] = []
    elif invalid == 'ignore':
        data['gitignore']['added'] = 'user-rule\n'
    content = '{' if invalid == 'json' else json.dumps(data)
    if invalid == 'duplicate':
        content = content.replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1')
    (tmp_path / install.MANIFEST).write_text(content)
    before = snapshot(tmp_path)
    assert install.run(tmp_path, command, force=True) == 2
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('command', ['init', 'upgrade', 'uninstall'])
@pytest.mark.parametrize('relative', ['.github/hooks', '.gitignore', '.kgmaker', '.kgmaker/templates/filename.txt'])
def test_symlink_collision_preflight(tmp_path, command, relative):
    root, outside = tmp_path / 'root', tmp_path / 'outside'
    root.mkdir()
    outside.write_bytes(b'untouched')
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.symlink_to(outside)
    before = snapshot(tmp_path)
    assert install.run(root, command, force=True) == 2
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('command', ['init', 'upgrade', 'uninstall'])
def test_publication_failure_rolls_back_files_modes_mtimes_and_dirs(tmp_path, command, monkeypatch):
    if command != 'init':
        assert init(tmp_path) == 0
        current = {name: text + b'\nnew' for name, text in install.bundled_files().items()}
        monkeypatch.setattr(install, 'bundled_files', lambda: current)
    (tmp_path / '.gitignore').write_bytes(b'user-rule\n' + (tmp_path / '.gitignore').read_bytes()
                                        if (tmp_path / '.gitignore').exists() else b'user-rule\n')
    before = snapshot(tmp_path)
    real_replace = os.replace
    calls = 0
    def fail_once(src, dst):
        nonlocal calls
        calls += 1
        if calls == 5:
            raise OSError('injected publication error')
        return real_replace(src, dst)
    monkeypatch.setattr(install.os, 'replace', fail_once)
    assert install.run(tmp_path, command) == 2
    assert calls >= 5
    assert snapshot(tmp_path) == before


def test_uninstall_data_tree_rename_failure_restores_external_files(tmp_path, monkeypatch):
    assert init(tmp_path) == 0
    before = snapshot(tmp_path)
    real_replace = os.replace
    def fail_tree(src, dst):
        if Path(src) == tmp_path / '.kgmaker':
            raise OSError('data tree locked')
        return real_replace(src, dst)
    monkeypatch.setattr(install.os, 'replace', fail_tree)
    assert install.run(tmp_path, 'uninstall') == 2
    assert snapshot(tmp_path) == before


def test_cli_other_cwd_and_uninitialized_upgrade(tmp_path, monkeypatch):
    root = tmp_path / 'target'
    root.mkdir()
    monkeypatch.chdir(tmp_path)
    for command, code in [('upgrade', 2), ('init', 0), ('upgrade', 0), ('uninstall', 0)]:
        monkeypatch.setattr('sys.argv', ['kgmaker', command, '--root', str(root)])
        with pytest.raises(SystemExit) as result:
            main()
        assert result.value.code == code
    assert not (tmp_path / '.kgmaker').exists()
    assert not list(root.iterdir())


def test_upgrade_preserves_notes_and_preexisting_files_even_with_force(tmp_path, monkeypatch):
    path = tmp_path / '.github/copilot-instructions.md'
    path.parent.mkdir()
    path.write_bytes(b'foreign instructions')
    assert init(tmp_path) == 0
    notes = tmp_path / '.kgmaker/NOTES.md'
    notes.write_bytes(b'user knowledge')
    before = snapshot(tmp_path)
    changed = install.bundled_files()
    changed['.github/copilot-instructions.md'] += b'new'
    changed['.kgmaker/NOTES.md'] += b'new'
    monkeypatch.setattr(install, 'bundled_files', lambda: changed)
    assert install.run(tmp_path, 'upgrade', force=True) == 0
    assert snapshot(tmp_path) == before


def test_upgrade_adds_new_ignore_rule_and_uninstall_preserves_others(tmp_path, monkeypatch):
    (tmp_path / '.gitignore').write_bytes(b'ours/\n')
    assert init(tmp_path) == 0
    monkeypatch.setattr(install, 'IGNORE_ENTRIES', (*install.IGNORE_ENTRIES, '.kgmaker/new-cache/'))
    assert install.run(tmp_path, 'upgrade') == 0
    assert b'.kgmaker/new-cache/' in (tmp_path / '.gitignore').read_bytes()
    assert install.run(tmp_path, 'uninstall') == 0
    assert (tmp_path / '.gitignore').read_bytes() == b'ours/\n'


def test_repeated_init_of_legacy_still_allows_upgrade(tmp_path, monkeypatch):
    assert init(tmp_path) == 0
    (tmp_path / install.MANIFEST).unlink()
    assert init(tmp_path) == 0
    current = install.bundled_files()
    current['.github/hooks/kgmaker.json'] += b'\n'
    monkeypatch.setattr(install, 'bundled_files', lambda: current)
    assert install.run(tmp_path, 'upgrade') == 0
    assert (tmp_path / '.github/hooks/kgmaker.json').read_bytes() == current['.github/hooks/kgmaker.json']


def test_uninstall_does_not_follow_runtime_data_symlinks(tmp_path):
    root = tmp_path / 'root'
    root.mkdir()
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'source.py').write_bytes(b'source')
    assert init(root) == 0
    (root / '.kgmaker/external').symlink_to(outside, target_is_directory=True)
    assert install.run(root, 'uninstall') == 0
    assert (outside / 'source.py').read_bytes() == b'source'


def test_init_preserves_half_installed_artifact_pair(tmp_path):
    path = tmp_path / '.kgmaker/templates/analysis.txt'
    path.parent.mkdir(parents=True)
    path.write_bytes(b'custom')
    assert init(tmp_path, force=True) == 0
    assert not path.with_suffix('.json').exists()
    assert path.read_bytes() == b'custom'


@pytest.mark.parametrize('prefix', [b'', b'user-rule\r\n'])
@pytest.mark.parametrize('upgrade', [False, True])
def test_legacy_init_adopts_ignore_rules_for_uninstall(tmp_path, prefix, upgrade):
    assert init(tmp_path) == 0
    (tmp_path / install.MANIFEST).unlink()
    ignore = tmp_path / '.gitignore'
    ignore.write_bytes(prefix + ('\n'.join(install.IGNORE_ENTRIES) + '\n').encode())
    assert init(tmp_path) == 0
    if upgrade:
        assert install.run(tmp_path, 'upgrade') == 0
    assert install.run(tmp_path, 'uninstall') == 0
    assert ignore.read_bytes() == prefix
