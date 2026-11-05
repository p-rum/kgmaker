"""T018 snapshot provenance and explicit, confined source-hash observations."""
from collections import deque
from copy import deepcopy
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import stat
import unicodedata

from .analysis_model import canonical, safe_path
from .architecture_model import ViewDocument
from .model import KnowledgeGraph
from .remote_mapping import _bounded, _graph, _workspace, digest
from .remote_interfaces import _ref as _base_ref
from .service_topology import aggregate_service_topology
from .topology_filter import filter_topology
from .workspace import split_id, qualified
from .process_triggers import _canonical_symbol

VERSION = 'view-explanation-1'
STATUS_VERSION = 'view-source-status-1'
_MAX_REFS = 10000
_MAX_REPORT_CHARS = 4_000_000
_MAX_SOURCE_FILES = 256
_MAX_FILE_BYTES = 2_000_000
_MAX_TOTAL_BYTES = 8_000_000
_HASH = re.compile(r'[0-9a-f]{64}\Z')


class ViewExplanationError(ValueError):
    def __init__(self, code):
        self.diagnostic={'code':code}
        super().__init__(code)


def _fail(code):
    raise ViewExplanationError(code) from None


def _ref(value):
    if type(value) is not str:_fail('EXPLAIN_UNSAFE_REFERENCE')
    # Namespace decoding is for privacy only; it never locates a source.
    parts=[value]
    if value.startswith('repo:'):
        repo,local=split_id(value);parts.extend([repo,local])
    for part in parts:
        if not part or len(part)>4096:_fail('EXPLAIN_UNSAFE_REFERENCE')
        if (re.search(r'(?i)(://|//[^/\s]*@|\b(?:Basic|Bearer)\s+\S+)',part)
                or any(unicodedata.category(c) in {'Cc','Cf','Cs','Zl','Zp'} for c in part)):
            _fail('EXPLAIN_UNSAFE_REFERENCE')
        try:_base_ref(part)
        except ValueError:
            # An existing JVM field ID contains name:descriptor. A field named
            # password is a typed identifier, not a password assignment/value.
            # This lexical exception grants no locator or evidence authority.
            if re.fullmatch(r'.*:field:[^:\s]+:(?:\[*[ZBCSIJFD]|\[*L[^;:\s]+;)',part) is None:
                _fail('EXPLAIN_UNSAFE_REFERENCE')
    return value


def _refs(values):
    if not isinstance(values,(list,tuple)):_fail('EXPLAIN_INVALID_REFERENCE_LIST')
    return tuple(sorted({_ref(value) for value in values}))


def _sha(value):
    if type(value) is not str or not _HASH.fullmatch(value):_fail('EXPLAIN_INVALID_HASH')
    return value


def _original(captured, graph=None):
    view=aggregate_service_topology(captured)
    if graph is not None:
        if not isinstance(graph,KnowledgeGraph):_fail('EXPLAIN_INVALID_GRAPH')
        if digest(_graph(graph))!=captured['input_binding']['graph_fingerprint']:_fail('EXPLAIN_GRAPH_MISMATCH')
        graph=KnowledgeGraph.from_dict(graph.to_dict())
    return view,graph


def _view(view,captured,filtering):
    original=aggregate_service_topology(captured)
    expected=original
    if filtering is not None:
        if (not isinstance(filtering,dict) or set(filtering)!={'schema_version','rules_version','document','filtering'}
                or not isinstance(filtering['filtering'],dict) or not isinstance(filtering['filtering'].get('criteria'),dict)):
            _fail('EXPLAIN_INVALID_FILTER')
        criteria=filtering['filtering']['criteria']
        if set(criteria)!={'focus_service','direction','max_hops','max_nodes','relations','scope','context_ids'}:_fail('EXPLAIN_INVALID_FILTER')
        rebuilt=filter_topology(original,**criteria)
        if canonical(rebuilt)!=canonical(filtering):_fail('EXPLAIN_FILTER_MISMATCH')
        expected=ViewDocument.from_dict(rebuilt['document'])
    document=view if isinstance(view,ViewDocument) else ViewDocument.from_dict(view)
    if document.to_dict(include_generation_metadata=False)!=expected.to_dict(include_generation_metadata=False):
        _fail('EXPLAIN_VIEW_MISMATCH')
    return document,original


