"""Source-bound receipts from explicit test execution."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from kgmaker import provenance
from kgmaker.analysis_model import AnalysisError, digest
from kgmaker.build_runner import create_plan, run_plan
from kgmaker.workflow import (WorkflowError, add_task, advance_task, load_task,
                              record_artifact, save_task, task_path)


pytestmark = pytest.mark.skipif(os.name != 'posix', reason='BUILD_EXECUTE requires POSIX')


def checkout(root):
    for args in (('init', '-q'), ('add', '.'), ('-c', 'user.name=Fixture',
                 '-c', 'user.email=fixture@example.test', 'commit', '-qm', 'fixture')):
        subprocess.run(['git', '-C', str(root), *args], check=True)


@pytest.fixture
def fixture(tmp_path):
    root = tmp_path / 'code'
    root.mkdir()
    (root / 'pom.xml').write_text('<project/>')
    (root / 'suite.py').write_text('import unittest\n\nclass Example(unittest.TestCase):\n'
                                 '    def test_value(self): self.assertEqual(1, 1)\n')
    (root / '.test-config').write_text('config')
    (root / 'deps.lock').write_text('lock')
    checkout(root)
    task = add_task(root, 'Exercise existing build-run', title='Verification fixture')
    tools = tmp_path / 'tools'
    exporter = tools / 'build/maven/target/kgmaker-build-export.jar'
    exporter.parent.mkdir(parents=True)
    exporter.write_bytes(b'fixture exporter placeholder')
    launcher = tools / 'mvn'
    launcher.write_text('#!' + sys.executable + '\n' + r'''
import importlib.util
import sys
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET
work = Path.cwd()
if (work / 'change-original').is_file():
    root = work.parents[3]
    (root / 'deps.lock').write_text('changed during build')
if (work / 'add-copied-input').is_file():
    (work / 'generated-config').write_text('not in the bound inputs')
export = Path(next(arg.split('=', 1)[1] for arg in sys.argv[1:] if arg.startswith('-Dkgmaker.export.path=')))
export.write_text('{"contexts":[],"diagnostics":[]}')
spec = importlib.util.spec_from_file_location('suite', 'suite.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
result = unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromModule(module))
if not (work / 'omit-report').is_file():
    report = work / 'target/surefire-reports/TEST-suite.xml'
    report.parent.mkdir(parents=True)
    suite = ET.Element('testsuite', tests=str(result.testsRun), failures=str(len(result.failures)),
                       errors=str(len(result.errors)), skipped=str(len(result.skipped)))
    if not (work / 'bad-report').is_file():
        case = ET.SubElement(suite, 'testcase', name='test_value')
        if result.failures:
            ET.SubElement(case, 'failure').text = 'CONFIDENTIAL_FIXTURE_LOG'
        if result.errors:
            ET.SubElement(case, 'error')
        if result.skipped:
            ET.SubElement(case, 'skipped')
    if (work / 'wrapper-report').is_file():
        wrapper = ET.Element('testsuites', tests='2', failures='1')
        wrapper.append(suite)
        suite = wrapper
    ET.ElementTree(suite).write(report)
sys.exit(0 if result.wasSuccessful() else 1)
''')
    launcher.chmod(0o700)
    return root, task, tools, launcher


def run(fixture, **kwargs):
    root, task, tools, launcher = fixture
    plan = create_plan(root, phase='test', home=tools, executable=str(launcher), offline=True)
    return run_plan(plan, verification_task=task['id'], **kwargs)


def traced(fixture, receipt):
    root, _, _, _ = fixture
    reference = receipt['verification']['reference']
    trace = provenance.trace(root, reference)
    row = next(row for row in trace['references'] if row['key'] == reference)
    assert any(link['source'] == reference and link['relation'] == 'verifies' for link in trace['links'])
    return row


def move(root, task, *phases):
    for phase in phases:
        task = advance_task(root, task['id'], phase)
    return task


def enable_gate(root):
    revision = provenance.load(root)['revision']
    with provenance.transaction(root, expected_revision=revision) as journal:
        journal['policy'][provenance.VERIFICATION_POLICY] = True


def workflow_trace(root, task):
    return next(row for row in provenance.trace(root, task['id'])['references']
                if 'verification_summary' in row)


def assert_gate_rejects(root, task, reason):
    task_file = task_path(root, task['id'])
    journal = root / provenance.JOURNAL
    before = task_file.read_bytes(), journal.read_bytes()
    with pytest.raises(WorkflowError, match=reason):
        advance_task(root, task['id'], 'done')
    with pytest.raises(WorkflowError, match=reason):
        save_task(root, task | {'status': 'done'}, expected_revision=digest(task))
    assert (task_file.read_bytes(), journal.read_bytes()) == before


def record_plan(root, task):
    return record_artifact(root, task['id'], 'architect', {
        'task_id': task['id'], 'role': 'architect', 'phase': 'plan', 'iteration': 0,
        'summary': 'Plan', 'status': 'completed', 'cited_paths': [], 'cited_node_ids': [],
        'packet_id': None, 'disposition': None, 'out_of_scope': [],
        'steps': [{'id': 'build', 'intent': 'Exercise the build', 'paths': [], 'tests': ['suite.py']}],
    })


def test_same_head_retry_requires_receipt_from_current_iteration(fixture):
    from kgmaker.context import prepare_packet

    root, task, _, _ = fixture
    task = move(root, task, 'analyze', 'plan', 'implement', 'test')
    enable_gate(root)
    receipt = run(fixture)
    original = traced(fixture, receipt)
    assert original['payload']['task_iteration'] == 0
    assert original['payload']['task_phase'] == 'test'
    task = move(root, task, 'review', 'implement', 'test', 'review')
    assert task['iteration'] == 1
    assert traced(fixture, receipt)['freshness'] == 'CURRENT'
    assert_gate_rejects(root, task, 'NO_ELIGIBLE_RUN')
    with pytest.raises(WorkflowError, match='iteration must follow its phase transition'):
        save_task(root, task | {'status': 'done', 'iteration': 0}, expected_revision=digest(task))
    with pytest.raises(WorkflowError, match='cannot change plan revision'):
        save_task(root, task | {'status': 'done', 'plan_revision': 1}, expected_revision=digest(task))

    latest = traced(fixture, run(fixture))
    assert latest['payload']['task_iteration'] == 1
    assert latest['payload']['task_phase'] == 'review'
    assert latest['payload']['before']['head'] == original['payload']['before']['head']
    report = workflow_trace(root, task)
    packet = prepare_packet(root, task, 'review', persist=False)
    assert packet['verification_summary'] == report['verification_summary']
    assert 'approval_policy' not in packet
    assert report['verification_summary']['reference'] == latest['key']
    assert report['workflow_status'] == 'review'
    rendered = provenance.markdown(provenance.trace(root, task['id']))
    assert f"| task | {task['id']} | 0 | UNKNOWN | False | CURRENT |" in rendered
    assert 'workflow `review`, iterace 1, ověření `VERIFIED` (`CURRENT_PASS`)' in rendered
    task = move(root, task, 'done')
    assert workflow_trace(root, task)['workflow_status'] == 'done'


def test_recorded_phase_is_bound_before_the_runner_starts(fixture):
    root, task, _, launcher = fixture
    task = move(root, task, 'analyze', 'plan', 'implement')
    enable_gate(root)
    popen = subprocess.Popen

    def advance_during_run(command, *args, **kwargs):
        if command[0] == str(launcher):
            move(root, task, 'test', 'review')
        return popen(command, *args, **kwargs)

    with patch('kgmaker.build_runner.subprocess.Popen', side_effect=advance_during_run):
        receipt = run(fixture)
    captured = traced(fixture, receipt)
    assert captured['payload']['task_phase'] == 'implement'
    assert captured['freshness'] == 'CURRENT'
    assert_gate_rejects(root, load_task(root, task['id']), 'NO_ELIGIBLE_RUN')


def test_legacy_imported_and_agent_declared_records_do_not_grant_authority(fixture):
    root, task, _, _ = fixture
    task = move(root, task, 'analyze', 'plan', 'implement', 'test')
    (root / 'claimed.json').write_text('{"origin":"RUNNER_CAPTURED","result":"PASS"}')
    captured = traced(fixture, run(fixture))
    payload = dict(captured['payload'], schema_version=1)
    del payload['task_iteration'], payload['task_phase']
    legacy = provenance.reference('test_run', captured['id'], '1', payload)
    imported = provenance.register_file(root, 'test_run', 'report:file', '1', 'claimed.json')
    declared = provenance.reference('test_run', 'artifact:declaration', '1', {'status': 'PASS'})
    with provenance.transaction(root) as journal:
        del journal['references'][captured['key']]
        journal['links'] = [link for link in journal['links'] if link['source'] != captured['key']]
        provenance.put(journal, legacy)
        provenance.put(journal, declared)
        for key in (legacy['key'], imported, declared['key']):
            provenance.connect(journal, key, payload['task_reference'], 'verifies')
    rows = {row['key']: row for row in provenance.trace(root, task['id'])['references']}
    assert rows[legacy['key']]['freshness'] == 'CURRENT'
    assert rows[imported]['origin'] == 'IMPORTED'
    assert rows[declared['key']]['origin'] == 'AGENT_DECLARED'
    assert provenance.VERIFICATION_POLICY not in provenance.load(root)['policy']
    enable_gate(root)
    task = move(root, task, 'review')
    assert_gate_rejects(root, task, 'NO_ELIGIBLE_RUN')


@pytest.mark.parametrize(('runner_edit', 'expected_result', 'reason'), [
    ('module.Example.test_value = lambda self: self.fail("latest run failed")', 'FAIL', 'LATEST_RUN_NOT_PASS'),
    ('if False:', 'NOT_RUN', 'UNVERIFIED_RUN'),
])
def test_newest_run_cannot_fall_back_to_an_earlier_pass(fixture, runner_edit, expected_result, reason):
    root, task, _, launcher = fixture
    task = move(root, task, 'analyze', 'plan', 'implement', 'test')
    enable_gate(root)
    original = traced(fixture, run(fixture))
    script = launcher.read_text()
    if expected_result == 'FAIL':
        script = script.replace('result = unittest.', runner_edit + '\nresult = unittest.')
    else:
        script = script.replace("if not (work / 'omit-report').is_file():", runner_edit)
    launcher.write_text(script)
    latest = traced(fixture, run(fixture))
    assert latest['payload']['result'] == expected_result
    assert latest['payload']['before']['inputs_sha256'] == original['payload']['before']['inputs_sha256']
    task = move(root, task, 'review')
    assert_gate_rejects(root, task, reason)
    assert workflow_trace(root, task)['verification_summary']['reference'] == latest['key']


def test_direct_save_cannot_restore_authority_by_rewriting_plan_revision(fixture):
    root, task, _, _ = fixture
    task = move(root, task, 'analyze', 'plan')
    task = record_plan(root, task)
    assert task['plan_revision'] == 1
    task = move(root, task, 'implement', 'test')
    enable_gate(root)
    rewritten = task | {'plan_revision': 0}
    save_task(root, rewritten, expected_revision=digest(task))
    assert traced(fixture, run(fixture))['freshness'] == 'CURRENT'
    task = move(root, rewritten, 'review')
    assert_gate_rejects(root, task, 'PLAN_REVISION_UNBOUND')


def test_current_verification_does_not_override_revoked_approval(fixture):
    root, task, _, _ = fixture
    task = record_plan(root, move(root, task, 'analyze', 'plan'))
    task = move(root, task, 'implement', 'test')
    enable_gate(root)
    assert traced(fixture, run(fixture))['freshness'] == 'CURRENT'
    task = move(root, task, 'review')
    task = record_artifact(root, task['id'], 'review', {
        'task_id': task['id'], 'role': 'review', 'phase': 'review', 'iteration': 0,
        'summary': 'Reviewed', 'status': 'completed', 'cited_paths': [], 'cited_node_ids': [],
        'packet_id': None, 'disposition': None, 'findings': [], 'overall': 'approve',
    })
    with provenance.transaction(root) as journal:
        refs = provenance.sync_task(journal, task)
        journal['identity'] = {'id': 'reviewer', 'kind': 'human'}
        journal['policy']['before_done'] = True
        for ref in refs:
            if ref['kind'] in {'requirement', 'plan', 'review'}:
                provenance.event(journal, ref['key'], 'approved', 'Reviewed exact content')
        review = refs[-1]['key']
        provenance.event(journal, review, 'revoked', 'Approval withdrawn')
    assert workflow_trace(root, task)['verification_summary']['status'] == 'VERIFIED'
    assert_gate_rejects(root, task, 'lacks local approval')
    with provenance.transaction(root) as journal:
        provenance.event(journal, review, 'approved', 'Approval restored')
    assert move(root, task, 'done')['status'] == 'done'


def test_legacy_policy_off_preserves_done_history_without_a_receipt(fixture):
    root, task, _, _ = fixture
    task = move(root, task, 'analyze', 'plan', 'implement', 'test', 'review', 'done')
    with provenance.transaction(root) as journal:
        provenance.sync_task(journal, task)
    payload = task_path(root, task['id']).read_bytes()
    assert provenance.VERIFICATION_POLICY not in provenance.load(root)['policy']
    enable_gate(root)
    report = workflow_trace(root, task)
    assert report['workflow_status'] == 'done'
    assert report['verification_summary']['status'] == 'UNVERIFIED'
    assert task_path(root, task['id']).read_bytes() == payload


def test_verification_policy_cli_requires_current_journal_revision(fixture):
    root, _, _, _ = fixture
    command = [sys.executable, '-m', 'kgmaker', 'trace', 'policy', '--root', str(root),
               '--verification-before-done', 'on']
    journal = root / provenance.JOURNAL
    missing = subprocess.run(command, capture_output=True)
    assert missing.returncode != 0
    assert '--expected-revision' in json.loads(missing.stdout)['error']
    assert not journal.exists()
    subprocess.run([*command, '--expected-revision', '0'], check=True, capture_output=True)
    assert provenance.load(root)['policy'] == {
        'before_implement': False, 'before_done': False, provenance.VERIFICATION_POLICY: True,
    }
    previous = journal.read_bytes()
    stale = subprocess.run([*command, '--expected-revision', '0'], capture_output=True)
    assert stale.returncode != 0
    assert 'Stale journal revision' in json.loads(stale.stdout)['error']
    assert journal.read_bytes() == previous


def test_equal_run_start_times_fail_closed(fixture, monkeypatch):
    from datetime import datetime

    class FixedStart(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 11, 21, tzinfo=tz)

    root, task, _, _ = fixture
    task = move(root, task, 'analyze', 'plan', 'implement', 'test')
    enable_gate(root)
    monkeypatch.setattr('kgmaker.verification.datetime', FixedStart)
    assert run(fixture)['verification']['result'] == 'PASS'
    assert run(fixture)['verification']['result'] == 'PASS'
    task = move(root, task, 'review')
    assert_gate_rejects(root, task, 'AMBIGUOUS_LATEST_RUN')


@pytest.mark.parametrize('entrypoint', ['advance', 'save'])
def test_done_rechecks_inputs_after_bound_report_validation(fixture, entrypoint):
    from kgmaker.verification import capture_reports

    root, task, _, _ = fixture
    task = move(root, task, 'analyze', 'plan', 'implement', 'test')
    enable_gate(root)
    receipt = run(fixture)
    assert receipt['verification']['freshness'] == 'CURRENT'
    task = move(root, task, 'review')
    task_file = task_path(root, task['id'])
    journal = root / provenance.JOURNAL
    before = task_file.read_bytes(), journal.read_bytes()

    def capture_then_edit(work):
        result = capture_reports(work)
        (root / '.test-config').write_text('changed while checking the XML at the same HEAD')
        return result

    with patch('kgmaker.verification.capture_reports', side_effect=capture_then_edit), \
            pytest.raises(WorkflowError, match='STALE_RUN'):
        if entrypoint == 'advance':
            advance_task(root, task['id'], 'done')
        else:
            save_task(root, task | {'status': 'done'}, expected_revision=digest(task))
    assert (task_file.read_bytes(), journal.read_bytes()) == before
    assert traced(fixture, receipt)['freshness'] == 'STALE'


def test_trace_shares_its_single_receipt_observation_with_task_summary(fixture):
    root, task, _, _ = fixture
    task = move(root, task, 'analyze', 'plan', 'implement', 'test')
    enable_gate(root)
    receipt = run(fixture)
    assert receipt['verification']['freshness'] == 'CURRENT'
    key = receipt['verification']['reference']

    with patch('kgmaker.verification.freshness', side_effect=['CURRENT', 'STALE']) as observed:
        references = provenance.trace(root, task['id'])['references']
    observed.assert_called_once()
    run_row = next(row for row in references if row['key'] == key)
    summary = next(row['verification_summary'] for row in references if row['id'] == task['id'])
    assert run_row['freshness'] == summary['freshness'] == 'CURRENT'
    assert summary['status'] == 'VERIFIED'


@pytest.mark.parametrize('changed', ['suite.py', '.test-config', 'deps.lock', 'untracked-input'])
def test_existing_cli_binds_real_exit_and_stales_same_head_inputs(fixture, tmp_path, changed):
    root, task, tools, launcher = fixture
    plan = create_plan(root, phase='test', home=tools, executable=str(launcher), offline=True)
    path = tmp_path / 'plan.json'
    path.write_text(json.dumps(plan))
    result = subprocess.run([sys.executable, '-m', 'kgmaker', 'project', 'build-run', '--plan',
                             str(path), '--record-verification', task['id']], check=True, capture_output=True)
    receipt = json.loads(result.stdout)
    assert receipt['verification']['result'] == 'PASS'
    assert receipt['verification']['freshness'] == 'CURRENT'
    before = traced(fixture, receipt)
    assert before['payload']['counts']['executed'] == 1
    (root / changed).write_text('changed')
    after = traced(fixture, receipt)
    assert after['payload'] == before['payload']
    assert after['origin'] == 'RUNNER_CAPTURED'
    assert after['freshness'] == 'STALE'


def test_real_failed_case_and_report_redaction(fixture):
    root = fixture[0]
    script = root / 'suite.py'
    script.write_text(script.read_text().replace('1, 1', '1, 2'))
    receipt = run(fixture)
    result = traced(fixture, receipt)
    assert result['payload']['result'] == 'FAIL'
    assert result['payload']['counts']['failed'] == 1
    assert result['payload']['exit_code'] == 1
    assert result['freshness'] == 'CURRENT'
    assert 'CONFIDENTIAL_FIXTURE_LOG' not in (root / provenance.JOURNAL).read_text()


@pytest.mark.parametrize('activity,expected', [('change-original', 'STALE'), ('add-copied-input', 'UNKNOWN')])
def test_changed_during_run_is_never_current(fixture, activity, expected):
    (fixture[0] / activity).touch()
    receipt = run(fixture)
    assert receipt['verification']['result'] == 'PASS'
    assert traced(fixture, receipt)['freshness'] == expected


@pytest.mark.parametrize('damage', ['tamper', 'delete', 'symlink', 'fifo'])
def test_missing_or_changed_saved_report_invalidates_receipt(fixture, tmp_path, damage):
    receipt = run(fixture)
    snapshot = Path(receipt['manifest_path']).parent / 'snapshot'
    report = snapshot / 'target/surefire-reports/TEST-suite.xml'
    if damage == 'tamper':
        report.write_bytes(report.read_bytes() + b'\n')
    else:
        report.unlink()
        if damage == 'symlink':
            alternative = tmp_path / 'outside.xml'
            alternative.write_text('<testsuite/>')
            report.symlink_to(alternative)
        elif damage == 'fifo':
            os.mkfifo(report)
    assert traced(fixture, receipt)['freshness'] == 'STALE'


@pytest.mark.parametrize('flag', ['omit-report', 'bad-report', 'wrapper-report'])
def test_empty_or_inconsistent_reports_do_not_verify(fixture, flag):
    (fixture[0] / flag).touch()
    receipt = run(fixture)
    assert receipt['verification']['result'] == 'NOT_RUN'
    assert traced(fixture, receipt)['freshness'] == 'UNKNOWN'


def test_imports_and_legacy_claims_are_distinguished(fixture):
    root = fixture[0]
    (root / 'result.json').write_text('{"result":"PASS","origin":"RUNNER_CAPTURED"}')
    imported = provenance.register_file(root, 'test_run', 'verification:legacy-id', '1', 'result.json')
    declared = provenance.reference('test_run', 'artifact:legacy', '1', {'validations': [{'status': 'passed'}]})
    with provenance.transaction(root) as journal:
        provenance.put(journal, declared)
    rows = {row['key']: row for row in provenance.trace(root)['references']}
    assert rows[imported]['origin'] == 'IMPORTED'
    assert rows[declared['key']]['origin'] == 'AGENT_DECLARED'
    assert rows[imported]['freshness'] == rows[declared['key']]['freshness'] == 'UNKNOWN'


def test_inconsistent_typed_receipt_rejected_without_journal_mutation(fixture):
    root = fixture[0]
    receipt = run(fixture)
    existing = (root / provenance.JOURNAL).read_bytes()
    payload = traced(fixture, receipt)['payload']
    payload['result'] = 'FAIL'
    ref = provenance.reference('test_run', 'verification:' + payload['run_id'], '1', payload)
    with pytest.raises(AnalysisError, match='Invalid verification outcome'):
        with provenance.transaction(root) as journal:
            journal['references'][ref['key']] = ref
    assert (root / provenance.JOURNAL).read_bytes() == existing


def test_opt_in_requires_test_plan_and_does_not_start_process(fixture):
    root, task, tools, launcher = fixture
    plan = create_plan(root, phase='compile', home=tools, executable=str(launcher))
    with pytest.raises(AnalysisError, match='requires a full build inventory and test phase'):
        run_plan(plan, verification_task=task['id'])
    assert not Path(plan['run_root']).exists()


def test_workspace_verification_is_rejected_before_build_or_journal_writes(fixture, tmp_path, monkeypatch, capsys):
    from kgmaker.cli import main

    root, task, tools, launcher = fixture
    other = tmp_path / 'other'
    other.mkdir()
    (other / 'README.md').write_text('Separate checkout\n')
    checkout(other)
    other_task = add_task(other, 'Keep the second checkout journal unchanged')
    manifest = tmp_path / 'workspace.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'workspace_id': 'verification', 'repositories': [
        {'id': 'selected', 'role': 'backend', 'path': root.name},
        {'id': 'other', 'role': 'shared', 'path': other.name},
    ]}))
    plan = create_plan(root, phase='test', home=tools, executable=str(launcher), offline=True)
    plan_file = tmp_path / 'plan.json'
    plan_file.write_text(json.dumps(plan))
    for repo, existing_task in ((root, task), (other, other_task)):
        with provenance.transaction(repo) as journal:
            provenance.sync_task(journal, existing_task)
    journals = {repo / provenance.JOURNAL: (repo / provenance.JOURNAL).read_bytes()
                for repo in (root, other)}

    monkeypatch.setattr(sys, 'argv', ['kgmaker', 'project', 'build-run', '--root', str(tmp_path),
                                    '--workspace', str(manifest), '--repo', 'selected', '--plan', str(plan_file),
                                    '--record-verification', task['id']])
    with patch('kgmaker.build_runner.run_plan', side_effect=AssertionError('Unexpected build runner')), \
            patch('subprocess.Popen', side_effect=AssertionError('Unexpected subprocess')), \
            pytest.raises(SystemExit) as failure:
        main()

    assert failure.value.code == 2
    assert json.loads(capsys.readouterr().out) == {
        'status': 'INVALID_INPUT', 'diagnostics': ['Verification capture supports a single plan checkout'],
    }
    assert not any((repo / '.kgmaker/build-runs').exists() for repo in (root, other))
    assert not (tmp_path / '.kgmaker').exists()
    assert all(path.read_bytes() == before for path, before in journals.items())


def test_actual_maven_surefire_pass_and_fail(tmp_path, monkeypatch):
    from kgmaker.inspection import worker_home

    maven = shutil.which('mvn')
    java = shutil.which('javac')
    tools = worker_home(None)
    exporter = tools / 'build/maven/target/kgmaker-build-export.jar'
    repository = os.environ.get('KGMAKER_TEST_MAVEN_REPOSITORY')
    if not (maven and java and exporter.is_file() and repository):
        message = 'Maven, JDK, exporter and explicitly prepared offline Maven repository required'
        if os.environ.get('KGMAKER_REQUIRE_EXPORTERS') == '1':
            pytest.fail(message)
        pytest.skip(message)
    monkeypatch.setenv('MAVEN_OPTS', f'-Dmaven.repo.local={repository}')
    root = tmp_path / 'actual'
    package = root / 'src/test/java/fixture'
    package.mkdir(parents=True)
    (root / 'pom.xml').write_text('''<project xmlns="http://maven.apache.org/POM/4.0.0">
      <modelVersion>4.0.0</modelVersion><groupId>fixture</groupId>
      <artifactId>verification</artifactId><version>1.0.0</version>
      <properties><maven.compiler.release>17</maven.compiler.release></properties>
      <dependencies><dependency><groupId>org.junit.jupiter</groupId><artifactId>junit-jupiter</artifactId>
        <version>5.11.4</version><scope>test</scope></dependency></dependencies>
      <build><plugins>
        <plugin><groupId>org.apache.maven.plugins</groupId><artifactId>maven-resources-plugin</artifactId><version>3.3.1</version></plugin>
        <plugin><groupId>org.apache.maven.plugins</groupId><artifactId>maven-compiler-plugin</artifactId><version>3.13.0</version></plugin>
        <plugin><groupId>org.apache.maven.plugins</groupId><artifactId>maven-surefire-plugin</artifactId><version>3.5.2</version></plugin>
      </plugins></build></project>''')
    test = package / 'CapturedTest.java'
    source = '''package fixture;
import static org.junit.jupiter.api.Assertions.assertEquals;
import org.junit.jupiter.api.Test;
class CapturedTest {
    @Test void executes() { assertEquals(1, ACTUAL); }
}
'''
    test.write_text(source.replace('ACTUAL', '1'))
    policy = root / '.test-config'
    policy.write_text('initial test configuration')
    checkout(root)
    task = add_task(root, 'Use actual Maven/Surefire test process')
    task = move(root, task, 'analyze', 'plan', 'implement', 'test')
    enable_gate(root)
    fixture = root, task, tools, maven

    passing = run(fixture)
    row = traced(fixture, passing)
    assert row['payload']['result'] == 'PASS', passing
    assert row['freshness'] == 'CURRENT'
    assert row['payload']['counts']['executed'] == 1
    task = move(root, task, 'review')
    policy.write_text('changed at the same HEAD')
    assert traced(fixture, passing)['freshness'] == 'STALE'
    assert_gate_rejects(root, task, 'STALE_RUN')

    test.write_text(source.replace('ACTUAL', '2'))
    failing = run(fixture)
    row = traced(fixture, failing)
    assert row['payload']['result'] == 'FAIL', failing
    assert row['freshness'] == 'CURRENT'
    assert row['payload']['counts']['failed'] == 1
    assert_gate_rejects(root, task, 'LATEST_RUN_NOT_PASS')

    test.write_text(source.replace('ACTUAL', '1'))
    assert_gate_rejects(root, task, 'STALE_RUN')
    repeated = run(fixture)
    row = traced(fixture, repeated)
    assert row['payload']['result'] == 'PASS', repeated
    assert row['payload']['before']['head'] == traced(fixture, passing)['payload']['before']['head']
    save_task(root, task | {'status': 'done'}, expected_revision=digest(task))
    task = load_task(root, task['id'])
    completed = task_path(root, task['id']).read_bytes()
    assert workflow_trace(root, task)['verification_summary']['status'] == 'VERIFIED'
    policy.write_text('changed after completion')
    report = workflow_trace(root, task)
    assert report['workflow_status'] == 'done'
    assert report['verification_summary']['status'] == 'STALE'
    assert task_path(root, task['id']).read_bytes() == completed
    assert traced(fixture, repeated)['payload'] == row['payload']


def test_chmod_alone_invalidates_prior_pass_and_real_rerun_fails(fixture):
    root = fixture[0]
    helper = root / 'helper.sh'
    helper.write_text('#!/bin/sh\nexit 0\n')
    helper.chmod(0o700)
    suite = root / 'suite.py'
    suite.write_text('import subprocess\nimport unittest\n\n'
                     'class Example(unittest.TestCase):\n'
                     '    def test_value(self): subprocess.run(["./helper.sh"], check=True)\n')
    passing = run(fixture)
    prior = traced(fixture, passing)
    assert prior['payload']['result'] == 'PASS'
    assert prior['freshness'] == 'CURRENT'
    helper.chmod(0o600)
    stale = traced(fixture, passing)
    assert stale['payload'] == prior['payload']
    assert stale['freshness'] == 'STALE'
    failing = traced(fixture, run(fixture))
    assert failing['payload']['result'] == 'FAIL'
    assert failing['freshness'] == 'CURRENT'


def test_verification_cannot_attach_to_other_task_or_plan_revision(fixture):
    root, first_task, _, _ = fixture
    second_task = add_task(root, 'Different purpose')
    receipt = run(fixture)
    reference = receipt['verification']['reference']
    altered = first_task | {'plan_revision': first_task['plan_revision'] + 1}
    with provenance.transaction(root) as journal:
        second_ref = provenance.sync_task(journal, second_task)[1]['key']
        different_revision = provenance.sync_task(journal, altered)[1]['key']
    existing = (root / provenance.JOURNAL).read_bytes()
    for target in (second_ref, different_revision):
        with pytest.raises(AnalysisError, match='Verification must link'):
            with provenance.transaction(root) as journal:
                provenance.connect(journal, reference, target, 'verifies')
        assert (root / provenance.JOURNAL).read_bytes() == existing


@pytest.mark.parametrize('field', ['build_status', 'report_coverage', 'build_system'])
def test_malformed_receipt_enums_are_rejected(fixture, field):
    from kgmaker.verification import validate_record

    payload = traced(fixture, run(fixture))['payload']
    target = payload['runner'] if field == 'build_system' else payload
    target[field] = []
    with pytest.raises(AnalysisError, match='Invalid verification'):
        validate_record(payload)


def test_receipt_cannot_attribute_run_to_a_different_executable(fixture):
    root, task, tools, launcher = fixture
    plan = create_plan(root, phase='test', home=tools, executable=str(launcher))
    plan['argv'][0] = '/bin/true'
    plan['plan_hash'] = digest({key: value for key, value in plan.items() if key != 'plan_hash'})
    with pytest.raises(AnalysisError, match='does not match its bound executable'):
        run_plan(plan, verification_task=task['id'])
    assert not Path(plan['run_root']).exists()


def test_read_write_mode_change_invalidates_prior_success(fixture):
    root = fixture[0]
    policy = root / 'settings'
    policy.write_text('unchanged\n')
    policy.chmod(0o600)
    (root / 'suite.py').write_text(
        "import pathlib\nimport stat\nimport unittest\n"
        "class Example(unittest.TestCase):\n"
        "    def test_mode(self):\n"
        "        mode = stat.S_IMODE(pathlib.Path('settings').stat().st_mode)\n"
        "        self.assertEqual(mode, 0o600)\n")
    passing = run(fixture)
    assert traced(fixture, passing)['freshness'] == 'CURRENT'
    policy.chmod(0o400)
    assert traced(fixture, passing)['freshness'] == 'STALE'
    failing = traced(fixture, run(fixture))
    assert failing['payload']['result'] == 'FAIL'
    assert failing['freshness'] == 'CURRENT'


def test_coherent_pass_summary_cannot_disagree_with_bound_xml(fixture):
    from kgmaker.verification import freshness, validate_record

    root = fixture[0]
    script = root / 'suite.py'
    script.write_text(script.read_text().replace('1, 1', '1, 2'))
    payload = traced(fixture, run(fixture))['payload']
    assert payload['result'] == 'FAIL'
    payload.update(result='PASS', exit_code=0, build_status='SUCCESS')
    payload['counts'].update(passed=1, failed=0)
    validate_record(payload)
    assert freshness(root, payload) == 'UNKNOWN'
