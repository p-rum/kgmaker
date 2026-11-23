"""Independent safety/freshness and actual XML test-state invariants."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import pytest
from kgmaker.analysis_model import AnalysisError, digest, file_hash
from kgmaker.build_runner import create_plan, run_plan, snapshot, tests_report as report_tests
from kgmaker.build_model import inspection_inputs, validate_manifest
from kgmaker.inspection import inspect_jvm


ROOT = Path(__file__).parents[1]


def test_mv02_real_reactor_output_precedes_stale_repository_jar(tmp_path, monkeypatch):
    required = [shutil.which(name) for name in ('mvn', 'javac', 'jar')]
    exporter = ROOT / 'workers/build/maven/target/kgmaker-build-export.jar'
    if not all(required) or not exporter.is_file():
        pytest.skip('blocked: Maven/JDK or trusted build exporter is unavailable')
    root = tmp_path / 'reactor'
    root.mkdir()
    cache_uri = (Path.home() / '.m2/repository').as_uri()
    (root / 'pom.xml').write_text('''<project xmlns="http://maven.apache.org/POM/4.0.0">
      <modelVersion>4.0.0</modelVersion>
      <groupId>example</groupId><artifactId>parent</artifactId><version>1</version><packaging>pom</packaging>
      <modules><module>processor</module><module>lib</module><module>app</module></modules>
      <properties><maven.compiler.release>21</maven.compiler.release><fixture.generated>base</fixture.generated>
        <fixture.bom.version>1</fixture.bom.version></properties>
      <dependencyManagement><dependencies><dependency>
        <groupId>example</groupId><artifactId>platform-bom</artifactId><version>${fixture.bom.version}</version>
        <type>pom</type><scope>import</scope>
      </dependency></dependencies></dependencyManagement>
      <profiles><profile><id>extra</id><properties><fixture.profile>active</fixture.profile>
        <fixture.generated>extra</fixture.generated></properties></profile></profiles>
      <build><pluginManagement><plugins><plugin><groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-compiler-plugin</artifactId><version>3.10.1</version>
        <configuration><generatedSourcesDirectory>${project.build.directory}/generated-sources/${fixture.generated}</generatedSourcesDirectory></configuration>
      </plugin></plugins></pluginManagement></build>
      <repositories><repository><id>stale-file-repo</id>
        <url>file://${maven.multiModuleProjectDirectory}/repo</url>
      </repository><repository><id>host-cache</id><url>__CACHE__</url></repository></repositories>
      <pluginRepositories><pluginRepository><id>host-plugin-cache</id>
        <url>__CACHE__</url></pluginRepository></pluginRepositories>
    </project>'''.replace('__CACHE__', cache_uri))
    parent = '''<parent><groupId>example</groupId><artifactId>parent</artifactId><version>1</version></parent>'''
    for module in ('processor', 'lib', 'app'):
        (root / module / 'src/main/java/example').mkdir(parents=True)
    (root / 'processor/pom.xml').write_text(f'''<project xmlns="http://maven.apache.org/POM/4.0.0">
      <modelVersion>4.0.0</modelVersion>{parent}<artifactId>processor</artifactId></project>''')
    (root / 'processor/src/main/java/example/GenerateProcessor.java').write_text('''package example;
      import java.io.Writer; import java.util.Set;
      import javax.annotation.processing.*; import javax.lang.model.SourceVersion;
      import javax.lang.model.element.TypeElement;
      @SupportedAnnotationTypes("*") @SupportedSourceVersion(SourceVersion.RELEASE_21)
      public final class GenerateProcessor extends AbstractProcessor {
        private boolean done;
        public boolean process(Set<? extends TypeElement> annotations, RoundEnvironment round) {
          if (!done) { done=true; try (Writer w=processingEnv.getFiler().createSourceFile("example.GeneratedMarker").openWriter()) {
            w.write("package example; public final class GeneratedMarker { public static String value() { return \\\"generated\\\"; } }");
          } catch (Exception e) { throw new IllegalStateException(e); } }
          return false;
        }
      }''')
    (root / 'lib/pom.xml').write_text(f'''<project xmlns="http://maven.apache.org/POM/4.0.0">
      <modelVersion>4.0.0</modelVersion>{parent}<artifactId>lib</artifactId></project>''')
    (root / 'app/pom.xml').write_text(f'''<project xmlns="http://maven.apache.org/POM/4.0.0">
      <modelVersion>4.0.0</modelVersion>{parent}<artifactId>app</artifactId>
      <dependencies><dependency><groupId>example</groupId><artifactId>lib</artifactId></dependency></dependencies>
      <build><plugins><plugin><groupId>org.apache.maven.plugins</groupId><artifactId>maven-compiler-plugin</artifactId>
        <configuration><annotationProcessorPaths><path><groupId>example</groupId><artifactId>processor</artifactId>
          <version>1</version></path></annotationProcessorPaths><compilerArgs><arg>-processor</arg>
          <arg>example.GenerateProcessor</arg></compilerArgs></configuration></plugin></plugins></build>
    </project>''')
    (root / 'lib/src/main/java/example/Lib.java').write_text(
        'package example; public class Lib { public static String freshOnly() { return "fresh"; } }')
    (root / 'app/src/main/java/example/App.java').write_text(
        'package example; public class App { String value() { return Lib.freshOnly(); } }')

    old_source = root / 'old-src/example/Lib.java'
    old_source.parent.mkdir(parents=True)
    old_source.write_text(
        'package example; public class Lib { public static String oldOnly() { return "old"; } }')
    old_classes = root / 'old-classes'
    old_classes.mkdir()
    subprocess.run([required[1], '-d', str(old_classes), str(old_source)], check=True)
    stale = root / 'repo/example/lib/1/lib-1.jar'
    stale.parent.mkdir(parents=True)
    subprocess.run([required[2], '--create', '--file', str(stale), '-C', str(old_classes), '.'], check=True)
    (stale.parent / 'lib-1.pom').write_text('''<project xmlns="http://maven.apache.org/POM/4.0.0">
      <modelVersion>4.0.0</modelVersion><groupId>example</groupId><artifactId>lib</artifactId><version>1</version>
    </project>''')
    bom = root / 'repo/example/platform-bom/1/platform-bom-1.pom'
    bom.parent.mkdir(parents=True)
    bom.write_text('''<project xmlns="http://maven.apache.org/POM/4.0.0">
      <modelVersion>4.0.0</modelVersion><groupId>example</groupId>
      <artifactId>platform-bom</artifactId><version>1</version><packaging>pom</packaging>
      <dependencyManagement><dependencies><dependency><groupId>example</groupId>
        <artifactId>lib</artifactId><version>1</version>
      </dependency></dependencies></dependencyManagement>
    </project>''')

    monkeypatch.setenv('MAVEN_OPTS', '-Dmaven.repo.local=.m2')
    real_java_home = Path(required[1]).resolve().parents[1]
    result = run_plan(create_plan(root, phase='compile', build_system='maven',
                                  executable=required[0], home=ROOT / 'workers', profiles=['extra'],
                                  java_home=real_java_home))
    assert result['result']['status'] == 'SUCCESS', Path(result['result']['log_path']).read_text()
    manifest = json.loads(Path(result['manifest_path']).read_text())
    validated = validate_manifest(root, manifest)
    assert validated['exporter'] == 'maven-session-2'
    app = next(item for item in manifest['contexts']
               if item['module'] == 'app' and item['source_set'] == 'main')
    sibling = [item for item in app['classpath']
               if item.get('realm', {}).get('module') == 'lib']
    assert len(sibling) == 1
    assert sibling[0]['path'].endswith('/lib/target/classes')
    assert sibling[0]['sha256'] != file_hash(stale)
    assert all(item['path'] != str(stale) for item in app['classpath'])
    assert app['build_profiles'] == ['extra']
    assert app['parent'] == {'group_id': 'example', 'artifact_id': 'parent', 'version': '1'}
    assert any(item['artifact_id'] == 'lib' and item['version'] == '1'
               for item in app['effective_dependencies'])
    assert any(item['artifact_id'] == 'lib' and item['version'] == '1'
               for item in app['dependency_management'])
    assert any(item['artifact_id'] == 'platform-bom' and item['version'] == '1'
               for item in app['imported_boms'])
    root_context = next(item for item in manifest['contexts']
                        if item['module'] == 'root' and item['source_set'] == 'main')
    assert root_context['imported_boms'] == [{
        'group_id': 'example', 'artifact_id': 'platform-bom', 'version': '1',
        'scope': 'import', 'type': 'pom', 'classifier': None, 'optional': False,
    }]
    assert app['compiler_options']['release'] == '21'
    assert all(app['toolchain'][key] for key in
               ('java_version', 'java_home', 'java_vendor', 'maven_version'))
    assert Path(app['toolchain']['java_home']).resolve() == real_java_home
    assert manifest['toolchain_selection']['java_home'] == str(real_java_home)
    assert any(path.endswith('target/generated-sources/extra')
               for path in app['generated_source_roots'])
    assert len(app['generated_sources']) == 1
    generated = app['generated_sources'][0]
    assert generated['path'].endswith('app/target/generated-sources/extra/example/GeneratedMarker.java')
    assert generated['execution_id'] == manifest['build_result']['execution_id']
    assert file_hash(root / generated['path']) == generated['sha256']
    inputs = inspection_inputs(root, manifest, context_id=app['id'], scope='production')
    assert inputs['build_context']['generated_source_roots'] == app['generated_source_roots']
    assert inputs['build_context']['toolchain'] == app['toolchain']
    assert inputs['build_context']['dependency_model']['effective_dependencies'] == app['effective_dependencies']
    assert inputs['build_context']['dependency_model_hash']
    generated_set = next(item for item in inputs['project_model']['source_sets'] if item.get('generated'))
    assert generated_set['files'] == [generated['path']]
    inspected = inspect_jvm(root, **inputs, home=ROOT / 'workers', publish=False)
    marker = next(node for node in inspected['graph']['nodes']
                  if node['name'] == 'GeneratedMarker' and node['kind'] == 'class')
    assert marker['origin'] == 'generated'
    generated_path = root / generated['path']
    generated_content = generated_path.read_text()
    generated_path.write_text(generated_content + '// tampered after build\n')
    with pytest.raises(AnalysisError, match='STALE_GENERATED_SOURCE'):
        validate_manifest(root, manifest)
    generated_path.write_text(generated_content)

    baseline_result = run_plan(create_plan(root, phase='compile', build_system='maven',
                                           executable=required[0], home=ROOT / 'workers',
                                           java_home=real_java_home))
    assert baseline_result['result']['status'] == 'SUCCESS', Path(baseline_result['result']['log_path']).read_text()
    baseline_manifest = json.loads(Path(baseline_result['manifest_path']).read_text())
    baseline_app = next(item for item in baseline_manifest['contexts']
                        if item['module'] == 'app' and item['source_set'] == 'main')
    assert baseline_app['build_profiles'] == []
    assert any(path.endswith('target/generated-sources/base')
               for path in baseline_app['generated_source_roots'])
    assert baseline_app['generated_source_roots'] != app['generated_source_roots']


def test_inventory_includes_untracked_extensionless_and_rejects_links(tmp_path):
    (tmp_path/'custom-input').write_text('one')
    (tmp_path/'target').mkdir();(tmp_path/'target/old.jar').write_text('old')
    before=snapshot(tmp_path)
    assert set(before)=={'custom-input'}
    (tmp_path/'added.kt').write_text('class Added')
    assert snapshot(tmp_path)!=before
    (tmp_path/'link').symlink_to(tmp_path/'custom-input')
    with pytest.raises(AnalysisError,match='Symlink'):snapshot(tmp_path)


def test_xml_build_pass_is_not_test_pass(tmp_path):
    assert report_tests(tmp_path,'test-compile')['status']=='NOT_RUN'
    assert report_tests(tmp_path,'test')['status']=='NOT_RUN'
    reports=tmp_path/'target/surefire-reports';reports.mkdir(parents=True)
    report=reports/'TEST-one.xml'
    report.write_text('<testsuite tests="0"/>')
    assert report_tests(tmp_path,'test')['status']=='ZERO_TESTS'
    report.write_text('<testsuite tests="2" skipped="2"/>')
    assert report_tests(tmp_path,'test')['status']=='SKIPPED'
    report.write_text('<testsuite tests="3" failures="1" skipped="1"/>')
    result=report_tests(tmp_path,'test')
    assert result['status']=='FAILED' and result['executed']==2 and result['passed']==1


def test_stale_plan_never_launches(tmp_path):
    (tmp_path/'pom.xml').write_text('<project/>')
    exporter=tmp_path/'tools/build/maven/target/kgmaker-build-export.jar';exporter.parent.mkdir(parents=True);exporter.write_text('placeholder never executed')
    plan=create_plan(tmp_path,executable='/bin/true',home=tmp_path/'tools')
    (tmp_path/'untracked').write_text('changed')
    with pytest.raises(AnalysisError,match='STALE_PLAN'):run_plan(plan)
    assert not Path(plan['run_root']).exists()


def test_execution_is_one_shot_and_no_export_is_partial(tmp_path):
    (tmp_path/'pom.xml').write_text('<project/>')
    exporter=tmp_path/'tools/build/maven/target/kgmaker-build-export.jar';exporter.parent.mkdir(parents=True);exporter.write_text('placeholder never loaded by true')
    plan=create_plan(tmp_path,executable='/bin/true',home=tmp_path/'tools')
    result=run_plan(plan)
    assert result['status']=='PARTIAL'
    assert result['result']['tests']['status']=='NOT_RUN'
    with pytest.raises(AnalysisError,match='already executed'):run_plan(plan)


def test_failed_build_cannot_claim_old_fresh_output(tmp_path):
    source=tmp_path/'A.java';source.write_text('class A {}')
    jar=tmp_path/'old.jar';jar.write_bytes(b'old')
    sources={'A.java':file_hash(source)}
    manifest={'schema_version':1,'build_id':'old','snapshot':{'sources':sources,'content_hash':digest(sources)},
      'build_result':{'status':'FAILED','execution_id':'run'},'contexts':[{'id':'main','repo_id':'fixture','module':'root','source_set':'main','scope':'production',
        'source_roots':['src/main'],'source_files':['A.java'],'classpath':[],'outputs':[{'path':'old.jar','sha256':file_hash(jar),'execution_id':'run','snapshot_hash':digest(sources),'freshness':'EXECUTION_BOUND'}]}]}
    with pytest.raises(AnalysisError,match='cannot supply fresh'):validate_manifest(tmp_path,manifest)


def test_relative_import_artifacts_are_root_relative_not_cwd(tmp_path):
    from kgmaker.build_model import inspection_inputs
    source=tmp_path/'A.java';source.write_text('class A {}')
    library=tmp_path/'library.jar';library.write_bytes(b'opaque supplied artifact; no compiler is executed')
    sources={'A.java':file_hash(source),'library.jar':file_hash(library)}
    manifest={'schema_version':1,'build_id':'relative','snapshot':{'sources':sources,'content_hash':digest(sources),'inventory':'ALL_BUILD_INPUTS_V1'},
        'build_result':{'status':'SUCCESS'},'contexts':[{'id':'custom:main','repo_id':'fixture','module':'custom','source_set':'main','scope':'production',
        'source_roots':['src/main'],'source_files':['A.java'],'classpath':[{'path':'library.jar','sha256':file_hash(library)}],'outputs':[]}]}
    inputs=inspection_inputs(tmp_path,manifest,context_id='custom:main',scope='production')
    assert inputs['classpath'][0]['path']==str(library)
    assert inputs['sources']==['A.java'] and inputs['module']=='custom' and inputs['repo_id']=='fixture'


@pytest.fixture
def configuration_manifest():
    def context(source_set, scope):
        return {"id": "root:" + source_set, "repo_id": "local", "module": "root",
                "source_set": source_set, "scope": scope, "source_roots": [], "source_files": [],
                "classpath": []}

    return {"schema_version": 1, "build_id": "config-fixture", "build_result": {"status": "SUCCESS"},
            "snapshot": {"sources": {}, "content_hash": digest({})},
            "contexts": [context("main", "production"), context("test", "test")]}


def test_build_context_config_fingerprint_comes_from_selected_context(tmp_path, configuration_manifest):
    manifest = configuration_manifest
    manifest["config_fingerprint"] = "a" * 64
    main, test = manifest["contexts"]
    test["config_fingerprint"] = "b" * 64
    legacy = inspection_inputs(tmp_path, manifest, context_id=main["id"], scope="production")["build_context"]
    assert "config_fingerprint" not in legacy
    main["config_fingerprint"] = "c" * 64
    for selected in (main, test):
        captured = inspection_inputs(tmp_path, manifest, context_id=selected["id"],
                                     scope=selected["scope"])["build_context"]
        assert captured["config_fingerprint"] == selected["config_fingerprint"]
        assert captured["manifest_hash"] == digest(manifest)


@pytest.mark.parametrize("value", [None, True, 1, {}, "", "a" * 63, "a" * 65, "A" * 64, "g" * 64, "a" * 64 + "\n"])
def test_build_manifest_rejects_invalid_context_config_fingerprint(tmp_path, configuration_manifest, value):
    configuration_manifest["contexts"][0]["config_fingerprint"] = value
    with pytest.raises(AnalysisError, match="config_fingerprint"):
        validate_manifest(tmp_path, configuration_manifest)


def test_actual_xml_test_execution_is_visible_even_before_test_phase(tmp_path):
    reports=tmp_path/'target/surefire-reports';reports.mkdir(parents=True)
    (reports/'TEST-custom-phase.xml').write_text('<testsuite tests="1" failures="0" skipped="0"/>')
    result=report_tests(tmp_path,'test-compile')
    assert result['status']=='PASSED' and result['executed']==1


def test_failed_result_without_model_is_a_valid_partial_import(tmp_path):
    from kgmaker.build_model import import_manifest, inspection_inputs
    source=tmp_path/'pom.xml';source.write_text('<project/>')
    sources={'pom.xml':file_hash(source)}
    manifest={'schema_version':1,'build_id':'failed','snapshot':{'sources':sources,'content_hash':digest(sources),'inventory':'ALL_BUILD_INPUTS_V1'},
              'build_result':{'status':'FAILED','execution_id':'failed'},'contexts':[]}
    result=import_manifest(tmp_path,manifest)
    assert result['status']=='PARTIAL' and result['build_result']['status']=='FAILED'
    with pytest.raises(AnalysisError,match='BUILD_ARTIFACT_UNAVAILABLE'):
        inspection_inputs(tmp_path,manifest,context_id=None,scope='production')


def test_project_mutating_copied_inputs_cannot_produce_fresh_analysis(tmp_path):
    root=tmp_path/'project';root.mkdir();(root/'pom.xml').write_text('<project/>');(root/'input').write_text('original')
    tool=tmp_path/'tool.sh';tool.write_text('#!/bin/sh\nprintf changed > input\n');tool.chmod(0o755)
    exporter=tmp_path/'tools/build/maven/target/kgmaker-build-export.jar';exporter.parent.mkdir(parents=True);exporter.write_text('trusted exporter placeholder; not loaded by this safety-test child')
    result=run_plan(create_plan(root,executable=str(tool),home=tmp_path/'tools'))
    assert result['status']=='PARTIAL'
    assert result['result']['freshness']=='MIXED_BUILD_INPUTS'
    assert (root/'input').read_text()=='original'
    assert any(d['code']=='BUILD_INPUTS_CHANGED_DURING_EXECUTION' for d in result['diagnostics'])


def _fake_jdk(path: Path, marker: str = 'one') -> Path:
    home = path / marker
    binary = home / 'bin'
    binary.mkdir(parents=True)
    for name in ('java', 'javac'):
        tool = binary / name
        tool.write_text('#!/bin/sh\nexit 0\n')
        tool.chmod(0o755)
    return home


def _fake_maven(path: Path, *, reported_java_home: str = '$JAVA_HOME') -> Path:
    tool = path / 'mvn-fixture'
    tool.write_text(f'''#!/bin/sh
for argument in "$@"; do
  case "$argument" in
    -Dkgmaker.export.path=*) export_path="${{argument#*=}}" ;;
  esac
done
cat > "$export_path" <<EOF
{{"schema_version":1,"exporter":"fixture","contexts":[{{"id":"root:main","module":"root","source_set":"main","scope":"production","source_roots":[],"source_files":[],"classpath_paths":[],"output_paths":[],"build_system":"maven","build_profiles":[],"compiler_options":{{}},"toolchain":{{"java_version":"21-fixture","java_home":"{reported_java_home}","java_vendor":"fixture","maven_version":"fixture"}}}}],"modules":{{"root":"SUCCESS"}},"diagnostics":[]}}
EOF
''')
    tool.chmod(0o755)
    return tool


def test_explicit_java_home_is_content_bound_and_used_by_build(tmp_path):
    root = tmp_path / 'project'
    root.mkdir()
    (root / 'pom.xml').write_text('<project/>')
    exporter = tmp_path / 'tools/build/maven/target/kgmaker-build-export.jar'
    exporter.parent.mkdir(parents=True)
    exporter.write_text('trusted fixture exporter')
    jdk = _fake_jdk(tmp_path / 'jdks')
    tool = _fake_maven(tmp_path)

    plan = create_plan(root, phase='compile', build_system='maven', executable=str(tool),
                       home=tmp_path / 'tools', java_home=jdk, environment=['PATH'])
    assert plan['toolchain_selection']['selection'] == 'EXPLICIT_JAVA_HOME'
    assert plan['toolchain_selection']['java_home'] == str(jdk.resolve())
    assert plan['toolchain_selection']['executables']['java']['sha256'] == file_hash(jdk / 'bin/java')
    result = run_plan(plan)
    assert result['status'] == 'SUCCESS'
    manifest = json.loads(Path(result['manifest_path']).read_text())
    assert manifest['toolchain_selection'] == plan['toolchain_selection']
    assert manifest['contexts'][0]['toolchain']['java_home'] == str(jdk.resolve())
    assert validate_manifest(root, manifest)['toolchain_selection']['fingerprint'] == plan['toolchain_selection']['fingerprint']
    tampered = json.loads(json.dumps(manifest))
    tampered['toolchain_selection']['java_home'] = str((tmp_path / 'other').resolve())
    with pytest.raises(AnalysisError, match='fingerprint mismatch'):
        validate_manifest(root, tampered)

    second = _fake_jdk(tmp_path / 'jdks', 'two')
    other = create_plan(root, phase='compile', build_system='maven', executable=str(tool),
                        home=tmp_path / 'tools', java_home=second)
    assert other['toolchain_selection']['fingerprint'] != plan['toolchain_selection']['fingerprint']
    (jdk / 'bin/javac').write_text('changed compiler')
    with pytest.raises(AnalysisError, match='STALE_TOOLCHAIN'):
        validate_manifest(root, manifest)


def test_missing_changed_or_ignored_explicit_java_home_never_publishes_fresh_outputs(tmp_path):
    root = tmp_path / 'project'
    root.mkdir()
    (root / 'pom.xml').write_text('<project/>')
    exporter = tmp_path / 'tools/build/maven/target/kgmaker-build-export.jar'
    exporter.parent.mkdir(parents=True)
    exporter.write_text('trusted fixture exporter')
    tool = _fake_maven(tmp_path)

    with pytest.raises(AnalysisError, match='TOOLCHAIN_UNAVAILABLE'):
        create_plan(root, executable=str(tool), home=tmp_path / 'tools',
                    java_home=tmp_path / 'missing-jdk')

    jdk = _fake_jdk(tmp_path / 'jdks')
    plan = create_plan(root, executable=str(tool), home=tmp_path / 'tools', java_home=jdk)
    (jdk / 'bin/java').write_text('#!/bin/sh\nexit 2\n')
    with pytest.raises(AnalysisError, match='STALE_PLAN'):
        run_plan(plan)
    assert not Path(plan['run_root']).exists()

    mismatch_jdk = _fake_jdk(tmp_path / 'jdks', 'mismatch')
    mismatch_tool = _fake_maven(tmp_path, reported_java_home=str(mismatch_jdk.resolve()))
    mismatch_plan = create_plan(root, executable=str(mismatch_tool), home=tmp_path / 'tools', java_home=jdk)
    mismatch = run_plan(mismatch_plan)
    assert mismatch['result']['status'] == 'TOOLCHAIN_UNAVAILABLE'
    manifest = json.loads(Path(mismatch['manifest_path']).read_text())
    assert all(not context['outputs'] for context in manifest['contexts'])
    assert any(item['code'] == 'EXPLICIT_TOOLCHAIN_MISMATCH' for item in mismatch['diagnostics'])


def test_external_toolchain_two_real_jdks(tmp_path):
    """T003-S03-W01-AC01: explicit selection reaches the real Maven exporter."""
    homes = [Path(os.environ.get('KGMAKER_TEST_OTHER_JAVA_HOME', '/usr/lib/jvm/java-22-openjdk-amd64')),
             Path('/usr/lib/jvm/java-21-openjdk-amd64')]
    if not shutil.which('mvn') or not all((home / 'bin/javac').is_file() for home in homes):
        pytest.skip('blocked: two real JDKs (21+) and Maven are required')
    if not (ROOT / 'workers/build/maven/target/kgmaker-build-export.jar').is_file():
        pytest.skip('blocked: trusted Maven build exporter is unavailable')
    root = tmp_path / 'project'
    root.mkdir()
    (root / 'pom.xml').write_text('''<project xmlns="http://maven.apache.org/POM/4.0.0">
      <modelVersion>4.0.0</modelVersion><groupId>example</groupId><artifactId>toolchains</artifactId>
      <version>1</version><properties><maven.compiler.release>17</maven.compiler.release></properties>
      <build><plugins><plugin><groupId>org.apache.maven.plugins</groupId>
      <artifactId>maven-compiler-plugin</artifactId><version>3.10.1</version></plugin></plugins></build>
      </project>''')
    source = root / 'src/main/java/Example.java'
    source.parent.mkdir(parents=True)
    source.write_text('public class Example {}')
    test_source = root / 'src/test/java/ExampleTest.java'
    test_source.parent.mkdir(parents=True)
    test_source.write_text('public class ExampleTest {}')
    manifests = []
    for home in homes:
        plan = create_plan(root, phase='test-compile', build_system='maven', java_home=home, offline=True)
        result = run_plan(plan)
        assert result['status'] == 'SUCCESS', result
        manifest = json.loads(Path(result['manifest_path']).read_text())
        validate_manifest(root, manifest)
        assert manifest['contexts']
        assert all(Path(c['toolchain']['java_home']).resolve() == home.resolve()
                   for c in manifest['contexts'])
        manifests.append(manifest)
    assert manifests[0]['toolchain_selection']['fingerprint'] != manifests[1]['toolchain_selection']['fingerprint']
    assert manifests[0]['contexts'][0]['toolchain']['java_version'] != manifests[1]['contexts'][0]['toolchain']['java_version']


def test_one_time_build_claim_rejects_an_existing_concurrent_owner(tmp_path, monkeypatch):
    (tmp_path / 'build.gradle').write_text('')
    adapter = tmp_path / 'tools/build/gradle/export.gradle'
    adapter.parent.mkdir(parents=True)
    adapter.write_text('')
    plan = create_plan(tmp_path, executable='/bin/true', home=tmp_path / 'tools')
    run = Path(plan['run_root'])
    work = Path(plan['cwd'])
    create = Path.mkdir

    def concurrent_claim(path, *args, **kwargs):
        if path in {run, work} and not run.exists():
            create(run, parents=True)
            (run / 'owner').write_text('first writer')
        return create(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'mkdir', concurrent_claim)
    with pytest.raises(AnalysisError, match='already executed'):
        run_plan(plan)
    assert (run / 'owner').read_text() == 'first writer'
    assert not work.exists()