def _selected(captured):
    selected=set()
    selection=captured['actual_selection']
    for value in selection.get('services',{}).values():
        for row in value.get('contexts',[]):
            if row.get('context_id') is not None:selected.add(_ref(row['context_id']))
    return selected


def _path(value,repo):
    value=_ref(value)
    prefix='@'+repo+'/'
    if not value.startswith(prefix):_fail('EXPLAIN_FOREIGN_SOURCE')
    relative=value[len(prefix):]
    path=PurePosixPath(relative)
    if (not relative or path.is_absolute() or '..' in path.parts or '\\' in relative
            or ':' in relative or str(path)!=relative):_fail('EXPLAIN_UNSAFE_SOURCE_PATH')
    return relative


def _range(value):
    if value is None:return None,'RANGE_UNAVAILABLE'
    if not isinstance(value,dict):return None,'RANGE_UNAVAILABLE'
    keys={'start','end','start_line','end_line','start_column','end_column'}
    if any(type(v) is not int or v<0 for k,v in value.items() if k in keys):return None,'RANGE_UNAVAILABLE'
    if (type(value.get('start_line')) is not int or value['start_line']<1
            or type(value.get('end_line')) is not int or value['end_line']<value['start_line']):return None,'RANGE_UNAVAILABLE'
    if ('start' in value)!=('end' in value):return None,'RANGE_UNAVAILABLE'
    if 'start' in value and value['start']>value['end']:return None,'RANGE_UNAVAILABLE'
    return {k:value[k] for k in keys if k in value},'CAPTURED_RANGE'


def _graph_index(graph,captured):
    # Ephemeral exact-ID lookups only, not discovery or a persisted catalog.
    result={'selected':_selected(captured)}
    for name,values in [('nodes',graph.nodes),('symbols',graph.symbols),('sites',graph.call_sites),('contexts',graph.contexts)]:
        rows={}
        for value in values:
            identity=value.id if name=='nodes' else value['id']
            rows.setdefault(identity,[]).append(value)
        result[name]=rows
    return result


