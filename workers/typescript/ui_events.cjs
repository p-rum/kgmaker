'use strict';
// Static, opt-in React18 adapter. No require/import of application or React JS.
const path=require('node:path');
const RULE='react-jsx-events-2';
const DECLARATION_SHA='b89c2ddec6bd955e8721d41e24ca667de06882338d88b183c2cdc1f41f4c5a34';
const EVENT_INTERFACES=new Set(['DOMAttributes','InputHTMLAttributes','SelectHTMLAttributes','TextareaHTMLAttributes']);

function adapters(ts,programs,discovery,hash,enabled) {
  const byFile=new Map(), snapshots=[];
  if(!enabled) return {byFile,snapshots};
  function packageAt(directory,name) {
    for(let count=0;count<64;count++) {
      const file=path.join(directory,'node_modules',name,'package.json');
      if(discovery.host.fileExists(file)) return file;
      const parent=path.dirname(directory);if(parent===directory)break;directory=parent;
    }
    return null;
  }
  function read(file) {
    if(!file)return null;
    const text=discovery.host.readFile(file);if(text===undefined)return null;
    try{return {data:JSON.parse(text),sha256:hash(Buffer.from(text))};}catch{return null;}
  }
  for(const {project,program} of programs) for(const file of project.parsed.fileNames) {
    if(!/\.tsx$/i.test(file))continue;
    const resolved=ts.resolveModuleName('react',file,project.parsed.options,discovery.host).resolvedModule;
    const declaration=resolved?.resolvedFileName;
    const typesFile=declaration?path.join(path.dirname(declaration),'package.json'):null;
    const types=read(typesFile), runtimeFile=packageAt(path.dirname(file),'react'),runtime=read(runtimeFile);
    const text=declaration?discovery.host.readFile(declaration):undefined;
    const declarationSha=text!==undefined?hash(Buffer.from(text)):null;
    const official=declaration && declaration.replace(/\\/g,'/').endsWith('/node_modules/@types/react/index.d.ts') &&
      resolved.isExternalLibraryImport===true && types?.data.name==='@types/react' && runtime?.data.name==='react';
    const source=program.getSourceFile(file), options=project.parsed.options;
    const pragmas=['jsx','jsxfrag','jsximportsource','jsxruntime'].some(key=>source?.pragmas?.has(key));
    let renderer=null, runtimeDeclaration=null, runtimeSha=null;
    // Only documented defaults + compiler-proven classic factory aliases.
    // Explicit legacy namespace/fragment/import-source controls are not defaults,
    // including empty strings; TypeScript may otherwise silently fall back.
    const defaultControls=!pragmas && options.reactNamespace===undefined &&
      options.jsxFragmentFactory===undefined && options.jsxImportSource===undefined;
    if(defaultControls && options.jsx===ts.JsxEmit.React) {
      const factory=options.jsxFactory===undefined?'React.createElement':options.jsxFactory;
      if(/^[A-Za-z_$][\w$]*(?:\.createElement)?$/.test(factory))renderer={kind:'classic',factory};
    } else if(defaultControls && options.jsxFactory===undefined &&
        [ts.JsxEmit.ReactJSX,ts.JsxEmit.ReactJSXDev].includes(options.jsx)) {
      const suffix=options.jsx===ts.JsxEmit.ReactJSXDev?'jsx-dev-runtime':'jsx-runtime';
      const runtimeModule=ts.resolveModuleName('react/'+suffix,file,options,discovery.host).resolvedModule;
      const expected=declaration?path.join(path.dirname(declaration),suffix+'.d.ts'):null;
      const runtimeText=runtimeModule?discovery.host.readFile(runtimeModule.resolvedFileName):undefined;
      runtimeSha=runtimeText!==undefined?hash(Buffer.from(runtimeText)):null;
      const expectedSha=suffix==='jsx-runtime'?'42c169fb8c2d42f4f668c624a9a11e719d5d07dacbebb63cbcf7ef365b0a75b3':'56ccb49443bfb72e5952f7012f0de1a8679f9f75fc93a5c1ac0bafb28725fc5f';
      if(runtimeModule?.isExternalLibraryImport===true && path.resolve(runtimeModule.resolvedFileName)===path.resolve(expected||'') && runtimeSha===expectedSha) {
        renderer={kind:'automatic',module:'react/'+suffix};runtimeDeclaration=expected;
      }
    }
    const supported=!!(renderer && official && runtime.data.version==='18.3.1' && types.data.version==='18.3.18' && declarationSha===DECLARATION_SHA);
    const snapshot={rule:RULE,status:supported?'SUPPORTED':'UNKNOWN',project_id:project.id,
      source_file:path.relative(project.parsed.options.configFilePath?path.dirname(project.parsed.options.configFilePath):path.dirname(file),file).split(path.sep).join('/'),
      react_version:typeof runtime?.data.version==='string'?runtime.data.version:null,
      types_version:typeof types?.data.version==='string'?types.data.version:null,
      react_package_sha256:runtime?.sha256||null,types_package_sha256:types?.sha256||null,
      declaration_sha256:declarationSha,renderer,runtime_declaration_sha256:runtimeSha};
    snapshots.push(snapshot);byFile.set(path.resolve(file),{snapshot,declaration:supported?path.resolve(declaration):null,renderer});
  }
  snapshots.sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b)));
  return {byFile,snapshots};
}

