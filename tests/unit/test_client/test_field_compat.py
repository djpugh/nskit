"""Tests for the string-condition / superset field-spec compatibility layer.

These cover the additions that let downstreams expressing fields with a
string ``"op:value"`` condition format (and ``help_text``/``display_name``)
use nskit's field models directly.
"""

from __future__ import annotations

import unittest

from nskit.client.field_models import ConditionalAction, ConditionalRule, FieldSpec
from nskit.client.interactive import InteractiveHandler


class TestConditionalRuleStringForm(unittest.TestCase):
    """The ``condition`` shorthand expands into operator/value."""

    def test_ne_true(self) -> None:
        r = ConditionalRule(depends_on="is_plugin", condition="ne:true")
        self.assertEqual(r.operator, "not_equals")
        self.assertEqual(r.value, "true")
        self.assertEqual(r.action, ConditionalAction.SKIP)

    def test_eq_alias(self) -> None:
        r = ConditionalRule(depends_on="x", condition="eq:dev")
        self.assertEqual(r.operator, "equals")
        self.assertEqual(r.value, "dev")

    def test_in_splits_csv(self) -> None:
        r = ConditionalRule(depends_on="env", condition="in:dev,acc,prod")
        self.assertEqual(r.operator, "in")
        self.assertEqual(r.value, ["dev", "acc", "prod"])

    def test_gt(self) -> None:
        r = ConditionalRule(depends_on="n", condition="gt:10")
        self.assertEqual(r.operator, "gt")
        self.assertEqual(r.value, "10")

    def test_structured_form_still_works(self) -> None:
        r = ConditionalRule(depends_on="x", operator="equals", value=3, action=ConditionalAction.SKIP)
        self.assertEqual(r.operator, "equals")
        self.assertEqual(r.value, 3)


class TestEvaluateConditionCompat(unittest.TestCase):
    """The evaluator matches the legacy string-based semantics."""

    def setUp(self) -> None:
        self.h = InteractiveHandler.__new__(InteractiveHandler)

    def test_ne_true_matches_legacy_semantics(self) -> None:
        # str(actual).lower() != "true"
        self.assertFalse(self.h._evaluate_condition(True, "not_equals", "true"))
        self.assertTrue(self.h._evaluate_condition(False, "not_equals", "true"))

    def test_eq_case_insensitive(self) -> None:
        self.assertTrue(self.h._evaluate_condition("Dev", "equals", "dev"))
        self.assertTrue(self.h._evaluate_condition("eq", "eq", "EQ"))

    def test_gt_lt(self) -> None:
        self.assertTrue(self.h._evaluate_condition("5", "gt", "3"))
        self.assertFalse(self.h._evaluate_condition("5", "lt", "3"))
        self.assertFalse(self.h._evaluate_condition("notanumber", "gt", "3"))

    def test_in_string_form(self) -> None:
        self.assertTrue(self.h._evaluate_condition("DEV", "in", ["dev", "acc"]))
        self.assertTrue(self.h._evaluate_condition("x", "not_in", ["dev", "acc"]))

    def test_typed_comparison_when_expected_not_string(self) -> None:
        # Non-string expected -> native typed comparison.
        self.assertTrue(self.h._evaluate_condition(3, "equals", 3))
        self.assertFalse(self.h._evaluate_condition(3, "equals", 4))
        self.assertTrue(self.h._evaluate_condition("b", "in", ["a", "b"]))

    def test_string_expected_stringifies_actual(self) -> None:
        # Expected is a string -> actual is stringified (e.g. 3 vs "3").
        self.assertTrue(self.h._evaluate_condition(3, "equals", "3"))


class TestFieldSpecSuperset(unittest.TestCase):
    """help_text / display_name are carried on FieldSpec."""

    def test_help_text_and_display_name(self) -> None:
        fs = FieldSpec(name="x", help_text="some help", display_name="X Field")
        self.assertEqual(fs.help_text, "some help")
        self.assertEqual(fs.display_name, "X Field")


if __name__ == "__main__":
    unittest.main()
