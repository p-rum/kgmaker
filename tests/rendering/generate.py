"""Generate actual compiler CFG for independent Mermaid parser checks."""
import argparse
import json
from pathlib import Path
import jsonschema
from kgmaker.inspection import inspect_frontend, inspect_jvm
from kgmaker.model import KnowledgeGraph
from kgmaker.flow import control_flow, mermaid
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--language',choices=('typescript','jvm'),default='typescript');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
root=Path(__file__).resolve().parents[2]
if a.language == 'jvm':
    realm={'repo_id':'fixture','module':'core','source_set':'main'}
    result=inspect_jvm(root/'fixtures/build-inspection/maven',repo_id='fixture',module='core',publish=False,
        classpath=[{'path':str(root/'fixtures/build-inspection/maven/target/classes'),'realm':realm},str(root/'workers/jvm/target/lib/kotlin-stdlib.jar')])
else:
    result=inspect_frontend(root/'fixtures/build-inspection/frontend',ui_framework='react',publish=False)
serialized=json.loads(json.dumps(result['graph']))
jsonschema.validate(serialized,json.loads((root/'docs/schemas/graph-v3.schema.json').read_text()))
graph=KnowledgeGraph.from_dict(serialized)
entry=next((c['method'] for c in graph.cfgs if any(b.get('kind')=='condition' for b in c['blocks'])),graph.cfgs[0]['method'])
report=control_flow(graph,entry)
(a.output/'flow.json').write_text(json.dumps(report,indent=2));(a.output/'flow.mmd').write_text(mermaid(report))
print('PASS: actual compiler graph-v3 JSON and source CFG generated')
