"""Explicit build execution with immutable plan inputs and isolated output roots.

LOCAL_TRUSTED is an execution policy for reviewed project code, not a sandbox.
The host remains responsible for enforcing its network/filesystem restrictions.
No analytical command calls this module implicitly.
"""
from __future__ import annotations
import os
import re
import shutil
import signal
import subprocess
import time
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from .analysis_model import AnalysisError, digest, file_hash, read_json, safe_path, write_json
from .inspection import artifact_hash, worker_home

VERSION = 'build-plan-1'
_BUILD_EXECUTE_SUPPORTED = os.name == 'posix'
EXCLUDED = {'.git', '.kgmaker', '.gradle', 'target', 'build', 'node_modules', '__pycache__', '.pytest_cache', '.venv'}


def exporter_contract(home: Path, build_system: str, adapter: Path, *, required=False) -> dict | None:
    """Check an optional distribution descriptor without launching any process.

    Legacy explicit worker homes remain content-bound by the existing plan.
    A present descriptor is authoritative: invalid/missing entries never fall
    back to an unverified adapter. Checksums bind contents, not publisher identity.
    """
    descriptor = home / 'build/exporters.json'
    if not descriptor.is_file():
        if required:
            raise AnalysisError('Packaged exporter distribution descriptor unavailable', 3)
        return None
    value = read_json(descriptor)
    if (not isinstance(value, dict) or type(value.get('schema_version')) is not int
            or value['schema_version'] != 1 or type(value.get('protocol_version')) is not int
            or value['protocol_version'] != 1):
        raise AnalysisError('Exporter distribution protocol unsupported', 3)
    records = value.get('exporters')
    record = records.get(build_system) if isinstance(records, dict) else None
    if not isinstance(record, dict) or set(record) != {'path', 'sha256', 'exporter', 'license'}:
        raise AnalysisError('Exporter distribution entry unavailable: ' + build_system, 3)
    if any(not isinstance(record[key], str) or not record[key] for key in record):
        raise AnalysisError('Exporter distribution entry invalid', 3)
    expected = safe_path(home / 'build', record['path'])
    license_path = safe_path(home / 'build', record['license'])
    if expected.resolve() != adapter.resolve() or not adapter.is_file() or file_hash(adapter) != record['sha256']:
        raise AnalysisError('Exporter distribution hash mismatch', 3)
    if not license_path.is_file():
        raise AnalysisError('Exporter distribution license unavailable', 3)
    return {'schema_version': 1, 'exporter': record['exporter'],
            'descriptor': {'path': str(descriptor), 'sha256': file_hash(descriptor)},
            'license': {'path': str(license_path), 'sha256': file_hash(license_path)}}


def snapshot(root: Path) -> dict:
    """Inventory every build input, including dirty/untracked and extensionless files."""
    result = {}
    for directory, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED)
        for d in dirs:
            if (Path(directory)/d).is_symlink():
                raise AnalysisError('Symlink build input unsupported: '+str(Path(directory)/d))
        for name in sorted(names):
            p=Path(directory)/name
            if p.is_symlink(): raise AnalysisError('Symlink build input unsupported: '+str(p))
            if not p.is_file(): raise AnalysisError('Non-regular build input unsupported: '+str(p))
            result[p.relative_to(root).as_posix()]=file_hash(p)
    return result


def _jdk_executable(java_home: Path, name: str) -> Path:
    """Resolve a required JDK executable without using the host PATH."""
    candidates = [java_home / 'bin' / name, java_home / 'bin' / (name + '.exe')]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise AnalysisError(f'TOOLCHAIN_UNAVAILABLE: {name} absent from explicit Java home', 3)


def _select_java_home(java_home: Path | None) -> dict | None:
    if java_home is None:
        return None
    home = java_home.expanduser().resolve()
    if not home.is_dir():
        raise AnalysisError('TOOLCHAIN_UNAVAILABLE: explicit Java home is not a directory', 3)
    executables = {}
    for name in ('java', 'javac'):
        path = _jdk_executable(home, name)
        executables[name] = {'path': str(path), 'sha256': file_hash(path)}
    selected = {'selection': 'EXPLICIT_JAVA_HOME', 'java_home': str(home),
                'executables': executables}
    selected['fingerprint'] = digest(selected)
    return selected


