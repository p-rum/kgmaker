"""Versioned references, local decisions and bidirectional workflow lineage.

The journal is an index of evidence, not a second task catalogue. Local actors
are declared identities. Integrity hashes are not authentication or signatures.
"""
from __future__ import annotations

import copy
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .analysis_model import AnalysisError, digest, read_json, safe_path, write_json, file_hash
from .memory import is_sensitive_path

JOURNAL = '.kgmaker/workflow/lineage.json'
VERIFICATION_POLICY = 'verification_before_done'
KINDS = {'requirement', 'analysis', 'task', 'plan', 'change', 'test_suite', 'test_case',
         'dataset', 'test_run', 'review', 'document'}
RELATIONS = {'analyzes', 'implements', 'verifies', 'uses_dataset', 'depends_on', 'supersedes'}
ACTIONS = {'requested', 'submitted', 'approved', 'rejected', 'revoked'}


def empty():
    return {'schema_version': 1, 'revision': 0, 'references': {}, 'links': [], 'events': [],
            'identity': None, 'policy': {'before_implement': False, 'before_done': False}}


def reference(kind, identifier, revision, payload, *, repo_id='local', locator=None):
    if kind not in KINDS or not isinstance(identifier, str) or not identifier or len(identifier) > 500:
        raise AnalysisError('Invalid reference kind or ID')
    if not isinstance(revision, str) or not revision or len(revision) > 200:
        raise AnalysisError('Reference revision must be non-empty text')
    if not isinstance(repo_id, str) or not repo_id or len(repo_id) > 100:
        raise AnalysisError('Invalid reference repository')
    record = dict(kind=kind, id=identifier, revision=revision, repo_id=repo_id,
                  sha256=digest(payload), locator=locator, payload=payload)
    record['key'] = 'ref:' + digest(record)
    return record


def _validate_data(data):
    """Validate an in-memory journal before it can become persisted history."""
    if (not isinstance(data, dict) or set(data) != set(empty()) or data['schema_version'] != 1
            or type(data['revision']) is not int or data['revision'] < 0):
        raise AnalysisError('Unsupported lineage journal contract')
    if not isinstance(data['references'], dict) or not isinstance(data['links'], list) \
            or not isinstance(data['events'], list):
        raise AnalysisError('Unsupported lineage journal contract')
    for key, item in data['references'].items():
        expected = reference(item['kind'], item['id'], item['revision'], item['payload'],
                             repo_id=item['repo_id'], locator=item['locator'])
        if key != expected['key'] or item != expected:
            raise AnalysisError('Reference integrity mismatch')
        if is_verification(item):
            from .verification import validate_record
            payload = item['payload']
            validate_record(payload)
            if (item['id'] != 'verification:' + payload['run_id'] or item['revision'] != '1'
                    or item['repo_id'] != 'local' or item['locator'] is not None):
                raise AnalysisError('Invalid verification reference')
            task = data['references'].get(payload['task_reference'])
            if not task or task['kind'] != 'task' or task['id'] != payload['task_id']:
                raise AnalysisError('Verification requires its exact captured task reference')
    for link in data['links']:
        if (set(link) != {'source', 'target', 'relation'} or link['relation'] not in RELATIONS
                or link['source'] not in data['references'] or link['target'] not in data['references']):
            raise AnalysisError('Dangling or malformed lineage link')
        if link['relation'] == 'verifies':
            source = data['references'][link['source']]
            if is_verification(source) and link['target'] != source['payload']['task_reference']:
                raise AnalysisError('Verification must link to its exact captured task reference')
    previous = None
    for event in data['events']:
        if not isinstance(event,dict) or set(event)!={'subject','action','actor','identity_trust','reason','timestamp','previous','key'}:
            raise AnalysisError('Invalid audit event fields')
        actor=event['actor']
        if not isinstance(actor,dict) or set(actor)!={'id','kind'} or not isinstance(actor['id'],str) or not actor['id'].strip() or len(actor['id'])>200 or actor['kind'] not in {'human','agent'}:
            raise AnalysisError('Invalid audit actor')
        if event['action'] in {'approved','rejected','revoked'} and actor['kind']!='human':
            raise AnalysisError('Agent cannot author human decisions')
        if event['previous'] != previous or event['key'] != 'event:' + digest({k:v for k,v in event.items() if k != 'key'}):
            raise AnalysisError('Audit event integrity mismatch')
        if event['subject'] not in data['references'] or event['action'] not in ACTIONS:
            raise AnalysisError('Invalid audit subject or action')
        previous = event['key']
    policy = data['policy']
    approvals = {'before_implement', 'before_done'}
    if (not isinstance(policy, dict) or not approvals <= policy.keys()
            or not policy.keys() <= approvals | {VERIFICATION_POLICY}
            or any(type(v) is not bool for v in policy.values())):
        raise AnalysisError('Invalid approval policy')
    return data


