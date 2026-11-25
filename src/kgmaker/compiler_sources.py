"""Source hashes shared by compiler capture, replay and proof consumers."""
from collections.abc import Mapping
from pathlib import PurePosixPath
import re

from .analysis_model import digest

JVM_RAW_SOURCE_SNAPSHOT = "selected-source-set-raw-1"
JVM_RAW_CAPTURE_PREFIX = "jvm-raw-1:"
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


def jvm_raw_capture_id(context):
    """Bind replayable source inputs to the original, pre-augmentation capture."""
    original = context.get("source_capture_base")
    raw = context.get("source_files")
    normalized = context.get("normalized_source_files")
    inputs = context.get("compiler_inputs")
    if (context.get("source_snapshot_version") != JVM_RAW_SOURCE_SNAPSHOT
            or context.get("language") != "jvm"
            or not isinstance(original, str) or not _SHA256.fullmatch(original)
            or not isinstance(raw, dict) or not isinstance(normalized, dict)
            or not normalized.keys() <= raw.keys()
            or not isinstance(inputs, list) or any(not isinstance(path, str) for path in inputs)):
        return None
    if any(not isinstance(checksum, str) or not _SHA256.fullmatch(checksum)
           for source_files in (raw, normalized) for checksum in source_files.values()):
        return None
    if inputs != sorted(set(inputs)) or any(
            path not in raw or not path.endswith((".java", ".kt"))
            or path.startswith("/") or "\\" in path or ":" in path
            or ".." in PurePosixPath(path).parts or PurePosixPath(path).as_posix() != path
            for path in inputs):
        return None
    return JVM_RAW_CAPTURE_PREFIX + digest({
        "capture": original,
        "source_snapshot_version": context["source_snapshot_version"],
        "compiler_inputs": inputs,
        "source_files": raw,
        "normalized_source_files": normalized,
    })


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
            from .workspace import split_id
            try:
                repo, _ = split_id(context_id)
            except ValueError:
                return None
            if not repo or not path.startswith(f'@{repo}/'):
                return None
            # Federated workspace graphs carry an inventory of raw file hashes.
        else:
            expected = projection.get(path, raw)
    if isinstance(expected, str) and _SHA256.fullmatch(expected) and files.get(path) == expected:
        return raw
    return None
