"""Actual pinned Spring API/Javac annotation mirror proof for T010."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
from unittest.mock import patch

import pytest

from kgmaker.inspection import command, inspect_jvm
from kgmaker.worker_protocol import WorkerError
from kgmaker.workspace import snapshot_workspace
from test_t010_catalog_http_providers import workspace_inputs, projection, interface_nodes

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / 'workers'


def test_actual_spring_class_method_mirrors_preserve_handlers_and_route_case(tmp_path):
    cache = Path(os.environ.get('KGMAKER_TEST_MAVEN_REPOSITORY', str(Path.home() / '.m2/repository')))
    lock = json.loads((ROOT / 'fixtures/http-provider-projection/dependencies.lock.json').read_text())
    try:
        command('jvm', HOME)
        classpath = []
        for item in lock['artifacts']:
            artifact = cache / item['path']
            if not artifact.is_file():
                raise WorkerError('Pinned Spring6.2.2 API fixture unavailable', 'TOOLCHAIN_UNAVAILABLE')
            assert hashlib.sha256(artifact.read_bytes()).hexdigest() == item['sha256']
            classpath.append(str(artifact))
    except WorkerError as error:
        if os.environ.get('KGMAKER_REQUIRE_HTTP_PROVIDERS') == '1':
            pytest.fail(str(error))
        pytest.skip('actual HTTP provider compiler prerequisite unavailable: ' + str(error))
    workspace, _, _ = workspace_inputs(tmp_path)
    beta = tmp_path / 'beta/src/main/java'
    beta.mkdir(parents=True)
    (beta / 'Beta.java').write_text('''
import org.springframework.web.bind.annotation.*;
@RequestMapping("/")
class Beta {
  @PostMapping("/orders") public void orders() { }
  @PostMapping public void root() { }
  @PostMapping({"/alias-one", "/alias-two"}) public void aliases() { }
  @RequestMapping(value="/multi", method={RequestMethod.GET, RequestMethod.POST}) public void multi() { }
  @PostMapping("/same") public void same() {} @PostMapping("/same") public void same(int number) {} } @RequestMapping("/") class Other { @PostMapping("/same") public void same() {} }
''')
    (beta / 'Inheritance.java').write_text("""
