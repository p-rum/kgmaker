"""Independent safety/freshness and actual XML test-state invariants."""
from pathlib import Path
import pytest
from kgmaker.analysis_model import AnalysisError, digest, file_hash
from kgmaker.build_runner import create_plan, run_plan, snapshot, tests_report as report_tests
from kgmaker.build_model import validate_manifest


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
