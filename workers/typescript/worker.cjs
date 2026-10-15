'use strict';
// One bounded JSON request/response. Never run npm or application code.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const ts = require('typescript');
const PROTOCOL = 1;
const VERSION = 'typescript-worker-1';
const hash = value => crypto.createHash('sha256').update(value).digest('hex');
const canonical = value => JSON.stringify(value);

function handshake() {
  return {protocol_version:PROTOCOL,worker:VERSION,compiler_version:ts.version,
    capabilities:['typescript-program','typechecker','overloads','aliases','project-references','source-ir','react-events'],
    limitations:['No Angular/Vue template semantics.','Dynamic callbacks/any remain unresolved.','Source IR is not runtime ordering.']};
}

function analyze(request) {
  const root = fs.realpathSync(request.root);
  const context = request.context;
  if (!context || typeof context.id !== 'string') throw Error('context.id is required');
  const prefix = `ts:${context.repo_id}:${context.module}:${context.source_set}:${context.id}`;
  const limits = {symbols:20000,calls:50000,...request.limits};
  const symbols = new Map(), sites = [], bodies = [], facts = [], diagnostics = [], inputs = new Map();
  const identityCache = new WeakMap();
  const functionNodes = [];
  const rootFileSet = new Set();

  function inside(file) {
    const relative = path.relative(root, file);
    return relative !== '..' && !relative.startsWith('..' + path.sep) && !path.isAbsolute(relative);
  }
  function fileInfo(source) {
    const file = source.fileName;
    const bytes = fs.readFileSync(file);
    let relative;
    let origin = 'handwritten';
    if (inside(file) && !file.includes(path.sep+'node_modules'+path.sep)) {
      relative = path.relative(root,file).split(path.sep).join('/');
    } else {
      origin = 'dependency';
      const marker = file.lastIndexOf(path.sep+'node_modules'+path.sep);
      relative = 'dependency/' + (marker >= 0 ? file.slice(marker+14).split(path.sep).join('/') : hash(bytes)+'/'+path.basename(file));
    }
    const sha256 = hash(bytes);
    inputs.set(file,{path:relative,sha256,origin});
    return {path:relative,sha256,origin};
  }
  function location(node) {
    const source = node.getSourceFile();
    const start = node.getStart(source), end = node.getEnd();
    const p = source.getLineAndCharacterOfPosition(start);
    const q = source.getLineAndCharacterOfPosition(end);
    return {...fileInfo(source),range:{start,end,start_line:p.line+1,start_column:p.character+1,end_line:q.line+1,end_column:q.character+1}};
  }
  function name(node) {
    if (node.name) return node.name.getText();
    if ((ts.isArrowFunction(node) || ts.isFunctionExpression(node)) && ts.isVariableDeclaration(node.parent))
      return node.parent.name.getText();
    if (ts.isConstructorDeclaration(node)) return 'constructor';
    return '<anonymous>';
  }
  function owner(node) {
    const names = [];
    for (let p=node.parent; p && !ts.isSourceFile(p); p=p.parent)
      if (ts.isClassLike(p) || ts.isInterfaceDeclaration(p) || ts.isModuleDeclaration(p) || ts.isFunctionLike(p))
        names.unshift(name(p));
    return names.join('.');
  }
  function callable(node) {
    return ts.isFunctionDeclaration(node) || ts.isMethodDeclaration(node) || ts.isArrowFunction(node) ||
      ts.isFunctionExpression(node) || ts.isConstructorDeclaration(node) || ts.isGetAccessorDeclaration(node) || ts.isSetAccessorDeclaration(node);
  }
  function id(node) {
    if (identityCache.has(node)) return identityCache.get(node);
    const loc = location(node);
    let signature = '';
    if (callable(node) || ts.isMethodSignature(node) || ts.isConstructSignatureDeclaration(node) || ts.isCallSignatureDeclaration(node)) {
      const s = checker.getSignatureFromDeclaration(node);
      if (s) signature = checker.signatureToString(s,node,ts.TypeFormatFlags.NoTruncation);
    }
    let value = `${prefix}:${loc.path}:${owner(node)}:${name(node)}:${signature || ts.SyntaxKind[node.kind]}`;
    if (ts.isParameter(node) && node.parent.parameters) {
      value=id(node.parent)+':parameter:'+node.parent.parameters.indexOf(node);
    }
    if (name(node) === '<anonymous>' || (node.parent && ts.isBlock(node.parent)))
      value += `:snapshot:${loc.sha256}:${loc.range.start}`;
    identityCache.set(node,value);
    return value;
  }
  function register(node, kind) {
    const identity = id(node);
    if (!symbols.has(identity)) {
      if (symbols.size >= limits.symbols) throw Error('symbol output limit exceeded');
      const loc = location(node);
      const type = node.name ? checker.getTypeAtLocation(node.name) : checker.getTypeAtLocation(node);
      symbols.set(identity,{id:identity,name:name(node),owner:owner(node),kind:kind || (callable(node)?'function':ts.SyntaxKind[node.kind]),
        type:checker.typeToString(type,node,ts.TypeFormatFlags.NoTruncation),...loc,
        identity_stability:identity.includes(':snapshot:')?'SNAPSHOT':'DECLARATION',
        scope:context.scope,context_id:context.id});
    }
    return identity;
  }
  function symbolDeclaration(symbol) {
    if (!symbol) return null;
    if (symbol.flags & ts.SymbolFlags.Alias) symbol = checker.getAliasedSymbol(symbol);
    return symbol.valueDeclaration || symbol.declarations?.[0] || null;
  }
  function targetForExpression(expression) {
    if (callable(expression)) return expression;
    const declaration = symbolDeclaration(checker.getSymbolAtLocation(expression));
    if (declaration && ts.isVariableDeclaration(declaration) && declaration.initializer && callable(declaration.initializer))
      return declaration.initializer;
    return declaration && callable(declaration) ? declaration : null;
  }
  function safeText(node) {
    if (!node) return null;
    // Source ranges remain exact; displayed literals cannot leak payloads/tokens.
    return node.getText().replace(/(['"`])(?:\\.|(?!\1)[^\\])*?\1/g,'"…"').slice(0,300);
  }
  function literal(node, seen=new Set()) {
    if (!node || seen.has(node)) return null;
    seen.add(node);
    if (ts.isStringLiteralLike(node)) return node.text;
    if (ts.isParenthesizedExpression(node)) return literal(node.expression,seen);
    if (ts.isBinaryExpression(node) && node.operatorToken.kind===ts.SyntaxKind.PlusToken) {
      const a=literal(node.left,seen), b=literal(node.right,seen);
      return a!==null && b!==null ? a+b : null;
    }
    if (ts.isIdentifier(node)) {
      const d=symbolDeclaration(checker.getSymbolAtLocation(node));
      if (d && ts.isVariableDeclaration(d) && d.initializer &&
          (d.parent.flags & ts.NodeFlags.Const)) return literal(d.initializer,seen);
    }
    return null;
  }
  function safeUri(uri) {
    if (uri === null) return null;
    return uri.replace(/(https?:\/\/)[^/@\s]+:[^/@\s]+@/gi,'$1[redacted]@')
      .replace(/([?&](?:token|password|secret|api[_-]?key|authorization)=)[^&]*/gi,'$1[redacted]');
  }

  const tsconfig = path.resolve(root, request.tsconfig || 'tsconfig.json');
  if (!inside(tsconfig)) throw Error('tsconfig escapes root');
  const transportInputs = new Map();
  const readFile = file => {
    const text = ts.sys.readFile(file);
    if (text !== undefined) transportInputs.set(path.resolve(file), {path:path.resolve(file),sha256:hash(fs.readFileSync(file))});
    return text;
  };
  const parsed = ts.getParsedCommandLineOfConfigFile(tsconfig,{}, {...ts.sys,readFile,onUnRecoverableConfigFileDiagnostic:d=>{throw Error(ts.flattenDiagnosticMessageText(d.messageText,'\n'));}});
  if (!parsed) throw Error('Unable to parse tsconfig');
  if (parsed.errors.length) throw Error(ts.formatDiagnostics(parsed.errors,{getCanonicalFileName:p=>p,getCurrentDirectory:()=>root,getNewLine:()=> '\n'}));
  const host=ts.createCompilerHost(parsed.options); host.readFile=readFile;
  const program = ts.createProgram({rootNames:parsed.fileNames,options:parsed.options,projectReferences:parsed.projectReferences,host});
  const checker = program.getTypeChecker();
  if (request.operation === 'project') {
    return {...handshake(),status:'COMPLETE',context_id:context.id,project:{
      input_files:[...transportInputs.values()].sort((a,b)=>a.path.localeCompare(b.path)),
      compiler_options:parsed.options,project_references:(parsed.projectReferences||[]).map(r=>r.path)}};
  }
  for (const diagnostic of ts.getPreEmitDiagnostics(program)) {
    diagnostics.push({code:'TS'+diagnostic.code,reason:ts.flattenDiagnosticMessageText(diagnostic.messageText,'\n'),
      path:diagnostic.file?fileInfo(diagnostic.file).path:null,start:diagnostic.start??null});
  }
  const projectFiles = program.getSourceFiles().filter(s=>inside(s.fileName) && !s.isDeclarationFile && !s.fileName.includes(path.sep+'node_modules'+path.sep));
  parsed.fileNames.forEach(f=>rootFileSet.add(f));
  const siteByNode = new WeakMap();
  function visit(node,caller) {
    if (callable(node)) {
      caller=register(node);
      if (node.body) functionNodes.push(node);
    } else if (ts.isClassLike(node) || ts.isInterfaceDeclaration(node) || ts.isTypeAliasDeclaration(node) ||
               ts.isEnumDeclaration(node) || ts.isEnumMember(node) || ts.isPropertyDeclaration(node) || ts.isPropertySignature(node)) {
      register(node);
    }
    if (ts.isCallExpression(node) || ts.isNewExpression(node)) {
      if (sites.length>=limits.calls) throw Error('call site output limit exceeded');
      const loc=location(node);
      const identity=`call:${caller}:${loc.sha256}:${loc.range.start}:${loc.range.end}`;
      const expressionType=checker.getTypeAtLocation(node.expression);
      const signature=checker.getResolvedSignature(node);
      const declaration=signature?.getDeclaration();
      let target=null, reason=null;
      if (expressionType.flags & (ts.TypeFlags.Any|ts.TypeFlags.Unknown)) reason='DYNAMIC_ANY';
      else if (!declaration) reason='MISSING_CALL_SIGNATURE_DECLARATION';
      else if (!callable(declaration) && !ts.isMethodSignature(declaration) && !ts.isConstructSignatureDeclaration(declaration) && !ts.isCallSignatureDeclaration(declaration)) reason='DYNAMIC_CALLBACK';
      else target=register(declaration);
      const symbol=checker.getSymbolAtLocation(node.expression);
      const site={id:identity,caller,...loc,declared_target:target,dispatch_candidates:[],dispatch_complete:false,
        invocation_kind:ts.isNewExpression(node)?'CONSTRUCTOR':'CALL',receiver_type:ts.isPropertyAccessExpression(node.expression) || ts.isElementAccessExpression(node.expression) ? checker.typeToString(checker.getTypeAtLocation(node.expression.expression)) : null,
        callable_type:checker.typeToString(expressionType),
        signature:signature?checker.signatureToString(signature):null,
        resolution_reason:reason || 'TYPESCRIPT_RESOLVED_SIGNATURE',evidence_kind:target?'SYMBOL_RESOLVED':'UNRESOLVED',
        context_id:context.id};
      if (symbol) site.expression_symbol=checker.getFullyQualifiedName(symbol);
      sites.push(site); siteByNode.set(node,identity);
      if (reason) diagnostics.push({code:reason,path:loc.path,range:loc.range,call_site:identity});
      if (target && signature) {
        for (let i=0; i<(node.arguments||[]).length && i<signature.parameters.length; i++) {
          const d=signature.parameters[i].valueDeclaration || signature.parameters[i].declarations?.[0];
          const a=symbolDeclaration(checker.getSymbolAtLocation(node.arguments[i]));
          if (a && d) facts.push({kind:'argument_to_parameter',source:register(a),target:register(d),...loc,evidence_kind:'SYMBOL_RESOLVED'});
        }
      }
      const targetLoc=declaration?location(declaration):null;
      const isFetch=target && symbol?.name==='fetch' && targetLoc?.origin==='dependency' && /lib\.dom\.d\.ts$/.test(targetLoc.path);
      const isAxios=target && targetLoc?.origin==='dependency' && /axios/.test(targetLoc.path) && ts.isPropertyAccessExpression(node.expression);
      if (isFetch || isAxios) {
        let method=isFetch?'GET':node.expression.name.text.toUpperCase();
        let methodKnown=true;
        if (isFetch && node.arguments[1]) {
          if (!ts.isObjectLiteralExpression(node.arguments[1])) methodKnown=false;
          else for (const p of node.arguments[1].properties) if (ts.isPropertyAssignment(p) && p.name.getText()==='method') {
            const value=literal(p.initializer); if (value===null) methodKnown=false; else method=value.toUpperCase();
          }
        }
        const uri=safeUri(literal(node.arguments[0]));
        site.integration={kind:'http',method:methodKnown?method:null,uri,execution:'REQUEST_EXECUTION',
          service_id:context.service_id||null,contract_id:context.contract_id||null,environment:context.environment||null};
        if (!uri || !methodKnown) diagnostics.push({code:'UNRESOLVED_HTTP_REQUEST',call_site:identity,path:loc.path});
      }
    }
    if (ts.isPropertyAccessExpression(node)) {
      const d=symbolDeclaration(checker.getSymbolAtLocation(node.name));
      if (d && (ts.isPropertyDeclaration(d) || ts.isPropertySignature(d) || ts.isEnumMember(d))) {
        const write=ts.isBinaryExpression(node.parent) && node.parent.left===node &&
          node.parent.operatorToken.kind>=ts.SyntaxKind.FirstAssignment && node.parent.operatorToken.kind<=ts.SyntaxKind.LastAssignment;
        facts.push({kind:ts.isEnumMember(d)?'reads_constant':write?'writes_field':'reads_field',source:caller,target:register(d),...location(node),evidence_kind:'SYMBOL_RESOLVED'});
      }
    }
    if (request.ui_framework==='react' && ts.isJsxAttribute(node) && ['onClick','onChange','onSubmit'].includes(node.name.text)) {
      let attributeSymbol=checker.getSymbolAtLocation(node.name);
      {
        const opening=node.parent.parent;
        const tag=opening.tagName?.getText();
        const intrinsic=checker.getJsxIntrinsicTagNamesAt(node).find(s=>s.name===tag);
        if (intrinsic) attributeSymbol=checker.getPropertyOfType(checker.getTypeOfSymbolAtLocation(intrinsic,node),node.name.text);
      }
      const attributeDeclaration=symbolDeclaration(attributeSymbol);
      const attrLoc=attributeDeclaration?location(attributeDeclaration):null;
      const expression=node.initializer && ts.isJsxExpression(node.initializer)?node.initializer.expression:null;
      const handler=expression?targetForExpression(expression):null;
      if (handler && attrLoc && /@types\/react/.test(attrLoc.path)) {
        facts.push({kind:'handles_event',source:caller,target:register(handler),event:node.name.text,
          ...location(node),evidence_kind:'FRAMEWORK_DERIVED',rule:'react-18.3.1/jsx-event-1'});
      } else diagnostics.push({code:'UNRESOLVED_UI_HANDLER',...location(node)});
    }
    if (ts.isImportSpecifier(node) || ts.isExportSpecifier(node)) {
      const alias=checker.getSymbolAtLocation(node.name);
      const original=symbolDeclaration(alias);
      if (alias && original && original!==node) facts.push({kind:'alias_of',source:register(node,'alias'),target:register(original),...location(node),evidence_kind:'SYMBOL_RESOLVED'});
    }
    ts.forEachChild(node,child=>visit(child,caller));
  }
  for (const source of projectFiles) {
    const loc=fileInfo(source);
    const moduleId=`${prefix}:${loc.path}:<module>`;
    symbols.set(moduleId,{id:moduleId,name:'<module>',kind:'module',owner:'',...loc,range:{start:0,end:source.end,start_line:1,start_column:1},scope:context.scope,context_id:context.id});
    visit(source,moduleId);
  }

  function calls(node) {
    const result=[];
    function v(n) {
      if (n!==node && callable(n)) return;
      const identity=siteByNode.get(n); if(identity) result.push(identity);
      ts.forEachChild(n,v);
    }
    if(node) v(node);
    return result;
  }
  function ir(node) {
    if (!node) return {kind:'empty'};
    const base={...location(node),label:safeText(node),calls:calls(node)};
    if (callable(node)) return {...base,kind:'reference',calls:[]};
    if (ts.isJsxExpression(node)) return ir(node.expression);
    if (ts.isJsxElement(node) || ts.isJsxSelfClosingElement(node) || ts.isJsxFragment(node)) {
      const opening=ts.isJsxElement(node)?node.openingElement:node;
      const attributes=opening.attributes?.properties || [];
      const values=attributes.map(a=>ts.isJsxSpreadAttribute(a)?ir(a.expression):ir(a.initializer));
      const children=(node.children||[]).filter(c=>!ts.isJsxText(c)).map(ir);
      return {...base,kind:'block',statements:[...values,...children,{...base,kind:'statement',calls:[],label:'JSX element construction'}]};
    }
    if (ts.isParenthesizedExpression(node)) return ir(node.expression);
    if (ts.isCallExpression(node) || ts.isNewExpression(node)) {
      const value={...base,kind:'call',call_site:siteByNode.get(node)||null,
        arguments:(node.arguments||[]).map(ir),receiver:ts.isPropertyAccessExpression(node.expression)?ir(node.expression.expression):{kind:'empty'}};
      if(ts.isPropertyAccessExpression(node.expression) && node.expression.questionDotToken)
        return {...base,kind:'safe_call',receiver:value.receiver,then:{...value,receiver:{kind:'empty'}}};
      return value;
    }
    if(ts.isVariableStatement(node))return {...base,kind:'block',statements:node.declarationList.declarations.map(ir)};
    if(ts.isVariableDeclaration(node))return {...base,kind:'assign',value:ir(node.initializer)};
    if(ts.isBinaryExpression(node) && node.operatorToken.kind>=ts.SyntaxKind.FirstAssignment && node.operatorToken.kind<=ts.SyntaxKind.LastAssignment)
      return {...base,kind:'assign',value:ir(node.right)};
    if (ts.isBlock(node)) return {...base,kind:'block',statements:node.statements.map(ir)};
    if (ts.isIfStatement(node)) return {...base,kind:'if',condition:ir(node.expression),then:ir(node.thenStatement),else:ir(node.elseStatement)};
    if (ts.isWhileStatement(node) || ts.isDoStatement(node)) return {...base,kind:ts.isDoStatement(node)?'do':'while',condition:ir(node.expression),body:ir(node.statement)};
    if (ts.isForStatement(node)) return {...base,kind:'for',initial:ir(node.initializer),condition:node.condition?ir(node.condition):{kind:'true'},update:ir(node.incrementor),body:ir(node.statement)};
    if (ts.isForOfStatement(node) || ts.isForInStatement(node)) return {...base,kind:'foreach',body:ir(node.statement),iterable:ir(node.expression)};
    if (ts.isReturnStatement(node)) return {...base,kind:'return',value:ir(node.expression)};
    if (ts.isThrowStatement(node)) return {...base,kind:'throw',value:ir(node.expression)};
    if (ts.isBreakStatement(node) || ts.isContinueStatement(node)) return {...base,kind:ts.isBreakStatement(node)?'break':'continue'};
    if (ts.isTryStatement(node)) return {...base,kind:'try',body:ir(node.tryBlock),catches:node.catchClause?[{type:'unknown',body:ir(node.catchClause.block)}]:[],finally:node.finallyBlock?ir(node.finallyBlock):null};
    if (ts.isConditionalExpression(node)) return {...base,kind:'if',condition:ir(node.condition),then:ir(node.whenTrue),else:ir(node.whenFalse)};
    if (ts.isAwaitExpression(node)) return {...base,kind:'await',value:ir(node.expression)};
    if (ts.isBinaryExpression(node) && [ts.SyntaxKind.AmpersandAmpersandToken,ts.SyntaxKind.BarBarToken,ts.SyntaxKind.QuestionQuestionToken].includes(node.operatorToken.kind))
      return {...base,kind:node.operatorToken.kind===ts.SyntaxKind.AmpersandAmpersandToken?'and':node.operatorToken.kind===ts.SyntaxKind.BarBarToken?'or':'elvis',left:ir(node.left),right:ir(node.right)};
    if (ts.isSwitchStatement(node)) return {...base,kind:'switch',condition:ir(node.expression),cases:node.caseBlock.clauses.map(c=>({label:ts.isDefaultClause(c)?'default':safeText(c.expression),body:{kind:'block',statements:c.statements.map(ir)}})),fallthrough:true};
    if (ts.isExpressionStatement(node)) return ir(node.expression);
    return {...base,kind:'statement'};
  }
  for (const node of functionNodes) bodies.push({method:id(node),body:ir(node.body),language:'typescript',context_id:context.id});
  for (const source of program.getSourceFiles()) fileInfo(source);
  for (const before of transportInputs.values()) if(hash(fs.readFileSync(before.path))!==before.sha256) throw Error('MIXED_CONFIG_SNAPSHOT');
  for (const [file,before] of inputs) if(hash(fs.readFileSync(file))!==before.sha256) throw Error('MIXED_SNAPSHOT:'+before.path);
  if (request.ui_framework && request.ui_framework!=='react') diagnostics.push({code:'UNSUPPORTED_UI_FRAMEWORK',framework:request.ui_framework});
  return {...handshake(),status:diagnostics.length?'PARTIAL':'COMPLETE',context_id:context.id,
    symbols:[...symbols.values()].sort((a,b)=>a.id<b.id?-1:a.id>b.id?1:0),call_sites:sites,bodies,facts,diagnostics,
    project:{input_files:[...transportInputs.values()].sort((a,b)=>a.path.localeCompare(b.path)),compiler_options:parsed.options,project_references:(parsed.projectReferences||[]).map(r=>r.path),
      root_files:parsed.fileNames.map(f=>path.relative(root,f)),program_files:projectFiles.map(s=>({...fileInfo(s),root_input:rootFileSet.has(s.fileName)})),
      dependencies:[...inputs.values()].filter(i=>i.origin==='dependency')},
    coverage:{files_found:projectFiles.length,files_analyzed:projectFiles.length,methods_analyzed:bodies.length,
      calls_found:sites.length,calls_resolved:sites.filter(s=>s.evidence_kind==='SYMBOL_RESOLVED').length,
      calls_unresolved:sites.filter(s=>s.evidence_kind==='UNRESOLVED').length}};
}

try {
  const buffer=fs.readFileSync(0);
  if(buffer.length>16*1024*1024) throw Error('request output limit exceeded');
  const request=JSON.parse(buffer.toString('utf8'));
  if(request.protocol_version!==PROTOCOL) throw Error('unsupported protocol version');
  const result=request.operation==='handshake'?handshake():(request.operation==='analyze'||request.operation==='project')?analyze(request):(()=>{throw Error('unsupported operation')})();
  const output=JSON.stringify(result);
  if(Buffer.byteLength(output)>64*1024*1024) throw Error('response output limit exceeded');
  process.stdout.write(output+'\n');
} catch(error) {
  process.stderr.write(String(error.stack||error)+'\n');
  process.stdout.write(JSON.stringify({protocol_version:PROTOCOL,worker:VERSION,status:'FAILED',diagnostics:[{code:'WORKER_FAILED',reason:String(error.message||error)}]})+'\n');
  process.exitCode=2;
}
