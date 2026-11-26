"""Shared VBA control and definition provenance for inventory consumers."""

from collections import defaultdict


def bound_relations(rows, relations):
    """Yield inventory relations with a flag for proven VBA-local context."""
    operation_parents = defaultdict(list)
    for edge in relations:
        if edge["kind"] == "contains" and rows[edge["target"]]["kind"] == "vba-operation":
            operation_parents[edge["target"]].append(edge)

    # An inventory hash checks content integrity. Bind local control and
    # definition links to their containing procedures before following them.
    sites = {}
    scope_fields = ("workbook", "module", "procedure")
    for key, parents in operation_parents.items():
        if len(parents) != 1:
            continue
        parent = parents[0]["source"]
        owner = rows[parent]
        if (owner["kind"] != "vba-procedure" or owner.get("complete") is not True
                or parents[0]["evidence"] != [parent]):
            continue
        place, declaration = rows[key]["locator"], owner["locator"]
        if any(not isinstance(place.get(field), str) or not place[field]
               or place[field] != declaration.get(field) for field in scope_fields):
            continue
        start, end = declaration.get("line"), declaration.get("end_line")
        line, statement = place.get("line"), place.get("statement")
        if (all(type(number) is int for number in (start, end, line, statement))
                and 0 < start <= line <= end and statement > 0):
            sites[key] = (parent, line, statement)

    for edge in relations:
        source, target, kind = edge["source"], edge["target"], edge["kind"]
        local = kind == "guarded-by" or (kind == "depends-on" and rows[source]["kind"] == "vba-operation")
        if local:
            source_site, target_site = sites.get(source), sites.get(target)
            if (source_site is None or target_site is None or source_site[0] != target_site[0]
                    or target_site[1] > source_site[1] or target_site[2] >= source_site[2]
                    or edge["evidence"] != [source]):
                continue
            operation = rows[target].get("operation")
            if kind == "guarded-by":
                if (operation != "condition" or rows[target].get("conditional") is not True
                        or rows[source].get("conditional") is not True):
                    continue
            elif operation not in ("assignment", "return-value"):
                continue
        yield edge, local


def local_alternatives(row, definition_ids):
    """Retain alternatives supported by multiple admitted definition links."""
    alternatives = row.get("alternatives")
    result = {}
    if isinstance(alternatives, dict):
        admitted = set(definition_ids)
        for symbol, choices in alternatives.items():
            if isinstance(choices, list):
                valid = list(dict.fromkeys(key for key in choices if isinstance(key, str) and key in admitted))
                if len(valid) > 1:
                    result[symbol] = valid
    return result