def is_verification(ref):
    payload = ref['payload']
    return ref['kind'] == 'test_run' and isinstance(payload, dict) and payload.get('record_type') == 'verification'


def _load(root):
    path = safe_path(root, JOURNAL)
    if not path.exists():
        return empty()
    envelope = read_json(path)
    if not isinstance(envelope, dict) or set(envelope) != {'data', 'sha256'} or envelope['sha256'] != digest(envelope['data']):
        raise AnalysisError('Lineage journal integrity mismatch')
    return _validate_data(envelope['data'])


@contextmanager
def transaction(root: Path, expected_revision=None):
    """Serialize writers and replace one journal atomically; errors leave it intact."""
    if expected_revision is not None and (type(expected_revision) is not int or expected_revision < 0):
        raise AnalysisError('Expected journal revision must be a non-negative integer')
    path = safe_path(root, JOURNAL)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = safe_path(root, JOURNAL + '.lock')
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise AnalysisError('Workflow journal is busy; retry after the current writer') from None
    try:
        os.close(fd)
        data = load(root)
        if expected_revision is not None and data['revision'] != expected_revision:
            raise AnalysisError('Stale journal revision')
        before = copy.deepcopy(data)
        yield data
        if data != before:
            try:
                if data.get('revision') != before['revision']:
                    raise AnalysisError('Journal revision is managed by transaction')
                events = data.get('events') if isinstance(data, dict) else None
                if isinstance(events, list) and events[:len(before['events'])] != before['events']:
                    raise AnalysisError('Audit event history is immutable')
                _validate_data(data)
            except AnalysisError:
                raise
            except (KeyError, TypeError, ValueError, AttributeError, RecursionError) as exc:
                raise AnalysisError('Malformed lineage journal: '+str(exc)) from exc
            data['revision'] = before['revision'] + 1
            write_json(path, {'data': data, 'sha256': digest(data)})
    finally:
        lock.unlink(missing_ok=True)


def put(data, ref):
    # Same logical revision cannot be silently replaced by different content.
    for old in data['references'].values():
        if all(old[k] == ref[k] for k in ('kind', 'id', 'revision', 'repo_id')) and old != ref:
            raise AnalysisError('Reference revision already has different content')
    data['references'][ref['key']] = ref
    return ref['key']


def connect(data, source, target, relation):
    if relation not in RELATIONS or source not in data['references'] or target not in data['references']:
        raise AnalysisError('Unknown relation or reference')
    if source == target:
        raise AnalysisError('Self references are not supported')
    link = dict(source=source, target=target, relation=relation)
    if link not in data['links']:
        data['links'].append(link)


def event(data, subject, action, reason, *, actor=None):
    identity = actor or data['identity']
    if (subject not in data['references'] or action not in ACTIONS or not isinstance(reason, str)
            or not reason.strip() or len(reason) > 2000):
        raise AnalysisError('Decision requires existing subject, action and bounded reason')
    if not isinstance(identity, dict) or set(identity) != {'id', 'kind'} or identity['kind'] not in {'human', 'agent'}:
        raise AnalysisError('Configure an explicit local identity first')
    if not isinstance(identity['id'],str) or not identity['id'].strip() or len(identity['id'])>200:
        raise AnalysisError('Invalid local actor ID')
    if action in {'approved', 'rejected', 'revoked'} and identity['kind'] != 'human':
        raise AnalysisError('Agents cannot record human approval decisions')
    value = dict(subject=subject, action=action, actor=identity.copy(), identity_trust='LOCAL_DECLARED',
                 reason=reason, timestamp=datetime.now(timezone.utc).isoformat(),
                 previous=data['events'][-1]['key'] if data['events'] else None)
    value['key'] = 'event:' + digest(value)
    data['events'].append(value)
    return value


def approved(data, key):
    decisions = [e for e in data['events'] if e['subject'] == key and e['action'] in {'approved', 'rejected', 'revoked'}]
    return bool(decisions and decisions[-1]['action'] == 'approved')


