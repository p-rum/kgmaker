"""Bounded diagrams and reports of a supplied ProcessView."""
from collections import defaultdict
from hashlib import sha256
import json
import re

from .analysis_model import canonical, digest
from .architecture_cli import _safe_output
from .architecture_render import _MAX_OUTPUT_BYTES, _mermaid_json, _mermaid_text, _text
from .architecture_render_common import InterfaceMarkdownError, _bounded
from .process_model import ProcessView, validate_process_view
from .process_store import read_process_reviews
from .view_explanation import _path as _source_path, _range as _source_range
from .workspace import split_id


_MERMAID_MAX_EDGES = 500
_MERMAID_MAX_TEXT_UNITS = 50_000


class ProcessMermaidError(ValueError):
    def __init__(self, code='INVALID_PROCESS_MERMAID'):
        self.code = code
        super().__init__(code)


class ProcessMarkdownError(ValueError):
    def __init__(self, code='INVALID_PROCESS_MARKDOWN'):
        self.code = code
        super().__init__(code)


def _diagram_id(prefix, identity):
    return prefix + sha256(identity.encode('utf-8')).hexdigest()


def _label(item, *parts, approved_label=None):
    attrs = item['attributes']
    details = [attrs.get(key) for key in ('condition', 'boundary_reason', 'async_role',
                                         'failure_role', 'failure_transition', 'execution', 'delivery')]
    if attrs.get('loop_back') is True:
        details.append('loop back')
    label_parts = [
        *parts, *(value for value in details if isinstance(value, str) and value),
        item['resolution_status'], item['freshness'],
    ]
    if approved_label is not None:
        label_parts.append(approved_label)
    return _mermaid_text(' · '.join(label_parts))


def _normalized(view):
    if type(view) is not ProcessView:
        raise ProcessMermaidError()
    try:
        _bounded(vars(view))
        document = view.to_dict(include_generation_metadata=False)
        validate_process_view(document)
    except InterfaceMarkdownError as error:
        code = 'PROCESS_MERMAID_LIMIT' if error.code == 'INTERFACE_MARKDOWN_LIMIT' else 'INVALID_PROCESS_MERMAID'
        raise ProcessMermaidError(code) from None
    except (ValueError, KeyError, TypeError, AttributeError, RecursionError, OverflowError):
        raise ProcessMermaidError() from None
    return document


def render_process_mermaid(view: ProcessView) -> str:
    """Render technical occurrences; comments map the diagram back to the supplied view."""
    return _render(_normalized(view), {})


def render_reviewed_process_mermaid(root, view: ProcessView, *, documents=(), conflicts=()) -> str:
    """Add labels from effective, locally declared approval of these explicit inputs."""
    document = _normalized(view)
    review = read_process_reviews(root, document, documents=documents, conflicts=conflicts)
    status = review['effective_status']
    if status != 'APPROVED':
        raise ProcessMermaidError(f'PROCESS_MERMAID_REVIEW_{status}')
    labels = {row['target_id']: row['label'] for row in review['active_annotations'] if 'label' in row}
    return _render(document, labels)


