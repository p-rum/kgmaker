"""Opt-in, same-runner benchmark for the existing bounded view producers."""

import argparse
from dataclasses import replace
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
from statistics import median
import subprocess
import sys
from time import perf_counter_ns
import tracemalloc

from kgmaker import flow
from kgmaker.analysis_model import canonical
from kgmaker.architecture_model import ViewEdge
from kgmaker.topology_filter import filter_topology
from test_t017_filter_topology_scope import star
from test_unified_flow_views import model_graph


SERVICES = 100
BINDINGS = 10_000
CFG_BRANCHES = 1_600
CASES = ('topology', 'cyclic_cfg')
METRICS = ('cold_ns', 'warm_ns', 'peak_python_bytes')
TESTS = Path(__file__).resolve().parents[1]


def topology_fixture():
    template = star()
    ids = [f'service:{index:03d}' for index in range(SERVICES)]
    nodes = tuple(replace(template.nodes[0], id=identity, label=identity) for identity in ids)
    edges = []
    for index in range(BINDINGS):
        group, source = divmod(index, SERVICES)
        target = (source + 1 + group % (SERVICES - 1)) % SERVICES
        edges.append(ViewEdge(
            f'edge:{index:05d}', ids[source], ids[target], 'remote_http_request_response',
            original_ids=(f'binding:{index:05d}',), evidence_refs=('proof:declared',),
            unknown_refs=('proof:declared',), evidence_kinds=('SOURCE_ONLY',),
            resolution_status='AMBIGUOUS', freshness='UNKNOWN',
            attributes={'scope': 'production', 'context_ids': ['context:main']},
        ))
    return replace(template, nodes=nodes, edges=tuple(edges))


def cyclic_cfg_fixture():
    graph = model_graph()
    cfg = graph.cfgs[0]
    root, normal_exit, error_exit = (cfg['blocks'][index] for index in (0, -2, -1))
    leaves = [{**root, 'id': f'leaf-{index:04d}', 'kind': 'basic_block',
               'original_ids': [f'ast:leaf-{index:04d}']} for index in range(CFG_BRANCHES)]
    cfg['blocks'] = [root, *leaves, normal_exit, error_exit]
    cfg['edges'] = [{'source': 'entry', 'target': leaf['id'], 'kind': 'true'} for leaf in leaves]
    cfg['edges'] += [{'source': leaf['id'], 'target': 'entry', 'kind': 'normal', 'loop_back': True}
                     for leaf in leaves]
    return graph


def topology_report(topology, *, max_hops=5, max_nodes=5):
    return filter_topology(topology, focus_service='service:000', direction='outgoing',
                           max_hops=max_hops, max_nodes=max_nodes, scope='production',
                           context_ids=['context:main'])


def cyclic_cfg_report(graph):
    return flow.build_report(graph, 'method', view='control-flow', max_nodes=CFG_BRANCHES // 2)


def fingerprint(text):
    return sha256(text.encode('utf-8')).hexdigest()


def sample_case(case):
    if case == 'topology':
        fixture = topology_fixture()
        parameters = {'services': SERVICES, 'bindings': BINDINGS, 'max_hops': 5, 'max_nodes': 5}

        def operation():
            return canonical(topology_report(fixture)) + '\n'
    else:
        fixture = cyclic_cfg_fixture()
        parameters = {'branches': CFG_BRANCHES, 'cycle_edges': CFG_BRANCHES, 'max_nodes': CFG_BRANCHES // 2}

        def operation():
            return flow.render(cyclic_cfg_report(fixture), 'json')

    fixture_hash = fingerprint(canonical(fixture.to_dict()))
    started = perf_counter_ns()
    output = operation()
    cold = perf_counter_ns() - started
    output_hash = fingerprint(output)
    warm = []
    for _ in range(3):
        started = perf_counter_ns()
        output = operation()
        warm.append(perf_counter_ns() - started)
        if fingerprint(output) != output_hash:
            raise ValueError(f'{case} produced different warm output')
    tracemalloc.start()
    try:
        output = operation()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    if fingerprint(output) != output_hash or fingerprint(canonical(fixture.to_dict())) != fixture_hash:
        raise ValueError(f'{case} changed its input or measured output')
    return {'case': case, 'parameters': parameters, 'fixture_sha256': fixture_hash,
            'output_sha256': output_hash, 'output_bytes': len(output.encode('utf-8')),
            'source': str(Path(flow.__file__).resolve().parents[1]), 'cold_ns': cold,
            'warm_ns': median(warm), 'warm_samples_ns': warm, 'peak_python_bytes': peak}


def compare_samples(baseline, candidate):
    identity = ('case', 'parameters', 'fixture_sha256', 'output_sha256', 'output_bytes')
    first = baseline[0]
    if any(any(row[key] != first[key] for key in identity) for row in (*baseline, *candidate)):
        raise ValueError(f"{first['case']} has mismatched fixture or output identities")
    before = {metric: median(row[metric] for row in baseline) for metric in METRICS}
    after = {metric: median(row[metric] for row in candidate) for metric in METRICS}
    exceeded = [metric for metric in METRICS if 4 * after[metric] > 5 * before[metric]]
    return {**{key: first[key] for key in identity}, 'baseline_medians': before,
            'candidate_medians': after, 'over_25_percent': exceeded,
            'baseline_samples': baseline, 'candidate_samples': candidate}


def measure(source, case):
    env = {**os.environ, 'PYTHONPATH': os.pathsep.join((str(source), str(TESTS))),
           'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1'}
    process = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--sample', case],
                             env=env, capture_output=True, text=True, check=True)
    sample = json.loads(process.stdout)
    if Path(sample['source']) != source:
        raise ValueError(f'benchmark loaded an unexpected source tree for {case}')
    return sample


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-source', type=Path, help='src directory of the comparison revision')
    parser.add_argument('--samples', type=int, default=3, help='fresh processes per case and source')
    parser.add_argument('--sample', choices=CASES, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.sample:
        print(json.dumps(sample_case(args.sample)))
        return 0
    if args.baseline_source is None or args.samples < 1:
        parser.error('a baseline source and positive sample count are required')
    sources = {'baseline': args.baseline_source.resolve(), 'candidate': TESTS.parent / 'src'}
    if not all((root / 'kgmaker/flow.py').is_file() for root in sources.values()):
        parser.error('baseline and candidate must contain src/kgmaker/flow.py')
    cases = []
    try:
        for case in CASES:
            samples = {side: [] for side in sources}
            for index in range(args.samples):
                order = sources if index % 2 == 0 else reversed(sources)
                for side in order:
                    samples[side].append(measure(sources[side], case))
            cases.append(compare_samples(samples['baseline'], samples['candidate']))
    except (ValueError, subprocess.CalledProcessError) as error:
        print(str(getattr(error, 'stderr', None) or error), file=sys.stderr)
        return 2
    report = {'runner': {'platform': platform.platform(), 'python': platform.python_version(),
                         'machine': platform.machine(), 'logical_cpus': os.cpu_count(),
                         'executable': sys.executable},
              'relative_tolerance_percent': 25, 'samples_per_source': args.samples, 'cases': cases}
    print(json.dumps(report, indent=2))
    return int(any(case['over_25_percent'] for case in cases))


if __name__ == '__main__':
    raise SystemExit(main())
