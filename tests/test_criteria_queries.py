"""T003-S06-W07 acceptance through real Javac and explicit QueryDSL APT."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from kgmaker.inspection import inspect_jvm
from kgmaker.model import KnowledgeGraph

REPO = Path(__file__).resolve().parents[1]
ARTIFACTS = [
    'jakarta/persistence/jakarta.persistence-api/3.1.0/jakarta.persistence-api-3.1.0.jar',
    'jakarta/annotation/jakarta.annotation-api/2.1.1/jakarta.annotation-api-2.1.1.jar',
    'org/springframework/data/spring-data-jpa/3.4.2/spring-data-jpa-3.4.2.jar',
    'org/springframework/data/spring-data-commons/3.4.2/spring-data-commons-3.4.2.jar',
    'org/springframework/spring-core/6.2.2/spring-core-6.2.2.jar',
    'com/querydsl/querydsl-core/5.1.0/querydsl-core-5.1.0.jar',
    'com/querydsl/querydsl-jpa/5.1.0/querydsl-jpa-5.1.0-jakarta.jar',
    'com/querydsl/querydsl-apt/5.1.0/querydsl-apt-5.1.0.jar',
    'com/querydsl/querydsl-codegen/5.1.0/querydsl-codegen-5.1.0.jar',
    'com/querydsl/codegen-utils/5.1.0/codegen-utils-5.1.0.jar',
    'com/mysema/commons/mysema-commons-lang/0.2.4/mysema-commons-lang-0.2.4.jar',
    'javax/inject/javax.inject/1/javax.inject-1.jar',
    'org/eclipse/jdt/ecj/3.26.0/ecj-3.26.0.jar',
]


def dependencies():
    repo = Path(os.environ.get('KGMAKER_TEST_MAVEN_REPOSITORY', Path.home() / '.m2/repository'))
    paths = [repo / relative for relative in ARTIFACTS]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        if os.environ.get('KGMAKER_REQUIRE_WORKERS') == '1':
            pytest.fail('Explicit fixture dependencies unavailable: ' + ', '.join(missing))
        pytest.skip('Explicit fixture dependencies unavailable: ' + ', '.join(missing))
    return paths


def project(root):
    paths = dependencies()
    shutil.copytree(REPO / 'fixtures/criteria-queries/src', root / 'src')
    generate(root, paths)
    return paths


def generate(root, paths):
    generated = root / 'src/generated/java'
    generated.mkdir(parents=True, exist_ok=True)
    classes = root / 'build/classes'
    classes.mkdir(parents=True, exist_ok=True)
    javac = Path(os.environ.get('JAVA_HOME', '/usr/lib/jvm/java-21-openjdk-amd64')) / 'bin/javac'
    if not javac.is_file():
        pytest.skip('Explicit Javac toolchain unavailable')
    # Deliberate fixture setup. inspect/scan always use -proc:none and never run APT.
    command = [str(javac), '--release', '21', '-proc:only', '-processor',
               'com.querydsl.apt.QuerydslAnnotationProcessor', '-classpath', os.pathsep.join(map(str, paths)),
               '-s', str(generated), '-d', str(classes), str(root / 'src/main/java/demo/Order.java')]
    result = subprocess.run(command, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert (generated / 'demo/QOrder.java').is_file()


def inspect(root, paths, **kwargs):
    return inspect_jvm(root, classpath=list(map(str, paths)), **kwargs)


@pytest.fixture(scope='module')
def actual(tmp_path_factory):
    root = tmp_path_factory.mktemp('criteria-actual')
    paths = project(root)
    import kgmaker.inspection as inspection
    captured = []
    original = inspection.request_worker
    def capture(*args, **kwargs):
        value = original(*args, **kwargs)
        captured.append(value)
        return value
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(inspection, 'request_worker', capture)
        result = inspect(root, paths, publish=False)
    graph = KnowledgeGraph.from_dict(result['graph'])
    return root, paths, graph, captured[-1], result["context"]


def programmatic(graph):
    return [node for node in graph.nodes if node.kind == 'orm_query'
            and node.metadata.get('query_language') in {'CRITERIA', 'SPECIFICATION', 'QUERYDSL'}]


def test_actual_criteria_specification_querydsl_and_fragment(actual):
    root, paths, graph, _, _ = actual
    queries = programmatic(graph)
    assert {q.metadata['query_language'] for q in queries} == {'CRITERIA', 'SPECIFICATION', 'QUERYDSL'}
    nodes = {node.id: node for node in graph.nodes}
    symbols = {item['id']: item for item in graph.symbols}
    by_method = {symbols[q.metadata['method']]['name']: q for q in queries
                 if symbols[q.metadata['method']]['name'] != '<lambda>'}
    for method in ('criteria', 'querydsl', 'querydslNumber', 'matching', 'toPredicate'):
        query = by_method[method]
        assert query.metadata['analysis_status'] == 'COMPLETE', (method, query.metadata)
        assert query.metadata['query'] is None
        assert query.metadata['execution'] == 'NOT_OBSERVED'
        attributes = [nodes[e.target] for e in graph.edges
                      if e.source == query.id and e.kind == 'filters_by']
        assert any(a.name.endswith('.id' if method == 'querydslNumber' else '.status') for a in attributes)
        assert all(e.evidence_ids and e.evidence_kind == 'FRAMEWORK_DERIVED' for e in graph.edges
                   if e.source == query.id)
    assert by_method['matching'].metadata['repository_fragment']['status'] == 'UNIQUE_DECLARATION'
    for method in ('dynamicAttribute', 'dynamicRoot', 'dynamicPredicate', 'dynamicQuerydsl', 'dynamicQuerydslPath'):
        query = by_method[method]
        assert query.metadata['analysis_status'] in {'UNKNOWN', 'PARTIAL'}, (method, query.metadata)
        assert query.metadata['query'] is None
        assert query.metadata['validated'] is False
        assert query.metadata['gaps']
    lambdas = [q for q in queries if symbols[q.metadata['method']]['name'] == '<lambda>']
    assert len(lambdas) == 2
    assert sorted(q.metadata['analysis_status'] for q in lambdas) == ['COMPLETE', 'PARTIAL']


@pytest.mark.parametrize('mutation', ['missing_version', 'unknown_version', 'bool_version', 'foreign_parameter',
                                      'class_type', 'source_hash', 'foreign_call', 'bad_receiver', 'querydsl_factory',
                                      'binding_reference', 'malformed_status'])
def test_invalid_actual_query_ir_is_rejected_without_store_mutation(actual, tmp_path, monkeypatch, mutation):
    from copy import deepcopy
    from kgmaker.inspection import validate_response
    from kgmaker.criteria_queries import _walk
    from kgmaker.worker_protocol import WorkerError
    _, _, graph, raw, context = actual
    response = deepcopy(raw)
    body = next(b for b in response['bodies'] if '.criteria(' in b['method'])
    call = next(n for n in _walk(body['body']) if n.get('kind') == 'call' and n.get('query_type'))
    if mutation == 'missing_version': body.pop('query_ir_version')
    elif mutation == 'unknown_version': body['query_ir_version'] = 99
    elif mutation == 'bool_version': body['query_ir_version'] = True
    elif mutation == 'foreign_parameter': body['query_parameters'][0]['binding']['id'] = 'foreign-binding'
    elif mutation == 'class_type':
        n = next(n for n in _walk(body['body']) if 'class_literal' in n)
        n['class_literal']['owner'] = 'other.Order'
    elif mutation == 'source_hash': call['sha256'] = '0' * 64
    elif mutation == 'binding_reference':
        next(n for n in _walk(body['body']) if n.get('binding_ref', {}).get('kind') == 'LOCAL_VARIABLE')['binding_ref']['id'] = 'wrong-binding'
    elif mutation == 'malformed_status': body['query_ir_status'] = []
    elif mutation == 'foreign_call': call['call_site'] = next(s['id'] for s in response['call_sites'] if s['caller'] != body['method'])
    elif mutation == 'bad_receiver': call['receiver']['field_receiver'] = 5
    else:
        next(s for s in response['symbols'] if s.get('querydsl_path'))['querydsl_path']['factory'] = 'invented'
    before = deepcopy(graph.to_dict())
    with pytest.raises(WorkerError) as rejected:
        validate_response(response, context)
    assert rejected.value.status == 'INVALID_PROTOCOL'
    assert graph.to_dict() == before


@pytest.mark.parametrize('mutation', ['stale', 'foreign_context', 'candidate_tamper', 'target_source', 'missing_call'])
def test_replay_rejects_invalid_programmatic_provenance(actual, mutation):
    from copy import deepcopy
    from kgmaker.framework import augment_framework_graph
    root, _, original, _, original_context = actual
    graph = KnowledgeGraph.from_dict(original.to_dict())
    context = deepcopy(original_context)
    symbols = {s['id']: s for s in graph.symbols}
    method = next(s for s in graph.symbols if s.get('name') == 'criteria' and s.get('programmatic_queries'))
    if mutation == 'stale': context['freshness'] = 'STALE'
    elif mutation == 'foreign_context': method['programmatic_queries'][0]['context_id'] = 'foreign'
    elif mutation == 'candidate_tamper': method['programmatic_queries'][0]['entity'] = 'other.Order'
    else:
        witness = next(w for w in method['programmatic_queries'][0]['witnesses'] if w.get('call_site'))
        if mutation == 'target_source': symbols[witness['compiler_target']]['origin'] = 'handwritten'
        else: graph.call_sites[:] = [s for s in graph.call_sites if s['id'] != witness['call_site']]
    projected = augment_framework_graph(root, graph, context)
    assert not [q for q in programmatic(projected) if q.metadata['method'] == method['id']]
    assert any(d['code'] == 'ORM_PROGRAMMATIC_PROVENANCE_INVALID' for d in projected.diagnostics)


@pytest.mark.parametrize('version', [1, 2, 3])
def test_old_graph_and_worker_protocol_remain_readable(actual, version):
    from copy import deepcopy
    from kgmaker.inspection import validate_response
    from kgmaker.criteria_queries import _walk
    _, _, graph, raw, context = actual
    old = graph.to_dict()
    old['version'] = version
    assert KnowledgeGraph.from_dict(old).nodes
    response = deepcopy(raw)
    for body in response['bodies']:
        body.pop('query_ir_version', None)
        body.pop('query_ir_status', None)
        body.pop('query_parameters', None)
        for node in list(_walk(body['body'])):
            for key in ('query_type', 'class_literal', 'query_lambda', 'field_receiver'):
                node.pop(key, None)
    for symbol in response['symbols']:
        for key in ('querydsl_path', 'query_type_contracts', 'query_callable_type', 'query_callable_symbol'):
            symbol.pop(key, None)
    validate_response(response, context)


def test_actual_ambiguous_fragment_keeps_local_intent_but_no_repository_binding(tmp_path):
    paths = project(tmp_path)
    (tmp_path / 'src/main/java/demo/OtherFragment.java').write_text('''package demo;
final class OtherFragment implements OrderFragment {
    public java.util.List<Order> matching(String status) { return java.util.List.of(); }
}''')
    graph = KnowledgeGraph.from_dict(inspect(tmp_path, paths, publish=False)['graph'])
    fragment = next(q for q in programmatic(graph) if q.name == 'matching:CRITERIA')
    assert fragment.metadata['repository_fragment']['status'] == 'UNKNOWN'
    assert 'REPOSITORY_FRAGMENT_AMBIGUOUS' in fragment.metadata['gaps']
    assert not any(e.target == fragment.id and e.kind == 'repository_uses_fragment' for e in graph.edges)
    assert any(e.source == fragment.id and e.kind == 'query_reads' for e in graph.edges)


def test_actual_same_named_application_api_and_dynamic_control_flow(tmp_path):
    paths = project(tmp_path)
    (tmp_path / 'src/main/java/demo/Fake.java').write_text('''package demo;
final class Fake {
    static final class CriteriaBuilder { CriteriaQuery createQuery(Class<?> type) { return new CriteriaQuery(); } }
    static final class CriteriaQuery { Object from(Class<?> type) { return new Object(); } }
    Object fake(CriteriaBuilder cb) { CriteriaQuery query = cb.createQuery(Order.class); return query.from(Order.class); }
    java.util.List<Order> conditional(jakarta.persistence.EntityManager em, boolean flag) {
        var cb = em.getCriteriaBuilder();
        var q = cb.createQuery(Order.class); var root = q.from(Order.class);
        if (flag) q.where(cb.equal(root.get("status"), "OPEN"));
        return em.createQuery(q).getResultList();
    }
}''')
    graph = KnowledgeGraph.from_dict(inspect(tmp_path, paths, publish=False)['graph'])
    assert not any(q.name == 'fake:CRITERIA' for q in programmatic(graph))
    conditional = next(q for q in programmatic(graph) if q.name == 'conditional:CRITERIA')
    assert conditional.metadata['analysis_status'] == 'UNKNOWN'
    assert 'DYNAMIC_CONTROL_FLOW' in conditional.metadata['gaps']
    assert not any(e.source == conditional.id for e in graph.edges)


def test_actual_offline_scan_hook_and_errors_preserve_last_valid_generation(tmp_path, monkeypatch):
    from kgmaker.cli import scan, hook_context
    from kgmaker.store import load_graph
    from kgmaker.worker_protocol import WorkerError
    paths = project(tmp_path)
    inspect(tmp_path, paths)
    before = load_graph(tmp_path)
    bindings = {e for e in before.edges if e.kind in {'query_reads', 'filters_by', 'repository_uses_fragment'}}
    assert bindings
    with monkeypatch.context() as offline:
        offline.setattr(subprocess, 'Popen', lambda *a, **kw: (_ for _ in ()).throw(AssertionError('implicit process')))
        assert scan(tmp_path, generate_docs=False) == 0
        assert hook_context(tmp_path) == 0
    assert {e for e in load_graph(tmp_path).edges if e.kind in {'query_reads', 'filters_by', 'repository_uses_fragment'}} == bindings
    store = tmp_path / '.kgmaker/graph.json'
    snapshot = store.read_bytes()
    assert inspect(tmp_path, paths, strict=True)['exit_code'] == 4
    assert store.read_bytes() == snapshot
    cancel = tmp_path / 'cancel'
    cancel.touch()
    for kwargs, status in [({'cancel_file': cancel}, 'CANCELLED'), ({'timeout': 0.000001}, 'TIMED_OUT')]:
        with pytest.raises(WorkerError) as rejected:
            inspect(tmp_path, paths, **kwargs)
        assert rejected.value.status == status
        assert store.read_bytes() == snapshot


def test_actual_final_xml_mapping_and_selected_persistence_unit(tmp_path):
    paths = project(tmp_path)
    metadata = tmp_path / 'META-INF'
    metadata.mkdir()
    (metadata / 'orders.xml').write_text('''<entity-mappings xmlns="https://jakarta.ee/xml/ns/persistence/orm" version="3.1">
      <entity class="demo.Order"><table name="xml_orders"/><attributes>
        <basic name="status"><column name="xml_status"/></basic></attributes></entity>
    </entity-mappings>''')
    (metadata / 'persistence.xml').write_text('''<persistence xmlns="https://jakarta.ee/xml/ns/persistence" version="3.1">
      <persistence-unit name="orders"><mapping-file>META-INF/orders.xml</mapping-file><class>demo.Order</class><exclude-unlisted-classes>true</exclude-unlisted-classes></persistence-unit>
      <persistence-unit name="other"><exclude-unlisted-classes>true</exclude-unlisted-classes></persistence-unit>
    </persistence>''')
    result = inspect(tmp_path, paths, publish=False, build_context={'persistence_unit': 'orders', 'database_id': 'orders-db', 'schema_stream_id': 'orders-stream'})
    graph = KnowledgeGraph.from_dict(result['graph'])
    nodes = {n.id: n for n in graph.nodes}
    query = next(q for q in programmatic(graph) if q.name == 'criteria:CRITERIA')
    assert query.metadata['validated'], query.metadata['gaps']
    attributes = [nodes[e.target] for e in graph.edges if e.source == query.id and e.kind == 'filters_by']
    assert len(attributes) == 1
    assert attributes[0].metadata['mapping_source'] == 'ORM_XML'
    assert attributes[0].metadata['column_name'] == 'xml_status'
    read = next(e for e in graph.edges if e.source == query.id and e.kind == 'query_reads')
    proof = next(e for e in graph.evidence if e['id'] in read.evidence_ids)
    assert proof['persistence_selection']['persistence_unit'] == 'orders'
    assert proof['persistence_selection']['database_id'] == 'orders-db'
    other = KnowledgeGraph.from_dict(inspect(tmp_path, paths, publish=False, build_context={'persistence_unit': 'other'})['graph'])
    other_query = next(q for q in programmatic(other) if q.name == 'criteria:CRITERIA')
    assert other_query.metadata['analysis_status'] == 'UNKNOWN'
    assert not any(e.source == other_query.id for e in other.edges)


@pytest.mark.parametrize('conflicting_access', [False, True])
def test_actual_inherited_property_access_reuses_effective_attributes(tmp_path, conflicting_access):
    paths = project(tmp_path)
    source = tmp_path / 'src/main/java/demo/Order.java'
    source.write_text('''package demo;
import jakarta.persistence.*;
import com.querydsl.core.annotations.QueryEntity;
@MappedSuperclass class Base {
    private Long id;
    @Id @Column(name="order_id")
    public Long getId() { return id; }
}
@Entity @QueryEntity @Access(AccessType.PROPERTY) @Table(name="orders")
public class Order extends Base {
    private String status;
    @Column(name="property_status") public String getStatus() { return status; }
    public void setStatus(String value) { status=value; }
}''')
    if conflicting_access:
        source.write_text(source.read_text().replace('private Long id;\n    @Id @Column(name="order_id")\n    public Long getId() { return id; }', '@Id @Column(name="order_id") public Long id;'))
    generate(tmp_path, paths)
    graph = KnowledgeGraph.from_dict(inspect(tmp_path, paths, publish=False)['graph'])
    query = next(q for q in programmatic(graph) if q.name == 'criteria:CRITERIA')
    nodes = {n.id: n for n in graph.nodes}
    attributes = [nodes[e.target] for e in graph.edges if e.source == query.id and e.kind == 'filters_by']
    if conflicting_access:
        assert not query.metadata['validated']
        assert not attributes
        assert any(d['code'] == 'ORM_MAPPED_SUPERCLASS_ACCESS_AMBIGUOUS' for d in graph.diagnostics)
        return
    assert query.metadata['validated'], query.metadata['gaps']
    assert len(attributes) == 1 and attributes[0].metadata['access'] == 'PROPERTY'
    assert any(n.kind == 'orm_attribute' and n.metadata.get('effective_owner') == 'demo.Order'
               and n.metadata.get('declaring_owner') == 'demo.Base' for n in graph.nodes)


def test_actual_generated_q_field_factory_name_and_entity_identity_are_not_guessed(tmp_path):
    paths = project(tmp_path)
    qtype = tmp_path / 'src/generated/java/demo/QOrder.java'
    qtype.write_text(qtype.read_text().replace('createString("status")', 'createString("missing")'))
    other = tmp_path / 'src/main/java/other/Order.java'
    other.parent.mkdir()
    other.write_text('''package other; @jakarta.persistence.Entity
public class Order { @jakarta.persistence.Id public Long id; @jakarta.persistence.Column public String status; }''')
    graph = KnowledgeGraph.from_dict(inspect(tmp_path, paths, publish=False)['graph'])
    q = next(q for q in programmatic(graph) if q.name == 'querydsl:QUERYDSL')
    assert q.metadata['analysis_status'] == 'PARTIAL'
    assert 'ATTRIBUTE_UNRESOLVED:missing' in q.metadata['gaps']
    assert not any(e.source == q.id and e.kind == 'filters_by' for e in graph.edges)
    nodes = {n.id: n for n in graph.nodes}
    reads = [nodes[e.target] for e in graph.edges if e.source == q.id and e.kind == 'query_reads']
    assert len(reads) == 1 and reads[0].metadata['owner'] == 'demo.Order'


def test_actual_invalid_response_does_not_replace_store(tmp_path, monkeypatch):
    from copy import deepcopy
    import kgmaker.inspection as inspection
    from kgmaker.worker_protocol import WorkerError
    paths = project(tmp_path)
    inspect(tmp_path, paths)
    store = tmp_path / '.kgmaker/graph.json'
    before = store.read_bytes()
    original = inspection.request_worker
    def broken(*args, **kwargs):
        response = deepcopy(original(*args, **kwargs))
        next(b for b in response['bodies'] if '.criteria(' in b['method'])['query_ir_version'] = 99
        return response
    monkeypatch.setattr(inspection, 'request_worker', broken)
    with pytest.raises(WorkerError) as rejected:
        inspect(tmp_path, paths)
    assert rejected.value.status == 'INVALID_PROTOCOL'
    assert store.read_bytes() == before


def test_actual_unused_selector_and_projection_are_not_filter_evidence(tmp_path):
    paths = project(tmp_path)
    (tmp_path / 'src/main/java/demo/Unused.java').write_text('''package demo;
import jakarta.persistence.*;
import jakarta.persistence.criteria.*;
final class Unused {
    java.util.List<Order> unused(EntityManager em) {
        var cb=em.getCriteriaBuilder(); var q=cb.createQuery(Order.class); var r=q.from(Order.class);
        var ignored=r.get("status"); cb.equal(ignored,"OPEN");
        return em.createQuery(q.select(r)).getResultList();
    }
    java.util.List<String> projection(EntityManager em) {
        var cb=em.getCriteriaBuilder(); var q=cb.createQuery(String.class); var r=q.from(Order.class);
        q.select(r.get("status")); return em.createQuery(q).getResultList();
    }
}''')
    graph = KnowledgeGraph.from_dict(inspect(tmp_path, paths, publish=False)['graph'])
    unused = next(q for q in programmatic(graph) if q.name == 'unused:CRITERIA')
    projection = next(q for q in programmatic(graph) if q.name == 'projection:CRITERIA')
    for query in (unused, projection):
        assert not any(e.source == query.id and e.kind == 'filters_by' for e in graph.edges)
    assert unused.metadata['analysis_status'] == 'COMPLETE'
    assert projection.metadata['analysis_status'] == 'PARTIAL'
    assert 'PROJECTION_UNSUPPORTED' in projection.metadata['gaps']


def test_actual_source_shadow_of_official_api_cannot_authorize_query(tmp_path):
    paths = project(tmp_path)
    api = tmp_path / 'src/main/java/jakarta/persistence/criteria/CriteriaBuilder.java'
    api.parent.mkdir(parents=True)
    api.write_text('''package jakarta.persistence.criteria;
public interface CriteriaBuilder {
    <T> CriteriaQuery<T> createQuery(Class<T> type);
    Predicate equal(Expression<?> expression, Object value);
}''')
    graph = KnowledgeGraph.from_dict(inspect(tmp_path, paths, publish=False)['graph'])
    assert not any(q.name == 'criteria:CRITERIA' for q in programmatic(graph))
    assert any(s.get('owner') == 'jakarta.persistence.criteria.CriteriaBuilder'
               and s.get('name') == 'createQuery' and s.get('origin') == 'handwritten' for s in graph.symbols)


def test_actual_criteria_where_replaces_querydsl_where_accumulates_and_helpers_are_unknown(tmp_path):
    paths = project(tmp_path)
    (tmp_path / 'src/main/java/demo/Mutation.java').write_text('''package demo;
import jakarta.persistence.*;
import jakarta.persistence.criteria.*;
import com.querydsl.jpa.impl.JPAQueryFactory;
final class Mutation {
    java.util.List<Order> clear(EntityManager em) {
        var cb=em.getCriteriaBuilder(); var q=cb.createQuery(Order.class); var r=q.from(Order.class);
        q.where(cb.equal(r.get("status"), "OPEN")); q.where();
        return em.createQuery(q).getResultList();
    }
    java.util.List<Order> replace(EntityManager em) {
        var cb=em.getCriteriaBuilder(); var q=cb.createQuery(Order.class); var r=q.from(Order.class);
        q.where(cb.equal(r.get("status"), "OPEN")); q.where(cb.equal(r.get("id"), 1L));
        return em.createQuery(q).getResultList();
    }
    java.util.List<Order> aliasClear(EntityManager em) {
        var cb=em.getCriteriaBuilder(); var q=cb.createQuery(Order.class); var r=q.from(Order.class);
        q.where(cb.equal(r.get("status"), "OPEN")); var alias=q; alias.where();
        return em.createQuery(q).getResultList();
    }
    java.util.List<Order> captured(EntityManager em) {
        var cb=em.getCriteriaBuilder(); var q=cb.createQuery(Order.class); var r=q.from(Order.class);
        q.where(cb.equal(r.get("status"), "OPEN")); Runnable reset=()->q.where(); reset.run();
        return em.createQuery(q).getResultList();
    }
    java.util.List<Order> castEscape(EntityManager em) {
        var cb=em.getCriteriaBuilder(); var q=cb.createQuery(Order.class); var r=q.from(Order.class);
        q.where(cb.equal(r.get("status"), "OPEN")); Object alias=(Object)q; mutateObject(alias);
        return em.createQuery(q).getResultList();
    }
    java.util.List<Order> dependencyEscape(EntityManager em) {
        var cb=em.getCriteriaBuilder(); var q=cb.createQuery(Order.class); var r=q.from(Order.class);
        q.where(cb.equal(r.get("status"), "OPEN")); java.util.List.of(q).get(0).where();
        return em.createQuery(q).getResultList();
    }
    void mutateObject(Object value) { ((CriteriaQuery<?>)value).where(); }
    void mutate(CriteriaQuery<Order> q) { q.where(); }
    java.util.List<Order> helper(EntityManager em) {
        var cb=em.getCriteriaBuilder(); var q=cb.createQuery(Order.class); var r=q.from(Order.class);
        q.where(cb.equal(r.get("status"), "OPEN")); mutate(q);
        return em.createQuery(q).getResultList();
    }
    java.util.List<Order> accumulated(JPAQueryFactory f) {
        var o=QOrder.order; var q=f.selectFrom(o);
        q.where(o.status.eq("OPEN")); q.where(o.id.eq(1L)); return q.fetch();
    }
}''')
    graph = KnowledgeGraph.from_dict(inspect(tmp_path, paths, publish=False)['graph'])
    nodes = {n.id: n for n in graph.nodes}
    queries = {q.name.split(':')[0]: q for q in programmatic(graph)}
    def filters(name):
        return {nodes[e.target].metadata['attribute'] for e in graph.edges
                if e.source == queries[name].id and e.kind == 'filters_by'}
    assert filters('clear') == set()
    assert filters('aliasClear') == set()
    assert filters('replace') == {'id'}
    assert filters('accumulated') == {'status', 'id'}
    for method in ('helper', 'captured', 'castEscape', 'dependencyEscape'):
        assert filters(method) == set(), method
        assert queries[method].metadata['analysis_status'] == 'UNKNOWN', method


def test_actual_duplicate_entity_compiler_error_cannot_select_one_definition(tmp_path):
    paths = project(tmp_path)
    duplicate = tmp_path / 'src/main/java/collision/Order.java'
    duplicate.parent.mkdir()
    duplicate.write_text('''package demo;
@jakarta.persistence.Entity public class Order {
    @jakarta.persistence.Id public Long id;
    @jakarta.persistence.Column public String status;
}''')
    graph = KnowledgeGraph.from_dict(inspect(tmp_path, paths, publish=False)['graph'])
    assert any(d.get('code', '').startswith('JAVAC_') for d in graph.diagnostics)
    for query in programmatic(graph):
        assert query.metadata['analysis_status'] == 'UNKNOWN'
        assert 'COMPILER_BODY_UNAVAILABLE' in query.metadata['gaps']
        assert not any(e.source == query.id for e in graph.edges)
