"""Actual compiler coroutine boundaries; application code is compiled, never run."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from kgmaker.inspection import command, artifact_hash
from kgmaker.worker_protocol import WorkerError, request_worker

HOME = Path(__file__).resolve().parents[1] / 'workers'
SOURCE = '''package sample
import kotlinx.coroutines.*
suspend fun fetch(): String { delay(1); delay(2); return "ok" }
suspend fun pipeline(scope: CoroutineScope): String {
    val task = scope.async { fetch() }
    scope.launch { fetch() }
    return task.await()
}
fun delay(value: String) {}
fun launch(value: Int) {}
fun ordinary() { delay("ordinary"); launch(1); kotlinx.coroutines.launch(1) }
'''

@pytest.fixture(scope='module', params=[True, False], ids=['debug', 'no-debug'])
def compiled(tmp_path_factory, request):
    root = tmp_path_factory.mktemp('coroutine-mapping')
    compiler = shutil.which('kotlinc')
    library = Path(compiler).resolve().parent.parent / 'lib/kotlinx-coroutines-core-jvm.jar' if compiler else Path('/missing-kotlin-coroutines')
    if not compiler or not library.is_file():
        if os.environ.get('KGMAKER_REQUIRE_WORKERS') == '1':
            pytest.fail('Actual pinned Kotlin/coroutines compiler inputs required')
        pytest.skip('Actual Kotlin/coroutines compiler inputs unavailable')
    assert hashlib.sha256(library.read_bytes()).hexdigest() == 'c24c8bb27bb320c4a93871501a7e5e0c61607638907b197aef675513d4c820be'
    source = root / 'Pipeline.kt'
    source.write_text(SOURCE)
    fake = root / 'Fake.kt'
    fake.write_text('package kotlinx.coroutines; fun launch(value: Int) {}')
    classes = root / 'classes'
    subprocess.run([compiler, str(source), str(fake), '-classpath', str(library), '-jvm-target', '21', '-d', str(classes)],
                   check=True, capture_output=True)
    if not request.param:
        stripper = root / 'StripDebug.java'
        stripper.write_text('import java.nio.file.*;import org.jetbrains.org.objectweb.asm.*;'
            'class StripDebug {public static void main(String[]a)throws Exception{'
            'try(var paths=Files.walk(Path.of(a[0]))){for(var p:paths.filter(x->x.toString().endsWith(".class")).toList())'
            '{var w=new ClassWriter(0);new ClassReader(Files.readAllBytes(p)).accept(w,ClassReader.SKIP_DEBUG);Files.write(p,w.toByteArray());}}}}')
        subprocess.run([shutil.which('java'), '-cp', str(HOME / 'jvm/target/lib/kotlin-compiler.jar'),
                        str(stripper), str(classes)], check=True, capture_output=True)
    return root, classes, library


def analyze(compiled, backend, sources=True, realm_override=None):
    root, classes, library = compiled
    try:
        worker = command('jvm', HOME, kotlin_backend=backend)
    except WorkerError as error:
        if os.environ.get('KGMAKER_REQUIRE_WORKERS') == '1': pytest.fail(str(error))
        pytest.skip(str(error))
    context = {'id': 'coroutine-fixture', 'repo_id': 'fixture', 'module': 'core',
               'source_set': 'main', 'scope': 'production',
               'bytecode_artifacts': [{'path': str(classes), 'sha256': artifact_hash(classes)}]}
    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
    response = request_worker(worker, {'operation': 'analyze', 'root': str(root), 'context': context,
        'sources': ['Pipeline.kt', 'Fake.kt'] if sources else [], 'classpath': [
            {'path': str(classes), 'realm': {**context, **(realm_override or {})}}, str(library), str(HOME / 'jvm/target/lib/kotlin-stdlib.jar')],
        'bytecode_roots': [{'path': str(classes), 'realm': {**context, **(realm_override or {})}}]}, cwd=root)
    assert before == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
    return response


@pytest.mark.parametrize('backend', ['k1', 'k2'])
def test_actual_suspend_source_sites_keep_boundaries(compiled, backend):
    response = analyze(compiled, backend)
    symbols = {s['id']: s for s in response['symbols']}
    sites = [s for s in response['call_sites'] if not s['caller'].startswith('bytecode:')]
    delays = [s for s in sites if s.get('range', {}).get('start_line') == 3]
    assert len(delays) == 2
    for site in delays:
        assert site['async_boundary'] == 'SUSPEND'
        assert site['async_boundary_evidence'] == 'COMPILER_SUSPEND_CALL'
        assert site['path'] == 'Pipeline.kt' and site['range'] and site['sha256']
    launches = [s for s in sites if s.get('async_boundary') == 'LAUNCH']
    assert len(launches) == 1 and launches[0]['async_boundary'] == 'LAUNCH'
    async_sites = [s for s in sites if s.get('async_boundary') == 'ASYNC']
    assert len(async_sites) == 1
    assert async_sites[0]['async_boundary_evidence'] == 'COMPILER_COROUTINES_API'
    awaited = [s for s in sites if s.get('range', {}).get('start_line') == 7]
    assert len(awaited) == 1 and awaited[0]['async_boundary'] == 'SUSPEND'
    assert awaited[0]['async_boundary_evidence'] == 'COMPILER_SUSPEND_CALL'
    assert awaited[0]['path'] == 'Pipeline.kt' and awaited[0]['sha256']
    assert all(s['scheduling'] == 'UNKNOWN' for s in [*delays, *launches, *async_sites, *awaited])
    assert all(s.get('source_locator_kind') != 'SOURCE_CALL_EXPRESSION' for s in response['call_sites']
               if s['caller'].startswith('bytecode:'))


@pytest.mark.parametrize('backend', ['k1', 'k2'])
def test_real_continuation_maps_declaration_without_mapping_state_instructions(compiled, backend):
    response = analyze(compiled, backend)
    continuations = [s for s in response['symbols'] if s.get('kind') == 'bytecode_method'
                     and s.get('name') == 'invokeSuspend' and '$fetch$' in s.get('owner', '')]
    assert len(continuations) == 1
    continuation = continuations[0]
    assert continuation['source_mapping_reason'] == 'KOTLIN_CONTINUATION_DECLARATION'
    assert len(continuation['source_mapping_ids']) == 1
    assert continuation['coroutine_suspension_lines'] == [3, 3]
    assert continuation['coroutine_order'] == 'UNKNOWN'
    assert continuation['path'] is None and continuation['range'] is None
    for site in response['call_sites']:
        if site['caller'] == continuation['id']:
            assert site['source_locator_kind'] == 'BYTECODE_ONLY'
            assert site['path'] is None and site['range'] is None
    if backend == 'k2':
        assert any(d['code'] == 'K2_SOURCE_CFG_UNSUPPORTED' for d in response['diagnostics'])


@pytest.mark.parametrize('backend', ['k1', 'k2'])
def test_missing_sources_never_map_continuation(compiled, backend):
    response = analyze(compiled, backend, sources=False)
    assert not [f for f in response['facts'] if f.get('resolution_reason') == 'KOTLIN_CONTINUATION_DECLARATION']


def test_actual_k1_cfg_preserves_suspend_calls_and_resume_boundary(compiled):
    from kgmaker.control_flow import from_body
    response = analyze(compiled, 'k1')
    symbols = {s['id']: s for s in response['symbols']}
    body = next(b for b in response['bodies'] if symbols[b['method']]['name'] == 'fetch')
    cfg = from_body(body)
    boundaries = [b for b in cfg['blocks'] if b['kind'] == 'async_boundary']
    assert len(boundaries) == 2
    assert all(b['source_file'] == 'Pipeline.kt' and b['source_range'] for b in boundaries)
    assert len([e for e in cfg['edges'] if e['kind'] == 'resume']) == 2
    assert all(any(e['source'] == b['id'] and e['kind'] == 'exception' for e in cfg['edges']) for b in boundaries)
    assert len([b for b in cfg['blocks'] if b['kind'] == 'call']) == 2


@pytest.mark.parametrize('backend', ['k1', 'k2'])
@pytest.mark.parametrize('realm', [{'repo_id': 'foreign'}, {'module': 'foreign'}, {'source_set': 'other'}, {'scope': 'test'}])
def test_foreign_continuation_realm_never_claims_source(compiled, backend, realm):
    response = analyze(compiled, backend, realm_override=realm)
    assert not [f for f in response['facts'] if f.get('resolution_reason') == 'KOTLIN_CONTINUATION_DECLARATION']


@pytest.mark.parametrize('backend', ['k1', 'k2'])
def test_mismatched_debug_metadata_file_stays_bytecode_only(compiled, backend, tmp_path):
    original, _, library = compiled
    root = tmp_path / 'copy'
    shutil.copytree(original, root)
    continuation = root / 'classes/sample/PipelineKt$fetch$1.class'
    raw = continuation.read_bytes()
    assert b'Pipeline.kt' in raw
    continuation.write_bytes(raw.replace(b'Pipeline.kt', b'WrongSrc.kt'))
    response = analyze((root, root / 'classes', library), backend)
    assert not [f for f in response['facts'] if f.get('resolution_reason') == 'KOTLIN_CONTINUATION_DECLARATION']


@pytest.mark.parametrize('backend', ['k1', 'k2'])
def test_ordinary_same_named_functions_do_not_claim_async_boundary(compiled, backend):
    response = analyze(compiled, backend)
    ordinary = next(s['id'] for s in response['symbols'] if s.get('name') == 'ordinary' and s.get('path'))
    sites = [s for s in response['call_sites'] if s['caller'] == ordinary]
    assert len(sites) == 3
    assert all('async_boundary' not in s for s in sites)


@pytest.mark.parametrize('backend', ['k1', 'k2'])
@pytest.mark.parametrize('mode', ['missing', 'unsupported-version', 'invalid-lines'])
def test_incomplete_or_malformed_debug_metadata_never_maps(compiled, backend, tmp_path, mode):
    original, _, library = compiled
    root = tmp_path / 'copy'
    shutil.copytree(original, root)
    continuation = root / 'classes/sample/PipelineKt$fetch$1.class'
    helper = root / 'RewriteMetadata.java'
    helper.write_text('''import java.nio.file.*;import org.jetbrains.org.objectweb.asm.*;
class RewriteMetadata {public static void main(String[] a)throws Exception {
 var p=Path.of(a[0]);var mode=a[1];var w=new ClassWriter(0);
 new ClassReader(Files.readAllBytes(p)).accept(new ClassVisitor(Opcodes.ASM9,w) {
  public AnnotationVisitor visitAnnotation(String d,boolean visible) {
   if(!d.equals("Lkotlin/coroutines/jvm/internal/DebugMetadata;"))return super.visitAnnotation(d,visible);
   if(mode.equals("missing"))return null;
   return new AnnotationVisitor(Opcodes.ASM9,super.visitAnnotation(d,visible)) {
    public AnnotationVisitor visitArray(String name) {
     var nested=super.visitArray(name);
     if(name.equals("l")&&mode.equals("invalid-lines"))return new AnnotationVisitor(Opcodes.ASM9,nested) {
      public void visit(String n,Object v){super.visit(n,0);}
     };
     return nested;
    }
    public void visit(String n,Object v){
     if(n.equals("l")&&mode.equals("invalid-lines")&&v instanceof int[] lines){super.visit(n,new int[lines.length]);return;}
     if(!n.equals("v"))super.visit(n,v);
    }
    public void visitEnd(){if(mode.equals("unsupported-version"))super.visit("v",99);super.visitEnd();}
   };
  }
 },0);Files.write(p,w.toByteArray());}}
''')
    subprocess.run([shutil.which('java'), '-cp', str(HOME / 'jvm/target/lib/kotlin-compiler.jar'),
                    str(helper), str(continuation), mode], check=True, capture_output=True)
    response = analyze((root, root / 'classes', library), backend)
    assert not [f for f in response['facts'] if f.get('resolution_reason') == 'KOTLIN_CONTINUATION_DECLARATION']