def _locator(graph,captured,ref,index=None):
    """Only exact public canonical source occurrences, never ID/name parsing."""
    index=_graph_index(graph,captured) if index is None else index
    nodes=index['nodes'].get(ref,[])
    if len(nodes)!=1:return None,'SOURCE_LOCATOR_UNAVAILABLE'
    node=nodes[0]
    if not ref.startswith('repo:'):return None,'SOURCE_NAMESPACE_UNAVAILABLE'
    repo,_=split_id(ref)
    symbols=index['symbols'].get(ref,[]);sites=index['sites'].get(ref,[])
    records=symbols+sites
    if len(records)!=1:return None,'CANONICAL_SOURCE_RECORD_UNAVAILABLE'
    record=records[0];cid=record.get('context_id')
    if cid not in index['selected']:return None,'SOURCE_CONTEXT_NOT_SELECTED'
    contexts=index['contexts'].get(cid,[])
    if len(contexts)!=1:return None,'SOURCE_CONTEXT_UNAVAILABLE'
    context=contexts[0]
    if (context.get('repo_id')!=repo or node.scope!=context.get('scope')
            or node.scope!=captured['input_binding']['scope'] or context.get('mode') not in {'BUILD_IMPORT','BUILD_EXECUTE'}):
        return None,'SOURCE_REALM_OR_SCOPE_UNPROVEN'
    path=record.get('path');checksum=record.get('sha256')
    if path!=node.path or type(checksum) is not str or not _HASH.fullmatch(checksum):return None,'SOURCE_HASH_UNAVAILABLE'
    relative=_path(path,repo)
    if (graph.files.get(path)!=checksum or not isinstance(context.get('source_files'),dict)
            or context['source_files'].get(path)!=checksum):return None,'SOURCE_SNAPSHOT_HASH_MISMATCH'
    metadata=node.metadata or {}
    if symbols:
        if not _canonical_symbol(record,node,context):return None,'CANONICAL_SOURCE_TUPLE_MISMATCH'
        if any(metadata.get(k)!=record.get(k) for k in ('name','kind','owner','descriptor','sha256')):
            return None,'CANONICAL_SOURCE_TUPLE_MISMATCH'
    else:
        span=record.get('range')
        for key,expected in [('id',ref),('context_id',cid),('path',path),('scope',node.scope)]:
            value=metadata.get(key)
            if value is None:continue
            if type(value) is not str:return None,'CANONICAL_SOURCE_TUPLE_MISMATCH'
            matches=value==expected
            if key in {'id','context_id'}:matches=matches or qualified(repo,value)==expected
            if key=='path':matches=matches or '@'+repo+'/'+value==expected
            if not matches:return None,'CANONICAL_SOURCE_TUPLE_MISMATCH'
        if (node.kind!='call_site' or record.get('scope')!=node.scope or not isinstance(span,dict)
                or metadata.get('sha256')!=checksum or metadata.get('range')!=span):
            return None,'CANONICAL_SOURCE_TUPLE_MISMATCH'
        caller=record.get('caller')
        if not isinstance(caller,str) or not caller.startswith('repo:') or split_id(caller)[0]!=repo:
            return None,'CANONICAL_SOURCE_TUPLE_MISMATCH'
        caller_nodes=index['nodes'].get(caller,[]);caller_records=index['symbols'].get(caller,[])
        caller_node=caller_nodes[0] if len(caller_nodes)==1 else None
        caller_record=caller_records[0] if len(caller_records)==1 else None
        if (caller_node is None or caller_record is None or caller_record.get('context_id')!=cid
                or caller_record.get('path')!=path or caller_record.get('sha256')!=checksum
                or not _canonical_symbol(caller_record,caller_node,context)):
            return None,'CANONICAL_SOURCE_TUPLE_MISMATCH'
        if (type(span.get('start')) is not int or type(span.get('end')) is not int
                or qualified(repo,'call:'+split_id(caller)[1]+':'+checksum+':'+str(span['start'])+':'+str(span['end']))!=ref):
            return None,'CANONICAL_SOURCE_TUPLE_MISMATCH'
    if symbols and metadata.get('range') is not None and metadata['range']!=record.get('range'):
        return None,'CANONICAL_SOURCE_RANGE_MISMATCH'
    span,range_status=_range(record.get('range') if metadata.get('range') is not None else None)
    return {'reference_id':ref,'repo_id':repo,'path':relative,'source_sha256':checksum,
        'context_id':_ref(cid),'scope':_ref(node.scope),'range':span,'range_status':range_status,
        'captured_context_freshness':_ref(context.get('freshness','UNKNOWN')),
        'authority':'CAPTURED_PUBLIC_GRAPH_TUPLE'},None


def _record_refs(value):
    refs=[]
    for key in ('original_ids','evidence_refs','source_refs','original_evidence_ids','compiler_evidence_ids',
                'evidence_ids','origin_interface_ids','origin_mapping_ids','origin_release_ids','origin_edge_ids','origin_binding_ids',
                'original_evidence_refs'):
        if key in value:refs.extend(_refs(value[key]))
    for key in ('source_id','target_id','source','target','original_id','compiler_symbol_id',
                'source_interface_id','target_interface_id','mapping_id','source_release_id','target_release_id','edge_id','interface_id','origin_id','origin_call_site','terminal_call_site',
                'caller','call_site_id','producer_site','consumer_site','declaration_id','request_definition_id'):
        if isinstance(value.get(key),str):refs.append(_ref(value[key]))
    for key in ('origin_candidates','candidates','unresolved_selectors'):
        if key in value:
            if not isinstance(value[key],list):_fail('EXPLAIN_INVALID_EXPANSION')
            for row in value[key]:
                if not isinstance(row,dict):_fail('EXPLAIN_INVALID_EXPANSION')
                refs.extend(_record_refs(row))
    return refs


