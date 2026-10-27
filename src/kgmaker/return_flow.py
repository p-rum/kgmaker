"""Compiler-owned return/result/consumer occurrences; no runtime values or execution.

A declared source body and a caller occurrence remain separate identities. A
body join is attached only to a supported source target; opaque dispatch, async,
callable and recursive bodies remain explicit boundaries.
"""
from __future__ import annotations

from dataclasses import replace

from .analysis_model import digest
from .model import Edge,KnowledgeGraph,Node

VERSION='return-consumer-1'
_VALUE_STATUSES={'VALUE','VOID','CALLABLE','UNKNOWN'}
_NULLABILITY={'UNKNOWN','MAY_BE_NULL','DECLARED_NON_NULL','NULL_LITERAL'}


def _range(value):
    if not (isinstance(value,dict) and all(type(value.get(k)) is int for k in ('start','end')) and 0<=value['start']<value['end']):return False
    for key in ('start_line','end_line','start_column','end_column'):
        if key in value and (type(value[key]) is not int or value[key]<1):return False
    if 'start_line' in value and 'end_line' in value:
        if value['end_line']<value['start_line']:return False
        if value['end_line']==value['start_line'] and 'start_column' in value and 'end_column' in value and value['end_column']<=value['start_column']:return False
    return True


def _info(value):
    return (isinstance(value,dict) and type(value.get('version')) is int and value['version']==1
            and _enum(value.get('status'),_VALUE_STATUSES) and isinstance(value.get('type_ref'),str)
            and len(value['type_ref'])<=2048 and _enum(value.get('nullability'),_NULLABILITY))


def _enum(value,allowed):
    return isinstance(value,str) and value in allowed


def _children(node):
    for key in ('body','value','receiver','condition','then','else','left','right','initial','update','iterable','finally'):
        value=node.get(key)
        if isinstance(value,dict):yield value
    for key in ('statements','arguments','expressions','resources'):
        values=node.get(key,[])
        if isinstance(values,list):
            yield from (v for v in values if isinstance(v,dict))
    values=node.get('catches',[])
    if isinstance(values,list):
        for value in values:
            if isinstance(value,dict) and isinstance(value.get('body'),dict):yield value['body']