import org.springframework.web.bind.annotation.*;
@RequestMapping("/parent") class ParentController { }
class Inherited extends ParentController { @PostMapping("/inherited") public void inherited() {} }
@RequestMapping("/local") class Direct extends ParentController { @PostMapping("/direct") public void direct() {} }
@RequestMapping("/custom") @interface CustomPrefix { }
@CustomPrefix class Composed { @PostMapping("/composed") public void composed() {} }
class NoPrefix { @PostMapping("/no-prefix") public void plain() {} }
@RequestMapping({"/A", "/B"}) class MultiPrefix { @PostMapping("/branch") public void branch() {} }
""")
    prefixes = ','.join('"/C' + str(index) + '"' for index in range(9))
    methods = ','.join('"/M' + str(index) + '"' for index in range(9))
    (beta / 'Truncated.java').write_text('import org.springframework.web.bind.annotation.*;\n'
        '@RequestMapping({' + prefixes + '}) class Truncated { @PostMapping({' + methods + '}) public void many() {} }\n')
    for repo in ['alpha', 'beta']:
        root = tmp_path / repo
        sources = sorted(path.relative_to(root).as_posix() for path in root.rglob('*.java'))
        result = inspect_jvm(root, home=HOME, classpath=classpath, repo_id=repo,
                             module='http-app', sources=sources)
        assert any(node['kind'] == 'spring_endpoint' for node in result['graph']['nodes'])
    _, coverage, _, graph, _ = snapshot_workspace(Path(workspace['_manifest_path']))
    with patch('subprocess.Popen', side_effect=AssertionError('pure projection process')),\
         patch('socket.socket', side_effect=AssertionError('pure projection network')):
        document = projection(workspace, graph, source_coverage=coverage)
    strong = [node for node in interface_nodes(document) if 'FRAMEWORK_DERIVED' in node.evidence_kinds]
    assert {node.owner_id for node in strong} == {'service:alpha', 'service:beta'}
    beta_strong = [node for node in strong if node.owner_id == 'service:beta']
    assert {node.attributes['normalized_route'] for node in beta_strong} >= {'/', '/alias-one', '/alias-two', '/multi'}
    assert {node.attributes['http_method'] for node in beta_strong if node.attributes['normalized_route'] == '/multi'} == {'GET', 'POST'}
    same_line = [node for node in beta_strong if node.attributes['normalized_route'] == '/same']
    assert len(same_line) == 3 and len({node.id for node in same_line}) == 3
    assert len({node.attributes['logical_id'] for node in same_line}) == 1
    assert len({tuple(node.attributes['handler_ids']) for node in same_line}) == 3
    assert len({node.attributes['registration_variant'] for node in same_line}) == 3
    assert all(node.resolution_status == 'RESOLVED' for node in same_line)
    assert {node.attributes['normalized_route'] for node in beta_strong} >= {'/local/direct', '/no-prefix', '/A/branch', '/B/branch'}
    inherited = [node for node in beta_strong if node.attributes['method_route'] in {'/inherited', '/composed'}]
    assert len(inherited) == 2 and all(node.attributes['normalized_route'] is None
        and 'SPRING_CLASS_PREFIX_UNKNOWN' in node.attributes['unresolved_reasons'] for node in inherited)
    truncated = [node for node in beta_strong if node.attributes['source_path'].endswith('/Truncated.java')]
    assert len(truncated) == 64 and all(node.resolution_status == 'UNRESOLVED'
        and 'HTTP_ROUTE_VARIANTS_TRUNCATED' in node.attributes['unresolved_reasons'] for node in truncated)
    upper = next(node for node in strong if node.attributes['normalized_route'] == '/Api/Orders')
    assert upper.resolution_status == 'RESOLVED'
    assert upper.freshness == 'CURRENT'
    assert upper.attributes['class_prefix'] == '/Api'
    assert upper.attributes['method_route'] == '/Orders'
    assert len(upper.attributes['handler_ids']) == 1
    assert upper.attributes['deployment_status'] == 'UNKNOWN'
    assert all('RUNTIME_OBSERVED' not in node.evidence_kinds for node in strong)
    dynamic = [node for node in strong if node.attributes['normalized_route'] is None]
    assert dynamic and all(node.resolution_status == 'UNRESOLVED' for node in dynamic)

    # Public partial-compiler-graph boundary, built from the actual compiler graph.
    # A missing hierarchy is not proof that this class has no route prefix.
    owner = next(item['owner'] for item in graph.symbols
                 if item['id'] == upper.attributes['handler_ids'][0])
    original = deepcopy(graph.to_dict())
    for hierarchy in ['missing', None, {}, [42], ['external.BaseController']]:
        partial = deepcopy(graph)
        for item in partial.symbols:
            if item.get('kind') == 'class' and item.get('owner') == owner:
                item['annotations'] = []
                if hierarchy == 'missing':
                    item.pop('supertypes', None)
                else:
                    item['supertypes'] = hierarchy
        before = deepcopy(partial.to_dict())
        with patch('subprocess.Popen', side_effect=AssertionError('partial graph process')),\
             patch('socket.socket', side_effect=AssertionError('partial graph network')):
            unknown = projection(workspace, partial, source_coverage=coverage)
        candidates = [node for node in interface_nodes(unknown)
                      if node.attributes['handler_ids'] == upper.attributes['handler_ids']]
        assert candidates
        assert all(node.attributes['normalized_route'] is None and node.resolution_status == 'UNRESOLVED'
                   and 'SPRING_CLASS_PREFIX_UNKNOWN' in node.attributes['unresolved_reasons']
                   for node in candidates), hierarchy
        assert partial.to_dict() == before
    complete = deepcopy(graph)
    for item in complete.symbols:
        if item.get('kind') == 'class' and item.get('owner') == owner:
            item['annotations'] = []
            item['supertypes'] = ['java.lang.Object']
    root_document = projection(workspace, complete, source_coverage=coverage)
    root_candidates = [node for node in interface_nodes(root_document)
                       if node.attributes['handler_ids'] == upper.attributes['handler_ids']]
    assert root_candidates and all(node.attributes['normalized_route'] == '/Orders'
                                   and node.resolution_status == 'RESOLVED' for node in root_candidates)
    assert graph.to_dict() == original

    # Audit all declaration binding keys together; these are model corruptions of
    # genuine compiler output, not new runtime evidence or executed applications.
    from kgmaker.interfaces import InterfaceProjectionError
    handler_id = upper.attributes['handler_ids'][0]
    handler_symbol = next(item for item in graph.symbols if item['id'] == handler_id)
    class_ids = {item['id'] for item in graph.symbols if item.get('kind') == 'class'
                 and item.get('owner') == owner and item.get('path') == handler_symbol['path']
                 and item.get('context_id') == handler_symbol['context_id']}
    assert len(class_ids) == 1
    failures = []
    owner_cases = [('missing', None), ('null', None), ('empty', ''), ('whitespace', ' '),
                   ('leading-space', ' ' + owner), ('list', []), ('object', {}), ('number', 42)]
    for location in ['both', 'method', 'class']:
        for label, value in owner_cases:
            partial = deepcopy(graph)
            for item in partial.symbols:
                if (location in {'both', 'method'} and item['id'] == handler_id
                        or location in {'both', 'class'} and item['id'] in class_ids):
                    if label == 'missing':
                        item.pop('owner', None)
                    else:
                        item['owner'] = value
            before = deepcopy(partial.to_dict())
            with patch('subprocess.Popen', side_effect=AssertionError('owner probe process')),\
                 patch('socket.socket', side_effect=AssertionError('owner probe network')):
                view = projection(workspace, partial, source_coverage=coverage)
            candidates = [node for node in interface_nodes(view) if node.attributes['handler_ids'] == [handler_id]]
            if not candidates or any(node.attributes['normalized_route'] is not None
                                     or node.resolution_status != 'UNRESOLVED' for node in candidates):
                failures.append(location + '-owner-' + label)
            assert partial.to_dict() == before
    alternate_path = next(path for path in graph.files if path.endswith('/Dynamic.java'))
    other_context = next(context['id'] for context in graph.contexts if context.get('repo_id') == 'beta'
                         and context.get('module') == 'http-app')
    for field, value in [('path', alternate_path), ('path', None), ('path', []),
                         ('context_id', other_context), ('repo_id', 'beta'), ('module', 'foreign-module')]:
        partial = deepcopy(graph)
        next(item for item in partial.symbols if item['id'] == handler_id)[field] = value
        before = deepcopy(partial.to_dict())
        try:
            with patch('subprocess.Popen', side_effect=AssertionError('binding probe process')),\
                 patch('socket.socket', side_effect=AssertionError('binding probe network')):
                projection(workspace, partial, source_coverage=coverage)
        except InterfaceProjectionError:
            pass
        else:
            failures.append('method-binding-' + field + '-' + str(value))
        assert partial.to_dict() == before
    for field, value in [('path', alternate_path), ('context_id', other_context),
                         ('repo_id', 'beta'), ('module', 'foreign-module')]:
        partial = deepcopy(graph)
        next(item for item in partial.symbols if item['id'] in class_ids)[field] = value
        before = deepcopy(partial.to_dict())
        view = projection(workspace, partial, source_coverage=coverage)
        candidates = [node for node in interface_nodes(view) if node.attributes['handler_ids'] == [handler_id]]
        if not candidates or any(node.attributes['normalized_route'] is not None for node in candidates):
            failures.append('class-binding-' + field + '-' + str(value))
        assert partial.to_dict() == before
    for checksum in [None, '0' * 64]:
        partial = deepcopy(graph)
        context = next(item for item in partial.contexts if item['id'] == handler_symbol['context_id'])
        if checksum is None:
            context['source_files'].pop(handler_symbol['path'])
        else:
            context['source_files'][handler_symbol['path']] = checksum
        before = deepcopy(partial.to_dict())
        with pytest.raises(InterfaceProjectionError) as error:
            projection(workspace, partial, source_coverage=coverage,
                       selected_contexts={('alpha', 'alpha', 'http-app'): handler_symbol['context_id']})
        assert error.value.diagnostic['code'] == 'HTTP_SOURCE_HASH_MISMATCH'
        assert partial.to_dict() == before
    assert graph.to_dict() == original

    from dataclasses import replace
    edge_index = next(i for i, edge in enumerate(graph.edges)
                      if edge.kind == 'exposes_endpoint' and edge.source == handler_id)
    observed_edge = graph.edges[edge_index]
    endpoint_id = observed_edge.target
    mutations = []
    for key in ['sha256', 'scope']:
        for location in ['method', 'class']:
            for value in [None, []] + (['0' * 64] if key == 'sha256' else ['test']):
                partial = deepcopy(graph)
                identity = handler_id if location == 'method' else next(iter(class_ids))
                next(item for item in partial.symbols if item['id'] == identity)[key] = value
                mutations.append((location + '-' + key + '-' + str(value), partial))
    for key, value in [('path', alternate_path), ('scope', 'test'), ('line', 99999)]:
        partial = deepcopy(graph)
        index = next(i for i, node in enumerate(partial.nodes) if node.id == endpoint_id)
        partial.nodes[index] = replace(partial.nodes[index], **{key: value})
        mutations.append(('endpoint-' + key, partial))
    for key, value in [('scope', 'test'), ('line', 99999)]:
        partial = deepcopy(graph)
        index = next(i for i, node in enumerate(partial.nodes) if node.id in class_ids)
        partial.nodes[index] = replace(partial.nodes[index], **{key: value})
        mutations.append(('class-node-' + key, partial))
    for key, value in [('source_file', alternate_path), ('source_file', None),
                       ('source_line', 99999), ('source_line', None)]:
        partial = deepcopy(graph)
        partial.edges[edge_index] = replace(partial.edges[edge_index], **{key: value})
        mutations.append(('edge-' + key + '-' + str(value), partial))
    for key, value in [('source', endpoint_id), ('target', handler_id), ('relation', 'unrelated'),
                       ('source_file', alternate_path), ('source_line', 99999), ('context_ids', [other_context]),
                       ('sha256', '0' * 64), ('framework_rules', {'spring': 'foreign-rules'})]:
        partial = deepcopy(graph)
        proof = next(item for item in partial.evidence if item['id'] == observed_edge.evidence_ids[0])
        proof[key] = value
        mutations.append(('proof-' + key, partial))
    for hierarchy in [None, {}, {'schema_version': 1, 'complete': False, 'types': ['java.lang.Object']},
                      {'schema_version': 1, 'complete': True, 'types': [[]]},
                      {'schema_version': 2, 'complete': True, 'types': ['java.lang.Object']},
                      {'schema_version': 1, 'complete': True, 'types': []},
                      {'schema_version': 1, 'complete': True, 'types': ['external.Parent']}]:
        partial = deepcopy(graph)
        item = next(item for item in partial.symbols if item['id'] in class_ids)
        item['annotations'] = []
        item['supertypes'] = ['java.lang.Object']
        item['type_hierarchy'] = hierarchy
        mutations.append(('incomplete-type-hierarchy-' + str(hierarchy), partial))
    for key, value in [('http_method', 'GET'), ('endpoint_path', '/different')]:
        partial = deepcopy(graph)
        index = next(i for i, node in enumerate(partial.nodes) if node.id == endpoint_id)
        partial.nodes[index] = replace(partial.nodes[index], metadata={**partial.nodes[index].metadata, key: value})
        mutations.append(('endpoint-metadata-' + key, partial))
    for location in ['method', 'class']:
        for key, value in [('name', 'unrelated'), ('signature', '(I)I')]:
            partial = deepcopy(graph)
            identity = handler_id if location == 'method' else next(iter(class_ids))
            index = next(i for i, node in enumerate(partial.nodes) if node.id == identity)
            partial.nodes[index] = replace(partial.nodes[index], **{key: value})
            mutations.append((location + '-node-' + key, partial))
    for label, partial in mutations:
        before = deepcopy(partial.to_dict())
        try:
            with patch('subprocess.Popen', side_effect=AssertionError('proof probe process')),\
                 patch('socket.socket', side_effect=AssertionError('proof probe network')):
                view = projection(workspace, partial, source_coverage=coverage)
        except InterfaceProjectionError:
            pass
        else:
            candidates = [node for node in interface_nodes(view) if node.attributes['handler_ids'] == [handler_id]]
            if any(node.attributes['normalized_route'] is not None for node in candidates):
                failures.append(label)
        assert partial.to_dict() == before
    assert not failures, failures

    # An old, nonselected compiler capture is valid historical input, not a
    # reason to validate its source bytes as though it were the chosen capture.
    from kgmaker.workspace import qualified
    current_context = next(item for item in graph.contexts if item['id'] == handler_symbol['context_id'])
    for stale in [True, False]:
        sibling = deepcopy(graph)
        old_context = deepcopy(current_context)
        old_context['id'] = qualified('alpha', 'historical-http-context')
        old_context['build_profiles'] = ['historical-profile']
        old_context['freshness'] = 'STALE' if stale else current_context['freshness']
        if stale:
            old_context['source_files'][handler_symbol['path']] = '0' * 64
        sibling.contexts.append(old_context)
        old_handler = qualified('alpha', 'historical-http-handler')
        old_endpoint = qualified('alpha', 'historical-http-endpoint')
        old_proof = qualified('alpha', 'historical-http-proof')
        by_id = {node.id: node for node in graph.nodes}
        sibling.nodes.extend([replace(by_id[handler_id], id=old_handler),
                              replace(by_id[endpoint_id], id=old_endpoint)])
        old_symbol = deepcopy(handler_symbol)
        old_symbol.update(id=old_handler, context_id=old_context['id'],
                          sha256=old_context['source_files'][handler_symbol['path']])
        sibling.symbols.append(old_symbol)
        proof = deepcopy(next(item for item in graph.evidence if item['id'] == observed_edge.evidence_ids[0]))
        proof.update(id=old_proof, source=old_handler, target=old_endpoint, context_ids=[old_context['id']])
        sibling.evidence.append(proof)
        sibling.edges.append(replace(observed_edge, source=old_handler, target=old_endpoint,
                                     context_ids=(old_context['id'],), evidence_ids=(old_proof,)))
        before = deepcopy(sibling.to_dict())
        with patch('subprocess.Popen', side_effect=AssertionError('selection probe process')),\
             patch('socket.socket', side_effect=AssertionError('selection probe network')):
            selected = projection(workspace, sibling, source_coverage=coverage,
                       selected_contexts={('alpha', 'alpha', 'http-app'): current_context['id']})
            ambiguous = projection(workspace, sibling, source_coverage=coverage)
        chosen = [node for node in interface_nodes(selected) if node.attributes['handler_ids'] == [handler_id]]
        assert chosen and chosen[0].id == upper.id and chosen[0].resolution_status == 'RESOLVED'
        assert all(old_context['id'] not in node.attributes['context_ids'] for node in interface_nodes(selected))
        assert any(item.get('code') == 'HTTP_CONTEXT_NOT_SELECTED' and item.get('context_id') == old_context['id']
                   and item.get('original_evidence_ids') == [old_proof] for item in selected.diagnostics)
        assert any(item.get('code') == 'AMBIGUOUS_CONTEXT' for item in ambiguous.diagnostics)
        assert not any(node.owner_id == 'service:alpha' and 'FRAMEWORK_DERIVED' in node.evidence_kinds
                       for node in interface_nodes(ambiguous))
        assert sibling.to_dict() == before

    for descriptor in [None, '', [], 42, 'not-a-descriptor', '([V)V', '(Lbroken)V']:
        partial = deepcopy(graph)
        item = next(item for item in partial.symbols if item['id'] == handler_id)
        item['descriptor'] = descriptor
        item['type'] = None
        index = next(i for i, node in enumerate(partial.nodes) if node.id == handler_id)
        partial.nodes[index] = replace(partial.nodes[index], signature=descriptor)
        before = deepcopy(partial.to_dict())
        document = projection(workspace, partial, source_coverage=coverage)
        assert not any(node.attributes['handler_ids'] == [handler_id] for node in interface_nodes(document))
        assert any(item.get('code') == 'HTTP_HANDLER_SIGNATURE_UNKNOWN' and item.get('source_id') == handler_id
                   for item in document.diagnostics)
        assert partial.to_dict() == before

    # Actual reinspection changes the context/handler snapshot IDs but not these
    # declarations. Logical/variant identity must survive unrelated source input.
    before_interfaces = {(node.owner_id, node.attributes['http_method'], node.attributes['method_route'],
                          node.attributes['class_prefix'], node.attributes['registration_variant']):
                         (node.id, node.attributes['logical_id']) for node in strong}
    old_handlers = {identity for node in strong for identity in node.attributes['handler_ids']}
    for repo in ['alpha', 'beta']:
        source = tmp_path / repo / 'src/main/java/Unrelated.java'
        source.write_text('class Unrelated { }\n')
        local = tmp_path / repo
        sources = sorted(path.relative_to(local).as_posix() for path in local.rglob('*.java'))
        inspect_jvm(local, home=HOME, classpath=classpath, repo_id=repo, module='http-app', sources=sources)
    _, next_coverage, _, next_graph, _ = snapshot_workspace(Path(workspace['_manifest_path']))
    next_document = projection(workspace, next_graph, source_coverage=next_coverage)
    next_strong = [node for node in interface_nodes(next_document) if 'FRAMEWORK_DERIVED' in node.evidence_kinds]
    after_interfaces = {(node.owner_id, node.attributes['http_method'], node.attributes['method_route'],
                         node.attributes['class_prefix'], node.attributes['registration_variant']):
                        (node.id, node.attributes['logical_id']) for node in next_strong}
    assert before_interfaces == after_interfaces
    assert old_handlers.isdisjoint({identity for node in next_strong for identity in node.attributes['handler_ids']})
    assert document.baseline_fingerprint != next_document.baseline_fingerprint

    # Same-file nonsemantic line movement must be provenance-only for canonical
    # compiler declarations, including unresolved/dynamic/truncated operations.
    before_lines = {(node.owner_id, node.attributes['http_method'], node.attributes['method_route'],
                     node.attributes['class_prefix'], node.attributes['registration_variant']):
                    (node.id, node.attributes['logical_id']) for node in next_strong}
    for repo in ['alpha', 'beta']:
        local = tmp_path / repo
        for source in local.rglob('*.java'):
            if source.name != 'Unrelated.java':
                source.write_text('// unrelated comment before declarations\n\n' + source.read_text())
        sources = sorted(path.relative_to(local).as_posix() for path in local.rglob('*.java'))
        inspect_jvm(local, home=HOME, classpath=classpath, repo_id=repo, module='http-app', sources=sources)
    _, shifted_coverage, _, shifted_graph, _ = snapshot_workspace(Path(workspace['_manifest_path']))
    shifted = projection(workspace, shifted_graph, source_coverage=shifted_coverage)
    shifted_strong = [node for node in interface_nodes(shifted) if 'FRAMEWORK_DERIVED' in node.evidence_kinds]
    after_lines = {(node.owner_id, node.attributes['http_method'], node.attributes['method_route'],
                    node.attributes['class_prefix'], node.attributes['registration_variant']):
                   (node.id, node.attributes['logical_id']) for node in shifted_strong}
    assert before_lines == after_lines
    shifted_proofs = {item['id']: item for item in shifted.provenance}
    old_proofs = {item['id']: item for item in next_document.provenance}
    for old in next_strong:
        current = next(node for node in shifted_strong if node.id == old.id)
        assert shifted_proofs[current.evidence_refs[0]]['source_line'] == old_proofs[old.evidence_refs[0]]['source_line'] + 2

    # The same canonical declaration can move within its explicitly owned module;
    # source path, like line/hash/context, is then fresh provenance rather than ID.
    source = beta / 'Beta.java'
    moved = beta / 'moved/Beta.java'
    moved.parent.mkdir()
    source.rename(moved)
    local = tmp_path / 'beta'
    sources = sorted(path.relative_to(local).as_posix() for path in local.rglob('*.java'))
    inspect_jvm(local, home=HOME, classpath=classpath, repo_id='beta', module='http-app', sources=sources)
    _, moved_coverage, _, moved_graph, _ = snapshot_workspace(Path(workspace['_manifest_path']))
    relocated = projection(workspace, moved_graph, source_coverage=moved_coverage)
    moved_strong = [node for node in interface_nodes(relocated) if 'FRAMEWORK_DERIVED' in node.evidence_kinds]
    assert {node.id for node in moved_strong} == {node.id for node in shifted_strong}
    assert all(node.attributes['source_path'].endswith('/moved/Beta.java') for node in moved_strong
               if node.owner_id == 'service:beta' and node.attributes['normalized_route'] == '/same')
