"""Real compiler golden matrix for T003-S04-W02; never synthesizes class files."""
import os
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from kgmaker.inspection import command, graph_from_response, artifact_hash
from kgmaker.model import KnowledgeGraph
from kgmaker.scanner import scan_repository
from kgmaker.worker_protocol import WorkerError, request_worker

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / 'workers'


@pytest.fixture(params=['k1', 'k2'])
def worker(request):
    try:
        return command('jvm', HOME, kotlin_backend=request.param)
    except WorkerError as exc:
        if os.environ.get('KGMAKER_REQUIRE_WORKERS') == '1':
            pytest.fail(str(exc))
        pytest.skip(str(exc))


@pytest.fixture(scope='module', params=[True, False], ids=['debug', 'no-debug'])
def compiled(tmp_path_factory, request):
    tmp_path = tmp_path_factory.mktemp('default-mapping')
    javac = shutil.which('javac')
    kotlinc = shutil.which('kotlinc')
    if not javac or not kotlinc:
        if os.environ.get('KGMAKER_REQUIRE_WORKERS') == '1':
            pytest.fail('Explicit JDK 21 and Kotlin 2.1.10 compiler required')
        pytest.skip('Explicit JDK 21 and Kotlin 2.1.10 compiler required')
    versions = subprocess.run([javac, '-version'], capture_output=True, text=True, check=True).stdout
    kotlin_version = subprocess.run([kotlinc, '-version'], capture_output=True, text=True, check=True)
    if '21.' not in versions or '2.1.10' not in kotlin_version.stdout + kotlin_version.stderr:
        if os.environ.get('KGMAKER_REQUIRE_WORKERS') == '1':
            pytest.fail('Golden matrix requires pinned JDK21/Kotlin2.1.10')
        pytest.skip('Golden matrix requires pinned JDK21/Kotlin2.1.10')
    java = tmp_path / 'Bridge.java'
    java.write_text('package fixture; interface Generic<T> { T get(); void put(T x); }\n'
                    'class Bridge implements Generic<String> {\n'
                    ' public String get() { return helper(); }\n'
                    ' public void put(String x) {}\n'
                    ' String helper() { return "ok"; }\n'
                    '}\n'
                    'interface JavaDefault { default String value() { return "java"; } }\n'
                    'class Pretend$DefaultImpls { static String value(JavaDefault x) { return x.value(); } }\n')
    kotlin = tmp_path / 'Defaults.kt'
    kotlin.write_text('package fixture\ninterface Defaults {\n'
                      ' fun value(): String = helper()\n'
                      ' fun helper(): String = "kotlin"\n}\n')
    modern = tmp_path / 'Modern.kt'
    modern.write_text('package fixture\ninterface Modern { fun greeting(): String = "all" }\n'
                      'fun staticTop(): String = "top"\n'
                      'object StaticHolder { @JvmStatic fun objectStatic(): String = "static" }\n'
                      'val initialized: String = staticTop()\n')
    classes = tmp_path / 'classes'
    classes.mkdir()
    subprocess.run([javac, '--release', '21', '-proc:none', '-g' if request.param else '-g:none',
                    '-d', str(classes), str(java)], check=True, capture_output=True)
    subprocess.run([kotlinc, '-jvm-target', '21', '-Xjvm-default=disable', '-d', str(classes),
                    str(kotlin)], check=True, capture_output=True)
    subprocess.run([kotlinc, '-jvm-target', '21', '-Xjvm-default=all', '-d', str(classes),
                    str(modern)], check=True, capture_output=True)
    if not request.param:
        # Kotlin has no -g:none switch. Strip only debug attributes from the
        # actual compiled classes with the pinned ASM reader, preserving code.
        stripper = tmp_path / 'StripDebug.java'
        stripper.write_text('import java.nio.file.*; import org.jetbrains.org.objectweb.asm.*; '
            'class StripDebug { public static void main(String[] args) throws Exception {'
            'try(var files=Files.walk(Path.of(args[0]))) {'
            'for(var p:files.filter(f->f.toString().endsWith(".class")).toList()) {'
            'var w=new ClassWriter(0);new ClassReader(Files.readAllBytes(p)).accept(w,ClassReader.SKIP_DEBUG);'
            'Files.write(p,w.toByteArray());}}}}')
        subprocess.run([shutil.which('java'), '-cp', str(HOME / 'jvm/target/lib/kotlin-compiler.jar'),
                        str(stripper), str(classes)], check=True, capture_output=True)
    store = tmp_path / '.kgmaker/graph.json'
    store.parent.mkdir()
    store.write_text(json.dumps(scan_repository(tmp_path).to_dict()), encoding='utf-8')
    KnowledgeGraph.from_dict(json.loads(store.read_text(encoding='utf-8')))
    return tmp_path, classes, request.param


