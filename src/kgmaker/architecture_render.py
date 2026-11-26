"""Pure bounded views of existing interface and topology snapshots."""
import hashlib
import json
import math
import re
import unicodedata

from .architecture_model import ViewDocument,ViewNode,ViewEdge
from .analysis_model import canonical
from .view_explanation import _ref
from .remote_interfaces import _refs
from .topology_filter import _contexts
from .architecture_render_common import InterfaceMarkdownError,_fail,_bounded,_identity,_MAX_ITEMS,_MAX_CHARS
from .architecture_cli import _safe_output

_MAX_OUTPUT_BYTES=4000000








def _text(value):
    if value is None:return 'UNKNOWN'
    if type(value) is bool:return 'true' if value else 'false'
    if type(value) not in (str,int,float):_fail()
    result=[]
    value=str(value).replace('\r\n','\n').replace('\r','\n')
    for char in value:
        if char in '\n\t\u2028\u2029':result.append(' ⏎ ' if char!='\t' else ' ⇥ ')
        elif unicodedata.category(char) in {'Cc','Cf'}:result.append('⟦U+'+format(ord(char),'04X')+'⟧')
        elif char=='&':result.append('&amp;')
        elif char=='<':result.append('&lt;')
        elif char=='>':result.append('&gt;')
        elif char in ':.@':result.append('&#'+str(ord(char))+';')
        elif char in '\\`|[]()*_!#{}~':result.append('\\'+char)
        else:result.append(char)
    return ''.join(result)


def _values(value):
    if value is None:return 'UNKNOWN'
    if not isinstance(value,(list,tuple)):_fail()
    return ', '.join(_text(v) for v in sorted(value,key=lambda v:str(v))) if value else 'NONE'




def _anchor(identity,role='item'):
    material=identity if role=='item' else role+'\0'+identity
    return 'evidence-'+hashlib.sha256(material.encode('utf-8')).hexdigest()


def _protocol(node):
    return node.attributes.get('protocol') or {'http_interface':'HTTP','kafka_interface':'KAFKA'}.get(node.kind,'UNKNOWN')


def _service(node):
    return node.attributes.get('service_id') or node.owner_id or 'UNKNOWN'


def _sort(node):
    return tuple(str(v) for v in (_service(node),node.attributes.get('direction') or 'UNKNOWN',_protocol(node),node.id))


def render_interface_markdown(document):
    """Render supplied static public evidence; never attest the current checkout."""
    try:return _render(document)
    except InterfaceMarkdownError:raise
    except (ValueError,TypeError,KeyError,AttributeError,RecursionError,OverflowError,UnicodeError):_fail()


class TopologyMermaidError(ValueError):
    """Invalid or unsafe topology Mermaid input."""

    def __init__(self, code='INVALID_TOPOLOGY_MERMAID'):
        self.code=code
        super().__init__(code)


def _topology_fail(code='INVALID_TOPOLOGY_MERMAID'):
    raise TopologyMermaidError(code) from None


def _mermaid_text(value):
    if value is None:return 'UNKNOWN'
    if type(value) not in (str,int,float,bool):_topology_fail()
    if type(value) is bool:return 'true' if value else 'false'
    value=str(value).replace('\r\n','\n').replace('\r','\n')
    output=[]
    for char in value:
        if char=='\n':output.append(' ⏎ ')
        elif char=='\t':output.append(' ⇥ ')
        elif unicodedata.category(char) in {'Cc','Cf'}:output.append('⟦U+'+format(ord(char),'04X')+'⟧')
        elif char=='&':output.append('#amp;')
        elif char=='<':output.append('#lt;')
        elif char=='>':output.append('#gt;')
        elif char=='"':output.append('#quot;')
        elif char=='%':output.append('#37;')
        else:output.append(char)
    return ''.join(output)


def _mermaid_json(value):
    """Preserve a JSON comment payload without raw HTML/script delimiters."""
    return (json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
            .replace('&','\\u0026').replace('<','\\u003c').replace('>','\\u003e')
            .replace('%','\\u0025')
            .replace('\u2028','\\u2028').replace('\u2029','\\u2029'))


