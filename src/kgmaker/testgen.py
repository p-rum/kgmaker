"""Offline test design for existing functionality; the host agent supplies proposals.

No model API, code execution, package installation or test execution occurs here.
"""
from __future__ import annotations

import ast
import copy
import csv
import io
import json
import os
import re
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path

from . import feature
from .analysis_model import AnalysisError, ID_PATTERN, digest, file_hash, read_json, safe_path, write_json
from .artifact_templates import render, render_snapshot
from .memory import is_sensitive_path

BASE = '.kgmaker/workflow/testgen'
MAX_BYTES = 1_000_000
FRAMEWORKS = {'unittest', 'pytest', 'junit', 'jest', 'vitest', 'playwright'}
_SCHEMA_TYPES = {
    'object': dict, 'array': list, 'string': str, 'integer': int,
    'number': (int, float), 'boolean': bool, 'null': type(None),
}


def directory(root, suite):
    if not isinstance(suite, str) or not ID_PATTERN.fullmatch(suite):
        raise AnalysisError('Invalid test suite ID')
    return safe_path(root, BASE + '/' + suite)


@contextmanager
def locked(root, suite):
    folder = directory(root, suite)
    folder.mkdir(parents=True, exist_ok=True)
    lock = folder / '.lock'
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise AnalysisError('Test suite is busy') from None
    try:
        os.close(fd)
        yield folder
    finally:
        lock.unlink(missing_ok=True)


def _state(root, suite):
    path = directory(root, suite) / 'state.json'
    if not path.exists():
        return {'schema_version': 1, 'packets': [], 'candidates': [], 'exports': []}
    envelope = read_json(path)
    if set(envelope) != {'data', 'sha256'} or digest(envelope['data']) != envelope['sha256']:
        raise AnalysisError('Test suite state integrity mismatch')
    state = envelope['data']
    if set(state) != {'schema_version', 'packets', 'candidates', 'exports'} or state['schema_version'] != 1:
        raise AnalysisError('Unsupported test suite state')
    for packet in state['packets']:
        if packet['packet_id'] != digest({k:v for k,v in packet.items() if k != 'packet_id'}):
            raise AnalysisError('Test packet integrity mismatch')
    for record in state['candidates']:
        if record['sha256'] != digest(record['candidate']):
            raise AnalysisError('Stored candidate integrity mismatch')
    return state


def _save(folder, state):
    write_json(folder / 'state.json', {'data':state, 'sha256':digest(state)})


def _snapshot(root, workspace, scope, context):
    details = {}
    baseline, coverage, sources, nodes = feature.snapshot(root, workspace=workspace, scope=scope,
                       context_id=context, _details=details, _select_context=False)
    graph, _, _ = feature.current_graph(root, workspace)
    from .views import project, select_context
    selected = select_context(graph, scope, context)
    projection = project(graph, scope, context_id=selected)
    return baseline, coverage, sources, graph, projection, details, selected


def _source(root, key, packet):
    if packet.get('workspace'):
        from .workspace import source_path
        return source_path(packet, key)
    return safe_path(root, key)


def _frameworks(root, sources, workspace):
    found = set()
    evidence = []
    for key, meta in sources.items():
        path = meta.get('path',key)
        name = Path(path).name
        if name not in {'pyproject.toml','package.json','pom.xml','build.gradle','build.gradle.kts','pytest.ini'} and not (name.startswith('test_') or '.test.' in name or '.spec.' in name):
            continue
        if is_sensitive_path(path):
            continue
        try:
            text = _source(root,key,{'source_manifest':sources,'workspace':workspace}).read_text(encoding='utf-8')[:100000]
        except (OSError, UnicodeError):
            continue
        patterns = {'unittest':r'\b(?:import unittest|from unittest import)\b',
                    'pytest':r'\bpytest\b', 'junit':r'\b(?:junit|org\.junit)\b',
                    'vitest':r'\bvitest\b', 'jest':r'\bjest\b', 'playwright':r'\bplaywright\b'}
        for framework, pattern in patterns.items():
            if re.search(pattern,text):
                found.add(framework)
                evidence.append({'path':key,'sha256':meta['sha256'],'framework':framework})
    return sorted(found), evidence