def _render(document, labels):
    technical = document['technical_view']
    metadata = {field: document[field] for field in ('schema_version', 'process_id', 'revision',
        'technical_status', 'entry_ids', 'exit_ids', 'outcome_ids')}
    metadata['context_ids'] = document['definition']['context_ids']
    metadata['technical_view'] = {key: value for key, value in technical.items() if key not in {'nodes', 'edges'}}
    try:
        _safe_output({'metadata': metadata, 'nodes': technical['nodes'], 'edges': technical['edges'],
                      'approved_labels': list(labels.values())})
    except ValueError:
        raise ProcessMermaidError('UNSAFE_PROCESS_MERMAID') from None
    if len(technical['edges']) > _MERMAID_MAX_EDGES:
        raise ProcessMermaidError('PROCESS_MERMAID_LIMIT')

    scope = _mermaid_text(technical['scope'])
    title = f"Technical process | Scope: {scope} | Coverage: {document['technical_status']}"
    if technical['coverage'].get('truncated') is True:
        title += ' | TRUNCATED'
    if document['process_id'] in labels:
        title += ' | ' + _mermaid_text(labels[document['process_id']])
    header = ['---', 'title: ' + json.dumps(title), '---']
    lines = ['flowchart LR', '  %% process-meta ' + _mermaid_json(metadata)]
    node_ids = {}
    lanes = defaultdict(list)
    for node in technical['nodes']:
        identity = node_ids[node['id']] = _diagram_id('n', node['id'])
        owner = node['owner_id']
        lane = owner if owner and owner.startswith('service:') and owner.removeprefix('service:') else None
        label = _label(node, node['kind'], node['label'], approved_label=labels.get(node['id']))
        if node['kind'] in {'decision', 'condition', 'loop_header'}:
            declaration = f'{identity}{{"{label}"}}'
        else:
            declaration = f'{identity}["{label}"]'
        lanes[lane].append(declaration)
        lines.append('  %% process-node ' + _mermaid_json({'diagram_id': identity, 'node': node}))

    lines.extend(f'  {declaration}' for declaration in lanes.pop(None, []))
    for owner, declarations in sorted(lanes.items()):
        identity = _diagram_id('s', owner)
        lines.append('  %% process-lane ' + _mermaid_json({'diagram_id': identity, 'owner_id': owner}))
        lines.append(f'  subgraph {identity}["{_mermaid_text(owner)}"]')
        lines.extend(f'    {declaration}' for declaration in declarations)
        lines.append('  end')

    for index, edge in enumerate(technical['edges']):
        lines.append('  %% process-edge ' + _mermaid_json({
            'diagram_id': _diagram_id('e', edge['id']), 'index': index, 'edge': edge,
        }))
        arrow = '-.->' if edge['relation'] == 'async' else '-->'
        label = _label(edge, edge['relation'], approved_label=labels.get(edge['id']))
        lines.append(f'  {node_ids[edge["source"]]} {arrow}|"{label}"| {node_ids[edge["target"]]}')

    # Mermaid 11.4.1 strips the header and metadata comments before counting
    # the flowchart's JavaScript string length in UTF-16 code units.
    text_units = sum(len(line.encode('utf-16-le')) // 2 + 1 for line in lines
                     if not line.startswith('  %% process-'))
    if text_units > _MERMAID_MAX_TEXT_UNITS:
        raise ProcessMermaidError('PROCESS_MERMAID_LIMIT')
    result = '\n'.join([*header, *lines]) + '\n'
    if len(result.encode('utf-8')) > _MAX_OUTPUT_BYTES:
        raise ProcessMermaidError('PROCESS_MERMAID_LIMIT')
    return result


def render_process_markdown(view: ProcessView) -> str:
    """Render technical evidence and the matching Mermaid diagram without source reads."""
    try:
        document = _normalized(view)
        return _markdown(document, _render(document, {}))
    except ProcessMermaidError as error:
        raise ProcessMarkdownError(error.code.replace('MERMAID', 'MARKDOWN')) from None
    except ProcessMarkdownError:
        raise
    except (ValueError, KeyError, TypeError, AttributeError, RecursionError, OverflowError):
        raise ProcessMarkdownError() from None


def _captured_locator(proof):
    source = proof.get('source_id')
    checksum = proof.get('content_hash')
    if (not isinstance(source, str) or not isinstance(checksum, str)
            or not re.fullmatch('[0-9a-f]{64}', checksum) or not proof['context_ids']):
        return 'SOURCE_LOCATOR_UNAVAILABLE'
    path = proof.get('source_file')
    try:
        repository, _ = split_id(source)
        _source_path(path, repository)
    except ValueError:
        return 'SOURCE_LOCATOR_UNAVAILABLE'
    locator = {'path': path, 'content_hash': checksum}
    span, _ = _source_range(proof.get('source_range'))
    if span is not None:
        locator['range'] = span
    elif type(proof.get('source_line')) is int and proof['source_line'] > 0:
        locator['line'] = proof['source_line']
    return locator


def _identity_text(value):
    # A visible JSON spelling also distinguishes spaces from literal escapes.
    if value is not None:
        return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':')).replace(' ', r'\u0020')