def _topology_node_identity(node,scope):
    logical=node.attributes.get('logical_id')
    if type(logical) is not str or not logical:return node.id
    realm={key:node.attributes[key] for key in ('realm','broker_realm','workspace_id','repository_id')
           if key in node.attributes and node.attributes[key] is not None}
    contexts=node.attributes.get('context_ids',())
    if not isinstance(contexts,(list,tuple)):_topology_fail()
    identity={'logical_id':logical,'realm':realm,'scope':node.attributes.get('scope',scope),
              'context_ids':sorted(set(contexts)),'owner_id':node.owner_id}
    return json.dumps(identity,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)


def _topology_relation(edge):
    names={
        'remote_http_request_response':'HTTP request/response',
        'publishes_to_channel':'Publishes to channel',
        'consumes_from_channel':'Consumes from channel',
        'reads':'Reads resource',
        'writes':'Writes resource',
        'depends_on':'Depends on',
    }
    relation=edge.relation
    label=names.get(relation,'UNKNOWN relation: '+relation)
    attrs=edge.attributes
    async_relation=(attrs.get('async') is True or relation in {'publishes_to_channel','consumes_from_channel'}
                    or attrs.get('execution_kind')=='ASYNC')
    if async_relation:label+='; ASYNC; delivery UNKNOWN'
    elif edge.resolution_status in {'UNRESOLVED','AMBIGUOUS'}:label+='; execution UNKNOWN'
    if edge.freshness!='CURRENT':label+='; freshness '+edge.freshness
    return label,async_relation


def _topology_snapshot(value):
    if type(value) not in (dict,ViewDocument):_topology_fail()
    _bounded(value)
    if type(value) is ViewDocument:
        raw={'document':value.to_dict(include_generation_metadata=False)}
        is_envelope=False
    else:
        raw=value
        is_envelope='document' in raw
    if 'document' in raw:
        if is_envelope:
            if set(raw)-{'schema_version','rules_version','document','filtering'}:
                _topology_fail()
            if 'filtering' not in raw or not isinstance(raw['filtering'],dict):_topology_fail()
            filtering=raw['filtering']
            required={'schema_version','rules_version','document','filtering'}
            if (set(raw)!=required or type(raw['schema_version']) is not int or raw['schema_version']!=1
                    or raw['rules_version']!='topology-filter-1'):
                _topology_fail()
        else:filtering=None
    else:
        filtering=None
        raw={'document':raw}
    view=ViewDocument.from_dict(raw['document'])
    if view.kind!='topology':_topology_fail()
    criteria = filtering.get('criteria', {}) if filtering is not None else {}
    if not isinstance(criteria, dict):
        _topology_fail()
    if criteria.get('scope', view.scope) != view.scope:
        _topology_fail('TOPOLOGY_MERMAID_FOREIGN_SCOPE')
    contexts = criteria.get('context_ids')
    selected = set(_refs(contexts)) if contexts is not None else None
    visible_evidence_refs = set()
    for item in (*view.nodes, *view.edges):
        if item.attributes.get('scope', view.scope) not in (view.scope, 'unknown'):
            _topology_fail('TOPOLOGY_MERMAID_FOREIGN_SCOPE')
        if selected is not None and not selected.issuperset(_contexts(item)):
            _topology_fail('TOPOLOGY_MERMAID_FOREIGN_CONTEXT')
        visible_evidence_refs.update(item.evidence_refs)
    for proof in view.provenance:
        if proof['id'] not in visible_evidence_refs:
            # T017 retains proof records for the omitted frontier as well.
            continue
        if proof.get('scope') not in (None, view.scope, 'unknown'):
            _topology_fail('TOPOLOGY_MERMAID_FOREIGN_SCOPE')
        if selected is not None and not selected.issuperset(_refs(proof.get('context_ids', []))):
            _topology_fail('TOPOLOGY_MERMAID_FOREIGN_CONTEXT')
    normalized=view.to_dict(include_generation_metadata=False)
    envelope={**raw,'document':normalized}
    try:_safe_output(envelope)
    except ValueError:_topology_fail('UNSAFE_TOPOLOGY_MERMAID')
    return view, filtering, envelope