def _statuses(source_status,graph,captured):
    if source_status is None:return {}
    fields={'schema_version','rules_version','capture_id','graph_fingerprint','manifest_sha256',
            'workspace_fingerprint','reference_ids','locators','status_id'}
    if graph is None or not isinstance(source_status,dict) or set(source_status)!=fields:_fail('EXPLAIN_INVALID_SOURCE_STATUS')
    if (type(source_status['schema_version']) is not int or source_status['schema_version']!=1
            or source_status['rules_version']!=STATUS_VERSION or source_status['capture_id']!=captured['capture_id']
            or source_status['graph_fingerprint']!=captured['input_binding']['graph_fingerprint']
            or source_status['manifest_sha256']!=captured['manifest_sha256']
            or source_status['workspace_fingerprint']!=captured['input_binding']['workspace_fingerprint']
            or source_status['status_id']!=digest({k:v for k,v in source_status.items() if k!='status_id'})):
        _fail('EXPLAIN_SOURCE_STATUS_MISMATCH')
    refs=_refs(source_status['reference_ids'])
    if len(refs)>_MAX_SOURCE_FILES or list(refs)!=source_status['reference_ids'] or not isinstance(source_status['locators'],list):
        _fail('EXPLAIN_INVALID_SOURCE_STATUS')
    result={};index=_graph_index(graph,captured)
    for row in source_status['locators']:
        if not isinstance(row,dict):_fail('EXPLAIN_INVALID_SOURCE_STATUS')
        base,reason=_locator(graph,captured,row.get('reference_id'),index)
        if base is None or set(row)!=set(base)|{'current_sha256','status'} or any(row[k]!=v for k,v in base.items()):
            _fail('EXPLAIN_SOURCE_STATUS_MISMATCH')
        ref=base['reference_id'];current=row['current_sha256'];status=row['status']
        if ref not in refs or ref in result:_fail('EXPLAIN_SOURCE_STATUS_MISMATCH')
        if current is not None:_sha(current)
        if (status not in {'CONTENT_MATCH','SOURCE_STALE','SOURCE_MISSING','SOURCE_UNAVAILABLE'}
                or status=='CONTENT_MATCH' and current!=base['source_sha256']
                or status=='SOURCE_STALE' and (current is None or current==base['source_sha256'])
                or status in {'SOURCE_MISSING','SOURCE_UNAVAILABLE'} and current is not None):
            _fail('EXPLAIN_SOURCE_STATUS_MISMATCH')
        result[ref]=deepcopy(row)
    if set(result)!=set(refs):_fail('EXPLAIN_SOURCE_STATUS_MISMATCH')
    return result


def explain_view_element(view,element_id,*,captured,graph=None,filtering=None,source_status=None):
    """Pure explanation of the original supplied snapshot; no current reads."""
    try:return _explain(view,element_id,captured,graph,filtering,source_status)
    except ViewExplanationError:raise
    except (ValueError,TypeError,KeyError,AttributeError,RecursionError,OverflowError):_fail('EXPLAIN_INVALID_INPUT')


