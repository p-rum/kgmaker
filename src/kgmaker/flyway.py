"""Offline Flyway SQL inventory and explicit clean-install migration plans.

Conventions follow Redgate's versioned/repeatable/baseline documentation.
Source SHA-256 is NOT a Flyway checksum. Nothing here executes migrations.
"""
from __future__ import annotations

import re
import tomllib
from xml.etree import ElementTree
from pathlib import Path

from .analysis_model import AnalysisError, digest, file_hash, safe_path

PARSER_VERSION = 'flyway-offline-1'
DEFAULT_LOCATION = 'src/main/resources/db/migration'
DEFAULTS = {'database_id': 'default', 'stream_id': 'main', 'dialect': 'postgresql',
            'locations': [DEFAULT_LOCATION], 'target': 'latest', 'default_schema': 'public',
            'schemas': ['public'], 'prefix': 'V', 'repeatable_prefix': 'R',
            'baseline_prefix': 'B', 'undo_prefix': 'U', 'separator': '__',
            'suffixes': ['.sql'], 'placeholders': {}, 'mode': 'versioned'}


def version(value: str) -> tuple[int, ...]:
    if not isinstance(value, str) or not re.fullmatch(r'\d+(?:[._]\d+)*', value):
        raise AnalysisError('Unsupported Flyway version: ' + str(value))
    parts = [int(v) for v in re.split(r'[._]', value)]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def configuration(root: Path, overrides: dict | None = None) -> dict:
    overrides = overrides or {}
    if not isinstance(overrides, dict):
        raise AnalysisError('Flyway configuration must be an object')
    config = {**DEFAULTS, 'provenance': [], 'diagnostics': []}
    profile = overrides.get('profile')
    paths = ['flyway.conf', 'flyway.toml', 'src/main/resources/application.properties',
             'src/main/resources/application.yml', 'src/main/resources/application.yaml',
             'pom.xml', 'build.gradle', 'build.gradle.kts']
    if profile:
        if not re.fullmatch(r'[\w-]+', profile):
            raise AnalysisError('Invalid configuration profile')
        paths += [f'src/main/resources/application-{profile}.{s}' for s in ('properties', 'yml', 'yaml')]
    aliases = {'locations': 'locations', 'defaultSchema': 'default_schema', 'default-schema': 'default_schema',
               'schemas': 'schemas', 'target': 'target', 'sqlMigrationPrefix': 'prefix',
               'sql-migration-prefix': 'prefix', 'sqlMigrationSeparator': 'separator',
               'sqlMigrationSuffixes': 'suffixes', 'baselineMigrationPrefix': 'baseline_prefix'}
    aliases.update({'sql-migration-separator': 'separator', 'sql-migration-suffixes': 'suffixes',
                    'repeatableSqlMigrationPrefix': 'repeatable_prefix', 'repeatable-sql-migration-prefix': 'repeatable_prefix',
                    'undoSqlMigrationPrefix': 'undo_prefix', 'baseline-migration-prefix': 'baseline_prefix'})
    selected_values = {}
    for relative in paths:
        path = safe_path(root, relative)
        if not path.is_file():
            continue
        text = path.read_text(encoding='utf-8')
        values = {}
        if relative == 'pom.xml':
            try:
                xml = ElementTree.fromstring(text)
                for element in xml.iter():
                    element.tag = element.tag.split('}')[-1]
                for plugin in xml.iter('plugin'):
                    if plugin.findtext('artifactId') != 'flyway-maven-plugin':
                        continue
                    configuration_node = plugin.find('configuration')
                    if configuration_node is not None:
                        for child in configuration_node:
                            if child.tag in aliases:
                                values[child.tag] = [x.text.strip() for x in child if x.text] if len(child) else (child.text or '').strip()
            except ElementTree.ParseError:
                config['diagnostics'].append('Unsupported Maven XML configuration')
        elif relative in {'build.gradle', 'build.gradle.kts'}:
            block = re.search(r'\bflyway\s*\{([^{}]*)\}', text, re.S)
            if block:
                for match in re.finditer(r'\b(\w+)\s*=\s*([^\n;]+)', block[1]):
                    key, raw = match[1], match[2].strip()
                    if key not in aliases:
                        continue
                    strings = re.findall(r'[\"\']([^\"\']+)[\"\']', raw)
                    if strings and re.fullmatch(r'(?:arrayOf\s*\(|\[)?\s*(?:[\"\'][^\"\']+[\"\']\s*,?\s*)+(?:\)|\])?', raw):
                        values[key] = strings if aliases[key] in {'locations', 'schemas', 'suffixes'} else strings[0]
                    else:
                        config['diagnostics'].append('Dynamic Gradle Flyway setting: ' + key)
        elif path.suffix == '.toml':
            try:
                values = tomllib.loads(text).get('flyway', {})
            except tomllib.TOMLDecodeError:
                config['diagnostics'].append('Unsupported TOML configuration: ' + relative)
        elif path.suffix in {'.properties', '.conf'}:
            for line in text.splitlines():
                match = re.match(r'\s*(?:spring\.)?flyway\.([\w.-]+)\s*=\s*(.*?)\s*$', line)
                if match:
                    values[match[1]] = match[2]
        else:
            # Indentation-scoped flat YAML scalar subset; never evaluate tags/expressions.
            active = None
            for line in text.splitlines():
                if re.match(r'\s*flyway:\s*$', line):
                    active = len(line) - len(line.lstrip())
                    continue
                if active is not None and line.strip() and len(line) - len(line.lstrip()) <= active:
                    active = None
                if active is not None:
                    m = re.match(r'\s*([\w-]+):\s*([^#\n]+)', line)
                    if m:
                        values[m[1]] = m[2].strip().strip('\"\'')
        used = []
        for key, value in values.items():
            if key not in aliases:
                if key in {'outOfOrder', 'cherryPick', 'callbacks', 'baselineVersion', 'baselineOnMigrate'}:
                    config['diagnostics'].append(f'Execution setting requires an explicit offline plan: {key}')
                continue  # includes all credentials, URL and passwords
            name = aliases[key]
            value = value.split(',') if name in {'locations', 'schemas', 'suffixes'} and isinstance(value, str) else value
            rank = 2 if profile and 'application-' + profile + '.' in relative else 1
            previous = selected_values.get(name)
            if previous and previous[1] == rank and previous[0] != value and name not in overrides:
                config['diagnostics'].append('Conflicting configuration requires explicit override: ' + name)
            if previous is None or rank >= previous[1]:
                config[name] = value
                selected_values[name] = (value, rank)
            used.append(key)
        if used:
            config['provenance'].append({'path': relative, 'sha256': file_hash(path), 'keys': sorted(used)})
    allowed = set(DEFAULTS) | {'profile', 'baseline_version', 'initial_snapshot'}
    unknown = set(overrides) - allowed
    if unknown:
        raise AnalysisError('Unsupported Flyway configuration keys: ' + ', '.join(sorted(unknown)))
    config.update(overrides)
    config['provenance'].append({'kind': 'EXPLICIT_CONFIGURATION', 'keys': sorted(overrides)})
    if config['dialect'] != 'postgresql' or config['mode'] not in {'versioned', 'baseline_script', 'snapshot'}:
        raise AnalysisError('Supported dialect is postgresql; modes are versioned/baseline_script/snapshot')
    for key in ('locations', 'schemas', 'suffixes'):
        if not isinstance(config[key], list) or any(not isinstance(x, str) or not x for x in config[key]):
            raise AnalysisError(key + ' must be a list of non-empty strings')
    for key in ('prefix', 'repeatable_prefix', 'baseline_prefix', 'undo_prefix', 'separator', 'default_schema', 'stream_id', 'database_id'):
        if not isinstance(config[key], str) or not config[key]:
            raise AnalysisError(key + ' must be a non-empty string')
    if not isinstance(config['placeholders'], dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in config['placeholders'].items()):
        raise AnalysisError('Placeholders must be explicitly supplied string values')
    if '${' in str(config['target']):
        config['diagnostics'].append('Dynamic target is unresolved; latest inventory is not a verified target')
        config['target'] = 'latest'
    return config


