"""Read-only Maven POM discovery used by project inspection.

This module intentionally reports a declared model.  Effective profiles,
dependency resolution and generated source roots require an explicit build
export and are therefore marked as unresolved until a BuildPlan/BuildManifest
supplies them.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .analysis_model import AnalysisError, digest, file_hash, safe_path


POM_NS = "http://maven.apache.org/POM/4.0.0"


def _tag(name: str) -> str:
    return "{" + POM_NS + "}" + name


def _text(parent: ET.Element | None, name: str, default: str | None = None) -> str | None:
    if parent is None:
        return default
    child = parent.find(_tag(name))
    value = child.text.strip() if child is not None and child.text else None
    return value or default


def _children(parent: ET.Element | None, name: str) -> list[ET.Element]:
    return list(parent.findall(_tag(name))) if parent is not None else []


def _interpolate(value: str | None, properties: dict[str, str]) -> str | None:
    if value is None:
        return None
    return re.sub(r"\$\{([^}]+)\}", lambda match: properties.get(match.group(1), match.group(0)), value)


def _parse(path: Path, root: Path, properties: dict[str, str]) -> dict[str, Any]:
    try:
        tree = ET.parse(path)
    except (ET.ParseError, OSError) as error:
        raise AnalysisError(f"Invalid Maven POM {path.relative_to(root)}: {error}") from None
    project = tree.getroot()
    if project.tag.split("}")[-1] != "project":
        raise AnalysisError(f"Invalid Maven POM root: {path.relative_to(root)}")
    local_properties = dict(properties)
    props = project.find(_tag("properties"))
    if props is not None:
        local_properties.update({child.tag.split("}")[-1]: (child.text or "").strip() for child in list(props)})
    group_id = _interpolate(_text(project, "groupId") or _text(project.find(_tag("parent")), "groupId"), local_properties)
    version = _interpolate(_text(project, "version") or _text(project.find(_tag("parent")), "version"), local_properties)
    artifact_id = _interpolate(_text(project, "artifactId"), local_properties)
    modules = [_interpolate((item.text or "").strip(), local_properties) for item in _children(project.find(_tag("modules")), "module")]
    dependencies = []
    for item in _children(project.find(_tag("dependencies")), "dependency"):
        dependencies.append({key: _interpolate(_text(item, key), local_properties)
                             for key in ("groupId", "artifactId", "version", "scope", "classifier", "type", "optional")})
    plugins = []
    build = project.find(_tag("build"))
    for item in _children(build.find(_tag("plugins")) if build is not None else None, "plugin"):
        plugins.append({key: _interpolate(_text(item, key), local_properties) for key in ("groupId", "artifactId", "version")})
    parent = project.find(_tag("parent"))
    relative_parent = _text(parent, "relativePath", "../pom.xml") if parent is not None else None
    return {
        "path": path.relative_to(root).as_posix(), "sha256": file_hash(path),
        "group_id": group_id, "artifact_id": artifact_id, "version": version,
        "packaging": _interpolate(_text(project, "packaging", "jar"), local_properties),
        "parent": {key: _interpolate(_text(parent, key), local_properties) for key in ("groupId", "artifactId", "version")}
                   if parent is not None else None,
        "parent_relative_path": relative_parent, "modules": [m for m in modules if m],
        "properties": dict(sorted(local_properties.items())), "dependencies": dependencies,
        "plugins": plugins,
    }


def discover(root: Path) -> dict[str, Any]:
    """Discover a Maven reactor without invoking Maven or resolving artifacts."""
    root = root.resolve()
    pom = root / "pom.xml"
    if not pom.is_file():
        raise AnalysisError("Maven root pom.xml is unavailable")
    modules: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    seen: set[Path] = set()

    def visit(path: Path, inherited: dict[str, str]) -> None:
        path = path.resolve()
        if path in seen:
            diagnostics.append({"code": "MAVEN_MODULE_CYCLE", "path": path.relative_to(root).as_posix()})
            return
        try:
            path.relative_to(root)
        except ValueError:
            raise AnalysisError("Maven module escapes approved root")
        seen.add(path)
        model = _parse(path, root, inherited)
        modules.append(model)
        for declared in model["modules"]:
            child = (path.parent / declared / "pom.xml").resolve()
            if not child.is_file():
                diagnostics.append({"code": "MAVEN_MODULE_POM_MISSING", "module": declared,
                                    "parent": model["path"]})
            else:
                visit(child, model["properties"])

    visit(pom, {})
    return {"status": "SOURCE_ONLY_DECLARED_MODEL", "root": str(root), "root_pom": "pom.xml",
            "modules": sorted(modules, key=lambda item: item["path"]), "diagnostics": diagnostics,
            "effective_model": "UNAVAILABLE_WITHOUT_EXPLICIT_BUILD_EXPORT",
            "fingerprint": digest({"modules": modules, "diagnostics": diagnostics}),
            "limitations": ["Profiles, BOM mediation and dependency resolution are declarations only.",
                            "Use an explicit build plan/import for effective classpaths and fresh outputs."]}