def build_output_realms(contexts: list[dict]) -> tuple[dict, list[dict]]:
    """Register actual exporter outputs; ambiguous ownership is never selected."""
    realms = {}; ambiguous = set()
    def register(path, realm):
        key = str(Path(path).resolve())
        if key in ambiguous:
            return
        if key in realms and realms[key] != realm:
            realms.pop(key); ambiguous.add(key)
        else:
            realms[key] = realm
    for context in contexts:
        realm = {key: context.get(key, 'local' if key == 'repo_id' else None)
                 for key in ('repo_id', 'module', 'source_set', 'scope')}
        for path in context.get('output_paths', []):
            register(path, realm)
        output_paths = {str(Path(path).resolve()) for path in context.get('output_paths', [])}
        for artifact in context.get('project_artifacts', []):
            # A declared archive path alone is not proof it was produced now.
            path = str(Path(artifact['path']).resolve())
            if path in output_paths and Path(path).is_file():
                register(path, realm)
    return realms, [{'code':'AMBIGUOUS_BUILD_OUTPUT_REALM','path':path} for path in sorted(ambiguous)]


def create_plan(root: Path, *, phase='test-compile', build_system=None, executable=None,
                profiles=None, timeout=300, policy='LOCAL_TRUSTED', home=None, environment=None,
                offline=False, java_home: Path | None = None) -> dict:
    if not _BUILD_EXECUTE_SUPPORTED:
        raise AnalysisError('UNSUPPORTED_PLATFORM: Windows BUILD_EXECUTE is not supported; use BUILD_IMPORT with verified local artifacts', 3)
    root=root.resolve()
    if policy != 'LOCAL_TRUSTED': raise AnalysisError('Host execution policy unavailable; use BUILD_IMPORT')
    if phase not in {'compile','test-compile','test'}: raise AnalysisError('Unsupported build phase')
    if timeout <= 0 or timeout > 86400: raise AnalysisError('Invalid build timeout')
    systems=[s for s,p in [('maven','pom.xml'),('gradle','build.gradle'),('gradle','build.gradle.kts')] if (root/p).is_file()]
    systems=sorted(set(systems))
    if build_system is None:
        if len(systems)!=1: raise AnalysisError('Explicit build-system required: '+', '.join(systems))
        build_system=systems[0]
    if build_system not in systems: raise AnalysisError('Build-system input unavailable')
    command=shutil.which(executable or ('mvn' if build_system=='maven' else 'gradle'))
    if not command: raise AnalysisError('TOOLCHAIN_UNAVAILABLE: '+build_system,3)
    command=str(Path(command).resolve())
    explicit_home = home is not None or bool(os.environ.get('KGMAKER_WORKERS_HOME'))
    home=worker_home(home)
    adapter=home/('build/maven/target/kgmaker-build-export.jar' if build_system=='maven' else 'build/gradle/export.gradle')
    if not adapter.is_file():raise AnalysisError('Build exporter unavailable; build/install trusted exporter explicitly',3)
    contract = exporter_contract(home, build_system, adapter, required=not explicit_home)
    # Bind environment values by hash; never persist credentials or tokens.
    names=environment or ['PATH','JAVA_HOME','MAVEN_OPTS','GRADLE_USER_HOME','HTTP_PROXY','HTTPS_PROXY','NO_PROXY','http_proxy','https_proxy','no_proxy']
    if any(not isinstance(n,str) or not n.replace('_','').isalnum() for n in names):raise AnalysisError('Invalid environment allowlist')
    selected_toolchain = _select_java_home(java_home)
    inputs=snapshot(root);token=uuid.uuid4().hex
    run_root=root/'.kgmaker/build-runs'/token;work=run_root/'snapshot';export=run_root/'export.json';copied_adapter=run_root/adapter.name
    argv=[command]
    if offline: argv += ['-o' if build_system=='maven' else '--offline']
    if build_system=='maven':
        argv += ['-B','-ntp',f'-Dmaven.ext.class.path={copied_adapter}',f'-Dkgmaker.snapshot.root={work}',f'-Dkgmaker.export.path={export}']
        for profile in profiles or []:
            if not isinstance(profile,str) or not profile or profile.startswith('-') or ',' in profile:raise AnalysisError('Invalid Maven profile')
            argv+=['-P'+profile]
        argv+=[phase]
    else:
        if profiles:raise AnalysisError('Gradle profiles unsupported; use explicit variant export')
        argv+=['--no-daemon','--init-script',str(copied_adapter),f'-Dkgmaker.snapshot.root={work}',f'-Dkgmaker.export.path={export}',{'compile':'classes','test-compile':'testClasses','test':'test'}[phase],'kgmakerExport']
    overrides = ({'JAVA_HOME': selected_toolchain['java_home']} if selected_toolchain else {})
    value={'schema_version':1,'version':VERSION,'root':str(root),'build_id':token,'build_system':build_system,'phase':phase,
        'snapshot':{'sources':inputs,'content_hash':digest(inputs),'inventory':'ALL_BUILD_INPUTS_V1'},
        'argv':argv,'cwd':str(work),'run_root':str(run_root),'export_path':str(export),
        'executable':{'path':command,'sha256':file_hash(Path(command))},'adapter':{'path':str(adapter),'sha256':file_hash(adapter)},
        'environment':{n:digest(overrides.get(n, os.environ.get(n))) for n in names},
        'environment_overrides':overrides,'toolchain_selection':selected_toolchain,'timeout':timeout,
        'execution_policy':{'mode':policy,'host_enforced':True,'isolation':'SEPARATE_SNAPSHOT_NOT_SECURITY_SANDBOX'}}
    if contract is not None:
        value['exporter_contract'] = contract
    value['plan_hash']=digest(value)
    return value


