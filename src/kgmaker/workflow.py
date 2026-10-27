"""Durable task/workflow state, kept separate from source-derived graph facts."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any

from .memory import VALIDATION_STATUSES, is_sensitive_path

SCHEMA_VERSION = 1
WORKFLOW_DIR = Path(".kgmaker/workflow")
TASKS_DIR = WORKFLOW_DIR / "tasks"
PACKETS_DIR = WORKFLOW_DIR / "packets"
DEFAULT_MAX_ITERATIONS = 3
MAX_ITERATIONS_LIMIT = 10
MAX_TITLE = 200
MAX_REQUEST = 8_000
MAX_SUMMARY = 2_000
MAX_NOTES = 2_000
MAX_STOP_REASON = 500
MAX_COMMAND = 200

STATUSES = ("intake", "analyze", "plan", "implement", "test", "review", "done", "failed", "blocked")
ACTIVE_STATUSES = ("intake", "analyze", "plan", "implement", "test", "review")
TERMINAL_STATUSES = ("done", "failed", "blocked")
ROLES = ("architect", "implementation", "test_expert", "review", "orchestrator")
ARTIFACT_STATUSES = ("completed", "failed", "blocked")
REVIEW_OVERALL = ("approve", "request_changes", "block")
FINDING_SEVERITIES = ("blocker", "major", "minor", "note")
FINDING_DISPOSITIONS = ("open", "resolved", "waived")
ROLE_PHASES = {
    "architect": {"analyze", "plan"},
    "implementation": {"implement"},
    "test_expert": {"test"},
    "review": {"review"},
    "orchestrator": set(ACTIVE_STATUSES),
}
TASK_FIELDS = {
    "schema_version", "id", "title", "request", "status", "iteration", "max_iterations",
    "base_commit", "head_commit", "worktree_fingerprint", "plan_revision",
    "accepted_paths", "artifact_ids", "stop_reason", "artifacts",
}
BASE_ARTIFACT_FIELDS = {
    "id", "task_id", "role", "phase", "iteration", "summary", "status",
    "cited_paths", "cited_node_ids", "packet_id", "disposition",
}
PLAN_ARTIFACT_FIELDS = BASE_ARTIFACT_FIELDS | {"steps", "out_of_scope"}
IMPLEMENTATION_ARTIFACT_FIELDS = BASE_ARTIFACT_FIELDS | {"changed_paths", "notes"}
TEST_ARTIFACT_FIELDS = BASE_ARTIFACT_FIELDS | {"validations"}
REVIEW_ARTIFACT_FIELDS = BASE_ARTIFACT_FIELDS | {"findings", "overall"}

_HEX_40 = re.compile(r"[0-9a-f]{40}")
_HEX_64 = re.compile(r"[0-9a-f]{64}")
_TASK_ID = re.compile(r"task:[0-9a-f]{64}")
_ARTIFACT_ID = re.compile(r"artifact:[0-9a-f]{64}")
_PACKET_ID = re.compile(r"packet:[0-9a-f]{64}")


class WorkflowError(ValueError):
    """A workflow task or artifact does not satisfy the persisted contract."""


def _canonical(record: dict[str, Any], exclude: set[str]) -> bytes:
    payload = {key: value for key, value in record.items() if key not in exclude}
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def task_id(title: str, request: str, max_iterations: int, base_commit: str | None) -> str:
    """Derive a stable task ID from the creation contract fields."""
    payload = {
        "title": title, "request": request, "max_iterations": max_iterations, "base_commit": base_commit,
    }
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()).hexdigest()
    return "task:" + digest


def artifact_id(record: dict[str, Any]) -> str:
    """Derive an artifact ID from persisted content, independent of key ordering."""
    return "artifact:" + hashlib.sha256(_canonical(record, {"id"})).hexdigest()


def packet_id(record: dict[str, Any]) -> str:
    """Derive a packet ID from packet content excluding estimate fields."""
    return "packet:" + hashlib.sha256(_canonical(record, {"packet_id", "token_estimate"})).hexdigest()


def _safe_path(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise WorkflowError(f"{field} must be a non-empty repository-relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value != path.as_posix():
        raise WorkflowError(f"{field} must be a safe repository-relative path")
    if is_sensitive_path(value):
        raise WorkflowError(f"{field} must not cite a sensitive path")
    return value


def _string_list(value: Any, field: str, limit: int = 200, item_limit: int = 500) -> list[str]:
    if not isinstance(value, list) or len(value) > limit or any(
        not isinstance(item, str) or not item or len(item) > item_limit for item in value
    ):
        raise WorkflowError(f"{field} must be a bounded array of non-empty strings")
    if len(set(value)) != len(value):
        raise WorkflowError(f"{field} must not contain duplicates")
    return value


def _bounded_text(value: Any, field: str, limit: int, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or len(value) > limit:
        raise WorkflowError(f"{field} must be text no longer than {limit} characters")
    if not allow_empty and not value.strip():
        raise WorkflowError(f"{field} must be non-empty text")
    return value


def _git_head(root: Path) -> str | None:
    toplevel = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )
    if toplevel.returncode:
        return None
    try:
        if Path(toplevel.stdout.strip()).resolve() != root.resolve():
            return None
    except OSError:
        return None
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )
    value = result.stdout.strip()
    return value if result.returncode == 0 and _HEX_40.fullmatch(value) else None


def _non_negative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise WorkflowError(f"{field} must be a non-negative integer")
    return value


def _artifact_fields(role: str, phase: str) -> set[str]:
    if role == "architect" and phase == "plan":
        return PLAN_ARTIFACT_FIELDS
    if role == "implementation":
        return IMPLEMENTATION_ARTIFACT_FIELDS
    if role == "test_expert":
        return TEST_ARTIFACT_FIELDS
    if role == "review":
        return REVIEW_ARTIFACT_FIELDS
    return BASE_ARTIFACT_FIELDS


def _validate_plan_steps(steps: Any, field: str) -> list[dict[str, Any]]:
    if not isinstance(steps, list) or not steps or len(steps) > 50:
        raise WorkflowError(f"{field} must be a bounded non-empty array")
    seen: set[str] = set()
    validated: list[dict[str, Any]] = []
    for index, item in enumerate(steps):
        prefix = f"{field}[{index}]"
        if not isinstance(item, dict) or set(item) != {"id", "intent", "paths", "tests"}:
            raise WorkflowError(f"{prefix} must contain id, intent, paths, and tests")
        step_id = _bounded_text(item["id"], f"{prefix}.id", 80)
        if step_id in seen:
            raise WorkflowError(f"{prefix}.id must be unique")
        seen.add(step_id)
        _bounded_text(item["intent"], f"{prefix}.intent", 500)
        paths = [_safe_path(path, f"{prefix}.paths") for path in _string_list(item["paths"], f"{prefix}.paths", 50)]
        tests = [_safe_path(path, f"{prefix}.tests") for path in _string_list(item["tests"], f"{prefix}.tests", 50)]
        validated.append({"id": step_id, "intent": item["intent"], "paths": paths, "tests": tests})
    return validated


def _validate_validations(values: Any, field: str) -> list[dict[str, str]]:
    if not isinstance(values, list) or not values or len(values) > 100:
        raise WorkflowError(f"{field} must be a bounded non-empty array")
    labels: set[str] = set()
    result: list[dict[str, str]] = []
    for index, item in enumerate(values):
        prefix = f"{field}[{index}]"
        if not isinstance(item, dict) or set(item) != {"label", "status", "command"}:
            raise WorkflowError(f"{prefix} must contain label, status, and command")
        label = item["label"]
        if not isinstance(label, str) or not label or len(label) > 80 or label in labels:
            raise WorkflowError(f"{prefix}.label must be unique bounded text")
        labels.add(label)
        if item["status"] not in VALIDATION_STATUSES:
            raise WorkflowError(f"{prefix}.status is unsupported")
        _bounded_text(item["command"], f"{prefix}.command", MAX_COMMAND)
        result.append({"label": label, "status": item["status"], "command": item["command"]})
    return result


def _validate_findings(values: Any, field: str) -> list[dict[str, Any]]:
    if not isinstance(values, list) or len(values) > 100:
        raise WorkflowError(f"{field} must be a bounded array")
    findings: list[dict[str, Any]] = []
    for index, item in enumerate(values):
        prefix = f"{field}[{index}]"
        if not isinstance(item, dict) or set(item) != {"severity", "path", "summary", "disposition"}:
            raise WorkflowError(f"{prefix} must contain severity, path, summary, and disposition")
        if item["severity"] not in FINDING_SEVERITIES:
            raise WorkflowError(f"{prefix}.severity is unsupported")
        path = item["path"]
        if path is not None:
            path = _safe_path(path, f"{prefix}.path")
        _bounded_text(item["summary"], f"{prefix}.summary", 500)
        if item["disposition"] not in FINDING_DISPOSITIONS:
            raise WorkflowError(f"{prefix}.disposition is unsupported")
        findings.append({
            "severity": item["severity"], "path": path,
            "summary": item["summary"], "disposition": item["disposition"],
        })
    return findings


def validate_artifact(record: Any, index: int | None = None) -> dict[str, Any]:
    """Validate one role artifact without mixing it into the semantic graph."""
    prefix = f"artifacts[{index}]" if index is not None else "artifact"
    if not isinstance(record, dict):
        raise WorkflowError(f"{prefix} must be an object")
    role = record.get("role")
    phase = record.get("phase")
    if role not in ROLES:
        raise WorkflowError(f"{prefix}.role is unsupported")
    if phase not in ACTIVE_STATUSES:
        raise WorkflowError(f"{prefix}.phase is unsupported")
    if phase not in ROLE_PHASES[role]:
        raise WorkflowError(f"{prefix} role {role} cannot record phase {phase}")
    expected_fields = _artifact_fields(role, phase)
    if set(record) != expected_fields:
        raise WorkflowError(f"{prefix} must contain exactly the {role} artifact fields")
    if not isinstance(record["task_id"], str) or not _TASK_ID.fullmatch(record["task_id"]):
        raise WorkflowError(f"{prefix}.task_id must be a task SHA-256 id")
    _non_negative_int(record["iteration"], f"{prefix}.iteration")
    _bounded_text(record["summary"], f"{prefix}.summary", MAX_SUMMARY)
    if record["status"] not in ARTIFACT_STATUSES:
        raise WorkflowError(f"{prefix}.status is unsupported")
    cited_paths = [_safe_path(path, f"{prefix}.cited_paths") for path in _string_list(record["cited_paths"], f"{prefix}.cited_paths")]
    _string_list(record["cited_node_ids"], f"{prefix}.cited_node_ids")
    packet = record["packet_id"]
    if packet is not None and (not isinstance(packet, str) or not _PACKET_ID.fullmatch(packet)):
        raise WorkflowError(f"{prefix}.packet_id must be a packet SHA-256 id or null")
    disposition = record["disposition"]
    if disposition is not None and (not isinstance(disposition, str) or not disposition or len(disposition) > 80):
        raise WorkflowError(f"{prefix}.disposition must be bounded text or null")

    if expected_fields is PLAN_ARTIFACT_FIELDS:
        _validate_plan_steps(record["steps"], f"{prefix}.steps")
        [_safe_path(path, f"{prefix}.out_of_scope") for path in _string_list(record["out_of_scope"], f"{prefix}.out_of_scope")]
    elif expected_fields is IMPLEMENTATION_ARTIFACT_FIELDS:
        [_safe_path(path, f"{prefix}.changed_paths") for path in _string_list(record["changed_paths"], f"{prefix}.changed_paths")]
        _bounded_text(record["notes"], f"{prefix}.notes", MAX_NOTES, allow_empty=True)
    elif expected_fields is TEST_ARTIFACT_FIELDS:
        _validate_validations(record["validations"], f"{prefix}.validations")
    elif expected_fields is REVIEW_ARTIFACT_FIELDS:
        _validate_findings(record["findings"], f"{prefix}.findings")
        if record["overall"] not in REVIEW_OVERALL:
            raise WorkflowError(f"{prefix}.overall is unsupported")

    expected = artifact_id(record)
    if record["id"] != expected:
        raise WorkflowError(f"{prefix}.id must be `{expected}`")
    record["cited_paths"] = cited_paths
    return record


def validate_task(record: Any) -> dict[str, Any]:
    """Validate a persisted task document, including append-only artifacts."""
    if not isinstance(record, dict):
        raise WorkflowError("task must be an object")
    version = record.get('schema_version')
    fields = TASK_FIELDS | ({'delivery'} if version == 2 else set())
    if set(record) != fields:
        raise WorkflowError("task must contain exactly the workflow contract fields")
    if type(version) is not int or version not in {1, 2}:
        raise WorkflowError('task must use schema_version 1 or 2')
    if version == 2:
        delivery = record['delivery']
        if not isinstance(delivery, dict) or set(delivery) != {'schema_version','bindings'} or delivery['schema_version'] != 1 or not isinstance(delivery['bindings'], dict):
            raise WorkflowError('Invalid task delivery metadata')
        for identifier, binding in delivery['bindings'].items():
            if identifier not in record['artifact_ids'] or not isinstance(binding,dict) or set(binding) != {'head_commit','source_fingerprint'} or not isinstance(binding['source_fingerprint'],str) or not _HEX_64.fullmatch(binding['source_fingerprint']):
                raise WorkflowError('Invalid artifact content binding')
            if binding['head_commit'] is not None and not _HEX_40.fullmatch(str(binding['head_commit'])):
                raise WorkflowError('Invalid artifact head binding')
    title = _bounded_text(record["title"], "title", MAX_TITLE)
    request = _bounded_text(record["request"], "request", MAX_REQUEST)
    if record["status"] not in STATUSES:
        raise WorkflowError("status is unsupported")
    iteration = _non_negative_int(record["iteration"], "iteration")
    max_iterations = record["max_iterations"]
    if (isinstance(max_iterations, bool) or not isinstance(max_iterations, int)
            or max_iterations < 1 or max_iterations > MAX_ITERATIONS_LIMIT):
        raise WorkflowError(f"max_iterations must be an integer from 1 to {MAX_ITERATIONS_LIMIT}")
    if iteration > max_iterations:
        raise WorkflowError("iteration cannot exceed max_iterations")
    for field in ("base_commit", "head_commit"):
        value = record[field]
        if value is not None and (not isinstance(value, str) or not _HEX_40.fullmatch(value)):
            raise WorkflowError(f"{field} must be a lowercase 40-character Git SHA or null")
    fingerprint = record["worktree_fingerprint"]
    if fingerprint is not None and (not isinstance(fingerprint, str) or not _HEX_64.fullmatch(fingerprint)):
        raise WorkflowError("worktree_fingerprint must be a lowercase SHA-256 or null")
    _non_negative_int(record["plan_revision"], "plan_revision")
    accepted = [_safe_path(path, "accepted_paths") for path in _string_list(record["accepted_paths"], "accepted_paths")]
    artifact_ids = _string_list(record["artifact_ids"], "artifact_ids", limit=500, item_limit=80)
    for item in artifact_ids:
        if not _ARTIFACT_ID.fullmatch(item):
            raise WorkflowError("artifact_ids must contain artifact SHA-256 ids")
    stop_reason = record["stop_reason"]
    if stop_reason is not None:
        _bounded_text(stop_reason, "stop_reason", MAX_STOP_REASON)
    if record["status"] in TERMINAL_STATUSES and not stop_reason and record["status"] != "done":
        raise WorkflowError("failed and blocked tasks require stop_reason")
    if record["status"] == "done" and stop_reason is not None:
        raise WorkflowError("done tasks must not set stop_reason")
    artifacts = record["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) > 500:
        raise WorkflowError("artifacts must be a bounded array")
    seen: list[str] = []
    for index, item in enumerate(artifacts):
        artifact = validate_artifact(item, index)
        if artifact["task_id"] != record["id"]:
            raise WorkflowError(f"artifacts[{index}].task_id must match the parent task")
        seen.append(artifact["id"])
    if seen != artifact_ids:
        raise WorkflowError("artifact_ids must match artifacts in order")
    expected = task_id(title, request, max_iterations, record["base_commit"])
    if record["id"] != expected:
        raise WorkflowError(f"id must be `{expected}`")
    record["accepted_paths"] = accepted
    return record


def legal_transitions(task: dict[str, Any]) -> list[str]:
    """Return the statuses a task may advance to from its current state."""
    status = task["status"]
    if status not in ACTIVE_STATUSES:
        return []
    allowed = {
        "intake": ["analyze"],
        "analyze": ["plan"],
        "plan": ["implement"],
        "implement": ["test"],
        "test": ["review"],
        "review": ["done"],
    }[status]
    can_retry = task["iteration"] + 1 < task["max_iterations"]
    if status == "test":
        allowed.append("failed")
        if can_retry:
            allowed.append("implement")
    elif status == "review":
        allowed.append("blocked")
        if can_retry:
            allowed.append("implement")
    return allowed


def create_task(
    root: Path,
    request: str,
    title: str | None = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> dict[str, Any]:
    """Create an intake task bound to HEAD when the root is a Git repository."""
    if not isinstance(request, str) or not request.strip() or len(request) > MAX_REQUEST:
        raise WorkflowError(f"request must be non-empty text no longer than {MAX_REQUEST} characters")
    request = request.strip()
    if title is None:
        title = re.sub(r"\s+", " ", request.splitlines()[0]).strip()[:MAX_TITLE]
    title = _bounded_text(title, "title", MAX_TITLE)
    if (isinstance(max_iterations, bool) or not isinstance(max_iterations, int)
            or max_iterations < 1 or max_iterations > MAX_ITERATIONS_LIMIT):
        raise WorkflowError(f"max_iterations must be an integer from 1 to {MAX_ITERATIONS_LIMIT}")
    base_commit = _git_head(root)
    record = {
        "schema_version": SCHEMA_VERSION,
        "id": task_id(title, request, max_iterations, base_commit),
        "title": title,
        "request": request,
        "status": "intake",
        "iteration": 0,
        "max_iterations": max_iterations,
        "base_commit": base_commit,
        "head_commit": None,
        "worktree_fingerprint": None,
        "plan_revision": 0,
        "accepted_paths": [],
        "artifact_ids": [],
        "stop_reason": None,
        "artifacts": [],
    }
    return validate_task(record)


def normalize_task_id(value: str) -> str:
    """Accept `task:<hex>`, `task-<hex>`, or a bare 64-character digest."""
    if not isinstance(value, str) or not value.strip():
        raise WorkflowError("task id is required")
    raw = value.strip()
    if _TASK_ID.fullmatch(raw):
        return raw
    if raw.startswith("task-") and _HEX_64.fullmatch(raw[5:]):
        return "task:" + raw[5:]
    if _HEX_64.fullmatch(raw):
        return "task:" + raw
    raise WorkflowError("task id must be a task SHA-256 id")


def task_path(root: Path, task_id_value: str) -> Path:
    identifier = normalize_task_id(task_id_value)
    return root / TASKS_DIR / f"{identifier.replace(':', '-')}.json"


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temporary.replace(path)
    except OSError:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def save_task(root: Path, task: dict[str, Any], *, expected_revision: str | None = None) -> Path:
    """Atomically persist a validated task document."""
    validated = validate_task(task)
    path = task_path(root, validated["id"])
    from .provenance import enforce_gate, transaction
    from .analysis_model import AnalysisError, digest
    try:
        with transaction(root):
            if expected_revision is not None:
                if not path.exists() or digest(load_task(root,validated['id'])) != expected_revision:
                    raise WorkflowError('Task changed concurrently; reload before writing')
            _atomic_write(path, validated)
    except AnalysisError as exc:
        raise WorkflowError(str(exc)) from exc
    return path


def load_task(root: Path, task_id_value: str) -> dict[str, Any]:
    path = task_path(root, task_id_value)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise WorkflowError(f"task is missing or unreadable: {error}") from None
    return validate_task(data)


def list_tasks(root: Path, status: str | None = None) -> list[dict[str, Any]]:
    """Load readable tasks, optionally filtered by status."""
    if status is not None and status not in STATUSES:
        raise WorkflowError("status is unsupported")
    directory = root / TASKS_DIR
    if not directory.is_dir():
        return []
    tasks: list[dict[str, Any]] = []
    for path in sorted(directory.glob("task-*.json")):
        try:
            task = validate_task(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, UnicodeError, json.JSONDecodeError, WorkflowError):
            continue
        if status is None or task["status"] == status:
            tasks.append(task)
    return tasks


def add_task(
    root: Path,
    request: str,
    title: str | None = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> dict[str, Any]:
    """Create or return the existing intake task for the same creation contract."""
    task = create_task(root, request, title=title, max_iterations=max_iterations)
    path = task_path(root, task["id"])
    if path.exists():
        return load_task(root, task["id"])
    save_task(root, task)
    return task


def advance_task(root: Path, task_id_value: str, target: str) -> dict[str, Any]:
    """Move a task to a legally reachable status and persist the result."""
    task = load_task(root, task_id_value)
    from .analysis_model import digest
    expected_revision = digest(task)
    if target not in STATUSES:
        raise WorkflowError("status is unsupported")
    allowed = legal_transitions(task)
    if target not in allowed:
        raise WorkflowError(f"cannot advance from {task['status']} to {target}")
    if target == "implement" and task["status"] in {"test", "review"}:
        task["iteration"] = task["iteration"] + 1
    task["status"] = target
    if target == "failed":
        task["stop_reason"] = task["stop_reason"] or "advanced to failed"
    elif target == "blocked":
        task["stop_reason"] = task["stop_reason"] or "advanced to blocked"
    elif target == "done":
        task["stop_reason"] = None
    save_task(root, task, expected_revision=expected_revision)
    return task


def stop_task(root: Path, task_id_value: str, reason: str) -> dict[str, Any]:
    """Mark a non-terminal task failed with a bounded stop reason."""
    task = load_task(root, task_id_value)
    from .analysis_model import digest
    expected_revision = digest(task)
    if task["status"] in TERMINAL_STATUSES:
        raise WorkflowError("cannot stop a terminal task")
    task["status"] = "failed"
    task["stop_reason"] = _bounded_text(reason, "stop_reason", MAX_STOP_REASON)
    save_task(root, task, expected_revision=expected_revision)
    return task


def _merge_paths(existing: list[str], extra: list[str]) -> list[str]:
    merged = list(existing)
    seen = set(existing)
    for path in extra:
        if path not in seen:
            merged.append(path)
            seen.add(path)
    return merged


def packet_path(root: Path, task: dict[str, Any], role: str, iteration: int) -> Path:
    """Return the generated packet path for a task role iteration."""
    slug = task["id"].replace(":", "-")
    return root / PACKETS_DIR / f"{slug}-{role}-{iteration}.json"


def record_artifact(root: Path, task_id_value: str, role: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Append a validated role artifact and persist the parent task."""
    task = load_task(root, task_id_value)
    from .analysis_model import digest
    expected_revision = digest(task)
    if task["status"] in TERMINAL_STATUSES:
        raise WorkflowError("cannot record artifacts on a terminal task")
    if role not in ROLES:
        raise WorkflowError("role is unsupported")
    record = dict(payload)
    record.setdefault("task_id", task["id"])
    record.setdefault("role", role)
    record.setdefault("phase", task["status"])
    record.setdefault("iteration", task["iteration"])
    if record.get("role") != role:
        raise WorkflowError("artifact role must match the requested role")
    if record.get("task_id") != task["id"]:
        raise WorkflowError("artifact task_id must match the parent task")
    if record.get("iteration") != task["iteration"]:
        raise WorkflowError("artifact iteration must match the current task iteration")
    if "id" not in record:
        record["id"] = artifact_id(record)
    artifact = validate_artifact(record)
    if artifact["id"] in task["artifact_ids"]:
        return task
    if artifact["packet_id"] is not None:
        prepared = packet_path(root, task, artifact["role"], artifact["iteration"])
        try:
            packet = json.loads(prepared.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise WorkflowError(f"packet is missing or unreadable: {error}") from None
        if packet.get("packet_id") != artifact["packet_id"]:
            raise WorkflowError("artifact packet_id does not match the prepared packet")
        if packet.get("task_id") != task["id"] or packet.get("role") != artifact["role"]:
            raise WorkflowError("artifact packet does not belong to this task role")
        if packet.get("iteration") != artifact["iteration"]:
            raise WorkflowError("artifact packet iteration does not match the artifact")
    if artifact['phase'] in {'implement', 'review'}:
        from .feature import source_inventory
        from .analysis_model import digest
        task['head_commit'] = _git_head(root)
        task['worktree_fingerprint'] = digest(source_inventory(root)[0])
        task['schema_version'] = 2
        task.setdefault('delivery', {'schema_version':1, 'bindings':{}})
        task['delivery']['bindings'][artifact['id']] = {
            'head_commit':task['head_commit'], 'source_fingerprint':task['worktree_fingerprint']}
    task["artifacts"] = [*task["artifacts"], artifact]
    task["artifact_ids"] = [*task["artifact_ids"], artifact["id"]]
    if artifact["role"] == "architect" and artifact["phase"] == "plan":
        task["plan_revision"] = task["plan_revision"] + 1
        step_paths = [path for step in artifact["steps"] for path in step["paths"]]
        task["accepted_paths"] = _merge_paths(task["accepted_paths"], step_paths)
    elif artifact["role"] == "implementation":
        task["accepted_paths"] = _merge_paths(task["accepted_paths"], artifact["changed_paths"])
    save_task(root, task, expected_revision=expected_revision)
    return task