def prepare(root: Path, suite: str, selector: str, *, scope='production', context=None,
            workspace: Path | None = None, framework=None, analysis=None, token_budget=8000,
            templates=None, expected_revision=None):
    if expected_revision is not None and (type(expected_revision) is not int or expected_revision < 0):
        raise AnalysisError('Expected test suite revision must be a non-negative integer')
    if type(token_budget) is not int or not 1000 <= token_budget <= 100000:
        raise AnalysisError('Token budget must be an integer from 1000 to 100000')
    directory(root,suite)
    baseline, coverage, sources, graph, projection, details, selected = _snapshot(root,workspace,scope,context)
    matches = [n for n in projection.nodes if n.id == selector]
    if not matches:
        matches = [n for n in projection.nodes if n.kind == 'file' and n.path == selector]
    if not matches:
        from .store import query_nodes
        matches = [n for n,_ in query_nodes(projection,selector,limit=10,scope='all')]
    if len(matches) != 1:
        raise AnalysisError('Select exactly one existing entity or file; candidates: ' + json.dumps(
            [{'id':n.id,'path':n.path} for n in matches],ensure_ascii=False))
    target = matches[0]
    if is_sensitive_path(target.path) or target.path not in sources:
        raise AnalysisError('Target is not an available non-sensitive source')
    neighbors = [e for e in graph.edges if target.id in (e.source,e.target)]
    ids = {target.id} | {v for e in neighbors for v in (e.source,e.target)}
    related = [n for n in graph.nodes if n.id in ids or n.path == target.path]
    tests = [n for n in graph.nodes if n.scope in {'test','test_fixture'} or n.path.startswith('tests/')]
    terms = set(re.findall(r'\w+',target.name.lower()))
    tests.sort(key=lambda n:(-sum(t in (n.name+' '+n.path).lower() for t in terms),n.id))
    related += tests[:12]
    keys = list(dict.fromkeys([target.path]+[n.path for n in related]+[
        k for k in sources if Path(sources[k].get('path',k)).name in {'pyproject.toml','package.json','pom.xml','build.gradle','build.gradle.kts','pytest.ini'}]))
    workspace_meta = details.get('workspace')
    framework_options, framework_evidence = _frameworks(root,sources,workspace_meta)
    if framework is not None and framework not in FRAMEWORKS:
        raise AnalysisError('Unsupported framework selection')
    if framework is not None and framework_options and framework not in framework_options:
        raise AnalysisError('Explicit framework is not evidenced by repository configuration/tests')
    if framework is None and len(framework_options)>1:
        raise AnalysisError('Ambiguous test framework; select --framework from '+', '.join(framework_options))
    chosen = framework or (framework_options[0] if framework_options else None)
    packet = {'schema_version':1,'suite_id':suite,'revision':0,'packet_id':'',
              'target':asdict(target),'baseline':baseline,'scope':scope,'context_id':selected,
              'workspace':workspace_meta,'workspace_manifest':str(workspace.resolve()) if workspace else None,
              'source_manifest':{},'sources':[], 'nodes':[asdict(n) for n in related[:40]],
              'edges':[asdict(e) for e in neighbors[:80]],'coverage':coverage,
              'framework':chosen,'framework_evidence':framework_evidence,'analysis':None,
              'templates':{},'limitations':['Static characterisation is not business approval.',
                 'No test was executed; all generated results are proposals.'], 'budget':token_budget}
    # Coverage detail remains available from existing tools; keep this packet bounded.
    packet['coverage'] = {'limitations':coverage.get('limitations',[]),
                          'parser_capabilities':coverage.get('parser_capabilities',{}),
                          'diagnostics':coverage.get('artifact_diagnostics',[])[:30]}
    if not chosen:
        packet['limitations'].append('FRAMEWORK_UNKNOWN: cases/data can be produced; executable code is BLOCKED.')
    for kind in ('test_case','test_data','test_code'):
        packet['templates'][kind] = render(root,kind,{'title':target.name,'body':'Host agent: provide structured '+kind+' candidate.'},(templates or {}).get(kind))
    packet['templates']['filename'] = render(root,'filename',
        {'id':suite,'slug':'test','extension':'py'},(templates or {}).get('filename'))
    if analysis:
        analysis_path = safe_path(root,f'.kgmaker/analyses/{analysis}/analysis.json')
        applied = read_json(analysis_path)
        receipt = read_json(safe_path(root,f'.kgmaker/analyses/{analysis}/receipts/{applied["revision"]}.json'))
        if receipt.get('candidate_hash') != digest(applied):
            raise AnalysisError('Analysis apply receipt does not match content')
        validation = feature.validate(root,analysis,applied)
        if not validation.get('valid'):
            raise AnalysisError('Linked analysis is invalid or stale')
        packet['analysis'] = {'id':analysis,'revision':applied['revision'],'sha256':digest(applied),
                              'packet_id':applied['packet_id']}
        packet['sources'].append({'path':analysis_path.relative_to(root).as_posix(),
                                  'sha256':file_hash(analysis_path),'text':analysis_path.read_text()})
    for key in keys[:40]:
        if key not in sources or is_sensitive_path(key):
            continue
        try:
            path = _source(root,key,{'source_manifest':sources,'workspace':workspace_meta})
            text = path.read_text(encoding='utf-8')
        except (OSError,UnicodeError):
            continue
        packet['source_manifest'][key] = sources[key]
        # Prefix bounded excerpts; citations outside an excerpt must be read explicitly by the host.
        excerpt = text[:min(len(text), max(1000,token_budget*2))]
        packet['sources'].append({'path':key,'sha256':sources[key]['sha256'],'text':excerpt})
        if len(json.dumps(packet,ensure_ascii=False)) > token_budget*4:
            packet['sources'].pop()
            packet['source_manifest'].pop(key)
            packet['limitations'].append('Context truncated to token budget; use existing query/impact tools for more evidence.')
            break
    if not any(s['path']==target.path for s in packet['sources']):
        raise AnalysisError('Token budget cannot hold target evidence; increase --token-budget')
    while len(json.dumps(packet,ensure_ascii=False)) > token_budget*4 and (packet['edges'] or len(packet['nodes'])>1):
        if packet['edges']: packet['edges'].pop()
        else: packet['nodes'].pop()
    if len(json.dumps(packet,ensure_ascii=False)) > token_budget*4:
        raise AnalysisError('Token budget too small for required packet metadata')
    packet = json.loads(json.dumps(packet, ensure_ascii=False))
    with locked(root,suite) as folder:
        state = _state(root,suite)
        current = len(state['packets'])
        if expected_revision is not None and current != expected_revision:
            raise AnalysisError('Stale packet revision')
        packet['revision'] = current+1
        packet['packet_id'] = digest({k:v for k,v in packet.items() if k!='packet_id'})
        # Identical preparation reuses the latest packet.
        if current:
            old = state['packets'][-1]
            same = {k:v for k,v in old.items() if k not in {'revision','packet_id'}}
            if same == {k:v for k,v in packet.items() if k not in {'revision','packet_id'}}:
                return old
        state['packets'].append(packet)
        _save(folder,state)
    return packet


