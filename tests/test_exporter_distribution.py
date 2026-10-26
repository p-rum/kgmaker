"""T003-S11-W02: verify trusted exporter distribution before any build."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import patch

import pytest

from kgmaker.analysis_model import AnalysisError, file_hash
from kgmaker.build_runner import create_plan, run_plan

ROOT = Path(__file__).resolve().parents[1]


def distribution(tmp_path, *, protocol=1, checksum=None):
    home = tmp_path / 'workers'
    adapter = home / 'build/gradle/export.gradle'
    adapter.parent.mkdir(parents=True)
    adapter.write_text('// trusted fixture, never executed\n')
    (home / 'build/LICENSE').write_text('Apache License 2.0\n')
    manifest = home / 'build/exporters.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'protocol_version': protocol,
        'exporters': {'gradle': {'path': 'gradle/export.gradle',
            'sha256': checksum or file_hash(adapter), 'exporter': 'gradle-composite-1',
            'license': 'LICENSE'}}}))
    project = tmp_path / 'project'
    project.mkdir()
    (project / 'build.gradle').write_text("plugins { id 'java' }\n")
    return home, adapter, manifest, project


@pytest.mark.parametrize('case', ['hash', 'protocol'])
def test_invalid_distribution_fails_before_process_or_store_mutation(tmp_path, case):
    home, _, _, project = distribution(tmp_path, protocol=2 if case == 'protocol' else 1,
                                       checksum='0' * 64 if case == 'hash' else None)
    store = project / '.kgmaker/graph.json'
    store.parent.mkdir()
    store.write_bytes(b'last valid graph')
    with patch('subprocess.Popen', side_effect=AssertionError('implicit process')):
        with pytest.raises(AnalysisError, match='[Ee]xporter.*(hash|protocol)'):
            create_plan(project, executable='/bin/true', home=home)
    assert store.read_bytes() == b'last valid graph'
    assert not (project / '.kgmaker/build-runs').exists()


def test_changed_distribution_manifest_invalidates_existing_plan(tmp_path):
    home, _, manifest, project = distribution(tmp_path)
    plan = create_plan(project, executable='/bin/true', home=home)
    manifest.write_text(manifest.read_text() + '\n')
    with patch('subprocess.Popen', side_effect=AssertionError('implicit process')):
        with pytest.raises(AnalysisError, match='STALE_PLAN.*distribution'):
            run_plan(plan)
    assert not Path(plan['run_root']).exists()


def test_missing_packaged_descriptor_never_falls_back_to_legacy(tmp_path, monkeypatch):
    home, _, manifest, project = distribution(tmp_path)
    manifest.unlink()
    monkeypatch.delenv('KGMAKER_WORKERS_HOME', raising=False)
    with patch('kgmaker.build_runner.worker_home', return_value=home), \
            patch('subprocess.Popen', side_effect=AssertionError('implicit process')):
        with pytest.raises(AnalysisError, match='descriptor unavailable'):
            create_plan(project, executable='/bin/true')
    assert not (project / '.kgmaker/build-runs').exists()


def test_explicit_legacy_home_preserves_existing_plan_contract(tmp_path):
    home, _, manifest, project = distribution(tmp_path)
    manifest.unlink()
    plan = create_plan(project, executable='/bin/true', home=home)
    assert 'exporter_contract' not in plan
    assert run_plan(plan)['status'] == 'PARTIAL'


def test_output_protocol_mismatch_does_not_publish_manifest_or_graph(tmp_path):
    home, _, _, project = distribution(tmp_path)
    executable = tmp_path / 'build-fixture'
    executable.write_text('#!' + sys.executable + '\nimport sys,json\nfrom pathlib import Path\n'
        "path=next(x.split('=',1)[1] for x in sys.argv if x.startswith('-Dkgmaker.export.path='))\n"
        "Path(path).write_text(json.dumps({'schema_version':99,'exporter':'wrong','contexts':[]}))\n")
    executable.chmod(0o755)
    store = project / '.kgmaker/graph.json'
    store.parent.mkdir()
    store.write_bytes(b'last valid graph')
    plan = create_plan(project, executable=str(executable), home=home)
    with pytest.raises(AnalysisError, match='output protocol mismatch'):
        run_plan(plan)
    assert store.read_bytes() == b'last valid graph'
    assert not (Path(plan['run_root']) / 'manifest.json').exists()


@pytest.fixture(scope='module')
def installed_exporters(tmp_path_factory):
    from test_worker_install import InstalledWorkerTests as WheelBuilder
    # Reuse the real sdist -> offline wheel -> clean venv builder from W01.
    class BuildInputs:
        directory = tmp_path_factory.mktemp('installed-exporters')
        environment = {k: v for k, v in os.environ.items()
                       if k not in {'PYTHONPATH', 'KGMAKER_WORKERS_HOME', 'NODE_PATH'}}
    inputs = BuildInputs
    inputs.python = WheelBuilder.install_wheel.__func__(inputs, 'exporters', source_only=False)
    return inputs


@pytest.mark.parametrize('system', ['maven', 'gradle'])
def test_installed_exporters_run_real_builds_outside_checkout(tmp_path, installed_exporters, system):
    executable = shutil.which('mvn' if system == 'maven' else 'gradle')
    if not executable or not shutil.which('javac'):
        if os.environ.get('KGMAKER_REQUIRE_EXPORTERS') == '1':
            pytest.fail('blocked: real Maven, Gradle and JDK required')
        pytest.skip('blocked: real ' + system + '/JDK unavailable')
    if system == 'maven' and not (ROOT / 'workers/build/maven/target/kgmaker-build-export.jar').is_file():
        reason = 'blocked: explicitly prepared Maven exporter artifact required in this checkout'
        if os.environ.get('KGMAKER_REQUIRE_EXPORTERS') == '1':
            pytest.fail(reason)
        pytest.skip(reason)
    root = tmp_path / system
    (root / 'src/main/java/example').mkdir(parents=True)
    (root / 'src/main/java/example/App.java').write_text('package example; public class App {}\n')
    if system == 'maven':
        (root / 'pom.xml').write_text('''<project xmlns="http://maven.apache.org/POM/4.0.0">
          <modelVersion>4.0.0</modelVersion><groupId>example</groupId><artifactId>installed</artifactId>
          <version>1</version><build><plugins>
          <plugin><artifactId>maven-compiler-plugin</artifactId><version>3.13.0</version>
          <configuration><release>21</release></configuration></plugin>
          <plugin><artifactId>maven-resources-plugin</artifactId><version>3.3.1</version></plugin>
          </plugins></build></project>''')
    else:
        (root / 'settings.gradle').write_text("rootProject.name = 'installed'\n")
        (root / 'build.gradle').write_text("plugins { id 'java' }\n")
    script = '''
import json,sys
from pathlib import Path
from kgmaker.build_runner import create_plan,run_plan
from kgmaker.build_model import validate_manifest
from kgmaker.inspection import worker_home
root=Path(sys.argv[1]); system=sys.argv[2]
assert 'site-packages' in str(worker_home()), worker_home()
plan=create_plan(root,build_system=system,phase='compile',offline=(system=='gradle'),timeout=120)
assert plan['exporter_contract']['schema_version']==1
assert Path(plan['exporter_contract']['license']['path']).is_file()
result=run_plan(plan)
assert result['result']['status']=='SUCCESS', Path(result['result']['log_path']).read_text()
manifest=json.loads(Path(result['manifest_path']).read_text())
validate_manifest(root,manifest)
assert manifest['exporter']==('maven-session-2' if system=='maven' else 'gradle-composite-1')
assert any(c['source_set']=='main' and c['outputs'] for c in manifest['contexts']), manifest
assert (root/'.kgmaker/graph.json').read_bytes()==b'last valid graph'
'''
    (root / '.kgmaker').mkdir()
    (root / '.kgmaker/graph.json').write_bytes(b'last valid graph')
    result = subprocess.run([str(installed_exporters.python), '-c', script, str(root), system],
        cwd=tmp_path, env=installed_exporters.environment, capture_output=True, text=True, timeout=150)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('mandatory', [False, True])
def test_missing_prepared_exporter_is_optional_skip_but_mandatory_failure(tmp_path, monkeypatch, mandatory):
    # Reproduce source-only CI: Maven/JDK executables exist, but no trusted JAR
    # was explicitly built. Never use another editable installation's resources.
    monkeypatch.setattr(sys.modules[__name__], 'ROOT', tmp_path / 'own-checkout')
    monkeypatch.setattr(shutil, 'which', lambda name: '/prepared/tool/' + name)
    monkeypatch.setenv('KGMAKER_REQUIRE_EXPORTERS', '1' if mandatory else '0')
    expected = pytest.fail.Exception if mandatory else pytest.skip.Exception
    with pytest.raises(expected, match='explicitly prepared Maven exporter artifact required'):
        test_installed_exporters_run_real_builds_outside_checkout(tmp_path, None, 'maven')
