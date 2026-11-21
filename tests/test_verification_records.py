"""Source-bound receipts from explicit test execution."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from kgmaker import provenance
from kgmaker.analysis_model import AnalysisError, digest
from kgmaker.build_runner import create_plan, run_plan
from kgmaker.workflow import add_task


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
    checkout(root)
    task = add_task(root, 'Use actual Maven/Surefire test process')
    fixture = root, task, tools, maven

    passing = run(fixture)
    row = traced(fixture, passing)
    assert row['payload']['result'] == 'PASS', passing
    assert row['freshness'] == 'CURRENT'
    assert row['payload']['counts']['executed'] == 1
    test.write_text(source.replace('ACTUAL', '2'))
    assert traced(fixture, passing)['freshness'] == 'STALE'

    failing = run(fixture)
    row = traced(fixture, failing)
    assert row['payload']['result'] == 'FAIL', failing
    assert row['freshness'] == 'CURRENT'
    assert row['payload']['counts']['failed'] == 1


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