def load_packet(root,suite):
    state = _state(root,suite)
    if not state['packets']:
        raise AnalysisError('Test suite has no prepared packet')
    return state['packets'][-1]


def freshness(root,packet):
    workspace = Path(packet['workspace_manifest']) if packet['workspace_manifest'] else None
    baseline,*_ = _snapshot(root,workspace,packet['scope'],packet['context_id'])
    stale = []
    if baseline != packet['baseline']:
        stale.append('Source, graph, compiler context or workspace baseline changed')
    if packet['analysis']:
        a = packet['analysis']
        path = safe_path(root,f'.kgmaker/analyses/{a["id"]}/analysis.json')
        if not path.exists() or digest(read_json(path)) != a['sha256']:
            stale.append('Linked analysis changed')
    return stale


def _citation(root,packet,citation):
    if not isinstance(citation,dict) or set(citation) != {'path','sha256','start','end','quote'}:
        raise AnalysisError('Citation requires path/hash/line range/quote')
    key = citation['path']
    sources = {s['path']:s for s in packet['sources']}
    if key not in sources or citation['sha256'] != sources[key]['sha256']:
        raise AnalysisError('Citation is outside the prepared packet or has a forged hash')
    if packet['analysis'] and key.startswith('.kgmaker/analyses/'):
        path = safe_path(root,key)
    else:
        path = _source(root,key,packet)
    if file_hash(path) != citation['sha256']:
        raise AnalysisError('Stale citation source')
    start,end = citation['start'],citation['end']
    if type(start) is not int or type(end) is not int or start<1 or end<start:
        raise AnalysisError('Invalid citation line range')
    lines = path.read_text(encoding='utf-8').splitlines()
    if end>len(lines) or not isinstance(citation['quote'],str) or not citation['quote'].strip() or citation['quote'] not in '\n'.join(lines[start-1:end]):
        raise AnalysisError('Citation quote is not present at the stated location')


