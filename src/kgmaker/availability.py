"""Fail-closed positive availability proofs over citations and current value paths.

A supplied observation is scoped evidence, not independently authenticated
production data. Migration declarations alone can never satisfy this checker.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from .analysis_model import AnalysisError, INPUT_METADATA
from .dataflow import impact_paths


def observation_staleness(candidate: dict) -> list[str]:
    result = []
    evidence = {e.get('id'): e for e in candidate.get('evidence', []) if isinstance(e, dict)}
    for item in candidate.get('input_requirements', []):
        if not isinstance(item, dict) or item.get('availability') not in {'AVAILABLE', 'PARTIAL'}:
            continue
        proof = item.get('availability_proof', {})
        if not isinstance(proof, dict) or proof.get('kind') != 'OBSERVED_VALUE_PATH':
            continue
        observation = evidence.get(proof.get('observation_evidence_id'), {}).get('value', {})
        try:
            collected = datetime.fromisoformat(observation['collected_at'].replace('Z', '+00:00'))
            age = (datetime.now(timezone.utc) - collected).total_seconds()
            maximum = observation['max_age_seconds']
            if type(maximum) is int and (age < 0 or age > maximum):
                result.append('Supplied observation expired/future: ' + item['id'])
        except (KeyError, TypeError, ValueError):
            pass  # malformed evidence is a normal validation error
    return result


def evaluate_proof(root, packet, candidate, item, graph=None) -> dict:
    proof = item.get('availability_proof')
    if not isinstance(proof, dict):
        raise AnalysisError('Positive availability requires a supported availability_proof')
    citations = {e['id']: e for e in candidate['evidence']}
    kind = proof.get('kind')
    if kind == 'APPROVED_MISSING':
        if set(proof) != {'kind', 'decision_id', 'scope'}:
            raise AnalysisError('Invalid approved-missing proof fields')
        answer = next((a for a in packet['answers'] if a['decision_id'] == proof['decision_id']), None)
        if not answer or answer['approval_status'] != 'APPROVED':
            raise AnalysisError('Missing-data proof needs an explicit approved decision')
        try:
            decision = json.loads(answer['answer'])
        except ValueError as exc:
            raise AnalysisError('Missing decision answer must be structured JSON') from exc
        if decision != {'input_id': item['id'], 'scope': proof['scope'], 'confirmed_missing': True} or not isinstance(proof['scope'], str) or not proof['scope'].strip():
            raise AnalysisError('Missing-data decision must match input and exact limited scope')
        if not any(e.get('kind') == 'HUMAN_DECISION' and e.get('decision_id') == proof['decision_id']
                   and e.get('approval_status') == 'APPROVED' for e in candidate['evidence']):
            raise AnalysisError('Missing-data decision must have validated human evidence')
        return {'availability': 'CONFIRMED_MISSING', 'usability': 'INCOMPATIBLE', 'scope': proof['scope']}
    if kind == 'CLOSED_CONTRACT_ABSENCE':
        if set(proof) != {'kind', 'evidence_id', 'field'}:
            raise AnalysisError('Invalid contract-absence proof fields')
        evidence = citations.get(proof['evidence_id'], {})
        if proof['evidence_id'] not in item['evidence_ids']:
            raise AnalysisError('Contract-absence proof must be cited by the input')
        value = evidence.get('value')
        if (evidence.get('kind') != 'CONTRACT' or evidence.get('validity') != 'VALID'
                or evidence.get('location', {}).get('type') != 'json_pointer'
                or not isinstance(value, dict) or value.get('additionalProperties') is not False
                or not isinstance(value.get('properties'), dict) or not isinstance(proof['field'], str)
                or proof['field'] in value['properties']):
            raise AnalysisError('Absence proof requires a cited closed object schema and an absent field')
        return {'availability': 'CONFIRMED_MISSING', 'usability': 'INCOMPATIBLE',
                'scope': f"Only contract {evidence.get('repo_id', '.')}/{evidence.get('path')}#{evidence['location']['pointer']}"}
    if kind != 'OBSERVED_VALUE_PATH' or set(proof) != {'kind', 'source_entity_id', 'target_entity_id', 'observation_evidence_id', 'mapping_decision_id'}:
        raise AnalysisError('Unsupported availability proof kind or fields')
    source, target = proof['source_entity_id'], proof['target_entity_id']
    if source not in packet['allowed_graph_ids'] or target not in packet['allowed_graph_ids'] or target not in item['source_ids']:
        raise AnalysisError('Observation path must bind real graph entities and the input source')
    if graph is None:
        from .feature import graph_for_packet
        graph = graph_for_packet(root, packet)
    paths = impact_paths(graph, source)['paths']
    matches = [p for p in paths if p['entity_ids'][-1] == target and p['weakest_confidence'] == 'EXTRACTED']
    if source != target and not matches:
        raise AnalysisError('Availability needs a fully EXTRACTED supported value path, not a heuristic match')
    path = matches[0] if matches else {'entity_ids': [source], 'edges': []}
    evidence = citations.get(proof['observation_evidence_id'], {})
    if proof['observation_evidence_id'] not in item['evidence_ids']:
        raise AnalysisError('Observation proof must be cited by the input')
    observation = evidence.get('value')
    if (evidence.get('kind') != 'CONTRACT' or evidence.get('validity') != 'VALID'
            or evidence.get('location', {}).get('type') != 'json_pointer' or not isinstance(observation, dict)
            or observation.get('schema_version') != 1 or observation.get('kind') != 'SUPPLIED_DATA_OBSERVATION'
            or observation.get('entity_id') != source):
        raise AnalysisError('Availability needs an exact cited supplied data observation, not a DTO/schema declaration')
    if not isinstance(observation.get('scope'), str) or not observation['scope'].strip():
        raise AnalysisError('Observation requires an explicit environment/dataset scope')
    if observation.get('value') is None:
        raise AnalysisError('No populated value in observation')
    hashes = observation.get('source_hashes')
    if not isinstance(hashes, dict):
        raise AnalysisError('Observation needs source_hashes for all value-path files')
    nodes = {n.id: n for n in graph.nodes}
    if any('PARTIAL' in (nodes[entity].summary or '') for entity in path['entity_ids']):
        raise AnalysisError('Availability path depends on a partial schema reconstruction')
    needed = {nodes[entity].path for entity in path['entity_ids']}
    needed |= {e['source_file'] for e in path['edges'] if e['source_file']}
    if not needed <= hashes.keys() or any(packet['source_manifest'].get(key, {}).get('sha256') != hashes[key] for key in needed):
        raise AnalysisError('Observation source provenance differs from the current value path')
    try:
        collected = datetime.fromisoformat(observation['collected_at'].replace('Z', '+00:00'))
        maximum_age = observation['max_age_seconds']
        age = (datetime.now(timezone.utc) - collected).total_seconds()
        if collected.tzinfo is None or type(maximum_age) is not int or maximum_age < 0 or not 0 <= age <= maximum_age:
            raise ValueError('expired/future observation')
    except (KeyError, TypeError, ValueError) as exc:
        raise AnalysisError('Observation is stale or has invalid collection/freshness provenance') from exc
    answer = next((a for a in packet['answers'] if a['decision_id'] == proof['mapping_decision_id']), None)
    if not answer or answer['approval_status'] != 'APPROVED':
        raise AnalysisError('Positive availability needs an approved business mapping decision')
    try:
        decision = json.loads(answer['answer'])
    except ValueError as exc:
        raise AnalysisError('Mapping decision must contain structured JSON') from exc
    requested = {key: item[key] for key in INPUT_METADATA}
    if decision != {'input_id': item['id'], 'entity_id': target, 'metadata': requested}:
        raise AnalysisError('Approved mapping does not match this exact input definition and metadata')
    metadata = observation.get('metadata')
    if not isinstance(metadata, dict) or set(metadata) - set(INPUT_METADATA):
        raise AnalysisError('Observation metadata must use the InputRequirement contract')
    conflicts = [key for key, value in metadata.items() if requested[key] is not None and requested[key] != value]
    if conflicts:
        raise AnalysisError('Observed input metadata is incompatible: ' + ', '.join(conflicts))
    complete = all(requested[key] is not None and metadata.get(key) == requested[key] for key in INPUT_METADATA)
    declared_type = (nodes[target].signature or '').lower().rstrip('?').split(' ')[0]
    canonical_types = {'double': 'number', 'bigdecimal': 'number', 'numeric': 'number', 'decimal': 'number',
                       'float8': 'number', 'number': 'number', 'long': 'integer', 'int': 'integer',
                       'bigint': 'integer', 'integer': 'integer', 'string': 'string', 'text': 'string',
                       'varchar': 'string', 'boolean': 'boolean', 'bool': 'boolean'}
    expected = (requested.get('data_type') or '').lower()
    if declared_type in canonical_types and expected in canonical_types:
        if canonical_types[declared_type] != canonical_types[expected]:
            raise AnalysisError('Input data type conflicts with the parsed source declaration')
    else:
        complete = False
    freshness = requested.get('freshness')
    duration = re.fullmatch(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', freshness or '')
    if duration and any(duration.groups()):
        seconds = sum(int(value or 0) * factor for value, factor in zip(duration.groups(), (3600, 60, 1)))
        if maximum_age > seconds or age > seconds:
            raise AnalysisError('Observation freshness is weaker than the required freshness')
    else:
        complete = False  # unsupported temporal policy cannot be called FIT
    value = observation['value']
    key_values = observation.get('key_values', {})
    if not isinstance(key_values, dict) or not isinstance(requested.get('keys'), list):
        complete = False
    elif any(key not in key_values or key_values[key] is None for key in requested['keys']):
        complete = False
    quality = requested.get('quality')
    if isinstance(quality, list):
        for rule in quality:
            if rule == 'nonnegative' and (type(value) not in {int, float} or value < 0):
                raise AnalysisError('Observed value violates the nonnegative quality requirement')
            if rule == 'positive' and (type(value) not in {int, float} or value <= 0):
                raise AnalysisError('Observed value violates the positive quality requirement')
            if rule == 'nonempty' and (not isinstance(value, str) or not value.strip()):
                raise AnalysisError('Observed value violates the nonempty quality requirement')
            if rule not in {'nonnegative', 'positive', 'nonempty'}:
                complete = False  # no implied proof of arbitrary free-text quality rules
    expected_type = requested.get('data_type')
    compatible_types = {'number': (int, float), 'Double': (int, float), 'BigDecimal': (int, float),
                        'integer': (int,), 'Int': (int,), 'Long': (int,), 'string': (str,),
                        'String': (str,), 'boolean': (bool,), 'Boolean': (bool,)}
    types = compatible_types.get(expected_type)
    if types and type(value) not in types:
        raise AnalysisError('Observed populated value has an incompatible data type')
    if types is None:
        complete = False
    # A single witnessed input cannot prove other dependencies in a calculation.
    if source != target:
        proved_nodes = set(path['entity_ids'])
        if any(e.source in proved_nodes and e.kind in {'reads_value', 'derived_from'} and e.target not in proved_nodes
               for e in graph.edges):
            complete = False
    return {'availability': 'AVAILABLE' if complete else 'PARTIAL',
            'usability': 'FIT' if complete else 'UNASSESSED', 'scope': observation['scope'],
            'provenance': 'SUPPLIED_OBSERVATION_WITH_APPROVED_MAPPING', 'path': path,
            'limitations': ['Scoped observation, not an authenticated deployment proof or global data guarantee.']}
