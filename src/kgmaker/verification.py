"""Local, file-bound test receipts in the existing delivery journal."""
from __future__ import annotations

import hashlib
import os
import re
import stat
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from .analysis_model import AnalysisError, digest, safe_path
from .memory import is_sensitive_path
from .workflow import STATUSES, _git_head

KIND = 'verification'
INVENTORY = 'ALL_BUILD_INPUTS_V1'
COUNTS = ('executed', 'passed', 'failed', 'skipped', 'total')
STATES = {'SUCCESS', 'FAILED', 'PARTIAL', 'CANCELLED', 'TIMED_OUT', 'TOOLCHAIN_UNAVAILABLE'}
MAX_REPORTS = 100
MAX_REPORT_BYTES = 4 * 1024 * 1024
MAX_DISCOVERY_ENTRIES = 20_000


def _report_path(value):
    if (not isinstance(value, str) or not value or len(value) > 500
            or any(ord(char) < 32 for char in value) or is_sensitive_path(value)):
        return False
    parts = value.split('/')
    if any(part in {'', '.', '..'} or '\\' in part or ':' in part for part in parts):
        return False
    if not re.fullmatch(r'TEST-[^/]+\.xml', parts[-1]):
        return False
    return parts[-3:-1] == ['target', 'surefire-reports'] or parts[-4:-2] == ['build', 'test-results']


def _report_bytes(work, relative):
    path = safe_path(work, relative)
    first = path.lstat()
    if not stat.S_ISREG(first.st_mode) or first.st_size > MAX_REPORT_BYTES:
        raise AnalysisError('Verification report is not a bounded regular file')
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    with os.fdopen(os.open(path, flags), 'rb') as source:
        opened = os.fstat(source.fileno())
        if not stat.S_ISREG(opened.st_mode) or opened.st_size > MAX_REPORT_BYTES:
            raise AnalysisError('Verification report is not a bounded regular file')
        data = source.read(MAX_REPORT_BYTES + 1)
        last = os.fstat(source.fileno())
    snapshots = (first, opened, last, path.lstat())
    identities = {(item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns) for item in snapshots}
    if len(data) > MAX_REPORT_BYTES or len(identities) != 1 or len(data) != first.st_size:
        raise AnalysisError('Verification report changed during read')
    return data


def _suite(suite):
    total, failed, errors, skipped = (int(suite.get(key, '0')) for key in ('tests', 'failures', 'errors', 'skipped'))
    cases = suite.findall('testcase')
    if (min(total, failed, errors, skipped) < 0 or len(cases) != total
            or failed + errors + skipped > total
            or sum(case.find('failure') is not None for case in cases) != failed
            or sum(case.find('error') is not None for case in cases) != errors
            or sum(case.find('skipped') is not None for case in cases) != skipped
            or any(sum(case.find(tag) is not None for tag in ('failure', 'error', 'skipped')) > 1
                   for case in cases)):
        raise ValueError('Inconsistent test case counts')
    return dict(zip(COUNTS, (total - skipped, total - skipped - failed - errors, failed + errors, skipped, total)))


def _discover_reports(work):
    from .build_runner import EXCLUDED

    paths, remaining = [], [work]
    visited = 0
    ignored = EXCLUDED - {'target', 'build'}
    while remaining:
        directory = remaining.pop()
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    visited += 1
                    if visited > MAX_DISCOVERY_ENTRIES or len(paths) > MAX_REPORTS:
                        return sorted(paths), True
                    path = directory / entry.name
                    if entry.is_dir(follow_symlinks=False) and entry.name not in ignored:
                        remaining.append(path)
                    elif _report_path(path.relative_to(work).as_posix()):
                        paths.append(path)
        except OSError:
            return sorted(paths), True
    return sorted(paths), False


def capture_reports(work):
    paths, incomplete = _discover_reports(work)
    records, artifacts = [], {}
    incomplete = incomplete or not paths or len(paths) > MAX_REPORTS
    for path in paths[:MAX_REPORTS]:
        relative = path.relative_to(work).as_posix()
        try:
            if not _report_path(relative):
                raise ValueError('Unsupported report path')
            data = _report_bytes(work, relative)
            tree = ET.fromstring(data)
            if (tree.tag != 'testsuite' or tree.find('.//testsuite') is not None
                    or tree.find('.//testsuites') is not None):
                raise ValueError('Expected one per-class test suite')
            records.append({'report': relative, **_suite(tree)})
            artifacts[relative] = hashlib.sha256(data).hexdigest()
        except (AnalysisError, OSError, ET.ParseError, ValueError):
            incomplete = True
    counts = {key: sum(row[key] for row in records) for key in COUNTS}
    status = ('FAILED' if counts['failed'] else 'PASSED' if counts['executed']
              else 'SKIPPED' if counts['skipped'] else 'ZERO_TESTS' if artifacts else 'NOT_RUN')
    return {'status': status, **counts, 'reports': records,
            'coverage': 'PARTIAL' if incomplete else 'SUPPORTED_XML_REPORTS'}, artifacts


