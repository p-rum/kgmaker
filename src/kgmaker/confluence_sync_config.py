"""Read-only live-connection settings; configuration never establishes a connection."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from typing import Mapping
from urllib.parse import urlsplit

from .analysis_model import AnalysisError, canonical

MAX_CONFIG_BYTES = 65_536
APIS = {"cloud-v1", "cloud-v2", "server-v1"}
ENVIRONMENT_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}\Z")


@dataclass(frozen=True)
class ConfluenceConnectionConfiguration:
    enabled: bool = False
    host: str | None = None
    api: str | None = None
    sandbox_space: str | None = None
    auth_kind: str | None = None
    token_env: str | None = None
    username_env: str | None = None


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AnalysisError("Confluence configuration contains duplicate JSON keys")
        result[key] = value
    return result


def _reject_constant(_value):
    raise AnalysisError("Confluence configuration must use strict JSON numeric values")


def _environment_name(value, field):
    if not isinstance(value, str) or not ENVIRONMENT_NAME.fullmatch(value):
        raise AnalysisError(f"Confluence {field} must name an environment variable")
    return value


def _connection(value) -> ConfluenceConnectionConfiguration:
    if not isinstance(value, dict):
        raise AnalysisError("Confluence connection must be an object")
    if set(value) - {"enabled", "host", "api", "sandbox_space", "auth"}:
        raise AnalysisError("Confluence connection contains unsupported settings; use auth references")
    enabled = value.get("enabled", False)
    if type(enabled) is not bool:
        raise AnalysisError("Confluence connection enabled must be boolean")
    host = value.get("host")
    if host is not None:
        if (not isinstance(host, str) or len(host) > 2048 or
                any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in host)):
            raise AnalysisError("Confluence host must be an absolute HTTP(S) base URL")
        try:
            parts = urlsplit(host)
            valid = (parts.scheme in {"http", "https"} and parts.hostname and
                     parts.username is None and parts.password is None and
                     not parts.query and not parts.fragment and parts.port != 0)
        except ValueError:
            valid = False
        if not valid:
            raise AnalysisError("Confluence host must be an absolute HTTP(S) base URL without credentials or query")
    api = value.get("api")
    if api is not None and (not isinstance(api, str) or api not in APIS):
        raise AnalysisError("Confluence api must be cloud-v1, cloud-v2 or server-v1")
    space = value.get("sandbox_space")
    if space is not None and (not isinstance(space, str) or not space.strip() or len(space) > 128 or
                              any(ord(c) < 32 for c in space)):
        raise AnalysisError("Confluence sandbox_space must be a non-empty bounded identifier")
    auth = value.get("auth")
    kind = token_env = username_env = None
    if auth is not None:
        if not isinstance(auth, dict) or set(auth) - {"kind", "token_env", "username_env"}:
            raise AnalysisError("Confluence auth accepts only kind and environment references")
        kind = auth.get("kind")
        if not isinstance(kind, str) or kind not in {"basic", "bearer"}:
            raise AnalysisError("Confluence auth kind must be basic or bearer")
        token_env = _environment_name(auth.get("token_env"), "token_env")
        if kind == "basic":
            username_env = _environment_name(auth.get("username_env"), "username_env")
        elif "username_env" in auth:
            raise AnalysisError("Confluence bearer auth must not declare username_env")
    if enabled and any(item is None for item in (host, api, space, kind)):
        raise AnalysisError("Enabled Confluence connection requires host, api, sandbox_space and auth references")
    return ConfluenceConnectionConfiguration(enabled, host, api, space, kind, token_env, username_env)


def load_connection_configuration(root: Path, config_file: Path | None = None) -> ConfluenceConnectionConfiguration:
    """Read the connection subsection alongside existing offline-export settings.

    Default precedence matches the existing JSON export configuration. An explicit
    missing or invalid file is an error and never falls back to another file.
    """
    candidates = (root / ".kgmaker/config.json", root / "kgmaker.json") if config_file is None else (
        config_file if config_file.is_absolute() else root / config_file,)
    for path in candidates:
        if config_file is None and not path.exists():
            continue
        try:
            with path.open("rb") as stream:
                raw = stream.read(MAX_CONFIG_BYTES + 1)
        except OSError:
            raise AnalysisError("Confluence configuration file is unavailable") from None
        if len(raw) > MAX_CONFIG_BYTES:
            raise AnalysisError("Confluence configuration exceeds the supported size")
        try:
            data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                              parse_constant=_reject_constant)
        except AnalysisError:
            raise
        except (ValueError, RecursionError):
            raise AnalysisError("Confluence configuration must be valid UTF-8 JSON within supported parser limits") from None
        if not isinstance(data, dict):
            raise AnalysisError("Confluence configuration root must be an object")
        current = data
        for key in ("documentation", "confluence"):
            current = current.get(key, {})
            if not isinstance(current, dict):
                raise AnalysisError("Confluence documentation configuration must be an object")
        if "connection" in current:
            return _connection(current["connection"])
    return ConfluenceConnectionConfiguration()


def connection_status(config: ConfluenceConnectionConfiguration,
                      *, environment: Mapping[str, str] | None = None) -> dict:
    """Report references and readiness, never their values or a live PASS."""
    environment = os.environ if environment is None else environment
    configured = all(item is not None for item in (config.host, config.api, config.sandbox_space, config.auth_kind))
    auth_ready = bool(config.token_env and environment.get(config.token_env))
    if config.auth_kind == "basic":
        auth_ready = auth_ready and bool(config.username_env and environment.get(config.username_env))
    return {"schema_version": 1, "configured": configured, "enabled": config.enabled,
            "host": config.host, "api": config.api, "sandbox_space": config.sandbox_space,
            "auth": {"kind": config.auth_kind, "token_env": config.token_env,
                     "username_env": config.username_env},
            "auth_ready": auth_ready, "live_status": "NOT_RUN"}


def register(sub):
    parser = sub.add_parser("confluence", help="explicit offline Confluence connection configuration")
    actions = parser.add_subparsers(dest="confluence_command", required=True)
    config = actions.add_parser("config", help="validate settings and show readiness without connecting")
    config.add_argument("--root", type=Path, default=Path.cwd())
    config.add_argument("--config-file", type=Path, help="explicit JSON configuration file")


def run(args):
    import sys
    try:
        config = load_connection_configuration(args.root.resolve(), args.config_file)
        print(canonical(connection_status(config)))
        return 0
    except AnalysisError as error:
        print(str(error), file=sys.stderr)
        return error.code