def _json_equal(left, right):
    """JSON equality: booleans are distinct from numbers, including nested values."""
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is bool and type(right) is bool and left == right
    if left is None or right is None:
        return left is None and right is None
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left == right
    if isinstance(left, str) and isinstance(right, str):
        return left == right
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(_json_equal(a, b) for a, b in zip(left, right))
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(_json_equal(left[k], right[k]) for k in left)
    return False


def _output_path(root, value):
    """Validate the canonical path used both for deduplication and actual writes."""
    target = safe_path(root, value)
    canonical = target.relative_to(root.resolve()).as_posix()
    if value != canonical:
        raise AnalysisError('Output path must be canonical and repository-relative')
    if (any(part.casefold() in {'.git', '.github', '.kgmaker'} for part in Path(canonical).parts)
            or is_sensitive_path(canonical)):
        raise AnalysisError('Output path is protected or sensitive')
    return target


def _schema_kind(schema, *, label='Dataset schema'):
    if not isinstance(schema,dict):
        raise AnalysisError(f'{label} must be an object')
    kind = schema.get('type')
    if not isinstance(kind, str) or kind not in _SCHEMA_TYPES:
        raise AnalysisError(f'{label} requires a supported type')
    return kind


def _schema_property_paths(path, precise, name, *, quote_keys):
    if name.isidentifier():
        child = precise + '.' + name
    else:
        child = f'{precise}[{json.dumps(name, ensure_ascii=False)}]'
    return (child if quote_keys else path + '.' + name), child


def schema_errors(value,schema,path='$'):
    """Supported JSON-schema subset, returning concrete violation paths."""
    return _schema_errors(value, schema, path, path, quote_keys=False)


def _schema_errors(value, schema, path, precise, *, quote_keys):
    kind = _schema_kind(schema)
    errors,unchecked = [],[]
    known = {'type','properties','required','items','enum','minimum','maximum','minLength','maxLength','nullable','additionalProperties'}
    unchecked += [path+':'+k for k in schema if k not in known]
    additional = schema.get('additionalProperties', True)
    if kind == 'object':
        if isinstance(additional, dict):
            _schema_kind(additional, label=f'{path}:additionalProperties schema')
        elif type(additional) is not bool:
            raise AnalysisError(f'{path}:additionalProperties requires a boolean or supported schema')
    nullable = value is None and schema.get('nullable') is True
    if not nullable and (not isinstance(value, _SCHEMA_TYPES[kind]) or
                         kind in {'integer', 'number'} and isinstance(value, bool)):
        return [path + ':type'], unchecked
    if 'enum' in schema:
        if not isinstance(schema['enum'], list) or not schema['enum']:
            raise AnalysisError('Dataset enum must be a non-empty array')
        if not any(_json_equal(value, choice) for choice in schema['enum']):
            errors.append(path + ':enum')
    if nullable:
        return errors, unchecked
    if kind in {'integer','number'}:
        for field,op in [('minimum',lambda x,y:x<y),('maximum',lambda x,y:x>y)]:
            if field in schema and op(value,schema[field]): errors.append(path+':'+field)
    if kind == 'string':
        for field,op in [('minLength',lambda x,y:x<y),('maxLength',lambda x,y:x>y)]:
            if field in schema and op(len(value),schema[field]): errors.append(path+':'+field)
    if kind == 'object':
        for name in schema.get('required',[]):
            if name not in value:
                child, _ = _schema_property_paths(path, precise, name, quote_keys=quote_keys)
                errors.append(child + ':required')
        for name,item in value.items():
            child, precise_child = _schema_property_paths(path, precise, name, quote_keys=quote_keys)
            if name in schema.get('properties',{}):
                e,u = _schema_errors(item, schema['properties'][name], child, precise_child,
                                     quote_keys=quote_keys)
                errors.extend(e)
                unchecked.extend(u)
            elif additional is False:
                errors.append(child + ':additionalProperties')
            elif isinstance(additional, dict):
                extra_errors, extra_unchecked = _schema_errors(item, additional, precise_child, precise_child,
                                                               quote_keys=True)
                errors.extend(extra_errors)
                unchecked.extend(extra_unchecked)
    if kind == 'array':
        if 'items' not in schema: unchecked.append(path+':items-unspecified')
        for i,item in enumerate(value):
            if 'items' in schema:
                e,u = _schema_errors(item, schema['items'], f'{path}[{i}]', f'{precise}[{i}]',
                                     quote_keys=quote_keys)
                errors.extend(e)
                unchecked.extend(u)
    return errors,unchecked


