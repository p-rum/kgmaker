"""Bounded replay candidates embedded in the existing graph generation.

Inspection validates fresh stage results. The graph store can retain version 1
metadata alongside the validated graph, with replay disabled until provenance can
be verified independently of the cached payload.
"""
from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path
import time

from .analysis_model import canonical, digest, file_hash
from .worker_protocol import WorkerError

VERSION = 'extraction-stages-1'
MAX_BYTES = 16 * 1024 * 1024
MAX_ENTRIES = 24
STAGES = {'worker-analysis', 'compiler-graph', 'framework-graph'}


def _sha(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _key_shape(key):
    if (type(key) is not dict or set(key) != {'version', 'stage', 'root', 'context',
            'engine', 'launch', 'base', 'upstream'}
            or key['version'] != VERSION or key['stage'] not in STAGES
            or not isinstance(key['root'], str) or not Path(key['root']).is_absolute()
            or not _sha(key['engine']) or type(key['context']) is not dict
            or type(key['launch']) is not dict): return False
    context, launch = key['context'], key['launch']
    if (not _sha(context.get('id')) or any(not isinstance(context.get(k), str) or not context[k]
            for k in ('repo_id', 'module', 'source_set', 'scope', 'language', 'selection_key'))
            or type(context.get('source_files')) is not dict
            or type(context.get('worker')) is not dict
            or set(launch) != {'argv', 'files', 'environment_sha256'}
            or type(launch['argv']) is not list or not launch['argv']
            or any(not isinstance(arg, str) for arg in launch['argv'])
            or type(launch['files']) is not dict or not launch['files']
            or any(not isinstance(path, str) or not _sha(checksum) for path, checksum in launch['files'].items())
            or not _sha(launch['environment_sha256'])): return False
    return ((key['base'] is None and key['upstream'] is None) if key['stage'] == 'worker-analysis'
            else _sha(key['base']) and _sha(key['upstream']))


def _bounded(value):
    pending = [(value, 0)]
    count, text_bytes = 0, 0
    while pending:
        item, depth = pending.pop()
        count += 1
        if count > 500000 or depth > 128:
            return False
        if type(item) is dict:
            if len(item) > 500000 - count or any(type(key) is not str for key in item): return False
            text_bytes += sum(len(key) for key in item)
            pending.extend((child, depth + 1) for child in item.values())
        elif type(item) in (list, tuple):
            if len(item) > 500000 - count: return False
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            text_bytes += len(item)
        elif type(item) not in (str, int, float, bool, type(None)):
            return False
        if text_bytes > MAX_BYTES: return False
    try:
        return len(canonical(value).encode('utf-8')) <= MAX_BYTES
    except (ValueError, TypeError, RecursionError, OverflowError):
        return False


def decode(value):
    """Unknown or malformed optimization metadata never invalidates graph facts."""
    try:
        if (type(value) is not dict or set(value) != {'schema_version', 'entries'}
                or type(value['schema_version']) is not int or value['schema_version'] != 1
                or type(value['entries']) is not list or len(value['entries']) > MAX_ENTRIES
                or not _bounded(value)):
            return {}
        seen = set()
        for entry in value['entries']:
            if (type(entry) is not dict or set(entry) != {'key', 'key_sha256', 'payload', 'payload_sha256'}
                    or not _key_shape(entry['key'])
                    or entry['key_sha256'] != digest(entry['key'])
                    or entry['payload_sha256'] != digest(entry['payload'])
                    or entry['key_sha256'] in seen
                    or type(entry['payload']) is not dict
                    or 'extraction_cache' in entry['payload']):
                return {}
            seen.add(entry['key_sha256'])
        return deepcopy(value)
    except (ValueError, TypeError, KeyError, RecursionError, OverflowError):
        return {}


def graph_payload(graph):
    value = graph.to_dict()
    value.pop('extraction_cache', None)
    value.pop('generated_at', None)
    return value


def engine_fingerprint():
    # All local extractor source bytes are conservative rule inputs. This also
    # invalidates edited development checkouts without inventing version labels.
    package = Path(__file__).parent
    return digest({p.name: file_hash(p) for p in sorted(package.glob('*.py'))})


def launch_inputs(argv):
    """Capture the selected executable/platform, without starting a process."""
    launcher = Path(argv[0])
    try:
        executable = launcher.resolve(strict=True)
        files = {str(executable): file_hash(executable)}
    except OSError:
        return None
    java_names = {'java', 'java.exe'}
    is_java = (os.path.normcase(launcher.name) in java_names
               or os.path.normcase(executable.name) in java_names)
    if is_java:
        try:
            for relative in ('release', 'lib/modules', 'lib/ct.sym'):
                target = executable.parent.parent / relative
                if not target.is_file():
                    return None
                files[str(target)] = file_hash(target)
        except OSError:
            return None
    environment = {name: os.environ.get(name) for name in
                   ('JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS', 'NODE_OPTIONS', 'CLASSPATH')}
    # Arbitrary runtime options may add uncaptured loaders/files. Keep explicit
    # inspection usable, but do not replay such an incompletely closed launch.
    if any(value and not (name == 'JAVA_TOOL_OPTIONS' and value == '-XX:-UsePerfData')
           for name, value in environment.items()):
        return None
    if is_java and os.name == 'posix':
        for name in ('LANG', 'LC_ALL', 'LC_CTYPE'):
            value = os.environ.get(name)
            environment[name] = os.fsencode(value).hex() if value is not None else None
    return {'argv': list(argv), 'files': files, 'environment_sha256': digest(environment)}


def retain(metadata, context_ids):
    value = decode(metadata)
    entries = [entry for entry in value.get('entries', [])
               if entry['key']['context']['id'] in context_ids]
    return {'schema_version': 1, 'entries': entries} if entries else {}


class InspectionStages:
    """Execute live stages and retain bounded metadata without authorizing replay."""

    def __init__(self, root, selected, argv, *, timeout, cancel_file):
        self.root, self.selected = Path(root), deepcopy(selected)
        self.argv = list(argv)
        self.cancel_file = Path(cancel_file) if cancel_file is not None else None
        self.deadline = time.monotonic() + timeout
        self.engine = engine_fingerprint()
        self.launch = launch_inputs(argv)
        worker = selected.get('worker', {})
        self.eligible = (self.launch is not None and worker.get('protocol_version') == 1
                         and isinstance(worker.get('worker'), str)
                         and isinstance(worker.get('compiler_version'), str)
                         and bool(worker.get('distribution'))
                         and selected.get('freshness') != 'STALE'
                         and selected.get('source_snapshot_version') in
                             {'selected-source-set-2', 'typescript-input-discovery-1'})
        self.entries = []
        self.statistics = []

    def guard(self):
        if self.cancel_file is not None and self.cancel_file.exists():
            raise WorkerError('Inspection cancelled before publication', 'CANCELLED')
        if time.monotonic() >= self.deadline:
            raise WorkerError('Inspection timed out before publication', 'TIMED_OUT')
        if self.engine != engine_fingerprint() or self.launch != launch_inputs(self.argv):
            raise WorkerError('Extraction engine/launcher changed during inspection', 'STALE')

    def run(self, stage, builder, validator, *, base=None, upstream=None):
        self.guard()
        key = {'version': VERSION, 'stage': stage,
               'root': str(self.root.resolve()), 'context': self.selected,
               'engine': self.engine, 'launch': self.launch,
               'base': digest(graph_payload(base)) if base is not None else None,
               'upstream': digest(upstream) if upstream is not None else None}
        identity = digest(key)
        # Both the digest and payload are stored together. Structural validation
        # alone cannot authenticate a concrete worker or graph claim from them.
        reason = 'UNVERIFIED_REPLAY' if self.eligible else 'INCOMPLETE_INPUT_CLOSURE'
        payload = builder()
        validator(payload)
        self.guard()
        entry = {'key': key, 'key_sha256': identity,
                 'payload': payload, 'payload_sha256': digest(payload)}
        if self.eligible and _bounded({'schema_version': 1, 'entries': [*self.entries, entry]}):
            self.entries.append(deepcopy(entry))
        elif self.eligible:
            reason = 'CACHE_SIZE_LIMIT'
        self.statistics.append({'stage': stage, 'status': 'BYPASS', 'reason': reason})
        return payload

    def attach(self, graph):
        self.guard()
        graph.extraction_cache = ({'schema_version': 1, 'entries': self.entries}
                                  if self.entries else {})
        return graph

    def report(self):
        return {'version': VERSION, 'stages': deepcopy(self.statistics)}
