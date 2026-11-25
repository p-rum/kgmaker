"""Create-only Jira Cloud CSV projection from a validated Kotlin/JVM plan."""

from __future__ import annotations

import csv
import io
import math
from collections import defaultdict

from ..analysis_model import AnalysisError, digest
from .plan import array, identity, location, object_fields, task_description, text

DEFAULT = {
    "schema_version": 1,
    "kind": "jira-task",
    "jira": "cloud",
    "work_types": {"epic": "Epic", "task": "Task"},
    "headers": {
        "summary": "Summary", "description": "Description", "type": "Work Type",
        "id": "Work item ID", "parent": "Parent", "blocks": "Blocks",
    },
    "fields": [{
        "field": "Labels", "type": "multi-select", "constant": ["excel-migration"],
        "applies_to": "all",
    }],
}
SYSTEM_TARGETS = {
    "summary": "Summary", "description": "Description", "type": "Work Type",
    "id": "Work item ID", "parent": "Parent", "blocks": "blocks (outward link)",
}
FIELD_TYPES = {"text", "paragraph", "number", "select", "multi-select", "account-id"}
USER_FIELDS = {"assignee", "reporter"}
RESERVED_TARGETS = {name.casefold() for name in SYSTEM_TARGETS.values()} | {
    "issue id", "issue key", "work item key", "issue type", "parent id", "epic link", "blocks",
}


def _single_line(value, field, limit=255):
    value = text(value, field, limit)
    if any(char in value for char in "\r\n\t") or value.startswith(("=", "+", "-", "@")):
        raise AnalysisError(f"{field} must be a single line of text suitable for Jira CSV")
    return value


def template(raw):
    fields = {"schema_version", "kind", "jira", "work_types", "headers", "fields"}
    object_fields(raw, fields, set(), "Jira template")
    if raw["schema_version"] != 1 or raw["kind"] != "jira-task" or raw["jira"] != "cloud":
        raise AnalysisError("Expected a Jira Cloud jira-task template v1")
    work_types = object_fields(raw["work_types"], set(DEFAULT["work_types"]), set(), "Jira work types")
    work_types = {key: _single_line(value, f"Jira {key} type", 60) for key, value in work_types.items()}
    if len({value.casefold() for value in work_types.values()}) != len(work_types):
        raise AnalysisError("Jira Epic and Task work types must be distinct")
    headers = object_fields(raw["headers"], set(DEFAULT["headers"]), set(), "Jira headers")
    headers = {key: _single_line(value, f"Jira {key} header") for key, value in headers.items()}
    seen_headers = {value.casefold() for value in headers.values()}
    if len(seen_headers) != len(headers):
        raise AnalysisError("Jira headers must be unique across fields")
    seen_targets = set(RESERVED_TARGETS)
    columns = []
    for raw_field in array(raw["fields"], "Jira fields", 35):
        required = {"field", "type"}
        allowed = {"header", "source", "constant", "required", "allowed_values", "applies_to"}
        value = object_fields(raw_field, required, allowed, "Jira field")
        name = _single_line(value["field"], "Jira field name")
        header = _single_line(value.get("header", name), f"Jira {name} header")
        kind = value["type"]
        applies_to = value.get("applies_to", "task")
        if name.casefold() in seen_targets or header.casefold() in seen_headers:
            raise AnalysisError(f"Duplicate or reserved Jira field or header: {name}")
        if (not isinstance(kind, str) or kind not in FIELD_TYPES
                or applies_to not in ("epic", "task", "all")
                or type(value.get("required", False)) is not bool
                or ("source" in value) == ("constant" in value)):
            raise AnalysisError(f"Invalid Jira field configuration: {name}")
        if name.casefold() in USER_FIELDS and kind != "account-id":
            raise AnalysisError(f"Jira {name} requires the account-id field type")
        field = {**value, "field": name, "header": header, "applies_to": applies_to}
        if "source" in value:
            source = value["source"]
            if source not in ("id", "title", "target", "kind"):
                if not isinstance(source, str) or not source.startswith("jira_fields."):
                    raise AnalysisError(f"Unknown Jira field source for {name}")
                identity(source.removeprefix("jira_fields."), f"Jira {name} source key")
            if kind == "account-id" and (not isinstance(source, str) or not source.startswith("jira_fields.")):
                raise AnalysisError(f"Jira {name} requires an explicitly supplied account ID")
        if "allowed_values" in value:
            if kind not in {"select", "multi-select"}:
                raise AnalysisError(f"Jira allowed_values requires a select field: {name}")
            options = [_single_line(item, f"Jira {name} option")
                       for item in array(value["allowed_values"], f"Jira {name} options", 200, nonempty=True)]
            if len(options) != len(set(options)):
                raise AnalysisError(f"Jira {name} options must be unique")
            field["allowed_values"] = options
        if "constant" in value:
            _values(field, value["constant"], "template")
        seen_targets.add(name.casefold())
        seen_headers.add(header.casefold())
        columns.append(field)
    return {**raw, "work_types": work_types, "headers": headers, "fields": columns}


