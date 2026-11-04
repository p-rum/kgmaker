"""Bounded pinned framework policy declarations, never observed retry execution."""
from dataclasses import replace
from pathlib import Path
import hashlib
import re
import zipfile

from .analysis_model import digest
from .model import Node, Edge, KnowledgeGraph
from .kafka_code import _Capture, validate_code_fact, _range

VERSION='kafka-retry-1'
RETRY='org.springframework.kafka.annotation.RetryableTopic'
DLT='org.springframework.kafka.annotation.DltHandler'
LISTENER='org.springframework.kafka.annotation.KafkaListener'
# Exact official Spring Kafka3.3.2 library, not only annotation class bytes:
# 3.2.0 has identical annotation classes but is deliberately unsupported.
SUPPORTED_SHA='39aedad4ed809a5d0a81c00c543afc2d931201e02d5b3f0e8bc9d36591993282'
RESOURCE_HASHES={
    'org/springframework/kafka/annotation/KafkaListener.class':'675902c8568c59246521e0c24c01115262b14649203676c4fb3f22e37f2cbe04',
    'org/springframework/kafka/annotation/RetryableTopic.class':'04cd9c6af6677d252a5f7adf05c5109a8f2882aab3b324c436ec1e354ecac58e',
    'org/springframework/kafka/annotation/DltHandler.class':'cec1f3864411c0f3190eaf6ebdd221221706f6a058c3e96b777edd7d8ceae310'}
RESOURCES=set(RESOURCE_HASHES)


def analysis_stamp(context):
    return {'version':VERSION,'classpath_sha256':digest(context.get('classpath',[]))}


def _hash(path):
    result=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(65536),b''):result.update(chunk)
    return result.hexdigest()


def api_witness(context,graph):
    """Only one occurrence of each resource in the supported whole JAR is admitted."""
    entries=context.get('classpath')
    if not isinstance(entries,list) or len(entries)>512:return None
    if any(s.get('context_id')==context.get('id') and s.get('owner') in {RETRY,DLT,LISTENER}
           and s.get('path') for s in graph.symbols):return None
    selected={}
    for entry in entries:
        if not isinstance(entry,dict) or not isinstance(entry.get('path'),str):return None
        p=Path(entry['path'])
        try:
            if p.is_dir():
                if any((p/name).exists() for name in RESOURCES):return None
                continue
            if not p.is_file() or p.stat().st_size>32_000_000:return None
            if not zipfile.is_zipfile(p):continue
            with zipfile.ZipFile(p) as archive:
                if len(archive.infolist())>50000:return None
                names=set(archive.namelist())
                if any(name.startswith('META-INF/versions/') and any(name.endswith('/'+resource) for resource in RESOURCES) for name in names):return None
                if 'META-INF/MANIFEST.MF' in names:
                    manifest=archive.getinfo('META-INF/MANIFEST.MF')
                    if manifest.file_size>65536:return None
                    if re.search(r'(?im)^class-path\s*:',archive.read(manifest).decode('utf-8',errors='replace')):return None
                matches=RESOURCES&names
                if matches & set(selected):return None
                if not matches:continue
                actual=_hash(p)
                if actual!=entry.get('sha256') or actual!=SUPPORTED_SHA:return None
                for name in matches:
                    info=archive.getinfo(name)
                    if info.file_size>1_000_000 or archive.namelist().count(name)!=1:return None
                    resource_hash=hashlib.sha256(archive.read(info)).hexdigest()
                    if resource_hash!=RESOURCE_HASHES[name]:return None
                    selected[name]={'jar_sha256':actual,'resource_sha256':resource_hash}
        except (OSError,ValueError,zipfile.BadZipFile,RuntimeError):return None
    return selected if set(selected)==RESOURCES else None


def _annotations(symbol,name):
    annotations=symbol.get('annotations')
    return [a for a in annotations if isinstance(a,dict) and a.get('name')==name] if isinstance(annotations,list) else []


