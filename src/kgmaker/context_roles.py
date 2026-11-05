"""Pure source/derived role boundaries; a role never proves current code."""
from collections.abc import Mapping
import re

from .analysis_model import AnalysisError


def derived_context_claim(context):
    """Explicit producer fields are claims, never authority by themselves."""
    return (context.get('origin_trust') == 'WORKSPACE_DECLARATION'
            or 'kafka_binding_version' in context)


def classify_context_role(context, *, workspace=None, contexts=None):
    """Return (role, unknown reason), without files, processes or mutation.

    Ordinary legacy source contexts need no new marker. A derived claim needs
    its explicit producer declaration before it can be classified; otherwise
    it remains UNKNOWN and cannot fall back to service source ownership.
    Captured historical hashes are identity, not a current-source assertion.
    """
    if not derived_context_claim(context):
        return ('SOURCE' if context.get('mode') == 'SOURCE_ONLY' else 'COMPILER'), None
    from .kafka_bindings import VERSION, _workspace_context
    from .workspace import split_id, source_key

    if context.get('kafka_binding_version') != VERSION:
        return 'UNKNOWN', 'UNSUPPORTED_DERIVED_CONTEXT_VERSION'
    if not isinstance(workspace, Mapping):
        return 'UNKNOWN', 'DERIVED_CONTEXT_DECLARATION_REQUIRED'
    if context.get('origin_trust') != 'WORKSPACE_DECLARATION':
        return 'UNKNOWN', 'INVALID_DERIVED_CONTEXT_ORIGIN'
    freshness = context.get('freshness')
    if not isinstance(freshness, str) or freshness not in {'CURRENT', 'CONTENT_VERIFIED', 'EXECUTION_BOUND', 'STALE', 'UNKNOWN'}:
        return 'UNKNOWN', 'INVALID_DERIVED_CONTEXT_FRESHNESS'
    decorations = {'stale_reason', 'next_command'} & set(context)
    if any(not isinstance(context[key], str) or len(context[key]) > 8192 for key in decorations):
        return 'UNKNOWN', 'INVALID_DERIVED_CONTEXT_FRESHNESS'
    inputs = context.get('source_files')
    if (not isinstance(inputs, dict) or any(not isinstance(path, str)
            or checksum is not None and (not isinstance(checksum, str)
                or re.fullmatch(r'[0-9a-f]{64}', checksum) is None)
            for path, checksum in inputs.items())):
        return 'UNKNOWN', 'INVALID_DERIVED_CONTEXT_INPUTS'
    matches = []
    for binding in (workspace.get('kafka_bindings') or {}).get('bindings', []):
        if any(context.get(key) != binding[key] for key in ('repo_id', 'module', 'source_set', 'scope')):
            continue
        allowed = {source_key(binding['repo_id'], item['path']) for item in binding['config_files']}
        allowed.add(source_key(binding['contract']['repo_id'], binding['contract']['path']))
        reference = binding.get('code_ref')
        if reference is not None:
            allowed.add(source_key(binding['repo_id'], reference['source_file']))
        if set(inputs) != allowed:
            continue
        selected = context.get('selected_compiler_context')
        original_id = None
        if selected is not None:
            if not isinstance(selected, str):
                continue
            try:
                repo, original_id = split_id(selected)
            except AnalysisError:
                continue
            original = (contexts or {}).get(selected)
            if (repo != binding['repo_id'] or not isinstance(original, Mapping)
                    or original.get('language') != 'jvm'
                    or not isinstance(original.get('analyzer_version'), str) or not original['analyzer_version']
                    or original.get('mode') not in ('BUILD_IMPORT', 'BUILD_EXECUTE')
                    or any(original.get(key) != binding[key] for key in ('repo_id', 'module', 'source_set', 'scope'))
                    or original.get('spring_profiles') != binding['profiles']):
                continue
        pinned = binding['context_id'] or (reference or {}).get('context_id')
        if pinned is not None and original_id != pinned:
            continue
        expected = _workspace_context(workspace, binding, inputs, original_id)
        expected['freshness'] = freshness
        identity_fields = {key: value for key, value in context.items() if key not in decorations}
        if identity_fields == expected:
            matches.append(binding['id'])
    if len(matches) != 1:
        return 'UNKNOWN', 'DERIVED_CONTEXT_IDENTITY_MISMATCH'
    return 'WORKSPACE_DERIVED', None
