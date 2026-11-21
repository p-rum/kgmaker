"""Source hashes shared by compiler capture, replay and proof consumers."""
from collections.abc import Mapping
import re


JVM_RAW_SOURCE_SNAPSHOT = "selected-source-set-raw-1"
JVM_JPA_SOURCE_SNAPSHOTS = frozenset({"selected-source-set-2", JVM_RAW_SOURCE_SNAPSHOT})
JVM_SOURCE_SNAPSHOTS = JVM_JPA_SOURCE_SNAPSHOTS | {"selected-source-set-1"}
_SHA256 = re.compile(r"[0-9a-f]{64}")


def normalized_source_projection(files, source_files):
    """Keep the structural hash for scanned paths whose byte hash differs."""
    return {path: files[path] for path, checksum in source_files.items()
            if path in files and files[path] != checksum}


def unsupported_kotlin_source(raw_file_hashes, compiler_inputs):
    """Kotlin workers report PSI offsets over normalized input text."""
    return next((path for path in compiler_inputs if path.endswith('.kt') and path in raw_file_hashes), None)


def compiler_source_digest(files, context, path):
    """Admit a captured digest against the file inventory for its graph kind."""
    captured = context.get("source_files")
    raw = captured.get(path) if isinstance(captured, Mapping) and isinstance(path, str) else None
    if not isinstance(raw, str) or not _SHA256.fullmatch(raw):
        return None
    expected = raw
    if context.get("source_snapshot_version") == JVM_RAW_SOURCE_SNAPSHOT:
        projection = context.get("normalized_source_files")
        if context.get("language") != "jvm" or not isinstance(projection, Mapping):
            return None
        context_id = context.get('id')
        if isinstance(context_id, str) and context_id.startswith('repo:'):
            repo = context.get('repo_id')
            if not isinstance(repo, str) or not repo or not context_id.startswith(f'repo:{repo}:') \
                    or not path.startswith(f'@{repo}/'):
                return None
            # Federated workspace graphs carry an inventory of raw file hashes.
        else:
            expected = projection.get(path, raw)
    if isinstance(expected, str) and _SHA256.fullmatch(expected) and files.get(path) == expected:
        return raw
    return None