def validate_return_ir(response,context=None):
    """Optional IR extension: reject malformed proof before graph publication."""
    symbols={s['id']:s for s in response['symbols']};ids=set(symbols);sites={s['id']:s for s in response['call_sites']}
    snapshot=(context or {}).get('source_files')
    context_id=(context or {}).get('id',response.get('context_id'))
    owners=[symbols[b['method']] for b in response['bodies'] if isinstance(b.get('method'),str) and b['method'] in symbols]
    # Interval trees avoid scanning every method for every repeated local read.
    groups={}
    for owner in owners:
        if (owner.get('context_id')==context_id and isinstance(owner.get('path'),str)
                and isinstance(owner.get('sha256'),str) and _range(owner.get('range'))):
            groups.setdefault((owner['path'],owner['sha256']),[]).append(owner)
    def index(values):
        if not values:return None
        middle=len(values)//2;left=index(values[:middle]);right=index(values[middle+1:]);value=values[middle]
        return value,max(value['range']['end'],left[1] if left else 0,right[1] if right else 0),left,right
    indexes={key:index(sorted(values,key=lambda o:(o['range']['start'],o['range']['end']))) for key,values in groups.items()}
    def enclosing_owners(value):
        pending=[indexes.get((value['path'],value['sha256']))];result=[];span=value['range']
        while pending:
            entry=pending.pop()
            if entry is None or entry[1]<span['end']:continue
            owner,_,left,right=entry
            if owner['range']['start']<=span['start']:
                if span['end']<=owner['range']['end']:result.append(owner)
                pending.append(right)
            pending.append(left)
        return result

    def location(value,owner=None):
        if not isinstance(value,dict):raise ValueError('Invalid return proof source locator')
        path=value.get('path');checksum=value.get('sha256');span=value.get('range')
        if (not isinstance(path,str) or not isinstance(checksum,str) or not _range(span)
                or not isinstance(snapshot,dict) or path not in snapshot or snapshot[path]!=checksum):
            raise ValueError('Return proof source snapshot/range mismatch')
        if owner is not None and (owner.get('context_id')!=context_id or owner.get('path')!=path
                or owner.get('sha256')!=checksum or not _range(owner.get('range'))
                or not owner['range']['start']<=span['start']<span['end']<=owner['range']['end']):
            raise ValueError('Return proof source owner mismatch')

    count=0
    for body in response['bodies']:
        if 'return_flow_version' not in body:continue
        if type(body['return_flow_version']) is not int or body['return_flow_version']!=1:
            raise ValueError('Unsupported return IR version')
        if not _enum(body.get('return_body_kind'),{'DECLARED','ERROR','CONSTRUCTOR','CALLABLE','ASYNC','GENERATOR','ACCESSOR'}):
            raise ValueError('Invalid return body kind')
        if body['return_body_kind']=='DECLARED' and not _info(body.get('return_type')):
            raise ValueError('Invalid declared return type proof')
        if not _enum(body.get('language'),{'java','kotlin','typescript'}):raise ValueError('Invalid return IR language')
        if 'return_dispatch' in body and not _enum(body['return_dispatch'],{'OPEN','STATIC','PRIVATE','LEXICAL','HARD_PRIVATE'}):
            raise ValueError('Invalid return dispatch proof')
        if body.get('return_binding_boundary') is not None and not _enum(body['return_binding_boundary'],{'TS_DIRECT_BUILTIN_EVAL','TS_DIRECT_EVAL_IDENTITY_UNKNOWN'}):
            raise ValueError('Invalid return binding boundary')
        active=body['return_body_kind']=='DECLARED'
        owner=symbols.get(body.get('method')) if isinstance(body.get('method'),str) else None
        if active:
            if owner is None or body.get('context_id')!=context_id:raise ValueError('Invalid return method owner/context')
            if any(k in owner and owner[k] is not None and type(owner[k]) is not bool for k in ('jvm_static','suspend','async','generator')):
                raise ValueError('Invalid return method flags')
            if owner.get('modifiers') is not None and (not isinstance(owner['modifiers'],list) or not all(isinstance(v,str) for v in owner['modifiers'])):
                raise ValueError('Invalid return method modifiers')
            location(owner,owner)
            location(body.get('body',{}),owner)
        pending=[(body.get('body',{}),0,owner)]
        while pending:
            node,depth,parent=pending.pop();count+=1
            if not isinstance(node,dict) or count>200000 or depth>256:raise ValueError('Return IR bounds exceeded')
            if not isinstance(node.get('kind'),str):raise ValueError('Invalid return IR kind')
            if 'value_info' in node and not _info(node['value_info']):raise ValueError('Invalid return expression type proof')
            located=any(k in node for k in ('path','sha256','range'))
            if active and (located or 'value_info' in node or node['kind'] in {'if','assign','destructure','safe_call'}):
                location(node,owner)
                if (parent.get('path')!=node['path'] or parent.get('sha256')!=node['sha256']
                        or not parent['range']['start']<=node['range']['start']<node['range']['end']<=parent['range']['end']):
                    raise ValueError('Return expression escapes enclosing source range')
            binding=node.get('value_binding')
            targets=node.get('value_targets',[])
            if not isinstance(targets,list) or len(targets)>256:raise ValueError('Invalid destructuring proof')
            bindings=([binding] if binding is not None else [])+[v.get('binding') for v in targets if isinstance(v,dict)]
            for item in bindings:
                if (not isinstance(item,dict) or type(item.get('version')) is not int or item['version']!=1
                        or not isinstance(item.get('id'),str) or not isinstance(item.get('name'),str)
                        or not _enum(item.get('kind'),{'LOCAL_VARIABLE','PARAMETER','FIELD','ENUM_CONSTANT'})
                        or not _range(item.get('range')) or not isinstance(item.get('path'),str)
                        or not isinstance(item.get('sha256'),str) or not _info(item.get('type'))
                        or (item.get('method') is not None and (not isinstance(item['method'],str) or item['method'] not in ids))
                        or (item.get('symbol') is not None and (not isinstance(item['symbol'],str) or item['symbol'] not in ids))):
                    raise ValueError('Invalid return consumer binding proof')
                if active:
                    declaration_owner=symbols.get(item.get('method'))
                    location(item,declaration_owner)
                    if item['kind']=='PARAMETER':
                        if declaration_owner is None or not item['id'].startswith(item['method']+':parameter:'):
                            raise ValueError('Return parameter binding owner mismatch')
                    elif item['kind']=='LOCAL_VARIABLE':
                        span=item['range']
                        enclosing=enclosing_owners(item)
                        if enclosing:
                            size=min(o['range']['end']-o['range']['start'] for o in enclosing)
                            if item.get('method') not in {o['id'] for o in enclosing if o['range']['end']-o['range']['start']==size}:
                                raise ValueError('Return local binding owner mismatch')
                        if not item['id'].endswith(f":{item['path']}:{item['sha256']}:{span['start']}:{span['end']}"):
                            raise ValueError('Return local binding identity mismatch')
                    else:
                        declaration=symbols.get(item.get('symbol'))
                        if declaration is None or declaration.get('context_id')!=context_id or any(item.get(k)!=declaration.get(k) for k in ('path','sha256','range')):
                            raise ValueError('Return field binding declaration mismatch')
            shape=node.get('value_shape')
            if shape is not None and (not isinstance(shape,dict) or not _enum(shape.get('kind'),{'TUPLE_ELEMENT','OBJECT_PROPERTY'})
                    or (shape['kind']=='TUPLE_ELEMENT' and (type(shape.get('size')) is not int or not 0<=shape['size']<=256))
                    or (shape['kind']=='OBJECT_PROPERTY' and (not isinstance(shape.get('keys'),list) or len(shape['keys'])>256 or not all(isinstance(k,str) for k in shape['keys'])))):
                raise ValueError('Invalid return projection shape')
            if 'value_targets' in node:
                if not isinstance(node['value_targets'],list) or len(node['value_targets'])>256:raise ValueError('Invalid destructuring proof')
                for target in node['value_targets']:
                    projection=target.get('projection') if isinstance(target,dict) else None
                    if (not isinstance(projection,dict) or not _enum(projection.get('status'),{'PROVEN','UNKNOWN'})
                            or not _enum(projection.get('kind'),{'DATA_COMPONENT','TUPLE_ELEMENT','OBJECT_PROPERTY'})
                            or type(projection.get('index')) is not int or projection['index']<0
                            or (projection.get('component_target') is not None and (not isinstance(projection['component_target'],str) or projection['component_target'] not in ids))):
                        raise ValueError('Invalid destructuring projection proof')
            if node.get('kind')=='call' and node.get('call_site') is not None:
                site=sites.get(node['call_site']) if isinstance(node['call_site'],str) else None
                if not site or site.get('caller')!=body['method']:raise ValueError('Return call belongs to another caller')
                if 'return_reference_kind' in site and not _enum(site['return_reference_kind'],{'LEXICAL_IDENTIFIER','HARD_PRIVATE_MEMBER','PROPERTY_OR_OTHER'}):
                    raise ValueError('Invalid return callable reference proof')
                if active and (node.get('range')!=site.get('range') or node.get('path')!=site.get('path') or node.get('sha256')!=site.get('sha256')):
                    raise ValueError('Return call source range mismatch')
            # Kotlin's selector call excludes its receiver in the source span;
            # retain the enclosing expression/statement boundary for call children.
            anchor=node if active and located and node['kind']!='call' else parent
            pending.extend((child,depth+1,anchor) for child in _children(node))