function event(ts,checker,node,adapter,allAdapters,symbolDeclaration,callbackProof,location) {
  const unknown=reason=>({reason});
  if(!adapter?.declaration)return unknown('UNSUPPORTED_UI_ADAPTER');
  function factoryProof(at,selected) {
    if(!selected?.declaration)return false;
    if(selected.renderer?.kind==='automatic')return true;
    const parts=selected.renderer?.factory?.split('.');
    if(!parts)return false;
    let symbol=checker.resolveName(parts[0],at,ts.SymbolFlags.Value,false);
    if(symbol?.flags & ts.SymbolFlags.Alias)symbol=checker.getAliasedSymbol(symbol);
    if(parts.length===2) {
      // A checkout object annotated/cast as typeof React has the same member
      // declaration type but is not the selected library factory value.
      const namespaces=symbol?.declarations||[];
      if(!namespaces.length || namespaces.some(d=>!ts.isModuleDeclaration(d) || d.name.text!=='React' ||
          path.resolve(d.getSourceFile().fileName)!==selected.declaration))return false;
      symbol=checker.getPropertyOfType(checker.getTypeOfSymbolAtLocation(symbol,at),parts[1]);
    }
    if(symbol?.flags & ts.SymbolFlags.Alias)symbol=checker.getAliasedSymbol(symbol);
    const declarations=symbol?.declarations||[];
    return declarations.length>0 && declarations.every(d=>ts.isFunctionDeclaration(d) && d.name?.text==='createElement' &&
      path.resolve(d.getSourceFile().fileName)===selected.declaration);
  }
  if(!factoryProof(node,adapter))return unknown('UI_RENDERER_UNPROVEN');
  const opening=node.parent.parent, eventName=node.name.text;
  // TypeScript treats uppercase/member JSX as a component even if a local
  // augmentation adds its spelling to IntrinsicElements. Custom intrinsics
  // also need the actual pinned library tag declaration, not just its prop type.
  const intrinsic=tag=>ts.isIdentifier(tag) && ts.isIntrinsicJsxName(tag.text)
    ?checker.getJsxIntrinsicTagNamesAt(tag).find(s=>s.name===tag.text):null;
  function officialAttribute(tag) {
    const symbol=intrinsic(tag);if(!symbol)return null;
    const tags=symbol.declarations||[];
    if(!tags.length || tags.some(d=>path.resolve(d.getSourceFile().fileName)!==adapter.declaration ||
        !ts.isInterfaceDeclaration(d.parent) || d.parent.name.text!=='IntrinsicElements'))return null;
    const property=checker.getPropertyOfType(checker.getTypeOfSymbolAtLocation(symbol,node),eventName);
    const declaration=symbolDeclaration(property);
    if(!declaration || path.resolve(declaration.getSourceFile().fileName)!==adapter.declaration ||
       !ts.isInterfaceDeclaration(declaration.parent) || !EVENT_INTERFACES.has(declaration.parent.name.text))return null;
    return declaration;
  }
  let attribute=officialAttribute(opening.tagName),wrapper=null;
  if(!attribute) {
    wrapper=symbolDeclaration(checker.getSymbolAtLocation(opening.tagName));
    if(!wrapper || location(wrapper).origin!=='handwritten' || !ts.isFunctionDeclaration(wrapper) || !wrapper.body || wrapper.body.statements.length!==1 ||
       wrapper.parameters.length!==1 || !ts.isIdentifier(wrapper.parameters[0].name) || wrapper.parameters[0].initializer)
      return unknown('UI_WRAPPER_UNPROVEN');
    const statement=wrapper.body.statements[0];
    if(!ts.isReturnStatement(statement))return unknown('UI_WRAPPER_UNPROVEN');
    let returned=statement.expression;while(returned&&ts.isParenthesizedExpression(returned))returned=returned.expression;
    const inner=returned&&(ts.isJsxElement(returned)?returned.openingElement:ts.isJsxSelfClosingElement(returned)?returned:null);
    if(!inner || inner.attributes.properties.some(a=>ts.isJsxSpreadAttribute(a)))return unknown('UI_WRAPPER_UNPROVEN');
    const innerAdapter=allAdapters.get(path.resolve(inner.getSourceFile().fileName));
    if(innerAdapter?.declaration!==adapter.declaration || !factoryProof(inner,innerAdapter))return unknown('UI_RENDERER_UNPROVEN');
    attribute=officialAttribute(inner.tagName);
    const forwards=inner.attributes.properties.filter(a=>ts.isJsxAttribute(a)&&a.name.text===eventName);
    const value=forwards.length===1 && forwards[0].initializer && ts.isJsxExpression(forwards[0].initializer)?forwards[0].initializer.expression:null;
    if(!attribute || !value || !ts.isPropertyAccessExpression(value) || value.name.text!==eventName || !ts.isIdentifier(value.expression) ||
       checker.getSymbolAtLocation(value.expression)!==checker.getSymbolAtLocation(wrapper.parameters[0].name))return unknown('UI_WRAPPER_UNPROVEN');
    const prop=checker.getPropertyOfType(checker.getTypeAtLocation(wrapper.parameters[0]),eventName);
    if(symbolDeclaration(prop)!==attribute)return unknown('UI_WRAPPER_PROP_UNPROVEN');
  }
  if(opening.attributes.properties.filter(a=>ts.isJsxAttribute(a)&&a.name.text===eventName).length!==1 || opening.attributes.properties.some(a=>ts.isJsxSpreadAttribute(a)))return unknown('UI_ATTRIBUTE_SPREAD_UNSUPPORTED');
  const expression=node.initializer&&ts.isJsxExpression(node.initializer)?node.initializer.expression:null;
  const binding=expression?callbackProof(expression):null;
  const handler=binding?.complete && binding.targets.length===1?binding.targets[0]:null;
  if(!handler || !ts.isFunctionLike(handler) || !handler.body)return unknown(binding?.reason || 'UNRESOLVED_UI_HANDLER');
  return {handler,proof:{ui_adapter:{...adapter.snapshot,attribute_declaration:location(attribute),
    wrapper:wrapper?location(wrapper):null},execution:'NOT_OBSERVED'}};
}
module.exports={RULE,adapters,event};
