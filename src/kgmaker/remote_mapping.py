"""Explicit operation/release declarations, never runtime or JVM call resolution.

Capture is the local I/O trust boundary. Resolution is a pure consumer of that
handoff; hashes establish consistency, not authentication of arbitrary JSON.
"""
from copy import deepcopy
from dataclasses import is_dataclass
import hashlib
import math
from pathlib import PurePosixPath, Path
import re

from .analysis_model import digest as _shared_digest
from .architecture_model import ViewDocument
from .model import KnowledgeGraph

VERSION = 'remote-contract-mapping-1'
SCOPES = {'production', 'test', 'test_fixture', 'development', 'unknown'}
_LIMIT = 2000
_HASH = re.compile(r'[0-9a-f]{64}\Z')
_SECRET = re.compile(r'(?i)(://|\b(?:Basic|Bearer)\s+\S+|(?:password|secret|api[_-]?key|access[_-]?token)\s*[=:])')
_URI_USERINFO = re.compile(r'//[^/\s]*@')
_FIELDS = {'schema_version','rule_version','workspace_id','workspace_manifest_sha256',
           'workspace_fingerprint','graph_fingerprint','selection','remote_declarations',
           'contract_capture','canonical_interfaces','diagnostics','capture_id'}


class RemoteMappingError(ValueError):
    def __init__(self, code):
        self.diagnostic = {'code': code}
        super().__init__(code)


def _fail(code):
    raise RemoteMappingError(code) from None


def digest(value):
    # Reuse the canonical shared encoder, but never expose malformed-key values
    # or low-level exceptions from an untrusted handoff.
    try:
        return _shared_digest(value)
    except (TypeError, ValueError, RecursionError, OverflowError):
        _fail('REMOTE_INVALID_JSON')


def _bounded(value):
    active=set(); stack=[(value,0,False)]; count=chars=0
    while stack:
        item,depth,leave=stack.pop()
        if leave:
            active.remove(id(item));continue
        count+=1
        if count>500000 or depth>80:_fail('REMOTE_INPUT_LIMIT')
        if isinstance(item,str):chars+=len(item)
        elif isinstance(item,float) and not math.isfinite(item):_fail('REMOTE_INVALID_JSON')
        elif type(item) is int and item.bit_length()>128:_fail('REMOTE_INPUT_LIMIT')
        container=isinstance(item,(dict,list,tuple)) or is_dataclass(item)
        if container:
            if id(item) in active:_fail('REMOTE_CYCLIC_INPUT')
            active.add(id(item));stack.append((item,depth,True))
            values=vars(item) if is_dataclass(item) else item
            if len(values)>50000:_fail('REMOTE_INPUT_LIMIT')
            if isinstance(values,dict):
                for key,child in values.items():
                    if not isinstance(key,(str,tuple)):_fail('REMOTE_INVALID_JSON')
                    stack.extend([(key,depth+1,False),(child,depth+1,False)])
            else:stack.extend((child,depth+1,False) for child in values)
        elif item is not None and not isinstance(item,(str,int,float,bool)):_fail('REMOTE_INVALID_JSON')
        if chars>32000000:_fail('REMOTE_INPUT_LIMIT')


def _text(value):
    return (isinstance(value,str) and 0<len(value)<=4096 and not _SECRET.search(value)
            and not _URI_USERINFO.search(value)
            and not any(ord(c)<32 or ord(c)==127 for c in value))


def _object(value, fields):
    if not isinstance(value,dict) or set(value)!=set(fields):_fail('REMOTE_INVALID_DECLARATION')


