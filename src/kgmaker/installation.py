"""Content-aware lifecycle for files installed in target projects (T053)."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
from importlib.metadata import PackageNotFoundError, version

from .analysis_model import AnalysisError, read_json, safe_path

MANIFEST = '.kgmaker/install-manifest.json'
IGNORE_ENTRIES = (
    '.kgmaker/analyses/', '.kgmaker/graph.json', '.kgmaker/semantic-input.json',
    '.kgmaker/semantic-update.json', '.kgmaker/semantic-update.md',
    '.kgmaker/semantic-patch.json', '.kgmaker/semantic-extract.md',
    '.kgmaker/confluence-index.json', '.kgmaker/workflow/',
)


def bundled_files() -> dict[str, bytes]:
    from .cli import bundled_init_files
    from .artifact_templates import KINDS, defaults
    result = {p.as_posix(): text.encode('utf-8') for p, text in bundled_init_files().items()}
    for kind in sorted(KINDS):
        definition, content = defaults(kind)
        result[f'.kgmaker/templates/{kind}.json'] = _json(definition)
        result[f'.kgmaker/templates/{kind}.txt'] = content.encode('utf-8')
    return result


def _json(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True,
                       allow_nan=False) + '\n').encode('utf-8')


def _hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _version() -> str:
    try:
        return version('kgmaker')
    except PackageNotFoundError:
        from . import __version__
        return __version__


def _path(root: Path, name: str) -> Path:
    path = safe_path(root, name)
    for parent in path.parents:
        if parent == root:
            break
        if parent.exists() and not parent.is_dir():
            raise AnalysisError(f'Parent is not a directory: {name}')
    if path.exists() and not stat.S_ISREG(path.stat().st_mode):
        raise AnalysisError(f'Output is not a regular file: {name}')
    return path


def _load(root, allowed):
    path = _path(root, MANIFEST)
    if not path.exists():
        return None
    value = read_json(path)
    if (not isinstance(value, dict)
            or set(value) != {'schema_version', 'package_version', 'files', 'preserved', 'gitignore'}
            or type(value['schema_version']) is not int or value['schema_version'] != 1
            or not isinstance(value['package_version'], str)
            or not isinstance(value['files'], dict)
            or not isinstance(value['preserved'], list)):
        raise AnalysisError('Invalid installation manifest')
    for name, digest in value['files'].items():
        if name not in allowed or not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
            raise AnalysisError(f'Invalid managed file in installation manifest: {name}')
    if (any(not isinstance(p, str) or p not in allowed for p in value['preserved'])
            or len(set(value['preserved'])) != len(value['preserved'])
            or set(value['preserved']) & value['files'].keys()):
        raise AnalysisError('Invalid preserved files in installation manifest')
    ignore = value['gitignore']
    if (not isinstance(ignore, dict) or set(ignore) != {'added', 'created'}
            or not isinstance(ignore['added'], str) or type(ignore['created']) is not bool):
        raise AnalysisError('Invalid gitignore ownership in installation manifest')
    # The manifest is data, not permission to remove arbitrary ignore rules.
    if any(line not in (*IGNORE_ENTRIES, '', '# Local kgmaker index')
           for line in ignore['added'].splitlines()):
        raise AnalysisError('Invalid managed gitignore rules')
    return value


def _legacy_ignore(content):
    """Remove only exact historical generated lines, retaining other bytes."""
    return b''.join(line for line in content.splitlines(keepends=True)
                    if line.rstrip(b'\r\n').decode('utf-8') not in
                    (*IGNORE_ENTRIES, '# Local kgmaker index'))


def plan(root: Path, operation: str, *, force: bool = False):
    """Return writes/deletions and conflicts without creating any paths."""
    from .installation_history import KNOWN_HASHES
    current = bundled_files()
    allowed = set(current) | set(KNOWN_HASHES)
    manifest = _load(root, allowed)
    old = dict(manifest['files']) if manifest else {}
    preserved = set(manifest['preserved']) if manifest else set()
    contents = {}
    for name in sorted(allowed):
        path = _path(root, name)
        contents[name] = path.read_bytes() if path.exists() else None
    ignore_path = _path(root, '.gitignore')
    ignore_content = ignore_path.read_bytes() if ignore_path.exists() else None
    ignore = dict(manifest['gitignore']) if manifest else {'added': '', 'created': ignore_content is None}
    changes, conflicts = {}, []

    # Legacy adoption is limited to byte-identical known releases/current files.
    if manifest is None:
        for name, content in contents.items():
            if content is not None and (_hash(content) in KNOWN_HASHES.get(name, ())
                                        or content == current.get(name)):
                old[name] = _hash(content)
        if operation == 'uninstall' and not old and not (root / '.kgmaker').exists():
            return {}, [], set()
        if operation == 'upgrade' and not old and not (root / '.kgmaker').exists():
            raise AnalysisError('Project is not initialized; run kgmaker init first')

    legacy_installation = manifest is None and bool(old)

    for name in sorted(allowed):
        content, wanted = contents[name], current.get(name)
        if operation == 'init':
            if wanted is None:
                if content is not None and name not in old:
                    preserved.add(name)
                continue
            # Editable artifact pairs retain historical init behavior, even with force.
            if name.startswith('.kgmaker/templates/'):
                other = str(Path(name).with_suffix('.txt' if name.endswith('.json') else '.json'))
                if content is not None or contents.get(other) is not None:
                    if name not in old:
                        preserved.add(name)
                    continue
            if content is not None and not force:
                if name not in old:
                    preserved.add(name)
                continue
        elif operation == 'upgrade':
            # NOTES is a user-editable seed, not a generated integration template.
            if name == '.kgmaker/NOTES.md' and content is not None:
                continue
            if name in preserved:
                continue
            if content is not None and content != wanted and _hash(content) != old.get(name) and not force:
                conflicts.append(name)
                continue
            if wanted is None and name not in old and content is None:
                continue
        else:  # uninstall: data under .kgmaker is removed as a single tree below.
            if name.startswith('.kgmaker/') or name in preserved or content is None:
                continue
            if _hash(content) != old.get(name) and not force:
                conflicts.append(name)
                continue
            wanted = None
        if content != wanted:
            changes[name] = wanted
        if wanted is not None:
            old[name] = _hash(wanted)
            preserved.discard(name)
        else:
            old.pop(name, None)

    if operation == 'uninstall':
        if ignore_content is not None:
            if manifest:
                added = ignore['added'].encode('utf-8')
                if added and ignore_content.count(added) != 1:
                    conflicts.append('.gitignore (managed block changed; restore it before uninstall)')
                    remaining = ignore_content
                else:
                    remaining = ignore_content.replace(added, b'', 1) if added else ignore_content
            else:
                remaining = _legacy_ignore(ignore_content)
            if remaining != ignore_content:
                changes['.gitignore'] = None if not remaining and (ignore['created'] or not manifest) else remaining
        data = safe_path(root, '.kgmaker')
        if data.exists():
            if not data.is_dir():
                raise AnalysisError('.kgmaker is not a directory')
            changes['.kgmaker'] = None
    else:
        if manifest is None:
            existing = ignore_content or b''
            # With legacy installations, old generated rules have no ownership
            # metadata. Adopt just those exact lines, preserving everything else.
            if operation == 'upgrade' or legacy_installation:
                existing = _legacy_ignore(existing)
            missing = [line for line in IGNORE_ENTRIES if line.encode() not in existing.splitlines()]
            added = ((b'\n' if existing and not existing.endswith(b'\n') else b'')
                     + b'\n# Local kgmaker index\n' + '\n'.join(missing).encode() + b'\n') if missing else b''
            updated = existing + added
            ignore['added'] = added.decode('utf-8')
            if updated != ignore_content:
                changes['.gitignore'] = updated
        elif operation == 'upgrade':
            existing = ignore_content or b''
            added = ignore['added'].encode('utf-8')
            if added and ignore_content is not None and existing.count(added) != 1:
                conflicts.append('.gitignore (managed block changed; restore it before upgrade)')
            else:
                missing = [line for line in IGNORE_ENTRIES if line.encode() not in existing.splitlines()]
                if missing:
                    extra = '\n'.join(missing).encode() + b'\n'
                    if added and ignore_content is not None:
                        updated = existing.replace(added, added + extra, 1)
                        ignore['added'] += extra.decode('utf-8')
                    else:
                        block = (b'\n' if existing and not existing.endswith(b'\n') else b'')
                        block += b'\n# Local kgmaker index\n' + extra
                        updated = existing + block
                        ignore['added'] = block.decode('utf-8')
                    changes['.gitignore'] = updated
        value = {'schema_version': 1, 'package_version': _version(), 'files': old,
                 'preserved': sorted(preserved), 'gitignore': ignore}
        # Plain repeated init must not silently claim a new package version.
        if manifest and operation == 'init':
            value['package_version'] = manifest['package_version']
        encoded = _json(value)
        if not manifest or encoded != (root / MANIFEST).read_bytes():
            changes[MANIFEST] = encoded
    return changes, conflicts, preserved


def _publish(root: Path, changes):
    """Stage all writes, then rename with rollback on catchable publication errors.

    Requires a quiescent target. Backups are retained if rollback itself fails.
    This does not promise crash atomicity across multiple files.
    """
    if not changes:
        return
    scratch = Path(tempfile.mkdtemp(prefix='.kgmaker-lifecycle-', dir=root))
    moved, made_dirs = [], []
    cleanup = True
    try:
        staged = {}
        for i, (name, content) in enumerate(changes.items()):
            if content is not None:
                path = scratch / f'new-{i}'
                path.write_bytes(content)
                target = root / name
                if target.exists():
                    path.chmod(stat.S_IMODE(target.stat().st_mode))
                staged[name] = path
        try:
            for i, (name, content) in enumerate(changes.items()):
                target = safe_path(root, name)
                missing = []
                parent = target.parent
                while not parent.exists():
                    missing.append(parent)
                    parent = parent.parent
                for directory in reversed(missing):
                    directory.mkdir()
                    made_dirs.append(directory)
                backup = scratch / f'old-{i}'
                existed = target.exists()
                if existed:
                    os.replace(target, backup)
                moved.append((target, backup, existed))
                if content is not None:
                    os.replace(staged[name], target)
        except BaseException:
            try:
                for target, backup, existed in reversed(moved):
                    if target.exists():
                        target.unlink()
                    if existed:
                        os.replace(backup, target)
                for directory in reversed(made_dirs):
                    directory.rmdir()
            except BaseException:
                cleanup = False
                print(f'Recovery backups retained in {scratch}', file=sys.stderr)
                raise
            raise
    finally:
        if cleanup:
            try:
                shutil.rmtree(scratch)
            except OSError as error:
                raise AnalysisError(f'Changes applied, but backup cleanup failed at {scratch}: {error}') from error
    # Remove only empty parents of deleted files, never foreign contents.
    for name, content in changes.items():
        if content is None:
            parent = (root / name).parent
            while parent != root:
                try:
                    parent.rmdir()
                except OSError:
                    break
                parent = parent.parent


def run(root: Path, operation: str, *, force=False, dry_run=False) -> int:
    if operation not in {'init', 'upgrade', 'uninstall'}:
        raise ValueError(operation)
    root = root.resolve()
    try:
        if not root.is_dir():
            raise AnalysisError('Project root must be an existing directory')
        changes, conflicts, preserved = plan(root, operation, force=force)
        for name, content in changes.items():
            print(f'{"REMOVE" if content is None else "WRITE"}: {name}')
        for name in sorted(preserved):
            if (root / name).exists():
                print(f'PRESERVE (pre-existing): {name}')
        if conflicts:
            print('Conflicts; no files changed:\n  ' + '\n  '.join(conflicts), file=sys.stderr)
            print('Merge local edits or explicitly use --force for managed files.', file=sys.stderr)
            return 2
        if dry_run:
            print('Dry run; no files changed.')
            return 0
        _publish(root, changes)
        print({'init': 'Initialized kgmaker in this repository.',
               'upgrade': 'Upgraded project files to installed kgmaker ' + _version() + '.',
               'uninstall': 'Removed kgmaker project integration and .kgmaker data.'}[operation])
        if operation == 'init':
            print('Next: kgmaker scan')
        return 0
    except (AnalysisError, OSError, UnicodeError) as error:
        print(f'Cannot {operation} kgmaker: {error}', file=sys.stderr)
        return 2
