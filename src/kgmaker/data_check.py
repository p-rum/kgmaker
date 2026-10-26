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
    _object(specification, {'schema_version', 'analysis_id', 'requirement_hash', 'requirements', 'inputs'}, {'evidence_references'})
    if type(specification['schema_version']) is not int or specification['schema_version'] != DATA_SCHEMA_VERSION:
        raise AnalysisError('Unsupported DataRequirementSet schema_version')
    if specification['analysis_id'] != analysis_id:
        raise AnalysisError('DataRequirementSet analysis_id mismatch')
    if specification['requirement_hash'] != packet['requirement_hash']:
        raise AnalysisError('DataRequirementSet requirement_hash is stale; recheck specification after prepare/revise', 3)
    _array(specification['requirements'], 'requirements')
    _array(specification['inputs'], 'inputs')
    prefix = f'analysis:{analysis_id}:'
    def reference_evidence(reference, identity):
        from .workspace import source_key
        _object(reference, {'path', 'location'}, {'quote', 'value', 'repo_id'})
        key = source_key(reference['repo_id'], reference['path']) if packet.get('workspace') and isinstance(reference.get('repo_id'), str) else reference['path']
        source = packet['source_manifest'].get(key)
        if source is None:
            raise AnalysisError('Evidence reference must be in the approved packet source manifest')
        feature.source_path(root, key, packet)
        return {**copy.deepcopy(reference), 'id': identity, 'source_id': key, 'kind': source['kind'],
                'sha256': source['sha256'], 'supports': 'Supplied reference; claims checked separately by availability proof.',
                'method': 'EXTRACTED', 'validity': 'VALID', 'confidence': 1}
    references = specification.get('evidence_references', [])
    _array(references, 'evidence_references')
    for reference in references:
        _object(reference, {'id', 'path', 'location'}, {'repo_id', 'quote', 'value'})
        candidate['evidence'].append(reference_evidence({k: v for k, v in reference.items() if k != 'id'}, reference['id']))
    candidate['requirements'] = []
    for index, requirement in enumerate(specification['requirements']):
        _object(requirement, {'id', 'text', 'kind', 'source_quote'}, {'source_reference'})
        candidate['requirements'].append({key: copy.deepcopy(requirement[key]) for key in
                                           ('id', 'text', 'kind', 'source_quote')})
        candidate['requirements'][-1]['status'] = 'UNRESOLVED'
        reference = requirement.get('source_reference')
        if reference is not None:
            candidate['evidence'].append(reference_evidence(reference, prefix + f'evidence:requirement-{index}'))
    # Reuse the feature validator for semantic references before using them as keys.
    preflight = feature.validate(root, analysis_id, candidate)
    if not preflight['valid']:
        return preflight
    graph = feature.graph_for_packet(root, packet)
    nodes = {n.id: n for n in graph.nodes}
    if set(nodes) != set(packet['allowed_graph_ids']):
        raise AnalysisError('AS_IS graph changed during data check; refresh the packet', 3)
    candidate_sources, ambiguities, tool_gaps = [], [], []
    requirement_ids = {r['id'] for r in candidate['requirements']}
    input_ids = set()
    for item in specification['inputs']:
        _object(item, {'id', 'name', 'requirement_ids'} | set(INPUT_METADATA),
                {'candidate_entity_ids', 'owner_role', 'dependency_ids', 'transformation', 'availability_proof'})
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
                       if n.kind in {'data_field', 'contract_field', 'db_column', 'workbook_cell',
                                     'template_variable'}]
            selected = matches[:10]
            if len(matches) > 10:
                tool_gaps.append({'input_id': item['id'], 'kind': 'CANDIDATE_LIMIT',
                                  'reason': f'{len(matches) - 10} navigation candidates omitted'})
        citations = []
        for number, node in enumerate(selected):
            source = packet['source_manifest'].get(node.path)
            if source is None:
                tool_gaps.append({'input_id': item['id'], 'kind': 'SOURCE_LOCATION',
                                  'reason': 'Candidate has no supported source locator: ' + node.id})
                continue
            evidence_id = prefix + f'evidence:input-{index}-source-{number}'
            citations.append(evidence_id)
            if node.kind == 'workbook_cell' and node.metadata:
                value = {key: node.metadata.get(key) for key in
                         ('formula', 'cached_value', 'cached_value_freshness')}
                evidence_item = {
                    'id': evidence_id, 'source_id': node.id, 'kind': source['kind'],
                    'path': source.get('path', node.path), 'sha256': source['sha256'],
                    'location': {'type': 'workbook_cell', 'sheet': node.metadata['sheet'],
                                 'cell': node.metadata['cell']}, 'value': value,
                    'supports': 'Workbook formula/cached-value locator; cached value freshness is unknown and no formula was evaluated.',
                    'method': 'EXTRACTED', 'validity': 'VALID', 'confidence': 1,
                }
            else:
                if node.line is None:
                    tool_gaps.append({'input_id': item['id'], 'kind': 'SOURCE_LOCATION',
                                      'reason': 'Candidate has no supported source locator: ' + node.id})
                    citations.pop()
                    continue
                lines = feature.source_path(root, node.path, packet).read_text(encoding='utf-8').splitlines()
                if not 1 <= node.line <= len(lines) or not lines[node.line - 1].strip():
                    raise AnalysisError('Candidate source location changed during data check', 3)
                evidence_item = {
                    'id': evidence_id, 'source_id': node.id, 'kind': source['kind'],
                    'path': source.get('path', node.path), 'sha256': source['sha256'],
                    'location': {'type': 'lines', 'start': node.line, 'end': node.line},
                    'quote': lines[node.line - 1],
                    'supports': 'Static declaration/navigation candidate only; no populated-data or business-equivalence proof.',
                    'method': 'EXTRACTED', 'validity': 'VALID', 'confidence': 1,
                }
            candidate['evidence'].append(evidence_item)
            if packet.get('workspace'):
                candidate['evidence'][-1]['repo_id'] = source['repo_id']
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
        reason = 'No supported positive availability proof supplied; static declarations do not prove populated, usable values.'
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
        if item.get('availability_proof') is not None:
            candidate['input_requirements'][-1]['availability_proof'] = copy.deepcopy(item['availability_proof'])
            proof = item['availability_proof']
            if isinstance(proof, dict):
                for key in ('evidence_id', 'observation_evidence_id'):
                    if isinstance(proof.get(key), str):
                        candidate['input_requirements'][-1]['evidence_ids'].append(proof[key])
            if isinstance(proof, dict) and proof.get('kind') == 'APPROVED_MISSING':
                answer = next((a for a in packet['answers'] if a['decision_id'] == proof.get('decision_id')), None)
                if answer:
                    candidate['evidence'].append({'id': prefix + f'evidence:missing-{index}', 'source_id': answer['decision_id'],
                                                 'kind': 'HUMAN_DECISION', 'supports': 'Explicit scoped missing-data decision',
                                                 'method': 'EXTRACTED', 'validity': 'VALID', 'confidence': 1, **answer})
                    candidate['input_requirements'][-1]['evidence_ids'].append(prefix + f'evidence:missing-{index}')
        else:
            tool_gaps.append({'input_id': item['id'], 'kind': 'AVAILABILITY_PROOF', 'reason': reason})
    from .availability import evaluate_proof
    for item in candidate['input_requirements']:
        if 'availability_proof' not in item:
            continue
        try:
            checked = evaluate_proof(root, packet, candidate, item, graph)
            item['availability'], item['usability'], item['verification_scope'] = checked['availability'], checked['usability'], checked['scope']
            item['next_step'] = 'Use only within the validated evidence scope; recheck freshness before implementation.'
            ambiguities = [a for a in ambiguities if a['input_id'] != item['id'] or a['kind'] != 'BUSINESS_EQUIVALENCE']
        except (AnalysisError, KeyError, TypeError, ValueError) as exc:
            tool_gaps.append({'input_id': item['id'], 'kind': 'PROOF_REJECTED', 'reason': str(exc)})
    # Let the normal validator check references, citations, metadata, and cycles.
    for reason in packet['coverage']['limitations']:
        tool_gaps.append({'input_id': None, 'kind': 'PARSER_ACCESS', 'reason': reason})
    for key in ('omitted_sources', 'unsupported_sources', 'exclusions', 'dataflow_diagnostics', 'artifact_diagnostics'):
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
            'data_delivery_gaps': [item for item in candidate['input_requirements'] if item['availability'] == 'CONFIRMED_MISSING'], 'coverage_gaps': tool_gaps,
            'interpretation': 'No delivery absence is confirmed. UNKNOWN does not mean missing business data.',
            'report': render_report(candidate, packet, [], applied=False, data_audit={'coverage_gaps': tool_gaps})}