def validate_remote_declarations(workspace):
    """Strict manifest shape only; does not inspect sources or contract bytes."""
    declaration=workspace.get('remote_mapping')
    if declaration is None:return {'schema_version':1,'releases':[],'compatibilities':[],'mappings':[]}
    _bounded(declaration)
    _object(declaration,{'schema_version','releases','compatibilities','mappings'})
    if type(declaration['schema_version']) is not int or declaration['schema_version']!=1:_fail('REMOTE_UNSUPPORTED_VERSION')
    for key in ('releases','compatibilities','mappings'):
        values=declaration[key]
        if not isinstance(values,list) or len(values)>_LIMIT:_fail('REMOTE_DECLARATION_LIMIT')
        ids=set()
        for value in values:
            if not isinstance(value,dict) or not _text(value.get('id')) or value['id'] in ids:_fail('REMOTE_INVALID_ID')
            ids.add(value['id'])
    services={s['id']:s for s in workspace.get('services',[])}
    contracts={(s['contract']['repo_id'],s['contract']['path']) for s in services.values()}
    releases={}
    for value in declaration['releases']:
        _object(value,{'id','service_id','interface_id','context_id','scope','release','contract'})
        if (any(not _text(value[k]) for k in ('id','service_id','interface_id','context_id','scope','release'))
                or value['service_id'] not in services or value['scope'] not in SCOPES):_fail('REMOTE_INVALID_RELEASE')
        contract=value['contract'];_object(contract,{'repo_id','path','sha256','pointer'})
        if not _text(contract['repo_id']) or not _text(contract['path']):_fail('REMOTE_INVALID_CONTRACT')
        path=PurePosixPath(contract['path'])
        if (path.is_absolute() or '..' in path.parts or '\\' in contract['path'] or ':' in contract['path']
                or (contract['repo_id'],contract['path']) not in contracts
                or not isinstance(contract['sha256'],str) or not _HASH.fullmatch(contract['sha256'])
                or not isinstance(contract['pointer'],str) or len(contract['pointer'])>4096
                or contract['pointer'] not in ('','#') and not contract['pointer'].startswith('#/')
                or contract['pointer'] and not _text(contract['pointer'])):_fail('REMOTE_INVALID_CONTRACT')
        releases[value['id']]=value
    compatibilities={}
    for value in declaration['compatibilities']:
        _object(value,{'id','source_release_id','target_release_id','assertion'})
        if (not _text(value['source_release_id']) or not _text(value['target_release_id'])
                or value['source_release_id'] not in releases or value['target_release_id'] not in releases
                or value['assertion']!='DECLARED_OPERATION_COMPATIBILITY'):_fail('REMOTE_INVALID_COMPATIBILITY')
        compatibilities[value['id']]=value
    for value in declaration['mappings']:
        _object(value,{'id','transport','source_release_id','target_release_id','compatibility_id'})
        if (not isinstance(value['transport'],str) or value['transport'] not in {'HTTP','KAFKA'}
                or not _text(value['source_release_id']) or not _text(value['target_release_id'])
                or value['source_release_id'] not in releases or value['target_release_id'] not in releases
                or value['compatibility_id'] is not None and (not _text(value['compatibility_id']) or value['compatibility_id'] not in compatibilities)):_fail('REMOTE_INVALID_MAPPING')
        source,target=releases[value['source_release_id']],releases[value['target_release_id']]
        if source['service_id']==target['service_id'] or source['scope']!=target['scope']:_fail('REMOTE_INVALID_SERVICE_PAIR')
        if value['compatibility_id'] is not None:
            pair=compatibilities[value['compatibility_id']]
            if any(pair[k]!=value[k] for k in ('source_release_id','target_release_id')):_fail('REMOTE_COMPATIBILITY_PAIR_MISMATCH')
    return {key:sorted(deepcopy(declaration[key]),key=lambda x:x['id']) if key!='schema_version' else 1 for key in declaration}


def _workspace(workspace):
    # These private locations enable capture, but are not public release authority.
    return {k:[{a:b for a,b in item.items() if not a.startswith('_')} for item in v] if k=='repositories' else v
            for k,v in workspace.items() if not k.startswith('_')}


def _graph(graph):
    value=graph.to_dict();value.pop('generated_at',None)
    return value