def _explain(view,element_id,captured,graph,filtering,source_status):
    _bounded((view,element_id,captured,graph,filtering,source_status));element_id=_ref(element_id)
    document,original=_view(view,captured,filtering);_,graph=_original(captured,graph)
    statuses=_statuses(source_status,graph,captured)
    element=next((x for x in (*document.nodes,*document.edges) if x.id==element_id),None)
    report={'schema_version':1,'rules_version':VERSION,'status':'EXPLAINED' if element else 'UNKNOWN_ELEMENT',
        'view_id':document.view_id,'element_id':element_id,'view_fingerprint':document.content_fingerprint,
        'baseline_fingerprint':document.baseline_fingerprint,'capture_id':captured['capture_id'],
        'graph_fingerprint':captured['input_binding']['graph_fingerprint'],
        'original_topology_fingerprint':original.content_fingerprint,
        'aggregation_rule':original.rules_version,'filtering_rule':filtering['rules_version'] if filtering else None,
        'scope':document.scope,'selection_fingerprints':{'requested':digest(captured['remote_selection']),
            'actual':digest(captured['actual_selection'])},'graph_status':'BOUND_PUBLIC_SNAPSHOT' if graph is not None else 'NOT_SUPPLIED',
        'source_status_authority':'SUPPLIED_LOCAL_CAPTURE_HANDOFF' if source_status is not None else 'NOT_SUPPLIED',
        'source_status_fingerprint':source_status['status_id'] if source_status is not None else None,
        'current_source_status':'NOT_CHECKED','origin_interface_ids':[],'mapping_ids':[], 'release_ids':[],
        'expanded_reference_ids':[],'evidence':[],'provenance':[],'source_locators':[],'unavailable_references':[],
        'coverage_status':document.coverage['status'],'truncated':document.coverage.get('truncated') is True,
        'limitations':['Captured reference chain only; no compiler, runtime, deployment or payload promotion.',
            'Source status is optional explicit local hash observation, not whole-context freshness.']}
    if filtering is not None:
        source=filtering['filtering'];report['filtering']={k:source[k] for k in ('fingerprint','status','truncated','upstream_truncated','omission_inventory_complete')}
        for key in ('omitted_node_ids','omitted_edge_ids','omitted_original_interface_ids','omitted_mapping_ids','omitted_release_ids','omitted_original_ids'):
            report['filtering'][key]=list(_refs(source[key]))
    if element is None:return _finish(report)
    for field in ('broker_realm','topic','consumer_group','capture_freshness','runtime_availability',
                  'payload_compatibility','runtime_execution','delivery','deployment'):
        if element.attributes.get(field) is not None:report[field]=_ref(element.attributes[field])
    report.update(resolution_status=element.resolution_status,freshness=element.freshness,
        context_ids=list(_refs(element.attributes.get('context_ids',[]))))
    for target,field in [('origin_interface_ids','origin_interface_ids'),('mapping_ids','origin_mapping_ids'),('release_ids','origin_release_ids')]:
        report[target]=list(_refs(element.attributes.get(field,[])))
    records={};provenance={}
    for value in (original.to_dict(),captured['data_document'],captured['remote_document']):
        for row in [*value['nodes'],*value['edges']]:
            key=_ref(row['id']);records.setdefault(key,[]).append(row)
        for proof in value['provenance']:provenance.setdefault(_ref(proof['id']),[]).append(proof)
    if graph is not None:
        for row in graph.evidence:provenance.setdefault(_ref(row['id']),[]).append(row)
    interfaces=set(report['origin_interface_ids']);mappings=set(report['mapping_ids']);releases=set(report['release_ids'])
    for release in captured['release_bindings']:
        records.setdefault(release['id'],[]).append({'id':release['id'],'attributes':{'interface_id':release['interface_id']}})
    index=_graph_index(graph,captured) if graph is not None else None
    queue=deque([element_id]);visited=set();locators={};unavailable={}
    while queue:
        ref=queue.popleft()
        if ref in visited:continue
        visited.add(ref)
        if len(visited)>_MAX_REFS:_fail('EXPLAIN_REFERENCE_LIMIT')
        found=False
        for row in records.get(ref,[]):
            found=True;queue.extend(_record_refs(row));attrs=row.get('attributes',{});queue.extend(_record_refs(attrs))
            interfaces.update(_refs(attrs.get('origin_interface_ids',[])));mappings.update(_refs(attrs.get('origin_mapping_ids',[])))
            releases.update(_refs(attrs.get('origin_release_ids',[])))
            if attrs.get('source_release_id') is not None:releases.add(_ref(attrs['source_release_id']))
            for candidate in attrs.get('candidates',[]):
                interfaces.add(_ref(candidate['target_interface_id']));mappings.add(_ref(candidate['mapping_id']))
                releases.add(_ref(candidate['target_release_id']))
            if row.get('evidence_refs'):
                report['evidence'].append({'owner_id':ref,'evidence_refs':list(_refs(row['evidence_refs'])),
                    'supporting_refs':list(_refs(row.get('supporting_refs',[]))),
                    'contradicting_refs':list(_refs(row.get('contradicting_refs',[]))),
                    'unknown_refs':list(_refs(row.get('unknown_refs',[]))),
                    'evidence_kinds':list(_refs(row.get('evidence_kinds',[]))),
                    'freshness':_ref(row.get('freshness','UNKNOWN')),
                    'context_ids':list(_refs(row.get('attributes',{}).get('context_ids',[])))})
        for proof in provenance.get(ref,[]):
            found=True;queue.extend(_record_refs(proof))
            kind=proof.get('evidence_kind',proof.get('kind','UNKNOWN'))
            freshness=proof.get('freshness','UNKNOWN');polarity=proof.get('polarity','UNKNOWN')
            report['provenance'].append({'reference_id':ref,
                'evidence_kind':kind if type(kind) is str and kind in {'SOURCE_ONLY','SYMBOL_RESOLVED','FRAMEWORK_DERIVED','RUNTIME_OBSERVED','UNRESOLVED','UNKNOWN','SYNTAX_CANDIDATE','DISPATCH_CANDIDATE'} else 'UNKNOWN',
                'freshness':freshness if type(freshness) is str and freshness in {'CURRENT','STALE','UNKNOWN'} else 'UNKNOWN',
                'polarity':polarity if type(polarity) is str and polarity in {'SUPPORTING','CONTRADICTING','UNKNOWN'} else 'UNKNOWN',
                'context_ids':list(_refs(proof.get('context_ids',[]))),
                'scope':_ref(proof['scope']) if proof.get('scope') is not None else None,
                'original_payload_hash':digest(proof)})
        if graph is not None:
            graph_nodes=index['nodes'].get(ref,[])
            if len(graph_nodes)==1 and graph_nodes[0].kind in {'http_request_definition','http_execution_intent',
                    'kafka_code_producer','kafka_code_listener','orm_attribute','orm_association'}:
                queue.extend(_record_refs(graph_nodes[0].metadata or {}))
            locator,reason=_locator(graph,captured,ref,index)
            if locator:
                found=True
                locators[ref]={**locator,'current_sha256':None,'status':'NOT_CHECKED'}
                if ref in statuses:locators[ref]=statuses[ref]
            elif not found:unavailable[ref]=reason
        elif not found:unavailable[ref]='ORIGINAL_GRAPH_NOT_SUPPLIED'
    report['expanded_reference_ids']=sorted(visited)
    report.update(origin_interface_ids=sorted(interfaces),mapping_ids=sorted(mappings),release_ids=sorted(releases))
    unique={digest(row):row for row in report['evidence']}
    report['evidence']=[unique[k] for k in sorted(unique)]
    unique={digest(row):row for row in report['provenance']}
    report['provenance']=[unique[k] for k in sorted(unique)]
    report['source_locators']=[locators[k] for k in sorted(locators)]
    report['unavailable_references']=[{'reference_id':k,'reason':unavailable[k]} for k in sorted(unavailable)]
    observed={row['status'] for row in locators.values() if row['status']!='NOT_CHECKED'}
    if observed:report['current_source_status']=next(iter(observed)) if len(observed)==1 else 'MIXED_SOURCE_STATUS'
    return _finish(report)