def _values(field, value, task):
    name, kind = field["field"], field["type"]
    label = f"{task} Jira field {name}"
    if value is None or value == "" or value == []:
        if field.get("required", False):
            raise AnalysisError(f"{label} is required")
        return []
    if kind == "number":
        if type(value) not in {int, float} or (type(value) is float and not math.isfinite(value)):
            raise AnalysisError(f"{label} requires a number")
        return [value]
    if kind == "multi-select":
        result = [_single_line(item, label) for item in array(value, label, 25)]
    elif kind in {"text", "paragraph"}:
        limit = 30_000 if kind == "paragraph" else 255
        if name.casefold() in {"priority", "status"}:
            limit = 60
        result = [text(value, label, limit)]
        if result[0].startswith(("=", "+", "-", "@")):
            raise AnalysisError(f"{label} starts with a spreadsheet formula marker")
    else:
        result = [_single_line(value, label, 60 if name.casefold() in {"priority", "status"} else 255)]
    if kind == "account-id" and any(char.isspace() or char == "@" for char in result[0]):
        raise AnalysisError(f"{label} requires an Atlassian account ID")
    if "allowed_values" in field and set(result) - set(field["allowed_values"]):
        raise AnalysisError(f"{label} contains a value outside the Jira template options")
    if len(result) != len(set(result)):
        raise AnalysisError(f"{label} contains a duplicate value")
    return result


def _source(field, row):
    if "constant" in field:
        return field["constant"]
    source = field["source"]
    if source.startswith("jira_fields."):
        return row["jira_fields"].get(source.removeprefix("jira_fields."))
    return row.get(source)


def render(inventory, plan, profile):
    profile = template(profile)
    evidence = {item["id"]: item for item in inventory["evidence"]}
    epic = {"id": "migration-epic", "kind": "epic", "title": plan["title"],
            "target": "Kotlin/JVM", "jira_fields": plan["jira_fields"]}
    tasks = plan["tasks"]
    ids = {row["id"]: index for index, row in enumerate([epic, *tasks], 1)}
    blocks = defaultdict(list)
    for task in tasks:
        for prerequisite in task["depends_on"]:
            blocks[prerequisite].append(ids[task["id"]])
    descriptions = ["Kotlin/JVM migration", f"Inventory {inventory['inventory_id']} · {inventory['status']}"]
    descriptions.extend(f"{key.capitalize()} — {value}" for key, value in plan["architecture"].items())
    descriptions.extend(f"Deferred [{row['id']}] ({location(evidence[row['id']])}) — {row['reason']}"
                        for row in plan["deferred"])
    rows = []
    for row in [epic, *tasks]:
        role = "epic" if row is epic else "task"
        description = "\n\n".join(descriptions) if row is epic else task_description(row, evidence)
        if len(description) > 30_000:
            raise AnalysisError(f"{row['id']} Jira Description exceeds 30000 characters")
        base = [_single_line(row["title"], f"{row['id']} Summary"), description,
                profile["work_types"][role], ids[row["id"]], "" if row is epic else ids[epic["id"]]]
        values = []
        for field in profile["fields"]:
            values.append(_values(field, _source(field, row), row["id"])
                          if field["applies_to"] in {role, "all"} else [])
        rows.append((base, sorted(blocks[row["id"]]), values))

    fields = ["summary", "description", "type", "id", "parent"]
    headings = [(profile["headers"][key], SYSTEM_TARGETS[key]) for key in fields]
    block_width = max((len(row[1]) for row in rows), default=0)
    headings.extend([(profile["headers"]["blocks"], SYSTEM_TARGETS["blocks"])] * block_width)
    widths = [max(1, *(len(row[2][index]) for row in rows)) for index, _ in enumerate(profile["fields"])]
    for field, width in zip(profile["fields"], widths):
        headings.extend([(field["header"], field["field"])] * width)
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow([header for header, _ in headings])
    for base, links, values in rows:
        flattened = base + links + [""] * (block_width - len(links))
        for items, width in zip(values, widths):
            flattened.extend(items + [""] * (width - len(items)))
        writer.writerow(flattened)
    return output.getvalue(), {
        "rows": len(rows),
        "template_sha256": digest(profile),
        "mapping": [{"column": index, "header": header, "jira_field": target}
                    for index, (header, target) in enumerate(headings, 1)],
        "importer": "Jira Cloud External system import",
    }
