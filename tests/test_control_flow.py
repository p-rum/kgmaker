"""Independent structural expectations, not rendered text golden files."""
import unittest
from collections import defaultdict, deque

from kgmaker.control_flow import from_body
from kgmaker.flow import mermaid


def ir(kind, **fields):
    return {"kind": kind, "label": kind, "path": "Source.kt", "sha256": "a"*64,
            "range": {"start": 0, "end": 1, "start_line": 1}, **fields}


def reachable(cfg, source, target, excluded_kinds=()):
    outgoing=defaultdict(list)
    for e in cfg["edges"]:
        if e["kind"] not in excluded_kinds:
            outgoing[e["source"]].append(e["target"])
    seen, queue=set(), deque([source])
    while queue:
        node=queue.popleft()
        if node==target:return True
        if node in seen:continue
        seen.add(node);queue.extend(outgoing[node])
    return False


class ControlFlowTests(unittest.TestCase):
    def build(self, body):
        return from_body({"method":"method:a","context_id":"context:a","body":body})

    def test_flow02_opposite_branches_never_form_b_then_c(self):
        cfg=self.build(ir("if", condition=ir("statement",label="flag"),
            then=ir("return",value=ir("call",call_site="b",label="B",arguments=[])),
            **{"else":ir("return",value=ir("call",call_site="c",label="C",arguments=[]))}))
        calls={b["call_site_ids"][0]:b["id"] for b in cfg["blocks"] if b["kind"]=="call"}
        self.assertFalse(reachable(cfg,calls["b"],calls["c"]))
        self.assertFalse(reachable(cfg,calls["c"],calls["b"]))
        self.assertEqual({"true","false"},{e["kind"] for e in cfg["edges"] if e["source"] in {b["id"] for b in cfg["blocks"] if b["kind"]=="condition"}})

    def test_nested_arguments_execute_before_outer_call(self):
        cfg=self.build(ir("call",call_site="outer",label="outer(inner())",
                          arguments=[ir("call",call_site="inner",label="inner",arguments=[])]))
        calls={b["call_site_ids"][0]:b["id"] for b in cfg["blocks"] if b["kind"]=="call"}
        self.assertTrue(reachable(cfg,calls["inner"],calls["outer"],("exception",)))
        self.assertFalse(reachable(cfg,calls["outer"],calls["inner"]))

    def test_flow01_return_and_throw_route_through_finally(self):
        cfg=self.build(ir("try", body=ir("if", condition=ir("statement",label="flag"),
            then=ir("return",value=ir("call",call_site="value",label="value",arguments=[])),
            **{"else":ir("throw",value=ir("call",call_site="error",label="error",arguments=[]))}),
            catches=[], **{"finally":ir("call",call_site="cleanup",label="cleanup",arguments=[])}))
        returns=[b for b in cfg["blocks"] if b["kind"]=="return"]
        throws=[b for b in cfg["blocks"] if b["kind"]=="throw"]
        cleanup={b["id"] for b in cfg["blocks"] if b.get("call_site_ids")==["cleanup"]}
        for b in returns+throws:
            edges=[e for e in cfg["edges"] if e["source"]==b["id"]]
            self.assertEqual(1,len(edges));self.assertIn(edges[0]["target"],cleanup)
        self.assertTrue(any(reachable(cfg,cfg["entry"],c) for c in cleanup))

    def test_break_inside_try_runs_cleanup_but_outer_try_cleanup_is_not_early(self):
        cfg=self.build(ir("while",condition=ir("statement",label="again"),body=ir("try",
            body=ir("break"),catches=[],**{"finally":ir("call",call_site="cleanup",label="cleanup",arguments=[])})))
        node=next(b for b in cfg["blocks"] if b["kind"]=="break")
        target=next(e["target"] for e in cfg["edges"] if e["source"]==node["id"])
        self.assertEqual(["cleanup"],next(b for b in cfg["blocks"] if b["id"]==target)["call_site_ids"])
        outer=self.build(ir("try",body=ir("while",condition=ir("statement",label="again"),body=ir("break")),catches=[],
            **{"finally":ir("call",call_site="cleanup",label="cleanup",arguments=[])}))
        self.assertTrue(any(e.get("loop_back") for e in cfg["edges"]))
        self.assertEqual(1,len([b for b in outer["blocks"] if b["kind"]=="break"]))

    def test_finally_return_overrides_prior_return(self):
        cfg=self.build(ir("try",body=ir("return",value=ir("call",call_site="first",label="first",arguments=[])),catches=[],
                         **{"finally":ir("return",value=ir("call",call_site="override",label="override",arguments=[]))}))
        first=next(b for b in cfg["blocks"] if b.get("call_site_ids")==["first"])
        override=[b["id"] for b in cfg["blocks"] if b.get("call_site_ids")==["override"]]
        self.assertTrue(any(reachable(cfg,first["id"],o,("exception",)) for o in override))

    def test_flow03_await_has_explicit_resume_and_exception_boundary(self):
        cfg=self.build(ir("await",value=ir("call",call_site="request",label="request",arguments=[])))
        await_node=next(b for b in cfg["blocks"] if b["kind"]=="async_boundary")
        self.assertEqual({"resume","exception"},{e["kind"] for e in cfg["edges"] if e["source"]==await_node["id"]})

    def test_flow04_mermaid_escapes_labels_and_is_deterministic(self):
        cfg=self.build(ir("statement",label='special "[x]" | <tag> & stuff'))
        report={"cfg":cfg}
        self.assertEqual(mermaid(report),mermaid(report))
        self.assertIn("&quot;",mermaid(report));self.assertIn("&#124;",mermaid(report))

    def test_unknown_expression_calls_do_not_gain_invented_evaluation_order(self):
        cfg=self.build(ir("statement",calls=["a","b"],label="opaque expression"))
        self.assertEqual("PARTIAL",cfg["status"])
        self.assertTrue(any(b["kind"]=="unresolved_boundary" and b["call_site_ids"]==["a","b"] for b in cfg["blocks"]))

    def test_unsupported_resource_close_is_visible_boundary_not_guessed_fallthrough(self):
        cfg=self.build(ir("try",resources=[ir("statement")],body=ir("statement"),catches=[]))
        self.assertEqual("PARTIAL",cfg["status"])
        self.assertTrue(any(b["kind"]=="unresolved_boundary" for b in cfg["blocks"]))


if __name__=='__main__': unittest.main()