def _finish(report):
    _bounded(report)
    if len(canonical(report))>_MAX_REPORT_CHARS:_fail('EXPLAIN_REPORT_LIMIT')
    return report


def _read_hash(root,relative,budget):
    # Shared confinement rejects traversal and symlinks; open each component
    # relative to a directory descriptor with NOFOLLOW to retain confinement
    # if a path changes after validation. No plaintext leaves this helper.
    safe_path(root,relative)
    if not hasattr(os,'O_NOFOLLOW') or not hasattr(os,'O_DIRECTORY'):return None,'SOURCE_UNAVAILABLE',0
    directory=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    handle=None
    try:
        parts=PurePosixPath(relative).parts
        for part in parts[:-1]:
            child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=directory)
            os.close(directory);directory=child
        handle=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|getattr(os,'O_NONBLOCK',0),dir_fd=directory)
        info=os.fstat(handle)
        if not stat.S_ISREG(info.st_mode) or info.st_size>min(_MAX_FILE_BYTES,budget):return None,'SOURCE_UNAVAILABLE',0
        chunks=[];size=0;limit=min(_MAX_FILE_BYTES,budget)
        while True:
            chunk=os.read(handle,min(65536,limit-size+1))
            if not chunk:break
            chunks.append(chunk);size+=len(chunk)
            if size>limit:return None,'SOURCE_UNAVAILABLE',0
        after=os.fstat(handle)
        if (info.st_size,info.st_mtime_ns,info.st_ino)!=(after.st_size,after.st_mtime_ns,after.st_ino):
            return None,'SOURCE_UNAVAILABLE',size
        return hashlib.sha256(b''.join(chunks)).hexdigest(),None,size
    finally:
        if handle is not None:os.close(handle)
        os.close(directory)


