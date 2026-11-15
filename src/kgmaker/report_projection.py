"""Read-only feature report projection; declarations never become availability proof.

This is a view of a validated FeatureAnalysis, not another analysis/store schema.
All associations retain existing IDs. Caller supplies historical freshness.
"""
from __future__ import annotations

from copy import deepcopy

VERSION = 1
FACETS = ('Required', 'Existing', 'Missing', 'Derived', 'External', 'Unresolved')


def report_projection(candidate: dict, packet: dict, stale: list[str], *, data_audit: dict | None = None) -> dict:
    evidence = {e['id']: e for e in candidate['evidence']}
    inventory = packet.get('evidence_inventory', [])
    def cited_source(identity, evidence_ids):
        for eid in evidence_ids:
            e = evidence.get(eid, {})
            if (e.get('source_id') != identity or e.get('validity') != 'VALID'
                    or e.get('method') != 'EXTRACTED'
                    or e.get('kind') not in {'CODE', 'CONTRACT', 'SCHEMA', 'CONFIG', 'WORKBOOK'}):
                continue
            if any(source['graph_id'] == identity and all(source.get(key) == e.get(key)
                   for key in ('path', 'repo_id', 'sha256')) for source in inventory):
                return True
        return False
    inputs = []
    for item in candidate['input_requirements']:
        reasons = []
        if stale:
            reasons.append('STALE_EVIDENCE')
        availability = 'UNKNOWN' if stale else item['availability']
        if availability in {'UNKNOWN', 'PARTIAL', 'NOT_FOUND_IN_SCOPE'}:
            reasons.append('AVAILABILITY_' + availability)
        if item['acquisition'] in {'UNRESOLVED', 'PROPOSED'}:
            reasons.append('ACQUISITION_' + item['acquisition'])
        if item['usability'] != 'FIT':
            reasons.append('USABILITY_' + item['usability'])
        current_sources = [identity for identity in item['source_ids']
                           if not stale and cited_source(identity, item['evidence_ids'])]
        if item['acquisition'] == 'EXISTING' and not current_sources:
            reasons.append('EXISTING_SOURCE_UNVERIFIED')
        flags = {'Required': bool(item['requirement_ids']), 'Existing': bool(current_sources),
                 'Missing': availability == 'CONFIRMED_MISSING',
                 'Derived': item['acquisition'] == 'DERIVED',
                 'External': item['acquisition'] in {'EXTERNAL', 'USER_SUPPLIED'},
                 'Unresolved': bool(reasons)}
        inputs.append({**deepcopy(item), 'availability': availability,
                       'historical_availability': item['availability'] if stale else None,
                       'facets': [name for name in FACETS if flags[name]],
                       'current_source_ids': current_sources, 'unresolved_reasons': reasons,
                       'validity': 'STALE' if stale else 'CURRENT_PACKET',
                       'acquisition_authority': 'DECLARED', 'runtime_status': 'UNKNOWN'})
    blockers = []
    answers = packet.get('answers', [])
    for q in candidate['questions']:
        approved = q['status'] == 'ANSWERED' and any(a['question_id'] == q['id'] and
                    a['approval_status'] == 'APPROVED' for a in answers)
        if q['blocking'] and (stale or not approved):
            blockers.append({'origin': 'QUESTION', 'kind': q.get('blocker_kind', 'UNCLASSIFIED'),
                             'question_id': q['id'], 'requirement_ids': q['requirement_ids'],
                             'reason': q['text'], 'owner_role': q['owner_role'],
                             'authority': 'DECLARED', 'status': 'STALE' if stale else 'OPEN'})
    coverage = candidate['coverage']
    gaps = deepcopy(data_audit.get('coverage_gaps', [])) if data_audit is not None else []
    for key in ('limitations', 'omitted_sources', 'unsupported_sources', 'pending',
                'artifact_diagnostics', 'dataflow_diagnostics', 'documentation_conflicts'):
        for value in coverage.get(key, []):
            gaps.append({'kind': key, 'reason': deepcopy(value)})
    blockers.extend({'origin': 'COVERAGE', 'kind': 'TOOL', 'authority': 'PACKET_COVERAGE',
                     'status': 'STALE' if stale else 'UNRESOLVED', 'coverage_gap': g} for g in gaps)
    delivery = []
    for requirement in candidate['requirements']:
        identity = requirement['id']
        linked = {key: [item['id'] for item in candidate[collection] if identity in item['requirement_ids']]
                  for key, collection in (('input_ids', 'input_requirements'), ('question_ids', 'questions'),
                       ('change_ids', 'changes'), ('acceptance_ids', 'acceptance_criteria'), ('test_ids', 'test_plan'))}
        missing = (['REQUIREMENT_UNRESOLVED'] if requirement['status'] != 'ADDRESSED' else [])
        if not linked['acceptance_ids']:
            missing.append('ACCEPTANCE_MISSING')
        if not linked['test_ids']:
            missing.append('TEST_PLAN_MISSING')
        delivery.append({'requirement_id': identity, **linked, 'gaps': missing,
                         'association': 'DECLARED_REQUIREMENT_IDS', 'execution_status': 'NOT_RUN'})
    partial = (candidate['completion']['processing_status'] != 'COMPLETE' or blockers or
               any(i['unresolved_reasons'] for i in inputs) or any(d['gaps'] for d in delivery))
    return {'schema_version': VERSION, 'analysis_id': candidate['analysis_id'],
            'packet_id': candidate['packet_id'], 'revision': candidate['revision'],
            'status': 'STALE' if stale else 'PARTIAL' if partial else 'VERIFIED_IN_SCOPE',
            'graph_selection': deepcopy(packet.get('graph_selection')),
            'baseline': deepcopy(candidate['baseline']), 'stale': list(stale),
            'facet_order': list(FACETS), 'inputs': inputs, 'blockers': blockers, 'delivery_plan': delivery,
            'impact_paths': deepcopy(candidate['impact_paths']),
            'evidence': [{**deepcopy(e), 'effective_validity': 'STALE' if stale else e['validity']}
                         for e in candidate['evidence']],
            'limitations': ['Facets overlap; acquisition and questions are declarations, not availability proof.',
                'Existing means a cited source, not a populated value. Missing is current scoped CONFIRMED_MISSING only.',
                'Delivery links share explicit requirement IDs; they do not prove implementation, test execution or runtime flow.',
                'Impact paths retain their evidence layers; disconnected branches are not joined.']}
