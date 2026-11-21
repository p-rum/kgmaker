"""Bounded local semantic decisions; never rewrites a technical ProcessView.

POSIX cooperating writers only. Review identities are declared, not authenticated.
Atomic replacement provides visibility; post-publication errors are indeterminate.
"""
from copy import deepcopy
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import tempfile
import threading

from .analysis_model import canonical, digest, safe_path, AnalysisError
from .process_semantics import (ProcessLabelPacketError, _bounded, _identifier,
    prepare_process_label_packet, validate_process_annotations, ANNOTATION_VALIDATION_VERSION,
    _context_selection, _proposed_annotations, VERSION as PACKET_VERSION)

VERSION = 'process-review-store-1'
MAX_HISTORY = 128
MAX_STORE_BYTES = 2 * 1024 * 1024
_IDENTITY_ASSURANCE = 'LOCAL_DECLARATION_NOT_AUTHENTICATED'
_THREAD_LOCK = threading.Lock()
_HEX = re.compile('[0-9a-f]{64}\\Z')
_PREPARED_KEYS = {'schema_version','rules_version','identity','baseline','baseline_hash',
    'payload_hash','annotations','document_bindings','technical_status','uncertainty','review_status'}
_ENTRY_KEYS = {'semantic_revision','previous_head','operation_id','operation_hash','action','reviewer',
    'identity_assurance','prepared','head'}


class ProcessReviewError(ValueError):
    """Fixed codes only. No user values or underlying filesystem diagnostics."""
    def __init__(self, code):
        self.diagnostic = {'code':code}
        super().__init__(code)


def _fail(code):
    raise ProcessReviewError(code) from None


def _hash(value):
    if type(value) is not str or _HEX.fullmatch(value) is None:
        _fail('INVALID_HASH_TOKEN')
    return value


def _id(value):
    try:
        return _identifier(value)
    except ProcessLabelPacketError:
        _fail('UNSAFE_IDENTIFIER')


def prepare_process_review(process, packet, candidate, *, documents=(), conflicts=()):
    """Revalidate all current explicit inputs; no stored report grants authority."""
    report=validate_process_annotations(process,packet,candidate,documents=documents,conflicts=conflicts)
    if not report['valid']: _fail('INVALID_REVIEW_INPUT')
    if not report['annotations']: _fail('EMPTY_PROPOSAL')
    baseline={'identity':deepcopy(report['technical_binding']), 'packet_hash':report['packet_hash'],
        'packet_rules_version':packet['rules_version'], 'validation_rules_version':report['rules_version'],
        'input_binding_hash':packet['input_binding_hash'],
        'budgets':{k:packet['budget'][k] for k in ('token_budget','char_budget')}}
    annotations=deepcopy(report['annotations'])
    return {'schema_version':1,'rules_version':VERSION,'identity':deepcopy(report['technical_binding']),
        'baseline':baseline,'baseline_hash':digest(baseline),
        'payload_hash':digest({'packet_hash':packet['packet_hash'],'annotations':annotations}),
        'annotations':annotations,'document_bindings':deepcopy(packet['document_bindings']),
        'technical_status':report['technical_status'],'uncertainty':report['uncertainty'],
        'review_status':report['review_status']}


def _paths(root, identity):
    try:
        root=Path(root)
        if root.is_symlink() or not root.is_dir(): _fail('INVALID_STORE_ROOT')
        namespace=digest({'process_id':identity['process_id'],'scope':identity['scope']})
        directory=safe_path(root,'.kgmaker/process-reviews')
        path=safe_path(root,f'.kgmaker/process-reviews/{namespace}.json')
        lock=safe_path(root,'.kgmaker/process-reviews/coordination.lock')
        return directory,path,lock
    except (OSError,ValueError,TypeError,AnalysisError):
        _fail('INVALID_STORE_PATH')


def _json(raw):
    def unique(pairs):
        result={}
        for k,v in pairs:
            if k in result: _fail('INVALID_STORE')
            result[k]=v
        return result
    def constant(value): _fail('INVALID_STORE')
    try:
        result=json.loads(raw,object_pairs_hook=unique,parse_constant=constant)
        _bounded(result)
        return result
    except (ValueError,UnicodeError,RecursionError,ProcessLabelPacketError):
        _fail('INVALID_STORE')


