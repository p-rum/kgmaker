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

    def test_ac02_real_end_to_end_context_profile_and_classpath_lifecycle(self):
        import io
        import tempfile
        from contextlib import redirect_stdout
        from unittest.mock import patch
        from kgmaker.analysis_model import inventory_candidate, write_json
        from kgmaker.cli import main
        from kgmaker.feature import current_graph, load_packet, validate
        from kgmaker.store import load_graph

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'fixture'
            shutil.copytree(FIXTURE / 'maven', root, ignore=shutil.ignore_patterns('.kgmaker'))
            flow = root / 'src/main/kotlin/fixture/Flow.kt'
            flow.write_text('data class Input(val value: Double)\n'
                            'fun twice(input: Input): Double = input.value * 2\n')
            (root / 'requirement.md').write_text('Trace Worker calls and Input.value impact.')
            classpath = [str(ROOT / 'workers/jvm/target/lib/kotlin-stdlib.jar'),
                         str(root / 'target/classes')]
            default = inspect_jvm(root, classpath=classpath, repo_id='fixture', module='core',
                                  build_context={'spring_profiles': ['default']})['context']
            special = inspect_jvm(root, classpath=classpath, repo_id='fixture', module='core',
                                  build_context={'spring_profiles': ['special']})['context']
            self.assertNotEqual(default['selection_key'], special['selection_key'])
            self.assertEqual({default['id'], special['id']},
                             {c['id'] for c in load_graph(root).contexts if c.get('analyzer_version')})

            real_popen = __import__('subprocess').Popen
            def git_only(argv, *args, **kwargs):
                self.assertIsInstance(argv, list)
                self.assertEqual('git', argv[0], 'offline lifecycle spawned a worker/project process')
                return real_popen(argv, *args, **kwargs)
            def cli(*argv):
                output = io.StringIO()
                with patch('sys.argv', ['kgmaker', *argv, '--root', str(root)]), redirect_stdout(output):
                    with self.assertRaises(SystemExit) as result:
                        main()
                return result.exception.code, output.getvalue()

            with patch('subprocess.Popen', side_effect=git_only):
                self.assertEqual(0, cli('scan', '--no-docs')[0])
                self.assertEqual(0, cli('hook-context')[0])
                query_code, query_output = cli('query', 'Worker', '--scope', 'production',
                                               '--context', default['id'])
                self.assertEqual(0, query_code, query_output)
                self.assertIn('Worker', query_output)
                graph = current_graph(root)[0]
                seed = next(node.id for node in graph.nodes if node.name == 'Input.value')
                impact_code, impact_output = cli('impact', '--entity', seed, '--include-data-flow',
                                                 '--format', 'json', '--scope', 'production',
                                                 '--context', default['id'])
                self.assertEqual(0, impact_code, impact_output)
                self.assertTrue(json.loads(impact_output)['paths'])

                prepare_code, prepare_output = cli(
                    'feature', 'prepare', '--requirement', 'requirement.md', '--id', 'ac02',
                    '--scope', 'production', '--context', default['id'], '--token-budget', '100000')
                self.assertEqual(0, prepare_code, prepare_output)
                packet = load_packet(root, 'ac02')
                candidate = inventory_candidate(packet)
                candidate_path = root / '.kgmaker/analyses/ac02/candidate.json'
                write_json(candidate_path, candidate)
                self.assertEqual(0, cli('feature', 'validate', '--analysis', 'ac02',
                                        '--candidate', '.kgmaker/analyses/ac02/candidate.json')[0])
                self.assertEqual(0, cli('feature', 'apply', '--analysis', 'ac02',
                                        '--candidate', '.kgmaker/analyses/ac02/candidate.json')[0])
                report_code, report_output = cli('feature', 'report', '--analysis', 'ac02')
                self.assertEqual(0, report_code, report_output)
                self.assertTrue((root / 'docs/generated/features/ac02.md').is_file())

                # Selecting another profile produces a new packet revision and
                # invalidates the already applied candidate without guessing a profile.
                self.assertEqual(0, cli(
                    'feature', 'prepare', '--requirement', 'requirement.md', '--id', 'ac02',
                    '--scope', 'production', '--context', special['id'], '--token-budget', '100000')[0])
                profile_packet = load_packet(root, 'ac02')
                self.assertEqual(2, profile_packet['revision'])
                self.assertEqual(special['id'], profile_packet['graph_selection']['context_id'])
                self.assertEqual(3, validate(root, 'ac02', candidate)['exit_code'])

                # A classpath content change invalidates both variants and removes
                # compiler facts from every offline projection.
                artifact = root / 'target/classes/fixture/Worker.class'
                artifact.write_bytes(artifact.read_bytes() + b'changed')
                stale_graph = current_graph(root)[0]
                compiler = [c for c in stale_graph.contexts if c.get('analyzer_version')]
                self.assertEqual({'STALE'}, {c['freshness'] for c in compiler})
                self.assertFalse(stale_graph.call_sites)
                self.assertEqual(3, validate(root, 'ac02', inventory_candidate(profile_packet))['exit_code'])

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

    def test_property_initializer_uses_primary_constructor_and_custom_accessor_has_exact_caller(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'src/main/kotlin/Holder.kt';source.parent.mkdir(parents=True)
            source.write_text('class Holder { val constructed = source(); val custom: String get() = source(); fun source() = "value" }')
            result=inspect_jvm(root,classpath=[str(ROOT/'workers/jvm/target/lib/kotlin-stdlib.jar')],publish=False)
            graph=KnowledgeGraph.from_dict(result['graph'])
            self.assertFalse(any(d['code']=='KOTLIN_PROPERTY_INITIALIZER_CFG_UNSUPPORTED' for d in graph.diagnostics))
            source_calls=[site for site in graph.call_sites if '.source()' in (site.get('declared_target') or '')]
            self.assertEqual(2,len(source_calls))
            self.assertTrue(any('.<init>()V' in site['caller'] for site in source_calls))
            self.assertTrue(any('.getCustom()' in site['caller'] for site in source_calls))

    def test_jv02_kotlin_constructor_lambda_reference_operator_and_function_metadata(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'src/main/kotlin/Advanced.kt';source.parent.mkdir(parents=True)
            source.write_text('''package fixture
class Advanced(val seed: Int) {
  var label: String = consume("initial")
    get() = field
    set(next) { field = next }
  init { consume("init") }
  constructor(): this(1) { consume("secondary") }
  inline fun <T> apply(value: T, transform: (T) -> String): String = transform(value)
  operator fun plus(other: Advanced): Advanced = Advanced(seed + other.seed)
  suspend fun suspendValue(): String = consume("suspend")
  fun consume(value: String): String = value
  fun readLabel(): String = label
  fun writeLabel() { label = "changed" }
  fun scenario(): String {
    val reference = ::consume
    val lambda = { value: String -> consume(value) }
    val combined = this + Advanced()
    return apply("x", lambda) + reference("r") + combined.seed
  }
}''')
            result=inspect_jvm(root,classpath=[str(ROOT/'workers/jvm/target/lib/kotlin-stdlib.jar')],publish=False)
            graph=KnowledgeGraph.from_dict(result['graph'])
            sites=[site for site in graph.call_sites if site.get('path')=='src/main/kotlin/Advanced.kt']
            self.assertTrue(any(site['invocation_kind']=='CONSTRUCTOR' and '.<init>()V' in (site.get('declared_target') or '') for site in sites))
            self.assertTrue(any(site['invocation_kind']=='METHOD_REFERENCE' and '.consume(' in (site.get('declared_target') or '') for site in sites))
            operator=next(site for site in sites if site['invocation_kind']=='OPERATOR')
            self.assertIn('.plus(',operator['declared_target'])
            self.assertEqual('KOTLIN_COMPILER_RESOLVED_OPERATOR',operator['resolution_reason'])
            lambda_symbol=next(symbol for symbol in graph.symbols if symbol.get('name')=='<lambda>')
            self.assertTrue(any(site['caller']==lambda_symbol['id'] and '.consume(' in (site.get('declared_target') or '') for site in sites))
            apply_symbol=next(symbol for symbol in graph.symbols if symbol.get('name')=='apply')
            suspend_symbol=next(symbol for symbol in graph.symbols if symbol.get('name')=='suspendValue')
            self.assertTrue(apply_symbol['inline'])
            self.assertEqual([False,False],apply_symbol['default_arguments'])
            self.assertTrue(suspend_symbol['suspend'])
            accessors=[site for site in sites if site['invocation_kind']=='ACCESSOR']
            self.assertTrue(any('.getLabel()' in (site.get('declared_target') or '') for site in accessors))
            self.assertTrue(any('.setLabel(' in (site.get('declared_target') or '') for site in accessors))
            getter=next(cfg for cfg in graph.cfgs if '.getLabel()' in cfg['method'])
            setter=next(cfg for cfg in graph.cfgs if '.setLabel(' in cfg['method'])
            self.assertEqual('COMPLETE_WITHIN_SUPPORTED_SYNTAX',getter['status'])
            self.assertEqual('COMPLETE_WITHIN_SUPPORTED_SYNTAX',setter['status'])
            self.assertFalse(any(site['caller'] in {getter['method'],setter['method']} and site['invocation_kind']=='ACCESSOR'
                                 for site in sites))
            primary=next(cfg for cfg in graph.cfgs if '.<init>(I)V' in cfg['method'])
            primary_calls={identity for block in primary['blocks'] for identity in block.get('call_site_ids', [])}
            constructor_consumes=[site for site in sites if site['caller']==primary['method'] and '.consume(' in (site.get('declared_target') or '')]
            self.assertEqual(2,len(constructor_consumes))
            self.assertTrue({site['id'] for site in constructor_consumes} <= primary_calls)
            for method_name,accessor_site in (
                    ('.readLabel()',next(site for site in accessors if '.getLabel()' in site['declared_target'])),
                    ('.writeLabel()',next(site for site in accessors if '.setLabel(' in site['declared_target']))):
                cfg=next(item for item in graph.cfgs if method_name in item['method'])
                represented={identity for block in cfg['blocks'] for identity in block.get('call_site_ids', [])}
                self.assertIn(accessor_site['id'],represented)
            scenario=next(cfg for cfg in graph.cfgs
                          if ':method:fixture.Advanced.scenario()' in cfg['method']
                          and not cfg['method'].startswith('lambda:'))
            represented={identity for block in scenario['blocks'] for identity in block.get('call_site_ids', [])}
            self.assertIn(operator['id'],represented)

    def test_kotlin_file_facade_and_object_initializers_keep_distinct_callers(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'src/main/kotlin/Initializers.kt';source.parent.mkdir(parents=True)
            source.write_text('''package fixture
fun make(value: String): String = value
val topLevel = make("top")
object Singleton {
  val value = make("object")
  init { make("init") }
}''')
            result=inspect_jvm(root,classpath=[str(ROOT/'workers/jvm/target/lib/kotlin-stdlib.jar')],publish=False)
            graph=KnowledgeGraph.from_dict(result['graph'])
            calls=[site for site in graph.call_sites if '.make(' in (site.get('declared_target') or '')]
            facade=next(site for site in calls if 'InitializersKt.<clinit>()V' in site['caller'])
            object_calls=[site for site in calls if 'Singleton.<init>()V' in site['caller']]
            self.assertEqual(2,len(object_calls))
            self.assertNotEqual(facade['caller'],object_calls[0]['caller'])
            for caller,expected in ((facade['caller'],{facade['id']}),
                                    (object_calls[0]['caller'],{site['id'] for site in object_calls})):
                cfg=next(item for item in graph.cfgs if item['method']==caller)
                represented={identity for block in cfg['blocks'] for identity in block.get('call_site_ids', [])}
                self.assertTrue(expected <= represented)
            self.assertFalse(any(d['code'] in {'KOTLIN_PROPERTY_INITIALIZER_CFG_UNSUPPORTED','KOTLIN_FILE_INITIALIZER_CFG_UNSUPPORTED'}
                                 for d in graph.diagnostics))

    def test_ac05_spring_profiles_conditions_qualifier_primary_and_short_name_guard(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            sources={
                'org/springframework/stereotype/Service.java': '''package org.springframework.stereotype;
                  import java.lang.annotation.*; @Target(ElementType.TYPE) @Retention(RetentionPolicy.RUNTIME)
                  public @interface Service { String value() default ""; }''',
                'org/springframework/context/annotation/Profile.java': '''package org.springframework.context.annotation;
                  import java.lang.annotation.*; @Target(ElementType.TYPE) @Retention(RetentionPolicy.RUNTIME)
                  public @interface Profile { String[] value(); }''',
                'org/springframework/context/annotation/Primary.java': '''package org.springframework.context.annotation;
                  import java.lang.annotation.*; @Target(ElementType.TYPE) @Retention(RetentionPolicy.RUNTIME)
                  public @interface Primary {}''',
                'org/springframework/context/annotation/Conditional.java': '''package org.springframework.context.annotation;
                  import java.lang.annotation.*; @Target(ElementType.TYPE) @Retention(RetentionPolicy.RUNTIME)
                  public @interface Conditional { Class<?>[] value(); }''',
                'org/springframework/context/annotation/Configuration.java': '''package org.springframework.context.annotation;
                  import java.lang.annotation.*; @Target(ElementType.TYPE) @Retention(RetentionPolicy.RUNTIME)
                  public @interface Configuration {}''',
                'org/springframework/context/annotation/Import.java': '''package org.springframework.context.annotation;
                  import java.lang.annotation.*; @Target(ElementType.TYPE) @Retention(RetentionPolicy.RUNTIME)
                  public @interface Import { Class<?>[] value(); }''',
                'org/springframework/context/annotation/Bean.java': '''package org.springframework.context.annotation;
                  import java.lang.annotation.*; @Target(ElementType.METHOD) @Retention(RetentionPolicy.RUNTIME)
                  public @interface Bean { String[] value() default {}; String[] name() default {}; }''',
                'org/springframework/beans/factory/annotation/Qualifier.java': '''package org.springframework.beans.factory.annotation;
                  import java.lang.annotation.*; @Target({ElementType.TYPE,ElementType.FIELD}) @Retention(RetentionPolicy.RUNTIME)
                  public @interface Qualifier { String value(); }''',
                'org/springframework/boot/autoconfigure/condition/ConditionalOnProperty.java': '''package org.springframework.boot.autoconfigure.condition;
                  import java.lang.annotation.*; @Target(ElementType.TYPE) @Retention(RetentionPolicy.RUNTIME)
                  public @interface ConditionalOnProperty { String name(); String havingValue() default ""; boolean matchIfMissing() default false; }''',
                'org/springframework/transaction/annotation/Transactional.java': '''package org.springframework.transaction.annotation;
                  import java.lang.annotation.*; @Target(ElementType.METHOD) @Retention(RetentionPolicy.RUNTIME)
                  public @interface Transactional {}''',
                'org/springframework/beans/factory/ObjectProvider.java': '''package org.springframework.beans.factory;
                  public interface ObjectProvider<T> { T getObject(); }''',
                'fake/Service.java': 'package fake; public @interface Service {}',
                'app/DomainService.java': '''package app;
                  import java.lang.annotation.*; import org.springframework.stereotype.Service;
                  @Service @Target(ElementType.TYPE) @Retention(RetentionPolicy.RUNTIME)
                  public @interface DomainService {}''',
                'outside/OutsideBean.java': '''package outside;
                  import org.springframework.stereotype.Service; @Service public class OutsideBean {}''',
                'external/ImportedProduct.java': 'package external; public class ImportedProduct {}',
                'external/PlainImported.java': 'package external; public class PlainImported {}',
                'external/ImportedConfig.java': '''package external;
                  import org.springframework.context.annotation.Configuration;
                  import org.springframework.context.annotation.Bean;
                  import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
                  @Configuration @ConditionalOnProperty(name="feature.imported",havingValue="true")
                  public class ImportedConfig { @Bean public ImportedProduct importedProduct() { return new ImportedProduct(); } }''',
                'app/SpringFixture.java': '''package app;
                  import org.springframework.stereotype.Service;
                  import org.springframework.context.annotation.Profile;
                  import org.springframework.context.annotation.Primary;
                  import org.springframework.context.annotation.Conditional;
                  import org.springframework.context.annotation.Configuration;
                  import org.springframework.context.annotation.Import;
                  import org.springframework.context.annotation.Bean;
                  import org.springframework.beans.factory.annotation.Qualifier;
                  import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
                  import org.springframework.transaction.annotation.Transactional;
                  import org.springframework.beans.factory.ObjectProvider;
                  import external.ImportedConfig; import external.ImportedProduct; import external.PlainImported;
                  import java.util.List; import java.util.Map; import java.util.Optional;
                  interface Gateway {}
                  @Service("blueGateway") @Profile("blue") class Blue implements Gateway {}
                  @Service("greenGateway") @Profile("green") @Primary class Green implements Gateway {}
                  @Service("conditionalGateway") @ConditionalOnProperty(name="feature.custom",havingValue="true")
                  class ConditionalGateway implements Gateway {}
                  class CustomCondition {}
                  @Service @Conditional(CustomCondition.class) class CustomOnly {}
                  @DomainService class MetaBean {}
                  @Configuration @Import({ImportedConfig.class,PlainImported.class}) class MainConfig {}
                  class InvalidFactory { @Bean ImportedProduct falseBean() { return new ImportedProduct(); } }
                  @Service class Consumer { Gateway gateway; @Qualifier("blueGateway") Gateway qualified;
                    List<Gateway> gateways; Map<String,Gateway> gatewayMap;
                    Optional<Gateway> optionalGateway; ObjectProvider<Gateway> gatewayProvider;
                    ImportedProduct importedProduct;
                    @Transactional void advised() {} void local() { advised(); } }
                  @fake.Service class NotSpringBean {}
                ''',
            }
            for relative,text in sources.items():
                path=root/'src/main/java'/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)

            def inspect(profiles,properties):
                result=inspect_jvm(root,classpath=[],publish=False,
                    build_context={'spring_profiles':profiles,'spring_properties':properties,
                                   'spring_available_classes':[],'spring_component_packages':['app']})
                return KnowledgeGraph.from_dict(result['graph'])

            blue=inspect(['blue'],{'feature.custom':'false'})
            selected_context=next(item for item in blue.contexts if item.get('language')=='jvm')
            self.assertEqual('annotation-source-v5',selected_context['framework_rule_versions']['spring'])
            self.assertEqual('annotation-source-v5',selected_context['framework_analysis']['spring'])
            beans={node.name:node.id for node in blue.nodes if node.kind=='spring_bean'}
            injections={node.name:node.id for node in blue.nodes if node.kind=='spring_injection'}
            selected={(edge.source,edge.target) for edge in blue.edges if edge.kind=='injects_bean'}
            self.assertIn((injections['Consumer.gateway'],beans['blueGateway']),selected,
                          {'beans':beans,'selected':selected,
                           'bean_metadata':{node.name:node.metadata for node in blue.nodes if node.kind=='spring_bean'}})
            self.assertIn((injections['Consumer.qualified'],beans['blueGateway']),selected)
            self.assertIn((injections['Consumer.gateways'],beans['blueGateway']),selected)
            self.assertIn((injections['Consumer.gatewayMap'],beans['blueGateway']),selected)
            self.assertIn((injections['Consumer.optionalGateway'],beans['blueGateway']),selected)
            self.assertTrue(any(edge.kind=='may_inject_bean' and edge.source==injections['Consumer.gatewayProvider']
                                and edge.target==beans['blueGateway'] for edge in blue.edges))
            injection_nodes={node.name:node for node in blue.nodes if node.kind=='spring_injection'}
            self.assertEqual('collection',injection_nodes['Consumer.gateways'].metadata['injection_kind'])
            self.assertEqual('map',injection_nodes['Consumer.gatewayMap'].metadata['injection_kind'])
            self.assertEqual('optional',injection_nodes['Consumer.optionalGateway'].metadata['injection_kind'])
            self.assertEqual('provider',injection_nodes['Consumer.gatewayProvider'].metadata['injection_kind'])
            self.assertNotIn('NotSpringBean',beans)
            self.assertIn('MetaBean',beans)
            imported_config=next(node for node in blue.nodes if node.kind=='spring_bean' and node.name=='ImportedConfig')
            imported_product=next(node for node in blue.nodes if node.kind=='spring_bean' and node.name=='importedProduct')
            self.assertEqual('INACTIVE',imported_config.metadata['condition_status'])
            self.assertEqual('INACTIVE',imported_product.metadata['condition_status'])
            self.assertEqual('ACTIVE',next(node for node in blue.nodes if node.kind=='spring_bean'
                                           and node.name=='PlainImported').metadata['condition_status'])
            self.assertNotIn('falseBean',beans)
            self.assertTrue(any(item.get('code')=='SPRING_BEAN_OUTSIDE_CONFIGURATION' for item in blue.diagnostics))
            outside=next(node for node in blue.nodes if node.kind=='spring_bean' and node.name=='OutsideBean')
            self.assertEqual('INACTIVE',outside.metadata['condition_status'])
            self.assertIn('org.springframework.stereotype.Service',
                          next(node for node in blue.nodes if node.kind=='spring_bean' and node.name=='MetaBean').metadata['stereotype_chain'])
            self.assertTrue(any(item.get('code')=='SPRING_CONDITION_UNRESOLVED' for item in blue.diagnostics))
            self.assertTrue(any(node.kind=='spring_proxy_boundary' and node.name=='self-invocation:advised'
                                for node in blue.nodes))
            self.assertTrue(any(edge.kind=='bypasses_proxy' for edge in blue.edges))

            green=inspect(['green'],{'feature.custom':'false'})
            green_beans={node.name:node.id for node in green.nodes if node.kind=='spring_bean'}
            green_injection=next(node.id for node in green.nodes if node.kind=='spring_injection' and node.name=='Consumer.gateway')
            self.assertTrue(any(edge.kind=='injects_bean' and edge.source==green_injection and edge.target==green_beans['greenGateway']
                                for edge in green.edges),
                            {'beans':{node.name:node.metadata for node in green.nodes if node.kind=='spring_bean'},
                             'edges':[(edge.kind,edge.target) for edge in green.edges if edge.source==green_injection],
                             'diagnostics':green.diagnostics})

            ambiguous=inspect(['blue'],{'feature.custom':'true'})
            gateway=next(node.id for node in ambiguous.nodes if node.kind=='spring_injection' and node.name=='Consumer.gateway')
            self.assertFalse(any(edge.kind=='injects_bean' and edge.source==gateway for edge in ambiguous.edges))
            self.assertGreaterEqual(sum(edge.kind=='may_inject_bean' and edge.source==gateway for edge in ambiguous.edges),2)
            self.assertTrue(any(item.get('code')=='SPRING_AMBIGUOUS_BEAN' for item in ambiguous.diagnostics))

            imported=inspect(['blue'],{'feature.custom':'false','feature.imported':'true'})
            imported_beans={node.name:node for node in imported.nodes if node.kind=='spring_bean'}
            imported_injection=next(node.id for node in imported.nodes if node.kind=='spring_injection'
                                    and node.name=='Consumer.importedProduct')
            self.assertEqual('ACTIVE',imported_beans['ImportedConfig'].metadata['condition_status'])
            self.assertEqual('ACTIVE',imported_beans['importedProduct'].metadata['condition_status'])
            self.assertTrue(any(edge.kind=='injects_bean' and edge.source==imported_injection
                                and edge.target==imported_beans['importedProduct'].id for edge in imported.edges))

            unknown=inspect(None,{})
            self.assertTrue(any(item.get('code')=='SPRING_CONDITION_UNRESOLVED' for item in unknown.diagnostics))
            unknown_injections={node.id for node in unknown.nodes if node.kind=='spring_injection'}
            self.assertFalse(any(edge.kind=='injects_bean' for edge in unknown.edges
                                 if edge.source in unknown_injections))

    def test_ac06_real_javac_embedded_id_and_association_roles(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            annotations={
                'Entity':'@Target(ElementType.TYPE) public @interface Entity {}',
                'Table':'@Target(ElementType.TYPE) public @interface Table { String name(); String schema() default ""; }',
                'Embeddable':'@Target(ElementType.TYPE) public @interface Embeddable {}',
                'EmbeddedId':'@Target({ElementType.FIELD,ElementType.METHOD}) public @interface EmbeddedId {}',
                'Id':'@Target({ElementType.FIELD,ElementType.METHOD}) public @interface Id {}',
                'Column':'@Target({ElementType.FIELD,ElementType.METHOD,ElementType.ANNOTATION_TYPE}) public @interface Column { String name() default ""; }',
                'AttributeOverride':'@Target({ElementType.FIELD,ElementType.METHOD}) public @interface AttributeOverride { String name(); Column column(); }',
                'ManyToOne':'@Target({ElementType.FIELD,ElementType.METHOD}) public @interface ManyToOne {}',
                'OneToMany':'@Target({ElementType.FIELD,ElementType.METHOD}) public @interface OneToMany { String mappedBy() default ""; }',
                'JoinColumn':'@Target({ElementType.FIELD,ElementType.METHOD}) public @interface JoinColumn { String name() default ""; }',
                'NamedQuery':'@Target(ElementType.TYPE) public @interface NamedQuery { String name(); String query(); }',
            }
            for name,declaration in annotations.items():
                path=root/'src/main/java/jakarta/persistence'/f'{name}.java';path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(f'package jakarta.persistence; import java.lang.annotation.*; @Retention(RetentionPolicy.RUNTIME) {declaration}')
            repository_api=root/'src/main/java/org/springframework/data/jpa/repository/JpaRepository.java'
            repository_api.parent.mkdir(parents=True,exist_ok=True)
            repository_api.write_text('package org.springframework.data.jpa.repository; public interface JpaRepository<T,ID> {}')
            query_api=root/'src/main/java/org/springframework/data/jpa/repository/Query.java'
            query_api.write_text('''package org.springframework.data.jpa.repository;
              import java.lang.annotation.*; @Target(ElementType.METHOD) @Retention(RetentionPolicy.RUNTIME)
              public @interface Query { String value() default ""; String name() default ""; boolean nativeQuery() default false; }''')
            model=root/'src/main/java/example/Model.java';model.parent.mkdir(parents=True,exist_ok=True)
            model.write_text('''package example;
import jakarta.persistence.*; import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
@Embeddable class OrderId { @Column(name="tenant_id") String tenant; @Column(name="order_no") String number; }
@Entity @Table(name="orders") @NamedQuery(name="Order.byTenant", query="select o from Order o where o.id.tenant = :tenant") class Order {
  @EmbeddedId @AttributeOverride(name="tenant", column=@Column(name="order_tenant")) OrderId id;
  @ManyToOne @JoinColumn(name="customer_id") Customer customer;
}
@Entity @Table(name="customers") class Customer {
  @Id @Column(name="id") Long id;
  @OneToMany(mappedBy="customer") List<Order> orders;
}
@Entity @Table(name="profiles") class Profile {
  private Long id;
  @Id @Column(name="profile_id") public Long getId() { return id; }
}
interface OrderView { String getTenant(); }
interface OrderRepository extends JpaRepository<Order,OrderId> {
  List<Order> findTop3ByCustomerIdAndIdTenantOrderByIdTenantDesc(Long customerId, String tenant);
  long deleteByCustomerId(Long customerId);
  List<Order> findByMissingValue(String value);
  @Query("select o from Order o where o.customer.id = :customerId")
  List<Order> loadByCustomer(Long customerId);
  @Query(value="select * from orders where customer_id = :customerId", nativeQuery=true)
  List<OrderView> loadNative(Long customerId);
  @Query("select o from Order o where o.id.tenant = :missing")
  List<Order> brokenExplicit(String tenant);
  @Query(name="Order.byTenant") List<Order> namedByTenant(String tenant);
}''')
            result=inspect_jvm(root,classpath=[],publish=False,
                               build_context={'database_id':'primary','schema_stream_id':'main','persistence_unit':'orders'})
            graph=KnowledgeGraph.from_dict(result['graph'])
            selected_context=next(item for item in graph.contexts if item.get('language')=='jvm')
            self.assertEqual('annotation-source-v4',selected_context['framework_rule_versions']['jpa'])
            self.assertEqual('annotation-source-v4',selected_context['framework_analysis']['jpa'])
            self.assertIn('OrderId',{node.name for node in graph.nodes if node.kind=='orm_embeddable'})
            self.assertNotIn('OrderId',{node.name for node in graph.nodes if node.kind=='orm_table'})
            order_id=next(node for node in graph.nodes if node.kind=='orm_attribute' and node.name=='Order.id')
            self.assertTrue(order_id.metadata['identifier'])
            self.assertTrue(any(edge.kind=='embeds_type' and edge.source==order_id.id for edge in graph.edges))
            embedded_attribute=next(node for node in graph.nodes if node.kind=='orm_embeddable_attribute'
                                    and node.name=='OrderId.tenant')
            self.assertEqual('tenant_id',embedded_attribute.metadata['default_column'])
            self.assertTrue(any(edge.kind=='overrides_attribute' and edge.target==embedded_attribute.id
                                for edge in graph.edges))
            associations={node.name:node for node in graph.nodes if node.kind=='orm_association'}
            self.assertEqual('OWNING',associations['Order.customer'].metadata['association_role'])
            self.assertEqual('INVERSE',associations['Customer.orders'].metadata['association_role'])
            self.assertTrue(any(edge.kind=='inverse_of' and edge.source==associations['Customer.orders'].id
                                and edge.target==associations['Order.customer'].id for edge in graph.edges))
            columns={node.name for node in graph.nodes if node.kind=='orm_column'}
            self.assertIn('order_tenant',columns)
            self.assertIn('customer_id',columns)
            self.assertNotIn('customer',columns)
            self.assertNotIn('orders',columns)
            profile_id=next(node for node in graph.nodes if node.kind=='orm_attribute' and node.name=='Profile.id')
            self.assertEqual('PROPERTY',profile_id.metadata['access'])
            self.assertIn('profile_id',columns)
            queries={node.name:node for node in graph.nodes if node.kind=='orm_query'}
            validated=queries['findTop3ByCustomerIdAndIdTenantOrderByIdTenantDesc:DERIVED']
            self.assertTrue(validated.metadata['validated'])
            self.assertEqual(['customer.id','id.tenant'],
                             [item['resolved_path'] for item in validated.metadata['predicates']])
            self.assertTrue(any(edge.kind=='query_reads' and edge.source==validated.id for edge in graph.edges))
            deleting=queries['deleteByCustomerId:DERIVED']
            self.assertTrue(any(edge.kind=='query_deletes' and edge.source==deleting.id for edge in graph.edges))
            self.assertTrue(any(item.get('code')=='SPRING_DATA_DERIVED_PROPERTY_UNRESOLVED'
                                and item.get('properties')==['missingValue'] for item in graph.diagnostics))
            jpql=queries['loadByCustomer:JPQL']
            self.assertTrue(jpql.metadata['validated'])
            self.assertEqual(['customerId'],jpql.metadata['parameters'])
            self.assertTrue(any(edge.kind=='query_reads' and edge.source==jpql.id
                                and edge.target==next(node.id for node in graph.nodes if node.name=='Order' and node.kind=='class')
                                for edge in graph.edges))
            customer_id=next(node.id for node in graph.nodes if node.kind=='orm_attribute' and node.name=='Customer.id')
            self.assertTrue(any(edge.kind=='filters_by' and edge.source==jpql.id and edge.target==customer_id
                                for edge in graph.edges))
            native=queries['loadNative:NATIVE_SQL']
            self.assertTrue(any(edge.kind=='query_reads' and edge.source==native.id
                                and edge.target==next(node.id for node in graph.nodes if node.kind=='orm_table' and node.name=='orders')
                                for edge in graph.edges))
            self.assertTrue(any(edge.kind=='returns_projection' and edge.source==native.id
                                and edge.target==next(node.id for node in graph.nodes if node.name=='OrderView')
                                for edge in graph.edges))
            self.assertTrue(any(item.get('code')=='SPRING_DATA_QUERY_PARAMETER_UNBOUND'
                                and item.get('parameters')==['missing'] for item in graph.diagnostics))
            named=queries['namedByTenant:JPQL']
            named_definition=next(node for node in graph.nodes if node.kind=='orm_named_query' and node.name=='Order.byTenant')
            self.assertTrue(named.metadata['validated'])
            self.assertTrue(any(edge.kind=='uses_named_query' and edge.source==named.id
                                and edge.target==named_definition.id for edge in graph.edges))

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