def analyze(worker, compiled, *, sources=True):
    root, classes, _ = compiled
    context = {'id': 'mapping-fixture', 'repo_id': 'fixture', 'module': 'core',
               'source_set': 'main', 'scope': 'production'}
    context['bytecode_artifacts'] = [{'path': str(classes), 'sha256': artifact_hash(classes)}]
    before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    result = request_worker(worker, {'operation': 'analyze', 'root': str(root), 'context': context,
                         'sources': ['Bridge.java', 'Defaults.kt', 'Modern.kt'] if sources else [],
                         'classpath': [{'path': str(classes), 'realm': context},
                                       str(HOME / 'jvm/target/lib/kotlin-stdlib.jar')],
                         'bytecode_roots': [str(classes)]}, cwd=root)
    assert before == {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    return result


def test_real_default_and_bridge_mapping(worker, compiled):
    result = analyze(worker, compiled)
    symbols = {s['id']: s for s in result['symbols']}
    bridge = next(s for s in symbols.values() if s.get('kind') == 'bytecode_method'
                  and s.get('owner') == 'fixture.Bridge' and s.get('bridge') and s.get('name') == 'get')
    void_bridge = next(s for s in symbols.values() if s.get('kind') == 'bytecode_method'
                       and s.get('owner') == 'fixture.Bridge' and s.get('bridge') and s.get('name') == 'put')
    default = next(s for s in symbols.values() if s.get('kind') == 'bytecode_method'
                   and s.get('owner') == 'fixture.Defaults$DefaultImpls' and s.get('name') == 'value')
    modern = next(s for s in symbols.values() if s.get('kind') == 'bytecode_method'
                  and s.get('owner') == 'fixture.Modern' and s.get('name') == 'greeting')
    static_top = next(s for s in symbols.values() if s.get('kind') == 'bytecode_method'
                      and s.get('owner') == 'fixture.ModernKt' and s.get('name') == 'staticTop')
    object_static = next(s for s in symbols.values() if s.get('kind') == 'bytecode_method'
                         and s.get('owner') == 'fixture.StaticHolder' and s.get('name') == 'objectStatic')
    java = next(s for s in symbols.values() if s.get('kind') == 'bytecode_method'
                and s.get('owner') == 'fixture.JavaDefault' and s.get('name') == 'value')
    for generated, reason, source_name, expected_static in [(bridge, 'VERIFIED_BRIDGE_DELEGATE', 'get', False),
                                            (void_bridge, 'VERIFIED_BRIDGE_DELEGATE', 'put', False),
                                            (default, 'KOTLIN_DEFAULT_IMPLS_SIGNATURE', 'value', False),
                                            (java, 'OWNER_NAME_DESCRIPTOR_MATCH', 'value', False),
                                            (modern, 'OWNER_NAME_DESCRIPTOR_MATCH', 'greeting', False),
                                            (static_top, 'OWNER_NAME_DESCRIPTOR_MATCH', 'staticTop', True),
                                            (object_static, 'OWNER_NAME_DESCRIPTOR_MATCH', 'objectStatic', True)]:
        assert generated['source_mapping_reason'] == reason
        assert len(generated['source_mapping_ids']) == 1
        source = symbols[generated['source_mapping_ids'][0]]
        assert source['name'] == source_name and source['path'] and source['range']
        assert source['jvm_static'] is expected_static
        assert generated['jvm_static'] is (True if reason == 'KOTLIN_DEFAULT_IMPLS_SIGNATURE' else expected_static)
        assert generated['id'].startswith('bytecode:') and generated['id'] != source['id']
        assert any(f['kind'] == 'maps_to_source' and f['source'] == generated['id']
                   and f['target'] == source['id'] for f in result['facts'])
    initializer = next(s for s in symbols.values() if s.get('kind') == 'bytecode_method'
                       and s.get('owner') == 'fixture.ModernKt' and s.get('name') == '<clinit>')
    assert initializer['source_mapping_ids'] == []
    pretend = next(s for s in symbols.values() if s.get('kind') == 'bytecode_method'
                   and s.get('owner') == 'fixture.Pretend$DefaultImpls' and s.get('name') == 'value')
    assert pretend['source_mapping_reason'] == 'OWNER_NAME_DESCRIPTOR_MATCH'  # its own declaration only
    assert all(symbols[i]['owner'] == 'fixture.Pretend$DefaultImpls' for i in pretend['source_mapping_ids'])
    site = next(s for s in result['call_sites'] if s['caller'] == default['id'])
    assert site['source_mapping_ids'] == default['source_mapping_ids']
    assert site['source_mapping_reason'] == default['source_mapping_reason']
    if not compiled[2]:
        assert all(s.get('source_line') is None and s.get('source_file_attribute') is None
                   for s in result['call_sites'] if s['id'].startswith('bytecode-call:'))
    assert site['path'] is None  # generated instruction is not a source call expression
    bytecode_sites = [s for s in result['call_sites'] if s['id'].startswith('bytecode-call:')]
    assert all(s['source_locator_kind'] == 'BYTECODE_ONLY' and s['representation'] == 'BYTECODE'
               for s in bytecode_sites)
    diagnostics = {d.get('call_site_id') for d in result['diagnostics']
                   if d.get('code') == 'BYTECODE_ONLY_CALL_SITE'}
    assert {s['id'] for s in bytecode_sites} <= diagnostics
    root = compiled[0]
    graph = graph_from_response(root, scan_repository(root), result,
            {'id': 'mapping-fixture', 'scope': 'production', 'origin_trust': 'LOCAL_COMPILER_INPUTS',
             'freshness': 'CONTENT_VERIFIED',
             'source_files': {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                              for name in ('Bridge.java', 'Defaults.kt', 'Modern.kt')}})
    restored = KnowledgeGraph.from_dict(graph.to_dict())
    mapping = next(e for e in restored.edges if e.kind == 'maps_to_source' and e.source == default['id'])
    proof = next(e for e in restored.evidence if e['id'] in mapping.evidence_ids)
    assert mapping.target == default['source_mapping_ids'][0]
    assert proof['representation'] == 'DECLARATION_MAPPING' and proof['source_range']
    assert proof['sha256'] == hashlib.sha256((root / 'Defaults.kt').read_bytes()).hexdigest()
    assert proof['artifact_hashes'] == [{'path': str(compiled[1]), 'sha256': artifact_hash(compiled[1])}]
    assert all(e.kind != 'calls' for e in restored.edges if e.source == default['id'] and e.target == mapping.target)


def test_absent_sources_remain_bytecode_only(worker, compiled):
    result = analyze(worker, compiled, sources=False)
    methods = [s for s in result['symbols'] if s.get('kind') == 'bytecode_method']
    assert methods and all(s['source_mapping_ids'] == [] for s in methods)
    diagnostics = {d.get('bytecode_method_id') for d in result['diagnostics']
                   if d.get('code') == 'BYTECODE_ONLY_SOURCE_MAPPING'}
    assert {s['id'] for s in methods} <= diagnostics
    assert not any(f['kind'] == 'maps_to_source' for f in result['facts'])


def test_wrong_source_signature_never_maps_generated_body(worker, compiled):
    root, _, _ = compiled
    original = {name: (root / name).read_bytes() for name in ['Defaults.kt', 'Bridge.java']}
    (root / 'Defaults.kt').write_text('package fixture\ninterface Defaults { fun value(x: Int): String = "other" }\n')
    (root / 'Bridge.java').write_text('package fixture; class Bridge { public Integer get() { return 1; } }')
    try:
        result = analyze(worker, compiled)
    finally:
        for name, data in original.items():
            (root / name).write_bytes(data)
    selected = [s for s in result['symbols'] if s.get('kind') == 'bytecode_method'
                and (s.get('bridge') or (s.get('owner') == 'fixture.Defaults$DefaultImpls' and s.get('name') == 'value'))]
    assert len(selected) == 3
    assert all(s['source_mapping_ids'] == [] for s in selected)
    diagnostics = {d.get('bytecode_method_id') for d in result['diagnostics']
                   if d.get('code') == 'BYTECODE_ONLY_SOURCE_MAPPING'}
    assert {s['id'] for s in selected} <= diagnostics


def test_nontrivial_bridge_body_stays_bytecode_only(worker, compiled):
    """Alter only an actual compiler bridge body; flags/name alone must not map it."""
    root, classes, _ = compiled
    bridge_file = classes / 'fixture/Bridge.class'
    original = bridge_file.read_bytes()
    patcher = root / 'PatchBridge.java'
    patcher.write_text('import java.nio.file.*; import org.jetbrains.org.objectweb.asm.*; '
        'import org.jetbrains.org.objectweb.asm.tree.*; '
        'class PatchBridge { public static void main(String[] args) throws Exception {'
        'var p=Path.of(args[0]); var c=new ClassNode();'
        'new ClassReader(Files.readAllBytes(p)).accept(c,0);'
        'for(var m:c.methods) if(m.name.equals("get") && (m.access&Opcodes.ACC_BRIDGE)!=0) {'
        'var extra=new InsnList();'
        'extra.add(new MethodInsnNode(Opcodes.INVOKESTATIC,"java/lang/System","nanoTime","()J",false));'
        'extra.add(new InsnNode(Opcodes.POP2));m.instructions.insert(extra);}'
        'var w=new ClassWriter(ClassWriter.COMPUTE_MAXS);c.accept(w);Files.write(p,w.toByteArray());}}')
    try:
        subprocess.run([shutil.which('java'), '-cp', str(HOME / 'jvm/target/lib/kotlin-compiler.jar'),
                        str(patcher), str(bridge_file)], check=True, capture_output=True)
        result = analyze(worker, compiled)
    finally:
        bridge_file.write_bytes(original)
        patcher.unlink()
    generated = next(s for s in result['symbols'] if s.get('kind') == 'bytecode_method'
                     and s.get('owner') == 'fixture.Bridge' and s.get('name') == 'get' and s.get('bridge'))
    assert generated['source_mapping_ids'] == []
    assert any(d.get('bytecode_method_id') == generated['id']
               and d['code'] == 'BYTECODE_ONLY_SOURCE_MAPPING' for d in result['diagnostics'])
    assert not any(f['kind'] == 'maps_to_source' and f['source'] == generated['id'] for f in result['facts'])


@pytest.mark.parametrize('foreign_fields', [{'repo_id': 'unrelated', 'module': 'different'}, {'scope': 'test'}],
                         ids=['foreign-owner', 'foreign-scope'])
def test_foreign_default_impls_realm_cannot_claim_local_source(worker, compiled, tmp_path, foreign_fields):
    root, classes, _ = compiled
    local = tmp_path / 'local'
    foreign = tmp_path / 'foreign'
    shutil.copytree(classes, local)
    (foreign / 'fixture').mkdir(parents=True)
    helper = local / 'fixture/Defaults$DefaultImpls.class'
    shutil.move(helper, foreign / 'fixture/Defaults$DefaultImpls.class')
    context = {'id': 'mapping-fixture', 'repo_id': 'fixture', 'module': 'core',
               'source_set': 'main', 'scope': 'production'}
    foreign_context = {**context, **foreign_fields}
    before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    result = request_worker(worker, {'operation': 'analyze', 'root': str(root), 'context': context,
        'sources': ['Bridge.java', 'Defaults.kt', 'Modern.kt'],
        'classpath': [{'path': str(local), 'realm': context}, {'path': str(foreign), 'realm': foreign_context},
                      str(HOME / 'jvm/target/lib/kotlin-stdlib.jar')],
        'bytecode_roots': [{'path': str(local), 'realm': context},
                           {'path': str(foreign), 'realm': foreign_context}]}, cwd=root)
    assert before == {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    generated = next(s for s in result['symbols'] if s.get('kind') == 'bytecode_method'
                     and s.get('owner') == 'fixture.Defaults$DefaultImpls' and s.get('name') == 'value')
    assert generated['source_mapping_ids'] == []
    assert not any(f['kind'] == 'maps_to_source' and f['source'] == generated['id'] for f in result['facts'])
    assert any(d.get('bytecode_method_id') == generated['id']
               and d['code'] == 'BYTECODE_ONLY_SOURCE_MAPPING' for d in result['diagnostics'])


def test_test_scope_bytecode_never_claims_production_source(worker, compiled):
    root, classes, _ = compiled
    context = {'id': 'mapping-fixture', 'repo_id': 'fixture', 'module': 'core',
               'source_set': 'main', 'scope': 'production'}
    test_realm = {**context, 'scope': 'test'}
    before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    result = request_worker(worker, {'operation': 'analyze', 'root': str(root), 'context': context,
        'sources': ['Bridge.java', 'Defaults.kt', 'Modern.kt'],
        'classpath': [{'path': str(classes), 'realm': test_realm},
                      str(HOME / 'jvm/target/lib/kotlin-stdlib.jar')],
        'bytecode_roots': [{'path': str(classes), 'realm': test_realm}]}, cwd=root)
    assert before == {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    methods = [s for s in result['symbols'] if s.get('kind') == 'bytecode_method']
    assert methods and all(s['source_mapping_ids'] == [] for s in methods)
    assert all(s['scope'] == 'test' and s.get('path') is None and s.get('range') is None for s in methods)
    assert not any(f['kind'] == 'maps_to_source' for f in result['facts'])


def test_duplicate_class_bodies_do_not_prove_source_mapping(worker, compiled, tmp_path):
    root, classes, _ = compiled
    alternate = tmp_path / 'Alternate.java'
    alternate.write_text('package fixture; class Bridge { public String get() { return "different body"; } }')
    duplicate = tmp_path / 'duplicate'
    duplicate.mkdir()
    subprocess.run([shutil.which('javac'), '--release', '21', '-proc:none', '-d', str(duplicate), str(alternate)],
                   check=True, capture_output=True)
    assert (classes / 'fixture/Bridge.class').read_bytes() != (duplicate / 'fixture/Bridge.class').read_bytes()
    context = {'id': 'mapping-fixture', 'repo_id': 'fixture', 'module': 'core',
               'source_set': 'main', 'scope': 'production'}
    before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    result = request_worker(worker, {'operation': 'analyze', 'root': str(root), 'context': context,
        'sources': ['Bridge.java', 'Defaults.kt', 'Modern.kt'],
        'classpath': [{'path': str(classes), 'realm': context}, {'path': str(duplicate), 'realm': context},
                      str(HOME / 'jvm/target/lib/kotlin-stdlib.jar')],
        'bytecode_roots': [str(classes), str(duplicate)]}, cwd=root)
    assert before == {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    generated = [s for s in result['symbols'] if s.get('kind') == 'bytecode_method' and s.get('owner') == 'fixture.Bridge']
    assert generated and all(s['source_mapping_ids'] == [] and s['source_mapping_reason'] == 'AMBIGUOUS_BYTECODE_CLASS'
                             for s in generated)
    ids = {s['id'] for s in generated}
    assert not any(f['kind'] == 'maps_to_source' and f['source'] in ids for f in result['facts'])
    assert any(d['code'] == 'DUPLICATE_BYTECODE_CLASS' for d in result['diagnostics'])


def test_same_realm_static_instance_abi_changes_never_map(worker, compiled):
    root, _, _ = compiled
    originals = {name: (root / name).read_bytes() for name in ['Bridge.java', 'Modern.kt']}
    changed_java = originals['Bridge.java'].decode().replace('class Bridge implements Generic<String>', 'class Bridge')
    changed_java = changed_java.replace('public String get() { return helper(); }', 'public static String get() { return "changed"; }')
    changed_java = changed_java.replace('static String value(JavaDefault x)', 'String value(JavaDefault x)')
    (root / 'Bridge.java').write_text(changed_java)
    (root / 'Modern.kt').write_text('package fixture\n'
        'object Modern { @JvmStatic fun greeting(): String = "changed" }\n'
        'class ModernKt { fun staticTop(): String = "changed" }\n')
    try:
        result = analyze(worker, compiled)
    finally:
        for name, data in originals.items():
            (root / name).write_bytes(data)
    symbols = result['symbols']
    expected_source_flags = {('fixture.Bridge', 'get', '()Ljava/lang/String;'): True,
                             ('fixture.Pretend$DefaultImpls', 'value', '(Lfixture/JavaDefault;)Ljava/lang/String;'): False,
                             ('fixture.Modern', 'greeting', '()Ljava/lang/String;'): True,
                             ('fixture.ModernKt', 'staticTop', '()Ljava/lang/String;'): False}
    for (owner, name, descriptor), source_static in expected_source_flags.items():
        generated = next(s for s in symbols if s.get('kind') == 'bytecode_method' and s.get('owner') == owner
                         and s.get('name') == name and s.get('descriptor') == descriptor)
        assert generated['source_mapping_ids'] == []
        assert generated['source_mapping_reason'] == 'SOURCE_METHOD_ABI_MISMATCH'
        source = next(s for s in symbols if s.get('path') and s.get('owner') == owner
                      and s.get('name') == name and s.get('descriptor') == descriptor)
        assert source['jvm_static'] is source_static
        assert generated['jvm_static'] is not source_static
    bridge = next(s for s in symbols if s.get('kind') == 'bytecode_method' and s.get('owner') == 'fixture.Bridge'
                  and s.get('name') == 'get' and s.get('bridge'))
    assert bridge['source_mapping_ids'] == []  # instance delegate cannot map a current static declaration
    default = next(s for s in symbols if s.get('kind') == 'bytecode_method'
                   and s.get('owner') == 'fixture.Defaults$DefaultImpls' and s.get('name') == 'value')
    assert default['source_mapping_ids']  # explicit static-helper -> instance-interface transform survives
    assert default['source_mapping_reason'] == 'KOTLIN_DEFAULT_IMPLS_SIGNATURE'