def _validate_prepared(p):
    if type(p) is not dict or set(p)!=_PREPARED_KEYS: _fail('INVALID_STORE')
    if type(p['schema_version']) is not int or p['schema_version']!=1 or p['rules_version']!=VERSION:
        _fail('INVALID_STORE')
    if (type(p['identity']) is not dict or type(p['baseline']) is not dict
            or set(p['baseline'])!={'identity','packet_hash','packet_rules_version','validation_rules_version','input_binding_hash','budgets'}
            or p['baseline']['identity']!=p['identity']
            or p['baseline']['validation_rules_version']!=ANNOTATION_VALIDATION_VERSION
            or p['review_status'] not in ('PENDING','CONFLICT')): _fail('INVALID_STORE')
    identity=p['identity']
    if set(identity)!={'process_id','revision','scope','context_ids','context_selection',
            'context_selection_hash','baseline_fingerprint','definition_fingerprint',
            'technical_fingerprint','process_content_hash'}: _fail('INVALID_STORE')
    _id(identity['process_id']);_id(identity['scope']);_id(identity['baseline_fingerprint'])
    if type(identity['revision']) is not int or identity['revision']<1: _fail('INVALID_STORE')
    if type(identity['context_ids']) is not list: _fail('INVALID_STORE')
    for ref in identity['context_ids']: _id(ref)
    for name in ('context_selection_hash','definition_fingerprint','technical_fingerprint','process_content_hash'):
        _hash(identity[name])
    selection = _context_selection(identity['context_selection'], identity['scope'], identity['context_ids'], replay=True)
    if selection != identity['context_selection']: _fail('INVALID_STORE')
    if p['baseline']['packet_rules_version']!=PACKET_VERSION: _fail('INVALID_STORE')
    if (p['baseline_hash']!=digest(p['baseline']) or p['payload_hash']!=digest({
            'packet_hash':p['baseline']['packet_hash'],'annotations':p['annotations']})):
        _fail('INVALID_STORE')
    if type(p['annotations']) is not list or not p['annotations'] or len(p['annotations'])>256:
        _fail('INVALID_STORE')
    if type(p['document_bindings']) is not list or type(p['uncertainty']) is not dict:
        _fail('INVALID_STORE')
    # Validate stored presentation as semantic proposals, never arbitrary JSON prose.
    targets=[];sources=[];groups=[]
    for item in p['annotations']:
        if type(item) is not dict: _fail('INVALID_STORE')
        targets.append(item.get('target_id'))
        if type(item.get('source_refs')) is not list: _fail('INVALID_STORE')
        sources.extend(item['source_refs'])
        if 'grouping_proposal' in item:
            if type(item['grouping_proposal']) is not list: _fail('INVALID_STORE')
            groups.extend(item['grouping_proposal'])
    fake={'packet_hash':p['baseline']['packet_hash'],'allowed_target_ids':targets,
        'allowed_source_refs':sources,'annotation_schema':{'allowed_fields':['id','target_id',
        'source_refs','semantic_review_status','label','description','grouping_proposal'],
        'required_fields':['id','target_id','source_refs','semantic_review_status'],
        'grouping_target_ids':groups}}
    normalized=_proposed_annotations(fake,{'schema_version':1,'packet_hash':fake['packet_hash'],
        'annotations':p['annotations']})
    if normalized!=p['annotations']: _fail('INVALID_STORE')
    for doc in p['document_bindings']:
        if type(doc) is not dict or set(doc)!={'ref','content_hash','scope','context_ids','hash_status','capture_hash'}:
            _fail('INVALID_STORE')
        _id(doc['ref']);_hash(doc['content_hash']);_hash(doc['capture_hash'])
        if (doc['scope']!=identity['scope'] or type(doc['context_ids']) is not list
                or doc['hash_status'] not in ('CONTENT_VERIFIED','SUPPLIED_NOT_REVERIFIED')): _fail('INVALID_STORE')
        for ref in doc['context_ids']:
            _id(ref)
            if ref not in identity['context_ids']: _fail('INVALID_STORE')
    u=p['uncertainty']
    if (set(u)!={'target_ids','truncated','diagnostic_count','coverage_hash'}
            or type(u['target_ids']) is not list or type(u['truncated']) is not bool
            or type(u['diagnostic_count']) is not int or u['diagnostic_count']<0): _fail('INVALID_STORE')
    for ref in u['target_ids']: _id(ref)
    _hash(u['coverage_hash'])
    if p['technical_status'] not in ('COMPLETE_WITHIN_SELECTED_SCOPE','PARTIAL','UNKNOWN'): _fail('INVALID_STORE')
    _hash(p['baseline']['packet_hash']);_hash(p['baseline']['input_binding_hash'])
    budgets=p['baseline']['budgets']
    if (type(budgets) is not dict or set(budgets)!={'token_budget','char_budget'}
            or any(type(v) is not int or v<0 for v in budgets.values())): _fail('INVALID_STORE')


