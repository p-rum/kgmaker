"""Compiler captures and pure public-snapshot policy guards; never run Kafka."""
import copy
import hashlib
import json
import os
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
import xml.etree.ElementTree as ET

import pytest
from kgmaker.analysis_model import digest
from kgmaker.inspection import inspect_jvm
from kgmaker.model import KnowledgeGraph,Node,Edge
from kgmaker.kafka_retry import policy_boundaries,api_witness,analysis_stamp
from test_t024_discover_process_triggers import actual_prerequisites
from test_kafka_code_bindings import extra_api_jars

ROOT=Path(__file__).resolve().parents[1]
JAVA='''package demo;
import org.springframework.kafka.annotation.*;
public class RetryEntries {
 @KafkaListener(topics={"orders"},groupId="group-one")
 @RetryableTopic(attempts="3",retryTopicSuffix="-retry",dltTopicSuffix="-dead")
 public void consume(String value) {}
 @DltHandler public void dead(String value) {}
}'''
KOTLIN='''package demo
import org.springframework.kafka.annotation.*
class RetryEntries {
 @KafkaListener(topics=["orders"],groupId="group-one")
 @RetryableTopic(attempts="3",retryTopicSuffix="-retry",dltTopicSuffix="-dead")
 fun consume(value: String) {}
 @DltHandler fun dead(value: String) {}
}'''


def api_inputs():
    repository=Path(os.environ.get('KGMAKER_TEST_MAVEN_REPOSITORY',str(Path.home()/'.m2/repository')))
    lock=json.loads((ROOT/'fixtures/kafka-retry-dlt/dependencies.lock.json').read_text())
    result={}
    for item in lock['artifacts']:
        try:
            for key,checksum in [('path','sha256'),('artifact_pom','artifact_pom_sha256')]:
                p=repository/item[key]
                if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=item[checksum]:raise ValueError('Pinned retry API input unavailable: '+item[key])
            name=ET.parse(repository/item['artifact_pom']).getroot().findtext('{http://maven.apache.org/POM/4.0.0}licenses/{http://maven.apache.org/POM/4.0.0}license/{http://maven.apache.org/POM/4.0.0}name')
            if name!=item['license_name']:raise ValueError('Pinned retry API license changed')
        except (ValueError,OSError,ET.ParseError) as error:
            if os.environ.get('KGMAKER_REQUIRE_WORKERS')=='1' or os.environ.get('KGMAKER_REQUIRE_K2')=='1':pytest.fail(str(error))
            pytest.skip(str(error))
        result[item['version']]=repository/item['path']
    return result


def inspect_capture(root,language,scenario='supported'):
    jars=actual_prerequisites('k1')+extra_api_jars();apis=api_inputs()
    if scenario=='unsupported':jars=[str(apis['3.2.0']) if '/spring-kafka/3.3.2/' in jar else jar for jar in jars]
    folder=root/('src/main/java/demo' if language=='java' else 'src/main/kotlin/demo');folder.mkdir(parents=True)
    text=JAVA if language=='java' else KOTLIN
    if scenario=='custom':text=text.replace('groupId="group-one")','groupId="group-one",errorHandler="opaqueHandler")')
    if scenario=='source-shadow':
        fake=root/'src/main/java/org/springframework/kafka/annotation/RetryableTopic.java';fake.parent.mkdir(parents=True,exist_ok=True)
        fake.write_text('package org.springframework.kafka.annotation; public @interface RetryableTopic { String attempts(); String retryTopicSuffix(); String dltTopicSuffix(); }')
    if scenario=='ambiguous':
        text=text[:-1]+('@DltHandler public void another(String value) {}\n}' if language=='java' else '@DltHandler fun another(value: String) {}\n}')
    if scenario=='expressions':text=text.replace('attempts="3"','attempts="#{dynamicAttempts}"')
    if scenario=='supported':
        second=text.replace('RetryEntries','OtherRetryEntries').replace('group-one','group-two')
        second=second[second.index('public class' if language=='java' else 'class Retry' if 'class Retry' in second else 'class Other'):]
        if language=='java':second=second.replace('public class','class',1)
        text+='\n'+second
    (folder/('RetryEntries.java' if language=='java' else 'RetryEntries.kt')).write_text(text)
    result=inspect_jvm(root,home=ROOT/'workers',kotlin_backend='k1',repo_id='retry-fixture',classpath=jars,publish=False)
    assert not any('.err.' in str(d.get('code','')) or str(d.get('reason','')).startswith('ERROR:') for d in result['diagnostics'])
    out=os.environ.get('KGMAKER_RETRY_CAPTURE_DIR')
    if out:
        target=Path(out);target.mkdir(parents=True,exist_ok=True)
        (target/('capture-'+language+'-'+scenario+'.json')).write_text(json.dumps(result,indent=2))
    return KnowledgeGraph.from_dict(result['graph'])


