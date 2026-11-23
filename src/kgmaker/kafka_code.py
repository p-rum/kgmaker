"""Versioned static Kafka code declarations over captured compiler facts only."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import re

from .analysis_model import digest, safe_path
from .compiler_sources import compiler_source_digest
from .model import Edge, KnowledgeGraph, Node

VERSION = 'kafka-code-1'
LISTENER = 'org.springframework.kafka.annotation.KafkaListener'
LISTENERS = 'org.springframework.kafka.annotation.KafkaListeners'
TOPIC = re.compile(r'[A-Za-z0-9._-]{1,249}\Z')
MAX_FACTS = 2048
SEND_OWNERS = {'org.springframework.kafka.core.KafkaTemplate', 'org.springframework.kafka.core.KafkaOperations'}
SEND_DESCRIPTOR = '(Ljava/lang/String;Ljava/lang/Object;)Ljava/util/concurrent/CompletableFuture;'


def declaration_witness(symbol: dict) -> dict:
    return {key: symbol.get(key) for key in
            ('id', 'owner', 'name', 'descriptor', 'kind', 'context_id', 'scope')}


def call_witness(site: dict, target: dict) -> dict:
    return {'site': {key: site.get(key) for key in
            ('id', 'caller', 'declared_target', 'context_id', 'path', 'sha256', 'range',
             'argument_mapping_status', 'invocation_kind', 'evidence_kind')},
            'target': {key: target.get(key) for key in
            ('id', 'owner', 'name', 'descriptor', 'kind', 'context_id', 'origin', 'path')}}


def analysis_stamp(context: dict) -> dict:
    return {'version': VERSION}


def validate_analysis(root: Path, context: dict) -> None:
    from .worker_protocol import WorkerError
    if 'kafka_code_analysis' not in context:
        return
    sources = context.get('kafka_code_source_hashes')
    if context['kafka_code_analysis'] != analysis_stamp(context) or not isinstance(sources, dict) or not sources:
        raise WorkerError('STALE_INDEX: Kafka code analysis changed; inspect again', 'STALE')
    from .scanner import _safe_source
    for path, checksum in sources.items():
        try:
            _, current = _safe_source(safe_path(root, path))
        except (ValueError, OSError, RuntimeError):
            current = None
        if not isinstance(checksum, str) or current != checksum:
            raise WorkerError('STALE_INDEX: Kafka code source changed; inspect again', 'STALE')


def _string(value, limit=4096):
    return isinstance(value, str) and 0 < len(value) <= limit and '\x00' not in value


def _range(value):
    if not isinstance(value, dict):
        return False
    keys = ['start', 'end', 'start_line', 'end_line', 'start_column', 'end_column']
    return (all(type(value.get(k)) is int for k in keys)
            and 0 <= value['start'] < value['end']
            and 1 <= value['start_line'] <= value['end_line']
            and value['start_column'] >= 1 and value['end_column'] >= 1)


def _property(value, context, fingerprint=None):
    """Only the pre-existing captured whole-property resolver may supply a value."""
    if not _string(value) or '[redacted]' in value.lower() or '<redacted>' in value.lower():
        return None, None
    match = re.fullmatch(r'\$\{([A-Za-z0-9_.-]+)\}', value)
    if match:
        from .kafka_bindings import _resolve
        properties = context.get('spring_properties')
        if fingerprint is None or not isinstance(properties, dict):
            return None, None
        resolved = _resolve(match[1], properties)
        return resolved, {'kind': 'CAPTURED_PROPERTY', 'key': match[1],
                          'properties_sha256': fingerprint} if resolved is not None else None
    if '${' in value or '#{' in value:
        return None, None
    return value, {'kind': 'COMPILER_LITERAL'}


class _Capture:
    def __init__(self, root, graph, context):
        self.root, self.graph, self.context = root.resolve(), graph, context
        self.nodes = {n.id: n for n in graph.nodes}
        self.symbols = {s['id']: s for s in graph.symbols if isinstance(s, dict) and _string(s.get('id'))}
        self.proofs = {e['id']: e for e in graph.evidence if isinstance(e, dict) and _string(e.get('id'))}
        captured = [c for c in graph.contexts if c.get('id') == context.get('id')]
        identity_fields = ['id', 'language', 'repo_id', 'module', 'source_set', 'scope', 'mode',
                           'origin_trust', 'freshness', 'analyzer_version', 'source_files', 'worker',
                           'spring_properties', 'spring_profiles', 'classpath', 'compiler_options']
        self.context_valid = (len(captured) == 1
            and context.get('mode') in {'BUILD_IMPORT', 'BUILD_EXECUTE'}
            and context.get('freshness') == 'CONTENT_VERIFIED'
            and context.get('origin_trust') == 'LOCAL_COMPILER_INPUTS'
            and all(_string(context.get(k)) for k in ('repo_id', 'module', 'source_set', 'scope'))
            and _string(context.get('analyzer_version'))
            and all(captured[0].get(k) == context.get(k) for k in identity_fields))
        self.files, self.raw_files = {}, {}
        self.source_bytes = 0
        properties = context.get('spring_properties')
        self.property_fingerprint = (digest(properties) if isinstance(properties, dict) and len(properties) <= 2048
            and all(isinstance(k, str) and isinstance(v, str) for k, v in properties.items())
            and sum(len(k) + len(v) for k, v in properties.items()) <= 1_000_000 else None)
        self.sites = {s['id']: s for s in graph.call_sites if isinstance(s, dict) and _string(s.get('id'))
                      and s.get('context_id') == context.get('id')}
        self.new_nodes, self.new_edges, self.new_evidence, self.diagnostics = [], [], [], []
        self.seen = False
        self.compiler_error = any('.err.' in str(d.get('code', ''))
            or 'ERROR' in str(d.get('code', '')).upper()
            or str(d.get('reason', '')).startswith('ERROR:') for d in graph.diagnostics)

    def issue(self, reason, symbol=None):
        item = {'code': 'KAFKA_CODE_UNPROVEN', 'reason': reason,
                'context_id': self.context.get('id'), 'status': 'UNKNOWN'}
        if symbol:
            item.update(path=symbol.get('path'), origin_id=symbol.get('id'))
        if item not in self.diagnostics:
            self.diagnostics.append(item)

    def source(self, symbol):
        """Canonical node, capture and one bounded byte snapshot must all agree."""
        cid, scope = self.context.get('id'), self.context.get('scope')
        if (not self.context_valid or self.compiler_error or not _string(cid) or scope not in {'production', 'test', 'test_fixture'}
                or self.context.get('language') != 'jvm' or symbol.get('context_id') != cid
                or symbol.get('scope') != scope or symbol.get('kind') != 'method'
                or not all(_string(symbol.get(k)) for k in ['id', 'owner', 'name', 'descriptor', 'path', 'sha256'])
                or not _range(symbol.get('range'))):
            return None
        node = self.nodes.get(symbol['id'])
        if (node is None or node.kind != 'method' or node.scope != scope
                or node.path != symbol['path'] or node.name != symbol['name']
                or node.signature != symbol['descriptor'] or type(node.line) is not int or node.line != symbol['range']['start_line']
                or not isinstance(node.metadata, dict)
                or any(node.metadata.get(k) != symbol.get(k) for k in
                       ['id', 'owner', 'name', 'descriptor', 'kind', 'path', 'range', 'sha256', 'context_id', 'scope', 'annotations'])):
            return None
        path = symbol['path']
        source_nodes = [n for n in self.graph.nodes if n.kind == 'file' and n.path == path]
        if (len(source_nodes) != 1 or source_nodes[0].scope != scope
                or (node.build_membership and self.context['module'] + ':' + self.context['source_set']
                    not in node.build_membership)):
            return None
        contains = [e for e in self.graph.edges if e.source == source_nodes[0].id
                    and e.target == node.id and e.kind == 'contains'
                    and e.evidence_kind == 'SYMBOL_RESOLVED' and e.context_ids == (cid,)
                    and e.source_file == path and type(e.source_line) is int
                    and e.source_line == symbol['range']['start_line']]
        if len(contains) != 1:
            return None
        proofs = [self.proofs.get(identity, {}) for identity in contains[0].evidence_ids]
        annotation_witness = any(isinstance(a, dict) and str(a.get('name', '')).rsplit('.', 1)[-1]
                                 in {'KafkaListener', 'KafkaListeners'} for a in (symbol.get('annotations') if isinstance(symbol.get('annotations'), list) else []))
        if not any(p.get('kind') == 'SYMBOL_RESOLVED' and p.get('relation') == 'contains'
                   and p.get('source') == source_nodes[0].id and p.get('target') == node.id
                   and p.get('context_ids') == [cid] and p.get('source_file') == path
                   and p.get('compiler_declaration') == declaration_witness(symbol)
                   and p.get('compiler_realm') == {k: self.context.get(k)
                        for k in ('repo_id', 'module', 'source_set', 'scope')}
                   and (not annotation_witness or p.get('compiler_annotation_fingerprint') == digest(symbol['annotations']))
                   and p.get('sha256') == symbol['sha256'] and _range(p.get('source_range')) and p.get('source_range') == symbol['range']
                   for p in proofs):
            return None
        if path not in self.files:
            if self.source_bytes >= 32_000_000:
                self.issue('KAFKA_SOURCE_BUDGET'); return None
            from .scanner import _safe_source, _file_digest
            try:
                target = safe_path(self.root, path)
                text, checksum = _safe_source(target)
            except (ValueError, OSError, RuntimeError):
                return None
            if text is not None:
                self.source_bytes += len(text.encode('utf-8'))
                if self.source_bytes > 32_000_000:
                    self.issue('KAFKA_SOURCE_BUDGET'); return None
            self.files[path] = (text, checksum, _file_digest(text) if text is not None else None)
        text, checksum, captured = self.files[path]
        if (text is None or checksum != symbol['sha256']
                or compiler_source_digest(self.graph.files, self.context, path) != checksum
                or self.graph.files.get(path) != captured):
            return None
        return node

    def add(self, kind, symbol, source_node, metadata, *, origin_id=None, location=None, logical_extra=None, compiler_refs=()):
        logical = {'repo_id': self.context.get('repo_id'), 'module': self.context.get('module'),
                   'source_set': self.context.get('source_set'), 'scope': source_node.scope,
                   'owner': symbol['owner'], 'name': symbol['name'], 'descriptor': symbol['descriptor']}
        logical.update(logical_extra or {})
        logical_id = kind + ':' + digest(logical)
        origin_id = origin_id or symbol['id']
        location = dict(location or symbol['range'])
        relation = 'declares_kafka_listener' if kind == 'kafka_code_listener' else 'declares_kafka_send'
        revision = digest({'logical_id': logical_id, 'context_id': self.context['id'],
                           'path': symbol['path'], 'sha256': symbol['sha256'], 'range': location,
                           'version': VERSION, 'facts': metadata})
        identity = logical_id + ':capture:' + revision
        proof = {'kind': 'FRAMEWORK_DERIVED', 'relation': relation,
                 'source': source_node.id, 'target': identity, 'source_file': symbol['path'],
                 'source_range': location, 'sha256': symbol['sha256'],
                 'context_ids': [self.context['id']], 'extractor': VERSION,
                 'origin_id': origin_id, 'compiler_evidence_ids': list(compiler_refs), 'freshness': 'CONTENT_VERIFIED',
                 'execution': 'NOT_OBSERVED'}
        evidence_id = 'evidence:' + digest(proof)
        self.new_nodes.append(Node(identity, kind, symbol['name'], symbol['path'], line=location['start_line'],
            scope=source_node.scope, role='contract', origin='generated',
            build_membership=source_node.build_membership,
            classification_evidence=source_node.classification_evidence,
            metadata={**metadata, 'version': VERSION, 'logical_id': logical_id, 'revision': revision,
                      'origin_id': origin_id, 'context_id': self.context['id'],
                      'source_realm': {k: self.context.get(k)
                          for k in ('repo_id', 'module', 'source_set', 'scope')},
                      'source_file': symbol['path'], 'source_sha256': symbol['sha256'],
                      'source_range': location, 'owner': symbol['owner'],
                      'method_name': symbol['name'], 'descriptor': symbol['descriptor'],
                      'scope': source_node.scope, 'execution': 'NOT_OBSERVED', 'activation': 'UNKNOWN'}))
        self.new_edges.append(Edge(source_node.id, identity, relation,
            'Canonical captured code declaration; runtime execution is not observed',
            evidence_kind='FRAMEWORK_DERIVED', context_ids=(self.context['id'],),
            evidence_ids=(evidence_id,), source_file=symbol['path'], source_line=location['start_line']))
        self.new_evidence.append({'id': evidence_id, **proof})

    def listener(self, symbol):
        annotations = symbol.get('annotations')
        if not isinstance(annotations, list):
            return
        candidates = [a for a in annotations if isinstance(a, dict) and
                      str(a.get('name', '')).rsplit('.', 1)[-1] in {'KafkaListener', 'KafkaListeners'}]
        if not candidates:
            return
        self.seen = True
        source = self.source(symbol)
        if source is None:
            self.issue('LISTENER_SOURCE_CONTEXT_OR_COMPILER_UNPROVEN', symbol); return
        if len(candidates) != 1 or candidates[0].get('name') != LISTENER:
            self.issue('LISTENER_CANONICAL_ANNOTATION_OR_REPEATABLE_UNPROVEN', symbol); return
        if any(s.get('owner') in {LISTENER, LISTENERS} and _string(s.get('path'))
               and s.get('context_id') == self.context['id'] for s in self.symbols.values()):
            self.issue('LISTENER_CANONICAL_ANNOTATION_SHADOWED_BY_SOURCE', symbol); return
        annotation = candidates[0]
        values = annotation.get('values')
        if (not isinstance(values, dict) or annotation.get('values_resolved') is False
                or 'values_resolved' in annotation and type(annotation['values_resolved']) is not bool):
            self.issue('LISTENER_ANNOTATION_VALUES_UNRESOLVED', symbol); return
        reasons, provenance = [], []
        group, origin = _property(values.get('groupId'), self.context, self.property_fingerprint)
        if group is None or not TOPIC.fullmatch(group) or group in {'.', '..'}:
            group = None; reasons.append('EXPLICIT_GROUP_UNPROVEN')
        elif origin:
            provenance.append({'field': 'groupId', **origin})
        raw_id = values.get('id', '')
        annotation_id = None
        if not isinstance(raw_id, str):
            reasons.append('LISTENER_ID_SHAPE_UNSUPPORTED')
        elif raw_id:
            annotation_id, origin = _property(raw_id, self.context, self.property_fingerprint)
            if not _string(annotation_id, 512):
                annotation_id = None; reasons.append('LISTENER_ID_UNRESOLVED')
        raw_topics, raw_pattern = values.get('topics', []), values.get('topicPattern', '')
        topics, pattern, selector = [], None, 'UNKNOWN'
        if not isinstance(raw_topics, list) or len(raw_topics) > 64 or not isinstance(raw_pattern, str):
            reasons.append('SUBSCRIPTION_SHAPE_UNSUPPORTED')
        elif raw_topics and raw_pattern:
            reasons.append('SUBSCRIPTION_SELECTOR_CONFLICT')
        elif raw_pattern:
            pattern, origin = _property(raw_pattern, self.context, self.property_fingerprint)
            if not _string(pattern, 2048):
                pattern = None; reasons.append('REGEX_SELECTOR_UNRESOLVED')
            else:
                selector = 'REGEX'
                provenance.append({'field': 'topicPattern', **origin})
        elif raw_topics:
            for raw in raw_topics:
                value, origin = _property(raw, self.context, self.property_fingerprint)
                if value is None or not TOPIC.fullmatch(value) or value in {'.', '..'}:
                    reasons.append('TOPIC_UNRESOLVED'); topics = []; break
                topics.append(value); provenance.append({'field': 'topics', **origin})
            if topics:
                selector = 'TOPICS'
        else:
            reasons.append('SUBSCRIPTION_SELECTOR_UNAVAILABLE')
        if (not isinstance(values.get('topicPartitions', []), list)
                or not isinstance(values.get('properties', []), list)
                or not isinstance(values.get('containerFactory', ''), str)
                or values.get('topicPartitions') or values.get('containerFactory') or values.get('properties')):
            reasons.append('LISTENER_CONTAINER_OR_PROPERTY_OVERRIDE_UNSUPPORTED')
        file_node = next(n for n in self.graph.nodes if n.kind == 'file' and n.path == symbol['path'])
        compiler_refs = self.compiler_refs(file_node.id, symbol['id'], 'contains', symbol, symbol['range'])
        self.add('kafka_code_listener', symbol, source,
            {'annotation': LISTENER, 'annotation_id': annotation_id, 'group_id': group,
             'subscription_kind': selector, 'topics': topics, 'topic_pattern': pattern,
             'status': 'UNKNOWN' if reasons else 'REGEX_CANDIDATE' if selector == 'REGEX' else 'DECLARED',
             'reasons': sorted(set(reasons)), 'property_provenance': provenance,
             'broker_realm': None, 'code_origin': 'COMPILER_ANNOTATION'}, compiler_refs=compiler_refs)

    def compiler_refs(self, source, target, relation, symbol, location, extra=None):
        cid = self.context['id']
        references = []
        for edge in self.graph.edges:
            if (edge.source != source or edge.target != target or edge.kind != relation
                    or edge.evidence_kind != 'SYMBOL_RESOLVED' or edge.context_ids != (cid,)
                    or edge.source_file != symbol['path'] or type(edge.source_line) is not int or edge.source_line != location['start_line']):
                continue
            for identity in edge.evidence_ids:
                proof = self.proofs.get(identity, {})
                if (proof.get('kind') == 'SYMBOL_RESOLVED' and proof.get('relation') == relation
                        and proof.get('source') == source and proof.get('target') == target
                        and proof.get('context_ids') == [cid] and proof.get('source_file') == symbol['path']
                        and _range(proof.get('source_range')) and proof.get('source_range') == location and proof.get('sha256') == symbol['sha256']
                        and all(type(proof.get(k)) is type(value) and proof.get(k) == value for k, value in (extra or {}).items())):
                    references.append(identity)
        return sorted(set(references))

    def token(self, symbol, where):
        if not _range(where):
            return None
        path = symbol['path']
        if path not in self.raw_files:
            from .scanner import MAX_FILE_BYTES
            import hashlib
            try:
                with safe_path(self.root, path).open('rb') as stream:
                    raw = stream.read(MAX_FILE_BYTES + 1)
                if len(raw) > MAX_FILE_BYTES or hashlib.sha256(raw).hexdigest() != symbol['sha256']:
                    return None
                self.raw_files[path] = raw.decode('utf-8').encode('utf-16-le')
            except (ValueError, OSError, RuntimeError, UnicodeError):
                return None
        raw = self.raw_files[path]
        if where['end'] * 2 > len(raw):
            return None
        try:
            return raw[where['start'] * 2:where['end'] * 2].decode('utf-16-le')
        except UnicodeError:
            return None

    def send(self, site, record, call):
        self.seen = True
        symbol = self.symbols.get(site.get('caller'), {})
        source = self.source(symbol)
        target = self.symbols.get(site.get('declared_target'), {})
        target_node = self.nodes.get(target.get('id'))
        location = site.get('range')
        if (source is None or not _range(location) or site.get('context_id') != self.context['id']
                or site.get('path') != symbol['path'] or site.get('sha256') != symbol['sha256']
                or site.get('evidence_kind') != 'SYMBOL_RESOLVED' or site.get('invocation_kind') == 'METHOD_REFERENCE'
                or target.get('origin') != 'dependency' or target.get('path') is not None
                or target.get('kind') != 'method' or target.get('context_id') != self.context['id']
                or target.get('owner') not in SEND_OWNERS or target.get('name') != 'send'
                or target.get('descriptor') != SEND_DESCRIPTOR or target_node is None
                or target_node.kind != 'method' or target_node.origin != 'dependency'
                or target_node.signature != SEND_DESCRIPTOR or not isinstance(target_node.metadata, dict)
                or any(target_node.metadata.get(k) != target.get(k) for k in ['id', 'owner', 'name', 'descriptor', 'context_id', 'origin', 'path'])):
            self.issue('SEND_API_SOURCE_OR_CONTEXT_UNPROVEN', site); return
        if not symbol['path'].endswith('.java') or record.get('language') != 'java':
            self.issue('KOTLIN_SEND_BODY_UNSUPPORTED', site); return
        body = record.get('body')
        if (record.get('method') != symbol['id'] or record.get('context_id') != self.context['id']
                or not isinstance(body, dict) or not _range(body.get('range'))
                or body.get('path') != symbol['path'] or body.get('sha256') != symbol['sha256']
                or not symbol['range']['start'] <= body['range']['start'] <= location['start'] < location['end'] <= body['range']['end'] <= symbol['range']['end']
                or call.get('kind') != 'call' or call.get('call_site') != site['id']
                or not _range(call.get('range')) or call.get('range') != location or call.get('path') != symbol['path']
                or call.get('sha256') != symbol['sha256']):
            self.issue('SEND_BODY_OWNERSHIP_UNPROVEN', site); return
        call_node = self.nodes.get(site['id'])
        if (call_node is None or call_node.kind != 'call_site' or call_node.scope != source.scope
                or call_node.path != symbol['path'] or type(call_node.line) is not int or call_node.line != location['start_line']):
            self.issue('SEND_CANONICAL_CALL_UNPROVEN', site); return
        call_refs = self.compiler_refs(source.id, site['id'], 'declares_call', symbol, location,
                                       {'compiler_call': call_witness(site, target)})
        arguments = call.get('arguments')
        if (not call_refs or site.get('argument_mapping_status') != 'PROVEN'
                or not isinstance(arguments, list) or len(arguments) != 2 or not isinstance(arguments[0], dict)):
            self.issue('SEND_ARGUMENT_MAPPING_UNPROVEN', site); return
        argument = arguments[0]
        literal = argument.get('literal')
        topic = literal.get('value') if isinstance(literal, dict) else None
        if (not isinstance(literal, dict) or literal.get('type') != 'STRING_LITERAL'
                or literal.get('source') != 'COMPILER_LITERAL' or not isinstance(topic, str)
                or not TOPIC.fullmatch(topic) or topic in {'.', '..'}
                or argument.get('path') != symbol['path'] or argument.get('sha256') != symbol['sha256']
                or not _range(argument.get('range'))
                or not location['start'] <= argument['range']['start'] < argument['range']['end'] <= location['end']
                or self.token(symbol, argument['range']) != '"' + topic + '"'):
            self.issue('SEND_LITERAL_TOPIC_UNPROVEN', site); return
        argument_id, parameter_id = site['id'] + ':argument:0', target['id'] + ':parameter:0'
        captured = self.symbols.get(argument_id, {})
        formal = self.symbols.get(parameter_id, {})
        captured_node, formal_node = self.nodes.get(argument_id), self.nodes.get(parameter_id)
        if (captured.get('kind') != 'value' or captured.get('call_site') != site['id']
                or captured.get('owner_method') != symbol['id'] or captured.get('context_id') != self.context['id']
                or captured.get('path') != symbol['path'] or captured.get('sha256') != symbol['sha256']
                or captured.get('range') != argument['range'] or captured.get('scope') != source.scope
                or formal.get('kind') != 'parameter' or formal.get('method') != target['id']
                or type(formal.get('parameter_index')) is not int or formal['parameter_index'] != 0
                or formal.get('context_id') != self.context['id']
                or captured_node is None or captured_node.kind != 'value' or captured_node.scope != source.scope
                or captured_node.path != symbol['path'] or type(captured_node.line) is not int
                or captured_node.line != argument['range']['start_line'] or captured_node.name != captured.get('name')
                or not isinstance(captured_node.metadata, dict)
                or any(captured_node.metadata.get(k) != captured.get(k) for k in ['id', 'path', 'sha256', 'range', 'context_id', 'call_site', 'owner_method'])
                or formal_node is None or formal_node.kind != 'parameter' or formal_node.name != formal.get('name') or not isinstance(formal_node.metadata, dict)
                or any(formal_node.metadata.get(k) != formal.get(k) for k in ['id', 'method', 'parameter_index', 'context_id'])):
            self.issue('SEND_FORMAL_ARGUMENT_OWNERSHIP_UNPROVEN', site); return
        refs = self.compiler_refs(argument_id, parameter_id, 'argument_to_parameter', symbol, argument['range'],
            {'argument_mapping_version': 1, 'call_site': site['id'], 'argument_index': 0, 'parameter_index': 0,
             'transformation': 'DIRECT', 'binding_kind': 'DECLARED_PARAMETER'})
        if not refs:
            self.issue('SEND_ARGUMENT_EVIDENCE_UNPROVEN', site); return
        siblings = sorted((s for s in self.sites.values() if s.get('caller') == symbol['id']
            and s.get('path') == symbol['path'] and _range(s.get('range'))
            and self.symbols.get(s.get('declared_target'), {}).get('owner') in SEND_OWNERS
            and self.symbols.get(s.get('declared_target'), {}).get('name') == 'send'),
            key=lambda s: (s['range']['start'], s['range']['end'], s['id']))
        slot = next((index for index, s in enumerate(siblings) if s['id'] == site['id']), None)
        if slot is None:
            self.issue('SEND_LOGICAL_ORIGIN_UNPROVEN', site); return
        self.add('kafka_code_producer', symbol, call_node,
            {'status': 'DECLARED', 'reasons': [], 'topic': topic, 'topics': [topic],
             'subscription_kind': 'TOPICS', 'topic_pattern': None, 'group_id': None,
             'call_site': site['id'], 'caller': symbol['id'], 'declared_target': target['id'],
             'argument_id': argument_id, 'parameter_id': parameter_id, 'topic_range': argument['range'],
             'api_owner': target['owner'], 'api_descriptor': target['descriptor'],
             'broker_realm': None, 'code_origin': 'JAVAC_API_CONTRACT', 'call_slot': slot},
            origin_id=site['id'], location=location,
            logical_extra={'call_slot': slot, 'api_owner': target['owner'], 'api_descriptor': target['descriptor']},
            compiler_refs=[*call_refs, *refs])

    def producers(self, bodies):
        calls = {}
        steps = 0
        for record in bodies:
            if not isinstance(record, dict) or record.get('context_id') != self.context.get('id'):
                continue
            stack, seen = [(record.get('body'), 0)], set()
            while stack:
                node, depth = stack.pop()
                if not isinstance(node, (dict, list)):
                    continue
                if id(node) in seen or depth > 128 or steps >= 50000:
                    self.issue('KAFKA_BODY_BUDGET_OR_CYCLE'); break
                seen.add(id(node)); steps += 1
                if isinstance(node, dict):
                    if node.get('kind') == 'call' and isinstance(node.get('call_site'), str):
                        calls.setdefault(node['call_site'], []).append((record, node))
                    stack.extend((value, depth + 1) for value in node.values() if isinstance(value, (dict, list)))
                else:
                    stack.extend((value, depth + 1) for value in node if isinstance(value, (dict, list)))
        for site in self.sites.values():
            target = self.symbols.get(site.get('declared_target'), {})
            if target.get('owner') not in SEND_OWNERS or target.get('name') != 'send':
                continue
            self.seen = True
            frames = calls.get(site['id'], [])
            if len(frames) != 1:
                self.issue('SEND_UNIQUE_BODY_UNAVAILABLE', site); continue
            if len(self.new_nodes) >= MAX_FACTS:
                self.issue('KAFKA_CODE_FACT_BUDGET'); break
            self.send(site, *frames[0])

    def finish(self, bodies):
        for symbol in self.graph.symbols:
            if isinstance(symbol, dict) and symbol.get('context_id') == self.context.get('id') and symbol.get('kind') == 'method':
                if len(self.new_nodes) >= MAX_FACTS:
                    self.issue('KAFKA_CODE_FACT_BUDGET'); break
                self.listener(symbol)
        self.producers(bodies)
        if not self.seen:
            return self.graph
        contexts = [{**c, 'kafka_code_analysis': analysis_stamp(c),
                     'kafka_code_source_hashes': {p: item[1] for p, item in self.files.items() if item[1]}}
                    if c.get('id') == self.context.get('id') else c
                    for c in self.graph.contexts] if self.files else self.graph.contexts
        result = replace(self.graph, nodes=[*self.graph.nodes, *self.new_nodes],
            edges=[*self.graph.edges, *self.new_edges], evidence=[*self.graph.evidence, *self.new_evidence],
            contexts=contexts, diagnostics=[*self.graph.diagnostics, *self.diagnostics])
        KnowledgeGraph.from_dict(result.to_dict())
        return result


def augment_kafka_graph(root: Path, graph: KnowledgeGraph, bodies: list[dict], context: dict) -> KnowledgeGraph:
    """Attach exact captured code declarations; this never executes application code."""
    KnowledgeGraph.from_dict(graph.to_dict())
    if not isinstance(context, dict) or not isinstance(bodies, list):
        raise ValueError('Kafka capture needs a selected context and a body list')
    return _Capture(root, graph, context).finish(bodies)


def validate_code_fact(root: Path, graph: KnowledgeGraph, context: dict, fact: Node) -> bool:
    """Revalidate a private captured fact against canonical source/compiler evidence."""
    metadata = fact.metadata
    if (not isinstance(context, dict) or not _string(context.get('id'))
            or fact.kind not in {'kafka_code_listener', 'kafka_code_producer'}
            or not isinstance(metadata, dict) or metadata.get('version') != VERSION
            or metadata.get('context_id') != context['id'] or not _string(metadata.get('origin_id'))
            or 'kafka_code_analysis' not in context):
        return False
    try:
        from .graph_provider import validate_context_snapshot
        validate_context_snapshot(root, context)
        capture = _Capture(root, graph, context)
        if fact.kind == 'kafka_code_listener':
            capture.listener(capture.symbols.get(metadata['origin_id'], {}))
        else:
            site = capture.sites.get(metadata['origin_id'], {})
            symbol = capture.symbols.get(site.get('caller'), {})
            argument = capture.symbols.get(site.get('id', '') + ':argument:0', {})
            if not site or not symbol or not argument:
                return False
            call = {'kind': 'call', 'call_site': site['id'], 'range': site.get('range'),
                    'path': site.get('path'), 'sha256': site.get('sha256'),
                    'arguments': [{'kind': 'statement', 'range': argument.get('range'),
                                   'path': argument.get('path'), 'sha256': argument.get('sha256'),
                                   'literal': {'type': 'STRING_LITERAL', 'source': 'COMPILER_LITERAL',
                                               'value': metadata.get('topic')}}, {}]}
            record = {'method': symbol['id'], 'context_id': context['id'], 'language': 'java',
                      'body': {'path': symbol.get('path'), 'sha256': symbol.get('sha256'),
                               'range': symbol.get('range')}}
            capture.send(site, record, call)
        expected = next((node for node in capture.new_nodes if node.id == fact.id), None)
        if expected is None or expected != fact:
            return False
        if not all(edge in graph.edges for edge in capture.new_edges):
            return False
        return all(capture.proofs.get(proof['id']) == proof for proof in capture.new_evidence)
    except (ValueError, OSError, RuntimeError):
        return False