def _operation(entry):
    return digest({k:entry[k] for k in ('operation_id','action','reviewer','previous_head')} | {
        'payload_hash':entry['prepared']['payload_hash'],'baseline_hash':entry['prepared']['baseline_hash']})


def _validate_store(value, identity):
    if (type(value) is not dict or set(value)!={'schema_version','rules_version','process_id','scope','history','head'}
            or type(value['schema_version']) is not int or value['schema_version']!=1
            or value['rules_version']!=VERSION or value['process_id']!=identity['process_id']
            or value['scope']!=identity['scope'] or type(value['history']) is not list
            or not value['history'] or len(value['history'])>MAX_HISTORY): _fail('INVALID_STORE')
    previous=None;seen=set()
    for number,entry in enumerate(value['history'],1):
        if (type(entry) is not dict or set(entry)!=_ENTRY_KEYS or type(entry['semantic_revision']) is not int
                or entry['semantic_revision']!=number or entry['previous_head']!=previous
                or entry['action'] not in ('APPROVE','REJECT')
                or entry['identity_assurance']!=_IDENTITY_ASSURANCE): _fail('INVALID_STORE')
        _id(entry['operation_id']);_id(entry['reviewer']);_validate_prepared(entry['prepared'])
        if (entry['operation_id'] in seen or entry['prepared']['identity']['process_id']!=value['process_id']
                or entry['prepared']['identity']['scope']!=value['scope']
                or (entry['action']=='APPROVE' and entry['prepared']['review_status']=='CONFLICT')
                or entry['operation_hash']!=_operation(entry)
                or entry['head']!=digest({k:v for k,v in entry.items() if k!='head'})):
            _fail('INVALID_STORE')
        seen.add(entry['operation_id']);previous=entry['head']
    if value['head']!=previous: _fail('INVALID_STORE')
    return value


def _read(path,identity):
    try:
        if path.is_symlink(): _fail('INVALID_STORE_PATH')
        if not path.exists(): return None
        with path.open('rb') as stream:
            raw=stream.read(MAX_STORE_BYTES+1)
        if len(raw)>MAX_STORE_BYTES: _fail('STORE_SIZE_LIMIT')
        return _validate_store(_json(raw),identity)
    except (OSError,UnicodeError,RecursionError,TypeError,KeyError,ProcessLabelPacketError):
        _fail('INVALID_STORE')


