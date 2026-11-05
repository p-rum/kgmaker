"""Workspace graph commands and read-only schema inspection."""
from __future__ import annotations
import json
from pathlib import Path
from .analysis_model import AnalysisError, read_json, safe_path


def register_schema(subparsers):
    parser = subparsers.add_parser('schema', help='offline Flyway schema reconstruction')
    sub = parser.add_subparsers(dest='schema_command', required=True)
    for action in ('inspect', 'diff', 'compatibility'):
        child = sub.add_parser(action)
        child.add_argument('--root', type=Path, default=Path.cwd())
        child.add_argument('--workspace', type=Path)
        child.add_argument('--repo')
        child.add_argument('--stream', default='main')
        child.add_argument('--target')
        child.add_argument('--database', help='explicit database realm selector')
        if action == 'compatibility':
            child.add_argument('--context', help='explicit compiler context ID')
        child.add_argument('--config', help='explicit root-relative JSON Flyway configuration')
        child.add_argument('--format', choices=('json', 'text'), default='json')
        if action == 'diff':
            child.add_argument('--from', dest='from_target', required=True)
            child.add_argument('--to', dest='to_target', required=True)


def schema_command(args):
    from .schema_replay import reconstruct, schema_diff
    from .workspace import load_workspace
    try:
        root, config = args.root.resolve(), {}
        if args.workspace:
            manifest = load_workspace(args.workspace)
            repos = [r for r in manifest['repositories'] if r['id'] == args.repo]
            if len(repos) != 1:
                raise AnalysisError('Workspace schema command requires an existing --repo')
            repo = repos[0]; root = Path(repo['_root'])
            configs = repo.get('flyway', {})
            configs = configs if isinstance(configs, list) else [configs]
            matches = [c for c in configs if c.get('stream_id', 'main') == args.stream
                       and (not getattr(args, 'database', None) or c.get('database_id') == args.database)]
            if len(matches) != 1:
                raise AnalysisError('Schema stream must identify exactly one declared configuration')
            config = matches[0]
        elif args.repo:
            raise AnalysisError('--repo requires --workspace')
        if args.config:
            config = {**config, **read_json(safe_path(root, args.config))}
        if getattr(args, 'database', None):
            config = {**config, 'database_id': args.database}
        config = {**config, 'target': args.target or config.get('target', 'latest'), 'stream_id': args.stream}
        if args.schema_command == 'compatibility':
            from .feature import current_graph
            from .schema_replay import schema_compatibility
            from .feature import attach_schema
            from .framework import augment_framework_graph
            schema = reconstruct(root, config)
            graph = current_graph(root, args.workspace)[0]
            if args.workspace is None:
                graph = attach_schema(graph, schema, root)
                for context in list(graph.contexts):
                    if context.get('language') == 'jvm' and context.get('freshness') != 'STALE':
                        graph = augment_framework_graph(root, graph, context)
            result = schema_compatibility(schema, graph, context_id=args.context)
        else:
            result = reconstruct(root, config) if args.schema_command == 'inspect' else schema_diff(root, config, args.from_target, args.to_target)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 2 if result.get('status') == 'INVALID' or result.get('replay_status') == 'INVALID' else 0
    except AnalysisError as exc:
        print(json.dumps({'error': str(exc), 'exit_code': exc.code})); return exc.code
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({'error': str(exc), 'exit_code': 1})); return 1


def workspace_command(args):
    from .workspace import snapshot_workspace
    from .store import save_graph, load_graph, query_nodes
    from .dataflow import impact_paths
    try:
        command = args.command
        baseline, coverage, sources, graph, metadata = snapshot_workspace(args.workspace, cache_root=args.root.resolve(),
                                                                          persist_cache=command in {'scan', 'build', 'update'})
        if command in {'scan', 'build', 'update', 'docs'}:
            if command == 'docs' and (args.confluence_dir or args.action):
                raise AnalysisError('Workspace docs renders federated graph only; Confluence checks are per-repo')
            save_graph(graph, args.root.resolve(), generate_docs=not getattr(args, 'no_docs', False))
            result = {'baseline': baseline, 'coverage': coverage, 'output_root': str(args.root.resolve())}
        elif command == 'status':
            old = load_graph(args.root.resolve())
            source_current = (old is not None and old.nodes == graph.nodes
                              and old.edges == graph.edges and old.files == graph.files
                              and old.contexts == graph.contexts)
            stale_contexts = [
                {key: context.get(key) for key in (
                    'id', 'repo_id', 'module', 'source_set', 'scope', 'stale_reason', 'next_command')}
                for context in graph.contexts
                if context.get('analyzer_version') and context.get('freshness') == 'STALE'
            ]
            result = {'current': source_current and not stale_contexts,
                      'source_graph_current': source_current,
                      'compiler_contexts_current': not stale_contexts,
                      'stale_compiler_contexts': stale_contexts,
                      'baseline': baseline, 'coverage': coverage}
        elif command == 'impact':
            if not args.entity or not args.include_data_flow or args.files:
                raise AnalysisError('Workspace impact requires --entity --include-data-flow')
            from .views import project, select_context
            context_id = select_context(graph, args.scope, args.context)
            result = impact_paths(project(graph, args.scope, context_id=context_id), args.entity)
        elif command == 'query':
            if args.analysis:
                from . import feature
                candidate = read_json(safe_path(args.root.resolve(), f'.kgmaker/analyses/{args.analysis}/analysis.json'))
                result = feature.validate(args.root.resolve(), args.analysis, candidate)
                packet = feature.load_packet(args.root.resolve(), args.analysis)
                if packet.get('workspace', {}).get('manifest_path') != str(args.workspace.resolve()):
                    raise AnalysisError('Query workspace differs from analysis workspace')
                if not result['valid']:
                    print(json.dumps(result)); return result['exit_code']
            from .views import select_context
            context_id = select_context(graph, args.scope, args.context)
            result = {'matches': [{'id': n.id, 'name': n.name, 'path': n.path, 'score': score, 'state': 'AS_IS'}
                                  for n, score in query_nodes(graph, ' '.join(args.terms), args.limit,
                                                              args.scope, context_id)]}
            if args.analysis:
                words = ' '.join(args.terms).lower().split()
                result['matches'] += [n for n in candidate['proposal']['nodes'] if any(w in json.dumps(n).lower() for w in words)]
        else:
            raise AnalysisError('Unsupported workspace command')
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        return 2 if command == 'status' and not result['current'] else 0
    except AnalysisError as exc:
        print(json.dumps({'error': str(exc), 'exit_code': exc.code})); return exc.code
    except (OSError, ValueError) as exc:
        print(json.dumps({'error': str(exc), 'exit_code': 1})); return 1
