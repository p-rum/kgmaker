"""Bounded Mermaid rendering of an explicitly supplied technical ProcessView."""
from collections import defaultdict
from hashlib import sha256
import json

from .architecture_cli import _safe_output
from .architecture_render import _MAX_OUTPUT_BYTES, _mermaid_json, _mermaid_text
from .architecture_render_common import InterfaceMarkdownError, _bounded
from .process_model import ProcessView, validate_process_view


_MERMAID_MAX_EDGES = 500
_MERMAID_MAX_TEXT_UNITS = 50_000


class ProcessMermaidError(ValueError):
    def __init__(self, code='INVALID_PROCESS_MERMAID'):
        self.code = code
        super().__init__(code)


def _diagram_id(prefix, identity):
    return prefix + sha256(identity.encode('utf-8')).hexdigest()


def _label(item, *parts):
    attrs = item['attributes']
    details = [attrs.get(key) for key in ('condition', 'boundary_reason', 'async_role',
                                         'failure_role', 'failure_transition', 'execution', 'delivery')]
    if attrs.get('loop_back') is True:
        details.append('loop back')
    return _mermaid_text(' · '.join([
        *parts, *(value for value in details if isinstance(value, str) and value),
        item['resolution_status'], item['freshness'],
    ]))


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
    document = _normalized(view)
    technical = document['technical_view']
    metadata = {field: document[field] for field in ('schema_version', 'process_id', 'revision',
        'technical_status', 'entry_ids', 'exit_ids', 'outcome_ids')}
    metadata['context_ids'] = document['definition']['context_ids']
    metadata['technical_view'] = {key: value for key, value in technical.items() if key not in {'nodes', 'edges'}}
    try:
        _safe_output({'metadata': metadata, 'nodes': technical['nodes'], 'edges': technical['edges']})
    except ValueError:
        raise ProcessMermaidError('UNSAFE_PROCESS_MERMAID') from None
    if len(technical['edges']) > _MERMAID_MAX_EDGES:
        raise ProcessMermaidError('PROCESS_MERMAID_LIMIT')

    scope = _mermaid_text(technical['scope'])
    title = f"Technical process | Scope: {scope} | Coverage: {document['technical_status']}"
    if technical['coverage'].get('truncated') is True:
        title += ' | TRUNCATED'
    header = ['---', 'title: ' + json.dumps(title), '---']
    lines = ['flowchart LR', '  %% process-meta ' + _mermaid_json(metadata)]
    node_ids = {}
    lanes = defaultdict(list)
    for node in technical['nodes']:
        identity = node_ids[node['id']] = _diagram_id('n', node['id'])
        owner = node['owner_id']
        lane = owner if owner and owner.startswith('service:') and owner.removeprefix('service:') else None
        label = _label(node, node['kind'], node['label'])
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
        label = _label(edge, edge['relation'])
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