def _topology_diagram(view, filtering, envelope):
    node_ids={node.id:'n'+hashlib.sha256(_topology_node_identity(node,view.scope).encode('utf-8')).hexdigest()
              for node in view.nodes}
    if len(set(node_ids.values()))!=len(node_ids):
        _topology_fail('TOPOLOGY_MERMAID_ID_COLLISION')
    status=view.coverage.get('status','UNKNOWN')
    truncated=(view.coverage.get('truncated') is True or
               filtering is not None and filtering.get('truncated') is True)
    evidence=', '.join(sorted({kind for node in view.nodes for kind in node.evidence_kinds} |
                              {kind for edge in view.edges for kind in edge.evidence_kinds})) or 'UNKNOWN'
    title=('Service topology | Scope: '+view.scope+' | Evidence: '+evidence+
           ' | Coverage: '+str(status)+(' | TRUNCATED' if truncated else '')+
           ' | runtime/data availability: UNKNOWN | ordering/delivery: NOT_OBSERVED')
    lines=['---','title: '+json.dumps(title,ensure_ascii=False),'---','flowchart LR',
           '  %% topology-meta '+_mermaid_json(envelope)]
    node_by_id={node.id:node for node in view.nodes}
    for node in sorted(view.nodes,key=lambda item:item.id):
        kind={
            'service':'Service',
            'data_resource':'Resource',
            'database_resource':'Database resource',
            'unresolved_data_resource':'Unresolved data resource',
            'external_system':'External system',
            'kafka_channel':'Channel',
            'unresolved_topology_boundary':'Unresolved boundary',
        }.get(node.kind,'UNKNOWN node kind: '+node.kind)
        label=kind+' — '+node.label+'; '+node.resolution_status+'; '+node.freshness
        kinds=', '.join(sorted(node.evidence_kinds)) or 'UNKNOWN'
        label+='; evidence '+kinds
        lines.append('  %% topology-node '+_mermaid_json(node.to_dict()))
        lines.append('  '+node_ids[node.id]+'["'+_mermaid_text(label)+'"]')
    for edge in sorted(view.edges,key=lambda item:item.id):
        if edge.source not in node_ids or edge.target not in node_ids:_topology_fail('TOPOLOGY_MERMAID_DANGLING_ENDPOINT')
        label,async_relation=_topology_relation(edge)
        label+='; '+edge.resolution_status+'; '+edge.freshness
        lines.append('  %% topology-edge '+_mermaid_json(edge.to_dict()))
        arrow='-.->' if async_relation else '-->'
        lines.append('  '+node_ids[edge.source]+' '+arrow+'|"'+_mermaid_text(label)+'"| '+node_ids[edge.target])
    result='\n'.join(lines)+'\n'
    if len(result.encode('utf-8'))>_MAX_OUTPUT_BYTES:_topology_fail('TOPOLOGY_MERMAID_LIMIT')
    return result


def render_topology_mermaid(value):
    """Render a supplied T017 topology result as a pure, bounded Mermaid diagram.

    Node IDs are hashes of captured logical model IDs. Mermaid edge syntax has no
    emitted model edge ID here; comments retain each edge's original logical ID,
    and the visible endpoints preserve its relation without changing cardinality.
    The title carries scope/evidence/coverage without synthetic graph vertices.
    """
    try:
        return _topology_diagram(*_topology_snapshot(value))
    except TopologyMermaidError:raise
    except (ValueError,TypeError,KeyError,AttributeError,RecursionError,OverflowError,UnicodeError):
        _topology_fail()


def render_topology_markdown(value):
    """Display a captured topology and its boundaries without observing sources."""
    try:
        view, filtering, envelope = _topology_snapshot(value)
        return _topology_markdown(view, filtering, _topology_diagram(view, filtering, envelope))
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError, OverflowError, UnicodeError):
        raise ValueError('Invalid topology Markdown input') from None