def migration_plan(root: Path, overrides: dict | None = None) -> dict:
    config = configuration(root, overrides)
    diagnostics = list(config['diagnostics'])
    inventory, seen = [], set()
    for location in config['locations']:
        if location.startswith('classpath:'):
            location = 'src/main/resources/' + location[len('classpath:'):].lstrip('/')
        elif location.startswith('filesystem:'):
            location = location[len('filesystem:'):]
        if ':' in location:
            diagnostics.append('Remote/JAR location is not covered: ' + location)
            continue
        directory = safe_path(root, location)
        if not directory.is_dir():
            diagnostics.append('Missing migration location: ' + location)
            continue
        for path in sorted(directory.rglob('*')):
            if not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            safe_path(root, relative)
            if relative in seen:
                continue
            seen.add(relative)
            name, kind, ver, description = path.name, 'UNKNOWN', None, path.stem
            sep = re.escape(config['separator'])
            for label, key in [('VERSIONED', 'prefix'), ('BASELINE', 'baseline_prefix'), ('UNDO', 'undo_prefix')]:
                m = re.match(re.escape(config[key]) + r'(\d+(?:[._]\d+)*)' + sep + r'(.+)', name)
                if m:
                    kind, ver, description = label, m[1], m[2]
                    break
            if name.startswith(config['repeatable_prefix'] + config['separator']):
                kind, description = 'REPEATABLE', name.split(config['separator'], 1)[1]
            if re.match(r'(?:before|after)[A-Z]', name):
                kind = 'CALLBACK'
            sql = any(name.endswith(s) for s in config['suffixes'])
            if path.suffix in {'.java', '.kt'}:
                kind = 'PROGRAMMATIC'
            elif not sql:
                continue
            inventory.append({'path': relative, 'sha256': file_hash(path), 'kind': kind,
                              'version': ver, 'description': description, 'sql': sql})
    versions = {}
    for item in inventory:
        if item['kind'] in {'VERSIONED', 'BASELINE', 'UNDO'}:
            key = item['kind'], version(item['version'])
            if key in versions:
                diagnostics.append('Duplicate/equivalent migration version: ' + item['path'] + ' / ' + versions[key])
            versions[key] = item['path']
        if item['kind'] in {'PROGRAMMATIC', 'CALLBACK', 'UNKNOWN'}:
            diagnostics.append('Unknown schema effects: ' + item['path'])
    target = None if config['target'] == 'latest' else version(config['target'])
    candidates = sorted([x for x in inventory if x['kind'] == 'VERSIONED'], key=lambda x: version(x['version']))
    selected = [x for x in candidates if target is None or version(x['version']) <= target]
    if config['mode'] == 'baseline_script':
        bases = [x for x in inventory if x['kind'] == 'BASELINE' and (target is None or version(x['version']) <= target)]
        if bases:
            base = max(bases, key=lambda x: version(x['version']))
            selected = [base] + [x for x in selected if version(x['version']) > version(base['version'])]
        else:
            diagnostics.append('No applicable baseline script')
    elif config['mode'] == 'snapshot':
        if not config.get('initial_snapshot') or not config.get('baseline_version'):
            diagnostics.append('Snapshot mode requires initial_snapshot and baseline_version')
        else:
            selected = [x for x in selected if version(x['version']) > version(config['baseline_version'])]
    elif any(x['kind'] == 'BASELINE' for x in inventory):
        diagnostics.append('Baseline scripts inventoried but versioned mode explicitly selected')
    repeatables = sorted([x for x in inventory if x['kind'] == 'REPEATABLE'], key=lambda x: x['description'])
    historical = target is not None and bool(candidates) and target < version(candidates[-1]['version'])
    if historical and repeatables:
        diagnostics.append('Historical repeatable contents are UNKNOWN; current repeatables not replayed')
    else:
        selected += repeatables
    return {'schema_version': 1, 'parser_version': PARSER_VERSION, 'config': config,
            'inventory': inventory, 'migrations': selected, 'diagnostics': sorted(set(diagnostics)),
            'valid': not any('Duplicate/' in d for d in diagnostics), 'historical': historical,
            'reconstruction_mode': 'CLEAN_INSTALL_DECLARATION', 'provenance': 'MIGRATION_DERIVED',
            'fingerprint': digest({'config': config, 'inventory': inventory})}