def register_file(root, kind, identifier, revision, path, *, repo_id='local', expected_revision=None):
    if is_sensitive_path(path):
        raise AnalysisError('Sensitive paths cannot be lineage evidence')
    target = safe_path(root, path)
    if not target.is_file() or target.stat().st_size > 1_000_000:
        raise AnalysisError('Evidence must be a bounded regular file')
    payload = {'text': target.read_text(encoding='utf-8')}
    ref = reference(kind, identifier, revision, payload, repo_id=repo_id,
                    locator={'path': path, 'sha256': file_hash(target)})
    with transaction(root, expected_revision) as data:
        key = put(data, ref)
    return key


def task_references(task):
    request = reference('requirement', task['id'] + ':request', '1', {'text': task['request']})
    # Task reference excludes transient status to preserve approvals across transitions.
    item = reference('task', task['id'], str(task['plan_revision']),
                     {k: task[k] for k in ('id', 'title', 'request', 'base_commit', 'plan_revision')})
    result = [request, item]
    for artifact in task['artifacts']:
        kind = {'plan': 'plan', 'analyze': 'analysis', 'implement': 'change', 'review': 'review', 'test': 'test_run'}.get(artifact['phase'])
        if kind:
            payload = artifact
            revision = '1'
            if kind == 'review':
                payload = {'review': artifact, 'binding': task.get('delivery',{}).get('bindings',{}).get(artifact['id'])}
                revision = digest(payload)
            result.append(reference(kind, artifact['id'], revision, payload))
    return result


def sync_task(data, task):
    refs = task_references(task)
    keys = [put(data, r) for r in refs]
    connect(data, keys[1], keys[0], 'implements')
    for ref in refs[2:]:
        connect(data, ref['key'], keys[1], 'verifies' if ref['kind'] in {'test_run', 'review'} else 'depends_on')
    return refs


def enforce_gate(root, task, target, *, data=None):
    if data is None:
        data = load(root)
    policy = 'before_implement' if target == 'implement' else 'before_done' if target == 'done' else None
    if policy is None or not data['policy'][policy]:
        return
    refs = task_references(task)
    required = [refs[0]]
    plan = [r for r in refs if r['kind'] == 'plan']
    if not plan:
        raise AnalysisError('Approval gate requires a current plan')
    required.append(plan[-1])
    if target == 'done':
        reviews = [r for r in refs if r['kind'] == 'review']
        if not reviews or reviews[-1]['payload']['review'].get('overall') != 'approve':
            raise AnalysisError('Approval gate requires an approved review result')
        last_change = max((i for i,r in enumerate(refs) if r['kind'] == 'change'), default=-1)
        if refs.index(reviews[-1]) < last_change:
            raise AnalysisError('Review predates implementation')
        from .feature import source_inventory
        current = digest(source_inventory(root)[0])
        binding = reviews[-1]['payload']['binding']
        from .workflow import _git_head
        if not binding or binding['source_fingerprint'] != current or binding['head_commit'] != _git_head(root):
            raise AnalysisError('Review is stale relative to current source content')
        required.append(reviews[-1])
    if any(not approved(data, r['key']) for r in required):
        raise AnalysisError('Approval gate: current requirement, plan or review lacks local approval')


