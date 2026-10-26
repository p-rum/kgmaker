"""Bounded Spring condition evaluation over explicit compiler/context facts.

No environment, classloader or application is queried. Missing or malformed
facts stay UNKNOWN; a present property value is a string, not a Python truthy
value. Profile expressions follow Spring's no-mixed-operators grammar.
"""
from __future__ import annotations

import copy
import re

PROFILE = "org.springframework.context.annotation.Profile"
CUSTOM = "org.springframework.context.annotation.Conditional"
BOOT = "org.springframework.boot.autoconfigure.condition."
KEYS = ("spring_profiles", "spring_properties", "spring_available_classes")


class AnnotationArguments(str):
    """Preserve compiler member types alongside the legacy display string."""

    def __new__(cls, text, members, resolved=True):
        value = super().__new__(cls, text)
        value.members = copy.deepcopy(members)
        value.resolved = resolved
        return value


def condition_inputs(context):
    return {key: context.get(key) for key in KEYS}


def _strings(value):
    values = [value] if isinstance(value, str) else value
    if not isinstance(values, list) or any(not isinstance(x, str) or not x.strip() for x in values):
        raise ValueError("expected nonempty literal string members")
    return values


def _profile(expression, active):
    if not expression.strip() or len(expression) > 4096 or "${" in expression:
        raise ValueError("unsupported profile expression")
    tokens = re.findall(r"[!&|()]|[^!&|()\s]+", expression)
    if len(tokens) > 256:
        raise ValueError("profile expression budget exceeded")
    position = 0

    def group(depth=0):
        nonlocal position
        if depth > 64:
            raise ValueError("profile expression nesting budget exceeded")

        def atom():
            nonlocal position
            if position >= len(tokens):
                raise ValueError("missing profile operand")
            token = tokens[position]
            position += 1
            if token == "!":
                if depth + position > 256:
                    raise ValueError("profile negation budget exceeded")
                return not atom()
            if token == "(":
                result = group(depth + 1)
                if position >= len(tokens) or tokens[position] != ")":
                    raise ValueError("unclosed profile group")
                position += 1
                return result
            if token in {"&", "|", ")"}:
                raise ValueError("unexpected profile operator")
            return token in active

        result = atom()
        operator = None
        while position < len(tokens) and tokens[position] != ")":
            selected = tokens[position]
            if selected not in {"&", "|"} or operator is not None and operator != selected:
                raise ValueError("profile operators require explicit grouping")
            operator = selected
            position += 1
            other = atom()  # Always consume/validate the complete expression.
            result = result and other if operator == "&" else result or other
        return result

    result = group()
    if position != len(tokens):
        raise ValueError("unexpected profile group terminator")
    return result


def _evaluate(name, members, context):
    if name == PROFILE:
        active = context.get("spring_profiles")
        if not isinstance(active, list) or any(not isinstance(x, str) or not x.strip() for x in active):
            raise ValueError("active Spring profiles unavailable or malformed")
        expressions = _strings(members.get("value"))
        if not expressions:
            raise ValueError("empty profile condition")
        results = [_profile(item, set(active or ["default"])) for item in expressions]
        return any(results), "profile expressions evaluated against explicit active/default profiles"

    if name == BOOT + "ConditionalOnProperty":
        if set(members) - {"value", "name", "prefix", "havingValue", "matchIfMissing"}:
            raise ValueError("unsupported property annotation members")
        names = _strings(members.get("name", []))
        alias = _strings(members.get("value", []))
        if names and alias and names != alias:
            raise ValueError("conflicting property name/value aliases")
        names = names or alias
        if not names or any(not re.fullmatch(r"[A-Za-z0-9_.-]+", x) for x in names):
            raise ValueError("property names unavailable or unsupported")
        prefix = members.get("prefix", "")
        expected = members.get("havingValue", "")
        missing = members.get("matchIfMissing", False)
        if not isinstance(prefix, str) or not isinstance(expected, str) or type(missing) is not bool:
            raise ValueError("malformed property annotation member types")
        prefix = prefix.strip()
        if prefix and not re.fullmatch(r"[A-Za-z0-9_.-]+", prefix):
            raise ValueError("unsupported property prefix")
        prefix += "." if prefix and not prefix.endswith(".") else ""
        properties = context.get("spring_properties")
        if not isinstance(properties, dict) or any(not isinstance(k, str) for k in properties):
            raise ValueError("condition property snapshot unavailable or malformed")
        results = []
        for key in [prefix + item for item in names]:
            if key not in properties:
                results.append(missing)
                continue
            actual = properties[key]
            if not isinstance(actual, str) or "${" in actual or "${" in expected:
                raise ValueError("property value unresolved or not a literal string")
            results.append(actual.casefold() != "false" if expected == "" else actual.casefold() == expected.casefold())
        return all(results), "all explicit property keys must match: " + ", ".join(prefix + x for x in names)

    required = _strings(members.get("value", [])) + _strings(members.get("name", []))
    if not required or any(not re.fullmatch(r"[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*", x) for x in required):
        raise ValueError("required class identities unavailable or unsupported")
    inventory = context.get("spring_available_classes")
    if not isinstance(inventory, list) or any(not isinstance(x, str) or not x for x in inventory):
        raise ValueError("explicit class inventory unavailable or malformed")
    present = set(inventory)
    return (all(item not in present for item in required) if name.endswith("ConditionalOnMissingClass")
            else all(item in present for item in required)), "exact names evaluated against explicit context class inventory"


def evaluate_conditions(values, context):
    states, reasons = [], []
    supported = {PROFILE, BOOT + "ConditionalOnProperty", BOOT + "ConditionalOnClass",
                 BOOT + "ConditionalOnMissingClass"}
    for name, args in values:
        if name not in supported:
            if name == CUSTOM or name.startswith(BOOT + "Conditional"):
                states.append("UNKNOWN")
                reasons.append(name + ": custom/unsupported condition is not executed")
            continue
        try:
            if not isinstance(args, AnnotationArguments) or args.resolved is not True or not isinstance(args.members, dict):
                raise ValueError("typed resolved compiler annotation members unavailable")
            matched, reason = _evaluate(name, args.members, context)
            states.append("ACTIVE" if matched else "INACTIVE")
            reasons.append(name + ": " + reason)
        except (ValueError, RecursionError) as error:
            states.append("UNKNOWN")
            reasons.append(name + ": " + str(error))
    return ("INACTIVE" if "INACTIVE" in states else "UNKNOWN" if "UNKNOWN" in states else "ACTIVE"), reasons
