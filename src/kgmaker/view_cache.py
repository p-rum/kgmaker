"""Explicit, content-bound cache for already-derived view documents.

The cache is a conservative single-artifact store. A cache hit requires the full
workspace and graph snapshots, selected scope/context, and caller-supplied rule
versions to match. That deliberately includes absent-provider lookup space.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping

from .analysis_model import AnalysisError, atomic_write, canonical, digest
from .architecture_model import ViewDocument, ViewValidationError

_SCHEMA_VERSION = 1
_RULES_VERSION = "derived-view-cache-1"
_MAX_CACHE_BYTES = 16 * 1024 * 1024


class ViewCacheError(ValueError):
    """Invalid cache request or builder output."""


def _public_workspace(workspace: Mapping[str, Any]) -> dict:
    if not isinstance(workspace, Mapping):
        raise ViewCacheError("VIEW_CACHE_INVALID_WORKSPACE")
    # Match the public workspace projection used by T014/T016; resolved checkout
    # paths and manifest-loader internals are not dependency authority.
    from .remote_mapping import _workspace
    try:
        value = _workspace(workspace)
        canonical(value)
        return value
    except (TypeError, ValueError, RecursionError, OverflowError):
        raise ViewCacheError("VIEW_CACHE_INVALID_WORKSPACE") from None


def _public_graph(graph: Any) -> dict:
    try:
        from .model import KnowledgeGraph
        if isinstance(graph, KnowledgeGraph):
            value = graph.to_dict()
        elif isinstance(graph, Mapping):
            value = dict(graph)
        else:
            raise TypeError
        # Generated timestamps do not affect view semantics.
        value.pop("generated_at", None)
        canonical(value)
        return value
    except (TypeError, ValueError, KeyError, RecursionError, OverflowError):
        raise ViewCacheError("VIEW_CACHE_INVALID_GRAPH") from None


def dependency_binding(*, workspace: Mapping[str, Any], graph: Any,
                       rules: Mapping[str, Any], scope: str,
                       context_selection: Mapping[str, Any] | None = None,
                       annotations: Any = ()) -> dict:
    """Return fingerprints over every declared positive and negative dependency.

    Complete public workspace and graph snapshots are bound, rather than a
    selected set of known providers. A newly added provider therefore changes
    the binding and revalidates any prior unresolved lookup conservatively.
    """
    if not isinstance(rules, Mapping) or not rules or any(
            not isinstance(key, str) or not key for key in rules):
        raise ViewCacheError("VIEW_CACHE_INVALID_RULES")
    if not isinstance(scope, str) or not scope:
        raise ViewCacheError("VIEW_CACHE_INVALID_SCOPE")
    selection = {} if context_selection is None else context_selection
    if not isinstance(selection, Mapping):
        raise ViewCacheError("VIEW_CACHE_INVALID_CONTEXT_SELECTION")
    public_workspace = _public_workspace(workspace)
    public_graph = _public_graph(graph)
    try:
        rule_snapshot = dict(rules)
        selection_snapshot = dict(selection)
        # Keep the materialized fields as well as the stable digest so callers
        # can audit why a cache was keyed without trusting the stored view.
        binding = {
            "workspace_fingerprint": digest(public_workspace),
            "graph_fingerprint": digest(public_graph),
            "context_fingerprint": _context_fingerprint(public_graph),
            "rule_fingerprint": digest(rule_snapshot),
            "annotation_fingerprint": digest(annotations),
            "scope": scope,
            "context_selection_fingerprint": digest(selection_snapshot),
        }
        binding["fingerprint"] = digest(binding)
        return binding
    except (TypeError, ValueError, RecursionError, OverflowError):
        raise ViewCacheError("VIEW_CACHE_INVALID_DEPENDENCIES") from None


def _context_fingerprint(graph: Mapping[str, Any]) -> str:
    from .graph_provider import view_context_fingerprint
    try:
        return view_context_fingerprint(dict(graph))
    except (TypeError, ValueError):
        raise ViewCacheError("VIEW_CACHE_INVALID_GRAPH") from None


def _cache_value(path: Path) -> dict | None:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > _MAX_CACHE_BYTES:
            return None
        raw = path.read_text(encoding="utf-8")
        value = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
        required = {"schema_version", "rules_version", "dependency_fingerprint",
                    "scope", "context_selection", "view", "cache_fingerprint"}
        if (not isinstance(value, dict) or set(value) != required
                or type(value["schema_version"]) is not int or value["schema_version"] != _SCHEMA_VERSION
                or value["rules_version"] != _RULES_VERSION
                or not isinstance(value["dependency_fingerprint"], str)
                or not isinstance(value["scope"], str)
                or not isinstance(value["context_selection"], dict)
                or not isinstance(value["view"], dict)):
            return None
        if value["cache_fingerprint"] != digest({k: v for k, v in value.items() if k != "cache_fingerprint"}):
            return None
        return value
    except (OSError, UnicodeError, ValueError, TypeError, RecursionError, OverflowError):
        return None


def _safe_cache_target(path: Path) -> Path:
    target = path.absolute()
    if target.exists() and target.is_symlink():
        raise ViewCacheError("VIEW_CACHE_UNSAFE_PATH")
    current = target.parent
    while True:
        if current.is_symlink():
            raise ViewCacheError("VIEW_CACHE_UNSAFE_PATH")
        if current.parent == current:
            break
        current = current.parent
    return target


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def _reject_constant(value):
    raise ValueError("non-finite JSON value")


def _read_hit(path: Path, binding: dict, scope: str, selection: dict) -> ViewDocument | None:
    value = _cache_value(path)
    if value is None or (value["dependency_fingerprint"] != binding["fingerprint"]
            or value["scope"] != scope or value["context_selection"] != selection):
        return None
    try:
        document = ViewDocument.from_dict(value["view"])
    except (ViewValidationError, AnalysisError, ValueError, TypeError, KeyError):
        return None
    if document.scope != scope or document.context_selection != selection:
        return None
    return document


def get_or_build_view(path: Path, *, workspace: Mapping[str, Any], graph: Any,
                      rules: Mapping[str, Any], scope: str,
                      context_selection: Mapping[str, Any] | None,
                      builder: Callable[[], ViewDocument], annotations: Any = (),
                      expected_baseline_fingerprint: str) -> ViewDocument:
    """Return a current cached view or build and atomically publish a valid one.

    Invalid inputs and builder failures happen before the cache file is touched.
    A stale/corrupt entry is treated as a miss and remains intact until a new,
    fully validated result is ready for atomic replacement.
    """
    if not callable(builder):
        raise ViewCacheError("VIEW_CACHE_INVALID_BUILDER")
    if not isinstance(expected_baseline_fingerprint, str) or not expected_baseline_fingerprint:
        raise ViewCacheError("VIEW_CACHE_BASELINE_REQUIRED")
    selection = {} if context_selection is None else dict(context_selection) if isinstance(context_selection, Mapping) else None
    if selection is None:
        raise ViewCacheError("VIEW_CACHE_INVALID_CONTEXT_SELECTION")
    binding = dependency_binding(workspace=workspace, graph=graph, rules=rules,
                                 scope=scope, context_selection=selection,
                                 annotations=annotations)
    target = _safe_cache_target(Path(path))
    hit = _read_hit(target, binding, scope, selection)
    if hit is not None and hit.baseline_fingerprint == expected_baseline_fingerprint:
        return hit
    document = builder()
    if not isinstance(document, ViewDocument):
        raise ViewCacheError("VIEW_CACHE_INVALID_BUILDER_RESULT")
    # Round-trip the public representation so unsupported fields/invalid
    # provenance cannot enter the last valid cache artifact.
    try:
        serialized = document.to_dict(include_generation_metadata=False)
        validated = ViewDocument.from_dict(serialized)
    except (ViewValidationError, AnalysisError, ValueError, TypeError, KeyError):
        raise ViewCacheError("VIEW_CACHE_INVALID_BUILDER_RESULT") from None
    if (validated.scope != scope or validated.context_selection != selection
            or validated.rules_version not in rules.values()):
        raise ViewCacheError("VIEW_CACHE_BUILDER_BINDING_MISMATCH")
    if validated.baseline_fingerprint != expected_baseline_fingerprint:
        raise ViewCacheError("VIEW_CACHE_BUILDER_BINDING_MISMATCH")
    # Protect against builders that mutate their supposedly captured inputs while
    # running; never publish a result after its dependency binding moved.
    current = dependency_binding(workspace=workspace, graph=graph, rules=rules,
        scope=scope, context_selection=selection, annotations=annotations)
    if current["fingerprint"] != binding["fingerprint"]:
        raise ViewCacheError("VIEW_CACHE_INPUT_CHANGED_DURING_BUILD")
    value = {"schema_version": _SCHEMA_VERSION, "rules_version": _RULES_VERSION,
             "dependency_fingerprint": binding["fingerprint"], "scope": scope,
             "context_selection": selection, "view": serialized}
    value["cache_fingerprint"] = digest(value)
    raw = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if len(raw.encode("utf-8")) > _MAX_CACHE_BYTES:
        raise ViewCacheError("VIEW_CACHE_SIZE_LIMIT")
    atomic_write(target, raw)
    return validated


def get_or_build_snapshot_view(path: Path, *, snapshot: Mapping[str, Any],
                               rules: Mapping[str, Any], scope: str,
                               context_selection: Mapping[str, Any],
                               builder: Callable[[], ViewDocument],
                               expected_baseline_fingerprint: str,
                               annotations: Any = ()) -> ViewDocument:
    """Cache a view derived from one already-validated content-bound handoff.

    This supports public projection call sites that consume a versioned capture
    bundle rather than separate workspace and graph objects. The complete bundle
    and annotation/review snapshot are part of the key.
    """
    if not isinstance(snapshot, Mapping):
        raise ViewCacheError("VIEW_CACHE_INVALID_SNAPSHOT")
    return get_or_build_view(path, workspace={"captured_snapshot": dict(snapshot)},
        graph={"schema_version": 1, "contexts": []}, rules=rules, scope=scope,
        context_selection=context_selection, builder=builder, annotations=annotations,
        expected_baseline_fingerprint=expected_baseline_fingerprint)