@pytest.fixture(scope='module',params=['java','kotlin'])
def captured(tmp_path_factory,request):
    replay=os.environ.get('KGMAKER_RETRY_REPLAY_DIR')
    if replay:
        if os.environ.get('KGMAKER_REQUIRE_WORKERS')=='1':pytest.fail('Pure replay cannot replace a required actual compiler run')
        return KnowledgeGraph.from_dict(json.loads((Path(replay)/('replay-current-'+request.param+'.json')).read_text()))
    return inspect_capture(tmp_path_factory.mktemp('retry-'+request.param),request.param)


def policies(graph):return [n for n in graph.nodes if n.kind=='kafka_retry_policy']


def test_actual_two_groups_keep_separate_static_retry_dlt_boundaries(captured):
    ps=policies(captured);assert len(ps)==2
    facts={n.id:n for n in captured.nodes}
    assert {facts[n.metadata['listener_fact_id']].metadata['group_id'] for n in ps}=={'group-one','group-two'}
    assert len({n.metadata['logical_id'] for n in ps})==2
    from kgmaker.flow import process
    for policy in ps:
        assert policy.metadata['status']=='DECLARED' and policy.metadata['attempts']==3
        rows=policy_boundaries(captured,{policy.metadata['origin_id']})
        assert {r['kind'] for r in rows}=={'declares_retry_boundary','declares_dlt_boundary'}
        assert all(r['status']=='DECLARED' and r['execution']=='NOT_OBSERVED' for r in rows)
        report=process(captured,policy.metadata['origin_id'])
        assert report['kafka_policy_boundaries']==rows
        assert all(e['kind'] not in {'declares_retry_boundary','declares_dlt_boundary'} for e in report['cfg']['edges'])


@pytest.mark.parametrize('language',['java','kotlin'])
@pytest.mark.parametrize('scenario',['custom','unsupported','source-shadow','ambiguous','expressions'])
def test_actual_configuration_or_api_remains_unknown(tmp_path,language,scenario):
    graph=inspect_capture(tmp_path,language,scenario);policy=policies(graph)[0]
    expected={'unsupported':'FRAMEWORK_API_UNSUPPORTED','source-shadow':'FRAMEWORK_API_UNSUPPORTED','custom':'CUSTOM_HANDLER_OR_CONTAINER_UNKNOWN','ambiguous':'DLT_HANDLER_UNPROVEN_OR_AMBIGUOUS','expressions':'ATTEMPTS_LITERAL_UNPROVEN'}[scenario]
    assert policy.metadata['status']=='UNKNOWN' and expected in policy.metadata['reasons']
    rows=policy_boundaries(graph,{policy.metadata['origin_id']})
    assert rows and all(r['status']=='UNKNOWN' for r in rows)
    assert not any(e.kind=='declares_dlt_boundary' for e in graph.edges)
    if scenario in {'unsupported','source-shadow'}:assert all(e.evidence_kind=='SYNTAX_CANDIDATE' for e in graph.edges if e.target==policy.id)