@contextmanager
def _locked(directory,lock):
    if os.name!='posix': _fail('UNSUPPORTED_PLATFORM')
    import fcntl
    with _THREAD_LOCK:
        stream=None
        try:
            directory.mkdir(parents=True,exist_ok=True)
            # Never unlink a coordination inode while another process may wait.
            fd=os.open(lock,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
            stream=os.fdopen(fd,'a+b')
            fcntl.flock(stream.fileno(),fcntl.LOCK_EX)
            yield
        except OSError:
            _fail('STORE_IO_ERROR')
        finally:
            if stream is not None: stream.close()


def _cancel(cancelled):
    if cancelled is not None and cancelled(): _fail('CANCELLED')


def _receipt(entry,current,*,idempotent=False,status='COMMITTED'):
    return {'status':status,'operation_id':entry['operation_id'],'head':entry['head'],
        'semantic_revision':entry['semantic_revision'],'is_current':entry['head']==current,
        'idempotent':idempotent,'identity_assurance':_IDENTITY_ASSURANCE}


def _publish(path,raw,cancelled):
    temporary=None;published=False
    try:
        fd,temporary=tempfile.mkstemp(prefix='.review-',suffix='.tmp',dir=path.parent)
        with os.fdopen(fd,'wb') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        _cancel(cancelled)
        os.replace(temporary,path);published=True
        directory_fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try: os.fsync(directory_fd)
        finally: os.close(directory_fd)
        return 'COMMITTED'
    except OSError:
        if published: return 'INDETERMINATE'
        _fail('STORE_IO_ERROR')
    finally:
        if temporary is not None and not published:
            try: os.unlink(temporary)
            except FileNotFoundError: pass
            except OSError: _fail('STORE_IO_ERROR')


def persist_process_review(root,process,packet,candidate,*,action,reviewer,operation_id,
        expected_head,expected_payload_hash,expected_baseline_hash,documents=(),conflicts=(),cancelled=None):
    """Explicit semantic decision, CAS-protected across cooperating POSIX writers."""
    if cancelled is not None and not callable(cancelled): _fail('INVALID_CANCELLATION')
    prepared=prepare_process_review(process,packet,candidate,documents=documents,conflicts=conflicts)
    if action not in ('APPROVE','REJECT'): _fail('INVALID_ACTION')
    reviewer=_id(reviewer);operation_id=_id(operation_id)
    if expected_head is not None: _hash(expected_head)
    if (_hash(expected_payload_hash)!=prepared['payload_hash']
            or _hash(expected_baseline_hash)!=prepared['baseline_hash']): _fail('REVIEW_TOKEN_MISMATCH')
    if action=='APPROVE' and prepared['review_status']=='CONFLICT': _fail('CONFLICT_REQUIRES_REVISION')
    try:
        _validate_prepared(prepared)
    except ProcessLabelPacketError:
        _fail('INVALID_REVIEW_INPUT')
    _cancel(cancelled)
    directory,path,lock=_paths(root,prepared['identity'])
    if expected_head is not None and not path.exists(): _fail('CAS_CONFLICT')
    with _locked(directory,lock):
        # Recheck ordinary confinement after initialization; no hostile-root claim.
        _paths(root,prepared['identity'])
        current=_read(path,prepared['identity']);head=current['head'] if current else None
        entry={'semantic_revision':len(current['history'])+1 if current else 1,
            'previous_head':expected_head,'operation_id':operation_id,'action':action,'reviewer':reviewer,
            'identity_assurance':_IDENTITY_ASSURANCE,'prepared':prepared}
        entry['operation_hash']=_operation(entry)
        for old in current['history'] if current else ():
            if old['operation_id']==operation_id:
                if old['operation_hash']!=entry['operation_hash']: _fail('OPERATION_CONFLICT')
                return _receipt(old,head,idempotent=True)
        if head!=expected_head: _fail('CAS_CONFLICT')
        _cancel(cancelled)
        if current and len(current['history'])>=MAX_HISTORY: _fail('HISTORY_LIMIT')
        entry['head']=digest(entry)
        value={'schema_version':1,'rules_version':VERSION,'process_id':prepared['identity']['process_id'],
            'scope':prepared['identity']['scope'],'history':(current['history'] if current else [])+[entry],
            'head':entry['head']}
        _validate_store(value,prepared['identity'])
        try: _bounded(value)
        except ProcessLabelPacketError: _fail('STORE_STRUCTURE_LIMIT')
        raw=canonical(value).encode('utf-8')
        if len(raw)>MAX_STORE_BYTES: _fail('STORE_SIZE_LIMIT')
        status=_publish(path,raw,cancelled)
        return _receipt(entry,entry['head'],status=status)


def read_process_reviews(root,process,*,documents=(),conflicts=()):
    """History is readable; effective approval requires the exact current snapshot."""
    try:
        packet=prepare_process_label_packet(process,documents=documents,conflicts=conflicts)['packet']
    except (ProcessLabelPacketError,UnicodeError):
        _fail('INVALID_CURRENT_INPUT')
    _,path,_=_paths(root,packet['identity'])
    value=_read(path,packet['identity'])
    if value is None:
        return {'schema_version':1,'history':[],'head':None,'effective_status':'EMPTY',
            'active_annotations':[],'identity_assurance':_IDENTITY_ASSURANCE}
    latest=value['history'][-1]
    approved=next((e for e in reversed(value['history']) if e['action']=='APPROVE'),None)
    current_for=approved or latest
    budgets=current_for['prepared']['baseline']['budgets']
    try:
        current_packet=prepare_process_label_packet(process,documents=documents,conflicts=conflicts,**budgets)['packet']
    except ProcessLabelPacketError:
        _fail('INVALID_CURRENT_INPUT')
    baseline=current_for['prepared']['baseline']
    matches=(current_packet['packet_hash']==baseline['packet_hash']
        and baseline['validation_rules_version']==ANNOTATION_VALIDATION_VERSION)
    if matches and (current_packet['identity'] != baseline['identity']
                    or current_packet['input_binding_hash'] != baseline['input_binding_hash']):
        _fail('INVALID_STORE')
    effective=('NEEDS_REVALIDATION' if not matches else 'APPROVED' if approved else 'REJECTED')
    return {'schema_version':1,'head':value['head'],'history':deepcopy(value['history']),
        'effective_status':effective,'active_annotations':deepcopy(approved['prepared']['annotations'])
            if approved and matches else [],'identity_assurance':_IDENTITY_ASSURANCE}