def input_fingerprint(root, sources):
    modes = {}
    for path in sources:
        metadata = safe_path(root, path).lstat()
        if not stat.S_ISREG(metadata.st_mode):
            raise AnalysisError('Verification input is not regular')
        modes[path] = stat.S_IMODE(metadata.st_mode)
    return digest({'sources': sources, 'modes': modes})


def observation(root, sources):
    return {'head': _git_head(root), 'inputs_sha256': input_fingerprint(root, sources),
            'at': datetime.now(timezone.utc).isoformat()}


def _result(record):
    state, code = record['build_status'], record['exit_code']
    if state == 'CANCELLED' and code is None:
        return 'NOT_RUN'
    if state not in {'SUCCESS', 'FAILED'}:
        return 'ERROR'
    if record['report_coverage'] != 'SUPPORTED_XML_REPORTS':
        return 'ERROR' if code != 0 or record['reports'] else 'NOT_RUN'
    counts = record['counts']
    if code == 0 and state == 'SUCCESS' and not counts['failed']:
        if counts['executed']:
            return 'PASS'
        return 'SKIP' if counts['skipped'] else 'NOT_RUN'
    if code not in {0, None} and state == 'FAILED' and counts['failed']:
        return 'FAIL'
    return 'ERROR'


def _hex(value, size):
    return isinstance(value, str) and bool(re.fullmatch(r'[0-9a-f]{' + str(size) + '}', value))


def validate_record(record):
    if not isinstance(record, dict):
        raise AnalysisError('Invalid verification record')
    version = record.get('schema_version')
    fields = {
            'schema_version', 'record_type', 'run_id', 'task_id', 'task_reference', 'runner', 'command_sha256',
            'before', 'after', 'scope', 'exit_code', 'build_status', 'counts', 'reports',
            'report_coverage', 'copied_unchanged', 'result', 'origin'}
    if version == 2:
        fields |= {'task_iteration', 'task_phase'}
    if (type(version) is not int or version not in (1, 2) or set(record) != fields
            or record['record_type'] != KIND or record['origin'] != 'RUNNER_CAPTURED'
            or record['scope'] != INVENTORY or not _hex(record['run_id'], 32)
            or not isinstance(record['task_id'], str) or not record['task_id'].startswith('task:')
            or not _hex(record['task_id'][5:], 64)
            or not isinstance(record['task_reference'], str) or not record['task_reference'].startswith('ref:')
            or not _hex(record['task_reference'][4:], 64)
            or not _hex(record['command_sha256'], 64)
            or not isinstance(record['build_status'], str) or record['build_status'] not in STATES
            or type(record['copied_unchanged']) is not bool
            or (record['exit_code'] is not None and type(record['exit_code']) is not int)):
        raise AnalysisError('Invalid verification record')
    if version == 2 and (type(record['task_iteration']) is not int or record['task_iteration'] < 0
                         or not isinstance(record['task_phase'], str) or record['task_phase'] not in STATUSES):
        raise AnalysisError('Invalid verification task observation')
    runner = record['runner']
    if (not isinstance(runner, dict) or set(runner) != {'build_system', 'plan_version', 'executable_sha256'}
            or runner['build_system'] not in ('maven', 'gradle') or runner['plan_version'] != 'build-plan-1'
            or not _hex(runner['executable_sha256'], 64)):
        raise AnalysisError('Invalid verification runner identity')
    for snapshot in (record['before'], record['after']):
        if (not isinstance(snapshot, dict) or set(snapshot) != {'head', 'inputs_sha256', 'at'}
                or (snapshot['head'] is not None and not _hex(snapshot['head'], 40))
                or not _hex(snapshot['inputs_sha256'], 64) or not isinstance(snapshot['at'], str)
                or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{6})?\+00:00', snapshot['at'])):
            raise AnalysisError('Invalid verification input observation')
    if version == 2:
        try:
            before = datetime.fromisoformat(record['before']['at'])
            after = datetime.fromisoformat(record['after']['at'])
        except ValueError as error:
            raise AnalysisError('Invalid verification input observation') from error
        if after < before:
            raise AnalysisError('Verification run ended before its start')
    counts, reports = record['counts'], record['reports']
    if (record['before']['head'] is None
            or not isinstance(counts, dict) or set(counts) != set(COUNTS)
            or any(type(value) is not int or value < 0 for value in counts.values())
            or counts['total'] != counts['executed'] + counts['skipped']
            or counts['executed'] != counts['passed'] + counts['failed']
            or not isinstance(reports, dict) or len(reports) > MAX_REPORTS
            or any(not _report_path(path) or not _hex(value, 64) for path, value in reports.items())
            or record['report_coverage'] not in ('PARTIAL', 'SUPPORTED_XML_REPORTS')
            or (not reports and (counts['total'] or record['report_coverage'] == 'SUPPORTED_XML_REPORTS'))
            or record['result'] != _result(record)):
        raise AnalysisError('Invalid verification outcome or reports')