def _policy_values(symbol, witness):
    reasons=[]
    if witness is None:reasons.append('FRAMEWORK_API_UNSUPPORTED')
    annotations=_annotations(symbol,RETRY)
    values=annotations[0].get('values') if len(annotations)==1 else None
    if not isinstance(values,dict) or len(values)>64:
        values={};reasons.append('RETRY_ANNOTATION_SHAPE_UNKNOWN')
    if len(annotations)!=1 or annotations[0].get('values_resolved',True) is not True:
        reasons.append('RETRY_ANNOTATION_VALUES_UNRESOLVED')
    attempts=values.get('attempts')
    attempts=int(attempts) if isinstance(attempts,str) and re.fullmatch('[1-9][0-9]{0,3}',attempts) else None
    retry=values.get('retryTopicSuffix');dlt=values.get('dltTopicSuffix')
    if attempts is None:reasons.append('ATTEMPTS_LITERAL_UNPROVEN')
    def suffix(value):return isinstance(value,str) and bool(re.fullmatch('[A-Za-z0-9._-]{1,128}',value))
    if not suffix(retry) or not suffix(dlt):reasons.append('SUFFIX_LITERAL_UNPROVEN')
    # Exact pinned defaults may be carried by Javac. They are not evaluated
    # into scheduling, destination, availability, or default handler claims.
    defaults={'backoff':'@org.springframework.retry.annotation.Backoff','timeout':'','kafkaTemplate':'',
        'listenerContainerFactory':'','autoCreateTopics':'true','numPartitions':'1','replicationFactor':'-1',
        'include':[],'exclude':[],'includeNames':[],'excludeNames':[],'traversingCauses':'',
        'exceptionBasedDltRouting':[],'topicSuffixingStrategy':'org.springframework.kafka.retrytopic.TopicSuffixingStrategy.SUFFIX_WITH_DELAY_VALUE',
        'sameIntervalTopicReuseStrategy':'org.springframework.kafka.retrytopic.SameIntervalTopicReuseStrategy.SINGLE_TOPIC',
        'dltStrategy':'org.springframework.kafka.retrytopic.DltStrategy.ALWAYS_RETRY_ON_ERROR',
        'autoStartDltHandler':'','concurrency':''}
    for key,value in values.items():
        if key not in {'attempts','retryTopicSuffix','dltTopicSuffix'} and (key not in defaults or value!=defaults[key]):
            reasons.append('RETRY_CONFIGURATION_UNSUPPORTED')
    listener_values=_annotations(symbol,LISTENER)[0].get('values',{})
    controls={'errorHandler','containerFactory','containerGroup','containerPostProcessor','filter',
              'contentTypeConverter','concurrency','autoStartup','batch','properties'}
    if any(listener_values.get(k) not in (None,'',[]) for k in controls):reasons.append('CUSTOM_HANDLER_OR_CONTAINER_UNKNOWN')
    return attempts,retry if suffix(retry) else None,dlt if suffix(dlt) else None,reasons