def _markdown(document, diagram):
    lines = []
    size = 0

    def add(line=''):
        nonlocal size
        size += len(line.encode('utf-8')) + 1
        if size > _MAX_OUTPUT_BYTES:
            raise ProcessMarkdownError('PROCESS_MARKDOWN_LIMIT')
        lines.append(line)

    def table(headers, rows):
        add('| ' + ' | '.join(headers) + ' |')
        add('| ' + ' | '.join('---' for _ in headers) + ' |')
        for row in rows:
            cells = (_text(canonical(value) if isinstance(value, (list, dict)) else value) for value in row)
            add('| ' + ' | '.join(cells) + ' |')
        add()

    def occurrence(item):
        attrs = item['attributes']
        truncated = attrs.get('truncated')
        return (_identity_text(attrs['context_ids']), item['resolution_status'], item['freshness'],
                attrs.get('boundary_reason'), truncated if type(truncated) is bool else None, _identity_text(item['original_ids']),
                item['evidence_kinds'], _identity_text(item['evidence_refs']))

    definition, technical = document['definition'], document['technical_view']
    add('# Technical process report\n')
    add('## Snapshot\n')
    table(('Snapshot', 'Captured value'), (
        ('Process ID', _identity_text(document['process_id'])), ('Revision', document['revision']),
        ('Content fingerprint', digest(document)), ('Baseline fingerprint', _identity_text(definition['baseline_fingerprint'])),
        ('Scope', _identity_text(technical['scope'])), ('Selected context IDs', _identity_text(definition['context_ids'])),
        ('Context selection', _identity_text(technical['context_selection'])),
        ('Technical coverage', document['technical_status']),
        ('Purpose', 'UNKNOWN'), ('Source observation', 'NOT_CHECKED'), ('Runtime execution', 'NOT_CHECKED'),
        ('Data availability', 'UNKNOWN'),
    ))
    add('## Triggers and outcomes\n')
    table(('Role', 'IDs'), (
        ('Triggers', _identity_text(definition['trigger_ids'])), ('Entries', _identity_text(document['entry_ids'])),
        ('Exits', _identity_text(document['exit_ids'])), ('Outcomes', _identity_text(document['outcome_ids'])),
    ))

    columns = ('Contexts', 'Resolution', 'Freshness', 'Boundary reason', 'Truncated',
               'Original IDs', 'Evidence kinds', 'Evidence refs')
    add('## Steps\n')
    table(('Step ID', 'Kind', 'Technical label', 'Owner', *columns),
          ((_identity_text(node['id']), node['kind'], node['label'], _identity_text(node['owner_id']), *occurrence(node))
           for node in technical['nodes']))
    add('## Transitions\n')
    table(('Transition ID', 'Source', 'Target', 'Relation', 'Condition', *columns),
          ((_identity_text(edge['id']), _identity_text(edge['source']), _identity_text(edge['target']), edge['relation'],
            edge['attributes'].get('condition'), *occurrence(edge)) for edge in technical['edges']))

    add('## Diagram\n')
    longest_run = max((len(run[0]) for run in re.finditer(r'`+', diagram)), default=0)
    fence = '`' * max(3, longest_run + 1)
    add(fence + 'mermaid')
    add(diagram.removesuffix('\n'))
    add(fence)
    add()

    add('## Uncertainty\n')
    table(('Coverage field', 'Value'), sorted(technical['coverage'].items()))
    table(('Diagnostic',), ((item,) for item in technical['diagnostics']))
    table(('Captured limitation',), ((limit,) for limit in technical['limits']))
    add('## Provenance\n')
    refs = {ref for item in (*technical['nodes'], *technical['edges']) for ref in item['evidence_refs']}
    table(('Evidence ID', 'Kind', 'Freshness', 'Polarity', 'Contexts', 'Source ID', 'Captured locator'),
          ((_identity_text(proof['id']), proof['evidence_kind'], proof['freshness'], proof['polarity'],
            _identity_text(proof['context_ids']), _identity_text(proof.get('source_id')), _captured_locator(proof))
           for proof in technical['provenance'] if proof['id'] in refs))
    return '\n'.join(lines) + '\n'