def _selection(scope, selected_contexts):
    if not isinstance(scope,str) or scope not in SCOPES:_fail('REMOTE_INVALID_SCOPE')
    selected={} if selected_contexts is None else selected_contexts
    if not isinstance(selected,dict) or len(selected)>_LIMIT:_fail('REMOTE_INVALID_SELECTION')
    rows=[]
    for key,value in selected.items():
        if not isinstance(key,tuple) or len(key)!=3 or any(not _text(k) for k in key) or not _text(value):_fail('REMOTE_INVALID_SELECTION')
        rows.append({'key':list(key),'context_id':value})
    return {'scope':scope,'selected_contexts':sorted(rows,key=lambda r:r['key'])}


def _views(values):
    if not isinstance(values,(list,tuple)) or len(values)!=3:_fail('REMOTE_INVALID_INTERFACES')
    result=[]
    try:
        for item in values:
            document=item if isinstance(item,ViewDocument) else ViewDocument.from_dict(item)
            if document.kind!='interfaces':_fail('REMOTE_INVALID_INTERFACES')
            result.append(document.to_dict(include_generation_metadata=False))
    except (ValueError,KeyError,TypeError,AttributeError):_fail('REMOTE_INVALID_INTERFACES')
    return sorted(result,key=lambda d:(d['rules_version'],d['view_id']))


def _pointer_inventory(document):
    pending=[('',document)];values=[]
    while pending:
        pointer,value=pending.pop()
        if len(values)>=10000:return sorted(values),True
        fragment='#'+pointer
        if _text(fragment):values.append(fragment)
        if isinstance(value,dict):
            pending.extend((pointer+'/'+str(key).replace('~','~0').replace('/','~1'),child) for key,child in value.items())
        elif isinstance(value,list):pending.extend((pointer+'/'+str(i),child) for i,child in enumerate(value))
    return sorted(values),False


def capture_remote_mapping_inputs(workspace,graph,*,scope='production',selected_contexts=None,source_coverage=None):
    """Explicit local capture/replay; no workers, builds, models or publication."""
    _bounded((workspace,graph,source_coverage,selected_contexts))
    if not isinstance(workspace,dict) or not isinstance(graph,KnowledgeGraph):_fail('REMOTE_INVALID_INPUT')
    selection=_selection(scope,selected_contexts);declaration=validate_remote_declarations(workspace)
    from .contract_inputs import capture_file
    from .interfaces import (capture_interface_contracts,attach_interface_contracts,
                             project_http_providers,project_http_consumers,project_kafka_interfaces)
    try:
        manifest=Path(workspace['_manifest_path'])
        captured_manifest=capture_file(manifest.parent,manifest.name,json_document=True)
        if (captured_manifest['raw_sha256']!=workspace['_manifest_hash']
                or digest(captured_manifest['document'])!=digest(_workspace(workspace))):_fail('REMOTE_MANIFEST_CHANGED')
        KnowledgeGraph.from_dict(graph.to_dict())
        contract_capture=capture_interface_contracts(workspace,graph)
        views=[]
        for project in (project_http_providers,project_http_consumers,project_kafka_interfaces):
            document=project(workspace,graph,scope=scope,selected_contexts=selected_contexts,source_coverage=source_coverage)
            views.append(attach_interface_contracts(workspace,graph,document,captured=contract_capture))
        # Private raw schemas may contain example payloads/credentials. Only the
        # hash/status and bounded pointer index cross the pure handoff boundary.
        summary={'source_capture_id':contract_capture['capture_id'],'files':{},'declarations':deepcopy(contract_capture['declarations'])}
        for key,record in contract_capture['files'].items():
            pointers,truncated=_pointer_inventory(record.get('document',{}))
            summary['files'][key]={k:deepcopy(record[k]) for k in ('repo_id','path','status','indexed','raw_sha256','source_sha256') if k in record}
            summary['files'][key].update(pointers=pointers,pointers_truncated=truncated)
        # Detect manifest mutation across source replays as well.
        if capture_file(manifest.parent,manifest.name)['raw_sha256']!=workspace['_manifest_hash']:_fail('REMOTE_MANIFEST_CHANGED')
    except RemoteMappingError:raise
    except (ValueError,TypeError,KeyError,OSError,RecursionError):_fail('REMOTE_CAPTURE_UNAVAILABLE')
    selection['source_coverage_fingerprint']=digest(source_coverage)
    result={'schema_version':1,'rule_version':VERSION,'workspace_id':workspace['workspace_id'],
        'workspace_manifest_sha256':workspace['_manifest_hash'],'workspace_fingerprint':digest(_workspace(workspace)),
        'graph_fingerprint':digest(_graph(graph)),'selection':selection,'remote_declarations':declaration,
        'contract_capture':summary,'canonical_interfaces':_views(views),'diagnostics':[]}
    result['capture_id']=digest(result)
    return result