def tests_report(work: Path, phase: str) -> dict:
    records=[]
    reports=sorted(set(work.rglob('surefire-reports/TEST-*.xml'))|set(work.rglob('test-results/*/TEST-*.xml')))
    for path in reports:
        try:
            tree=ET.parse(path).getroot()
            suites=[tree] if tree.tag=='testsuite' else list(tree.findall('testsuite'))
            for suite in suites:
                total=int(suite.get('tests','0')); failed=int(suite.get('failures','0'))+int(suite.get('errors','0')); skipped=int(suite.get('skipped','0'))
                records.append({'report':path.relative_to(work).as_posix(),'executed':max(0,total-skipped),'passed':max(0,total-skipped-failed),'failed':failed,'skipped':skipped,'total':total})
        except (ET.ParseError,ValueError,OSError):records.append({'report':str(path),'status':'UNRESOLVED_REPORT'})
    valid=[r for r in records if 'total' in r]; totals={k:sum(r[k] for r in valid) for k in ('executed','passed','failed','skipped','total')}
    status=('FAILED' if totals['failed'] else 'PASSED' if totals['executed'] else 'SKIPPED' if totals['skipped'] else 'ZERO_TESTS' if valid else 'NOT_RUN')
    return {'status':status,**totals,'reports':records,'coverage':'PARTIAL' if any('total' not in r for r in records) or (phase=='test' and not valid) else 'SUPPORTED_XML_REPORTS'}