def augment_retry_graph(root,graph,context):
    """Add optional declarations over the same selected canonical Kafka capture."""
    KnowledgeGraph.from_dict(graph.to_dict())
    capture=_Capture(Path(root),graph,context)
    candidates=[s for s in graph.symbols if s.get('context_id')==context.get('id')
                and _annotations(s,RETRY)]
    if not candidates:return graph
    witness=api_witness(context,graph)
    nodes=[];edges=[];proofs=[];diagnostics=[]
    def proven(symbol):
        source=capture.source(symbol)
        if source is None:return None
        if not any(p.get('kind')=='SYMBOL_RESOLVED' and p.get('relation')=='contains'
            and p.get('target')==symbol['id'] and p.get('context_ids')==[context['id']]
            and p.get('compiler_annotation_fingerprint')==digest(symbol['annotations'])
            for p in graph.evidence):return None
        return source
    listeners={n.metadata.get('origin_id'):n for n in graph.nodes
               if n.kind=='kafka_code_listener' and isinstance(n.metadata,dict)
               and n.metadata.get('context_id')==context['id']}
    for symbol in candidates[:2048]:
        reasons=[];source=proven(symbol);fact=listeners.get(symbol.get('id'))
        if source is None or fact is None or not validate_code_fact(Path(root),graph,context,fact):
            diagnostics.append({'code':'KAFKA_RETRY_UNPROVEN','reason':'CANONICAL_LISTENER_UNPROVEN','context_id':context['id'],'source_id':symbol.get('id')});continue
        attempts,retry,dlt,reasons=_policy_values(symbol,witness)
        # A DLT method is declaration-associated only for one canonical listener
        # and one exact owner-scoped handler with matching supported payload ABI.
        same=[s for s in graph.symbols if s.get('context_id')==context['id'] and s.get('owner')==symbol['owner'] and _annotations(s,DLT)]
        owner_listeners=[s for s in graph.symbols if s.get('context_id')==context['id'] and s.get('owner')==symbol['owner'] and _annotations(s,LISTENER)]
        handler=None
        if len(same)==1 and len(owner_listeners)==1 and same[0].get('descriptor')==symbol.get('descriptor') and proven(same[0]) is not None:
            h=same[0];ann=_annotations(h,DLT)
            if len(ann)==1 and ann[0].get('values')=={} and ann[0].get('values_resolved',True) is True:handler=h
        if handler is None:reasons.append('DLT_HANDLER_UNPROVEN_OR_AMBIGUOUS')
        if len(candidates)>2048:reasons.append('RETRY_POLICY_LIMIT')
        logical='kafka-retry-policy:'+digest({'listener':fact.metadata['logical_id'],'version':VERSION})
        metadata={'version':VERSION,'logical_id':logical,'origin_id':symbol['id'],'listener_fact_id':fact.id,
            'context_id':context['id'],'classpath_sha256':digest(context.get('classpath',[])),'source_sha256':symbol['sha256'],'source_range':symbol['range'],
            'attempts':attempts,'retry_suffix':retry,'dlt_suffix':dlt,
            'handler_id':handler['id'] if handler is not None else None,'api':witness,
            'source_realm':{k:context[k] for k in ('repo_id','module','source_set','scope')},
            'handler_annotation_fingerprint':digest(handler['annotations']) if handler is not None else None,
            'handler_sha256':handler['sha256'] if handler is not None else None,
            'handler_range':handler['range'] if handler is not None else None,
            'annotation_fingerprint':digest(symbol['annotations']),'status':'DECLARED' if not reasons else 'UNKNOWN',
            'reasons':sorted(set(reasons)),'async_boundary':'RETRY_POLICY','execution':'NOT_OBSERVED','delivery':'NOT_OBSERVED',
            'activation':'UNKNOWN','runtime_availability':'UNKNOWN','data_availability':'UNKNOWN',
            'scheduling':'UNKNOWN','destinations':'UNKNOWN'}
        identity=logical+':capture:'+digest(metadata)
        nodes.append(Node(identity,'kafka_retry_policy',symbol['name'],symbol['path'],line=symbol['range']['start_line'],
            scope=context['scope'],role='contract',origin='generated',metadata=metadata))
        relations=[(symbol['id'],identity,'declares_retry_boundary')]
        if handler is not None and not reasons:relations.append((identity,handler['id'],'declares_dlt_boundary'))
        file_node=next(n for n in graph.nodes if n.kind=='file' and n.path==symbol['path'])
        compiler_refs=capture.compiler_refs(file_node.id,symbol['id'],'contains',symbol,symbol['range'])
        evidence_kind='FRAMEWORK_DERIVED' if witness is not None else 'SYNTAX_CANDIDATE'
        handler_refs=[]
        if handler is not None:
            handler_file=next(n for n in graph.nodes if n.kind=='file' and n.path==handler['path'])
            handler_refs=capture.compiler_refs(handler_file.id,handler['id'],'contains',handler,handler['range'])
        for first,last,kind in relations:
            proof={'kind':evidence_kind,'source':first,'target':last,'relation':kind,'context_ids':[context['id']],
                'source_file':symbol['path'],'source_range':symbol['range'],'sha256':symbol['sha256'],
                'extractor':VERSION,'compiler_evidence_ids':sorted(set(compiler_refs+(handler_refs if kind=='declares_dlt_boundary' else []))),'execution':'NOT_OBSERVED',
                'async_boundary':'RETRY_POLICY' if kind=='declares_retry_boundary' else 'DLT_POLICY'}
            pid='evidence:'+digest(proof);proofs.append({'id':pid,**proof})
            edges.append(Edge(first,last,kind,'Pinned framework policy declaration; execution unobserved',source_file=symbol['path'],
                source_line=symbol['range']['start_line'],evidence_kind=evidence_kind,context_ids=(context['id'],),evidence_ids=(pid,)))
        diagnostics.extend({'code':'KAFKA_RETRY_UNPROVEN','reason':reason,'context_id':context['id'],'source_id':symbol['id']} for reason in sorted(set(reasons)))
    contexts=[{**c,'kafka_retry_analysis':analysis_stamp(c)} if c.get('id')==context['id'] else c for c in graph.contexts]
    return replace(graph,nodes=[*graph.nodes,*nodes],edges=[*graph.edges,*edges],evidence=[*graph.evidence,*proofs],
                   contexts=contexts,diagnostics=[*graph.diagnostics,*diagnostics])