def _topology_markdown(view, filtering, diagram):
    lines = []
    size = 0

    def add(line=''):
        nonlocal size
        size += len(line.encode('utf-8')) + 1
        if size > _MAX_OUTPUT_BYTES:
            raise ValueError('Topology Markdown output limit')
        lines.append(line)

    def cell(value):
        if isinstance(value, (list, tuple, dict)):
            value = canonical(value)
        return _text(value)

    def table(headers, rows):
        add('| ' + ' | '.join(headers) + ' |')
        add('| ' + ' | '.join('---' for _ in headers) + ' |')
        for row in rows:
            add('| ' + ' | '.join(cell(value) for value in row) + ' |')
        add()

    nodes = sorted(view.nodes, key=lambda node: node.id)
    edges = sorted(view.edges, key=lambda edge: edge.id)
    items = [*nodes, *edges]
    contexts = sorted({context for item in items for context in _contexts(item)})
    selection = filtering.get('criteria', {}).get('context_ids') if filtering is not None else None
    add('# Service topology')
    add()
    table(('Snapshot', 'Captured value'), (
        ('View ID', view.view_id), ('Content fingerprint', view.content_fingerprint),
        ('Baseline', view.baseline_fingerprint), ('Rules', view.rules_version), ('Scope', view.scope),
        ('Coverage', view.coverage['status']), ('Truncated', view.coverage.get('truncated')),
        ('Context filter', selection if selection is not None else 'All captured contexts'),
        ('Context IDs of retained elements', contexts), ('Source observation', 'NOT_CHECKED'),
    ))
    if selection is None:
        table(('Captured context selection', 'Value'), sorted(view.context_selection.items()))

    add('## Diagram')
    add()
    # The original diagram is byte-identical, including safe metadata comments.
    # A longer fence keeps any backtick runs in captured labels inside the diagram.
    longest_run = max((len(run[0]) for run in re.finditer(r'`+', diagram)), default=0)
    fence = '`' * max(3, longest_run + 1)
    add(fence + 'mermaid')
    add(diagram.removesuffix('\n'))
    add(fence)
    add()

    def node_rows(group):
        return ((node.id, node.attributes.get('logical_id'), node.label, node.kind, _contexts(node),
                 node.resolution_status, node.freshness, node.evidence_kinds) for node in group)

    node_headers = ('ID', 'Logical ID', 'Label', 'Kind', 'Contexts', 'Resolution', 'Freshness', 'Evidence kinds')
    add('## Service inventory')
    add()
    table(node_headers, node_rows(node for node in nodes if node.kind == 'service'))
    other_nodes = [node for node in nodes if node.kind != 'service']
    if other_nodes:
        add('## Other topology elements')
        add()
        table(node_headers, node_rows(other_nodes))
    add('## Relationships')
    add()
    table(('ID', 'Source', 'Target', 'Relation', 'Contexts', 'Resolution', 'Freshness', 'Evidence kinds'),
          ((edge.id, edge.source, edge.target, edge.relation, _contexts(edge), edge.resolution_status,
            edge.freshness, edge.evidence_kinds) for edge in edges))

    add('## Scope, limits and omitted boundaries')
    add()
    table(('Coverage field', 'Value'), sorted(view.coverage.items()))
    table(('Limit',), ((limit,) for limit in sorted(view.limits)))
    if filtering is None:
        add('Omission inventory unavailable in the captured view.')
        add()
    else:
        names = ('criteria', 'status', 'truncated', 'upstream_truncated', 'omission_inventory_complete',
                 'omitted_edge_ids', 'omitted_original_ids', 'omitted_original_interface_ids',
                 'omitted_mapping_ids', 'omitted_release_ids')
        table(('Filter inventory', 'Captured value'), ((name, filtering.get(name)) for name in names))
        reasons = {item['id']: item['reason'] for item in filtering.get('omitted_nodes', [])}
        table(('Omitted node ID', 'Captured reason'),
              ((identity, reasons.get(identity)) for identity in _refs(filtering.get('omitted_node_ids', []))))
        table(('Boundary ID', 'Reason', 'Anchor', 'Direction', 'Relation', 'Scope', 'Contexts',
               'Omitted nodes', 'Omitted edges', 'Evidence refs'),
              ((row['id'], row['reason'], row.get('anchor_id'), row.get('direction'), row.get('relation'),
                row.get('scope'), row.get('context_ids'), row.get('omitted_node_ids'), row.get('omitted_edge_ids'),
                row.get('evidence_refs')) for row in sorted(filtering.get('frontier', []), key=lambda row: row['id'])))
    table(('Diagnostic', 'Captured details'),
          ((row.get('code'), {key: value for key, value in row.items() if key != 'code'})
           for row in sorted(view.diagnostics, key=canonical)))

    add('## Sources and provenance')
    add()
    table(('Element ID', 'Original IDs', 'Supporting refs', 'Contradicting refs', 'Unknown refs'),
          ((item.id, item.original_ids, item.supporting_refs, item.contradicting_refs, item.unknown_refs)
           for item in items))
    proofs = {proof['id']: proof for proof in view.provenance}
    refs = sorted({ref for item in items for ref in item.evidence_refs})
    # T016 proof rows carry references and a payload hash, without T018's bound source locator.
    add(r'Source locations: SOURCE\_LOCATOR\_UNAVAILABLE in this topology capture.')
    add()
    table(('Evidence ID', 'Kind', 'Freshness', 'Polarity', 'Scope', 'Contexts', 'Source ID',
           'Source refs', 'Original payload hash'),
          ((proof['id'], proof['evidence_kind'], proof['freshness'], proof['polarity'], proof.get('scope'),
            proof.get('context_ids'), proof.get('source_id'), proof.get('source_refs'),
            proof.get('original_payload_hash')) for proof in (proofs[ref] for ref in refs)))
    return '\n'.join(lines) + '\n'