def reidentify(graph,policy,metadata):
    identity=metadata['logical_id']+':capture:'+digest(metadata)
    proofmap={}
    for p in graph.evidence:
        if p.get('extractor')=='kafka-retry-1' and policy.id in (p.get('source'),p.get('target')):
            old=p['id'];p['source']=identity if p['source']==policy.id else p['source'];p['target']=identity if p['target']==policy.id else p['target']
            p['id']='evidence:'+digest({k:v for k,v in p.items() if k!='id'});proofmap[old]=p['id']
    graph.nodes=[replace(n,id=identity,metadata=metadata) if n.id==policy.id else n for n in graph.nodes]
    graph.edges=[replace(e,source=identity if e.source==policy.id else e.source,target=identity if e.target==policy.id else e.target,
        evidence_ids=tuple(proofmap.get(ref,ref) for ref in e.evidence_ids)) for e in graph.edges]


CASES=['foreign-extra-edge','empty-evidence','edge-kind','edge-context','edge-file','edge-line','dlt-target',
       'proof-kind','proof-context','proof-source','proof-hash','proof-range','proof-extractor','proof-compiler-refs',
       'source-node','source-symbol','source-annotation','handler-scope','handler-symbol','handler-annotation',
       'handler-own-proof','listener-fact','listener-proof','coherent-attempts','coherent-missing-listener','coherent-api-resource','classpath','version','source-api-shadow','code-stamp','freshness','context-scope','source-file-hash','compiler-realm','annotation-proof']


