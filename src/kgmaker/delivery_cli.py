"""CLI for project templates, test proposals and local delivery evidence."""
from __future__ import annotations

import json
from pathlib import Path

from .analysis_model import AnalysisError, read_json, safe_path
from . import artifact_templates as templates
from . import provenance, testgen


def register(sub):
    p=sub.add_parser('template',help='project artifact templates (data only)')
    commands=p.add_subparsers(dest='delivery_action',required=True)
    for action in ('init','list','render'):
        child=commands.add_parser(action);child.add_argument('--root',type=Path,default=Path.cwd())
        if action=='render':
            child.add_argument('--kind',choices=sorted(templates.KINDS),required=True)
            child.add_argument('--template');child.add_argument('--variables',required=True)
            child.add_argument('--output-dir');child.add_argument('--filename');child.add_argument('--filename-template')
            child.add_argument('--filename-variables')
    p=sub.add_parser('testgen',help='prepare and validate host-agent test proposals; no execution')
    commands=p.add_subparsers(dest='delivery_action',required=True)
    for action in ('prepare','validate','apply','report','export'):
        child=commands.add_parser(action);child.add_argument('--root',type=Path,default=Path.cwd())
        child.add_argument('--id',required=True)
        if action=='prepare':
            child.add_argument('--target',required=True);child.add_argument('--scope',default='production')
            child.add_argument('--context');child.add_argument('--workspace',type=Path)
            child.add_argument('--framework',choices=sorted(testgen.FRAMEWORKS));child.add_argument('--analysis')
            child.add_argument('--token-budget',type=int,default=8000)
            child.add_argument('--template-filename')
            child.add_argument('--template-case');child.add_argument('--template-data');child.add_argument('--template-code')
            child.add_argument('--expected-revision',type=int)
        if action in {'validate','apply'}: child.add_argument('--candidate',required=True)
        if action=='report': child.add_argument('--format',choices=('json','markdown'),default='markdown')
        if action=='export':
            child.add_argument('--data-dir',default='tests/fixtures/kgmaker')
            child.add_argument('--data-format',choices=('json','csv'),default='json')
    p=sub.add_parser('trace',help='local identities, optional approval gates and delivery lineage')
    commands=p.add_subparsers(dest='delivery_action',required=True)
    for action in ('identity','policy','register','link','decide','sync-task','sync-analysis','sync-testgen','capture-change','show','check'):
        child=commands.add_parser(action);child.add_argument('--root',type=Path,default=Path.cwd())
        if action not in {'show', 'check'}:
            child.add_argument('--expected-revision', type=int)
        if action=='identity':
            child.add_argument('--actor',required=True);child.add_argument('--kind',choices=('human','agent'),default='human')
        elif action=='policy':
            child.add_argument('--before-implement',choices=('on','off'))
            child.add_argument('--before-done',choices=('on','off'))
        elif action=='register':
            child.add_argument('--kind',choices=sorted(provenance.KINDS),required=True)
            child.add_argument('--id',required=True);child.add_argument('--revision',required=True)
            child.add_argument('--path',required=True);child.add_argument('--repo-id',default='local')
        elif action=='link':
            child.add_argument('--source',required=True);child.add_argument('--target',required=True)
            child.add_argument('--relation',choices=sorted(provenance.RELATIONS),required=True)
        elif action=='decide':
            child.add_argument('--subject',required=True);child.add_argument('--action',choices=sorted(provenance.ACTIONS),required=True)
            child.add_argument('--reason',required=True)
        elif action in {'sync-task','sync-analysis','sync-testgen'}: child.add_argument('--id',required=True)
        elif action=='capture-change':
            child.add_argument('--task',required=True);child.add_argument('--base',required=True);child.add_argument('--head')
        elif action=='show':
            child.add_argument('reference',nargs='?');child.add_argument('--format',choices=('json','markdown'),default='markdown')


