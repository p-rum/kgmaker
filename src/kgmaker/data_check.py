"""Thin, read-only structured-input audit over the existing feature pipeline.

Only semantic specifications are accepted. Hashes, availability and the candidate
envelope come from the packet and validator, never from the caller or a model.
"""
from __future__ import annotations

import copy
from dataclasses import asdict
from pathlib import Path

from . import feature
from .analysis_model import AnalysisError, INPUT_METADATA, inventory_candidate, safe_path
from .analysis_report import render_report
from .dataflow import impact_paths
from .store import query_nodes

DATA_SCHEMA_VERSION = 1


def _object(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= set(value) or set(value) - set(required) - set(optional):
        raise AnalysisError("Invalid DataRequirementSet fields; required: " + ", ".join(sorted(required)))


def _array(value, label):
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise AnalysisError(label + " must be an array of objects")


def _ids(value, allowed, label):
    if (not isinstance(value, list) or any(not isinstance(x, str) for x in value)
            or len(set(value)) != len(value) or not set(value) <= allowed):
        raise AnalysisError(label + " must contain unique, existing IDs")


def data_check(root: Path, analysis_id: str, specification: dict) -> dict:
    """Return validated candidate + rendered report; never write/apply artifacts."""
    packet = feature.load_packet(root, analysis_id)
    candidate = inventory_candidate(packet)
    initial = feature.validate(root, analysis_id, candidate)
    if not initial['valid']:
        return initial
    _object(specification, {'schema_version', 'analysis_id', 'requirement_hash', 'requirements', 'inputs'})
    if type(specification['schema_version']) is not int or specification['schema_version'] != DATA_SCHEMA_VERSION:
        raise AnalysisError('Unsupported DataRequirementSet schema_version')
    if specification['analysis_id'] != analysis_id:
        raise AnalysisError('DataRequirementSet analysis_id mismatch')
    if specification['requirement_hash'] != packet['requirement_hash']:
        raise AnalysisError('DataRequirementSet requirement_hash is stale; recheck specification after prepare/revise', 3)
    _array(specification['requirements'], 'requirements')
    _array(specification['inputs'], 'inputs')
    prefix = f'analysis:{analysis_id}:'
    candidate['requirements'] = []
    for index, requirement in enumerate(specification['requirements']):
        _object(requirement, {'id', 'text', 'kind', 'source_quote'}, {'source_reference'})
        candidate['requirements'].append({key: copy.deepcopy(requirement[key]) for key in
                                           ('id', 'text', 'kind', 'source_quote')})
        candidate['requirements'][-1]['status'] = 'UNRESOLVED'
        reference = requirement.get('source_reference')
        if reference is not None:
            _object(reference, {'path', 'location'}, {'quote', 'value'})
            path = reference['path']
            safe_path(root, path)
            source = packet['source_manifest'].get(path)
            if source is None:
                raise AnalysisError('Requirement reference must be in the packet source manifest')
            candidate['evidence'].append({
                **copy.deepcopy(reference), 'id': prefix + f'evidence:requirement-{index}',
                'source_id': path, 'kind': source['kind'], 'sha256': source['sha256'],
                'supports': 'Supplied requirement reference; not proof of business equivalence.',
                'method': 'EXTRACTED', 'validity': 'VALID', 'confidence': 1,
            })
    # Reuse the feature validator for semantic references before using them as keys.
    preflight = feature.validate(root, analysis_id, candidate)
    if not preflight['valid']:
        return preflight
    graph, _, _ = feature.current_graph(root)
    nodes = {n.id: n for n in graph.nodes}
    if set(nodes) != set(packet['allowed_graph_ids']):
        raise AnalysisError('AS_IS graph changed during data check; refresh the packet', 3)
    candidate_sources, ambiguities, tool_gaps = [], [], []
    requirement_ids = {r['id'] for r in candidate['requirements']}
    input_ids = set()
    for item in specification['inputs']:
        _object(item, {'id', 'name', 'requirement_ids'} | set(INPUT_METADATA),
                {'candidate_entity_ids', 'owner_role', 'dependency_ids', 'transformation'})
        identity = item['id']
        if not isinstance(item['name'], str) or not item['name'].strip():
            raise AnalysisError('Input name must be a non-empty string')
        if not isinstance(identity, str) or not identity.startswith(prefix + 'input:') or identity in input_ids:
            raise AnalysisError('Inputs require unique analysis-scoped input IDs')
        input_ids.add(identity)
    for index, item in enumerate(specification['inputs']):
        _ids(item['requirement_ids'], requirement_ids, 'requirement_ids')
        _ids(item.get('dependency_ids', []), input_ids, 'dependency_ids')
        explicit = item.get('candidate_entity_ids', [])
        _ids(explicit, set(packet['allowed_graph_ids']), 'candidate_entity_ids')
        selected = [nodes[identity] for identity in explicit]
        if not explicit:
            matches = [n for n, _ in query_nodes(graph, item['name'], len(graph.nodes))
                       if n.kind in {'data_field', 'contract_field', 'db_column'}]
            selected = matches[:10]
            if len(matches) > 10:
                tool_gaps.append({'input_id': item['id'], 'kind': 'CANDIDATE_LIMIT',
                                  'reason': f'{len(matches) - 10} navigation candidates omitted'})
        citations = []
        for number, node in enumerate(selected):
            source = packet['source_manifest'].get(node.path)
            if source is None or node.line is None:
                tool_gaps.append({'input_id': item['id'], 'kind': 'SOURCE_LOCATION',
                                  'reason': 'Candidate has no supported source locator: ' + node.id})
                continue
            lines = safe_path(root, node.path).read_text(encoding='utf-8').splitlines()
            if not 1 <= node.line <= len(lines) or not lines[node.line - 1].strip():
                raise AnalysisError('Candidate source location changed during data check', 3)
            evidence_id = prefix + f'evidence:input-{index}-source-{number}'
            citations.append(evidence_id)
            candidate['evidence'].append({
                'id': evidence_id, 'source_id': node.id, 'kind': source['kind'], 'path': node.path,
                'sha256': source['sha256'], 'location': {'type': 'lines', 'start': node.line, 'end': node.line},
                'quote': lines[node.line - 1], 'supports': 'Static declaration/navigation candidate only; no populated-data or business-equivalence proof.',
                'method': 'EXTRACTED', 'validity': 'VALID', 'confidence': 1,
            })
            candidate_sources.append({'input_id': item['id'], 'entity': asdict(node),
                                      'evidence_id': evidence_id, 'match_status': 'UNASSESSED',
                                      'static_impact': impact_paths(graph, node.id)})
        business_unknowns = [key for key in INPUT_METADATA if item[key] is None]
        question_ids = []
        if business_unknowns:
            question_id = prefix + f'question:input-{index}-definition'
            question_ids.append(question_id)
            text = 'Define required input ' + item['name'] + ': ' + ', '.join(business_unknowns) + '.'
            candidate['questions'].append({'id': question_id, 'text': text, 'owner_role': item.get('owner_role'),
                                           'requirement_ids': item['requirement_ids'], 'status': 'OPEN', 'blocking': True})
            ambiguities.append({'input_id': item['id'], 'question_id': question_id,
                                'kind': 'BUSINESS_METADATA', 'fields': business_unknowns})
        if selected:
            ambiguities.append({'input_id': item['id'], 'kind': 'BUSINESS_EQUIVALENCE',
                                'candidate_entity_ids': [n.id for n in selected],
                                'reason': 'Navigation matches do not establish equivalent business definitions.'})
        reason = 'No supported positive availability proof checker; static declarations do not prove populated, usable values.'
        if not selected:
            reason += ' No field navigation candidate found in this supplied scope; this is not a confirmed missing input.'
        deps = item.get('dependency_ids', [])
        candidate['input_requirements'].append({
            **{key: copy.deepcopy(item[key]) for key in INPUT_METADATA},
            'id': item['id'], 'name': item['name'], 'requirement_ids': item['requirement_ids'],
            'source_ids': [n.id for n in selected], 'evidence_ids': citations,
            'dependency_ids': deps, 'question_ids': question_ids,
            'availability': 'UNKNOWN', 'acquisition': 'DERIVED' if deps else 'UNRESOLVED',
            'usability': 'UNASSESSED', 'transformation': item.get('transformation'),
            'owner_role': item.get('owner_role'), 'verification_scope': 'Supplied single repository root; packet coverage and exclusions apply.',
            'next_step': 'Specify the required definition, keys, units and temporal meaning; delivery is not yet confirmed.',
        })
        tool_gaps.append({'input_id': item['id'], 'kind': 'AVAILABILITY_PROOF', 'reason': reason})
    # Let the normal validator check references, citations, metadata, and cycles.
    for reason in packet['coverage']['limitations']:
        tool_gaps.append({'input_id': None, 'kind': 'PARSER_ACCESS', 'reason': reason})
    for key in ('omitted_sources', 'unsupported_sources', 'exclusions', 'dataflow_diagnostics'):
        if packet['coverage'].get(key):
            tool_gaps.append({'input_id': None, 'kind': key.upper(), 'details': packet['coverage'][key]})
    pending = packet['coverage']['pending'] + [gap.get('reason', gap['kind']) for gap in tool_gaps]
    pending += ['Resolve business ambiguity for ' + a['input_id'] for a in ambiguities]
    candidate['completion'] = {'processing_status': 'PARTIAL', 'decision_readiness': 'BLOCKED',
                               'pending': sorted(set(pending))}
    # Even an empty specification needs semantic assessment, never automatic readiness.
    if not candidate['completion']['pending']:
        candidate['completion']['pending'] = ['Data prerequisite assessment is incomplete.']
    validation = feature.validate(root, analysis_id, candidate)
    if not validation['valid']:
        return validation
    return {**validation, 'schema_version': DATA_SCHEMA_VERSION, 'analysis_id': analysis_id,
            'candidate': candidate, 'candidate_sources': candidate_sources,
            'ambiguity_queue': ambiguities, 'business_decisions': candidate['questions'],
            'data_delivery_gaps': [], 'coverage_gaps': tool_gaps,
            'interpretation': 'No delivery absence is confirmed. UNKNOWN does not mean missing business data.',
            'report': render_report(candidate, packet, [], applied=False, data_audit={'coverage_gaps': tool_gaps})}
