"""T046-S04 supported constraints and explicit unsupported boundaries."""
import unittest
from kgmaker.testgen import schema_errors


class SyntheticDataTests(unittest.TestCase):
    def test_nested_constraints_and_unknown_keywords_remain_explicit(self):
        schema={'type':'object','required':['amount','tag'],
                'properties':{'amount':{'type':'integer','minimum':1,'maximum':10},
                              'tag':{'type':'string','minLength':2,'maxLength':4,'pattern':'[a-z]+'}},
                'additionalProperties':False}
        errors,unknown=schema_errors({'amount':0,'tag':'x','extra':1},schema)
        self.assertEqual({'$.amount:minimum','$.tag:minLength','$.extra:additionalProperties'},set(errors))
        self.assertEqual(['$.tag:pattern'],unknown)
        self.assertEqual([],schema_errors({'amount':5,'tag':'ok'},schema)[0])

    def test_boolean_is_not_integer_and_nullability_is_explicit(self):
        self.assertEqual(['$:type'],schema_errors(True,{'type':'integer'})[0])
        self.assertEqual([],schema_errors(None,{'type':'integer','nullable':True})[0])
        self.assertEqual(['$:type'],schema_errors(None,{'type':'integer'})[0])
        self.assertEqual(['$:enum'],schema_errors('c',{'type':'string','enum':['a','b']})[0])
        self.assertEqual(['$:maximum'],schema_errors(11,{'type':'integer','maximum':10})[0])
        self.assertEqual(['$:maxLength'],schema_errors('long',{'type':'string','maxLength':3})[0])

    def test_missing_required_field_is_different_from_null(self):
        schema={'type':'object','required':['value'],'properties':{'value':{'type':'null'}}}
        self.assertEqual(['$.value:required'],schema_errors({},schema)[0])
        self.assertEqual([],schema_errors({'value':None},schema)[0])

    def test_enum_uses_json_types_recursively(self):
        examples = [(0, False, 'integer'), (1, True, 'integer'),
                    (True, 1, 'boolean'), ([0], [False], 'array'),
                    ({'x': [1]}, {'x': [True]}, 'object')]
        for value, choice, kind in examples:
            with self.subTest(value=value, choice=choice):
                errors, _ = schema_errors(value, {'type': kind, 'enum': [choice]})
                self.assertIn('$:enum', errors)
        for value, choice, kind in [(1, 1.0, 'number'), ([1], [1.0], 'array'),
                                    ({'a': 1, 'b': False}, {'b': False, 'a': 1.0}, 'object')]:
            with self.subTest(value=value):
                self.assertEqual([], schema_errors(value, {'type': kind, 'enum': [choice]})[0])
        self.assertIn('$:enum', schema_errors(None, {'type': 'integer', 'nullable': True, 'enum': [1]})[0])
