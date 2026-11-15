"""Pin a report to loaded artifact bytes and existing read-only source snapshots."""
from pathlib import Path

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
        self.watch(path)
        value = loader() if loader else read_json(path)
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