def run_plan(plan: dict, *, cancel_file: Path | None=None, verification_task: str | None = None) -> dict:
    if not _BUILD_EXECUTE_SUPPORTED:
        raise AnalysisError('UNSUPPORTED_PLATFORM: Windows BUILD_EXECUTE is not supported; use BUILD_IMPORT with verified local artifacts', 3)
    original={k:v for k,v in plan.items() if k!='plan_hash'}
    if plan.get('schema_version')!=1 or plan.get('plan_hash')!=digest(original):raise AnalysisError('BuildPlan content binding mismatch')
    if plan.get('execution_policy',{}).get('mode')!='LOCAL_TRUSTED':raise AnalysisError('Host execution policy unavailable; use BUILD_IMPORT')
    root=Path(plan['root']).resolve();run=Path(plan['run_root']);work=Path(plan['cwd']);adapter=Path(plan['adapter']['path'])
    task = None
    if verification_task is not None:
        from . import verification
        from .workflow import _git_head, load_task

        if plan['phase'] != 'test' or plan['snapshot'].get('inventory') != verification.INVENTORY:
            raise AnalysisError('Verification capture requires a full build inventory and test phase')
        if not re.fullmatch('[0-9a-f]{32}', plan['build_id']) or plan.get('version') != VERSION:
            raise AnalysisError('Verification capture requires a current BuildPlan')
        if (not isinstance(plan.get('argv'), list) or not plan['argv']
                or plan['argv'][0] != plan['executable']['path']):
            raise AnalysisError('Verification command does not match its bound executable')
        if _git_head(root) is None:
            raise AnalysisError('Verification capture requires a Git checkout root with a commit')
        task = load_task(root, verification_task)
    # Paths cannot be changed independently of the root and build identity.
    expected=safe_path(root,'.kgmaker/build-runs/'+plan['build_id'])
    if run!=expected or work!=run/'snapshot' or Path(plan['export_path'])!=run/'export.json':raise AnalysisError('Invalid plan output containment')
    if snapshot(root)!=plan['snapshot']['sources']:raise AnalysisError('STALE_PLAN: build inputs changed',3)
    for record in (plan['executable'],plan['adapter']):
        if not Path(record['path']).is_file() or file_hash(Path(record['path']))!=record['sha256']:raise AnalysisError('STALE_PLAN: executable/exporter changed',3)
    contract = plan.get('exporter_contract')
    if contract is not None:
        if not isinstance(contract, dict) or contract.get('schema_version') != 1 or not isinstance(contract.get('exporter'), str):
            raise AnalysisError('Invalid exporter protocol contract', 3)
        for key in ('descriptor', 'license'):
            record = contract.get(key)
            if not isinstance(record, dict) or not isinstance(record.get('path'), str):
                raise AnalysisError('Invalid exporter distribution binding', 3)
            path = Path(record['path'])
            if not path.is_file() or file_hash(path) != record.get('sha256'):
                raise AnalysisError('STALE_PLAN: exporter distribution changed', 3)
    overrides=plan.get('environment_overrides',{})
    if not isinstance(overrides,dict) or set(overrides)-{'JAVA_HOME'} or any(not isinstance(v,str) or not v for v in overrides.values()):
        raise AnalysisError('Invalid BuildPlan environment overrides')
    selected=plan.get('toolchain_selection')
    if selected is not None:
        if (not isinstance(selected,dict) or selected.get('selection')!='EXPLICIT_JAVA_HOME'
                or selected.get('java_home')!=overrides.get('JAVA_HOME')
                or selected.get('fingerprint')!=digest({k:v for k,v in selected.items() if k!='fingerprint'})
                or not isinstance(selected.get('executables'),dict)):
            raise AnalysisError('Invalid explicit toolchain selection')
        for name in ('java','javac'):
            record=selected['executables'].get(name)
            if (not isinstance(record,dict) or not isinstance(record.get('path'),str)
                    or not isinstance(record.get('sha256'),str)):
                raise AnalysisError('Invalid explicit toolchain executable')
            path=Path(record['path'])
            if not path.is_file() or file_hash(path)!=record['sha256']:
                raise AnalysisError('STALE_PLAN: selected Java toolchain changed',3)
    env={}
    for name,expected_hash in plan['environment'].items():
        value=overrides.get(name,os.environ.get(name))
        if digest(value)!=expected_hash:raise AnalysisError('STALE_PLAN: allowed environment changed: '+name,3)
        if value is not None:env[name]=value
    env.update(overrides)
    if selected:
        current_path=env.get('PATH','')
        env['PATH']=str(Path(selected['java_home'])/'bin')+(os.pathsep+current_path if current_path else '')
    try:
        run.mkdir(parents=True)
    except FileExistsError as error:
        raise AnalysisError('BuildPlan already executed; create a new plan') from error
    work.mkdir()
    for relative,expected_hash in plan['snapshot']['sources'].items():
        source=safe_path(root,relative);target=safe_path(work,relative);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        if file_hash(target)!=expected_hash:raise AnalysisError('Mixed snapshot during copy',3)
    shutil.copy2(adapter,run/adapter.name)
    if snapshot(root)!=plan['snapshot']['sources']:raise AnalysisError('Source changed while capturing snapshot',3)
    if task is not None:
        before = verification.observation(root, plan['snapshot']['sources'])
        if before['head'] is None:
            raise AnalysisError('Verification capture lost the Git checkout before execution', 3)
        copied_before = verification.input_fingerprint(work, plan['snapshot']['sources'])
    start=time.monotonic();state='SUCCESS';return_code=None;log=run/'build.log'
    if cancel_file and cancel_file.exists():state='CANCELLED'
    else:
        try:
            with log.open('wb') as output:
                process=subprocess.Popen(plan['argv'],cwd=work,env=env,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
                while process.poll() is None:
                    if cancel_file and cancel_file.exists():state='CANCELLED';break
                    if time.monotonic()-start>plan['timeout']:state='TIMED_OUT';break
                    time.sleep(.05)
                if state in {'TIMED_OUT','CANCELLED'}:
                    os.killpg(process.pid,signal.SIGTERM)
                    try:process.wait(timeout=2)
                    except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
                return_code=process.returncode
                if state=='SUCCESS' and return_code!=0:state='FAILED'
        except FileNotFoundError:state='TOOLCHAIN_UNAVAILABLE'
    export=read_json(Path(plan['export_path'])) if Path(plan['export_path']).is_file() else None
    if contract is not None and export is not None:
        if (not isinstance(export, dict) or type(export.get('schema_version')) is not int
                or export['schema_version'] != contract['schema_version']
                or export.get('exporter') != contract['exporter']):
            raise AnalysisError('Exporter output protocol mismatch', 3)
    if state=='SUCCESS' and export is None:state='PARTIAL'
    diagnostics=list(export.get('diagnostics',[]) if export else [{'code':'BUILD_MODEL_EXPORT_UNAVAILABLE'}])
    if state=='SUCCESS' and selected and export:
        expected_home=Path(selected['java_home']).resolve()
        mismatches=[]
        for context in export.get('contexts',[]):
            actual=(context.get('toolchain') or {}).get('java_home') if isinstance(context,dict) else None
            if not isinstance(actual,str) or Path(actual).resolve()!=expected_home:
                mismatches.append({'context':context.get('id') if isinstance(context,dict) else None,
                                   'reported_java_home':actual})
        if mismatches:
            state='TOOLCHAIN_UNAVAILABLE'
            diagnostics.append({'code':'EXPLICIT_TOOLCHAIN_MISMATCH','expected_java_home':str(expected_home),
                                'contexts':mismatches})
    if task is not None:
        tests, report_artifacts = verification.capture_reports(work)
    else:
        tests = tests_report(work, plan['phase'])
    result={'status':state,'execution_id':plan['build_id'],'return_code':return_code,'duration_seconds':round(time.monotonic()-start,3),
        'tests':tests,'modules':export.get('modules',{}) if export else {},'log_path':str(log),
        'log_sha256':file_hash(log) if log.exists() else None,'snapshot_hash':plan['snapshot']['content_hash']}
    # A changed original snapshot does not invalidate the copied build, but it is
    # stale for indexing the current checkout and cannot be imported as fresh.
    current=snapshot(root)
    copied_unchanged=all(safe_path(work, p).is_file() and file_hash(safe_path(work, p))==expected for p,expected in plan['snapshot']['sources'].items())
    result['freshness']='MIXED_BUILD_INPUTS' if not copied_unchanged else 'EXECUTION_BOUND' if current==plan['snapshot']['sources'] else 'STALE_SOURCE'
    contexts=[]
    output_realms, realm_diagnostics = build_output_realms(export.get('contexts', [])) if state == 'SUCCESS' and copied_unchanged and export else ({}, [])
    diagnostics.extend(realm_diagnostics)
    for c in export.get('contexts',[]) if export else []:
        c=dict(c);c.pop('project_artifacts',None);c['repo_id']=c.get('repo_id','local');c['classpath']=[]
        for raw in c.pop('classpath_paths',[]):
            path=Path(raw)
            if path.exists():
                artifact={'path':str(path),'sha256':artifact_hash(path)}
                if str(path.resolve()) in output_realms:artifact['realm']=output_realms[str(path.resolve())]
                c['classpath'].append(artifact)
            else:c.setdefault('diagnostics',[]).append({'code':'CLASSPATH_ARTIFACT_UNAVAILABLE','path':raw})
        generated_roots = set(c.get('generated_source_roots', []))
        generated_files = [path for path in c.get('source_files', [])
                           if any(path == root_path or path.startswith(root_path.rstrip('/') + '/')
                                  for root_path in generated_roots)]
        generated_prefix = f'.kgmaker/build-runs/{plan["build_id"]}/snapshot/'
        generated_available = state == 'SUCCESS' and copied_unchanged
        remap = ({path: generated_prefix + path for path in generated_files}
                 if generated_available else {})
        c['source_files'] = ([remap.get(path, path) for path in c.get('source_files', [])]
                             if generated_available else
                             [path for path in c.get('source_files', []) if path not in generated_files])
        c['source_roots'] = [generated_prefix + path if path in generated_roots else path
                             for path in c.get('source_roots', [])]
        c['generated_source_roots'] = [generated_prefix + path for path in c.get('generated_source_roots', [])]
        c['generated_sources'] = []
        if generated_available:
            for original, durable in remap.items():
                path = safe_path(root, durable)
                if path.is_file():
                    c['generated_sources'].append({'path': durable, 'sha256': file_hash(path),
                        'execution_id': plan['build_id'], 'snapshot_hash': plan['snapshot']['content_hash'],
                        'freshness': 'EXECUTION_BOUND'})
        c['outputs']=[]
        for raw in c.pop('output_paths',[]):
            path=Path(raw)
            if state=='SUCCESS' and copied_unchanged and path.exists():c['outputs'].append({'path':str(path),'sha256':artifact_hash(path),'execution_id':plan['build_id'],'snapshot_hash':plan['snapshot']['content_hash'],'freshness':'EXECUTION_BOUND'})
        contexts.append(c)
    manifest={'schema_version':1,'build_id':plan['build_id'],'mode':'BUILD_EXECUTE','origin_trust':'HOST_EXECUTION',
        'snapshot':plan['snapshot'],'build_result':result,'contexts':contexts,'diagnostics':diagnostics,
        'toolchain_selection':selected,
        'plan_hash':plan['plan_hash'],'exporter':export.get('exporter') if export else None}
    if not copied_unchanged:manifest['diagnostics'].append({'code':'BUILD_INPUTS_CHANGED_DURING_EXECUTION'})
    write_json(run/'result.json',result);write_json(run/'manifest.json',manifest)
    report_status='PARTIAL' if state=='SUCCESS' and (manifest['diagnostics'] or any(c.get('diagnostics') for c in contexts)) else state
    report = {'status':report_status,'build_id':plan['build_id'],'result':result,'manifest_path':str(run/'manifest.json'),'diagnostics':manifest['diagnostics']}
    if task is not None:
        after = verification.observation(root, current)
        try:
            copied_after = verification.input_fingerprint(work, snapshot(work))
            full_copy_matches = copied_before == before['inputs_sha256'] == copied_after
        except (AnalysisError, OSError):
            full_copy_matches = False
        report['verification'] = verification.record_execution(
            root, task, plan, before, after, result, report_artifacts, full_copy_matches)
    return report