def _ids(items,label):
    if not isinstance(items,list) or len(items)>200:
        raise AnalysisError(label+' must be a bounded list')
    ids = [item.get('id') if isinstance(item,dict) else None for item in items]
    if any(not isinstance(i,str) or not ID_PATTERN.fullmatch(i) for i in ids) or len(ids)!=len(set(ids)):
        raise AnalysisError('Duplicate or invalid '+label+' IDs')
    return set(ids)


def _validate(root,suite,candidate):
    packet = load_packet(root,suite)
    stale = freshness(root,packet)
    if stale:
        raise AnalysisError('Stale test packet: '+'; '.join(stale),3)
    expected = {'schema_version','suite_id','packet_id','cases','datasets','files','questions'}
    if not isinstance(candidate,dict) or set(candidate)!=expected or candidate['schema_version']!=1 or candidate['suite_id']!=suite or candidate['packet_id']!=packet['packet_id']:
        raise AnalysisError('Candidate does not match the test generation contract/packet')
    if len(json.dumps(candidate,ensure_ascii=False)) > MAX_BYTES:
        raise AnalysisError('Candidate exceeds size limit')
    case_ids = _ids(candidate['cases'],'case')
    dataset_ids = _ids(candidate['datasets'],'dataset')
    if not case_ids:
        raise AnalysisError('At least one test case is required')
    if not isinstance(candidate['questions'],list) or any(not isinstance(q,str) for q in candidate['questions']):
        raise AnalysisError('Questions must be text')
    for case in candidate['cases']:
        fields = {'id','title','target_ids','requirement_refs','category','preconditions','steps','expected','dataset_ids'}
        if set(case)!=fields or case['category'] not in {'positive','negative','boundary','characterization'}:
            raise AnalysisError('Invalid test case contract')
        if case['target_ids'] != [packet['target']['id']]:
            raise AnalysisError('Test must reference the selected existing functionality')
        if not isinstance(case['dataset_ids'],list) or not set(case['dataset_ids'])<=dataset_ids:
            raise AnalysisError('Unknown test dataset reference')
        if not isinstance(case['requirement_refs'],list):
            raise AnalysisError('Requirement references must be a list')
        if case['requirement_refs']:
            from .provenance import load
            refs=load(root)['references']
            if any(k not in refs or refs[k]['kind']!='requirement' for k in case['requirement_refs']):
                raise AnalysisError('Unknown requirement reference')
        for field in ('title','preconditions'):
            if not isinstance(case[field],str) or not case[field].strip():
                raise AnalysisError('Case requires '+field)
        if not isinstance(case['steps'],list) or not case['steps'] or any(not isinstance(s,str) or not s.strip() for s in case['steps']):
            raise AnalysisError('Case requires executable-design steps')
        expected_result=case['expected']
        if not isinstance(expected_result,dict) or set(expected_result)!={'text','basis','citations'} or expected_result['basis'] not in {'CODE_CHARACTERIZATION','CONTRACT','ANALYSIS'} or not isinstance(expected_result['text'],str) or not expected_result['text'].strip() or not expected_result['citations']:
            raise AnalysisError('Expected result requires explicit basis and evidence citations')
        for c in expected_result['citations']:
            _citation(root,packet,c)
            is_analysis=c['path'].startswith('.kgmaker/analyses/')
            if expected_result['basis']=='CODE_CHARACTERIZATION' and packet['source_manifest'].get(c['path'],{}).get('kind')!='CODE':
                raise AnalysisError('Code characterization must cite code')
            if expected_result['basis']=='CONTRACT' and Path(c['path']).suffix not in {'.json','.yaml','.yml','.proto','.sql'}:
                raise AnalysisError('Contract expectation must cite a contract source')
            if expected_result['basis']=='ANALYSIS' and not is_analysis:
                raise AnalysisError('Analysis expectation must cite the linked analysis')
    unchecked=[]
    for dataset in candidate['datasets']:
        if set(dataset)!={'id','purpose','schema','data','negative','expected_violations','citations','foreign_keys'} or type(dataset['negative']) is not bool or not isinstance(dataset['purpose'],str) or not dataset['purpose'].strip():
            raise AnalysisError('Invalid synthetic dataset contract')
        if not isinstance(dataset['citations'],list) or not dataset['citations']:
            raise AnalysisError('Dataset constraints require source citations')
        for c in dataset['citations']: _citation(root,packet,c)
        errors,gaps=schema_errors(dataset['data'],dataset['schema'])
        unchecked += [dataset['id']+':'+g for g in gaps]
        if not isinstance(dataset['foreign_keys'],list):
            raise AnalysisError('Foreign keys must be a list')
        for fk in dataset['foreign_keys']:
            if not isinstance(fk,dict) or set(fk)!={'field','dataset_id','target_field'} or fk['dataset_id'] not in dataset_ids:
                raise AnalysisError('Invalid dataset foreign key')
            other=next(d for d in candidate['datasets'] if d['id']==fk['dataset_id'])
            if not isinstance(dataset['data'],list) or not isinstance(other['data'],list):
                raise AnalysisError('Foreign keys require row datasets')
            values = [r[fk['target_field']] for r in other['data']
                      if isinstance(r, dict) and fk['target_field'] in r]
            for i,row in enumerate(dataset['data']):
                if (not isinstance(row, dict) or fk['field'] not in row or
                        not any(_json_equal(row[fk['field']], value) for value in values)):
                    errors.append(f'$[{i}].'+fk['field']+':foreign_key')
        if dataset['negative']:
            if not errors or sorted(errors)!=sorted(dataset['expected_violations']):
                raise AnalysisError('Negative dataset must declare exactly its actual violations')
        elif errors or dataset['expected_violations']:
            raise AnalysisError('Invalid positive dataset: '+', '.join(errors))
    if not isinstance(candidate['files'],list) or len(candidate['files'])>200:
        raise AnalysisError('Test files must be a bounded list')
    paths=set();covered=set()
    for item in candidate['files']:
        if not isinstance(item,dict) or set(item)!={'path','content','case_ids'} or not isinstance(item['content'],str) or not item['content'].strip():
            raise AnalysisError('Invalid generated test file')
        path=item['path']
        _output_path(root, path)
        if path in paths:
            raise AnalysisError('Unsafe or duplicate test output path')
        if not packet['framework']:
            raise AnalysisError('Executable test code is BLOCKED without a selected framework')
        if not isinstance(item['case_ids'],list) or not item['case_ids'] or not set(item['case_ids'])<=case_ids:
            raise AnalysisError('Generated test code cites unknown cases')
        if Path(path).suffix=='.py':
            try: ast.parse(item['content'])
            except SyntaxError as exc: raise AnalysisError('Generated Python syntax is invalid: '+str(exc)) from exc
        else:
            unchecked.append(path+':test-code-syntax-not-checked')
        covered.update(item['case_ids']);paths.add(path)
    return {'valid':True,'candidate_hash':digest(candidate),'packet_id':packet['packet_id'],
            'execution':'NOT_RUN','synthetic':True,'unchecked_constraints':unchecked,
            'code_status':'PROPOSED' if candidate['files'] else 'BLOCKED' if not packet['framework'] else 'NOT_PROVIDED',
            'cases_without_code':sorted(case_ids-covered)}


