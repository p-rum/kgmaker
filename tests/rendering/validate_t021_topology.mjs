import fs from 'node:fs';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import {JSDOM} from 'jsdom';
const dom=new JSDOM('<!doctype html><html><body></body></html>');
globalThis.window=dom.window;globalThis.document=dom.window.document;globalThis.Element=dom.window.Element;
dom.window.SVGElement.prototype.getBBox=()=>({x:0,y:0,width:40,height:20});
dom.window.SVGElement.prototype.getComputedTextLength=()=>40;
const {default:mermaid}=await import('mermaid');
mermaid.initialize({startOnLoad:false,securityLevel:'strict',flowchart:{htmlLabels:false}});
const text=fs.readFileSync(process.argv[2],'utf8');
await mermaid.parse(text);
const diagram=await mermaid.mermaidAPI.getDiagramFromText(text);
const vertices=diagram.db.getVertices(),edges=diagram.db.getEdges();
const records=prefix=>text.split('\n').filter(line=>line.startsWith('  %% '+prefix+' '))
  .map(line=>JSON.parse(line.slice(('  %% '+prefix+' ').length)));
const nodes=records('topology-node'),modelEdges=records('topology-edge');
const meta=records('topology-meta')[0],scope=meta.document.scope;
const hash=value=>crypto.createHash('sha256').update(value).digest('hex');
const nodeIdentity=node=>{
  if(typeof node.attributes.logical_id!=='string')return node.id;
  const realm=Object.fromEntries(Object.keys(node.attributes).filter(key=>
    ['realm','broker_realm','workspace_id','repository_id'].includes(key)&&node.attributes[key]!==null).sort()
    .map(key=>[key,node.attributes[key]]));
  return JSON.stringify({context_ids:[...(node.attributes.context_ids??[])].sort(),logical_id:node.attributes.logical_id,
    owner_id:node.owner_id,realm,scope:node.attributes.scope??scope});
};
const nodeId=node=>'n'+hash(nodeIdentity(node));
assert.deepEqual([...vertices.keys()].sort(),nodes.map(nodeId).sort());
assert.equal(edges.length,modelEdges.length);
const endpoints=edges.map(edge=>edge.start+'>'+edge.end).sort();
const byId=Object.fromEntries(nodes.map(node=>[node.id,nodeId(node)]));
assert.deepEqual(endpoints,modelEdges.map(edge=>byId[edge.source]+'>'+byId[edge.target]).sort());
const rendered=await mermaid.render('t021Topology',text);
assert(!/<(?:script|iframe|object|embed)\b/i.test(rendered.svg));
assert(!/\b(?:href|xlink:href)\s*=\s*["'](?:https?:|\/\/)/i.test(rendered.svg));
assert(!/<(?:script|iframe|object|embed|svg)\b/i.test(text));
assert(!/^\s*click\s+/im.test(text));
const svgDom=new JSDOM(rendered.svg,{contentType:'image/svg+xml'});
const svg=svgDom.window.document.documentElement;
assert.equal(svg.querySelectorAll('script,iframe,object,embed,image,a').length,0);
assert.equal(svg.querySelectorAll('[href],[xlink\\:href],[onload],[onclick]').length,0);
for(const element of svg.querySelectorAll('*'))for(const attribute of element.attributes)
  assert(!/^on/i.test(attribute.name));
console.log(JSON.stringify({status:'PASS',vertices:vertices.size,edges:edges.length}));