def validate_analysis(context):
    from .worker_protocol import WorkerError
    if 'kafka_retry_analysis' in context and context['kafka_retry_analysis']!=analysis_stamp(context):
        raise WorkerError('STALE_INDEX: Kafka retry policy rules changed; inspect again','STALE')


def qualified_metadata(repo, metadata):
    from .workspace import qualified
    result=dict(metadata)
    for key in ('origin_id','logical_id','context_id','listener_fact_id','handler_id'):
        if isinstance(metadata.get(key),str):
            result['original_'+key]=metadata[key]
            result[key]=qualified(repo,metadata[key])
    result['repo_id']=repo
    return result


def _original_metadata(metadata, identity):
    from .workspace import split_id, qualified
    if not identity.startswith('repo:'):return metadata,identity
    repo,original_id=split_id(identity)
    if metadata.get('repo_id')!=repo:return None,None
    result=dict(metadata);result.pop('repo_id',None)
    for key in ('origin_id','logical_id','context_id','listener_fact_id','handler_id'):
        original=result.pop('original_'+key,None)
        if isinstance(result.get(key),str):
            if not isinstance(original,str) or result[key]!=qualified(repo,original):return None,None
            result[key]=original
        elif original is not None:return None,None
    return result,original_id



def _original_evidence(record, repo):
    """Undo only existing workspace qualification, never repair a proof."""
    from .workspace import split_id, source_key
    result=dict(record)
    if repo is None:return result
    if result.pop('repo_id',None)!=repo:return None
    def raw(value):
        owner,identity=split_id(value)
        if owner!=repo:raise ValueError('Foreign evidence realm')
        return identity
    for key in ('id','source','target','origin_id'):
        if isinstance(result.get(key),str):result[key]=raw(result[key])
    if 'original_origin_id' in result:
        if result.pop('original_origin_id')!=result.get('origin_id'):return None
    result['context_ids']=[raw(value) for value in result.get('context_ids',[])]
    path=result.get('source_file')
    if isinstance(path,str):
        prefix=source_key(repo,'')
        if not path.startswith(prefix):return None
        result['source_file']=path[len(prefix):]
    if 'compiler_evidence_ids' in result:
        result['compiler_evidence_ids']=[raw(value) for value in result['compiler_evidence_ids']]
    return result


def _proof_identity(record,repo):
    try:
        original=_original_evidence(record,repo)
        if original is None:return False
        identity=original.pop('id')
        return identity=='evidence:'+digest(original)
    except (KeyError,TypeError,ValueError,RecursionError):return False