def apply(root,suite,candidate):
    result=validate(root,suite,candidate)
    with locked(root,suite) as folder:
        state=_state(root,suite)
        if state['packets'][-1]['packet_id']!=candidate['packet_id']:
            raise AnalysisError('Packet changed during validation')
        for old in state['candidates']:
            if old['sha256']==result['candidate_hash']:
                return {**result,'revision':old['revision']}
        revision=len(state['candidates'])+1
        state['candidates'].append({'revision':revision,'sha256':result['candidate_hash'],
                                    'candidate':copy.deepcopy(candidate),'receipt':result})
        _save(folder,state)
    return {**result,'revision':revision}


def report(root,suite):
    state=_state(root,suite)
    if not state['candidates']:
        raise AnalysisError('No applied test design')
    record=state['candidates'][-1]
    packet=next(p for p in state['packets'] if p['packet_id']==record['candidate']['packet_id'])
    stale=freshness(root,packet)
    if packet!=state['packets'][-1]: stale.append('Newer packet exists')
    return {**record,'packet':packet,'stale':stale,'exports':state['exports'],'execution':'NOT_RUN'}


def export(root,suite,*,data_dir='tests/fixtures/kgmaker',data_format='json'):
    if data_format not in {'json','csv'}:
        raise AnalysisError('Unsupported dataset export format')
    _output_path(root, data_dir)
    with locked(root,suite) as folder:
        state=_state(root,suite)
        if not state['candidates']: raise AnalysisError('No applied test design')
        record=state['candidates'][-1];candidate=record['candidate']
        validate(root,suite,candidate)
        packet = next(p for p in state['packets'] if p['packet_id']==candidate['packet_id'])
        files={f['path']:f['content'] for f in candidate['files']}
        for dataset in candidate['datasets']:
            name_result=render_snapshot(packet['templates']['filename'],{'id':suite,'slug':dataset['id'],'extension':data_format})
            name=data_dir+'/'+name_result['text']
            if name in files: raise AnalysisError('Dataset/test output collision')
            if data_format=='json':
                content=json.dumps(dataset['data'],ensure_ascii=False,indent=2)+'\n'
            else:
                rows=dataset['data']
                if not isinstance(rows,list) or not rows or any(not isinstance(r,dict) or any(isinstance(v,(list,dict)) for v in r.values()) for r in rows):
                    raise AnalysisError('CSV requires a non-empty flat object row dataset')
                columns=sorted({k for r in rows for k in r})
                buffer=io.StringIO();writer=csv.DictWriter(buffer,fieldnames=columns)
                writer.writeheader();writer.writerows(rows);content=buffer.getvalue()
            files[name]=content
        if not files: raise AnalysisError('No files or datasets to export')
        paths = {name: _output_path(root, name) for name in files}
        if any(p.exists() for p in paths.values()):
            raise AnalysisError('Export collision; existing files preserved')
        # Preflight ancestor collisions before creating any files.
        for path in paths.values():
            if any(p.exists() and not p.is_dir() for p in path.parents if p.is_relative_to(root)):
                raise AnalysisError('Export parent is not a directory')
        root_resolved = root.resolve()
        missing_directories = {
            parent for path in paths.values() for parent in path.parents
            if parent != root_resolved and parent.is_relative_to(root_resolved) and not parent.exists()
        }
        written=[]
        try:
            for name,path in paths.items():
                path.parent.mkdir(parents=True,exist_ok=True)
                with path.open('x',encoding='utf-8') as stream:
                    written.append(path);stream.write(files[name])
            receipt={'revision':record['revision'],'candidate_hash':record['sha256'],'execution':'NOT_RUN',
                     'files':{name:file_hash(path) for name,path in paths.items()},'data_origin':'SYNTHETIC',
                     'filename_template':packet['templates']['filename']['template']}
            state['exports'].append(receipt);_save(folder,state)
        except BaseException:
            for path in written: path.unlink(missing_ok=True)
            for path in sorted(missing_directories, key=lambda item: len(item.parts), reverse=True):
                try: path.rmdir()
                except OSError: pass
            raise
    return receipt


def candidate_template(packet):
    """Structured starting point for a host-agent response; not a valid test yet."""
    target=packet['target']['id']
    return {'schema_version':1,'suite_id':packet['suite_id'],'packet_id':packet['packet_id'],
            'cases':[{'id':'case-1','title':'Describe the scenario','target_ids':[target],
                      'requirement_refs':[],'category':'characterization',
                      'preconditions':'Describe preconditions','steps':['Describe an action'],
                      'expected':{'text':'Describe expected behaviour','basis':'CODE_CHARACTERIZATION',
                                  'citations':[]},'dataset_ids':[]}],
            'datasets':[],'files':[],'questions':[]}


def validate(root, suite, candidate):
    """Return deterministic diagnostics for malformed structures at the library boundary."""
    try:
        return _validate(root, suite, candidate)
    except AnalysisError:
        raise
    except (KeyError, TypeError, ValueError, RecursionError) as exc:
        raise AnalysisError('Malformed test candidate: ' + str(exc)) from exc
