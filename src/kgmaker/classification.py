"""Versioned conservative classification; no build script is executed here.

Build memberships describe compiler inputs, not deployment. Overrides change
projections, never compiler facts. Rules retain conflicts for CI and review.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .analysis_model import AnalysisError, digest, read_json, safe_path

VERSION = "classification-1"
SCOPES = {"production", "test", "test_fixture", "development", "unknown"}
ROLES = {"executable_code", "configuration", "migration", "contract", "documentation", "resource", "unknown"}
ORIGINS = {"handwritten", "generated", "dependency", "unknown"}


@dataclass(frozen=True)
class Classification:
    scope: str
    role: str
    origin: str
    build_membership: tuple[str, ...]
    classification_evidence: tuple[str, ...]


class Classifier:
    def __init__(self, root: Path, model: dict | None = None, strict: bool = False):
        self.root, self.strict = root, strict
        self.diagnostics: list[dict] = []
        path = safe_path(root, ".kgmaker/classification.json")
        self.config = read_json(path) if path.exists() else {"schema_version": 1, "overrides": []}
        if not isinstance(self.config, dict) or type(self.config.get("schema_version")) is not int or self.config["schema_version"] != 1:
            raise AnalysisError("classification overrides must use schema_version 1")
        if set(self.config) - {"schema_version", "overrides"} or not isinstance(self.config.get("overrides"), list):
            raise AnalysisError("invalid classification override contract")
        for rule in self.config["overrides"]:
            if not isinstance(rule, dict) or set(rule) - {"path", "scope", "role", "origin", "reason"}:
                raise AnalysisError("invalid classification override")
            if not isinstance(rule.get("reason"), str) or not rule["reason"].strip():
                raise AnalysisError("classification override requires a reason")
            safe_path(root, rule.get("path"))
            for key, allowed in (("scope", SCOPES), ("role", ROLES), ("origin", ORIGINS)):
                if key in rule and rule[key] not in allowed:
                    raise AnalysisError("invalid classification " + key)
        self.model = model or {"source_sets": []}
        if not isinstance(self.model.get("source_sets"), list):
            raise AnalysisError("source_sets must be a list")
        for source in self.model["source_sets"]:
            if not isinstance(source, dict) or not all(isinstance(source.get(k), str) and source[k] for k in ("id", "module", "scope")) or source["scope"] not in SCOPES:
                raise AnalysisError("source set requires id, module and valid scope")
            if (not isinstance(source.get("roots", []), list) or not isinstance(source.get("files", []), list)
                    or ("generated" in source and type(source["generated"]) is not bool)):
                raise AnalysisError("source set roots/files must be lists")
            for value in source.get("roots", []) + source.get("files", []):
                safe_path(root, value)
        self.fingerprint = digest({"version": VERSION, "overrides": self.config, "model": self.model})

    def classify(self, path: str) -> Classification:
        p = PurePosixPath(path)
        parts = tuple(x.lower() for x in p.parts)
        name, suffix = p.name.lower(), p.suffix.lower()
        evidence = [VERSION + ":path-convention:" + path]
        memberships = []
        scopes = set()
        origin = "unknown"
        for source in self.model["source_sets"]:
            if path in source.get("files", []) or any(path == r or path.startswith(r.rstrip("/") + "/") for r in source.get("roots", [])):
                memberships.append(source["module"] + ":" + source["id"])
                scopes.add(source["scope"])
                evidence.append("supplied-source-set:" + source["module"] + ":" + source["id"])
                if source.get("generated") is True:
                    origin = "generated"
        if suffix in {".md", ".mdx", ".rst", ".html"}:
            role = "documentation"
        elif suffix == ".sql" and any(x in parts for x in ("migration", "migrations")):
            role = "migration"
        elif "openapi" in name or "contract" in parts or "contracts" in parts:
            role = "contract"
        elif suffix in {".yaml", ".yml", ".properties", ".toml", ".xml", ".json", ".kts"}:
            role = "configuration"
        elif suffix in {".py", ".kt", ".java", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".mjs", ".cjs"}:
            role = "executable_code"
        else:
            role = "resource"
        if any(x in parts for x in ("testfixtures", "test-fixtures", "test_fixture", "fixtures", "__fixtures__")):
            scope = "test_fixture"
        elif any(x in parts for x in ("test", "tests", "integrationtest", "__tests__", "e2e", "mock", "mocks", "__mocks__")) or any(x in name for x in (".test.", ".spec.")) or name.startswith("test_") or (suffix in {".java", ".kt"} and p.stem.endswith(("Test", "Tests"))):
            scope = "test"
        elif any(x in parts for x in ("development", "dev", "examples", "scripts")):
            scope = "development"
        elif "main" in parts or (parts and parts[0] in {"src", "app", "pages", "lib"}):
            scope = "production"
        else:
            scope = "unknown"
        conventional = scope
        if scopes:
            scope = next(iter(scopes)) if len(scopes) == 1 else "unknown"
            if len(scopes) > 1 or (scope == "production" and conventional in {"test", "test_fixture"}):
                self.diagnostics.append({"path": path, "code": "BUILD_SCOPE_CONFLICT", "scopes": sorted(scopes), "convention": conventional})
        if any(x in parts for x in ("generated", "generated-sources", "generatedsources")):
            origin = "generated"
        if origin == "unknown" and memberships:
            origin = "handwritten"
        for rule in self.config["overrides"]:
            if path == rule["path"] or path.startswith(rule["path"].rstrip("/") + "/"):
                if "scope" in rule and scopes and scopes != {rule["scope"]}:
                    self.diagnostics.append({"path": path, "code": "OVERRIDE_BUILD_CONFLICT", "scopes": sorted(scopes), "override": rule["scope"], "reason": rule["reason"]})
                scope, role, origin = rule.get("scope", scope), rule.get("role", role), rule.get("origin", origin)
                evidence.append("override:" + rule["path"] + ":" + rule["reason"])
        if self.strict and any(d["path"] == path for d in self.diagnostics):
            raise AnalysisError("strict classification conflict: " + path, 4)
        return Classification(scope, role, origin, tuple(sorted(memberships)), tuple(evidence))