@pytest.mark.parametrize('case',CASES)
def test_public_snapshot_tamper_is_local_unknown_without_mutation(captured,case):
    graph=KnowledgeGraph.from_dict(copy.deepcopy(captured.to_dict()));policy=policies(graph)[0];md=policy.metadata
    edge=next(e for e in graph.edges if e.source==policy.id and e.kind=='declares_dlt_boundary')
    proof=next(p for p in graph.evidence if p['id']==edge.evidence_ids[0]);origin=md['origin_id'];handler=md['handler_id']
    if case=='foreign-extra-edge':
        graph.nodes.append(Node('foreign-method','method','foreign','foreign.kt',scope='test'))
        graph.contexts.append({'id':'foreign-context','scope':'test'})
        graph.edges.append(Edge(policy.id,'foreign-method','declares_dlt_boundary',evidence_kind='SYNTAX_CANDIDATE',context_ids=('foreign-context',)))
        KnowledgeGraph.from_dict(graph.to_dict())
    elif case.startswith('edge-') or case in {'empty-evidence','dlt-target'}:
        change={'empty-evidence':{'evidence_ids':()},'edge-kind':{'evidence_kind':'SYNTAX_CANDIDATE'},
            'edge-context':{'context_ids':()},'edge-file':{'source_file':'other.kt'},'edge-line':{'source_line':edge.source_line+1},
            'dlt-target':{'target':origin}}[case]
        graph.edges=[replace(e,**change) if e is edge else e for e in graph.edges]
    elif case.startswith('proof-'):
        key={'proof-kind':'kind','proof-context':'context_ids','proof-source':'source','proof-hash':'sha256',
             'proof-range':'source_range','proof-extractor':'extractor','proof-compiler-refs':'compiler_evidence_ids'}[case]
        proof[key]=[] if key in {'context_ids','compiler_evidence_ids'} else {} if key=='source_range' else 'changed'
    elif case in {'source-node','handler-scope'}:
        identity=origin if case=='source-node' else handler
        graph.nodes=[replace(n,scope='test') if n.id==identity else n for n in graph.nodes]
    elif case in {'source-symbol','handler-symbol'}:
        next(s for s in graph.symbols if s['id']==(origin if case=='source-symbol' else handler))['scope']='test'
    elif case in {'source-annotation','handler-annotation'}:
        next(s for s in graph.symbols if s['id']==(origin if case=='source-annotation' else handler))['annotations']=[]
    elif case=='handler-own-proof':
        graph.evidence=[p for p in graph.evidence if not(p.get('relation')=='contains' and p.get('target')==handler)]
    elif case=='listener-fact':
        graph.nodes=[replace(n,metadata={**n.metadata,'group_id':'forged'}) if n.id==md['listener_fact_id'] else n for n in graph.nodes]
    elif case=='listener-proof':
        graph.evidence=[p for p in graph.evidence if not(p.get('relation')=='declares_kafka_listener' and p.get('target')==md['listener_fact_id'])]
    elif case.startswith('coherent-'):
        new=copy.deepcopy(md)
        if case=='coherent-attempts':new['attempts']=9
        elif case=='coherent-missing-listener':
            symbol=next(s for s in graph.symbols if s['id']==origin)
            symbol['annotations']=[a for a in symbol['annotations'] if a['name']!='org.springframework.kafka.annotation.KafkaListener']
            graph.nodes=[replace(n,metadata={**n.metadata,'annotations':symbol['annotations']}) if n.id==origin else n for n in graph.nodes]
            new['annotation_fingerprint']=digest(symbol['annotations'])
            for p in graph.evidence:
                if p.get('relation')=='contains' and p.get('target')==origin:p['compiler_annotation_fingerprint']=digest(symbol['annotations'])
            for _ in range(3):
                mapping={}
                for p in graph.evidence:
                    old=p['id'];p['id']='evidence:'+digest({k:v for k,v in p.items() if k!='id'})
                    if old!=p['id']:mapping[old]=p['id']
                for p in graph.evidence:
                    if 'compiler_evidence_ids' in p:p['compiler_evidence_ids']=[mapping.get(i,i) for i in p['compiler_evidence_ids']]
                graph.edges=[replace(e,evidence_ids=tuple(mapping.get(i,i) for i in e.evidence_ids)) for e in graph.edges]
        else:next(iter(new['api'].values()))['resource_sha256']='0'*64
        reidentify(graph,policy,new)
        if case=='coherent-missing-listener':KnowledgeGraph.from_dict(graph.to_dict())
    elif case=='classpath':
        c=next(c for c in graph.contexts if c['id']==md['context_id']);c['classpath']=list(reversed(c['classpath']));c['kafka_retry_analysis']=analysis_stamp(c)
    elif case=='source-api-shadow':
        identity='protected-annotation-shadow'
        graph.nodes.append(Node(identity,'class','RetryableTopic','fake.java',scope='production'))
        graph.symbols.append({'id':identity,'kind':'class','context_id':md['context_id'],'owner':'org.springframework.kafka.annotation.RetryableTopic','path':'fake.java'})
    elif case=='code-stamp':
        next(c for c in graph.contexts if c['id']==md['context_id'])['kafka_code_analysis']={'version':'foreign'}
    elif case=='freshness':next(c for c in graph.contexts if c['id']==md['context_id'])['freshness']='STALE'
    elif case=='context-scope':next(c for c in graph.contexts if c['id']==md['context_id'])['scope']='test'
    elif case=='source-file-hash':graph.files[policy.path]='0'*64
    elif case in {'compiler-realm','annotation-proof'}:
        original=next(p for p in graph.evidence if p.get('relation')=='contains' and p.get('target')==origin)
        if case=='compiler-realm':original['compiler_realm']['repo_id']='foreign'
        else:original['compiler_annotation_fingerprint']='0'*64
        for _ in range(3):
            replacements={}
            for p in graph.evidence:
                old=p['id'];p['id']='evidence:'+digest({k:v for k,v in p.items() if k!='id'})
                if old!=p['id']:replacements[old]=p['id']
            for p in graph.evidence:
                if 'compiler_evidence_ids' in p:p['compiler_evidence_ids']=[replacements.get(i,i) for i in p['compiler_evidence_ids']]
            graph.edges=[replace(e,evidence_ids=tuple(replacements.get(i,i) for i in e.evidence_ids)) for e in graph.edges]
    elif case=='version':
        c=next(c for c in graph.contexts if c['id']==md['context_id']);c['kafka_retry_analysis']['version']='future'
    before=copy.deepcopy(graph.to_dict())
    with patch('subprocess.Popen',side_effect=AssertionError('projection executed process')),patch('socket.socket',side_effect=AssertionError('projection used network')):
        rows=policy_boundaries(graph,{origin})
    assert rows and all(r['status']=='UNKNOWN' and r['kind']=='unresolved_policy_boundary' for r in rows),case
    assert all(r['target']!='foreign-method' for r in rows)
    assert graph.to_dict()==before
    other=[p for p in policies(graph) if p.metadata['origin_id']!=origin]
    if other and case not in {'classpath','version','source-api-shadow','code-stamp','freshness','context-scope','source-file-hash'}:assert all(r['status']=='DECLARED' for r in policy_boundaries(graph,{other[0].metadata['origin_id']}))