def _declaration(graph,identity,context,repo):
    """Canonical selected method mirror and its original annotation proof."""
    from .workspace import _qualified_symbol
    from .kafka_code import declaration_witness
    nodes={n.id:n for n in graph.nodes};proofs={p['id']:p for p in graph.evidence}
    matches=[s for s in graph.symbols if s.get('id')==identity]
    node=nodes.get(identity)
    if len(matches)!=1 or node is None or not isinstance(node.metadata,dict):return None
    symbol=matches[0];raw=node.metadata
    expected=_qualified_symbol(repo,raw) if repo is not None else raw
    if (symbol!=expected or node.kind!='method' or symbol.get('kind')!='method'
            or node.name!=symbol.get('name') or node.signature!=symbol.get('descriptor')
            or node.path!=symbol.get('path') or node.scope!=symbol.get('scope') or node.scope!=context.get('scope')
            or symbol.get('context_id')!=context.get('id')
            or not all(isinstance(symbol.get(k),str) and symbol[k] for k in ('id','owner','name','descriptor','path','sha256','context_id'))
            or re.fullmatch('[0-9a-f]{64}',symbol.get('sha256','')) is None
            or not _range(symbol.get('range')) or node.line!=symbol['range'].get('start_line')
            or not isinstance(context.get('source_files'),dict)
            or graph.files.get(node.path) is None or context['source_files'].get(node.path)!=graph.files[node.path]):return None
    refs=[]
    for edge in graph.edges:
        if edge.kind!='contains' or edge.target!=identity:continue
        file=nodes.get(edge.source)
        if (file is None or file.kind!='file' or file.path!=node.path or file.scope!=node.scope
                or edge.evidence_kind!='SYMBOL_RESOLVED' or edge.context_ids!=(context['id'],)
                or edge.source_file!=node.path or edge.source_line!=node.line):continue
        for ref in edge.evidence_ids:
            proof=proofs.get(ref,{})
            original=_original_evidence(proof,repo) if proof else None
            if (original is not None and _proof_identity(proof,repo)
                    and proof.get('kind')=='SYMBOL_RESOLVED' and proof.get('relation')=='contains'
                    and proof.get('source')==file.id and proof.get('target')==identity
                    and proof.get('context_ids')==[context['id']] and proof.get('source_file')==node.path
                    and proof.get('source_range')==symbol['range'] and proof.get('sha256')==symbol.get('sha256')
                    and original.get('compiler_declaration')==declaration_witness(raw)
                    and original.get('compiler_realm')=={k:context.get(k) for k in ('repo_id','module','source_set','scope')}
                    and proof.get('origin_trust')=='LOCAL_COMPILER_INPUTS' and proof.get('freshness')=='CONTENT_VERIFIED'
                    and proof.get('compiler_annotation_fingerprint')==digest(symbol.get('annotations'))):refs.append(ref)
    return (symbol,raw,sorted(set(refs))) if refs else None


def _listener_anchor(graph,fact,method,context,repo,refs):
    from .workspace import split_id,qualified,source_key
    if fact is None or fact.kind!='kafka_code_listener' or fact.scope!=context['scope'] or fact.path!=method['path']:return False
    md=fact.metadata
    if not isinstance(md,dict):return False
    original=dict(md);identity=fact.id
    if repo is not None:
        owner,identity=split_id(identity)
        if owner!=repo or original.pop('repo_id',None)!=repo:return False
        for key in ('origin_id','logical_id','context_id'):
            value=original.pop('original_'+key,None)
            if not isinstance(value,str) or original.get(key)!=qualified(repo,value):return False
            original[key]=value
        value=original.pop('original_source_file',None)
        if not isinstance(value,str) or original.get('source_file')!=source_key(repo,value):return False
        original['source_file']=value
    base={'version','logical_id','revision','origin_id','context_id','source_realm','source_file',
          'source_sha256','source_range','owner','method_name','descriptor','scope','execution','activation'}
    facts={k:v for k,v in original.items() if k not in base}
    logical={**original.get('source_realm',{}),'owner':method['owner'],'name':method['name'],'descriptor':method['descriptor']}
    expected_logical='kafka_code_listener:'+digest(logical)
    expected_revision=digest({'logical_id':expected_logical,'context_id':original.get('context_id'),
        'path':original.get('source_file'),'sha256':method.get('sha256'),'range':method.get('range'),
        'version':'kafka-code-1','facts':facts})
    if (identity!=expected_logical+':capture:'+expected_revision or md.get('origin_id')!=method['id']
            or md.get('context_id')!=context['id'] or md.get('source_sha256')!=method['sha256']
            or md.get('source_range')!=method['range'] or original.get('version')!='kafka-code-1'):return False
    proofs={p['id']:p for p in graph.evidence}
    for edge in graph.edges:
        if (edge.kind!='declares_kafka_listener' or edge.source!=method['id'] or edge.target!=fact.id
                or edge.evidence_kind!='FRAMEWORK_DERIVED' or edge.context_ids!=(context['id'],)
                or edge.source_file!=method['path'] or edge.source_line!=method['range']['start_line']):continue
        for ref in edge.evidence_ids:
            p=proofs.get(ref,{})
            if (_proof_identity(p,repo) and p.get('kind')=='FRAMEWORK_DERIVED'
                    and p.get('source')==edge.source and p.get('target')==edge.target
                    and p.get('relation')==edge.kind and p.get('context_ids')==[context['id']]
                    and p.get('source_file')==method['path'] and p.get('source_range')==method['range']
                    and p.get('sha256')==method['sha256'] and p.get('compiler_evidence_ids')==refs):return True
    return False


