"""Architecture adapter: snapshot JSON or interface Markdown; explicit capture only."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import stat
import sys

from .analysis_model import AnalysisError, canonical, safe_path
from .architecture_model import ViewDocument
from .model import KnowledgeGraph
from .remote_mapping import _bounded, _selection, _workspace, resolve_remote_mappings
from .view_explanation import _ref
from .view_store import ViewExportError
from .inspection import sanitize

BUNDLE_VERSION='architecture-interface-inputs-1'
_MAX_INPUT_BYTES=32_000_000
_MAX_OUTPUT_CHARS=4_000_000
_CATALOGS={'http-providers':'http-providers','http-consumers':'http-consumers','kafka':'kafka-interfaces'}


class ArchitectureCLIError(ValueError):
    def __init__(self,code,exit_code=2):
        self.code=code;self.exit_code=exit_code
        super().__init__(code)


class SafeParser(argparse.ArgumentParser):
    def error(self,message):
        raise ArchitectureCLIError('INVALID_ARGUMENTS') from None


def _fail(code,exit_code=2):
    raise ArchitectureCLIError(code,exit_code) from None


def _configure(parser):
    actions=parser.add_subparsers(dest='architecture_command',required=True,parser_class=SafeParser)
    scopes = ('production', 'test', 'test_fixture', 'development', 'unknown')
    for name in ('interfaces','topology','explain'):
        child=actions.add_parser(name)
        child.add_argument('--root',type=Path,default=Path.cwd(),help='coordinator and relative input path root')
        child.add_argument('--workspace',type=Path,help='explicit manifest for capture-local or check-source')
        child.add_argument('--scope',choices=scopes,help='assert snapshot scope; local capture defaults to production')
        child.add_argument('--context-selection',type=Path,help='versioned capture pins; exact assertion in snapshot replay')
        child.add_argument('--strict',action='store_true')
        formats=('json','markdown') if name=='interfaces' else ('json','mermaid','markdown') if name=='topology' else ('json',)
        child.add_argument('--format',choices=formats,default='json')
        child.add_argument('--expected-fingerprint')
        child.add_argument('--cancel-file',type=Path)
        if name=='interfaces':
            child.add_argument('--catalog',choices=tuple(_CATALOGS),required=True)
            inputs=child.add_mutually_exclusive_group(required=True)
            inputs.add_argument('--interface-capture',type=Path)
            inputs.add_argument('--capture-local',action='store_true',help='explicit source/parser replay; existing indexes required, no index publication')
        elif name=='topology':
            inputs=child.add_mutually_exclusive_group(required=True)
            inputs.add_argument('--capture-snapshot',type=Path)
            inputs.add_argument('--capture-local',action='store_true',help='explicit source/parser replay; existing indexes required, no index publication; --view-cache separately opts into view publication')
            child.add_argument('--view-cache',type=Path,help='explicitly reuse/publish a derived view cache artifact')
            _configure_topology_filters(child)
        else:
            child.add_argument('--snapshot',type=Path,required=True)
            child.add_argument('--capture-snapshot',type=Path,required=True)
            child.add_argument('--element',required=True)
            child.add_argument('--graph-snapshot',type=Path)
            source=child.add_mutually_exclusive_group()
            source.add_argument('--source-status',type=Path,help='replay a supplied source-status handoff; no current source reads')
            source.add_argument('--check-source',action='store_true',help='explicit confined hash observation of bound original source references')
    export = actions.add_parser('export', help='publish JSON, Markdown and Mermaid from an explicit topology capture',
                                allow_abbrev=False)
    export.add_argument('--root', type=Path, default=Path.cwd(), help='coordinator path root')
    export.add_argument('--capture-snapshot', type=Path, required=True, help='explicit T016 topology capture JSON')
    export.add_argument('--output', type=Path, required=True, help='artifact directory inside the coordinator')
    export.add_argument('--scope', choices=scopes, help='assert captured scope')
    export.add_argument('--expected-fingerprint', help='exact canonical filtered topology SHA-256')
    export.add_argument('--timeout', type=float, default=30.0, help='cooperative publication deadline in seconds')
    export.add_argument('--cancel-file', type=Path, help='coordinator-local file that cancels an unpublished export')
    _configure_topology_filters(export)
    return parser


def _configure_topology_filters(parser):
    parser.add_argument('--focus')
    parser.add_argument('--direction', choices=('incoming', 'outgoing', 'both'), default='both')
    parser.add_argument('--max-hops', type=int)
    parser.add_argument('--max-nodes', type=int, default=200)
    parser.add_argument('--relations', nargs='*')
    parser.add_argument('--filter-contexts', nargs='*')


def register(subparsers):
    _configure(subparsers.add_parser('architecture',help='architecture snapshots; explicit derived-view cache opt-in'))


def _path(args,value):
    path=value if value.is_absolute() else args.root/value
    path=path.absolute()
    return safe_path(Path(path.anchor),'/'.join(path.parts[1:]))


def _read(args,value):
    path=_path(args,value)
    flags=os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0)
    descriptor=os.open(path,flags)
    try:
        before=os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):_fail('INPUT_UNAVAILABLE')
        if before.st_size>_MAX_INPUT_BYTES:_fail('INPUT_LIMIT')
        pieces=[];size=0
        while True:
            piece=os.read(descriptor,min(65536,_MAX_INPUT_BYTES-size+1))
            if not piece:break
            pieces.append(piece);size+=len(piece)
            if size>_MAX_INPUT_BYTES:_fail('INPUT_LIMIT')
        after=os.fstat(descriptor)
        if (before.st_size,before.st_mtime_ns,before.st_ino)!=(after.st_size,after.st_mtime_ns,after.st_ino):
            _fail('INPUT_CHANGED_DURING_READ',3)
    finally:os.close(descriptor)
    def pairs(values):
        result={}
        for key,value in values:
            if key in result:_fail('INVALID_JSON')
            result[key]=value
        return result
    def constant(value):_fail('INVALID_JSON')
    try:value=json.loads(b''.join(pieces).decode('utf-8'),object_pairs_hook=pairs,parse_constant=constant)
    except (ValueError,UnicodeError,RecursionError):_fail('INVALID_JSON')
    _bounded(value)
    return value


def _selectors(args):
    if args.context_selection is None:return None
    document=_read(args,args.context_selection)
    if (not isinstance(document,dict) or set(document)!={'schema_version','contexts'}
            or type(document['schema_version']) is not int or document['schema_version']!=1
            or not isinstance(document['contexts'],list) or len(document['contexts'])>2000):_fail('INVALID_SELECTOR')
    selected={}
    for row in document['contexts']:
        if not isinstance(row,dict) or set(row)!={'service_id','repo_id','module','context_id'}:_fail('INVALID_SELECTOR')
        key=tuple(_ref(row[k]) for k in ('service_id','repo_id','module'))
        if key in selected:_fail('INVALID_SELECTOR')
        selected[key]=_ref(row['context_id'])
    _selection(args.scope or 'production',selected)
    return selected


def _assert_selection(args,scope,rows,selected):
    if args.scope is not None and args.scope!=scope:_fail('CAPTURED_SCOPE_MISMATCH')
    if selected is not None and _selection(scope,selected)['selected_contexts']!=rows:
        _fail('CAPTURED_SELECTION_MISMATCH')


def _cancel(args):
    if args.cancel_file is not None and _path(args,args.cancel_file).exists():raise KeyboardInterrupt


@contextmanager
def _readonly_git():
    old=os.environ.get('GIT_OPTIONAL_LOCKS');os.environ['GIT_OPTIONAL_LOCKS']='0'
    try:yield
    finally:
        if old is None:os.environ.pop('GIT_OPTIONAL_LOCKS',None)
        else:os.environ['GIT_OPTIONAL_LOCKS']=old


def _preflight(args):
    from .workspace import load_workspace
    from .store import GRAPH_FILE
    if args.workspace is None:_fail('EXPLICIT_WORKSPACE_REQUIRED')
    manifest=_path(args,args.workspace)
    _read(args,manifest)  # bounded manifest before the existing typed loader
    workspace=load_workspace(manifest)
    # Every original public index must validate BEFORE any source parser/capture.
    for repo in workspace['repositories']:
        path=Path(repo['_root'])/GRAPH_FILE
        if not path.is_file():_fail('ORIGINAL_INDEX_REQUIRED')
        try:KnowledgeGraph.from_dict(_read(args,path))
        except (ValueError,TypeError,KeyError):_fail('ORIGINAL_INDEX_INVALID')
    return workspace,manifest


def _interfaces(args,selected):
    if args.capture_local:
        from .workspace import snapshot_workspace
        from .remote_mapping import capture_remote_mapping_inputs
        with _readonly_git():
            workspace,manifest=_preflight(args);_cancel(args)
            _,coverage,_,graph,_=snapshot_workspace(manifest,persist_cache=False)
            captured=capture_remote_mapping_inputs(workspace,graph,scope=args.scope or 'production',
                selected_contexts=selected,source_coverage=coverage)
        bundle={'schema_version':1,'rules_version':BUNDLE_VERSION,'workspace':_workspace(workspace),
                'graph':graph.to_dict(),'captured':captured}
    else:
        if args.workspace is not None:_fail('EXPLICIT_CAPTURE_REQUIRED')
        bundle=_read(args,args.interface_capture)
    if (not isinstance(bundle,dict) or set(bundle)!={'schema_version','rules_version','workspace','graph','captured'}
            or type(bundle['schema_version']) is not int or bundle['schema_version']!=1
            or bundle['rules_version']!=BUNDLE_VERSION or not isinstance(bundle['workspace'],dict)):
        _fail('INVALID_INTERFACE_BUNDLE')
    public=bundle['workspace']
    if any(k.startswith('_') for k in public) or any(any(k.startswith('_') for k in r) for r in public.get('repositories',[])):
        _fail('INVALID_INTERFACE_BUNDLE')
    captured=bundle['captured'];selection=captured['selection'];scope=selection['scope']
    _assert_selection(args,scope,selection['selected_contexts'],selected)
    workspace={**public,'_manifest_hash':captured['workspace_manifest_sha256']}
    graph=KnowledgeGraph.from_dict(bundle['graph'])
    # Validate the literal W07 input tuple; no live projector or resolver substitute.
    pins={tuple(row['key']):row['context_id'] for row in selection['selected_contexts']}
    resolve_remote_mappings(workspace,graph,captured['canonical_interfaces'],captured=captured,
                            scope=scope,selected_contexts=pins)
    identity='view:'+_CATALOGS[args.catalog]+':'+workspace['workspace_id']+':'+scope
    matches=[d for d in captured['canonical_interfaces'] if d['view_id']==identity]
    if len(matches)!=1:_fail('CAPTURED_CATALOG_UNAVAILABLE')
    view=ViewDocument.from_dict(matches[0])
    return view.to_dict(include_generation_metadata=False),view.content_fingerprint


def _cache_target(args, workspace=None):
    """Protect explicit input files and source repositories from cache writes."""
    if args.view_cache is None:return None
    from .view_cache import _safe_cache_target
    target=_safe_cache_target(_path(args,args.view_cache))
    for name in ('capture_snapshot','context_selection','workspace','cancel_file'):
        value=getattr(args,name,None)
        if value is None:continue
        source=_path(args,value)
        if target==source or target.exists() and source.exists() and target.samefile(source):
            _fail('VIEW_CACHE_INPUT_ALIAS')
    if workspace is not None:
        for repo in workspace['repositories']:
            root=Path(repo['_root']).resolve()
            if target.is_relative_to(root) and not target.is_relative_to(root/'.kgmaker/views'):
                _fail('VIEW_CACHE_SOURCE_PATH')
    return target


def _validate_topology_filters(args):
    if args.max_nodes<1 or args.max_nodes>20000 or args.max_hops is not None and not 0<=args.max_hops<=20000:
        _fail('INVALID_FILTER')
    for values in (args.relations,args.filter_contexts):
        if values is not None:
            for value in values:_ref(value)
    if args.focus is not None:_ref(args.focus)


def _filter_topology(args, view):
    from .topology_filter import filter_topology

    return filter_topology(view, focus_service=args.focus, direction=args.direction,
        max_hops=args.max_hops, max_nodes=args.max_nodes, relations=args.relations,
        scope=args.scope, context_ids=args.filter_contexts)


def _topology(args,selected):
    from .service_topology import capture_topology_inputs,aggregate_service_topology,prepare_service_topology_cache

    target=_cache_target(args)
    _validate_topology_filters(args)
    if args.capture_local:
        with _readonly_git():
            workspace,manifest=_preflight(args);_cancel(args)
            _cache_target(args,workspace)
            captured=capture_topology_inputs(manifest,scope=args.scope or 'production',selected_contexts=selected)
    else:
        if args.workspace is not None:_fail('EXPLICIT_CAPTURE_REQUIRED')
        captured=_read(args,args.capture_snapshot)
    selection=captured['remote_selection']
    _assert_selection(args,selection['scope'],selection['selected_contexts'],selected)
    args.prepared_view=(prepare_service_topology_cache(captured,target)
        if target is not None else None)
    original=args.prepared_view.document if args.prepared_view is not None else aggregate_service_topology(captured)
    result=_filter_topology(args, original)
    return result,ViewDocument.from_dict(result['document']).content_fingerprint


def _export(args):
    from ._view_export_cli import export_snapshot_artifacts
    from .architecture_render import render_topology_artifacts
    from .service_topology import aggregate_service_topology

    _validate_topology_filters(args)

    def decode_snapshot(value):
        view = aggregate_service_topology(value)
        _assert_selection(args, view.scope, None, None)
        return _filter_topology(args, view)

    return export_snapshot_artifacts(args, args.capture_snapshot, 'topology', decode_snapshot,
                                     render_topology_artifacts, max_input_bytes=_MAX_INPUT_BYTES)


def _explain(args,selected):
    from .view_explanation import explain_view_element,capture_explanation_source_status
    from .workspace import load_workspace
    _ref(args.element)
    if args.workspace is not None and not args.check_source:_fail('EXPLICIT_SOURCE_CHECK_REQUIRED')
    if args.check_source and (args.workspace is None or args.graph_snapshot is None):_fail('SOURCE_CHECK_INPUTS_REQUIRED')
    captured=_read(args,args.capture_snapshot);selection=captured['remote_selection']
    _assert_selection(args,selection['scope'],selection['selected_contexts'],selected)
    snapshot=_read(args,args.snapshot);filtering=None;view=snapshot
    if isinstance(snapshot,dict) and snapshot.get('rules_version')=='topology-filter-1':
        filtering=snapshot;view=snapshot['document']
    graph=KnowledgeGraph.from_dict(_read(args,args.graph_snapshot)) if args.graph_snapshot is not None else None
    status=_read(args,args.source_status) if args.source_status is not None else None
    result=explain_view_element(view,args.element,captured=captured,graph=graph,filtering=filtering,source_status=status)
    if args.check_source and result['source_locators']:
        manifest=_path(args,args.workspace);_read(args,manifest)
        workspace=load_workspace(manifest)
        status=capture_explanation_source_status(workspace,graph,captured=captured,
            reference_ids=[row['reference_id'] for row in result['source_locators']])
        result=explain_view_element(view,args.element,captured=captured,graph=graph,filtering=filtering,source_status=status)
    return result,result['view_fingerprint']


def _incomplete(value):
    if 'document' in value:
        return value['document']['coverage']['status']!='COMPLETE_WITHIN_SELECTED_SCOPE' or value['filtering']['truncated']
    if value.get('rules_version')=='view-explanation-1':
        return (value['coverage_status']!='COMPLETE_WITHIN_SELECTED_SCOPE' or value['status']!='EXPLAINED'
            or bool(value['unavailable_references']) or value['truncated']
            or value['current_source_status'] not in {'NOT_CHECKED','CONTENT_MATCH'})
    return value['coverage']['status']!='COMPLETE_WITHIN_SELECTED_SCOPE'


def _safe_output(value):
    if sanitize(value)!=value:_fail('UNSAFE_OUTPUT')
    pending=[value]
    while pending:
        item=pending.pop()
        if isinstance(item,dict):pending.extend(item.keys());pending.extend(item.values())
        elif isinstance(item,list):pending.extend(item)
        elif isinstance(item,str) and (item.startswith('repo:') or re.search(r'(?i)\b(?:password|secret|api[_-]?key|access[_-]?token)\s*[=:]',item)):
            _ref(item)


def _diagnostic(code,exit_code):
    value={'code':code,'exit_code':exit_code}
    if code in {'ORIGINAL_INDEX_REQUIRED','ORIGINAL_INDEX_INVALID'}:
        value['next_action']='Create or repair each original .kgmaker/graph.json explicitly before --capture-local; architecture never builds indexes.'
    if code=='INVALID_ARGUMENTS':value['next_action']='Use kgmaker architecture --help for supported arguments.'
    try:sys.stderr.write(json.dumps(value)+'\n')
    except (BrokenPipeError,OSError):pass


def run(argv):
    try:
        args=_configure(SafeParser(prog='kgmaker architecture')).parse_args(argv)
        args.root=args.root.resolve()
        if not args.root.is_dir():_fail('INVALID_ROOT')
        if args.expected_fingerprint is not None and re.fullmatch('[0-9a-f]{64}',args.expected_fingerprint) is None:
            _fail('INVALID_EXPECTED_FINGERPRINT')
        if args.architecture_command == 'export':
            return _export(args)
        _cancel(args);selected=_selectors(args)
        result,fingerprint={'interfaces':_interfaces,'topology':_topology,'explain':_explain}[args.architecture_command](args,selected)
        if args.expected_fingerprint is not None and args.expected_fingerprint!=fingerprint:_fail('EXPECTED_FINGERPRINT_MISMATCH',3)
        _cancel(args);_bounded(result);_safe_output(result)
        if args.architecture_command=='topology' and args.format=='markdown':
            from .architecture_render import render_topology_markdown
            payload=render_topology_markdown(result)
        elif args.format=='markdown':
            from .architecture_render import render_interface_markdown
            payload=render_interface_markdown(result)
        elif args.architecture_command=='topology' and args.format=='mermaid':
            from .architecture_render import render_topology_mermaid
            payload=render_topology_mermaid(result)
        else:payload=canonical(result)+'\n'
        if len(payload)>_MAX_OUTPUT_CHARS:_fail('OUTPUT_LIMIT')
        code=4 if args.strict and _incomplete(result) else 0
        sys.stdout.write(payload);sys.stdout.flush()
        prepared=getattr(args,'prepared_view',None)
        if code==0 and prepared is not None:
            _cancel(args)
            prepared.publish()
        return code
    except (ArchitectureCLIError, ViewExportError) as error:
        _diagnostic(error.code,error.exit_code);return error.exit_code
    except KeyboardInterrupt:
        _diagnostic('CANCELLED',130);return 130
    except BrokenPipeError:
        try:
            target=os.open(os.devnull,os.O_WRONLY)
            try:os.dup2(target,sys.stdout.fileno())
            finally:os.close(target)
        except (OSError,ValueError,AttributeError):pass
        return 141
    except (ValueError,TypeError,KeyError,AttributeError,OSError,RecursionError,OverflowError) as error:
        diagnostic=getattr(error,'diagnostic',None);raw=diagnostic.get('code') if isinstance(diagnostic,dict) else None
        conflict=type(raw) is str and raw in {'TOPOLOGY_CAPTURE_CHANGED','REMOTE_MANIFEST_CHANGED','EXPLAIN_WORKSPACE_CHANGED'}
        conflict=conflict or isinstance(error,AnalysisError) and error.code==3
        code=3 if conflict else 2
        _diagnostic('CURRENT_CAPTURE_CONFLICT' if conflict else 'INVALID_INPUT',code);return code
    except Exception:
        _diagnostic('INTERNAL_ERROR',1);return 1
