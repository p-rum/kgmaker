'use strict';
// Bounded, compiler-bound value occurrences. No evaluation or application I/O.
const path=require('node:path');
const VERSION=1;
function collect(api) {
  const {ts,functions,checkerFor,location,binding,siteFor,symbols,facts,context,adapters,diagnostics,resolvedSite}=api;
  const values=new Map(),states=new Map(),setters=new Map(),writes=new Map(),mutated=new Set(),escapes=new Set(),poisoned=new Set();
  const libDom=path.resolve(path.dirname(require.resolve('typescript')),'lib.dom.d.ts');
  const key=n=>binding(n)?.id;
  const symbolAt=n=>{const c=checkerFor(n);let s=c.getSymbolAtLocation(n);return s?.flags&ts.SymbolFlags.Alias?c.getAliasedSymbol(s):s;};
  function root(n){while(n&&(ts.isPropertyAccessExpression(n)||ts.isElementAccessExpression(n)))n=n.expression;return n;}
  function audit(n) {
    if(ts.isBinaryExpression(n)&&n.operatorToken.kind>=ts.SyntaxKind.FirstAssignment&&n.operatorToken.kind<=ts.SyntaxKind.LastAssignment)mutated.add(key(root(n.left)));
    if((ts.isPostfixUnaryExpression(n)||ts.isPrefixUnaryExpression(n))&&[ts.SyntaxKind.PlusPlusToken,ts.SyntaxKind.MinusMinusToken].includes(n.operator))mutated.add(key(root(n.operand)));
    if(ts.isDeleteExpression(n))mutated.add(key(root(n.expression)));
    if(ts.isBinaryExpression(n)&&n.operatorToken.kind>=ts.SyntaxKind.FirstAssignment&&n.operatorToken.kind<=ts.SyntaxKind.LastAssignment)poisoned.add(symbolAt(ts.isPropertyAccessExpression(n.left)?n.left.name:n.left));
    if(ts.isCallExpression(n))for(const arg of n.arguments)if(ts.isIdentifier(arg)){const type=checkerFor(arg).getTypeAtLocation(arg);if(!(type.flags&(ts.TypeFlags.StringLike|ts.TypeFlags.NumberLike|ts.TypeFlags.BooleanLike|ts.TypeFlags.BigIntLike)))mutated.add(key(arg));}
    ts.forEachChild(n,audit);
  }
  const sources=[...new Set(functions.map(f=>f.getSourceFile()))];sources.forEach(audit);
  function official(n,name,owner) {
    const s=symbolAt(n);return !poisoned.has(s)&&!!s?.declarations?.length&&s.declarations.every(d=>path.resolve(d.getSourceFile().fileName)===libDom&&d.name?.getText()===name&&(!owner||d.parent.name?.text===owner));
  }
  function occurrence(n,role,extra={}) {
    const loc=location(n),suffix=Object.hasOwn(extra,'projection_key')?':projection:'+encodeURIComponent(String(extra.projection_key)):'';
    const id=`value:${context.id}:${loc.path}:${loc.sha256}:${loc.range.start}:${loc.range.end}:${role}${suffix}`;
    if(context.source_files?.[loc.path]!==loc.sha256)throw Error('VALUE_SOURCE_NOT_CAPTURED');
    if(!symbols.has(id)&&symbols.size>=api.limit)throw Error('symbol output limit exceeded');
    symbols.set(id,{id,kind:'value_occurrence',name:role,...loc,scope:context.scope,context_id:context.id,
      value_flow_version:VERSION,value_role:role,runtime_execution:'NOT_OBSERVED',availability:'UNKNOWN',...extra});return id;
  }
  function edge(from,to,kind,n,extra={}) {
    facts.push({source:from,target:to,kind,...location(n),value_flow_version:VERSION,evidence_kind:kind==='writes_value'?'FRAMEWORK_DERIVED':'SYMBOL_RESOLVED',
      runtime_execution:'NOT_OBSERVED',availability:'UNKNOWN',...extra});
  }
  function project(value,n,role,extra={}) {
    const result={...value,id:occurrence(n,role,{request: value.request,field:value.field??null,...extra})};
    edge(value.id,result.id,'maps_to',n);return result;
  }
  // State names/setter names are irrelevant: their declaration symbols and the
  // selected pinned React declaration establish the pair.
  for(const fn of functions) {
    function discover(n) {
      if(n!==fn&&ts.isFunctionLike(n))return;
      if(ts.isVariableDeclaration(n)&&ts.isArrayBindingPattern(n.name)&&n.name.elements.length===2&&n.initializer&&ts.isCallExpression(n.initializer)&&n.parent.flags&ts.NodeFlags.Const) {
        const call=n.initializer,adapter=adapters.get(path.resolve(n.getSourceFile().fileName));
        const callee=ts.isPropertyAccessExpression(call.expression)?call.expression.name:call.expression;
        const s=symbolAt(callee),entries=n.name.elements;
        if(adapter?.declaration&&!poisoned.has(s)&&s?.declarations?.length&&s.declarations.every(d=>ts.isFunctionDeclaration(d)&&d.name?.text==='useState'&&path.resolve(d.getSourceFile().fileName)===adapter.declaration)&&entries.every(e=>ts.isBindingElement(e)&&ts.isIdentifier(e.name)&&!e.initializer&&!e.dotDotDotToken)) {
          const state=key(entries[0].name),setter=key(entries[1].name);
          if(state&&setter&&!mutated.has(state)&&!mutated.has(setter)) {
            const record={state,setter,node:entries[0],adapter:adapter.snapshot};states.set(state,record);setters.set(setter,record);
          }
        }
      }
      ts.forEachChild(n,discover);
    }discover(fn);
  }
  // Refuse aliases/escapes of a setter, or multiple assignments. An updater
  // callback does not imply its returned value is the next state.
  for(const source of sources) {
    function refs(n) {
      if(ts.isIdentifier(n)&&setters.has(key(n))&&!ts.isBindingElement(n.parent)) {
        if(ts.isCallExpression(n.parent)&&n.parent.expression===n)writes.set(key(n),(writes.get(key(n))||0)+1);
        else escapes.add(key(n));
      }ts.forEachChild(n,refs);
    }refs(source);
  }
  function propertyDeclaration(at,field) {
    const c=checkerFor(at),property=c.getPropertyOfType(c.getTypeAtLocation(at),field);
    const declarations=property?.declarations||[];
    if(declarations.length!==1||!ts.isPropertySignature(declarations[0]))return null;
    const d=declarations[0],loc=location(d);
    if(context.source_files?.[loc.path]!==loc.sha256)return null;
    return {symbol:api.register(d),...loc};
  }
  function evaluate(n,env) {
    if(!n)return null;
    if(ts.isParenthesizedExpression(n)||ts.isAsExpression(n)||ts.isTypeAssertionExpression(n)||ts.isSatisfiesExpression(n)||ts.isNonNullExpression(n))return evaluate(n.expression,env);
    if(ts.isAwaitExpression(n)){const value=evaluate(n.expression,env);return value?.stage==='response_pending'?{...value,stage:'response'}:value?.stage==='json_pending'?{...value,stage:'json'}:null;}
    if(ts.isIdentifier(n))return mutated.has(key(n))?null:env.get(key(n))||values.get(key(n))||null;
    if(ts.isCallExpression(n)) {
      const site=siteFor(n);
      if(n.arguments.length===1&&ts.isStringLiteral(n.arguments[0])&&official(n.expression,'fetch')) {
        const request={call_site:site,method:'GET',path:n.arguments[0].text};
        if(!site||!request.path.startsWith('/')||/[?#]/.test(request.path))return null;
        return {id:occurrence(n,'HTTP_RESPONSE',{request}),request,stage:'response_pending'};
      }
      if(ts.isPropertyAccessExpression(n.expression)&&n.arguments.length===0&&official(n.expression.name,'json','Body')) {
        const value=evaluate(n.expression.expression,env);
        if(value?.stage==='response')return {...project(value,n,'JSON_RESULT'),stage:'json_pending'};
      }
      return null;
    }
    if(ts.isPropertyAccessExpression(n)) {
      const value=evaluate(n.expression,env),field=n.name.text;
      if(value?.properties?.has(field))return project(value.properties.get(field),n,'FIELD_READ');
      if(value?.stage==='json')return {...project({...value,field},n,'FIELD_READ',{json_projection:true,field_declaration:propertyDeclaration(n.expression,field)}),stage:'field'};
      return null;
    }
    if(ts.isObjectLiteralExpression(n)) {
      const properties=new Map();
      for(const p of n.properties) {
        if(!(ts.isPropertyAssignment(p)||ts.isShorthandPropertyAssignment(p))||!ts.isIdentifier(p.name))return null;
        let value;
        if(ts.isShorthandPropertyAssignment(p)) {
          const s=checkerFor(p).getShorthandAssignmentValueSymbol(p),d=s?.valueDeclaration;
          value=d?env.get(key(d))||values.get(key(d)):null;
        } else value=evaluate(p.initializer,env);
        if(value?.stage==='field')properties.set(p.name.text,project(value,p,'OBJECT_MAPPING'));
      }
      return properties.size?{properties}:null;
    }
    return null;
  }
  const ui=[];
  function visit(n,env) {
    if(!n)return;
    if(ts.isBlock(n)){for(const s of n.statements)visit(s,env);return;}
    if(ts.isVariableStatement(n)){if(n.declarationList.flags&ts.NodeFlags.Const)for(const d of n.declarationList.declarations)visit(d,env);return;}
    if(ts.isVariableDeclaration(n)) {
      const value=evaluate(n.initializer,env);if(!value)return;
      if(ts.isIdentifier(n.name)&&!mutated.has(key(n)))env.set(key(n),value.id?project(value,n,'ASSIGNMENT',{binding_id:key(n)}):value);
      else if(ts.isObjectBindingPattern(n.name))for(const e of n.name.elements) {
        const field=e.propertyName||e.name;
        if(e.dotDotDotToken||e.initializer||!ts.isIdentifier(e.name)||!ts.isIdentifier(field)||mutated.has(key(e)))continue;
        const origin=value.properties?.get(field.text)||(value.stage==='json'?{...value,field:field.text}:null);
        if(origin)env.set(key(e),{...project(origin,e,'DESTRUCTURE',{binding_id:key(e),json_projection:value.stage==='json',field_declaration:propertyDeclaration(n.initializer,field.text)}),stage:'field'});
      }return;
    }
    if(ts.isExpressionStatement(n))return visit(n.expression,env);
    if(ts.isCallExpression(n)) {
      const setter=setters.get(key(n.expression));
      if(setter&&writes.get(setter.setter)===1&&!escapes.has(setter.setter)&&n.arguments.length===1) {
        const value=evaluate(n.arguments[0],env);
        if(value) {
          const properties=new Map(),items=value.properties||new Map([[null,value]]);
          for(const [field,origin] of items)if(origin.stage==='field') {
            const id=occurrence(n,'STATE_WRITE',{projection_key:field,binding_id:setter.state,setter_binding:setter.setter,request:origin.request,field:origin.field,ui_adapter:setter.adapter});
            edge(origin.id,id,'writes_value',n,{ui_adapter:setter.adapter});properties.set(field,{...origin,id});
          }
          if(properties.size)values.set(setter.state,properties.has(null)?properties.get(null):{properties});
        }
      } else if(resolvedSite(n)&&!ts.isPropertyAccessExpression(n.expression)) {
        // The graph describes the exact argument consumer; repository role
        // supplies test classification, never a magic expect/assert spelling.
        for(let i=0;i<n.arguments.length;i++) {
          const value=evaluate(n.arguments[i],env);
          if(value?.stage==='field') {
            const id=occurrence(n.arguments[i],'ARGUMENT',{call_site:siteFor(n),argument_index:i,request:value.request,field:value.field});
            edge(value.id,id,'passes_value',n.arguments[i]);
          }
        }
      }return;
    }
    if(ts.isReturnStatement(n)) {if(n.expression)collectUi(n.expression,env);return;}
    // No propagation through conditional/loop/try or callback control flow.
    if(ts.isIfStatement(n)||ts.isIterationStatement(n,false)||ts.isTryStatement(n))diagnostics.push({code:'FRONTEND_VALUE_CONTROL_FLOW_UNKNOWN',...location(n)});
  }
  function collectUi(n,env) {
    if(ts.isJsxElement(n)) {
      const tag=n.openingElement.tagName;
      if(ts.isIdentifier(tag)&&ts.isIntrinsicJsxName(tag.text))for(const child of n.children) {
        if(ts.isJsxExpression(child)&&child.expression)ui.push({node:child.expression,env:new Map(env)});
        else if(ts.isJsxElement(child))collectUi(child,env);
      }
    } else if(ts.isJsxFragment(n))for(const child of n.children)collectUi(child,env);
  }
  // Each method has its own environment. Only compiler-bound React state is
  // shared with its closures, not arbitrary same-name values.
  for(const fn of functions)if(fn.body&&ts.isBlock(fn.body))visit(fn.body,new Map());
  for(const item of ui) {
    const value=evaluate(item.node,item.env);
    if(value?.stage==='field') {
      const id=occurrence(item.node,'JSX_CONSUMER',{request:value.request,field:value.field});
      edge(value.id,id,'displayed_in',item.node);
    }
  }
}
module.exports={collect,VERSION};
