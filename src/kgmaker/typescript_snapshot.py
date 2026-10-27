"""Replay captured compiler filesystem observations; never resolve a TS module."""
from __future__ import annotations

import os
from pathlib import Path

from .analysis_model import file_hash
from .worker_protocol import WorkerError

SNAPSHOT_VERSION = 'typescript-input-discovery-1'
MAX_RECORDS = 20000
MAX_ENTRIES = 100000


def _invalid():
    raise WorkerError('Malformed or unsupported TypeScript input discovery snapshot', 'INVALID_PROTOCOL')


def _absolute(value):
    if not isinstance(value, str) or not value or len(value) > 32768 or '\0' in value or not Path(value).is_absolute():
        _invalid()
    return value


def validate_capture(project):
    if not isinstance(project, dict):
        _invalid()
    data = project.get('input_discovery')
    if (not isinstance(data, dict) or set(data) != {'version', 'case_sensitive', 'observations', 'directories'}
            or type(data['version']) is not int or data['version'] != 1 or type(data['case_sensitive']) is not bool):
        _invalid()
    records, directories, files = data['observations'], data['directories'], project.get('input_files')
    if any(not isinstance(items, list) for items in (records, directories, files)) or len(records) + len(directories) > MAX_RECORDS or not files or len(files) > MAX_RECORDS:
        _invalid()
    seen = set()
    for item in files:
        if not isinstance(item, dict) or set(item) != {'path', 'sha256'}:
            _invalid()
        path = _absolute(item['path'])
        checksum = item['sha256']
        if path in seen or not isinstance(checksum, str) or len(checksum) != 64 or any(c not in '0123456789abcdef' for c in checksum):
            _invalid()
        seen.add(path)
    seen = set()
    for item in records:
        if not isinstance(item, dict) or set(item) != {'op', 'path', 'value'}:
            _invalid()
        op, path, value = item['op'], _absolute(item['path']), item['value']
        if not isinstance(op, str) or op not in {'file', 'directory', 'realpath'} or (op, path) in seen:
            _invalid()
        if op == 'realpath':
            _absolute(value)
        elif type(value) is not bool:
            _invalid()
        seen.add((op, path))
    def canonical_path(value):
        path = Path(value).as_posix()
        return path if data['case_sensitive'] else path.lower()
    observed_files = {canonical_path(item['path']): item['value'] for item in records if item['op'] == 'file'}
    if any(observed_files.get(canonical_path(item['path'])) is not True for item in files):
        _invalid()
    seen, total = set(), 0
    for item in directories:
        if not isinstance(item, dict) or set(item) != {'path', 'entries'} or not isinstance(item['entries'], list):
            _invalid()
        path = _absolute(item['path'])
        if path in seen:
            _invalid()
        seen.add(path)
        names = set()
        total += len(item['entries'])
        if total > MAX_ENTRIES:
            _invalid()
        for entry in item['entries']:
            if not isinstance(entry, list) or len(entry) != 3:
                _invalid()
            name, kind, link = entry
            if (not isinstance(name, str) or name in {'', '.', '..'} or len(name) > 4096
                    or any(c in name for c in ('/', '\\', '\0')) or name in names
                    or not isinstance(kind, str) or kind not in {'file', 'directory', 'other'}
                    or (link is not None and (not isinstance(link, str) or len(link) > 32768 or '\0' in link))):
                _invalid()
            names.add(name)
    return data


def captured_sources(root: Path, project: dict) -> dict[str, str]:
    validate_capture(project)
    result = {}
    for item in project['input_files']:
        try:
            relative = Path(item['path']).relative_to(root).as_posix()
        except ValueError:
            continue
        result[relative] = item['sha256']
    return dict(sorted(result.items()))


def _entries(root: Path, directory: Path):
    if directory == root / '.kgmaker' or root / '.kgmaker' in directory.parents:
        return []
    try:
        with os.scandir(directory) as iterator:
            entries = []
            for entry in iterator:
                if Path(entry.path) == root / '.kgmaker':
                    continue
                link = os.readlink(entry.path).replace(os.sep, '/') if entry.is_symlink() else None
                kind = 'file' if entry.is_file() else 'directory' if entry.is_dir() else 'other'
                entries.append([entry.name, kind, link])
        return sorted(entries, key=lambda item: item[0].encode('utf-8'))
    except (FileNotFoundError, NotADirectoryError):
        return []


def replay(root: Path, project: dict) -> None:
    try:
        data = validate_capture(project)
        for item in project['input_files']:
            if not Path(item['path']).is_file() or file_hash(Path(item['path'])) != item['sha256']:
                raise ValueError('compiler input content changed: ' + item['path'])
        for item in data['observations']:
            target = Path(item['path'])
            if item['op'] == 'file':
                actual = target.is_file()
            elif item['op'] == 'directory':
                actual = target.is_dir()
            else:
                try:
                    actual = target.resolve(strict=True).as_posix()
                except OSError:
                    actual = target.as_posix()
            expected = item['value']
            if isinstance(actual, str) and not data['case_sensitive']:
                actual, expected = actual.lower(), expected.lower()
            if actual != expected:
                raise ValueError('compiler discovery changed: ' + item['path'])
        for item in data['directories']:
            if _entries(root, Path(item['path'])) != item['entries']:
                raise ValueError('compiler directory membership changed: ' + item['path'])
    except (OSError, ValueError, WorkerError) as error:
        raise WorkerError('STALE_INDEX: TypeScript input snapshot: ' + str(error), 'STALE') from error
