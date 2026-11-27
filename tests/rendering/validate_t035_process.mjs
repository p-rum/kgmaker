import assert from 'node:assert/strict';
import fs from 'node:fs';
import { JSDOM } from 'jsdom';

const version = name => JSON.parse(fs.readFileSync(new URL(`./node_modules/${name}/package.json`, import.meta.url))).version;
assert.equal(version('mermaid'), '11.4.1');
assert.equal(version('jsdom'), '26.0.0');

const dom = new JSDOM('<!doctype html><html><body></body></html>');
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.Element = dom.window.Element;
dom.window.SVGElement.prototype.getBBox = () => ({ x: 0, y: 0, width: 40, height: 20 });
dom.window.SVGElement.prototype.getComputedTextLength = () => 40;
const { default: mermaid } = await import('mermaid');
mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', htmlLabels: false, flowchart: { htmlLabels: false } });

const source = fs.readFileSync(process.argv[2], 'utf8');
const records = name => {
  const prefix = `  %% process-${name} `;
  return source.split('\n').filter(line => line.startsWith(prefix)).map(line => JSON.parse(line.slice(prefix.length)));
};
const nodes = records('node');
const edges = records('edge');
const lanes = records('lane');
const byId = new Map(nodes.map(record => [record.node.id, record.diagram_id]));
assert.equal(new Set(edges.map(record => record.diagram_id)).size, edges.length);

await mermaid.parse(source);
const { db } = await mermaid.mermaidAPI.getDiagramFromText(source);
assert.deepEqual([...db.getVertices().keys()].sort(), [...byId.values()].sort());
assert.deepEqual(db.getEdges().map(edge => [edge.start, edge.end]), edges.map(({ edge, index }, i) => {
  assert.equal(index, i);
  return [byId.get(edge.source), byId.get(edge.target)];
}));
const groups = new Map(db.getSubGraphs().map(group => [group.id, [...group.nodes].sort()]));
assert.equal(groups.size, lanes.length);
for (const lane of lanes) {
  assert.deepEqual(groups.get(lane.diagram_id), nodes.filter(r => r.node.owner_id === lane.owner_id).map(r => r.diagram_id).sort());
}

assert(!/^\s*click\s+/im.test(source));
assert(!/<(?:script|iframe|object|embed|svg)\b/i.test(source));
const { svg } = await mermaid.render('t035Process', source);
const output = new JSDOM(svg, { contentType: 'image/svg+xml' }).window.document.documentElement;
assert.equal(output.querySelectorAll('g.node').length, nodes.length);
assert.equal(output.querySelectorAll('path.flowchart-link').length, edges.length);
if (process.argv[3]) {
  const labels = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
  const checkLabel = (text, label) => {
    assert.equal(text.split(label).length, 2);
    assert(output.textContent.includes(label));
  };
  checkLabel(db.getDiagramTitle(), labels.title);
  for (const [target, label] of Object.entries(labels.node)) {
    const matches = nodes.filter(({ diagram_id }) => db.getVertices().get(diagram_id).text.includes(label));
    assert.deepEqual(matches.map(record => record.node.id), [target]);
    checkLabel(db.getVertices().get(matches[0].diagram_id).text, label);
  }
  for (const [target, label] of Object.entries(labels.edge)) {
    const matches = edges.filter(({ index }) => db.getEdges()[index].text.includes(label));
    assert.deepEqual(matches.map(record => record.edge.id), [target]);
    checkLabel(db.getEdges()[matches[0].index].text, label);
  }
}
assert.equal(output.querySelectorAll('script,iframe,object,embed,image,a,foreignObject').length, 0);
assert.equal(output.querySelectorAll('[href],[xlink\\:href]').length, 0);
for (const element of output.querySelectorAll('*')) {
  for (const attribute of element.attributes) assert(!/^on/i.test(attribute.name));
}
console.log(JSON.stringify({ vertices: nodes.length, edges: edges.length, lanes: groups.size }));
