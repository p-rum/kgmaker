"""T003-S03-W04: typed options are provenance, never implicit K2 support."""
import copy

import pytest

from kgmaker.analysis_model import AnalysisError, digest
from kgmaker.build_model import validate_manifest


def manifest(options):
    return {"schema_version": 1, "build_id": "options-test", "build_result": {"status": "SUCCESS"},
            "snapshot": {"sources": {}, "content_hash": digest({})}, "contexts": [
                {"id": "main", "repo_id": "local", "module": "root", "source_set": "main",
                 "scope": "production", "source_roots": [], "source_files": [], "classpath": [],
                 "compiler_options": {"kotlin": options}}]}


@pytest.mark.parametrize("options", [
    [], {"language_version": 2.1}, {"api_version": "${unresolved}"},
    {"free_args": "-Xcontext-receivers"}, {"plugins": [None]},
    {"plugin_options": [True]}, {"jvm_target": "21", "status": "COMPLETE"},
])
def test_invalid_kotlin_options_rejected_without_mutation(tmp_path, options):
    if isinstance(options, dict):
        options = {'schema_version': 1, 'status': 'CAPTURED_CONFIGURATION', **options}
    value = manifest(options)
    before = copy.deepcopy(value)
    with pytest.raises(AnalysisError, match="Kotlin"):
        validate_manifest(tmp_path, value)
    assert value == before


def test_old_manifest_and_typed_options_are_compatible(tmp_path):
    options = {"schema_version": 1, "language_version": "1.9", "api_version": "1.9",
               "jvm_target": "21", "free_args": ["-Xjsr305=strict"],
               "plugins": ["spring"], "plugin_options": ["all-open:annotation=example.Open"],
               "status": "CAPTURED_CONFIGURATION"}
    value = manifest(options)
    assert validate_manifest(tmp_path, value) == value
    value["contexts"][0]["compiler_options"] = {"release": "21"}
    assert validate_manifest(tmp_path, value) == value


def test_kotlin_plugin_artifact_change_rejects_manifest_without_store_mutation(tmp_path):
    from kgmaker.analysis_model import file_hash
    from kgmaker.build_model import import_manifest
    plugin = tmp_path / 'kotlin-maven-allopen.jar'
    plugin.write_bytes(b'first-plugin')
    options = {'schema_version': 1, 'status': 'CAPTURED_CONFIGURATION',
               'plugin_artifacts': [{'coordinates': 'org.jetbrains.kotlin:kotlin-maven-allopen:2.1.0',
                                     'path': str(plugin), 'sha256': file_hash(plugin)}]}
    value = manifest(options)
    assert validate_manifest(tmp_path, value) == value
    plugin.write_bytes(b'swapped-plugin')
    with pytest.raises(AnalysisError, match='Kotlin plugin artifact'):
        import_manifest(tmp_path, value)
    assert not (tmp_path / '.kgmaker').exists()


