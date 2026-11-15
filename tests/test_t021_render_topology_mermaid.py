"""T021 public contract tests; fixtures are hand-labelled model inputs, not runtime proof."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
from contextlib import redirect_stdout
from io import StringIO

import pytest

from kgmaker.architecture_model import ViewDocument, ViewEdge, ViewNode
from kgmaker.architecture_render import render_topology_mermaid
from kgmaker.topology_filter import filter_topology


ROOT = Path(__file__).parents[1]


def golden_topology():
    nodes = (
        ViewNode('service:checkout', 'service', 'Checkout “API” [prod]', attributes={
            'scope': 'production', 'logical_id': 'service:checkout', 'context_ids': ['ctx:prod'],
        }, evidence_refs=('proof:service',), evidence_kinds=('SOURCE_ONLY',),
                 resolution_status='RESOLVED'),
        ViewNode('service:orders', 'service', 'Orders', attributes={
            'scope': 'production', 'logical_id': 'service:orders', 'context_ids': ['ctx:prod'],
        }, evidence_refs=('proof:service',), evidence_kinds=('SOURCE_ONLY',),
                 resolution_status='RESOLVED'),
        ViewNode('channel:kafka:alpha:orders', 'kafka_channel', 'orders “α” [topic] %%{init: {"securityLevel":"loose"}}%%', attributes={
            'scope': 'production', 'logical_id': 'channel:orders', 'broker_realm': 'alpha',
            'context_ids': ['ctx:prod'],
        }, evidence_refs=('proof:channel',), evidence_kinds=('SOURCE_ONLY',),
                 resolution_status='UNRESOLVED'),
        ViewNode('resource:db:alpha', 'data_resource', 'ledger <svg/onload=alert(1)>\n%{click}', attributes={
            'scope': 'production', 'logical_id': 'resource:ledger', 'realm': 'alpha',
            'context_ids': ['ctx:prod'],
        }, evidence_refs=('proof:resource',), evidence_kinds=('SOURCE_ONLY',),
                 resolution_status='RESOLVED'),
        ViewNode('resource:db:beta', 'data_resource', 'ledger', attributes={
            'scope': 'production', 'logical_id': 'resource:ledger', 'realm': 'beta',
            'context_ids': ['ctx:prod'],
        }, evidence_refs=('proof:resource',), evidence_kinds=('SOURCE_ONLY',),
                 resolution_status='RESOLVED'),
    )
    edges = (
        ViewEdge('edge:http', 'service:checkout', 'service:orders', 'remote_http_request_response',
                 attributes={'scope': 'production', 'context_ids': ['ctx:prod']},
                 evidence_refs=('proof:http',), evidence_kinds=('SOURCE_ONLY',),
                 resolution_status='RESOLVED', freshness='UNKNOWN'),
        ViewEdge('edge:async', 'service:orders', 'channel:kafka:alpha:orders', 'publishes_to_channel',
                 attributes={'scope': 'production', 'context_ids': ['ctx:prod'], 'async': True},
                 evidence_refs=('proof:channel',), evidence_kinds=('SOURCE_ONLY',),
                 resolution_status='UNRESOLVED', freshness='UNKNOWN'),
        ViewEdge('edge:db', 'service:orders', 'resource:db:alpha', 'reads',
                 attributes={'scope': 'production', 'context_ids': ['ctx:prod']},
                 evidence_refs=('proof:resource',), evidence_kinds=('SOURCE_ONLY',),
                 resolution_status='RESOLVED', freshness='UNKNOWN'),
        ViewEdge('edge:unknown', 'service:checkout', 'resource:db:beta', 'unclassified_sync',
                 attributes={'scope': 'production', 'context_ids': ['ctx:prod']},
                 evidence_refs=('proof:resource',), evidence_kinds=('SOURCE_ONLY',),
                 resolution_status='UNRESOLVED', freshness='UNKNOWN'),
    )
    proofs = tuple({'id': f'proof:{kind}', 'evidence_kind': 'SOURCE_ONLY',
                    'freshness': 'UNKNOWN', 'polarity': 'UNKNOWN', 'scope': 'production'}
                   for kind in ('service', 'channel', 'resource', 'http'))
    document = ViewDocument('view:topology:golden', 'topology', 'a' * 64,
        'service-topology-view-1', 'production', {'contexts': [{'id': 'ctx:prod'}]},
        nodes=nodes, edges=edges,
        coverage={'status': 'PARTIAL', 'truncated': True,
                  'reason': 'node limit; omitted alternatives remain in filtering inventory'},
        provenance=proofs, limits=('max_nodes=5',))
    return filter_topology(document, max_nodes=5)


def test_t021_golden_projects_exact_http_kafka_and_db_model_without_fake_vertices():
    source = golden_topology()
    before = deepcopy(source)
    text = render_topology_mermaid(source)
    rows = [line for line in text.splitlines() if line.startswith('  n') and '[' in line]
    edges = [line for line in text.splitlines() if '-->' in line or '-.->' in line]
    assert len(rows) == len(source['document']['nodes'])
    assert len(edges) == len(source['document']['edges'])
    assert 'HTTP request/response' in text
    assert 'ASYNC; delivery UNKNOWN' in text
    assert 'UNKNOWN relation: unclassified_sync; execution UNKNOWN' in text
    assert 'reads' in text.lower()
    assert 'Evidence: SOURCE_ONLY' in text and 'Coverage: PARTIAL' in text
    assert 'truncated' in text.lower() and 'UNKNOWN' in text
    assert '<' not in text and '%%{init:' not in text
    meta_line=next(line for line in text.splitlines() if line.startswith('  %% topology-meta '))
    assert json.loads(meta_line.removeprefix('  %% topology-meta '))==source
    assert source == before


def test_t021_hashes_logical_identity_with_realm_and_keeps_provenance():
    text = render_topology_mermaid(golden_topology())
    left = json.dumps({'context_ids':['ctx:prod'],'logical_id':'resource:ledger','owner_id':None,
                       'realm':{'realm':'alpha'},'scope':'production'},sort_keys=True,separators=(',',':'))
    right = json.dumps({'context_ids':['ctx:prod'],'logical_id':'resource:ledger','owner_id':None,
                        'realm':{'realm':'beta'},'scope':'production'},sort_keys=True,separators=(',',':'))
    assert f"n{hashlib.sha256(left.encode()).hexdigest()}" in text
    assert f"n{hashlib.sha256(right.encode()).hexdigest()}" in text
    assert '%% topology-meta ' in text and 'proof:channel' in text


def test_t021_invalid_inputs_are_read_only_and_rejected():
    source = golden_topology()
    before = deepcopy(source)
    source['document']['edges'][0]['target'] = 'missing:node'
    invalid = deepcopy(source)
    with pytest.raises((ValueError, TypeError)):
        render_topology_mermaid(source)
    assert source == invalid and source != before


def test_t021_pure_renderer_never_starts_process_or_network(monkeypatch):
    import socket
    def forbidden(*args, **kwargs):
        raise AssertionError('renderer attempted process/network I/O')
    monkeypatch.setattr(subprocess,'Popen',forbidden)
    monkeypatch.setattr(socket,'socket',forbidden)
    result=render_topology_mermaid(golden_topology())
    assert 'flowchart LR' in result


def test_t021_real_mermaid_114_parser_and_renderer_accepts_malicious_labels(tmp_path):
    text = render_topology_mermaid(golden_topology())
    output = tmp_path / 'topology.mmd'
    output.write_text(text, encoding='utf-8')
    harness = ROOT / 'tests/rendering/validate_t021_topology.mjs'
    result = subprocess.run(['node', str(harness), str(output)], cwd=ROOT,
                            text=True, capture_output=True, check=False)
    if result.returncode and 'ERR_MODULE_NOT_FOUND' in result.stderr:
        pytest.skip('Mermaid 11.4.1/jsdom test dependencies unavailable')
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt['status'] == 'PASS'
    assert receipt['vertices'] == 5 and receipt['edges'] == 4


@pytest.mark.parametrize('transport,expected_edges',[('HTTP',1),('KAFKA',2)])
def test_t021_real_t016_http_kafka_topology_parses_and_renders(tmp_path,transport,expected_edges):
    from test_t016_aggregate_service_topology import labelled_handoff
    from kgmaker.service_topology import aggregate_service_topology
    text=render_topology_mermaid(filter_topology(aggregate_service_topology(labelled_handoff(transport))))
    output=tmp_path/f'{transport.lower()}.mmd'
    output.write_text(text,encoding='utf-8')
    harness=ROOT/'tests/rendering/validate_t021_topology.mjs'
    result=subprocess.run(['node',str(harness),str(output)],cwd=ROOT,text=True,capture_output=True,check=False)
    if result.returncode and 'ERR_MODULE_NOT_FOUND' in result.stderr:
        pytest.skip('Mermaid 11.4.1/jsdom test dependencies unavailable')
    assert result.returncode==0,result.stderr
    receipt=json.loads(result.stdout)
    assert receipt['status']=='PASS' and receipt['vertices']==2+(transport=='KAFKA')
    assert receipt['edges']==expected_edges


def test_t021_architecture_cli_topology_mermaid_replays_t019_snapshot(tmp_path):
    from kgmaker.architecture_cli import run
    from test_t016_aggregate_service_topology import labelled_handoff
    snapshot=tmp_path/'topology.json'
    snapshot.write_text(json.dumps(labelled_handoff()),encoding='utf-8')
    output=StringIO()
    with redirect_stdout(output):
        code=run(['topology','--root',str(tmp_path),'--capture-snapshot',str(snapshot),'--format','mermaid'])
    assert code==0
    text=output.getvalue()
    assert text.startswith('---\ntitle:') and 'flowchart LR' in text
    assert 'Evidence:' in text and 'Coverage:' in text


def test_t021_cli_render_failure_preserves_last_valid_artifact_and_skips_publish(tmp_path,monkeypatch):
    import kgmaker.architecture_cli as cli
    artifact=tmp_path/'valid.mmd';artifact.write_text('last-valid\n',encoding='utf-8')
    published=[]
    class Prepared:
        def publish(self):
            published.append(True);artifact.write_text('mutated\n',encoding='utf-8')
    def invalid(args,selected):
        args.prepared_view=Prepared()
        return ({'document': {'not':'a view'},'filtering':{}},'a'*64)
    monkeypatch.setattr(cli,'_topology',invalid)
    output=StringIO()
    with redirect_stdout(output):
        code=cli.run(['topology','--root',str(tmp_path),'--capture-snapshot','ignored.json','--format','mermaid'])
    assert code==2 and output.getvalue()==''
    assert artifact.read_text(encoding='utf-8')=='last-valid\n' and published==[]
