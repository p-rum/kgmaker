import unittest

from kgmaker.dataflow import extract_dataflow, impact_paths
from kgmaker.model import Edge, KnowledgeGraph, Node


class DataflowTests(unittest.TestCase):
    def test_kotlin_constructor_fields_expression_and_mapping(self):
        source = '''data class Input(val pessimisticDecline: Double)
data class Report(val midDecline: Double)
class Calculator {
    fun calculate(input: Input): Report {
        val midDecline = input.pessimisticDecline / 2
        return Report(midDecline)
    }
}
'''
        result = extract_dataflow({'scenario.kt': source})
        self.assertEqual([], result.diagnostics)
        field = next(n for n in result.nodes if n.name == 'Input.pessimisticDecline')
        target = next(n for n in result.nodes if n.name == 'Report.midDecline')
        derived = next(e for e in result.edges if e.kind == 'derived_from')
        self.assertEqual(field.id, derived.target)
        self.assertEqual(5, derived.source_line)
        mapping = next(e for e in result.edges if e.kind == 'maps_to')
        self.assertEqual(target.id, mapping.target)
        self.assertEqual('EXTRACTED', mapping.confidence)
        graph = KnowledgeGraph(1, '.', '', result.nodes, result.edges, {})
        impact = impact_paths(graph, field.id)
        self.assertTrue(any(p['entity_ids'][-1] == target.id for p in impact['paths']))
        self.assertFalse(any(p['entity_ids'][-1] == field.id for p in impact_paths(graph, target.id)['paths']))

    def test_field_inventory_for_java_typescript_and_json(self):
        result = extract_dataflow({
            'A.java': 'record Position(double volume, String currency) {}\nclass Account {\n private double balance;\n private String currency;\n void f() { double local = 0; }\n}',
            'Report.ts': 'export interface Report {\n value: number;\n readonly currency?: string;\n}\ntype Alias = { amount: number }',
            'api.json': '{"components":{"schemas":{"Result":{"properties":{"a/b":{"type":"number"}}}}}}',
        })
        names = {n.name for n in result.nodes}
        self.assertTrue({'Position.volume', 'Position.currency', 'Account.balance', 'Account.currency', 'Report.value', 'Report.currency', 'Alias.amount'} <= names)
        self.assertNotIn('Account.local', names)
        json_node = next(n for n in result.nodes if n.kind == 'contract_field')
        self.assertEqual('/components/schemas/Result/properties/a~1b', json_node.name)
        self.assertIsNone(json_node.line)

    def test_ambiguous_types_do_not_create_maps(self):
        result = extract_dataflow({'one.kt': 'data class Input(val value: Double)',
                                  'two.kt': 'data class Input(val value: Double)',
                                  'calc.kt': 'fun twice(input: Input): Double = input.value * 2\n'})
        self.assertFalse(result.edges)
        self.assertTrue(any('unresolved expression' in d['reason'] for d in result.diagnostics))

    def test_control_flow_calls_and_comments_do_not_fabricate_dependencies(self):
        source = '''// data class Fake(val x: Double)
data class Input(val x: Double)
fun conditional(input: Input): Double { if (true) return input.x; return 0 }
fun call(input: Input): Double = unknown(input.x)
'''
        result = extract_dataflow({'a.kt': source})
        self.assertFalse(result.edges)
        self.assertFalse(any('Fake' in n.name for n in result.nodes))
        self.assertEqual(2, len(result.diagnostics))

    def test_same_method_name_in_different_owners_has_distinct_identity(self):
        result = extract_dataflow({'a.kt': 'class One {\n fun f(x: Double): Double = x * 2\n}\nclass Two {\n fun f(x: Double): Double = x * 3\n}'})
        returns = [n for n in result.nodes if n.kind == 'return_value']
        self.assertEqual(2, len(returns))
        self.assertNotEqual(returns[0].id, returns[1].id)
        self.assertFalse(result.diagnostics)

    def test_fa35_direction_weakest_link_and_external_boundary(self):
        nodes = [Node(x, 'external_system' if x == 'pdf' else 'data_field', x, 'a.kt') for x in ['input', 'output', 'dto', 'ui', 'pdf', 'internal']]
        edges = [Edge('output', 'input', 'derived_from'), Edge('output', 'dto', 'maps_to'),
                 Edge('dto', 'ui', 'displayed_in', confidence='INFERRED'), Edge('dto', 'pdf', 'sent_to'),
                 Edge('pdf', 'internal', 'maps_to')]
        graph = KnowledgeGraph(1, '.', '', nodes, edges, {})
        result = impact_paths(graph, 'input')
        by_target = {p['entity_ids'][-1]: p for p in result['paths']}
        self.assertEqual({'output', 'dto', 'ui', 'pdf'}, set(by_target))
        self.assertEqual('INFERRED', by_target['ui']['weakest_confidence'])
        self.assertIn('external', by_target['pdf']['unresolved_boundary'])
        self.assertEqual([], impact_paths(graph, 'ui')['paths'])
        self.assertTrue(impact_paths(graph, 'input', max_depth=1)['truncated'])

    def test_comment_only_edit_preserves_field_ids(self):
        before = extract_dataflow({'a.kt': 'data class Input(val x: Double)\n'})
        after = extract_dataflow({'a.kt': '// comment\ndata class Input(val x: Double)\n'})
        self.assertEqual([n.id for n in before.nodes], [n.id for n in after.nodes])
        self.assertNotEqual(before.nodes[0].line, after.nodes[0].line)

    def test_parameter_reassignment_does_not_create_false_proof(self):
        source = 'data class Input(val value: Double)\nfun f(input: Input): Double {\n input = unknown()\n return input.value\n}\n'
        result = extract_dataflow({'a.kt': source})
        self.assertEqual([], result.edges)
        self.assertTrue(result.diagnostics)