def capture_explanation_source_status(workspace,graph,*,captured,reference_ids):
    """Explicit local hash-only I/O, derived only from bound selected graph refs."""
    from .workspace import load_workspace
    try:
        _bounded((workspace,graph,captured,reference_ids));_,graph=_original(captured,graph)
        refs=_refs(reference_ids)
        if graph is None or len(refs)>_MAX_SOURCE_FILES:_fail('EXPLAIN_SOURCE_REFERENCE_LIMIT')
        if not isinstance(workspace,dict):_fail('EXPLAIN_INVALID_WORKSPACE')
        manifest=Path(workspace['_manifest_path'])
        if not manifest.is_absolute():_fail('EXPLAIN_INVALID_WORKSPACE')
        safe_path(Path(manifest.anchor),'/'.join(manifest.parts[1:]))
        manifest_hash,manifest_status,_=_read_hash(manifest.parent,manifest.name,_MAX_FILE_BYTES)
        if manifest_status is not None or manifest_hash!=captured['manifest_sha256']:_fail('EXPLAIN_WORKSPACE_MISMATCH')
        loaded=load_workspace(manifest)
        fingerprint=captured['input_binding']['workspace_fingerprint']
        if (digest(_workspace(workspace))!=fingerprint or digest(_workspace(loaded))!=fingerprint
                or loaded['_manifest_hash']!=captured['manifest_sha256']):_fail('EXPLAIN_WORKSPACE_MISMATCH')
        roots={r['id']:Path(r['_root']) for r in loaded['repositories']}
        locators=[];total=0;index=_graph_index(graph,captured)
        # Validate EVERY requested locator before any source reads.
        for ref in refs:
            locator,reason=_locator(graph,captured,ref,index)
            if locator is None:_fail('EXPLAIN_SOURCE_REFERENCE_UNAVAILABLE')
            if locator['repo_id'] not in roots:_fail('EXPLAIN_FOREIGN_SOURCE')
            safe_path(roots[locator['repo_id']],locator['path'])
            locators.append(locator)
        result=[]
        for locator in locators:
            try:
                current,status,size=_read_hash(roots[locator['repo_id']],locator['path'],_MAX_TOTAL_BYTES-total)
                total+=size
                status=status or ('CONTENT_MATCH' if current==locator['source_sha256'] else 'SOURCE_STALE')
            except FileNotFoundError:current=None;status='SOURCE_MISSING'
            except (OSError,ValueError):current=None;status='SOURCE_UNAVAILABLE'
            result.append({**locator,'current_sha256':current,'status':status})
        manifest_hash,manifest_status,_=_read_hash(manifest.parent,manifest.name,_MAX_FILE_BYTES)
        if manifest_status is not None or manifest_hash!=captured['manifest_sha256']:_fail('EXPLAIN_WORKSPACE_CHANGED')
        value={'schema_version':1,'rules_version':STATUS_VERSION,'capture_id':captured['capture_id'],
            'graph_fingerprint':captured['input_binding']['graph_fingerprint'],
            'manifest_sha256':captured['manifest_sha256'],'workspace_fingerprint':fingerprint,
            'reference_ids':list(refs),'locators':result}
        value['status_id']=digest(value)
        return value
    except ViewExplanationError:raise
    except (ValueError,TypeError,KeyError,OSError,AttributeError,RecursionError,OverflowError):_fail('EXPLAIN_SOURCE_CAPTURE_UNAVAILABLE')