def test_real_maven_kotlin_execution_options(tmp_path):
    import json
    import shutil
    from pathlib import Path
    from kgmaker.build_runner import create_plan, run_plan
    root = Path(__file__).parents[1]
    if not shutil.which('mvn') or not (root / 'workers/build/maven/target/kgmaker-build-export.jar').is_file():
        pytest.skip('blocked: Maven or trusted exporter unavailable')
    project = tmp_path / 'project'
    project.mkdir()
    (project / 'src/main/kotlin').mkdir(parents=True)
    (project / 'src/main/kotlin/Options.kt').write_text('class Options { fun value(): String = "ok" }')
    pom = """<project xmlns="http://maven.apache.org/POM/4.0.0"><modelVersion>4.0.0</modelVersion>
      <groupId>example</groupId><artifactId>options</artifactId><version>1</version>
      <dependencies><dependency><groupId>org.jetbrains.kotlin</groupId><artifactId>kotlin-stdlib</artifactId><version>2.1.10</version></dependency></dependencies>
      <build><plugins><plugin><groupId>org.jetbrains.kotlin</groupId><artifactId>kotlin-maven-plugin</artifactId><version>2.1.10</version>
        <configuration><languageVersion>1.9</languageVersion><apiVersion>1.9</apiVersion>
          <jvmTarget>21</jvmTarget><sourceDirs><sourceDir>src/main/kotlin</sourceDir></sourceDirs><args><arg>-Xjsr305=__MODE__</arg></args></configuration>
        <executions><execution><id>compile-kotlin</id><phase>process-sources</phase><goals><goal>compile</goal></goals></execution></executions>
      </plugin></plugins></build></project>"""
    captured = []
    for mode in ('warn', 'strict'):
        (project / 'pom.xml').write_text(pom.replace('__MODE__', mode))
        result = run_plan(create_plan(project, phase='compile', home=root / 'workers', offline=True))
        assert result['result']['status'] == 'SUCCESS', Path(result['result']['log']).read_text()
        value = validate_manifest(project, json.loads(Path(result['manifest_path']).read_text()))
        options = next(c for c in value['contexts'] if c['source_set'] == 'main')['compiler_options']['kotlin']
        assert options['status'] == 'CAPTURED_CONFIGURATION'
        assert options['language_version'] == options['api_version'] == '1.9'
        assert options['jvm_target'] == '21'
        assert options['free_args'] == ['-Xjsr305=' + mode]
        selected = next(c for c in value['contexts'] if c['source_set'] == 'main')
        assert any((Path(o['path']) / 'Options.class').is_file() for o in selected['outputs'])
        from kgmaker.build_model import inspection_inputs
        assert inspection_inputs(project, value, context_id=selected['id'], scope='production')['build_context']['compiler_options']['kotlin'] == options
        captured.append(options)
    assert digest(captured[0]) != digest(captured[1])

    (project / 'pom.xml').write_text(pom.replace('__MODE__', 'warn').replace(
        '<languageVersion>1.9</languageVersion><apiVersion>1.9</apiVersion>', ''))
    implicit = run_plan(create_plan(project, phase='compile', home=root / 'workers', offline=True))
    assert implicit['result']['status'] == 'SUCCESS'
    assert implicit['status'] == 'PARTIAL'
    implicit_manifest = validate_manifest(project, json.loads(Path(implicit['manifest_path']).read_text()))
    implicit_context = next(c for c in implicit_manifest['contexts'] if c['source_set'] == 'main')
    implicit_options = implicit_context['compiler_options']['kotlin']
    assert implicit_options['status'] == 'PARTIAL'
    assert 'language_version' not in implicit_options and 'api_version' not in implicit_options
    assert any(item['code'] == 'KOTLIN_OPTION_UNRESOLVED_DEFAULT' for item in implicit_options['diagnostics'])
    assert implicit_context['diagnostics'] == implicit_options['diagnostics']
    assert implicit_options['plugin_artifacts']

    all_open_pom = (pom.replace('2.1.10', '1.9.25').replace('__MODE__', 'warn')
                    .replace('</args></configuration>',
                             '</args><compilerPlugins><plugin>all-open</plugin></compilerPlugins>'
                             '<pluginOptions><option>all-open:annotation=example.Open</option></pluginOptions></configuration>')
                    .replace('</plugin></plugins>',
                             '<dependencies><dependency><groupId>org.jetbrains.kotlin</groupId>'
                             '<artifactId>kotlin-maven-allopen</artifactId><version>1.9.25</version>'
                             '</dependency></dependencies></plugin></plugins>'))
    (project / 'pom.xml').write_text(all_open_pom)
    all_open = run_plan(create_plan(project, phase='compile', home=root / 'workers', offline=True))
    assert all_open['result']['status'] == 'SUCCESS'
    all_open_manifest = validate_manifest(project, json.loads(Path(all_open['manifest_path']).read_text()))
    all_open_options = next(c for c in all_open_manifest['contexts'] if c['source_set'] == 'main')['compiler_options']['kotlin']
    assert all_open_options['status'] == 'CAPTURED_CONFIGURATION'
    assert 'all-open' in all_open_options['plugins']
    assert any('kotlin-maven-allopen' in item['coordinates'] for item in all_open_options['plugin_artifacts'])