def _validated_edges(graph,n):
    """Pure consistency replay over the supplied versioned snapshot, no I/O."""
    from .workspace import split_id
    md=n.metadata;raw,raw_id=_original_metadata(md,n.id)
    repo=split_id(n.id)[0] if n.id.startswith('repo:') else None
    nodes={v.id:v for v in graph.nodes};contexts={c['id']:c for c in graph.contexts};proofs={p['id']:p for p in graph.evidence}
    c=contexts.get(md.get('context_id'),{})
    if (raw is None or raw_id!=raw.get('logical_id','')+':capture:'+digest(raw)
            or md.get('version')!=VERSION or c.get('scope')!=n.scope
            or c.get('mode') not in {'BUILD_IMPORT','BUILD_EXECUTE'}
            or c.get('origin_trust')!='LOCAL_COMPILER_INPUTS' or c.get('freshness')!='CONTENT_VERIFIED'
            or c.get('kafka_retry_analysis')!=analysis_stamp(c)
            or c.get('kafka_code_analysis')!={'version':'kafka-code-1'}
            or not isinstance(c.get('framework_rule_versions'),dict) or c['framework_rule_versions'].get('kafka_retry')!=VERSION
            or md.get('classpath_sha256')!=digest(c.get('classpath',[]))):return None
    declaration=_declaration(graph,md.get('origin_id'),c,repo)
    if declaration is None:return None
    symbol,source,refs=declaration
    if (n.path!=symbol['path'] or n.name!=symbol['name'] or n.line!=symbol['range']['start_line']
            or md.get('annotation_fingerprint')!=digest(symbol['annotations'])
            or md.get('source_sha256')!=symbol['sha256'] or md.get('source_range')!=symbol['range']
            or md.get('source_realm')!={k:c.get(k) for k in ('repo_id','module','source_set','scope')}
            or not isinstance(c.get('kafka_code_source_hashes'),dict)
            or c['kafka_code_source_hashes'].get(source.get('path'))!=symbol['sha256']
            or not _listener_anchor(graph,nodes.get(md.get('listener_fact_id')),symbol,c,repo,refs)):return None
    api=md.get('api')
    if api is not None:
        if any(s.get('context_id')==c['id'] and s.get('owner') in {RETRY,DLT,LISTENER} and s.get('path') for s in graph.symbols):return None
        if not isinstance(api,dict) or set(api)!=RESOURCES:return None
        if any(value!={'jar_sha256':SUPPORTED_SHA,'resource_sha256':RESOURCE_HASHES[name]} for name,value in api.items()):return None
        if not any(e.get('sha256')==SUPPORTED_SHA for e in c.get('classpath',[]) if isinstance(e,dict)):return None
    attempts,retry,dlt,reasons=_policy_values(symbol,api)
    handler=nodes.get(md.get('handler_id'));handler_refs=[]
    owner_listeners=[s for s in graph.symbols if s.get('context_id')==c['id'] and s.get('owner')==symbol['owner'] and _annotations(s,LISTENER)]
    owner_handlers=[s for s in graph.symbols if s.get('context_id')==c['id'] and s.get('owner')==symbol['owner'] and _annotations(s,DLT)]
    if handler is not None:
        hd=_declaration(graph,handler.id,c,repo)
        if (hd is None or len(owner_listeners)!=1 or len(owner_handlers)!=1 or owner_handlers[0]['id']!=handler.id
                or hd[0]['owner']!=symbol['owner'] or hd[0]['descriptor']!=symbol['descriptor']
                or len(_annotations(hd[0],DLT))!=1 or _annotations(hd[0],DLT)[0].get('values')!={}
                or _annotations(hd[0],DLT)[0].get('values_resolved',True) is not True
                or md.get('handler_annotation_fingerprint')!=digest(hd[0]['annotations'])
                or md.get('handler_sha256')!=hd[0]['sha256'] or md.get('handler_range')!=hd[0]['range']):return None
        handler_refs=hd[2]
    else:reasons.append('DLT_HANDLER_UNPROVEN_OR_AMBIGUOUS')
    if (md.get('attempts')!=attempts or md.get('retry_suffix')!=retry or md.get('dlt_suffix')!=dlt
            or md.get('reasons')!=sorted(set(reasons)) or md.get('status')!=('UNKNOWN' if reasons else 'DECLARED')):return None
    expected={(symbol['id'],n.id,'declares_retry_boundary')}
    if not reasons:expected.add((n.id,handler.id,'declares_dlt_boundary'))
    related={n.id,symbol['id']}|({handler.id} if handler is not None else set())
    edges=[e for e in graph.edges if e.kind in {'declares_retry_boundary','declares_dlt_boundary'} and {e.source,e.target}&related]
    if len(edges)!=len(expected) or {(e.source,e.target,e.kind) for e in edges}!=expected:return None
    evidence_kind='FRAMEWORK_DERIVED' if api is not None else 'SYNTAX_CANDIDATE'
    for edge in edges:
        if (edge.evidence_kind!=evidence_kind or edge.context_ids!=(c['id'],)
                or edge.source_file!=symbol['path'] or edge.source_line!=symbol['range']['start_line']
                or len(edge.evidence_ids)!=1):return None
        p=proofs.get(edge.evidence_ids[0],{})
        required_refs=sorted(set(refs+(handler_refs if edge.kind=='declares_dlt_boundary' else [])))
        if (not _proof_identity(p,repo) or p.get('kind')!=evidence_kind or p.get('source')!=edge.source
                or p.get('target')!=edge.target or p.get('relation')!=edge.kind or p.get('extractor')!=VERSION
                or p.get('context_ids')!=[c['id']] or p.get('source_file')!=symbol['path']
                or p.get('source_range')!=symbol['range'] or p.get('sha256')!=symbol['sha256']
                or p.get('compiler_evidence_ids')!=required_refs or p.get('execution')!='NOT_OBSERVED'
                or p.get('async_boundary')!=('RETRY_POLICY' if edge.kind=='declares_retry_boundary' else 'DLT_POLICY')):return None
    return edges