def _render(document):
    if type(document) not in (dict,ViewDocument):_fail()
    _bounded(document)
    data=document.to_dict(include_generation_metadata=False) if type(document) is ViewDocument else document
    view=ViewDocument.from_dict(data)
    if view.kind!='interfaces':_fail()
    # Existing T019 public-output privacy policy, without invoking its CLI path.
    try:_safe_output(view.to_dict(include_generation_metadata=False))
    except ValueError:_fail('UNSAFE_INTERFACE_MARKDOWN')
    _identity(view.view_id);_identity(view.scope);_identity(view.rules_version)
    for node in view.nodes:
        _identity(node.id)
        if node.attributes.get('scope',view.scope) not in (view.scope,'unknown'):_fail()
        if 'context_id' in node.attributes and node.attributes['context_id'] is not None:_identity(node.attributes['context_id'])
        if 'context_ids' in node.attributes:
            values=node.attributes['context_ids']
            if not isinstance(values,(list,tuple)):_fail()
            for value in values:_identity(value)
        if node.owner_id is not None:_identity(node.owner_id)
        for key in ('service_id','logical_id','origin_id','origin_call_site','terminal_call_site','request_definition_id','declaration_id','code_fact_id','subscription_id','subscription_logical_id','release_id','source_release_id','target_release_id','source_path'):
            if node.attributes.get(key) is not None:_identity(node.attributes[key])
        for key in ('handler_ids','request_type_ids','response_type_ids','message_type_ids'):
            if key in node.attributes:
                values=node.attributes[key]
                if not isinstance(values,(list,tuple)):_fail()
                for value in values:_identity(value)
        for ref in (*node.original_ids,*node.evidence_refs):_identity(ref)
    for edge in view.edges:
        for ref in (edge.id,edge.source,edge.target,*edge.original_ids,*edge.evidence_refs):_identity(ref)
    for proof in view.provenance:_identity(proof['id'])
    lines=[];size=0
    def add(line=''):
        nonlocal size
        size+=len((line+'\n').encode('utf-8'))
        if size>_MAX_OUTPUT_BYTES:_fail('INTERFACE_MARKDOWN_LIMIT')
        lines.append(line)
    def table(headers,rows):
        add('| '+' | '.join(headers)+' |');add('| '+' | '.join('---' for _ in headers)+' |')
        for row in rows:add('| '+' | '.join(row)+' |')
        add()
    def pair(name,value):add('- '+name+': '+_text(value))
    def link(identity,role='item'):return '[Evidence](#'+_anchor(identity,role)+')'
    add('# Interface catalog');add();add('## Snapshot');add()
    for label,value in [('View ID',view.view_id),('Content fingerprint',view.content_fingerprint),('Baseline',view.baseline_fingerprint),('Rules',view.rules_version),
                         ('Scope',view.scope),('Coverage',view.coverage['status'])]:pair(label,value)
    pair('Source observation','NOT_CHECKED');add()
    context_rows=[]
    def contexts(value,path=()):
        if isinstance(value,dict):
            for key in sorted(value):contexts(value[key],(*path,key))
        elif isinstance(value,(tuple,list)):
            for index,item in enumerate(value):contexts(item,(*path,str(index)))
        else:
            if path and path[-1]=='context_id' and value is not None:_identity(value)
            context_rows.append((_text(' / '.join(path)),_text(value)))
    contexts(view.context_selection)
    table(('Selected context field','Captured value'),context_rows or [('NONE','UNKNOWN')])
    for name,value in sorted(view.coverage.items()):
        if name=='status':continue
        if name=='counts':
            for key,count in sorted(value.items()):pair('Coverage '+key,count)
        elif name=='reasons':
            if not isinstance(value,(list,tuple)):_fail()
            for reason in value:pair('Coverage reason',reason)
        elif type(value) in (str,int,float,bool) or value is None:pair('Coverage '+name,value)
        else:pair('Coverage field retained in JSON',name)
    add()
    nodes=sorted((n for n in view.nodes if n.kind!='service'),key=_sort)
    headers=('Service','Direction','Protocol','Interface ID','Label','Operation / channel','Resolution','Freshness','Evidence kind','Context','Execution','Proof')
    def node_row(node):
        a=node.attributes
        if node.kind=='kafka_interface':
            operation='; '.join((_values(a.get('topics')),_text(a.get('topic_pattern')),
                'realm='+_text(a.get('broker_realm')),'group='+_text(a.get('consumer_group')),
                'subscription='+_text(a.get('subscription_kind'))))
        else:operation=_text(a.get('http_method'))+' '+_text(a.get('normalized_route',a.get('route_expression',a.get('original_route'))))
        return (_text(_service(node)),_text(a.get('direction')),_text(_protocol(node)),_text(node.id),_text(node.label),operation,
            _text(node.resolution_status),_text(node.freshness),_values(node.evidence_kinds),
            _values(a.get('context_ids')) if 'context_ids' in a else _text(a.get('context_id')),
            _text(a.get('execution_status',a.get('runtime_execution'))),link(node.id))
    assigned=set()
    for heading,directions in [('Provided interfaces',{'PROVIDED'}),('Used interfaces',{'CONSUMER','PRODUCER','USED'})]:
        add('## '+heading);add()
        selected=[n for n in nodes if n.kind in {'http_interface','kafka_interface'} and n.attributes.get('direction') in directions]
        assigned.update(n.id for n in selected);table(headers,[node_row(n) for n in selected])
    add('## Generated and unclassified');add();table(headers,[node_row(n) for n in nodes if n.id not in assigned])
    if not nodes:pair('Catalog boundary','No interface rows supplied within this captured scope; coverage and diagnostics remain authoritative.');add()
    add('## Contract bindings');add();rows=[]
    for node in nodes:
        bindings=node.attributes.get('contract_bindings',[])
        if not isinstance(bindings,(list,tuple)):_fail()
        for binding in sorted(bindings,key=canonical):
            if not isinstance(binding,dict):_fail()
            contract=binding.get('contract')
            if contract is None:contract={}
            if not isinstance(contract,dict):_fail()
            schema=binding.get('schema_references',[])
            if not isinstance(schema,(list,tuple)):_fail()
            schema_text=[]
            for reference in schema:
                if not isinstance(reference,dict):_fail()
                schema_text.append(_text(reference.get('role'))+': '+_text(reference.get('pointer')))
            rows.append((_text(node.id),_text(binding.get('role')),_text(binding.get('status')),
                _text(contract.get('repo_id'))+' / '+_text(contract.get('path')),_text(binding.get('revision')),
                _text(binding.get('revision_fingerprint')),_text(binding.get('raw_sha256')),
                _text(binding.get('operation_pointer')),', '.join(sorted(schema_text)) if schema_text else 'NONE',_text(binding.get('payload_compatibility')),
                _values(binding.get('reasons')),link(node.id)))
    table(('Interface ID','Role','Binding status','Contract','Revision','Revision fingerprint','SHA256','Pointer','Schema references','Payload compatibility','Reasons','Proof'),rows)
    add('## Unresolved and stale');add()
    for node in nodes:
        a=node.attributes;reasons=[]
        for key in ('reasons','unresolved_reasons'):
            if key in a:
                if not isinstance(a[key],(list,tuple)):_fail()
                reasons.extend(a[key])
        if node.resolution_status!='RESOLVED' or node.freshness!='CURRENT' or reasons:
            add('- '+_text(node.id)+': '+_text(node.resolution_status)+' / '+_text(node.freshness)+'; '+_values(reasons)+'; '+link(node.id))
    add();add('## Evidence and origins');add()
    proofs={p['id']:p for p in view.provenance};anchors={}
    def evidence(identity,role='item'):
        anchor=_anchor(identity,role)
        if anchor in anchors:_fail()
        anchors[anchor]=(role,identity);add('<a id="'+anchor+'"></a>');pair('Identity',identity)
    for node in nodes:
        evidence(node.id);pair('Kind',node.kind);pair('Owner',node.owner_id)
        pair('Original IDs',', '.join(_identity(v) for v in sorted(node.original_ids)) if node.original_ids else 'NONE')
        for label,refs in [('Supporting',node.supporting_refs),('Contradicting',node.contradicting_refs),('Unknown',node.unknown_refs)]:
            pair(label,', '.join(refs) if refs else 'NONE')
        if not node.evidence_refs:pair('Evidence status','MISSING / UNKNOWN')
        for ref in sorted(node.evidence_refs):add('- '+_text(ref)+': '+link(ref,'proof'))
        for key in ('generation_status','payload_compatibility','implementation_status','registration_kind','runtime_status',
                    'runtime_execution','runtime_availability','data_availability','deployment_status','deployment_availability',
                    'release_id','release','source_release_id','target_release_id','consumer_group','subscription_id','subscription_logical_id',
                    'source_path','metadata_raw_sha256','generated_raw_sha256','generator_execution'):
            if key in node.attributes:pair(key,node.attributes[key])
        if 'generation_origin' in node.attributes:
            origin=node.attributes['generation_origin']
            if origin is not None:
                if not isinstance(origin,dict):_fail()
                for key in ('repo_id','path','sha256'):
                    if key in origin:
                        if key in ('repo_id','path') and origin[key] is not None:_identity(origin[key])
                        pair('Generation origin '+key,origin[key])
        for key in ('handler_ids','request_type_ids','response_type_ids','message_type_ids'):
            if key in node.attributes:pair(key,', '.join(node.attributes[key]))
        add()
    for edge in sorted(view.edges,key=lambda e:e.id):
        evidence(edge.id,'edge')
        for label,value in [('Source',edge.source),('Target',edge.target),('Relation',edge.relation),('Resolution',edge.resolution_status),('Freshness',edge.freshness)]:pair(label,value)
        for label,refs in [('Original IDs',edge.original_ids),('Evidence IDs',edge.evidence_refs),('Supporting',edge.supporting_refs),('Contradicting',edge.contradicting_refs),('Unknown',edge.unknown_refs)]:pair(label,', '.join(refs) if refs else 'NONE')
        add()
    for identity,proof in sorted(proofs.items()):
        evidence(identity,'proof')
        for key in ('evidence_kind','freshness','polarity','source_file','source_line','raw_sha256','sha256','content_hash','role','scope'):
            if key in proof:pair(key,proof[key])
        if 'context_ids' in proof:
            if not isinstance(proof['context_ids'],(list,tuple)):_fail()
            pair('Context IDs',', '.join(_identity(v) for v in proof['context_ids']))
        if proof.get('source_file') is not None:_identity(proof['source_file'])
        span=proof.get('range',proof.get('source_range'))
        if span is not None:
            if not isinstance(span,dict):_fail()
            for key in ('start','end','start_line','start_column','end_line','end_column'):
                if key in span:pair('Range '+key,span[key])
        add()
    add('## Diagnostics and limits');add()
    for diagnostic in sorted(view.diagnostics,key=canonical):
        pair('Diagnostic',diagnostic.get('code','UNKNOWN'))
        for key in ('message','reason','source_id','target_id','interface_id','service_id','view_id','context_id','count'):
            if key in diagnostic:pair(key,diagnostic[key])
        if 'context_ids' in diagnostic:
            if not isinstance(diagnostic['context_ids'],(list,tuple)):_fail()
            pair('Context IDs',', '.join(_identity(v) for v in diagnostic['context_ids']))
        opaque=sorted(set(diagnostic)-{'code','message','reason','source_id','target_id','interface_id','service_id','view_id','context_id','count','context_ids'})
        if opaque:pair('Additional diagnostic fields retained in JSON',', '.join(opaque))
    for limit in sorted(view.limits):pair('Limit',limit)
    return '\n'.join(lines)+'\n'