@pytest.mark.parametrize('order',['before','after','same'])
def test_duplicate_real_annotation_resources_fail_closed(captured,order):
    graph=KnowledgeGraph.from_dict(copy.deepcopy(captured.to_dict()));p=policies(graph)[0]
    c=next(c for c in graph.contexts if c['id']==p.metadata['context_id']);apis=api_inputs()
    duplicate={'path':str(apis['3.3.2'] if order=='same' else apis['3.2.0']),
        'sha256':hashlib.sha256(apis['3.3.2' if order=='same' else '3.2.0'].read_bytes()).hexdigest()}
    if order=='before':c['classpath'].insert(0,duplicate)
    else:c['classpath'].append(duplicate)
    assert api_witness(c,graph) is None


def test_existing_workspace_qualification_preserves_proven_policy(captured):
    from kgmaker.workspace import (qualified,source_key,_qualified_context,_qualified_symbol,
        _qualified_evidence,_qualified_kafka_metadata,_qualified_retry_metadata)
    repo='backend'
    graph=replace(captured,
        nodes=[replace(n,id=qualified(repo,n.id),path=source_key(repo,n.path),
            metadata=_qualified_retry_metadata(repo,n.metadata) if n.kind=='kafka_retry_policy' else
                     _qualified_kafka_metadata(repo,n.metadata) if n.kind=='kafka_code_listener' else n.metadata) for n in captured.nodes],
        edges=[replace(e,source=qualified(repo,e.source),target=qualified(repo,e.target),
            context_ids=tuple(qualified(repo,c) for c in e.context_ids),
            source_file=source_key(repo,e.source_file) if e.source_file else None,
            evidence_ids=tuple(qualified(repo,i) for i in e.evidence_ids)) for e in captured.edges],
        contexts=[_qualified_context(repo,c) for c in captured.contexts],
        files={source_key(repo,p):h for p,h in captured.files.items()},
        symbols=[_qualified_symbol(repo,s) for s in captured.symbols],
        evidence=[_qualified_evidence(repo,p) for p in captured.evidence])
    methods={p.metadata['origin_id'] for p in policies(graph)}
    before=copy.deepcopy(graph.to_dict());rows=policy_boundaries(graph,methods)
    assert rows and all(r['status']=='DECLARED' for r in rows)
    assert all(r['source'].startswith('repo:backend:') and r['target'].startswith('repo:backend:') for r in rows)
    assert graph.to_dict()==before


def test_legacy_without_policy_never_infers_retry(captured):
    ids={p.id for p in policies(captured)}
    graph=replace(captured,nodes=[n for n in captured.nodes if n.id not in ids],
        edges=[e for e in captured.edges if e.source not in ids and e.target not in ids])
    assert policy_boundaries(graph,{s['id'] for s in graph.symbols})==[]


