"""Data-only, content-bound project artifact templates (T046)."""
from __future__ import annotations

import re
from pathlib import Path
from string import Template

from .analysis_model import AnalysisError, read_json, safe_path

KINDS = frozenset(('requirement', 'analysis', 'test_case', 'test_data',
                   'test_code', 'implementation_task', 'filename'))
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}\Z')


def render(root: Path, kind: str, variables: dict[str, str], template_id: str | None = None) -> dict:
    """Render without execution or writes; explicit invalid selections never fall back."""
    if kind not in KINDS:
        raise AnalysisError('Unknown template kind')
    selected = template_id
    if selected is None:
        settings = safe_path(root, '.kgmaker/templates/defaults.json')
        config = read_json(settings) if settings.exists() else {}
        if not isinstance(config, dict) or set(config) - KINDS:
            raise AnalysisError('Invalid template defaults')
        selected = config.get(kind, kind)
    if not isinstance(selected, str):
        raise AnalysisError('Invalid template ID')
    if not _ID.fullmatch(selected):
        raise AnalysisError('Invalid template ID')
    directory = safe_path(root, '.kgmaker/templates')
    manifest_path = safe_path(root, f'.kgmaker/templates/{selected}.json')
    if manifest_path.exists():
        manifest = read_json(manifest_path)
        expected = {'schema_version', 'id', 'kind', 'revision', 'description', 'variables', 'content'}
        if not isinstance(manifest, dict) or set(manifest) != expected:
            raise AnalysisError('Invalid template manifest fields')
        if (manifest['schema_version'] != 1 or manifest['id'] != selected
                or manifest['kind'] != kind or type(manifest['revision']) is not int
                or manifest['revision'] < 1):
            raise AnalysisError('Invalid template identity or revision')
        names = manifest['variables']
        if (not isinstance(names, list) or any(not isinstance(n, str) or not n.isidentifier() for n in names)
                or len(set(names)) != len(names)):
            raise AnalysisError('Invalid template variables')
        content_path = safe_path(directory, manifest['content'])
        if not content_path.is_file() or content_path.stat().st_size > 1_000_000:
            raise AnalysisError('Invalid template content')
        content = content_path.read_text(encoding='utf-8')
    elif template_id is not None or selected != kind:
        raise AnalysisError('Explicit template does not exist')
    else:
        names = ['id', 'slug', 'extension'] if kind == 'filename' else ['title', 'body']
        content = '${id}_${slug}.${extension}' if kind == 'filename' else '# ${title}\n\n${body}\n'
        manifest = {'schema_version': 1, 'id': selected, 'kind': kind, 'revision': 1,
                    'description': 'Bundled default', 'variables': names, 'content': None}
    template = Template(content)
    if not template.is_valid() or set(template.get_identifiers()) != set(names):
        raise AnalysisError('Template placeholders do not match manifest')
    if not isinstance(variables, dict) or any(not isinstance(variables.get(n), str) for n in names):
        raise AnalysisError('Missing or non-text template variable')
    result = template.substitute({n: variables[n] for n in names})
    if kind == 'filename':
        _validate_filename(result)
    from .analysis_model import digest
    return {'text': result, 'template': {'id': selected, 'revision': manifest['revision'],
            'sha256': digest({'manifest': manifest, 'content': content})},
            'definition': {'manifest': manifest, 'content': content}}


def defaults(kind):
    if kind not in KINDS:
        raise AnalysisError('Unknown template kind')
    names = ['id', 'slug', 'extension'] if kind == 'filename' else ['title', 'body']
    content = '${id}_${slug}.${extension}' if kind == 'filename' else '# ${title}\n\n${body}\n'
    return ({'schema_version': 1, 'id': kind, 'kind': kind, 'revision': 1,
             'description': 'Project default', 'variables': names, 'content': kind + '.txt'}, content)


def install(root):
    """Install editable defaults, preserving both modified and half-installed pairs."""
    from .analysis_model import write_json, atomic_write
    directory = safe_path(root, '.kgmaker/templates')
    written = []
    for kind in sorted(KINDS):
        manifest, content = defaults(kind)
        paths = [safe_path(directory, kind + '.json'), safe_path(directory, kind + '.txt')]
        if any(p.exists() for p in paths):
            continue
        directory.mkdir(parents=True, exist_ok=True)
        atomic_write(paths[1], content)
        write_json(paths[0], manifest)
        written.extend(p.relative_to(root).as_posix() for p in paths)
    return written


def generate(root, kind, variables, *, template_id=None, filename_template=None,
             filename_variables=None, output_dir=None, filename=None):
    """Render a reviewable artefact; publication is explicit and never overwrites."""
    result = render(root, kind, variables, template_id)
    if output_dir is not None:
        name = render(root, 'filename', filename_variables or {}, filename_template) if filename is None else None
        value = filename if filename is not None else name['text']
        if Path(value).name != value or '/' in value or '\\' in value:
            raise AnalysisError('Output filename must be a basename')
        # Validate even a caller-supplied filename through the same portable rules.
        _validate_filename(value)
        directory = safe_path(root, output_dir)
        target = safe_path(root, output_dir.rstrip('/') + '/' + value)
        if target.exists():
            raise AnalysisError('Output collision; existing artefact preserved')
        directory.mkdir(parents=True, exist_ok=True)
        from . import provenance
        from .analysis_model import digest, file_hash
        created = False
        try:
            with provenance.transaction(root) as data:
                # Exclusive creation prevents races overwriting an existing artefact.
                with target.open('x', encoding='utf-8') as stream:
                    created = True
                    stream.write(result['text'])
                metadata = {'template': result['template'], 'content_sha256': file_hash(target)}
                if name:
                    metadata['filename_template'] = name['template']
                ref = provenance.reference('document', target.relative_to(root).as_posix(),
                         digest(metadata), metadata,
                         locator={'path':target.relative_to(root).as_posix(), 'sha256':file_hash(target)})
                provenance.put(data, ref)
                result['reference'] = ref['key']
        except BaseException:
            if created:
                target.unlink(missing_ok=True)
            raise
        result['output'] = target.relative_to(root).as_posix()
        if name:
            result['filename_template'] = name['template']
    return result


def _validate_filename(value):
    if (not isinstance(value,str) or not value or len(value)>240 or value in ('.','..')
            or any(c in value for c in '/\\:<>"|?*') or value.endswith((' ','.'))
            or any(ord(c)<32 for c in value)
            or value.split('.')[0].upper() in {'CON','PRN','AUX','NUL',
                *('COM'+str(i) for i in range(1,10)), *('LPT'+str(i) for i in range(1,10))}):
        raise AnalysisError('Unsafe generated filename')


def render_snapshot(snapshot, variables):
    """Use the exact pinned definition, even if project defaults have since changed."""
    from .analysis_model import digest
    definition = snapshot['definition']
    if digest(definition) != snapshot['template']['sha256']:
        raise AnalysisError('Template snapshot integrity mismatch')
    names = definition['manifest']['variables']
    if any(not isinstance(variables.get(n),str) for n in names):
        raise AnalysisError('Missing pinned template variable')
    value = Template(definition['content']).substitute({n:variables[n] for n in names})
    if definition['manifest']['kind']=='filename':
        _validate_filename(value)
    return {'text':value,'template':snapshot['template']}