def policy_boundaries(graph, methods):
    """Never expose a foreign or unproved policy edge as a declared boundary."""
    result=[]
    for node in graph.nodes:
        if node.kind!='kafka_retry_policy' or not isinstance(node.metadata,dict):continue
        md=node.metadata
        if md.get('origin_id') not in methods:continue
        try:edges=_validated_edges(graph,node)
        except (ValueError,TypeError,KeyError,AttributeError,RecursionError):edges=None
        if edges is None:
            result.append({'source':md.get('origin_id'),'target':node.id,'kind':'unresolved_policy_boundary',
                'async_boundary':'UNKNOWN','policy_id':node.id,'status':'UNKNOWN',
                'reasons':['KAFKA_POLICY_PROOF_UNPROVEN'],'execution':'NOT_OBSERVED','delivery':'NOT_OBSERVED',
                'runtime_availability':'UNKNOWN','evidence_ids':[]})
            continue
        for edge in edges:
            result.append({'source':edge.source,'target':edge.target,'kind':edge.kind,
                'async_boundary':'RETRY_POLICY' if edge.kind=='declares_retry_boundary' else 'DLT_POLICY',
                'policy_id':node.id,'status':md['status'],'reasons':md['reasons'],'execution':'NOT_OBSERVED',
                'delivery':'NOT_OBSERVED','runtime_availability':'UNKNOWN','evidence_ids':list(edge.evidence_ids)})
    return sorted(result,key=lambda row:(row['policy_id'],row['kind'],row['target']))