@pytest.mark.parametrize('required',[False,True])
@pytest.mark.parametrize('mode',['missing','wrong'])
def test_api_prerequisite_does_not_accept_missing_or_wrong_bytes(tmp_path,monkeypatch,required,mode):
    fixture=tmp_path/'fixtures/kafka-retry-dlt';fixture.mkdir(parents=True)
    lock=json.loads((ROOT/'fixtures/kafka-retry-dlt/dependencies.lock.json').read_text());item=lock['artifacts'][-1]
    (fixture/'dependencies.lock.json').write_text(json.dumps({**lock,'artifacts':[item]}))
    repository=tmp_path/'m2'
    if mode=='wrong':
        artifact=repository/item['path'];artifact.parent.mkdir(parents=True);artifact.write_bytes(b'wrong jar')
    monkeypatch.setitem(api_inputs.__globals__,'ROOT',tmp_path)
    monkeypatch.setenv('KGMAKER_TEST_MAVEN_REPOSITORY',str(repository))
    monkeypatch.setenv('KGMAKER_REQUIRE_WORKERS','1' if required else '0');monkeypatch.setenv('KGMAKER_REQUIRE_K2','0')
    with patch('subprocess.Popen',side_effect=AssertionError('unverified tool executed')):
        with pytest.raises(pytest.fail.Exception if required else pytest.skip.Exception):api_inputs()


def test_policy_markdown_keeps_framework_intent_separate_from_cfg(captured):
    from kgmaker.flow import process,markdown
    policy=policies(captured)[0]
    before=copy.deepcopy(captured.to_dict())
    with patch('subprocess.Popen',side_effect=AssertionError('flow executed process')),patch('socket.socket',side_effect=AssertionError('flow used network')):
        report=process(captured,policy.metadata['origin_id']);text=markdown(report)
    assert 'Kafka retry/DLT policy declarations (execution NOT_OBSERVED)' in text
    assert 'delivery NOT_OBSERVED; runtime/data availability UNKNOWN' in text
    assert captured.to_dict()==before


@pytest.mark.parametrize('field',['origin_id','context_id','logical_id','handler_id','api','source_realm','source_range','reasons','status','version'])
@pytest.mark.parametrize('value',[None,[],{}],ids=['null','array','object'])
def test_primitive_policy_fields_fail_closed_as_public_unknown(captured,field,value):
    graph=KnowledgeGraph.from_dict(copy.deepcopy(captured.to_dict()));policy=policies(graph)[0];origin=policy.metadata['origin_id']
    original=copy.deepcopy(policy.metadata.get(field))
    policy.metadata[field]=copy.deepcopy(value)
    KnowledgeGraph.from_dict(graph.to_dict())
    before=copy.deepcopy(graph.to_dict());rows=policy_boundaries(graph,{origin})
    if value==original:
        assert rows==policy_boundaries(captured,{origin})
    else:
        assert rows and all(r['status']=='UNKNOWN' and r['source']==origin for r in rows)
    assert graph.to_dict()==before


@pytest.mark.parametrize('change',['kind','metadata-array','metadata-null'])
def test_selected_malformed_policy_remains_a_visible_unknown(captured,change):
    graph=KnowledgeGraph.from_dict(copy.deepcopy(captured.to_dict()));policy=policies(graph)[0];origin=policy.metadata['origin_id']
    values={'kind':{'kind':'file'},'metadata-array':{'metadata':[]},'metadata-null':{'metadata':None}}[change]
    graph.nodes=[replace(n,**values) if n.id==policy.id else n for n in graph.nodes]
    rows=policy_boundaries(graph,{origin})
    assert rows and all(r['status']=='UNKNOWN' for r in rows)


def test_bad_method_selection_is_controlled_and_read_only(captured):
    before=copy.deepcopy(captured.to_dict())
    for bad in (None,'method-id',[{}]):
        with pytest.raises(ValueError,match='explicit method IDs'):policy_boundaries(captured,bad)
    assert captured.to_dict()==before
