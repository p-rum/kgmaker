"""T003-S03-W02: model-defined custom sets, never name-based scope promotion."""
import json
import os
from pathlib import Path

import pytest

from kgmaker.build_runner import create_plan, run_plan
from kgmaker.build_model import inspection_inputs
from kgmaker.classification import Classifier

ROOT = Path(__file__).parents[1]


def test_real_gradle_custom_variants_and_unknown_scope(tmp_path):
    gradle = os.environ.get('KGMAKER_TEST_GRADLE')
    if not gradle or not Path(gradle).is_file():
        pytest.skip('BLOCKED: set KGMAKER_TEST_GRADLE to supported Gradle 8.13')
    (tmp_path / 'settings.gradle').write_text("rootProject.name='custom-variants'\n")
    (tmp_path / 'build.gradle').write_text('''plugins { id 'java' }
sourceSets {
    integration { java.srcDir 'custom/integration' }
    contest { java.srcDir 'src/main/contest' }
}
ext.kgmakerSourceSetScopes = [integration:'test']
def generated = layout.buildDirectory.dir('generated/sources/annotationProcessor/java/main')
sourceSets.main.java.srcDir(generated)
tasks.register('generateMain') {
    outputs.dir(generated)
    doLast {
        def f = generated.get().file('Generated.java').asFile
        f.parentFile.mkdirs(); f.text = 'class Generated {}'
    }
}
tasks.named('compileJava') { dependsOn('generateMain') }
''')
    for name in ['src/main/java/Main.java', 'src/test/java/Test.java',
                 'custom/integration/Integration.java', 'src/main/contest/Contest.java']:
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('class ' + p.stem + ' {}')
    plan = create_plan(tmp_path, executable=gradle, home=ROOT/'workers', offline=True)
    result = run_plan(plan)
    manifest = json.loads(Path(result['manifest_path']).read_text())
    assert manifest['build_result']['status'] == 'SUCCESS', manifest['build_result']
    contexts = {c['source_set']: c for c in manifest['contexts']}
    assert contexts['integration']['scope'] == 'test'
    assert contexts['integration']['scope_origin'] == 'EXPLICIT_MAPPING'
    assert contexts['contest']['scope'] == 'unknown'
    assert contexts['contest']['scope_origin'] == 'UNKNOWN'
    assert contexts['contest']['diagnostics'][0]['code'] == 'UNMAPPED_GRADLE_SOURCE_SET'
    for name, scope in [('main', 'production'), ('test', 'test'), ('integration', 'test')]:
        c = contexts[name]
        inputs = inspection_inputs(tmp_path, manifest, context_id=c['id'], scope=scope)
        classifier = Classifier(tmp_path, model=inputs['project_model'])
        for path in inputs['sources']:
            classified = classifier.classify(path)
            assert classified.scope == scope
            assert any(name in membership for membership in classified.build_membership)
        if name == 'main':
            generated = c['generated_sources']
            assert len(generated) == 1
            assert classifier.classify(generated[0]['path']).origin == 'generated'
    unknown = Classifier(tmp_path, model={'source_sets':[dict(id='contest',module='root',scope='unknown',roots=['src/main/contest'])]})
    assert unknown.classify('src/main/contest/Contest.java').scope == 'unknown'


@pytest.mark.parametrize('origin,scope', [('UNKNOWN','production'), ('INFERRED','test'), ({},'unknown')])
def test_invalid_scope_provenance_cannot_publish_manifest(tmp_path, origin, scope):
    from kgmaker.analysis_model import AnalysisError, digest
    from kgmaker.build_model import import_manifest
    manifest = dict(schema_version=1, build_id='invalid',
                    build_result=dict(status='SUCCESS'),
                    snapshot=dict(sources={}, content_hash=digest({})),
                    contexts=[dict(id='custom', repo_id='local', module='root', source_set='custom',
                                   scope=scope, scope_origin=origin, source_roots=[], source_files=[],
                                   classpath=[])])
    with pytest.raises(AnalysisError, match='scope provenance'):
        import_manifest(tmp_path, manifest)
    assert not (tmp_path/'.kgmaker').exists()