def trace(root, selector=None, *, data=None):
    from .verification import freshness, summary

    if data is None:
        data = load(root)
    refs = data['references']
    if selector:
        seeds = {key for key,r in refs.items() if key == selector or r['id'] == selector}
        if not seeds:
            raise AnalysisError('Unknown trace reference')
    else:
        seeds = set(refs)
    selected = set(seeds)
    while True:
        extra = {v for link in data['links'] if link['source'] in selected or link['target'] in selected
                 for v in (link['source'], link['target'])}
        if extra <= selected:
            break
        selected |= extra
    keys = sorted(selected)
    observed_freshness = {key: freshness(root, refs[key]['payload'])
                          for key in keys if is_verification(refs[key])}
    result = []
    for key in keys:
        ref = refs[key]
        stale = False
        verification = {}
        if ref['locator']:
            try:
                stale = file_hash(safe_path(root, ref['locator']['path'])) != ref['locator']['sha256']
            except (OSError, AnalysisError):
                stale = True
        if ref['kind'] == 'review' and isinstance(ref['payload'],dict) and ref['payload'].get('binding'):
            from .feature import source_inventory
            from .workflow import _git_head
            binding = ref['payload']['binding']
            stale = stale or digest(source_inventory(root)[0]) != binding['source_fingerprint'] or binding['head_commit'] != _git_head(root)
        if ref['kind'] == 'test_suite':
            try:
                from . import testgen
                state = testgen._state(root,ref['id'])
                packet = next(p for p in state['packets'] if p['packet_id']==ref['payload']['packet_id'])
                stale = stale or bool(testgen.freshness(root,packet))
            except (ImportError, AnalysisError, OSError, StopIteration, KeyError, TypeError):
                stale = True
        if ref['kind'] == 'test_run':
            if key in observed_freshness:
                state = observed_freshness[key]
                verification = {'origin': 'RUNNER_CAPTURED', 'freshness': state}
                stale = state == 'STALE'
            else:
                verification = {'origin': 'IMPORTED' if ref['locator'] else 'AGENT_DECLARED',
                                'freshness': 'STALE' if stale else 'UNKNOWN'}
        if ref['kind'] == 'task' and ref['repo_id'] == 'local':
            from .workflow import WorkflowError, load_task

            try:
                task = load_task(root, ref['id'])
            except WorkflowError:
                pass  # A registered task reference may have no local task state.
            else:
                if task_references(task)[1]['key'] == key:
                    verification = {'workflow_status': task['status'],
                                    'workflow_iteration': task['iteration'],
                                    'verification_summary': summary(
                                        root, data, task, observed_freshness=observed_freshness)}
        events = [e for e in data['events'] if e['subject'] == key]
        result.append({**ref, 'stale': stale, 'approved': approved(data,key) and not stale,
                       **verification,
                       'requested_by': next((e['actor'] for e in events if e['action']=='requested'), 'UNKNOWN'),
                       'decisions': events})
    links = [l for l in data['links'] if l['source'] in selected and l['target'] in selected]
    linked = {v for l in links for v in (l['source'],l['target'])}
    gaps=[{'reference':r['key'],'reason':'ORPHAN'} for r in result if r['key'] not in linked]
    for task_ref in [r for r in result if r['kind']=='task']:
        component={task_ref['key']}
        while True:
            extra={v for l in links if l['source'] in component or l['target'] in component
                   for v in (l['source'],l['target'])}
            if extra<=component: break
            component |= extra
        kinds={refs[k]['kind'] for k in component}
        missing={'requirement','analysis','change'}-kinds
        if not kinds & {'test_suite','test_run'}: missing.add('test_suite_or_run')
        gaps.extend({'reference':task_ref['key'],'reason':'MISSING_'+k.upper()} for k in sorted(missing))
    gaps.extend({'reference':r['key'],'reason':'MISSING_REQUESTER'} for r in result
                if r['kind']=='requirement' and r['requested_by']=='UNKNOWN')
    return {'schema_version':1, 'revision':data['revision'], 'references':result, 'links':links,
            'gaps':gaps, 'identity_trust':'LOCAL_DECLARED'}



def markdown(report):
    lines = ['# Dohledatelnost změn', '', 'Identita: LOCAL_DECLARED (lokální evidence).', '',
             '| Druh | ID | Revize | Zadavatel | Schválení | Stav |', '|---|---|---|---|---|---|']
    for r in report['references']:
        who = r['requested_by']
        who = who['id'] if isinstance(who,dict) else who
        cells = [r['kind'], r['id'], r['revision'], who, str(r['approved']),
                 r.get('freshness', 'STALE' if r['stale'] else 'CURRENT')]
        lines.append('| ' + ' | '.join(str(c).replace('|','\\|').replace('\n',' ') for c in cells) + ' |')
    tasks = [row for row in report['references'] if 'verification_summary' in row]
    if tasks:
        lines += ['', '## Ověření úloh', '']
        for row in tasks:
            verification = row['verification_summary']
            lines.append(f"- `{row['id']}` — workflow `{row['workflow_status']}`, iterace "
                         f"{row['workflow_iteration']}, ověření `{verification['status']}` "
                         f"(`{verification['reason']}`).")
    lines += ['', '## Vazby', '']
    lines += [f"- `{l['source']}` — {l['relation']} → `{l['target']}`" for l in report['links']]
    lines += ['', '## Rozhodnutí', '']
    for r in report['references']:
        lines += [f"- {e['timestamp']}: {e['actor']['id']} {e['action']} `{r['key']}`: {e['reason']}" for e in r['decisions']]
    lines += ['', '## Mezery', '']
    lines += [f"- {g['reference']}: {g['reason']}" for g in report['gaps']]
    return '\n'.join(lines) + '\n'


