"""One bounded flow report, with presentation order separate from execution."""
from __future__ import annotations

import copy
import html
import json
import math
import time
from collections import defaultdict, deque
from pathlib import Path

from .analysis_model import AnalysisError, atomic_write, canonical, digest

VERSION = 'flow-view-1'


def ordered_cfg(cfg):
    """Validate and visit adjacency; never turn sibling branches into a sequence."""
    blocks, edges = cfg.get('blocks'), cfg.get('edges')
    if not isinstance(blocks, list) or not isinstance(edges, list):
        raise AnalysisError('Invalid flow CFG collections')
    ids = [b.get('id') for b in blocks]
    if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise AnalysisError('Invalid or duplicate flow node IDs')
    nodes = {b['id']: b for b in blocks}
    for edge in edges:
        if edge.get('source') not in nodes or edge.get('target') not in nodes or not isinstance(edge.get('kind'), str):
            raise AnalysisError('Renderer received dangling/invalid CFG edge')
    start = cfg.get('entry')
    if nodes and start not in nodes:
        raise AnalysisError('Flow entry is absent')
    priority = {'normal':0, 'call':1, 'true':2, 'false':3, 'returns_to':4, 'resume':5, 'exception':6}
    outgoing = defaultdict(list)
    for edge in edges:
        outgoing[edge['source']].append(edge)
    order, seen = [], set()
    def visit(first):
        queue = deque([first])
        while queue:
            identity = queue.popleft()
            if identity in seen:
                continue
            seen.add(identity); order.append(identity)
            queue.extend(e['target'] for e in sorted(outgoing[identity],
                key=lambda e:(priority.get(e['kind'],10),e['kind'],e['target'],canonical(e))))
    if nodes:
        visit(start)
    unreachable = sorted(set(nodes)-seen)
    for identity in unreachable:
        visit(identity)
    for key in ('exit','exceptional_exit'):
        if cfg.get(key) is not None and cfg[key] not in nodes:
            raise AnalysisError('Flow exit is absent without an explicit omitted endpoint')
    position = {identity:i for i,identity in enumerate(order)}
    return ({**cfg, 'blocks':[nodes[i] for i in order], 'edges':sorted(edges,
             key=lambda e:(position[e['source']],priority.get(e['kind'],10),position[e['target']],canonical(e)))},
            order, unreachable)