class _Projection:
    def __init__(self,graph,bodies,context):
        self.graph,self.context=graph,context
        self.nodes={n.id:n for n in graph.nodes};self.symbols={s['id']:dict(s) for s in graph.symbols}
        self.sites={s['id']:dict(s) for s in graph.call_sites}
        self.bodies={b['method']:b for b in bodies if b.get('context_id')==context['id']}
        self.edges=list(graph.edges);self.evidence=list(graph.evidence);self.evidence_ids={e["id"] for e in graph.evidence};self.diagnostics=list(graph.diagnostics)
        self.returns={};self.supported={};self.pending=[];self.steps=0;self.current=None;self.out_of_scope=set()
        from .callgraph import strongly_connected
        self.recursive={m for component in strongly_connected(graph) for m in component}

    def issue(self,reason,node=None):
        item={'code':reason,'reason':reason,'context_id':self.context['id'],'method':self.current}
        if node:item.update(path=node.get('path'),range=node.get('range'))
        if item not in self.diagnostics:self.diagnostics.append(item)

    def node(self,identity,role,loc,info,**extra):
        if identity in self.nodes:return identity
        if len(self.nodes)-len(self.graph.nodes)>=20000:
            self.issue('RETURN_FLOW_NODE_LIMIT',loc);return None
        caller=self.nodes.get(self.current)
        if not caller or not _range(loc.get('range')) or not _info(info):return None
        metadata={'id':identity,'kind':'value','name':role.lower().replace('_',' '),'value_role':role,
            'owner_method':self.current,'context_id':self.context['id'],'scope':caller.scope,
            'origin':caller.origin,'path':loc.get('path'),'range':loc['range'],'sha256':loc.get('sha256'),
            'value_type':info,'return_mapping_version':1,'availability':'UNKNOWN','runtime_execution':'NOT_OBSERVED',**extra}
        self.symbols[identity]=metadata
        self.nodes[identity]=Node(identity,'value',metadata['name'],loc.get('path') or caller.path,
            line=loc['range'].get('start_line'),scope=caller.scope,role='contract',origin=caller.origin,metadata=metadata)
        return identity

    def edge(self,source,target,loc,kind,*,site=None,condition=None,guards=(),transformation='DIRECT',**extra):
        if source is None or target is None or source not in self.nodes or target not in self.nodes:return
        if len(self.evidence)-len(self.graph.evidence)>=50000:
            self.issue('RETURN_FLOW_EDGE_LIMIT',loc);return
        producer_site=self.symbols.get(source,{}).get('call_site')
        proof={'kind':'SYMBOL_RESOLVED','source':source,'target':target,'relation':'returns_to',
            'return_mapping_version':1,'consumer_kind':kind,'transformation':transformation,'call_site':producer_site or site,
            'producer_call_site':producer_site,'consumer_call_site':site if kind in {'ARGUMENT','RECEIVER'} else None,
            'context_ids':[self.context['id']],'source_file':loc.get('path'),'source_range':loc.get('range'),
            'sha256':loc.get('sha256'),'condition':condition,'branch_guards':list(guards),
            'availability':'UNKNOWN','runtime_execution':'NOT_OBSERVED',**extra}
        identity='evidence:'+digest(proof)
        if identity in self.evidence_ids:return
        self.evidence_ids.add(identity)
        self.evidence.append({'id':identity,**proof})
        self.edges.append(Edge(source,target,'returns_to',evidence_kind='SYMBOL_RESOLVED',context_ids=(self.context['id'],),
            evidence_ids=(identity,),source_file=loc.get('path'),source_line=(loc.get('range') or {}).get('start_line')))

    def direct(self,site):
        target=self.symbols.get(site.get('declared_target'),{})
        body=self.bodies.get(site.get('declared_target'),{})
        if body.get('language')=='typescript':
            return (body.get('return_dispatch')=='HARD_PRIVATE' and site.get('return_reference_kind')=='HARD_PRIVATE_MEMBER') or (body.get('return_dispatch')=='LEXICAL' and site.get('return_reference_kind')=='LEXICAL_IDENTIFIER')
        modifiers=target.get('modifiers') or []
        return (target.get('jvm_static') is True or 'static' in modifiers or 'final' in modifiers or 'private' in modifiers
                or site.get('invocation_kind') in {'STATIC','SPECIAL'} or body.get('return_dispatch') in {'STATIC','PRIVATE'})

    def status(self,site,status,reason):
        site.update(return_mapping_version=1,return_mapping_status=status,return_mapping_reason=reason)

    def expression(self,node,env,guards=(),condition=None,depth=0):
        self.steps+=1
        if self.steps>20000 or depth>128:
            self.supported[self.current]=False;self.issue('RETURN_FLOW_LIMIT',node);return set()
        if not isinstance(node,dict):return set()
        kind=node.get('kind')
        if kind=='call':
            receiver=self.expression(node.get('receiver',{}),env,guards,condition,depth+1)
            arguments=[self.expression(v,env,guards,condition,depth+1) for v in node.get('arguments',[])]
            site=self.sites.get(node.get('call_site'))
            if not site or site.get('caller')!=self.current:return set()
            for role,origins,loc,index in [('RECEIVER',receiver,node.get('receiver',{}),None)]+[
                    ('ARGUMENT',values,node['arguments'][i],i) for i,values in enumerate(arguments)]:
                if not origins:continue
                identity=site['id']+(':receiver' if role=='RECEIVER' else ':argument:'+str(index))
                target=self.node(identity,role,loc,loc.get('value_info',{}),call_site=site['id'],argument_index=index)
                for source in origins:self.edge(source,target,loc,role,site=site['id'],condition=condition,guards=guards)
            target=self.symbols.get(site.get('declared_target'),{});info=node.get('value_info',{})
            if site.get('invocation_kind')=='METHOD_REFERENCE':self.status(site,'NOT_EXECUTION','METHOD_REFERENCE');return set()
            if target.get('name')=='<init>' or target.get('kind')=='constructor' or info.get('status')=='VOID':
                self.status(site,'NOT_VALUE','VOID_UNIT_OR_CONSTRUCTOR');return set()
            if (not target or site.get('evidence_kind')!='SYMBOL_RESOLVED' or not _info(info)
                    or info['status']!='VALUE' or target.get('suspend') or target.get('async') or target.get('generator')):
                self.status(site,'UNKNOWN','RETURN_TYPE_OR_TARGET_UNSUPPORTED');self.issue('RETURN_TYPE_OR_TARGET_UNSUPPORTED',node);return set()
            identity=self.node(site['id']+':result','CALL_RESULT',node,info,call_site=site['id'],declared_target=site['declared_target'],condition=condition)
            self.status(site,'PROVEN','COMPILER_CALL_RESULT_TYPE')
            return {identity} if identity else set()
        if kind=='reference':return set()
        if kind=='safe_call':
            receiver=self.expression(node.get('receiver',{}),env,guards,condition,depth+1)
            value=node.get('then',{});site=self.sites.get(value.get('call_site'))
            if site:
                loc=node.get('receiver',{});identity=self.node(site['id']+':receiver','RECEIVER',loc,loc.get('value_info',{}),call_site=site['id'])
                for source in receiver:self.edge(source,identity,loc,'RECEIVER',site=site['id'],condition='NON_NULL_RECEIVER',guards=guards)
            result=self.expression(value,env,guards,'NON_NULL_RECEIVER',depth+1)
            info=node.get('value_info',{})
            identity=self.current+':safe_result:'+str(node.get('sha256'))+':'+str((node.get('range') or {}).get('start'))
            join=self.node(identity,'CONDITIONAL_RESULT',node,info)
            for source in result:self.edge(source,join,node,'SAFE_RESULT',condition='NON_NULL_RECEIVER',guards=guards,transformation='SAFE_CHAIN')
            for source in receiver:self.edge(source,join,node,'NULL_PROPAGATION',condition='NULL_RECEIVER',guards=guards,transformation='NULL_PATH')
            return {join} if join else set()
        binding=node.get('value_binding')
        if isinstance(binding,dict) and kind not in {'assign','destructure'}:
            if binding.get('method')!=self.current:
                self.supported[self.current]=False;self.issue('RETURN_CAPTURE_OR_FIELD_UNKNOWN',node);return set()
            if binding['id'] in env:return env[binding['id']]
            if binding['kind']=='PARAMETER':
                identity=binding['id']
                if identity not in self.nodes:self.node(identity,'PARAMETER_INPUT',binding,binding['type'],binding_id=identity)
                env[identity]={identity};return env[identity]
            self.supported[self.current]=False;self.issue('RETURN_LOCAL_DEFINITION_UNKNOWN',node);return set()
        if kind=='if':
            self.expression(node.get('condition',{}),env,guards,condition,depth+1)
            left,right=dict(env),dict(env)
            yes=self.expression(node.get('then',{}),left,guards+({'range':node.get('range'),'branch':'TRUE'},),condition,depth+1)
            no=self.expression(node.get('else',{}),right,guards+({'range':node.get('range'),'branch':'FALSE'},),condition,depth+1)
            for key in left.keys()|right.keys():env[key]=left.get(key,set())|right.get(key,set())
            return yes|no
        if kind=='assign':
            values=self.expression(node.get('value',{}),env,guards,condition,depth+1);binding=node.get('value_binding')
            if not isinstance(binding,dict) or binding.get('kind') not in {'LOCAL_VARIABLE','PARAMETER'} or binding.get('method') not in {self.current,None}:
                if values:self.issue('RETURN_CONSUMER_TARGET_UNKNOWN',node)
                self.supported[self.current]=False;return set()
            identity=binding['id']+':write:'+str(node.get('sha256'))+':'+str((node.get('range') or {}).get('start'))
            target=self.node(identity,'ASSIGNMENT',node,binding['type'],binding_id=binding['id'],binding_name=binding['name']) if values else None
            for source in values:self.edge(source,target,node,'ASSIGNMENT',condition=condition,guards=guards,transformation='ASSIGNMENT_CONVERSION')
            env[binding['id']]={target} if target else set();return env[binding['id']]
        if kind=='destructure':
            values=self.expression(node.get('value',{}),env,guards,condition,depth+1)
            for target in node.get('value_targets',[]):
                binding=target['binding']
                identity=binding['id']+':destructure:'+str(node.get('sha256'))+':'+str((node.get('range') or {}).get('start'))
                value=self.node(identity,'DESTRUCTURE',binding,binding['type'],binding_id=binding['id'],binding_name=binding['name'],projection=target['projection'])
                env[binding['id']]={value} if value else set()
                self.pending.append((self.current,values,target,node,guards,condition))
            return set()
        if kind=='sequence':
            result=set()
            for value in node.get('expressions',[]):result=self.expression(value,env,guards,condition,depth+1)
            return result
        if kind=='elvis':
            self.supported[self.current]=False;self.issue('RETURN_ELVIS_FLOW_UNSUPPORTED',node);return set()
        return set()

    def execute(self,node,env,guards=(),depth=0):
        if depth>64:
            self.supported[self.current]=False;self.issue('RETURN_CONTROL_DEPTH_LIMIT',node);return False,guards
        kind=node.get('kind')
        if kind=='block':
            for child in node.get('statements',[]):
                terminated,guards=self.execute(child,env,guards,depth+1)
                if terminated:return True,guards
        elif kind=='return':
            value=node.get('value',{});origins=self.expression(value,env,guards)
            info=value.get('value_info',{})
            if _info(info) and info['status']=='VALUE':
                identity=self.node(self.current+':return_expr:'+str(value.get('sha256'))+':'+str((value.get('range') or {}).get('start')),'RETURN_EXPRESSION',value,info,branch_guards=list(guards))
                if identity:
                    for source in origins:self.edge(source,identity,value,'RETURN_EXPRESSION',guards=guards)
                    self.returns.setdefault(self.current,[]).append((identity,value,guards))
            else:self.supported[self.current]=False;self.issue('RETURN_EXPRESSION_UNKNOWN',value)
            return True,guards
        elif kind=='if':
            self.expression(node.get('condition',{}),env,guards)
            yes_guard=guards+({'range':node.get('range'),'branch':'TRUE'},)
            no_guard=guards+({'range':node.get('range'),'branch':'FALSE'},)
            left,right=dict(env),dict(env)
            yes,_=self.execute(node.get('then',{'kind':'empty'}),left,yes_guard,depth+1)
            no,_=self.execute(node.get('else',{'kind':'empty'}),right,no_guard,depth+1)
            if yes and no:return True,guards
            env.clear()
            if yes:env.update(right);return False,no_guard
            if no:env.update(left);return False,yes_guard
            env.update({key:left.get(key,set())|right.get(key,set()) for key in left.keys()|right.keys()})
        else:self.expression(node,env,guards)
        return False,guards

    def finish(self):
        for method,body in self.bodies.items():
            self.current=method
            declaration=self.nodes.get(method)
            if declaration is None or (self.context.get('scope')!='all' and declaration.scope!=self.context.get('scope')):
                self.out_of_scope.add(method);self.supported[method]=False
                continue
            if body.get('return_flow_version')!=1 or body.get('return_body_kind')!='DECLARED':continue
            self.supported[method]=True
            pending=[body.get('body',{})];unsupported=False
            while pending:
                node=pending.pop()
                if node.get('kind') not in {'block','return','if','call','reference','safe_call','assign','destructure','sequence','statement','empty','true','and','or','elvis'}:unsupported=True;break
                pending.extend(_children(node))
            if unsupported:self.supported[method]=False;self.issue('RETURN_CONTROL_FLOW_UNSUPPORTED',body.get('body'));continue
            self.execute(body.get('body',{}),{})
        for method,values,target,loc,guards,condition in self.pending:
            self.current=method;projection=target['projection'];binding=target['binding'];proven=projection['status']=='PROVEN'
            if projection['kind']!='DATA_COMPONENT':
                shapes=[]
                for value in values:
                    result=self.symbols.get(value,{})
                    site=self.sites.get(result.get('call_site'),{});callee=site.get('declared_target')
                    if not self.supported.get(callee) or callee in self.recursive or not self.direct(site):
                        shapes.append(None)
                    else:shapes.extend(v.get('value_shape') for _,v,_ in self.returns.get(callee,[]))
                proven=proven and bool(shapes) and all(isinstance(s,dict) and s.get('kind')==projection['kind'] and
                    (projection['index']<s.get('size',0) if projection['kind']=='TUPLE_ELEMENT' else projection.get('key') in s.get('keys',[])) for s in shapes)
            if not proven or not values:
                self.supported[method]=False
                self.issue('RETURN_DESTRUCTURING_PROJECTION_UNKNOWN',loc)
                continue
            identity=binding['id']+':destructure:'+str(loc.get('sha256'))+':'+str((loc.get('range') or {}).get('start'))
            node=self.node(identity,'DESTRUCTURE',binding,binding['type'],binding_id=binding['id'],binding_name=binding['name'],projection=projection)
            for value in values:self.edge(value,node,loc,'DESTRUCTURE',guards=guards,condition=condition,transformation=projection['kind'],projection=projection)
        for method,body in self.bodies.items():
            self.current=method;symbol=self.symbols.get(method,{})
            returns=self.returns.get(method,[])
            if not self.supported.get(method) or method in self.recursive or not returns:continue
            info=body.get('return_type',{})
            if not _info(info) or info['status']!='VALUE':continue
            contract=self.node(method+':return','DECLARED_RETURN',symbol,info,method=method)
            for identity,loc,guards in returns:self.edge(identity,contract,loc,'DECLARED_RETURN',guards=guards,transformation='RETURN_ALTERNATIVE')
        for site in self.sites.values():
            if site.get('context_id')!=self.context['id']:continue
            self.current=site.get('caller');target=site.get('declared_target');body=self.bodies.get(target,{})
            contract=target+':return' if target else None;result=site['id']+':result'
            if result in self.nodes and contract in self.nodes and self.direct(site) and target not in self.recursive and set(site.get('dispatch_candidates',[])) <= {target}:
                self.edge(contract,result,site,'CALL_RESULT',site=site['id'],condition=self.symbols[result].get('condition'),transformation='DECLARED_BODY_RETURN',declared_target=target)
                site['return_body_status']='DECLARED_SOURCE_BODY'
                site['return_body_reason']='COMPILER_PROVEN_DIRECT_SOURCE_BODY'
            else:
                site['return_body_status']='UNKNOWN'
                site['return_body_reason']='DECLARED_BODY_PROOF_UNAVAILABLE'
                if body.get('return_ir_reason')=='RETURN_SOURCE_NOT_CAPTURED':site['return_body_reason']='RETURN_SOURCE_NOT_CAPTURED'
                elif target in self.out_of_scope:site['return_body_reason']='RETURN_SOURCE_SCOPE_NOT_SELECTED'
                elif body.get('language')=='typescript' and not self.direct(site):
                    boundary=body.get('return_binding_boundary')
                    site['return_body_reason']=(boundary if isinstance(boundary,str) else None) or ('TS_CALLEE_IDENTITY_NOT_CLOSED'
                        if body.get('return_dispatch') in ('LEXICAL','HARD_PRIVATE') else 'TS_MUTABLE_BODY_BINDING')
            if 'return_mapping_version' not in site:
                self.status(site,'NOT_EXECUTION' if site.get('invocation_kind')=='METHOD_REFERENCE' else 'UNKNOWN',
                    'METHOD_REFERENCE' if site.get('invocation_kind')=='METHOD_REFERENCE' else 'RETURN_SOURCE_IR_UNAVAILABLE')
        return replace(self.graph,nodes=sorted(self.nodes.values(),key=lambda n:n.id),edges=self.edges,
            symbols=sorted(self.symbols.values(),key=lambda n:n['id']),call_sites=list(self.sites.values()),
            evidence=self.evidence,diagnostics=self.diagnostics)


def augment_return_flow(graph:KnowledgeGraph,bodies:list[dict],context:dict)->KnowledgeGraph:
    return _Projection(graph,bodies,context).finish()


def return_consumer_bindings(graph:KnowledgeGraph,call_site:str|None=None)->list[dict]:
    proofs={p['id']:p for p in graph.evidence}
    result=[]
    for edge in graph.edges:
        if edge.kind!='returns_to' or edge.evidence_kind!='SYMBOL_RESOLVED':continue
        for identity in edge.evidence_ids:
            proof=proofs.get(identity,{})
            if (proof.get('return_mapping_version')!=1 or proof.get('source')!=edge.source or proof.get('target')!=edge.target):continue
            if call_site is not None and call_site not in {proof.get('call_site'),proof.get('producer_call_site'),proof.get('consumer_call_site')}:continue
            result.append(dict(proof))
    return sorted(result,key=lambda p:(p['source'],p['target'],p['consumer_kind']))
