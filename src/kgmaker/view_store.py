"""Atomic publication of immutable sets of derived view artifacts."""
from contextlib import contextmanager, suppress
import errno
from hashlib import sha256
import os
from pathlib import Path
import re
import stat
from uuid import uuid4

from .analysis_model import AnalysisError, canonical, decode_json, safe_path


_FILENAMES = {'json': 'view.json', 'markdown': 'view.md', 'mermaid': 'view.mmd'}
_MAX_ARTIFACT_BYTES = 4_000_000
_MAX_MANIFEST_BYTES = 4096
_MANIFEST = 'manifest.json'


class ViewExportError(ValueError):
    def __init__(self, code, exit_code=2):
        self.code = code
        self.exit_code = exit_code
        super().__init__(code)


def export_path(root, path):
    """Resolve an explicit path against the coordinator without following symlinks."""
    try:
        relative = path.relative_to(root) if path.is_absolute() else path
        if not relative.parts:
            raise ViewExportError('INVALID_EXPORT_PATH')
        safe_path(root, relative.as_posix())
        # Descriptor traversal must still check the caller's original path.
        return relative
    except (ValueError, OSError, RuntimeError):
        raise ViewExportError('INVALID_EXPORT_PATH') from None


@contextmanager
def _root_directory(root):
    if os.name != 'posix' or not hasattr(os, 'O_NOFOLLOW') or not hasattr(os, 'O_DIRECTORY'):
        raise ViewExportError('EXPORT_PLATFORM_UNAVAILABLE')
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        yield fd
    finally:
        os.close(fd)


@contextmanager
def _directory(parent, parts, created=None):
    fd = os.dup(parent)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        for part in parts:
            try:
                child = os.open(part, flags, dir_fd=fd)
            except FileNotFoundError:
                if created is None:
                    raise
                made = False
                try:
                    os.mkdir(part, dir_fd=fd)
                    made = True
                except FileExistsError:
                    pass
                child = os.open(part, flags, dir_fd=fd)
                if made:
                    try:
                        identity = os.fstat(child)
                        created.append((os.dup(fd), part, identity))
                    except BaseException:
                        os.close(child)
                        raise
            os.close(fd)
            fd = child
    except OSError as error:
        os.close(fd)
        if error.errno in {errno.ENOTDIR, errno.ELOOP}:
            raise ViewExportError('INVALID_EXPORT_PATH') from None
        raise
    except BaseException:
        os.close(fd)
        raise
    try:
        yield fd
    finally:
        os.close(fd)