def test_ambiguous_source_sets_keep_unknown_without_process(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('classification must remain offline')
    monkeypatch.setattr('subprocess.Popen', forbidden)
    model = dict(source_sets=[dict(id=name,module='root',scope=scope,roots=['src/shared'])
                              for name,scope in [('one','production'),('two','test')]])
    classifier = Classifier(tmp_path, model=model)
    assert classifier.classify('src/shared/File.java').scope == 'unknown'
    assert classifier.diagnostics[0]['code'] == 'BUILD_SCOPE_CONFLICT'


def test_real_gradle_invalid_mapping_is_unknown_preserves_store(tmp_path):
    gradle = os.environ.get('KGMAKER_TEST_GRADLE')
    if not gradle or not Path(gradle).is_file():
        pytest.skip('BLOCKED: set KGMAKER_TEST_GRADLE to supported Gradle 8.13')
    (tmp_path/'settings.gradle').write_text("rootProject.name='invalid-variant'")
    (tmp_path/'build.gradle').write_text("plugins { id 'java' }; sourceSets { custom {} }; ext.kgmakerSourceSetScopes = [custom:'unsupported']")
    store = tmp_path/'.kgmaker/graph.json'
    store.parent.mkdir()
    store.write_bytes(b'previous graph generation')
    result = run_plan(create_plan(tmp_path, executable=gradle, home=ROOT/'workers', offline=True))
    manifest = json.loads(Path(result['manifest_path']).read_text())
    context = next(c for c in manifest['contexts'] if c['source_set']=='custom')
    assert context['scope'] == 'unknown'
    assert context['scope_origin'] == 'UNKNOWN'
    assert context['diagnostics'][0]['code'] == 'INVALID_GRADLE_SOURCE_SET_SCOPE'
    assert result['status'] == 'PARTIAL'
    assert store.read_bytes() == b'previous graph generation'


def test_selected_variant_snapshot_ignores_sibling_sources_and_configs_offline(tmp_path, monkeypatch):
    from kgmaker.inspection import context, graph_from_response
    from kgmaker.graph_provider import validate_context_snapshot
    from kgmaker.scanner import scan_repository
    from kgmaker.worker_protocol import WorkerError
    paths={'custom/integration/Integration.java':'class Integration {}',
           'src/test/java/Sibling.java':'class Sibling {}',
           'src/test/resources/application.properties':'sibling=one',
           'custom/integration/application.properties':'selected=one',
           'gradle.properties':'shared=one'}
    for name,text in paths.items():
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
    model={'source_sets':[{'module':'root','id':'integration','scope':'test','roots':['custom/integration']}]}
    base=scan_repository(tmp_path,project_model=model)
    selected=context(tmp_path,base,'jvm',{},repo_id='local',module='root',source_set='integration',scope='test',
                     build_context={'project_model':model})
    from kgmaker.store import save_graph
    response={'context_id':selected['id'],'worker':{},'symbols':[{'id':'variant-method','name':'run','kind':'method',
              'context_id':selected['id'],'path':'custom/integration/Integration.java'}],
              'call_sites':[],'bodies':[],'facts':[],'diagnostics':[],'coverage':{},'status':'PARTIAL'}
    save_graph(graph_from_response(tmp_path,base,response,selected,project_model=model),tmp_path)
    monkeypatch.setattr('subprocess.Popen',lambda *a,**kw: pytest.fail('offline refresh launched process'))
    (tmp_path/'src/test/java/Sibling.java').write_text('class Sibling { int changed; }')
    (tmp_path/'src/test/java/Added.java').write_text('class Added {}')
    (tmp_path/'src/test/resources/application.properties').write_text('sibling=two')
    validate_context_snapshot(tmp_path,selected)
    from kgmaker.cli import scan,hook_context
    from kgmaker.feature import current_graph
    assert scan(tmp_path,generate_docs=False)==0
    assert hook_context(tmp_path)==0
    live,_,_=current_graph(tmp_path)
    assert any(symbol['id']=='variant-method' for symbol in live.symbols)
    (tmp_path/'custom/integration/application.properties').write_text('selected=two')
    with pytest.raises(WorkerError,match='source/config'):
        validate_context_snapshot(tmp_path,selected)
    (tmp_path/'custom/integration/application.properties').write_text('selected=one')
    (tmp_path/'gradle.properties').write_text('shared=two')
    with pytest.raises(WorkerError,match='source/config'):
        validate_context_snapshot(tmp_path,selected)


@pytest.mark.parametrize('source_set,scope',[('custom','production'),('main','test'),('test','production'),('testFixtures','test')])
def test_forged_gradle_convention_preserves_existing_store(tmp_path, source_set, scope):
    from kgmaker.analysis_model import AnalysisError,digest
    from kgmaker.build_model import import_manifest
    from kgmaker.scanner import scan_repository
    from kgmaker.store import save_graph,load_graph
    save_graph(scan_repository(tmp_path),tmp_path)
    assert load_graph(tmp_path) is not None
    manifest={'schema_version':1,'build_id':'forged','build_result':{'status':'SUCCESS'},
              'snapshot':{'sources':{},'content_hash':digest({})},
              'contexts':[{'id':'custom','repo_id':'local','module':'root','source_set':source_set,
                           'scope':scope,'scope_origin':'GRADLE_CONVENTION','source_roots':[],'source_files':[],'classpath':[]}]}
    before={p.relative_to(tmp_path).as_posix():p.read_bytes() for p in (tmp_path/'.kgmaker').rglob('*') if p.is_file()}
    with pytest.raises(AnalysisError,match='scope provenance'):
        import_manifest(tmp_path,manifest)
    assert before=={p.relative_to(tmp_path).as_posix():p.read_bytes() for p in (tmp_path/'.kgmaker').rglob('*') if p.is_file()}


@pytest.mark.parametrize('source_set,scope,origin',[('main','production','GRADLE_CONVENTION'),
    ('test','test','GRADLE_CONVENTION'),('testFixtures','test_fixture','GRADLE_CONVENTION'),
    ('custom','production',None)])
def test_conventional_pairs_and_legacy_manifest_remain_readable(tmp_path,source_set,scope,origin):
    from kgmaker.analysis_model import digest
    from kgmaker.build_model import validate_manifest
    selected={'id':'set','repo_id':'local','module':'root','source_set':source_set,'scope':scope,
              'source_roots':[],'source_files':[],'classpath':[]}
    if origin is not None:
        selected['scope_origin']=origin
    manifest={'schema_version':1,'build_id':'legacy','build_result':{'status':'SUCCESS'},
              'snapshot':{'sources':{},'content_hash':digest({})},'contexts':[selected]}
    assert validate_manifest(tmp_path,manifest)['contexts'][0]['scope']==scope
