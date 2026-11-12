"""Data-only, content-bound project artifact templates (T046)."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path, PurePosixPath
from string import Template

from .analysis_model import AnalysisError, read_json, safe_path

KINDS = frozenset(('requirement', 'analysis', 'test_case', 'test_data',
                   'test_code', 'implementation_task', 'filename'))
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}\Z')
_RESERVED_SEGMENTS = frozenset(('.git', '.github', '.kgmaker'))
_WINDOWS_RESERVED = frozenset({
    'CON', 'PRN', 'AUX', 'NUL',
    *(f'COM{i}' for i in range(1, 10)),
    *(f'LPT{i}' for i in range(1, 10)),
})


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
    directory = safe_path(root, '.kgmaker/templates')
    planned = []
    for kind in sorted(KINDS):
        manifest, content = defaults(kind)
        paths = [safe_path(directory, kind + '.json'), safe_path(directory, kind + '.txt')]
        if any(p.exists() for p in paths):
            continue
        planned.extend(((paths[0], json.dumps(manifest, ensure_ascii=False, indent=2,
                                               sort_keys=True, allow_nan=False) + '\n'),
                        (paths[1], content)))
    if not planned:
        return []

    # Validate every destination before creating anything. Exclusive writes plus
    # rollback keep a later symlink/race/I/O error from leaving a partial install.
    missing_directories = []
    cursor = directory
    root_resolved = root.resolve()
    while cursor != root_resolved and not cursor.exists():
        missing_directories.append(cursor)
        cursor = cursor.parent
    created = []
    try:
        directory.mkdir(parents=True, exist_ok=True)
        for path, text in planned:
            stream = path.open('x', encoding='utf-8', newline='\n')
            created.append(path)
            with stream:
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
    except BaseException:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        for path in missing_directories:
            try:
                path.rmdir()
            except OSError:
                pass
        raise
    return [path.relative_to(root).as_posix() for path, _ in planned]


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
        canonical_directory = _validate_export_path(output_dir)
        directory = safe_path(root, canonical_directory)
        target = safe_path(root, canonical_directory + '/' + value)
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
            or value.casefold() in _RESERVED_SEGMENTS
            or value.split('.')[0].rstrip(' .').upper() in _WINDOWS_RESERVED):
        raise AnalysisError('Unsafe generated filename')


def _validate_export_path(value):
    """Require one canonical, portable, non-internal repository directory."""
    if not isinstance(value, str) or not value:
        raise AnalysisError('Output directory must be a canonical relative path')
    path = PurePosixPath(value)
    parts = value.split('/')
    if (path.is_absolute() or path.as_posix() != value
            or any(not part or part in {'.', '..'} for part in parts)):
        raise AnalysisError('Output directory must be a canonical relative path')
    for part in parts:
        _validate_filename(part)
        if part.casefold() in _RESERVED_SEGMENTS:
            raise AnalysisError('Output directory uses a reserved repository segment')
    return value


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