def sync_analysis(root, analysis_id, *, expected_revision=None):
    from . import feature
    path = safe_path(root,f'.kgmaker/analyses/{analysis_id}/analysis.json')
    candidate = read_json(path)
    check = feature.validate(root,analysis_id,candidate)
    if not check.get('valid'):
        raise AnalysisError('Cannot trace invalid/stale analysis')
    receipt = read_json(safe_path(root,f'.kgmaker/analyses/{analysis_id}/receipts/{candidate["revision"]}.json'))
    if receipt.get('candidate_hash') != digest(candidate):
        raise AnalysisError('Analysis receipt mismatch')
    ref=reference('analysis',analysis_id,str(candidate['revision']),candidate,
                  locator={'path':path.relative_to(root).as_posix(),'sha256':file_hash(path)})
    with transaction(root, expected_revision) as data:
        key=put(data,ref)
        for requirement in candidate['requirements']:
            r=reference('requirement',requirement['id'],str(candidate['revision']),requirement)
            put(data,r);connect(data,key,r['key'],'analyzes')
    return key


def sync_testgen(root,suite, *, expected_revision=None):
    from . import testgen
    report=testgen.report(root,suite)
    candidate=report['candidate'];revision=str(report['revision']);packet=report['packet']
    ref=reference('test_suite',suite,revision,{'candidate_hash':report['sha256'],
                  'packet_id':candidate['packet_id'],'execution':'NOT_RUN','target':packet['target']['id']})
    with transaction(root, expected_revision) as data:
        key=put(data,ref)
        for case in candidate['cases']:
            c=reference('test_case',suite+':'+case['id'],revision,case)
            put(data,c);connect(data,c['key'],key,'depends_on')
            for requirement in case['requirement_refs']:
                connect(data,c['key'],requirement,'verifies')
        for dataset in candidate['datasets']:
            d=reference('dataset',suite+':'+dataset['id'],revision,{'origin':'SYNTHETIC',**dataset})
            put(data,d)
            for case in candidate['cases']:
                if dataset['id'] in case['dataset_ids']:
                    c=reference('test_case',suite+':'+case['id'],revision,case)
                    connect(data,c['key'],d['key'],'uses_dataset')
        if packet['analysis']:
            a=packet['analysis']
            matches=[r for r in data['references'].values() if r['kind']=='analysis' and r['id']==a['id'] and r['revision']==str(a['revision']) and r['sha256']==a['sha256']]
            for match in matches: connect(data,key,match['key'],'depends_on')
    return key


def capture_change(root,task_id,base,head=None, *, expected_revision=None):
    import subprocess
    from .workflow import load_task
    def git(*args):
        try:
            return subprocess.run(['git','-C',str(root),*args],capture_output=True,check=True,text=True).stdout
        except (OSError,subprocess.CalledProcessError) as exc:
            raise AnalysisError('Git change evidence unavailable: '+str(exc)) from exc
    # Resolve refs first so caller text cannot be interpreted as diff options.
    base_sha=git('rev-parse','--verify',base+'^{commit}').strip()
    head_sha=git('rev-parse','--verify',(head or 'HEAD')+'^{commit}').strip()
    paths=git('diff','--name-only',base_sha,head_sha,'--').splitlines()
    if head is None:
        paths=git('diff','--name-only',base_sha,'--').splitlines()
        diff=git('diff','--binary',base_sha,'--')
    else:
        diff=git('diff','--binary',base_sha,head_sha,'--')
    if any(is_sensitive_path(p) for p in paths):
        raise AnalysisError('Change includes sensitive paths')
    task=load_task(root,task_id)
    payload={'base_commit':base_sha,'head_commit':head_sha if head else None,
             'state':'COMMITTED' if head else 'WORKTREE','changed_paths':paths,
             'diff_sha256':digest(diff),'task_id':task['id']}
    ref=reference('change',task['id']+':change',digest(payload),payload)
    with transaction(root, expected_revision) as data:
        refs=sync_task(data,task);put(data,ref);connect(data,ref['key'],refs[1]['key'],'implements')
    return ref['key']


def load(root):
    """Reject malformed journals through the public analysis error contract."""
    try:
        return _load(root)
    except AnalysisError:
        raise
    except (KeyError, TypeError, ValueError, AttributeError, RecursionError) as exc:
        raise AnalysisError('Malformed lineage journal: '+str(exc)) from exc
