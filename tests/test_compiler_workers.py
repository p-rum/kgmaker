"""Real compiler/fixture integration; optional for the dependency-free Python job.

CI sets KGMAKER_REQUIRE_WORKERS=1 so a missing compiler/build cannot be silently
reported as an integration PASS. Ground truth is independently hand-labelled.
"""
import json
import os
import shutil
import unittest
from pathlib import Path

from kgmaker.inspection import command, inspect_frontend, inspect_jvm
from kgmaker.model import KnowledgeGraph
from kgmaker.worker_protocol import WorkerError, handshake, request_worker
from test_control_flow import reachable

ROOT=Path(__file__).parents[1]
FIXTURE=ROOT/'fixtures/build-inspection'


class CompilerWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.jvm=command('jvm');cls.ts=command('typescript')
            if not (FIXTURE/'maven/target/classes/fixture/Worker.class').is_file():
                raise WorkerError('Actual Maven fixture build is required','TOOLCHAIN_UNAVAILABLE')
        except WorkerError as error:
            if os.environ.get('KGMAKER_REQUIRE_WORKERS')=='1':raise AssertionError(str(error)) from error
            raise unittest.SkipTest(str(error))
        cls.truth=json.loads((FIXTURE/'ground-truth.json').read_text())
        cls.context={'id':'test-compiler','repo_id':'fixture','module':'core','source_set':'main','scope':'production'}
        # Resolve the actual fixture classpath, not a mock runner result.
        worker_lib=ROOT/'workers/jvm/target/lib/kotlin-stdlib.jar'
        cp=[{'path':str(FIXTURE/'maven/target/classes'),'realm':cls.context},str(worker_lib)]
        cls.result=inspect_jvm(FIXTURE/'maven',classpath=cp,repo_id='fixture',module='core',publish=False)
        cls.graph=KnowledgeGraph.from_dict(cls.result['graph'])
        cls.frontend=inspect_frontend(FIXTURE/'frontend',ui_framework='react',repo_id='fixture',publish=False)

    def test_p0_jv01_real_mixed_compiler_calls_exactly_match_ground_truth(self):
        actual=sorted((s['caller'].split(':method:')[-1],s['declared_target'].split(':method:')[-1])
                      for s in self.graph.call_sites if s.get('declared_target'))
        expected=sorted((s['caller'],s['target']) for s in self.truth['jvm_calls'])
        self.assertEqual(expected,actual)
        self.assertEqual(5,self.result['coverage']['calls_resolved'])
        self.assertEqual(0,self.result['coverage']['calls_unresolved'])

    def test_offline_refresh_preserves_real_call_sites_and_cfg(self):
        import tempfile
        from contextlib import redirect_stdout
        from io import StringIO
        from unittest.mock import patch
        from kgmaker.cli import scan, hook_context
        from kgmaker.feature import current_graph
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "fixture"
            shutil.copytree(FIXTURE / "maven", root, ignore=shutil.ignore_patterns(".kgmaker"))
            result = inspect_jvm(root, classpath=[str(ROOT / "workers/jvm/target/lib/kotlin-stdlib.jar"),
                                                str(root / "target/classes")])
            original = KnowledgeGraph.from_dict(result["graph"])
            self.assertTrue(original.call_sites)
            self.assertTrue(original.cfgs)
            with patch("subprocess.Popen", side_effect=AssertionError("offline process")):
                with redirect_stdout(StringIO()):
                    self.assertEqual(0, scan(root, generate_docs=False))
                    self.assertEqual(0, hook_context(root))
                graph, _, _ = current_graph(root)
            self.assertEqual(original.call_sites, graph.call_sites)
            self.assertEqual(original.cfgs, graph.cfgs)

    def test_flow01_flow02_compiler_if_branch_preserves_opposite_overloads(self):
        cfg=next(c for c in self.graph.cfgs if 'Worker.choose(Z)' in c['method'])
        sites={s['id']:s for s in self.graph.call_sites}
        blocks={}
        for b in cfg['blocks']:
            if b['kind']=='call':
                for site_id in b['call_site_ids']:
                    target=sites[site_id]['declared_target']
                    if 'process(I)' in target:blocks['int']=b['id']
                    if 'process(Ljava/lang/String;)' in target:blocks['string']=b['id']
        self.assertFalse(reachable(cfg,blocks['int'],blocks['string']))
        self.assertFalse(reachable(cfg,blocks['string'],blocks['int']))

    def test_ts01_ts02_react_handler_and_overloads_use_typechecker_symbols(self):
        graph=KnowledgeGraph.from_dict(self.frontend['graph'])
        signatures={s.get('signature') for s in graph.call_sites}
        self.assertTrue(set(self.truth['typescript_overloads'])<=signatures)
        self.assertTrue(any(e.kind=='handles_event' and e.evidence_kind=='FRAMEWORK_DERIVED' for e in graph.edges))
        self.assertEqual(3,self.frontend['coverage']['calls_resolved'])
        app=next(c for c in graph.cfgs if ':App:' in c['method'])
        sites={s['id'] for s in graph.call_sites if s['caller']==app['method']}
        represented={identity for b in app['blocks'] if b['kind']=='call' for identity in b.get('call_site_ids', [])}
        self.assertEqual(sites, represented)

    def test_ts_reexport_resolves_and_lockfile_change_marks_only_context_stale(self):
        import tempfile
        from kgmaker.feature import current_graph
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'src').mkdir()
            (root / 'tsconfig.json').write_text(json.dumps({
                'compilerOptions': {'target': 'ES2022', 'module': 'commonjs', 'strict': True},
                'include': ['src/**/*.ts'],
            }))
            (root / 'package-lock.json').write_text('{"lockfileVersion":3}')
            (root / 'src/lib.ts').write_text('export function choose(value: number): number { return value + 1; }')
            (root / 'src/index.ts').write_text("export { choose } from './lib';")
            (root / 'src/app.ts').write_text("import { choose } from './index'; export const result = choose(1);")
            result = inspect_frontend(root, repo_id='fixture', module='web', publish=True)
            graph = KnowledgeGraph.from_dict(result['graph'])
            target = next(site['declared_target'] for site in graph.call_sites
                          if site.get('path') == 'src/app.ts' and site.get('declared_target'))
            symbol = next(item for item in graph.symbols if item['id'] == target)
            self.assertEqual('src/lib.ts', symbol['path'])
            self.assertTrue(any(edge.kind == 'alias_of' for edge in graph.edges))

            (root / 'package-lock.json').write_text('{"lockfileVersion":3,"changed":true}')
            refreshed = current_graph(root)[0]
            compiler = next(item for item in refreshed.contexts if item.get('analyzer_version'))
            self.assertEqual('STALE', compiler['freshness'])
            self.assertFalse(refreshed.call_sites)

    def test_unsupported_property_bodies_have_boundaries_instead_of_guessed_callers(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'src/main/kotlin/Holder.kt';source.parent.mkdir(parents=True)
            source.write_text('class Holder { val constructed = source(); val custom: String get() = source(); fun source() = "value" }')
            result=inspect_jvm(root,classpath=[str(ROOT/'workers/jvm/target/lib/kotlin-stdlib.jar')],publish=False)
            graph=KnowledgeGraph.from_dict(result['graph'])
            self.assertEqual('PARTIAL',result['status'])
            self.assertTrue(any(d['code']=='KOTLIN_PROPERTY_BODY_CFG_UNSUPPORTED' for d in graph.diagnostics))
            self.assertTrue(any(n.kind=='unresolved_boundary' and n.name=='KOTLIN_PROPERTY_BODY_CFG_UNSUPPORTED' for n in graph.nodes))
            self.assertFalse(graph.call_sites)

    def test_bytecode_default_method_uses_most_specific_interface_not_classfile_order(self):
        import tempfile
        import subprocess
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'Defaults.java';classes=root/'classes';classes.mkdir()
            source.write_text('package fixture; interface A { default String value(){ return "base"; } } interface B extends A { default String value(){ return "child"; } } class Parent implements A {} class C extends Parent implements A,B {} class D { String call(C c){ return c.value(); } }')
            subprocess.run([shutil.which('javac'),'-proc:none','--release','21','-d',str(classes),str(source)],check=True,capture_output=True)
            result=request_worker(self.jvm,{'operation':'analyze','root':str(root),'context':self.context,'sources':[],
                'classpath':[{'path':str(classes),'realm':self.context}],'bytecode_roots':[str(classes)]},cwd=root)
            site=next(s for s in result['call_sites'] if 'fixture.D.call' in s['caller'] and s.get('declared_target') and '.value()' in s['declared_target'])
            self.assertTrue(site['declared_target'].endswith('fixture.B.value()Ljava/lang/String;'))

    def test_protocol_handshakes_are_versioned_and_log_free(self):
        self.assertIn('java-attribution',handshake(self.jvm,cwd=ROOT)['capabilities'])
        self.assertEqual('5.7.3',handshake(self.ts,cwd=ROOT)['compiler_version'])

    def test_bytecode_is_distinct_and_cha_completeness_is_not_invented(self):
        request={'operation':'analyze','root':str(FIXTURE/'maven'),'context':self.context,
            'sources':['src/main/java/fixture/JavaBridge.java','src/main/kotlin/fixture/Worker.kt'],
            'classpath':[{'path':str(FIXTURE/'maven/target/classes'),'realm':self.context},str(ROOT/'workers/jvm/target/lib/kotlin-stdlib.jar')],
            'bytecode_roots':[str(FIXTURE/'maven/target/classes')]}
        result=request_worker(self.jvm,request,cwd=ROOT)
        self.assertTrue(result['bytecode_cfgs'])
        self.assertTrue(any(s['id'].startswith('bytecode:') for s in result['symbols']))
        self.assertTrue(all(not s.get('dispatch_complete') for s in result['call_sites']))
        self.assertTrue(all(s.get('bytecode_offset') is None for s in result['call_sites'] if s['id'].startswith('bytecode')))


if __name__=='__main__':unittest.main()