def record_execution(root, task, plan, before, after, result, reports, copied_unchanged):
    from . import provenance

    tests = result['tests']
    record = {
        'schema_version': 2, 'record_type': KIND, 'run_id': plan['build_id'], 'task_id': task['id'],
        'task_reference': provenance.task_references(task)[1]['key'],
        'task_iteration': task['iteration'], 'task_phase': task['status'],
        'runner': {'build_system': plan['build_system'], 'plan_version': plan['version'],
                   'executable_sha256': plan['executable']['sha256']},
        'command_sha256': digest(plan['argv']), 'before': before, 'after': after, 'scope': INVENTORY,
        'exit_code': result['return_code'], 'build_status': result['status'],
        'counts': {key: tests[key] for key in COUNTS}, 'reports': reports,
        'report_coverage': tests['coverage'], 'copied_unchanged': copied_unchanged,
        'origin': 'RUNNER_CAPTURED',
    }
    record['result'] = _result(record)
    validate_record(record)
    ref = provenance.reference('test_run', 'verification:' + record['run_id'], '1', record)
    with provenance.transaction(root) as journal:
        provenance.sync_task(journal, task)
        key = provenance.put(journal, ref)
        provenance.connect(journal, key, record['task_reference'], 'verifies')
    return {'reference': key, 'result': record['result'], 'freshness': freshness(root, record)}


def _input_freshness(root, observed):
    from .build_runner import snapshot

    try:
        head = _git_head(root)
        if head is None:
            return 'UNKNOWN'
        if head != observed['head'] or input_fingerprint(root, snapshot(root)) != observed['inputs_sha256']:
            return 'STALE'
    except (AnalysisError, OSError):
        return 'UNKNOWN'
    return 'CURRENT'


def freshness(root, record):
    before, after = record['before'], record['after']
    if after['head'] is None:
        return 'UNKNOWN'
    if any(before[key] != after[key] for key in ('head', 'inputs_sha256')):
        return 'STALE'
    if not record['copied_unchanged'] or record['report_coverage'] != 'SUPPORTED_XML_REPORTS':
        return 'UNKNOWN'
    state = _input_freshness(root, before)
    if state != 'CURRENT':
        return state
    try:
        work = safe_path(root, '.kgmaker/build-runs/' + record['run_id'] + '/snapshot')
        observed, reports = capture_reports(work)
    except (AnalysisError, OSError):
        return 'STALE'
    if reports != record['reports']:
        return 'STALE'
    if observed['coverage'] != record['report_coverage'] or any(
            observed[key] != record['counts'][key] for key in COUNTS):
        return 'UNKNOWN'
    # Report validation may take time while the original checkout is writable.
    return _input_freshness(root, before)


def summary(root, journal, task, *, observed_freshness=None):
    """Evaluate the newest local test/review receipt for the exact task selection."""
    from .provenance import is_verification, task_references

    result = {'status': 'UNVERIFIED', 'result': None, 'freshness': 'UNKNOWN',
              'reference': None, 'reason': 'NO_ELIGIBLE_RUN'}
    plan_count = sum(artifact['phase'] == 'plan' and artifact['role'] == 'architect'
                     for artifact in task['artifacts'])
    if task['plan_revision'] != plan_count:
        return {**result, 'reason': 'PLAN_REVISION_UNBOUND'}
    target = task_references(task)[1]['key']
    latest, ambiguous = None, False
    for link in journal['links']:
        if link['target'] != target or link['relation'] != 'verifies':
            continue
        ref = journal['references'][link['source']]
        if not is_verification(ref):
            continue
        record = ref['payload']
        if (record['schema_version'] != 2 or record['task_iteration'] != task['iteration']
                or record['task_phase'] not in {'test', 'review'}):
            continue
        started = datetime.fromisoformat(record['before']['at'])
        if latest is None or started > latest[0]:
            latest, ambiguous = (started, ref), False
        elif started == latest[0] and ref['key'] != latest[1]['key']:
            ambiguous = True
    if latest is None:
        return result
    if ambiguous:
        return {**result, 'reason': 'AMBIGUOUS_LATEST_RUN'}
    ref = latest[1]
    record = ref['payload']
    state = observed_freshness.get(ref['key']) if observed_freshness is not None else None
    if state is None:
        state = freshness(root, record)
    if state == 'STALE':
        result.update(status='STALE', reason='STALE_RUN')
    elif state != 'CURRENT':
        result.update(reason='UNVERIFIED_RUN')
    elif record['result'] == 'PASS':
        result.update(status='VERIFIED', reason='CURRENT_PASS')
    else:
        result.update(reason='LATEST_RUN_NOT_PASS')
    return {**result, 'result': record['result'], 'freshness': state, 'reference': ref['key']}