def test_real_gradle_kotlin_task_options(tmp_path):
    import json
    import os
    from pathlib import Path
    from kgmaker.build_runner import create_plan, run_plan
    root = Path(__file__).parents[1]
    executable = os.environ.get('KGMAKER_TEST_GRADLE')
    if not executable:
        pytest.skip('blocked: set KGMAKER_TEST_GRADLE to a Gradle 8.13 executable with Kotlin 2.2.20 cache')
    project = tmp_path / 'gradle-options'
    project.mkdir()
    (project / 'settings.gradle').write_text("""pluginManagement {
        repositories { mavenCentral(); gradlePluginPortal() }
        resolutionStrategy { eachPlugin { if (requested.id.id == 'org.jetbrains.kotlin.jvm')
          useModule('org.jetbrains.kotlin:kotlin-gradle-plugin:2.2.20') } }
      }
      rootProject.name = 'kotlin-options'""")
    (project / 'src/main/kotlin').mkdir(parents=True)
    (project / 'src/main/kotlin/Options.kt').write_text('class Options { fun value() = "ok" }')
    build = """plugins { id 'org.jetbrains.kotlin.jvm' version '2.2.20' }
      repositories { mavenCentral() }
      kotlin { compilerOptions {
        languageVersion = org.jetbrains.kotlin.gradle.dsl.KotlinVersion.KOTLIN_1_9
        apiVersion = org.jetbrains.kotlin.gradle.dsl.KotlinVersion.KOTLIN_1_9
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_21
        freeCompilerArgs.add('-Xjsr305=__MODE__')
      } }
    """
    captured = []
    for mode in ('warn', 'strict'):
        (project / 'build.gradle').write_text(build.replace('__MODE__', mode))
        result = run_plan(create_plan(project, phase='compile', home=root / 'workers', executable=executable,
                                      offline=os.environ.get('KGMAKER_TEST_GRADLE_ONLINE') != '1', timeout=180))
        assert result['result']['status'] == 'SUCCESS', result
        value = validate_manifest(project, json.loads(Path(result['manifest_path']).read_text()))
        selected = next(c for c in value['contexts'] if c['source_set'] == 'main')
        options = selected['compiler_options']['kotlin']
        assert options['status'] == 'CAPTURED_CONFIGURATION', options
        assert options['compiler_version'] == '2.2.20'
        assert options['language_version'] == options['api_version'] == '1.9'
        assert options['jvm_target'] == '21'
        assert '-Xjsr305=' + mode in options['free_args']
        assert selected['outputs'], 'actual Kotlin compile output required'
        captured.append(options)
    assert digest(captured[0]) != digest(captured[1])


def test_kotlin_options_change_context_identity_without_other_context_mutation(tmp_path):
    from kgmaker.inspection import context
    from kgmaker.scanner import scan_repository
    source = tmp_path / 'src/main/kotlin/Options.kt'
    source.parent.mkdir(parents=True)
    source.write_text('class Options')
    base = scan_repository(tmp_path)
    def selected(module, flag):
        return context(tmp_path, base, 'jvm', {}, repo_id='local', module=module,
                       source_set='main', scope='production', build_context={
                           'compiler_options': {'kotlin': {'schema_version': 1,
                               'status': 'CAPTURED_CONFIGURATION', 'free_args': [flag]}}})
    before = selected('a', '-Xjsr305=warn')
    unrelated = selected('b', '-Xjsr305=warn')
    after = selected('a', '-Xjsr305=strict')
    assert before['id'] != after['id']
    assert before['selection_key'] != after['selection_key']
    assert unrelated == selected('b', '-Xjsr305=warn')


def test_kotlin_configuration_tamper_is_stale_offline(tmp_path):
    from unittest.mock import patch
    from kgmaker.graph_provider import validate_context_snapshot
    from kgmaker.inspection import context
    from kgmaker.scanner import scan_repository
    from kgmaker.worker_protocol import WorkerError
    base = scan_repository(tmp_path)
    selected = context(tmp_path, base, 'jvm', {}, repo_id='local', module='a',
                       source_set='main', scope='production', build_context={
                           'compiler_options': {'kotlin': {'schema_version': 1,
                               'status': 'CAPTURED_CONFIGURATION', 'language_version': '1.9'}}})
    untouched = copy.deepcopy(selected)
    with patch('subprocess.Popen', side_effect=AssertionError('implicit process')):
        validate_context_snapshot(tmp_path, selected)
        selected['compiler_options']['kotlin']['language_version'] = '2.1'
        with pytest.raises(WorkerError, match='Kotlin compiler context configuration changed'):
            validate_context_snapshot(tmp_path, selected)
        validate_context_snapshot(tmp_path, untouched)