def finalize(report, graph=None):
    result = copy.deepcopy(report)
    cfg, order, unreachable = ordered_cfg(result['cfg'])
    result['cfg'] = cfg
    result['flow_model_version'] = VERSION
    relation = result.get('view') in {'integrations','data-flow'}
    result['ordering'] = {'kind':'RELATIONSHIP_ONLY' if relation else 'CFG_PARTIAL_ORDER',
        'display_order':order, 'unreachable_from_entry':unreachable,
        'meaning':'Deterministic adjacency display; list position is not execution order. Branch alternatives, cycles and async boundaries retain their edges.'}
    result.update(execution='NOT_OBSERVED',availability='UNKNOWN')
    gaps = list(result.get('coverage',{}).get('gaps',[]))
    def gap(code, reason, **refs):
        gaps.append({'code':code,'reason':reason,**refs})
    if not cfg['blocks']:
        gap('CFG_UNAVAILABLE','No supported CFG exists for this entry; absence is not proof of no execution.',entity_ids=[result.get('entry')])
    if result.get('truncated'):
        gap('NODE_LIMIT','Omitted detail remains outside the selected node/depth budget.')
    if relation:
        gap('RELATIONSHIP_ONLY','These source/data/integration relationships do not establish CFG execution order.')
    proofs = {e['id']:e for e in graph.evidence} if graph is not None else {}
    contexts = {c['id']:c for c in result.get('contexts',[])}
    sites = {s['id']:s for s in graph.call_sites} if graph is not None else {}
    for block in cfg['blocks']:
        refs = {'node_ids':[block['id']], 'original_ids':block.get('original_ids',[])}
        if not relation and block.get('kind')=='call' and len(block.get('call_site_ids',[]))!=1:
            gap('AMBIGUOUS_CALL_BLOCK','This CFG block does not identify one ordered call occurrence.',**refs)
        if block.get('boundary_reason') or block.get('kind') == 'unresolved_boundary':
            gap('UNRESOLVED_BOUNDARY',block.get('boundary_reason') or block.get('label','Unresolved boundary'),**refs)
        if block.get('kind') == 'async_boundary' or block.get('async_boundary') or block.get('continuation') in {'SEPARATE','UNKNOWN'}:
            gap('ASYNC_ORDER_UNKNOWN','Caller continuation does not establish worker completion, delivery or global async order.',**refs)
        block.setdefault('original_ids',[block['id']])
        block.setdefault('context_ids',[cfg['context_id']] if cfg.get('context_id') else [])
        block.setdefault('evidence_ids',list(cfg.get('evidence_ids',[])))
        if graph is not None and not relation:
            # Preserve the exact site proofs even when admission stops expansion.
            # CFG syntax and call resolution remain distinct records in provenance.
            for site_id in block.get('call_site_ids',[]):
                site=sites.get(site_id,{})
                block['evidence_ids']=sorted(set(block['evidence_ids']) | set(site.get('evidence_ids',[])))
                if site.get('context_id'):
                    block['context_ids']=sorted(set(block['context_ids']) | {site['context_id']})
            from .views import execution_authority_gaps, evidence_freshness_gaps
            authority = execution_authority_gaps(contexts,graph.files,proofs,block['context_ids'],block['evidence_ids'])
            for item in authority + evidence_freshness_gaps(proofs,block['evidence_ids']):
                gap(item['code'],item['reason'],**refs,context_ids=block['context_ids'],evidence_ids=block['evidence_ids'])
            for site_id in block.get('call_site_ids',[]):
                site=sites.get(site_id)
                if not site or not site.get('declared_target') or site.get('evidence_kind')=='UNRESOLVED':
                    gap('UNRESOLVED_CALL', (site or {}).get('resolution_reason','Call-site proof unavailable'),**refs,call_site=site_id)
                elif site.get('dispatch_complete') is not True:
                    gap('INCOMPLETE_DISPATCH','Static target set is not proved complete.',**refs,call_site=site_id)
    for edge in cfg['edges']:
        edge.setdefault('context_ids',[cfg['context_id']] if cfg.get('context_id') else [])
        edge.setdefault('evidence_ids',list(cfg.get('evidence_ids',[])))
    for diagnostic in result.get('diagnostics',[]):
        gap(diagnostic.get('code','CFG_DIAGNOSTIC'),diagnostic.get('reason') or diagnostic.get('message') or canonical(diagnostic),diagnostic=diagnostic)
    gaps = [json.loads(x) for x in sorted({canonical(g) for g in gaps})]
    unknown = not cfg['blocks'] or any(g['code'] in {'EXECUTION_AUTHORITY_UNKNOWN','STALE_EVIDENCE','EVIDENCE_FRESHNESS_UNKNOWN'} for g in gaps)
    status = 'UNKNOWN' if unknown else 'PARTIAL' if gaps or result.get('status')=='PARTIAL' else result.get('status','COMPLETE_WITHIN_SUPPORTED_SYNTAX')
    result['status'] = status
    result['coverage'] = {'status':status,'gaps':gaps}
    result['contexts'] = sorted(result.get('contexts',[]),key=lambda c:c['id'])
    used = {p for b in cfg['blocks'] for p in b.get('evidence_ids',[])}
    used.update(p for e in cfg['edges'] for p in e.get('evidence_ids',[]))
    result['provenance'] = {'evidence': [proofs[p] for p in sorted(used) if p in proofs],
        'context_ids': sorted({c for b in cfg['blocks'] for c in b.get('context_ids',[])}),
        'evidence_ids':sorted(used)} if graph is not None else result.get('provenance',{})
    return result


def _label(value):
    return html.escape(str(value),quote=True).replace('\n','<br/>').replace('\r',' ').replace('|','&#124;')


def mermaid(report):
    report=finalize(report)
    title='Flow '+report.get('view','control-flow')+': '+report['status']+'; execution NOT_OBSERVED'
    if report.get('truncated'): title+='; truncated'
    lines=['---','title: '+json.dumps(title),'---','flowchart TD', '  %% flow-meta '+canonical({k:v for k,v in report.items() if k!='cfg'})]
    ids={b['id']:'n'+digest(b['id'])[:20] for b in report['cfg']['blocks']}
    for block in report['cfg']['blocks']:
        lines.append('  %% flow-node '+canonical(block))
        label=_label(block.get('label',block.get('kind','node')))
        if block.get('boundary_reason'): label+='<br/>'+_label(block['boundary_reason'])
        if block.get('kind')=='async_boundary' or block.get('async_boundary'):
            label+='<br/>async boundary; scheduling UNKNOWN'
        shape='{"'+label+'"}' if block.get('kind') in {'condition','exception_dispatch'} else '["'+label+'"]'
        lines.append('  '+ids[block['id']]+shape)
    for edge in report['cfg']['edges']:
        lines.append('  %% flow-edge '+canonical(edge))
        arrow='-.->' if edge['kind'] in {'exception','resume','suspend','async'} else '-->'
        lines.append(f"  {ids[edge['source']]} {arrow}|{_label(edge.get('condition') or edge['kind'])}| {ids[edge['target']]}")
    return '\n'.join(lines)+'\n'


