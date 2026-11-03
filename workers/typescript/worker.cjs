'use strict';
// One bounded JSON request/response. Never run npm or application code.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const ts = require('typescript');
const PROTOCOL = 1;
const VERSION = 'typescript-worker-5';
const hash = value => crypto.createHash('sha256').update(value).digest('hex');
const canonical = value => JSON.stringify(value);

function handshake() {
  return {protocol_version:PROTOCOL,worker:VERSION,compiler_version:ts.version,
    capabilities:['return-consumer-ir-v1','argument-parameter-bindings-v1','typescript-program','typechecker','overloads','aliases','project-references','bounded-callback-candidates','source-ir','react-events'],
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
  const callbackBindings = new Map(), parameterCalls = [], limitedParameters = new Set();
  const CALLBACK_LIMIT = 64;
  const rootFileSet = new Set();
  const sourceOwners = new Map();
  const ownerDeclarationIndexes = new WeakMap();

  function projectFor(file) { return sourceOwners.get(path.resolve(file)); }
  function symbolPrefix(file) {
    const project = projectFor(file);
    return project && projects.size > 1 ? `${prefix}:project:${project.config}` : prefix;
  }

  function declarationContext(node) {
    const source=node.getSourceFile(), project=projectFor(source.fileName);
    if (!project) return {node,checker};
    const owner=ownerPrograms.get(project.id);
    const ownerSource=owner.program.getSourceFile(path.resolve(source.fileName));
    if (!ownerSource) throw Error(`TS_PROJECT_OWNER_DECLARATION_MISSING:${project.config}: ${source.fileName}`);
    if (ownerSource===source) return {node,checker:owner.checker};
    let index=ownerDeclarationIndexes.get(ownerSource);
    if (!index) {
      index=new Map();
      const visit=n=>{index.set(`${n.kind}:${n.pos}:${n.end}`,n);ts.forEachChild(n,visit);};
      visit(ownerSource);ownerDeclarationIndexes.set(ownerSource,index);
    }
    const declaration=index.get(`${node.kind}:${node.pos}:${node.end}`);
    if (!declaration) throw Error(`TS_PROJECT_OWNER_DECLARATION_MISSING:${project.config}: ${source.fileName}`);
    return {node:declaration,checker:owner.checker};
  }

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
    const owned=declarationContext(node);node=owned.node;
    if (identityCache.has(node)) return identityCache.get(node);
    const loc = location(node);
    let signature = '';
    if (callable(node) || ts.isMethodSignature(node) || ts.isConstructSignatureDeclaration(node) || ts.isCallSignatureDeclaration(node)) {
      const s = owned.checker.getSignatureFromDeclaration(node);
      if (s) signature = owned.checker.signatureToString(s,node,ts.TypeFormatFlags.NoTruncation);
    }
    let value = `${symbolPrefix(node.getSourceFile().fileName)}:${loc.path}:${owner(node)}:${name(node)}:${signature || ts.SyntaxKind[node.kind]}`;
    if (ts.isParameter(node) && node.parent.parameters) {
      value=id(node.parent)+':parameter:'+node.parent.parameters.indexOf(node);
    }
    if (name(node) === '<anonymous>' || (node.parent && ts.isBlock(node.parent)))
      value += `:snapshot:${loc.sha256}:${loc.range.start}`;
    identityCache.set(node,value);
    return value;
  }
  function register(node, kind) {
    const owned=declarationContext(node);node=owned.node;
    const identity = id(node);
    if (!symbols.has(identity)) {
      if (symbols.size >= limits.symbols) throw Error('symbol output limit exceeded');
      const loc = location(node);
      const type = node.name ? owned.checker.getTypeAtLocation(node.name) : owned.checker.getTypeAtLocation(node);
      symbols.set(identity,{id:identity,name:name(node),owner:owner(node),kind:kind || (callable(node)?'function':ts.SyntaxKind[node.kind]),
        type:owned.checker.typeToString(type,node,ts.TypeFormatFlags.NoTruncation),...loc,
        identity_stability:identity.includes(':snapshot:')?'SNAPSHOT':'DECLARATION',
        async:callable(node)&&!!(ts.getCombinedModifierFlags(node)&ts.ModifierFlags.Async),generator:callable(node)&&!!node.asteriskToken,
        project_id:projectFor(node.getSourceFile().fileName)?.id || null,
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
  // These are possible source callables, never a closed-world dispatch proof.
  function callbackProof(expression, activeChecker=checker, seen=new Set()) {
    if (!expression) return {targets:[],complete:false};
    if (seen.has(expression) || seen.size>=16)
      return {targets:[],complete:false,reason:'CALLBACK_TARGET_LIMIT'};
    seen=new Set(seen);seen.add(expression);
    if (ts.isParenthesizedExpression(expression) || ts.isAsExpression(expression) ||
        ts.isTypeAssertionExpression(expression) || ts.isNonNullExpression(expression) || ts.isSatisfiesExpression(expression))
      return callbackProof(expression.expression,activeChecker,seen);
    if (ts.isConditionalExpression(expression)) {
      const left=callbackProof(expression.whenTrue,activeChecker,seen);
      const right=callbackProof(expression.whenFalse,activeChecker,seen);
      const targets=[...new Set([...left.targets,...right.targets])];
      return {targets:targets.slice(0,CALLBACK_LIMIT),complete:left.complete && right.complete && targets.length<=CALLBACK_LIMIT,
        reason:targets.length>CALLBACK_LIMIT?'CALLBACK_TARGET_LIMIT':left.reason || right.reason};
    }
    if (callable(expression)) return {targets:[declarationContext(expression).node],complete:true};
    let symbol=activeChecker.getSymbolAtLocation(expression);
    if (symbol?.flags & ts.SymbolFlags.Alias) symbol=activeChecker.getAliasedSymbol(symbol);
    const declaration=symbol?.valueDeclaration || symbol?.declarations?.[0];
    if (!declaration) return {targets:[],complete:false};
    const owned=declarationContext(declaration), node=owned.node;
    if (ts.isParameter(node)) return {targets:[],complete:false,parameter:node};
    if (ts.isVariableDeclaration(node)) {
      if (!(node.parent.flags & ts.NodeFlags.Const))
        return {targets:[],complete:false,reason:'MUTABLE_CALLBACK'};
      return callbackProof(node.initializer,owned.checker,seen);
    }
    if (ts.isPropertyAssignment(node) || ts.isPropertyDeclaration(node) || ts.isPropertySignature(node) || ts.isBindingElement(node))
      return {targets:[],complete:false,reason:'MUTABLE_CALLBACK'};
    if (callable(node) || ts.isMethodSignature(node) || ts.isCallSignatureDeclaration(node))
      return {targets:[node],complete:true};
    return {targets:[],complete:false};
  }
  function implementationParameter(signature,index) {
    const declaration=signature.parameters[index]?.valueDeclaration || signature.parameters[index]?.declarations?.[0];
    if (!declaration || !ts.isParameter(declaration)) return declaration;
    const owned=declarationContext(declaration), parent=owned.node.parent;
    if (parent.body || !parent.name || owned.node.dotDotDotToken) return owned.node;
    const symbol=owned.checker.getSymbolAtLocation(parent.name);
    const implementations=(symbol?.declarations || []).filter(d=>callable(d) && d.body);
    // The compiler symbol joins overload declarations to exactly one body.
    if (implementations.length!==1 || implementations[0].parameters.some(p=>p.dotDotDotToken)) return owned.node;
    return implementations[0].parameters[index] || owned.node;
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

  let tsconfig = path.resolve(root, request.tsconfig || 'tsconfig.json');
  if (!inside(tsconfig)) throw Error('tsconfig escapes root');
  const transportInputs = new Map();
  const readFile = file => {
    const before = ts.sys.fileExists(file) ? hash(fs.readFileSync(file)) : null;
    const text = ts.sys.readFile(file);
    if (text !== undefined) {
      const resolved=path.resolve(file), sha256=hash(fs.readFileSync(file));
      if (sha256!==before || (transportInputs.has(resolved) && transportInputs.get(resolved).sha256!==sha256))
        throw Error('MIXED_CONFIG_SNAPSHOT:'+resolved);
      transportInputs.set(resolved,{path:resolved,sha256});
    } else if (before!==null) throw Error('MIXED_CONFIG_SNAPSHOT:'+path.resolve(file));
    return text;
  };
  const discovery=require('./input_snapshot.cjs').inputSnapshot(ts,root,readFile);
  const projects = new Map(), orderedProjects = [], activeProjects = new Set();
  const relative = file => path.relative(root,file).split(path.sep).join('/');
  function loadProject(config, parent=null) {
    config = path.resolve(config);
    const located = parent ? relative(parent) : relative(config);
    if (!inside(config)) throw Error(`TS_PROJECT_REFERENCE_OUTSIDE_ROOT:${located}: ${relative(config)}`);
    if (!fs.existsSync(config)) throw Error(`TS_PROJECT_REFERENCE_MISSING:${located}: ${relative(config)}`);
    config = fs.realpathSync(config);
    if (!inside(config)) throw Error(`TS_PROJECT_REFERENCE_OUTSIDE_ROOT:${located}: ${relative(config)}`);
    if (activeProjects.has(config)) throw Error(`TS_PROJECT_REFERENCE_CYCLE:${located}: ${relative(config)}`);
    if (projects.has(config)) return projects.get(config);
    if (projects.size >= 128) throw Error(`TS_PROJECT_REFERENCE_LIMIT:${located}: maximum 128 projects`);
    activeProjects.add(config);
    const parsed = ts.getParsedCommandLineOfConfigFile(config,{}, {...ts.sys,...discovery.host,
      onUnRecoverableConfigFileDiagnostic:d=>{throw Error(`TS_PROJECT_CONFIG:${relative(config)}: `+ts.flattenDiagnosticMessageText(d.messageText,'\n'));}});
    if (!parsed) throw Error(`TS_PROJECT_CONFIG:${relative(config)}: unable to parse tsconfig`);
    if (parsed.errors.length) throw Error(`TS_PROJECT_CONFIG:${relative(config)}: `+ts.formatDiagnostics(parsed.errors,{getCanonicalFileName:p=>p,getCurrentDirectory:()=>root,getNewLine:()=> '\n'}));
    if (parsed.options.disableSourceOfProjectReferenceRedirect && parsed.projectReferences?.length)
      throw Error(`TS_PROJECT_REFERENCE_REDIRECT_DISABLED:${relative(config)}: source-reference analysis requires compiler source redirects`);
    const project = {id:`ts-project:${context.repo_id}:${relative(config)}`,config:relative(config),parsed,references:[]};
    projects.set(config,project);
    for (const reference of parsed.projectReferences || []) {
      const child = loadProject(ts.resolveProjectReferencePath(reference), config);
      project.references.push(child.id);
    }
    for (const file of parsed.fileNames) {
      const owner=sourceOwners.get(path.resolve(file));
      if (owner && owner.id!==project.id) throw Error(`TS_PROJECT_SOURCE_AMBIGUOUS:${relative(config)}: ${relative(file)} also belongs to ${owner.config}`);
      sourceOwners.set(path.resolve(file),project);
      rootFileSet.add(file);
    }
    activeProjects.delete(config);
    orderedProjects.push(project);
    return project;
  }
  const rootProject=loadProject(tsconfig);
  tsconfig=fs.realpathSync(tsconfig);
  const parsed=rootProject.parsed;
  const programs=orderedProjects.map(project=>{
    const host=Object.assign(ts.createCompilerHost(project.parsed.options),discovery.host);
    // Analysis follows the compiler's source redirects, never stale emitted .d.ts
    // and never invokes a solution builder or emit.
    host.useSourceOfProjectReferenceRedirect=()=>true;
    host.getParsedCommandLine=config=>projects.get(fs.existsSync(config)?fs.realpathSync(config):path.resolve(config))?.parsed;
    return {project,program:ts.createProgram({rootNames:project.parsed.fileNames,options:project.parsed.options,
      projectReferences:project.parsed.projectReferences,host})};
  });
  const ownerPrograms=new Map(programs.map(({project,program})=>[project.id,{program,checker:program.getTypeChecker()}]));
  let checker;
  const fingerprints=new Map();
  const projectGraph={version:1,root_project:rootProject.id,projects:orderedProjects.map(project=>{
    const sourceFiles=project.parsed.fileNames.map(file=>({path:relative(file),sha256:hash(fs.readFileSync(file))}))
      .sort((a,b)=>a.path.localeCompare(b.path));
    const references=[...project.references].sort();
    const fingerprint=hash(canonical({config:hash(fs.readFileSync(path.resolve(root,project.config))),
      compiler_options:project.parsed.options,source_files:sourceFiles,
      references:references.map(id=>({id,fingerprint:fingerprints.get(id)}))}));
    fingerprints.set(project.id,fingerprint);
    return {id:project.id,repo_id:context.repo_id,config:project.config,references,fingerprint,
      root_files:sourceFiles.map(file=>file.path),source_files:sourceFiles,compiler_options:project.parsed.options};
  })};
  discovery.lockfiles([...projects.keys()]);
  const compilerDiagnostics=programs.map(({project,program})=>({project,diagnostics:ts.getPreEmitDiagnostics(program)}));
  const uiAdapter=require('./ui_events.cjs');
  const uiAdapters=uiAdapter.adapters(ts,programs,discovery,hash,request.ui_framework==='react');
  const uiProject=request.ui_framework==='react'?{ui_adapters:uiAdapters.snapshots}:{};
  discovery.validate();
  if (request.operation === 'project') {
    return {...handshake(),status:'COMPLETE',context_id:context.id,project:{
      ...uiProject,input_files:[...transportInputs.values()].sort((a,b)=>a.path.localeCompare(b.path)),input_discovery:discovery.snapshot(),
      compiler_options:parsed.options,project_references:(parsed.projectReferences||[]).map(r=>r.path),project_graph:projectGraph}};
  }
  const bindingErrors=[];
  for (const {project,diagnostics:capturedDiagnostics} of compilerDiagnostics) {
    for (const diagnostic of capturedDiagnostics) {
      if(diagnostic.category===ts.DiagnosticCategory.Error && diagnostic.file && diagnostic.start!=null)
        bindingErrors.push({file:diagnostic.file.fileName,start:diagnostic.start,end:diagnostic.start+Math.max(1,diagnostic.length||0)});
      diagnostics.push({code:'TS'+diagnostic.code,reason:ts.flattenDiagnosticMessageText(diagnostic.messageText,'\n'),
        project_id:project.id,path:diagnostic.file?fileInfo(diagnostic.file).path:project.config,start:diagnostic.start??null});
    }
  }
  const projectFiles = [], visitedSources = new Set();
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
      const signatureContract=declaration && (ts.isMethodSignature(declaration) || ts.isCallSignatureDeclaration(declaration) || ts.isConstructSignatureDeclaration(declaration));
      const symbol=checker.getSymbolAtLocation(node.expression);
      const proof=ts.isCallExpression(node)?callbackProof(node.expression):{targets:[],complete:false};
      if (expressionType.flags & (ts.TypeFlags.Any|ts.TypeFlags.Unknown)) reason='DYNAMIC_ANY';
      else if (proof.reason && !signatureContract) reason=proof.reason;
      else if (ts.isCallExpression(node) && expressionType.flags & ts.TypeFlags.Union) reason='AMBIGUOUS_CALLBACK';
      else if (proof.parameter) reason='CALLBACK_PARAMETER_OPEN_WORLD';
      else if (!declaration) reason='MISSING_CALL_SIGNATURE_DECLARATION';
      else if (!callable(declaration) && !ts.isMethodSignature(declaration) && !ts.isConstructSignatureDeclaration(declaration) && !ts.isCallSignatureDeclaration(declaration)) {
        if (signature && proof.complete && proof.targets.length===1) target=register(proof.targets[0]);
        else reason='DYNAMIC_CALLBACK';
      } else if (ts.isCallExpression(node) && symbolDeclaration(symbol) && ts.isVariableDeclaration(symbolDeclaration(symbol)) && !proof.complete && !signatureContract)
        reason='DYNAMIC_CALLBACK';
      else target=register(declaration);
      const lexicalReference=ts.isIdentifier(node.expression)&&symbol&&!(symbol.flags&ts.SymbolFlags.Alias)&&symbol.valueDeclaration&&
        ts.isFunctionDeclaration(symbol.valueDeclaration)&&declaration&&id(symbol.valueDeclaration)===id(declaration);
      const memberSymbol=ts.isPropertyAccessExpression(node.expression)?checker.getSymbolAtLocation(node.expression.name):null;
      const privateReference=ts.isPropertyAccessExpression(node.expression)&&ts.isPrivateIdentifier(node.expression.name)&&
        declaration&&ts.isMethodDeclaration(declaration)&&declaration.name&&ts.isPrivateIdentifier(declaration.name)&&
        memberSymbol&&memberSymbol.valueDeclaration&&id(memberSymbol.valueDeclaration)===id(declaration);
      const site={id:identity,caller,...loc,declared_target:target,argument_mapping_version:1,argument_mapping_status:'UNKNOWN',argument_mapping_reason:'NO_SOURCE_ARGUMENT_BINDING_PROOF',dispatch_candidates:[],dispatch_complete:false,
        invocation_kind:ts.isNewExpression(node)?'CONSTRUCTOR':'CALL',receiver_type:ts.isPropertyAccessExpression(node.expression) || ts.isElementAccessExpression(node.expression) ? checker.typeToString(checker.getTypeAtLocation(node.expression.expression)) : null,
        callable_type:checker.typeToString(expressionType),return_reference_kind:lexicalReference?'LEXICAL_IDENTIFIER':privateReference?'HARD_PRIVATE_MEMBER':'PROPERTY_OR_OTHER',
        signature:signature?checker.signatureToString(signature):null,
        resolution_reason:reason || 'TYPESCRIPT_RESOLVED_SIGNATURE',evidence_kind:target?'SYMBOL_RESOLVED':'UNRESOLVED',
        context_id:context.id};
      if (reason==='AMBIGUOUS_CALLBACK') site.dispatch_candidates=proof.targets.map(n=>register(n)).sort();
      if (proof.parameter && reason!=='DYNAMIC_ANY') parameterCalls.push({site,parameter:register(proof.parameter)});
      if (symbol) site.expression_symbol=checker.getFullyQualifiedName(symbol);
      sites.push(site); siteByNode.set(node,identity);
      if (reason) diagnostics.push({code:reason,path:loc.path,range:loc.range,call_site:identity});
      const bindingError=bindingErrors.some(error=>error.file===node.getSourceFile().fileName && error.start<node.end && error.end>node.getStart());
      if(target && signature && bindingError) {site.argument_mapping_reason='TS_ARGUMENT_MAPPING_UNAVAILABLE';diagnostics.push({code:'TS_ARGUMENT_MAPPING_UNAVAILABLE',reason:'Call overlaps compiler error; recovery signature is not mapping proof',...loc,call_site:identity});}
      if (target && signature && !bindingError) {
        const args=node.arguments||[], parameters=signature.parameters;
        const formal=index=>parameters[index]?.valueDeclaration || parameters[index]?.declarations?.[0];
        const rest=parameters.length>0 && !!formal(parameters.length-1)?.dotDotDotToken;
        const unsupportedSpread=args.some((argument,index)=>ts.isSpreadElement(argument) && (!rest || index<parameters.length-1));
        let completeBinding=!unsupportedSpread;
        if(unsupportedSpread) diagnostics.push({code:'TS_ARGUMENT_MAPPING_UNAVAILABLE',reason:'Spread before fixed formals needs tuple binding proof',...loc,call_site:identity});
        else for(let i=0;i<args.length;i++) {
          const pi=rest?Math.min(i,parameters.length-1):i,d=formal(pi);
          if(!d) { completeBinding=false;diagnostics.push({code:'TS_ARGUMENT_MAPPING_UNAVAILABLE',reason:'No attributed formal for argument',...loc,call_site:identity});continue; }
          const parameterId=register(d,'parameter');
          Object.assign(symbols.get(parameterId),{kind:'parameter',method:target,parameter_index:pi});
          const argumentId=identity+':argument:'+i,argument=ts.isSpreadElement(args[i])?args[i].expression:args[i];
          const argumentLocation=location(argument);
          if(symbols.size>=limits.symbols)throw Error('symbol output limit exceeded');
          symbols.set(argumentId,{id:argumentId,name:'argument '+i,kind:'value',call_site:identity,owner_method:caller,
            scope:context.scope,context_id:context.id,...argumentLocation});
          const origin=symbolDeclaration(checker.getSymbolAtLocation(argument));
          if(origin)facts.push({kind:'derived_from',source:argumentId,target:register(origin),...argumentLocation,evidence_kind:'SYMBOL_RESOLVED',resolution_reason:'TYPESCRIPT_ARGUMENT_SYMBOL_REFERENCE'});
          const transformation=rest && pi===parameters.length-1?(ts.isSpreadElement(args[i])?'VARARG_SPREAD':'VARARG_ELEMENT'):'DIRECT';
          facts.push({kind:'argument_to_parameter',source:argumentId,target:parameterId,call_site:identity,
            argument_index:i,parameter_index:pi,parameter_name:symbols.get(parameterId).name,transformation,binding_kind:'DECLARED_PARAMETER',
            argument_mapping_version:1,context_id:context.id,...argumentLocation,evidence_kind:'SYMBOL_RESOLVED',resolution_reason:'TYPESCRIPT_RESOLVED_SIGNATURE_ARGUMENT_MAPPING'});
        }
        site.argument_mapping_status=completeBinding?'PROVEN':'UNKNOWN';
        site.argument_mapping_reason=completeBinding?'TYPESCRIPT_RESOLVED_SIGNATURE_ARGUMENT_MAPPING':'TS_ARGUMENT_MAPPING_UNAVAILABLE';
        for(let pi=args.length;pi<parameters.length;pi++) {
          const d=formal(pi);
          if(d?.initializer)(site.argument_omissions ||= []).push({parameter_index:pi,parameter_name:parameters[pi].name,reason:'DEFAULT_VALUE_NOT_EVALUATED'});
        }
      }
      if (target && signature) {
        for (let i=0; i<(node.arguments||[]).length && i<signature.parameters.length; i++) {
          const parameterType=checker.getTypeOfSymbolAtLocation(signature.parameters[i],node);
          const callback=!(parameterType.flags & (ts.TypeFlags.Any|ts.TypeFlags.Unknown)) && checker.getSignaturesOfType(parameterType,ts.SignatureKind.Call).length>0;
          if (!callback) continue; // ordinary argument occurrences use the versioned declared-formal proof above
          const d=implementationParameter(signature,i);
          if (!d) continue;
          const argument=node.arguments[i], argumentType=checker.getTypeAtLocation(argument);
          const bound=callback && !(argumentType.flags & (ts.TypeFlags.Any|ts.TypeFlags.Unknown))?callbackProof(argument):{targets:[],complete:false};
          const fallback=symbolDeclaration(checker.getSymbolAtLocation(argument));
          const sources=bound.targets.length?bound.targets:fallback?[fallback]:[];
          const parameter=register(d);
          if (callback && bound.reason==='CALLBACK_TARGET_LIMIT' && projectFor(d.getSourceFile().fileName) && !d.getSourceFile().isDeclarationFile)
            limitedParameters.add(parameter);
          for (const source of sources) {
            const identity=register(source);
            facts.push({kind:'argument_to_parameter',source:identity,target:parameter,...loc,
              evidence_kind:bound.targets.length && (!bound.complete || bound.targets.length!==1)?'DISPATCH_CANDIDATE':'SYMBOL_RESOLVED'});
            if (callback && bound.targets.includes(source) && projectFor(d.getSourceFile().fileName) && !d.getSourceFile().isDeclarationFile) {
              if (!callbackBindings.has(parameter)) callbackBindings.set(parameter,new Set());
              const candidates=callbackBindings.get(parameter);
              if (candidates.size>=CALLBACK_LIMIT && !candidates.has(identity)) limitedParameters.add(parameter);
              else candidates.add(identity);
            }
          }
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
      const result=uiAdapter.event(ts,checker,node,uiAdapters.byFile.get(path.resolve(node.getSourceFile().fileName)),uiAdapters.byFile,symbolDeclaration,callbackProof,location);
      if(result.handler) facts.push({kind:'handles_event',source:caller,target:register(result.handler),event:node.name.text,
        ...location(node),evidence_kind:'FRAMEWORK_DERIVED',...result.proof});
      else diagnostics.push({code:result.reason,...location(node)});
    }
    if (ts.isImportSpecifier(node) || ts.isExportSpecifier(node)) {
      const alias=checker.getSymbolAtLocation(node.name);
      const original=symbolDeclaration(alias);
      if (alias && original && original!==node) facts.push({kind:'alias_of',source:register(node,'alias'),target:register(original),...location(node),evidence_kind:'SYMBOL_RESOLVED'});
    }
    ts.forEachChild(node,child=>visit(child,caller));
  }
  for (const {program} of programs) {
    checker=program.getTypeChecker();
    for (const source of program.getSourceFiles()) {
      if (!inside(source.fileName) || source.isDeclarationFile || source.fileName.includes(path.sep+'node_modules'+path.sep) || visitedSources.has(source.fileName)) continue;
      visitedSources.add(source.fileName);projectFiles.push(source);
      const loc=fileInfo(source);
      const moduleId=`${symbolPrefix(source.fileName)}:${loc.path}:<module>`;
      symbols.set(moduleId,{id:moduleId,name:'<module>',kind:'module',owner:'',...loc,
        project_id:projectFor(source.fileName)?.id || null,
        range:{start:0,end:source.end,start_line:1,start_column:1},scope:context.scope,context_id:context.id});
      visit(source,moduleId);
    }
  }

  for (const {site,parameter} of parameterCalls) {
    site.dispatch_candidates=[...new Set([...site.dispatch_candidates,...(callbackBindings.get(parameter) || [])])].sort();
    if (limitedParameters.has(parameter)) {
      site.resolution_reason='CALLBACK_TARGET_LIMIT';
      diagnostics.push({code:'CALLBACK_TARGET_LIMIT',call_site:site.id,path:site.path,range:site.range,candidate_limit:CALLBACK_LIMIT});
    }
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
  function valueInfo(node,declaredReturn=false) {
    try {
      const owned=declarationContext(node), c=owned.checker,n=owned.node;
      if(bindingErrors.some(e=>e.file===n.getSourceFile().fileName && e.start<n.getEnd() && e.end>n.getStart()))
        return {version:1,status:'UNKNOWN',type_ref:'unknown',nullability:'UNKNOWN'};
      if(!declaredReturn && n.kind===ts.SyntaxKind.NullKeyword)return {version:1,status:'VALUE',type_ref:'null',nullability:'NULL_LITERAL'};
      const options=projectFor(n.getSourceFile().fileName)?.parsed?.options || parsed.options;
      const strictNull=options.strictNullChecks ?? options.strict ?? false;
      const signature=declaredReturn?c.getSignatureFromDeclaration(n):null;
      const type=declaredReturn?(signature?c.getReturnTypeOfSignature(signature):null):c.getTypeAtLocation(n);
      if(!type)return {version:1,status:'UNKNOWN',type_ref:'unknown',nullability:'UNKNOWN'};
      const parts=type.isUnion()?type.types:[type];
      if(parts.some(t=>t.flags & (ts.TypeFlags.Any|ts.TypeFlags.Unknown)))
        return {version:1,status:'UNKNOWN',type_ref:'unknown',nullability:'UNKNOWN'};
      if(parts.every(t=>t.flags & (ts.TypeFlags.Void|ts.TypeFlags.Never)))
        return {version:1,status:'VOID',type_ref:'void',nullability:'UNKNOWN'};
      const callable=parts.some(t=>t.getCallSignatures().length || t.getConstructSignatures().length);
      const primitive=t=>t.flags&ts.TypeFlags.StringLike?'string':t.flags&ts.TypeFlags.NumberLike?'number':t.flags&ts.TypeFlags.BooleanLike?'boolean':t.flags&ts.TypeFlags.BigIntLike?'bigint':t.flags&ts.TypeFlags.Null?'null':t.flags&ts.TypeFlags.Undefined?'undefined':t.flags&ts.TypeFlags.TypeParameter?'type_parameter':c.isTupleType(t)?'tuple':'object';
      const kinds=[...new Set(parts.map(primitive))].sort();
      const nullable=parts.some(t=>t.flags&(ts.TypeFlags.Null|ts.TypeFlags.Undefined));
      return {version:1,status:callable?'CALLABLE':'VALUE',type_ref:kinds.join('|'),
        nullability:parts.every(t=>t.flags&ts.TypeFlags.Null)?'NULL_LITERAL':!strictNull?'UNKNOWN':nullable?'MAY_BE_NULL':'DECLARED_NON_NULL'};
    }catch(error){return {version:1,status:'UNKNOWN',type_ref:'unknown',nullability:'UNKNOWN'};}
  }
  function valueBinding(node) {
    if(!node)return null;
    const owned=declarationContext(node),c=owned.checker,n=owned.node;
    let declaration=n;
    if(ts.isIdentifier(n)) {
      let symbol=c.getSymbolAtLocation(n);if(symbol?.flags&ts.SymbolFlags.Alias)symbol=c.getAliasedSymbol(symbol);
      declaration=symbol?.valueDeclaration || symbol?.declarations?.[0];
    }
    if(!declaration || !(ts.isVariableDeclaration(declaration)||ts.isBindingElement(declaration)||ts.isParameter(declaration)) || !ts.isIdentifier(declaration.name))return null;
    const loc=location(declaration);
    // External/global declaration locators are not captured source binding proof.
    if (!context.source_files || context.source_files[loc.path]!==loc.sha256)return null;
    let parent=declaration.parent;while(parent && !callable(parent))parent=parent.parent;
    const identity=ts.isParameter(declaration)?id(declaration):`${symbolPrefix(declaration.getSourceFile().fileName)}:binding:${loc.path}:${loc.sha256}:${loc.range.start}:${loc.range.end}`;
    return {version:1,id:identity,name:declaration.name.text,kind:ts.isParameter(declaration)?'PARAMETER':'LOCAL_VARIABLE',method:parent?id(parent):null,symbol:null,type:valueInfo(declaration),...loc};
  }
  function valueTargets(node) {
    const pattern=node.name;if(!pattern || !(ts.isArrayBindingPattern(pattern)||ts.isObjectBindingPattern(pattern)))return [];
    const c=declarationContext(node).checker;const type=c.getTypeAtLocation(node.initializer);
    return pattern.elements.flatMap((entry,index)=>{
      if(ts.isOmittedExpression(entry))return [];
      const binding=valueBinding(entry);if(!binding)return [];
      let status='PROVEN',kind=ts.isArrayBindingPattern(pattern)?'TUPLE_ELEMENT':'OBJECT_PROPERTY',key=null;
      if(entry.dotDotDotToken || entry.initializer || !ts.isIdentifier(entry.name))status='UNKNOWN';
      if(kind==='TUPLE_ELEMENT') {if(!c.isTupleType(type))status='UNKNOWN';}
      else {
        const property=entry.propertyName || entry.name;
        key=ts.isIdentifier(property)?property.text:ts.isStringLiteral(property)?property.text:null;
        if(key==null || !ts.isIdentifierText(key,ts.ScriptTarget.Latest))status='UNKNOWN';
        const symbol=key==null?null:c.getPropertyOfType(type,key);
        if(!symbol || symbol.declarations?.some(d=>ts.isGetAccessorDeclaration(d)||ts.isSetAccessorDeclaration(d)))status='UNKNOWN';
      }
      return [{binding,projection:{kind,index,key,status}}];
    });
  }
  function literalShape(node) {
    if(ts.isArrayLiteralExpression(node) && !node.elements.some(ts.isSpreadElement))return {kind:'TUPLE_ELEMENT',size:node.elements.length};
    if(ts.isObjectLiteralExpression(node) && node.properties.every(p=>ts.isPropertyAssignment(p) && ts.isIdentifier(p.name)))
      return {kind:'OBJECT_PROPERTY',keys:node.properties.map(p=>p.name.text)};
    return null;
  }
  function ir(node) {
    if (!node) return {kind:'empty'};
    const base={...location(node),label:safeText(node),calls:calls(node),value_info:valueInfo(node)};
    if(ts.isIdentifier(node))base.value_binding=valueBinding(node);
    const shape=literalShape(node);if(shape)base.value_shape=shape;
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
    if(ts.isVariableDeclaration(node))return ts.isIdentifier(node.name)?{...base,kind:'assign',value_binding:valueBinding(node),value:ir(node.initializer)}:{...base,kind:'destructure',value:ir(node.initializer),value_targets:valueTargets(node)};
    if(ts.isBinaryExpression(node) && node.operatorToken.kind>=ts.SyntaxKind.FirstAssignment && node.operatorToken.kind<=ts.SyntaxKind.LastAssignment)
      return {...base,kind:'assign',value_binding:valueBinding(node.left),value:ir(node.right)};
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
  // Lexical declarations may be assigned too. Refuse their original body when
  // the compiler binds an assignment target to that declaration; members are
  // mutable regardless of static/TypeScript-private modifiers.
  const reassignedFunctions=new Set(), directEvalCalls=[], dynamicScopeFiles=new Map();
  function assignedFunctions(node) {
    if (ts.isIdentifier(node)||ts.isShorthandPropertyAssignment(node)) {
      const owned=declarationContext(node);
      const symbol=ts.isShorthandPropertyAssignment(owned.node)
        ? owned.checker.getShorthandAssignmentValueSymbol(owned.node)
        : owned.checker.getSymbolAtLocation(owned.node);
      for (const declaration of symbol&&symbol.declarations||[])
        if (ts.isFunctionDeclaration(declaration)) reassignedFunctions.add(id(declaration));
    } else ts.forEachChild(node,assignedFunctions);
  }
  function inspectAssignments(node) {
    if (ts.isCallExpression(node)&&ts.isIdentifier(node.expression)&&node.expression.text==='eval') directEvalCalls.push(node.expression);
    if (ts.isForOfStatement(node)||ts.isForInStatement(node)) assignedFunctions(node.initializer);
    if (ts.isBinaryExpression(node) && node.operatorToken.kind>=ts.SyntaxKind.FirstAssignment && node.operatorToken.kind<=ts.SyntaxKind.LastAssignment)
      assignedFunctions(node.left);
    if ((ts.isPrefixUnaryExpression(node)||ts.isPostfixUnaryExpression(node)) && [ts.SyntaxKind.PlusPlusToken,ts.SyntaxKind.MinusMinusToken].includes(node.operator))
      assignedFunctions(node.operand);
    ts.forEachChild(node,inspectAssignments);
  }
  for (const source of projectFiles) inspectAssignments(source);
  const builtinEvalFile=fs.realpathSync(path.join(path.dirname(require.resolve('typescript')),'lib.es5.d.ts'));
  for (const expression of directEvalCalls) {
    const owned=declarationContext(expression);
    let symbol=owned.checker.getSymbolAtLocation(owned.node);
    if (symbol&&(symbol.flags&ts.SymbolFlags.Alias)) symbol=owned.checker.getAliasedSymbol(symbol);
    const declarations=symbol&&symbol.declarations||[];
    const builtin=declarations.some(d=>d.getSourceFile().isDeclarationFile&&fs.realpathSync(d.getSourceFile().fileName)===builtinEvalFile&&ts.isFunctionDeclaration(d)&&d.name&&d.name.text==='eval');
    const knownLocal=declarations.length>0&&declarations.every(d=>
      ts.isFunctionDeclaration(d)&&d.body&&!d.getSourceFile().isDeclarationFile&&
        ((ts.isSourceFile(d.parent)&&ts.isExternalModule(d.parent))||ts.isBlock(d.parent))&&!reassignedFunctions.has(id(d))||
      ts.isVariableDeclaration(d)&&d.initializer&&ts.isVariableDeclarationList(d.parent)&&(d.parent.flags&ts.NodeFlags.Const)&&
        (ts.isArrowFunction(d.initializer)||ts.isFunctionExpression(d.initializer)));
    if (!knownLocal||builtin) {
      const file=path.resolve(expression.getSourceFile().fileName);
      if (builtin||!dynamicScopeFiles.has(file)) dynamicScopeFiles.set(file,builtin?'TS_DIRECT_BUILTIN_EVAL':'TS_DIRECT_EVAL_IDENTITY_UNKNOWN');
    }
  }
  for (const node of functionNodes) {
    const flags=ts.getCombinedModifierFlags(node);
    const kind=ts.isConstructorDeclaration(node)?'CONSTRUCTOR':flags&ts.ModifierFlags.Async?'ASYNC':node.asteriskToken?'GENERATOR':ts.isArrowFunction(node)||ts.isFunctionExpression(node)?'CALLABLE':ts.isGetAccessorDeclaration(node)||ts.isSetAccessorDeclaration(node)?'ACCESSOR':'DECLARED';
    const source=location(node),captured=context.source_files&&context.source_files[source.path]===source.sha256;
    bodies.push({method:id(node),body:ts.isBlock(node.body)?ir(node.body):{kind:'return',value:ir(node.body)},language:'typescript',context_id:context.id,return_flow_version:captured?1:undefined,return_ir_reason:captured?null:'RETURN_SOURCE_NOT_CAPTURED',return_body_kind:kind,return_type:valueInfo(node,true),return_binding_boundary:dynamicScopeFiles.get(path.resolve(node.getSourceFile().fileName))||null,return_dispatch:ts.isFunctionDeclaration(node)&&!dynamicScopeFiles.has(path.resolve(node.getSourceFile().fileName))&&((ts.isSourceFile(node.parent)&&ts.isExternalModule(node.parent))||ts.isBlock(node.parent))&&!reassignedFunctions.has(id(node))?'LEXICAL':node.name&&ts.isPrivateIdentifier(node.name)?'HARD_PRIVATE':'OPEN'});
  }
  for (const {program} of programs) for (const source of program.getSourceFiles()) fileInfo(source);
  discovery.validate();
  for (const before of transportInputs.values()) if(hash(fs.readFileSync(before.path))!==before.sha256) throw Error('MIXED_CONFIG_SNAPSHOT');
  for (const [file,before] of inputs) if(hash(fs.readFileSync(file))!==before.sha256) throw Error('MIXED_SNAPSHOT:'+before.path);
  if (request.ui_framework && request.ui_framework!=='react') diagnostics.push({code:'UNSUPPORTED_UI_FRAMEWORK',framework:request.ui_framework});
  return {...handshake(),status:diagnostics.length?'PARTIAL':'COMPLETE',context_id:context.id,
    symbols:[...symbols.values()].sort((a,b)=>a.id<b.id?-1:a.id>b.id?1:0),call_sites:sites,bodies,facts,diagnostics,
    project:{...uiProject,input_files:[...transportInputs.values()].sort((a,b)=>a.path.localeCompare(b.path)),input_discovery:discovery.snapshot(),compiler_options:parsed.options,project_references:(parsed.projectReferences||[]).map(r=>r.path),project_graph:projectGraph,
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
