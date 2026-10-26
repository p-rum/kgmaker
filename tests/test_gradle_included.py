"""T003-S03-W03 composite model identity and real dependency substitution."""
import json
import os
from pathlib import Path
import zipfile
import pytest
from kgmaker.build_runner import create_plan, run_plan
from kgmaker.build_model import inspection_inputs

ROOT=Path(__file__).parents[1]


def test_real_gradle_included_duplicate_modules_and_stale_artifact(tmp_path):
    gradle=os.environ.get('KGMAKER_TEST_GRADLE')
    if not gradle or not Path(gradle).is_file():
        pytest.skip('BLOCKED: set KGMAKER_TEST_GRADLE to supported Gradle8.13')
    files={
        'settings.gradle':"rootProject.name='coordinator'; include('lib'); includeBuild('included')",
        'build.gradle':"plugins { id 'java' }; repositories { maven { url = uri('repo') } }; dependencies { implementation 'sample:lib:1'; implementation files('stable.jar') }",
        'lib/build.gradle':"plugins { id 'java' }; group='other'; version='1'",
        'lib/src/main/java/Other.java':'class Other {}',
        'included/settings.gradle':"rootProject.name='dependency'; include('lib')",
        'included/lib/build.gradle':"plugins { id 'java' }; group='sample'; version='1'",
        'included/lib/src/main/java/sample/Api.java':'package sample; public class Api { public static String current(){return "fresh";} }',
        'src/main/java/App.java':'class App { String get(){ return sample.Api.current(); } }',
        'repo/sample/lib/1/lib-1.pom':'<project><modelVersion>4.0.0</modelVersion><groupId>sample</groupId><artifactId>lib</artifactId><version>1</version></project>',
    }
    for name,text in files.items():
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
    stale=tmp_path/'repo/sample/lib/1/lib-1.jar'
    with zipfile.ZipFile(stale,'w') as z:z.writestr('stale.txt','no current API')
    with zipfile.ZipFile(tmp_path/'stable.jar','w') as z:z.writestr('stable.txt','external stable dependency')
    result=run_plan(create_plan(tmp_path,executable=gradle,home=ROOT/'workers',offline=True))
    manifest=json.loads(Path(result['manifest_path']).read_text())
    assert manifest['build_result']['status']=='SUCCESS',manifest['build_result']
    libs=[c for c in manifest['contexts'] if c['module'].endswith('lib') and c['source_set']=='main']
    assert len(libs)==2
    assert len({c['id'] for c in libs})==2
    assert len({c['repo_id'] for c in libs})==2
    included=next(c for c in libs if c['repo_id']!='local')
    app=next(c for c in manifest['contexts'] if c['module']=='root' and c['source_set']=='main')
    included_artifact=next(a for a in app['classpath'] if a.get('realm',{}).get('repo_id')==included['repo_id'])
    assert 'included/lib/build' in included_artifact['path']
    assert any(a['path'].endswith('/stable.jar') for a in app['classpath'])
    raw=json.loads(Path(result['manifest_path']).with_name('export.json').read_text())
    raw_app=next(c for c in raw['contexts'] if c['id']==app['id'])
    assert [a['path'] for a in app['classpath']]==raw_app['classpath_paths']
    assert all('/repo/sample/' not in a['path'] for a in app['classpath'])
    inputs=inspection_inputs(tmp_path,manifest,context_id=included['id'],scope='production')
    assert inputs['repo_id']==included['repo_id']
    assert inputs['sources']==['included/lib/src/main/java/sample/Api.java']


def test_colliding_output_owners_are_unknown_without_process(tmp_path,monkeypatch):
    from kgmaker.build_runner import build_output_realms
    def forbidden(*args,**kwargs):raise AssertionError('offline realm indexing spawned process')
    monkeypatch.setattr('subprocess.Popen',forbidden)
    common=dict(module='lib',source_set='main',scope='production',output_paths=[str(tmp_path/'shared')])
    realms,diagnostics=build_output_realms([dict(common,repo_id='one'),dict(common,repo_id='two')])
    assert realms=={}
    assert diagnostics[0]['code']=='AMBIGUOUS_BUILD_OUTPUT_REALM'


def test_included_identity_collision_does_not_replace_manifest(tmp_path):
    from kgmaker.analysis_model import AnalysisError,digest
    from kgmaker.build_model import import_manifest
    c=dict(id='one',repo_id='local',module='included/lib',source_set='main',scope='production',
           build_root='included',source_roots=[],source_files=[],classpath=[])
    manifest=dict(schema_version=1,build_id='collision',build_result=dict(status='SUCCESS'),
                  snapshot=dict(sources={},content_hash=digest({})),contexts=[c])
    with pytest.raises(AnalysisError,match='repository identity'):import_manifest(tmp_path,manifest)
    assert not (tmp_path/'.kgmaker').exists()


@pytest.mark.parametrize('claim', ['ghost', 'wrong-owner', 'ambiguous'])
def test_classpath_realm_requires_unique_matching_producer_output(tmp_path, claim):
    from kgmaker.analysis_model import AnalysisError, digest
    from kgmaker.build_runner import snapshot
    from kgmaker.inspection import artifact_hash
    from kgmaker.build_model import import_manifest

    produced = tmp_path / 'included/lib/build/classes'
    produced.mkdir(parents=True)
    (produced / 'Product.class').write_bytes(b'current-bytecode')
    external = tmp_path / 'external.jar'
    external.write_bytes(b'external-artifact')
    sources = snapshot(tmp_path)
    snapshot_hash = digest(sources)
    produced_hash = artifact_hash(produced)
    classpath_path = external if claim == 'ghost' else produced
    classpath_hash = artifact_hash(classpath_path)
    producer = dict(id='producer', repo_id='gradle-producer', build_root='included',
                    module='included/lib', source_set='main', scope='production',
                    source_roots=[], source_files=[], classpath=[], outputs=[dict(
                        path=str(produced), sha256=produced_hash, execution_id='execution',
                        snapshot_hash=snapshot_hash, freshness='EXECUTION_BOUND')])
    consumer = dict(id='consumer', repo_id='local', build_root='.', module='root',
                    source_set='main', scope='production', source_roots=[], source_files=[],
                    classpath=[dict(path=str(classpath_path), sha256=classpath_hash,
                                    realm=dict(repo_id='gradle-producer' if claim != 'wrong-owner' else 'other',
                                               module='included/lib', source_set='main', scope='production'))])
    contexts = [producer, consumer]
    if claim == 'ambiguous':
        contexts.insert(1, dict(producer, id='duplicate', repo_id='gradle-duplicate',
                                build_root='other', module='other/lib'))
    manifest = dict(schema_version=1, build_id='forged-realm',
                    build_result=dict(status='SUCCESS', execution_id='execution'),
                    snapshot=dict(sources=sources, content_hash=snapshot_hash,
                                  inventory='ALL_BUILD_INPUTS_V1'), contexts=contexts)
    with pytest.raises(AnalysisError, match='realm'):
        import_manifest(tmp_path, manifest)
    assert not (tmp_path / '.kgmaker').exists()