def _context(node,by_id):
    attrs=node['attributes']
    value=attrs.get('context_id')
    if isinstance(value,str):return value
    values=attrs.get('context_ids')
    if isinstance(values,list) and len(values)==1 and isinstance(values[0],str):return values[0]
    fact=by_id.get(attrs.get('code_fact_id'))
    return (fact.metadata or {}).get('context_id') if fact else None


def resolve_remote_mappings(workspace,graph,interfaces,*,captured,scope,selected_contexts=None):
    """Pure resolution of explicit declarations in a trusted local capture handoff."""
    _bounded((workspace,graph,interfaces,captured,selected_contexts))
    if not isinstance(workspace,dict) or not isinstance(graph,KnowledgeGraph):_fail('REMOTE_INVALID_INPUT')
    selection=_selection(scope,selected_contexts);declaration=validate_remote_declarations(workspace)
    if (not isinstance(captured,dict) or set(captured)!=_FIELDS
            or type(captured.get('schema_version')) is not int or captured['schema_version']!=1
            or captured.get('rule_version')!=VERSION or captured.get('workspace_id')!=workspace.get('workspace_id')
            or captured.get('workspace_manifest_sha256')!=workspace.get('_manifest_hash')
            or captured.get('workspace_fingerprint')!=digest(_workspace(workspace))
            or captured.get('graph_fingerprint')!=digest(_graph(graph))
            or captured.get('remote_declarations')!=declaration
            or captured.get('capture_id')!=digest({k:v for k,v in captured.items() if k!='capture_id'})):_fail('REMOTE_CAPTURE_MISMATCH')
    chosen=captured.get('selection')
    if (not isinstance(chosen,dict) or set(chosen)!={'scope','selected_contexts','source_coverage_fingerprint'}
            or any(chosen[k]!=v for k,v in selection.items())
            or not isinstance(chosen['source_coverage_fingerprint'],str) or not _HASH.fullmatch(chosen['source_coverage_fingerprint'])):_fail('REMOTE_SELECTION_MISMATCH')
    documents=_views(interfaces)
    if documents!=captured['canonical_interfaces'] or any(d['scope']!=scope for d in documents):_fail('REMOTE_INTERFACE_MISMATCH')
    contract_capture=captured['contract_capture']
    if not isinstance(contract_capture,dict) or not isinstance(contract_capture.get('files'),dict):_fail('REMOTE_INVALID_CONTRACT_CAPTURE')
    by_id={n.id:n for n in graph.nodes};contexts={c['id']:c for c in graph.contexts}
    interfaces_by_id={}
    for doc in documents:
        for node in doc['nodes']:
            if node['kind'] in {'http_interface','kafka_interface'}:interfaces_by_id.setdefault(node['id'],[]).append((node,doc))
    releases={r['id']:r for r in declaration['releases']};rows={};diagnostics=[]
    def authority(release,transport,source):
        if release['scope']!=scope:return None,'REMOTE_SCOPE_UNSELECTED'
        entries=interfaces_by_id.get(release['interface_id'],[])
        if len(entries)!=1:return None,'REMOTE_INTERFACE_UNKNOWN_OR_AMBIGUOUS'
        node,doc=entries[0];attrs=node['attributes']
        direction=('CONSUMER',) if transport=='HTTP' and source else ('PROVIDER','PROVIDED') if transport=='HTTP' else ('PRODUCER',) if source else ('CONSUMER',)
        service=attrs.get('service_id') or (node.get('owner_id') or '').removeprefix('service:')
        if (node['kind']!=('http_interface' if transport=='HTTP' else 'kafka_interface') or attrs.get('direction') not in direction
                or service!=release['service_id'] or _context(node,by_id)!=release['context_id']):return None,'REMOTE_REALM_OR_DIRECTION_UNPROVEN'
        context=contexts.get(release['context_id'])
        if context is None or context.get('scope')!=scope or context.get('freshness') not in {'CURRENT','CONTENT_VERIFIED','EXECUTION_BOUND'}:return None,'REMOTE_CONTEXT_UNAVAILABLE'
        if node['resolution_status']!='RESOLVED' or node['freshness']!='CURRENT':return None,'REMOTE_INTERFACE_UNRESOLVED'
        if any(e['target']==node['id'] and e['resolution_status']!='RESOLVED' for e in doc['edges']):return None,'REMOTE_INTERFACE_UNRESOLVED'
        contract=release['contract'];record=contract_capture['files'].get('@'+contract['repo_id']+'/'+contract['path'],{})
        pointer='#' if contract['pointer']=='' else contract['pointer']
        if (record.get('status')!='CAPTURED' or record.get('indexed') is not True
                or record.get('raw_sha256')!=contract['sha256'] or pointer not in record.get('pointers',[])):return None,'REMOTE_CONTRACT_UNAVAILABLE_OR_CHANGED'
        if transport=='HTTP':
            parts=contract['pointer'].split('/')
            if (len(parts)!=4 or parts[:2]!=['#','paths'] or re.search(r'~(?![01])',parts[2])
                    or parts[3].upper() not in {'GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS'}):return None,'REMOTE_OPERATION_POINTER_UNSUPPORTED'
            from .test_analysis import normalized_path
            declared_route=parts[2].replace('~1','/').replace('~0','~')
            route=attrs.get('route_expression') if source else attrs.get('normalized_route')
            if (attrs.get('http_method')!=parts[3].upper() or not isinstance(route,str)
                    or normalized_path(route)!=normalized_path(declared_route)):return None,'REMOTE_OPERATION_MISMATCH'
        bindings=[b for b in attrs.get('contract_bindings',[]) if b.get('status')=='BOUND_DECLARATION'
            and b.get('contract')=={'repo_id':contract['repo_id'],'path':contract['path']} and b.get('raw_sha256')==contract['sha256']
            and (b.get('operation_pointer')==contract['pointer'] if transport=='HTTP' else True)]
        # Ordinary HTTP clients have no implicit contract expectation in T013.
        # The explicit release record supplies just that declared expectation.
        if not (transport=='HTTP' and source) and not bindings:return None,'REMOTE_CONTRACT_BINDING_UNPROVEN'
        if transport=='KAFKA':
            ref=attrs.get('message_contract_ref')
            if (attrs.get('code_binding')!='VERIFIED_STATIC' or not attrs.get('broker_realm') or attrs.get('topic_pattern')
                    or attrs.get('subscription_kind')!='TOPICS' or not attrs.get('topics')
                    or not isinstance(ref,dict) or ref.get('release')!=release['release']):return None,'REMOTE_MESSAGE_BINDING_UNPROVEN'
        return (node,doc),'CURRENT_CAPTURE'
    for mapping in declaration['mappings']:
        source,target=releases[mapping['source_release_id']],releases[mapping['target_release_id']]
        if source['scope']!=scope:continue
        row=rows.setdefault(source['id'],{'source_interface_id':source['interface_id'],'source_release_id':source['id'],
            'transport':mapping['transport'],'resolution_status':'UNRESOLVED','candidates':[],'mapping_ids':[],
            'unresolved_mapping_ids':[],'reasons':[],'runtime_execution':'NOT_OBSERVED','delivery':'NOT_OBSERVED',
            'runtime_availability':'UNKNOWN','deployment':'UNKNOWN','payload_compatibility':'UNKNOWN'})
        row['mapping_ids'].append(mapping['id'])
        left,reason=authority(source,mapping['transport'],True)
        right,target_reason=authority(target,mapping['transport'],False)
        reasons=[]
        if left is None:reasons.append(reason)
        if right is None:reasons.append(target_reason)
        a,b=source['contract'],target['contract']
        if mapping['compatibility_id'] is None and (a['sha256'],a['pointer'],source['release'])!=(b['sha256'],b['pointer'],target['release']):reasons.append('REMOTE_CONTRACT_OR_RELEASE_INCOMPATIBLE')
        if left and right and mapping['transport']=='KAFKA':
            x,y=left[0]['attributes'],right[0]['attributes']
            if x['broker_realm']!=y['broker_realm'] or sorted(x['topics'])!=sorted(y['topics']):reasons.append('REMOTE_BROKER_OR_TOPIC_MISMATCH')
        if reasons:
            row['unresolved_mapping_ids'].append(mapping['id']);row['reasons']+=reasons
            continue
        source_node,source_doc=left;target_node,target_doc=right
        row['execution_intent']=source_node['attributes'].get('execution_status','ASYNC_DECLARATION' if mapping['transport']=='KAFKA' else 'UNKNOWN')
        row['candidates'].append({'target_interface_id':target['interface_id'],'target_service_id':target['service_id'],
            'target_release_id':target['id'],'mapping_id':mapping['id'],'compatibility_id':mapping['compatibility_id'],
            'compatibility':'EXACT_DECLARATION' if mapping['compatibility_id'] is None else 'EXPLICIT_PAIRED_DECLARATION',
            'transition_kind':'HTTP_REQUEST_RESPONSE' if mapping['transport']=='HTTP' else 'ASYNC_PUBLISH_SUBSCRIBE',
            'scope':scope,'context_ids':sorted({source['context_id'],target['context_id']}),
            'source_contract':deepcopy(a),'target_contract':deepcopy(b),
            'evidence_refs':sorted(set(source_node['evidence_refs'])|set(target_node['evidence_refs'])),
            'evidence_kinds':sorted(set(source_node['evidence_kinds'])|set(target_node['evidence_kinds'])),
            'freshness':'CAPTURE_TIME_ONLY','consumer_group':target_node['attributes'].get('consumer_group')})
    for row in rows.values():
        candidates=sorted(row['candidates'],key=lambda c:(c['target_interface_id'],c['target_release_id'],c['mapping_id']))
        row['candidates']=candidates;row['mapping_ids'].sort();row['unresolved_mapping_ids'].sort();row['reasons']=sorted(set(row['reasons']))
        distinct={(c['target_interface_id'],c['target_release_id']) for c in candidates}
        row['resolution_status']='AMBIGUOUS' if len(distinct)>1 else 'RESOLVED' if distinct and not row['unresolved_mapping_ids'] else 'UNRESOLVED'
        if row['unresolved_mapping_ids']:row['reasons'].append('REMOTE_CANDIDATE_SET_INCOMPLETE')
    return {'schema_version':1,'rule_version':VERSION,'input_hash':captured['capture_id'],
        'bindings':[rows[k] for k in sorted(rows)],'diagnostics':diagnostics,
        'coverage':{'status':'PARTIAL' if rows else 'UNKNOWN','omitted_mapping_ids':[],'truncated':False},
        'authority':'LOCAL_CAPTURE_HANDOFF_ONLY','freshness':'CAPTURE_TIME_ONLY'}