def _test_markdown(report):
    lines=['# Návrh testů', '', 'Spuštění: NOT_RUN. Data: SYNTHETIC.', '']
    if report['stale']: lines+=['STALE: '+'; '.join(report['stale']),'']
    for c in report['candidate']['cases']:
        lines += ['## '+c['id']+': '+c['title'],'',c['preconditions'],'']
        lines += [str(i)+'. '+s for i,s in enumerate(c['steps'],1)]
        lines += ['', 'Očekávání ('+c['expected']['basis']+'): '+c['expected']['text'],'']
        lines += ['- '+e['path']+':'+str(e['start'])+' SHA256 '+e['sha256'] for e in c['expected']['citations']]
    lines += ['', '## Omezení', '', *report['packet']['limitations'],
              *report['receipt']['unchecked_constraints'], *report['candidate']['questions']]
    return '\n'.join(lines)+'\n'


def run(args):
    root=args.root.resolve();action=args.delivery_action
    try:
        if args.command=='template':
            if action=='init': result={'written':templates.install(root)}
            elif action=='list':
                folder=safe_path(root,'.kgmaker/templates')
                result={'kinds':sorted(templates.KINDS),'project_manifests':[
                    p.relative_to(root).as_posix() for p in sorted(folder.glob('*.json')) if p.name!='defaults.json']}
            else:
                result=templates.generate(root,args.kind,read_json(safe_path(root,args.variables)),
                    template_id=args.template,filename_template=args.filename_template,
                    filename_variables=read_json(safe_path(root,args.filename_variables)) if args.filename_variables else None,
                    output_dir=args.output_dir,filename=args.filename)
        elif args.command=='testgen':
            if action=='prepare':
                result=testgen.prepare(root,args.id,args.target,scope=args.scope,context=args.context,
                    workspace=args.workspace,framework=args.framework,analysis=args.analysis,
                    token_budget=args.token_budget,expected_revision=args.expected_revision,
                    templates={k:v for k,v in [('test_case',args.template_case),('test_data',args.template_data),('test_code',args.template_code),('filename',args.template_filename)] if v})
                result={'packet':result,'candidate_template':testgen.candidate_template(result)}
            elif action in {'validate','apply'}:
                result=getattr(testgen,action)(root,args.id,read_json(safe_path(root,args.candidate)))
            elif action=='export': result=testgen.export(root,args.id,data_dir=args.data_dir,data_format=args.data_format)
            else:
                result=testgen.report(root,args.id)
                if args.format=='markdown':
                    print(_test_markdown(result));return 3 if result['stale'] else 0
        else:
            if action=='register':
                result={'reference':provenance.register_file(root,args.kind,args.id,args.revision,args.path,
                    repo_id=args.repo_id,expected_revision=args.expected_revision)}
            elif action=='sync-analysis': result={'reference':provenance.sync_analysis(root,args.id,expected_revision=args.expected_revision)}
            elif action=='sync-testgen': result={'reference':provenance.sync_testgen(root,args.id,expected_revision=args.expected_revision)}
            elif action=='capture-change': result={'reference':provenance.capture_change(root,args.task,args.base,args.head,expected_revision=args.expected_revision)}
            elif action in {'show','check'}:
                result=provenance.trace(root,getattr(args,'reference',None))
                if action=='show' and args.format=='markdown':
                    print(provenance.markdown(result));return 0
                if action=='check':
                    result['valid']=not any(r['stale'] for r in result['references']) and not result['gaps']
                    print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['valid'] else 4
            else:
                with provenance.transaction(root,args.expected_revision) as data:
                    if action=='identity':
                        if not args.actor.strip() or len(args.actor)>200: raise AnalysisError('Invalid local actor')
                        data['identity']={'id':args.actor,'kind':args.kind};result=data['identity']
                    elif action=='policy':
                        if args.before_implement is not None: data['policy']['before_implement']=args.before_implement=='on'
                        if args.before_done is not None: data['policy']['before_done']=args.before_done=='on'
                        result=data['policy']
                    elif action=='link':
                        provenance.connect(data,args.source,args.target,args.relation);result={'linked':True}
                    elif action=='decide': result=provenance.event(data,args.subject,args.action,args.reason)
                    elif action=='sync-task':
                        from .workflow import load_task
                        result={'references':provenance.sync_task(data,load_task(root,args.id))}
                    else: raise AnalysisError('Unknown trace action')
        print(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True))
        return 0
    except (AnalysisError,OSError,UnicodeError,ValueError,KeyError,TypeError) as exc:
        code=exc.code if isinstance(exc,AnalysisError) else 2
        print(json.dumps({'error':str(exc),'exit_code':code},ensure_ascii=False));return code