def _identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _read_file(parent, name, limit, *, single_link=False):
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    with os.fdopen(os.open(name, flags, dir_fd=parent), 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or (single_link and before.st_nlink != 1):
            raise ViewExportError('INVALID_EXPORT_FILE')
        if before.st_size > limit:
            raise ViewExportError('EXPORT_SIZE_LIMIT')
        raw = stream.read(limit + 1)
        if len(raw) > limit:
            raise ViewExportError('EXPORT_SIZE_LIMIT')
        if _identity(before) != _identity(os.fstat(stream.fileno())):
            raise ViewExportError('EXPORT_FILE_CHANGED', 3)
    return raw, _identity(before)


def read_export_snapshot(root, relative, limit):
    """Read a confined input's bounded bytes and the stamp of those bytes."""
    relative = export_path(root, relative)
    with _root_directory(root) as base, _directory(base, relative.parts[:-1]) as parent:
        return _read_file(parent, relative.name, limit)


def export_snapshot_stamp(root, relative):
    """Check an already validated relative input path without reading its bytes."""
    with _root_directory(root) as base, _directory(base, relative.parts[:-1]) as parent:
        return _identity(os.stat(relative.name, dir_fd=parent, follow_symlinks=False))


def _manifest(parent, kind):
    try:
        raw, identity = _read_file(parent, _MANIFEST, _MAX_MANIFEST_BYTES, single_link=True)
    except FileNotFoundError:
        return None, None
    try:
        value = decode_json(raw.decode('utf-8'), 'export manifest')
    except (AnalysisError, UnicodeError):
        raise ViewExportError('INVALID_EXPORT_MANIFEST') from None
    if (not isinstance(value, dict)
            or set(value) != {'schema_version', 'view_kind', 'generation', 'view_fingerprint', 'artifacts'}
            or type(value['schema_version']) is not int or value['schema_version'] != 1
            or value['view_kind'] != kind or not _hex(value['generation'], 32)
            or not _hex(value['view_fingerprint'], 64) or not isinstance(value['artifacts'], dict)
            or value['artifacts'].keys() != _FILENAMES.keys()):
        raise ViewExportError('INVALID_EXPORT_MANIFEST')
    directory = 'generation-' + value['generation']
    try:
        with _directory(parent, (directory,)) as generation:
            for format, filename in _FILENAMES.items():
                artifact = value['artifacts'][format]
                if (not isinstance(artifact, dict) or set(artifact) != {'path', 'sha256'}
                        or artifact['path'] != f'{directory}/{filename}' or not _hex(artifact['sha256'], 64)):
                    raise ViewExportError('INVALID_EXPORT_MANIFEST')
                payload, _ = _read_file(generation, filename, _MAX_ARTIFACT_BYTES, single_link=True)
                if sha256(payload).hexdigest() != artifact['sha256']:
                    raise ViewExportError('INVALID_EXPORT_MANIFEST')
    except FileNotFoundError:
        raise ViewExportError('INVALID_EXPORT_MANIFEST') from None
    return value, (raw, identity)


def _hex(value, length):
    return isinstance(value, str) and re.fullmatch(rf'[0-9a-f]{{{length}}}', value) is not None


def _same_entry(parent, name, identity):
    try:
        return os.path.samestat(identity, os.stat(name, dir_fd=parent, follow_symlinks=False))
    except FileNotFoundError:
        return False


def _same_file(parent, name, identity):
    try:
        return _identity(identity) == _identity(os.stat(name, dir_fd=parent, follow_symlinks=False))
    except FileNotFoundError:
        return False


def _write_file(parent, name, raw, owned):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    with os.fdopen(os.open(name, flags, 0o600, dir_fd=parent), 'wb') as stream:
        owned[name] = os.fstat(stream.fileno())
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
        owned[name] = os.fstat(stream.fileno())


def _unlink_owned(parent, files):
    for name, identity in files.items():
        with suppress(OSError):
            if _same_entry(parent, name, identity):
                os.unlink(name, dir_fd=parent)


def _stage_and_switch(parent, generation, files, manifest, check_current, guard):
    directory = 'generation-' + generation
    temporary = '.manifest-' + generation
    raw = (canonical(manifest) + '\n').encode('utf-8')
    temporary_files = {}
    artifact_files = {}
    staging_identity = None
    switched = False
    try:
        os.mkdir(directory, 0o700, dir_fd=parent)
        staging_identity = os.stat(directory, dir_fd=parent, follow_symlinks=False)
        with _directory(parent, (directory,)) as staging:
            if not os.path.samestat(staging_identity, os.fstat(staging)):
                raise ViewExportError('EXPORT_CONFLICT', 3)
            try:
                for format, filename in _FILENAMES.items():
                    _write_file(staging, filename, files[format], artifact_files)
                os.fsync(staging)
                _write_file(parent, temporary, raw, temporary_files)
                os.fsync(parent)
                _, source_stamp = check_current()
                if (not _same_entry(parent, directory, staging_identity)
                        or not _same_file(parent, temporary, temporary_files[temporary])
                        or any(not _same_file(staging, name, info) for name, info in artifact_files.items())):
                    raise ViewExportError('EXPORT_CONFLICT', 3)
                guard(source_stamp)
                try:
                    os.replace(temporary, _MANIFEST, src_dir_fd=parent, dst_dir_fd=parent)
                    switched = True
                except (KeyboardInterrupt, OSError):
                    # A signal can arrive after the rename has committed but
                    # before the call returns. The manifest inode proves it.
                    if not _same_entry(parent, _MANIFEST, temporary_files[temporary]):
                        raise
                    switched = True
            finally:
                if not switched:
                    _unlink_owned(staging, artifact_files)
    except (KeyboardInterrupt, OSError):
        if not switched:
            raise
    finally:
        if not switched:
            _unlink_owned(parent, temporary_files)
            with suppress(OSError):
                if staging_identity is not None and _same_entry(parent, directory, staging_identity):
                    os.rmdir(directory, dir_fd=parent)


def publish_view_artifacts(root: Path, output: Path, kind, render, *, checkpoint, verify_input, verify_input_stamp):
    """Render then switch one manifest under an optimistic, destination-local CAS."""
    output = export_path(root, output)
    if any(part.casefold() in {'.git', '.kgmaker'} for part in output.parts):
        raise ViewExportError('INVALID_EXPORT_PATH')
    created = []
    keep_output = False
    receipt = None
    try:
        with _root_directory(root) as base:
            from fcntl import LOCK_EX, LOCK_NB, flock

            try:
                with _directory(base, output.parts) as previous:
                    directory = os.fstat(previous)
                    _, expected = _manifest(previous, kind)
            except FileNotFoundError:
                directory, expected = None, None

            checkpoint()
            fingerprint, files = render()
            files = {format: text.encode('utf-8') for format, text in files.items()}
            if files.keys() != _FILENAMES.keys() or any(len(raw) > _MAX_ARTIFACT_BYTES for raw in files.values()):
                raise ViewExportError('EXPORT_SIZE_LIMIT')
            hashes = {format: sha256(raw).hexdigest() for format, raw in files.items()}
            checkpoint()
            verify_input()
            try:
                with _directory(base, output.parts, created) as target:
                    try:
                        flock(target, LOCK_EX | LOCK_NB)
                    except BlockingIOError:
                        # A concurrent owner may be using a just-created directory.
                        keep_output = True
                        raise ViewExportError('EXPORT_CONFLICT', 3) from None

                    def check_current():
                        checkpoint()
                        value, token = _manifest(target, kind)
                        if token != expected:
                            raise ViewExportError('EXPORT_CONFLICT', 3)
                        return value, verify_input()

                    def guard(source_stamp):
                        if not os.path.samestat(os.fstat(base), root.stat(follow_symlinks=False)):
                            raise ViewExportError('EXPORT_CONFLICT', 3)
                        with _directory(base, output.parts) as current:
                            identity = os.fstat(current)
                            if (not os.path.samestat(identity, os.fstat(target))
                                    or (directory is not None and not os.path.samestat(directory, identity))):
                                raise ViewExportError('EXPORT_CONFLICT', 3)
                        try:
                            manifest_stamp = _identity(os.stat(_MANIFEST, dir_fd=target, follow_symlinks=False))
                        except FileNotFoundError:
                            manifest_stamp = None
                        if manifest_stamp != (None if expected is None else expected[1]):
                            raise ViewExportError('EXPORT_CONFLICT', 3)
                        verify_input_stamp(source_stamp)
                        checkpoint()

                    active, source_stamp = check_current()
                    guard(source_stamp)
                    if (active is not None and active['view_fingerprint'] == fingerprint
                            and {key: item['sha256'] for key, item in active['artifacts'].items()} == hashes):
                        receipt = active
                        return receipt
                    generation = uuid4().hex
                    manifest = {
                        'schema_version': 1,
                        'view_kind': kind,
                        'generation': generation,
                        'view_fingerprint': fingerprint,
                        'artifacts': {
                            format: {'path': f'generation-{generation}/{filename}', 'sha256': hashes[format]}
                            for format, filename in _FILENAMES.items()
                        },
                    }
                    _stage_and_switch(target, generation, files, manifest, check_current, guard)
                    receipt = manifest
                    return receipt
            finally:
                for parent, name, identity in reversed(created):
                    try:
                        if receipt is None and not keep_output and _same_entry(parent, name, identity):
                            os.rmdir(name, dir_fd=parent)
                    except OSError:
                        pass
                    finally:
                        os.close(parent)
    except KeyboardInterrupt:
        # Once published, an interrupted descriptor close cannot cancel it.
        if receipt is None:
            raise
        return receipt
