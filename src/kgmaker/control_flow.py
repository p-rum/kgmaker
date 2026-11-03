"""Deterministic CFG construction from worker-owned structured AST IR.

No file-order traversal, name matching, LLM input or path-feasibility inference.
Finally continuations are cloned with original IDs; abrupt completion never
silently becomes fallthrough. Exceptions are conservative candidate edges.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from .analysis_model import AnalysisError, digest

VERSION = "source-cfg-2"


@dataclass(frozen=True)
class Environment:
    exception: str
    finalizers: tuple = ()
    break_target: tuple[str, int] | None = None
    continue_target: tuple[str, int] | None = None
    suffix: str = ""


class Builder:
    def __init__(self, method: str, context_id: str, *, max_blocks: int = 3000, max_depth: int = 150):
        self.method, self.context_id = method, context_id
        self.max_blocks, self.max_depth = max_blocks, max_depth
        self.blocks, self.edges, self.diagnostics = {}, [], []
        self.serial = 0
        self.entry = self.node("entry", "entry", {}, Environment(""))
        self.exit = self.node("exit", "return/exit", {}, Environment(""))
        self.exceptional_exit = self.node("exceptional_exit", "uncaught exception", {}, Environment(""))

    def node(self, kind, label, ir, env):
        if len(self.blocks) >= self.max_blocks:
            raise AnalysisError("CFG block limit exceeded; no truncated CFG is published as complete", 4)
        self.serial += 1
        original = "ast:" + digest({"method": self.method, "path": ir.get("path"), "range": ir.get("range"), "kind": kind})[:24]
        identity = "cfg:" + digest({"method": self.method, "original": original, "suffix": env.suffix, "serial": self.serial})[:24]
        self.blocks[identity] = {"id": identity, "kind": kind, "label": label or kind,
                                "source_file": ir.get("path"), "source_range": ir.get("range"),
                                "sha256": ir.get("sha256"), "original_ids": [original],
                                "call_site_ids": [ir["call_site"]] if ir.get("call_site") else ir.get("calls", [])}
        if isinstance(ir.get("_verified_local_operation"), str):
            self.blocks[identity]["_verified_local_operation"] = ir["_verified_local_operation"]
        if ir.get("async_boundary") in {"SUSPEND", "LAUNCH", "ASYNC"}:
            self.blocks[identity].update(async_boundary=ir["async_boundary"], scheduling="UNKNOWN")
        return identity

    def edge(self, source, target, kind="normal", **metadata):
        if source not in self.blocks or target not in self.blocks:
            raise AnalysisError("Internal CFG edge refers to unknown block")
        metadata["loop_back"] = metadata.get("loop_back", self.blocks[target]["kind"] == "loop_header" and self.blocks[source]["kind"] != "entry")
        self.edges.append({"source": source, "target": target, "kind": kind, **metadata})

    def computation(self, ir, destination, env, kind="basic_block", label=None):
        node = self.node(kind, label or ir.get("label") or kind, ir, env)
        self.edge(node, destination)
        if ir.get("call_site") or ir.get("calls"):
            self.edge(node, env.exception, "exception", condition="may throw; feasibility not established")
        return node

    def abrupt(self, destination, env, *, keep=0, reason="return", depth=0):
        result = destination
        # Each frame saves the environment outside that finally. A return/throw
        # inside cleanup replaces the original continuation, as the language does.
        frames = env.finalizers[:max(0, len(env.finalizers) - keep)]
        for body, outside in reversed(frames):
            suffix = env.suffix + ":finally:" + reason + ":" + digest({"destination": destination})[:8]
            result = self.emit(body, result, replace(outside, suffix=suffix), depth + 1)
        return result

    def condition(self, ir, when_true, when_false, env, depth):
        kind = ir.get("kind", "empty")
        if kind == "and":
            right = self.condition(ir["right"], when_true, when_false, env, depth + 1)
            return self.condition(ir["left"], right, when_false, env, depth + 1)
        if kind == "or":
            right = self.condition(ir["right"], when_true, when_false, env, depth + 1)
            return self.condition(ir["left"], when_true, right, env, depth + 1)
        node = self.node("condition", ir.get("label") or "condition value", ir, env)
        self.edge(node, when_true, "true", condition="condition evaluates TRUE")
        self.edge(node, when_false, "false", condition="condition evaluates FALSE")
        if kind == "call":
            return self.emit(ir, node, env, depth + 1)
        if kind == "sequence":
            result = node
            for expression in reversed(ir.get("expressions", [])):
                result = self.emit(expression, result, env, depth + 1)
            return result
        if ir.get("calls"):
            self.edge(node, env.exception, "exception", condition="condition evaluation may throw")
        return node

    def emit(self, ir, destination, env, depth=0):
        if depth > self.max_depth:
            raise AnalysisError("CFG nesting limit exceeded", 4)
        if not isinstance(ir, dict):
            raise AnalysisError("Invalid worker IR node")
        kind = ir.get("kind", "empty")
        if kind == "statement" and ir.get("calls"):
            ir = {**ir, "kind": "unsupported", "reason": "UNSUPPORTED_EXPRESSION_EVALUATION_ORDER"}
            kind = "unsupported"
        if kind in {"empty", "reference"}:
            return destination
        if kind in {"block", "sequence"}:
            result = destination
            for statement in reversed(ir.get("statements" if kind == "block" else "expressions", [])):
                result = self.emit(statement, result, env, depth + 1)
            return result
        if kind == "if":
            yes = self.emit(ir.get("then", {"kind": "empty"}), destination, env, depth + 1)
            no = self.emit(ir.get("else", {"kind": "empty"}), destination, env, depth + 1)
            return self.condition(ir.get("condition", {"kind": "empty"}), yes, no, env, depth + 1)
        if kind in {"while", "do", "for", "foreach"}:
            header = self.node("loop_header", kind, ir, env)
            update = self.emit(ir.get("update", {"kind": "empty"}), header, env, depth + 1)
            inner = replace(env, break_target=(destination, len(env.finalizers)), continue_target=(update, len(env.finalizers)))
            body = self.emit(ir.get("body", {"kind": "empty"}), update, inner, depth + 1)
            test = self.condition(ir.get("condition", {"kind": "statement", "label": "iterator has next"}), body, destination, env, depth + 1)
            self.edge(header, test)
            result = body if kind == "do" else header
            if kind == "foreach":
                result = self.emit(ir.get("iterable", {"kind": "empty"}), result, env, depth + 1)
            if kind == "for":
                result = self.emit(ir.get("initial", {"kind": "empty"}), result, env, depth + 1)
            return result
        if kind in {"return", "throw", "break", "continue"}:
            if ir.get("labelled_target"):
                return self.boundary(ir, "LABELLED_CONTROL_FLOW", env)
            if kind == "return":
                target = self.abrupt(self.exit, env, reason="return", depth=depth)
            elif kind == "throw":
                target = env.exception
            else:
                selected = env.break_target if kind == "break" else env.continue_target
                if selected is None:
                    return self.boundary(ir, "UNBOUND_" + kind.upper(), env)
                target = self.abrupt(selected[0], env, keep=selected[1], reason=kind, depth=depth)
            node = self.node(kind, kind, ir, env)
            self.edge(node, target, kind)
            return self.emit(ir.get("value", {"kind": "empty"}), node, env, depth + 1)
        if kind == "try":
            if ir.get("resources"):
                return self.boundary(ir, "RESOURCE_CLOSE_CFG_UNSUPPORTED", env)
            cleanup = ir.get("finally")
            normal = self.emit(cleanup, destination, replace(env, suffix=env.suffix + ":finally:normal"), depth + 1) if cleanup else destination
            exceptional = self.emit(cleanup, env.exception, replace(env, suffix=env.suffix + ":finally:exception"), depth + 1) if cleanup else env.exception
            finalizers = ((cleanup, env),) + env.finalizers if cleanup else env.finalizers
            catch_env = replace(env, exception=exceptional, finalizers=finalizers)
            handler = exceptional
            for catch in reversed(ir.get("catches", [])):
                entry = self.emit(catch["body"], normal, catch_env, depth + 1)
                dispatch = self.node("exception_dispatch", "catch " + str(catch.get("type") or "unknown"), ir, env)
                self.edge(dispatch, entry, "exception", condition="first matching catch: " + str(catch.get("type") or "unknown"))
                self.edge(dispatch, handler, "exception", condition="does not match catch")
                handler = dispatch
            return self.emit(ir["body"], normal, replace(catch_env, exception=handler), depth + 1)
        if kind == "switch":
            # Kotlin when has no fallthrough; Java/TS switch keeps explicit
            # fallthrough in statement order. Break targets this switch only.
            cases = ir.get("cases", [])
            next_case = destination
            entries = []
            inner = replace(env, break_target=(destination, len(env.finalizers)))
            for case in reversed(cases):
                entry = self.emit(case["body"], next_case if ir.get("fallthrough") else destination, inner, depth + 1)
                entries.append((case, entry))
                next_case = entry
            dispatch = self.node("condition", "switch/when selection", ir, env)
            default = False
            for case, entry in reversed(entries):
                self.edge(dispatch, entry, "case", condition=case.get("label", "unknown"))
                default |= case.get("label") == "default"
            if not default:
                self.edge(dispatch, destination, "case", condition="no case matches")
            return self.emit(ir.get("condition", {"kind": "empty"}), dispatch, env, depth + 1)
        if kind in {"elvis", "safe_call"}:
            left = ir.get("left", ir.get("receiver", {"kind": "empty"}))
            right = ir.get("right", ir.get("then", {"kind": "empty"}))
            right_entry = self.emit(right, destination, env, depth + 1)
            test = self.node("condition", "value != null", ir, env)
            self.edge(test, destination if kind == "elvis" else right_entry, "true", condition="value is non-null")
            self.edge(test, right_entry if kind == "elvis" else destination, "false", condition="value is null")
            return self.emit(left, test, env, depth + 1)
        if kind in {"and", "or"}:
            return self.condition(ir, destination, destination, env, depth + 1)
        if kind in {"assign", "destructure"}:
            node = self.computation({**ir, "calls": []}, destination, env, label=kind)
            return self.emit(ir.get("value", {"kind": "empty"}), node, env, depth + 1)
        if kind in {"await", "suspend", "join"}:
            node = self.node("async_boundary", kind, ir, env)
            self.edge(node, destination, "resume", condition="continuation after completion; scheduling unknown")
            self.edge(node, env.exception, "exception", condition="completion failure/cancellation")
            return self.emit(ir.get("value", {"kind": "empty"}), node, env, depth + 1)
        if kind == "call":
            boundary = ir.get("async_boundary")
            if boundary in {"SUSPEND", "LAUNCH", "ASYNC"}:
                continuation = self.node("async_boundary", boundary.lower(), ir, env)
                self.edge(continuation, destination, "resume" if boundary == "SUSPEND" else "async",
                          condition="source continuation; scheduling and child completion unknown")
                self.edge(continuation, env.exception, "exception", condition="failure/cancellation boundary")
                destination = continuation
            node = self.computation(ir, destination, env, kind="call", label=ir.get("label") or "call")
            result = node
            for argument in reversed(ir.get("arguments", [])):
                result = self.emit(argument, result, env, depth + 1)
            return self.emit(ir.get("receiver", {"kind": "empty"}), result, env, depth + 1)
        if kind == "unsupported":
            return self.boundary(ir, ir.get("reason", "UNSUPPORTED_IR"), env)
        return self.computation(ir, destination, env)

    def boundary(self, ir, reason, env):
        self.diagnostics.append({"code": reason, "source_file": ir.get("path"), "source_range": ir.get("range")})
        return self.node("unresolved_boundary", reason, ir, env)

    def build(self, body: dict) -> dict:
        env = Environment(self.exceptional_exit)
        start = self.emit(body, self.exit, env)
        self.edge(self.entry, start)
        return {"method": self.method, "context_id": self.context_id, "version": VERSION,
                "entry": self.entry, "exit": self.exit, "exceptional_exit": self.exceptional_exit,
                "representation": "SOURCE", "status": "PARTIAL" if self.diagnostics else "COMPLETE_WITHIN_SUPPORTED_SYNTAX",
                "blocks": sorted(self.blocks.values(), key=lambda b: b["id"]),
                "edges": sorted(self.edges, key=lambda e: (e["source"], e["target"], e["kind"], e.get("condition", ""))),
                "diagnostics": self.diagnostics,
                "limitations": ["Static paths are not proof of feasible inputs or runtime execution.",
                                "Exceptional edges are conservative; unknown exception types remain visible."]}


def from_body(record: dict, **limits) -> dict:
    return Builder(record["method"], record["context_id"], **limits).build(record["body"])
