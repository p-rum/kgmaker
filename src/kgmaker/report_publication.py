"""Pin a report to loaded artifact bytes and existing read-only source snapshots."""
from pathlib import Path
from types import SimpleNamespace

from . import feature
from .analysis_model import AnalysisError, digest, read_json, safe_path


class ReportGuard:
    def __init__(self, root: Path):
        self.root = root
        self.artifacts = {}

    def watch(self, path: Path):
        raw = path.read_bytes() if path.exists() else None
        self.artifacts[path] = raw
        return raw

    def read(self, path: Path, loader=None):
        raw = self.watch(path)
        if raw is None:
            raise AnalysisError('Report input disappeared: ' + str(path), 3)
        # Reuse the strict parser (duplicate keys/non-finite values rejected),
        # feeding the captured bytes rather than reading a second payload.
        value = read_json(SimpleNamespace(name=path.name, read_text=lambda encoding: raw.decode(encoding)))
        if loader is not None and loader() != value:
            raise AnalysisError('Report input payload changed during loading: ' + str(path), 3)
        self.check_artifacts()
        return value

    def check_artifacts(self):
        for path, raw in self.artifacts.items():
            if (path.read_bytes() if path.exists() else None) != raw:
                raise AnalysisError('Report input changed during publication: ' + str(path), 3)

    def bind_sources(self, packet: dict):
        self.workspace = Path(packet['workspace']['manifest_path']) if packet.get('workspace') else None
        self.watch(safe_path(self.root, packet['requirement_path']))
        # Use the existing complete snapshot so unavailable selected contexts may
        # still be reported as historical. Never persist caches or select a new context.
        self.snapshot_hash = self.current_sources()
        self.check_artifacts()

    def current_sources(self):
        baseline, coverage, sources, _ = feature.snapshot(
            self.root, workspace=self.workspace, _select_context=False)
        # Atomic output tempfiles are intentionally outside feature evidence.
        # Ignore only their inventory exclusion entries, never source/context data.
        coverage = {**coverage, 'exclusions': [entry for entry in coverage.get('exclusions', [])
                    if not entry.get('path', '').startswith(feature.GENERATED_PREFIX)]}
        return digest({'baseline': baseline, 'coverage': coverage, 'sources': sources})

    def verify(self):
        self.check_artifacts()
        if self.current_sources() != self.snapshot_hash:
            raise AnalysisError('Report source/context inputs changed during publication', 3)
        self.check_artifacts()


def report_output_path(root: Path, output: str) -> Path:
    """Keep the report inside its reserved subtree and reject file aliases."""
    from .view_cache import _safe_cache_target, ViewCacheError
    if not output.startswith(feature.GENERATED_PREFIX):
        raise AnalysisError('Feature report output must be under docs/generated/features/ to prevent evidence feedback')
    target = safe_path(root, output)
    if target.relative_to(root).parts[:3] != ('docs', 'generated', 'features'):
        raise AnalysisError('Feature report output escapes its reserved subtree')
    try:
        return _safe_cache_target(target)
    except ViewCacheError as exc:
        raise AnalysisError('Unsafe feature report output or input alias: ' + str(exc)) from exc


def publish_report(target: Path, text: str, writer, *, before_replace):
    """Use atomic_write, cleaning only empty parents created by this attempt.

    Same ownership rule as flow_report.publish: preserve preexisting directories
    and concurrent contents, including on KeyboardInterrupt.
    """
    missing = []
    parent = target.parent
    while not parent.exists():
        missing.append(parent)
        parent = parent.parent
    created = []
    try:
        for parent in reversed(missing):
            try:
                parent.mkdir()
                created.append(parent)
            except FileExistsError:
                if not parent.is_dir():
                    raise
        writer(target, text, before_replace=before_replace)
    except BaseException:
        for parent in reversed(created):
            try:
                parent.rmdir()
            except OSError:
                pass
        raise