def markdown(report):
    report=finalize(report)
    lines=['# Deterministic '+report.get('view','control-flow')+' view','',
        '- Status: '+report['status'], '- Scope: '+str(report.get('scope','unknown')),
        '- Entry: `'+str(report.get('entry','unknown'))+'`',
        '- Execution: NOT_OBSERVED; availability: UNKNOWN',
        '- Ordering: '+report['ordering']['kind']+'. '+report['ordering']['meaning'],'',
        '```mermaid',mermaid(report).rstrip(),'```','','## Source/provenance','']
    for context in report['contexts']:
        lines.append('- Context: `'+context['id']+'`; mode: '+str(context.get('mode','UNKNOWN'))+'; freshness: '+str(context.get('freshness','UNKNOWN')))
    for block in report['cfg']['blocks']:
        lines.append('- `'+block['id']+'`: '+str(block.get('source_file') or 'synthetic control node')+
                     '; original IDs: '+', '.join('`'+i+'`' for i in block['original_ids'])+
                     '; evidence: '+', '.join('`'+i+'`' for i in block['evidence_ids']))
    bindings={p['id']:p for b in report['cfg']['blocks'] for p in b.get('return_consumer_bindings',[])}
    if bindings:
        lines.extend(['','## Static return/consumer bindings (availability UNKNOWN)',''])
        for p in sorted(bindings.values(),key=lambda p:p['id']):
            lines.append('- `'+p['source']+'` → `'+p['target']+'`: '+p['transformation'])
    lines.extend(['','## Coverage/limits',''])
    lines.extend('- '+g['code']+': '+g['reason']+' '+canonical({k:v for k,v in g.items() if k not in {'code','reason'}}) for g in report['coverage']['gaps'])
    lines.extend('- '+str(s) for s in report.get('limitations',[]))
    for key,title in [('http','HTTP request intent'),('kafka_policy_boundaries','Kafka retry/DLT policy declarations')]:
        if report.get(key): lines.extend(['','## '+title+' (execution NOT_OBSERVED)','', '```json', json.dumps(report[key],ensure_ascii=False,indent=2,allow_nan=False),'```'])
    return '\n'.join(lines)+'\n'


def render(report, format='json'):
    report=finalize(report)
    if format=='json': return json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    if format=='mermaid': return mermaid(report)
    if format=='markdown': return markdown(report)
    raise AnalysisError('Unsupported flow format')


class RenderBudget:
    """Cooperative local deadline/cancellation, checked again immediately before replace."""
    def __init__(self, timeout=30.0, cancel_file=None):
        if isinstance(timeout,bool) or not isinstance(timeout,(int,float)) or not math.isfinite(timeout) or timeout<=0:
            raise AnalysisError('Flow timeout must be finite and positive')
        self.deadline=time.monotonic()+timeout
        self.cancel_file=Path(cancel_file) if cancel_file else None
        self.check()

    def check(self):
        if self.cancel_file is not None and self.cancel_file.exists():
            raise AnalysisError('FLOW_CANCELLED: output not published',4)
        if time.monotonic()>=self.deadline:
            raise AnalysisError('FLOW_TIMEOUT: output not published',4)


def publish(report, format, output=None, *, budget=None):
    budget=budget or RenderBudget()
    budget.check()
    text=render(report,format)
    budget.check()
    if output is not None:
        target=Path(output)
        missing=[]; parent=target.parent
        while not parent.exists():
            missing.append(parent); parent=parent.parent
        created=[]
        try:
            for parent in reversed(missing):
                try:
                    parent.mkdir()
                    created.append(parent)
                except FileExistsError:
                    if not parent.is_dir(): raise
            atomic_write(target,text,before_replace=budget.check)
        except BaseException:
            for parent in reversed(created):
                try: parent.rmdir()
                except OSError: pass  # Preserve concurrent contents and existing parents.
            raise
    return text


def output_path(root, output, graph, cancel_file=None):
    """Reuse repository containment and file-alias checks; exports stay in flows/."""
    from .analysis_model import safe_path
    from .view_cache import _safe_cache_target
    root=Path(root).resolve()
    path=Path(output)
    if path.is_absolute():
        try: path=path.relative_to(root)
        except ValueError: raise AnalysisError('Flow output must stay in .kgmaker/flows/') from None
    if len(path.parts)<3 or path.parts[:2]!=('.kgmaker','flows'):
        raise AnalysisError('Flow output must stay in .kgmaker/flows/')
    target=_safe_cache_target(safe_path(root,path.as_posix()))
    inputs=[root/p for p in graph.files]
    inputs.append(root/'.kgmaker/graph.json')
    if cancel_file is not None: inputs.append(Path(cancel_file).absolute())
    if any(target==p.absolute() or (target.exists() and p.exists() and target.samefile(p)) for p in inputs):
        raise AnalysisError('Flow output aliases an input')
    return target
